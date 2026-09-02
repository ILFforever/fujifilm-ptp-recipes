# XRFC per-generation value tables

**TL;DR** — X RAW STUDIO ships, inside `XRFC.dll`, a set of lookup tables that define the legal
values of each recipe property **per camera generation**. Ten properties are generation-bound — nine
of them inside the 23-property recipe block, plus File Type which is never sent to the camera. The
other fourteen block properties are not bound at all. Where a property is generation-bound, the
*encoding is stable* and only the *supported set* changes — with one exception, `ImageSize`, whose
value space genuinely differs and which is the reason Fuji's compatibility fallback exists.

This page records those tables in full, the mechanism that selects between them, and the mapping from
camera body to variant.

Confidence labels follow [README.md](README.md): **CONFIRMED** (read directly in code or binary
data), **INFERRED**, **UNRESOLVED**.

---

## 1. Scope and what this is not

**CONFIRMED.** The source is `XRFC.dll`, the application layer of X RAW STUDIO. These tables are the
values Fuji's own client considers legal for a given body in the tether-RAW-conversion workflow.

They are **not** a statement of camera firmware behaviour. A body may accept a value this table omits,
or reject one it lists. Nothing here has been verified against a non-X-Trans-V camera. Treat the
tables as Fuji's own risk ranking, not as a compatibility guarantee.

Everything below is derived from static analysis. No camera is required to reproduce it.

---

## 2. How the variant system works

**CONFIRMED.**

`XRFC.DAT` decodes to `ConversionCaps` XML — see
[xrfc-capability-database.md](xrfc-capability-database.md). Each per-model `PropertyGroup` records
each setting twice: whether the body supports it at all, and *which encoding variant* it uses.

```xml
<FilmSimulation type="Std2">true</FilmSimulation>
<ImageSize      type="Std3">true</ImageSize>
<NoiseReduction type="Std1">true</NoiseReduction>
```

At DLL load, a set of static initialisers construct one `std::multimap<std::string,int>` per
generation-bound property. The key is the variant name (`Std1`…`Std6`, `Ext1`…`Ext3`); each mapped
value is one legal wire value. A property with 6 variants and 105 total entries is one multimap with
105 nodes.

When the capability file is parsed, each property's parser:

1. reads the element text and compares it against the literal `"true"` — the result becomes that
   property's "supported" boolean in the capability record (the offset is per-property: `+0x120` for
   Film Simulation, `+0x140` for Grain Effect, `+0x1d8` for Colour Temperature, and so on);
2. if supported, reads the `<xmlattr>.type` attribute;
3. performs `equal_range(type)` on that property's multimap;
4. pushes every mapped value into a `std::vector<int>` stored in the capability record.

Three properties depart from step 3. Grain Effect and a few others key their primary map on the
element *text* rather than the type attribute, and Colour Temperature's `Std2` bypasses the map
entirely to write a continuous range. Those cases are covered in §10, §11 and §13.

The capability record is `0x448` bytes. For `FilmSimulation` the vector's `begin`/`end` live at
`+0x128`/`+0x130`; `CapabilityClass::GetFilmSimulation` returns its length via
`(end - begin) >> 2` and memcpys the array out to the caller. `XRFC_CapFilmSimulation` is the
public entry point.

If the attribute is absent the parser substitutes the literal `"Std1"`.

### Consequence

The variant name never reaches the camera. It selects which value list the client considers legal
*before* anything is written. A third-party client has no access to this table at runtime — it must
either hard-code the equivalent or detect capability from `GetDeviceInfo`.

---

## 3. Extraction method

**CONFIRMED.** Reproducible from a Ghidra decompile of `XRFC.dll` plus `pefile`:

1. **Find every multimap.** Each is built by an initialiser of the shape
   `DAT_<map> = FUN_180065ba0(); puVar = &DAT_<start>; do { ... } while (puVar != &DAT_<end>);`
   The loop bounds give the backing array exactly — entry stride is `0x28`
   (`std::string` = `0x20`, `int` at `+0x20`, 4 bytes padding). 380 such loops exist in the binary.
2. **Bind map to property.** The parser function for a property contains the literal
   `"<Property>.<xmlattr>.type"` and references that property's map global. This is what makes the
   binding exact rather than guessed by address proximity.
3. **Read entries.** For each slot in `[start, end)` recover the key string and the int at `+0x20`.
4. **Resolve strings.** Key strings are `&DAT_` pointers into `.rdata`; read them from the PE.

> **Pitfall that produced wrong results twice.** The compiler emits **four** different construction
> shapes for these pairs, and matching only some silently drops entries:
>
> | Shape | Form |
> |---|---|
> | A | `FUN_180060410(&DAT_slot, &DAT_str, len)` then `_DAT_(slot+0x20) = v` |
> | B | `local_a = &DAT_str; local_b = v; FUN_180064250(&DAT_slot, &local_a)` |
> | C | `FUN_180060410(&DAT_slot, "literal", len)` — key given as a C literal |
> | D | `FUN_18005cf70(&DAT_slot, &DAT_str)` — copy-construct from another `std::string` |
>
> Additionally, the **first call in each initialiser** carries extra trailing arguments
> (`, in_R9, 0xfffffffffffffffe`), so a regex anchored on a closing parenthesis after the length
> drops the first entry of every array. Always verify recovered count equals
> `(end - start) / 0x28` before trusting a table.

Every table below is at **100 % coverage** by that check.

The binary contains **two identical copies** of the whole table set (a second linked instance at
`0x1804a****`). Sizes and contents match; only one is described here.

---

## 4. Summary: which properties are generation-bound

**CONFIRMED.**

| PTP code | Property | Variants in code | Nature of the difference |
|---|---|---:|---|
| `0xD18E` | Image Size | 7 | **Different value spaces.** The only property with a fallback shim |
| `0xD192` | Film Simulation | 6 | Nested range, `1..15` → `1..20` |
| `0xD18F` | Image Quality | 2 | `Std1 [2,3]`, `Ext1 [6,2,3]` |
| `0xD199` | White Balance | 2 | `Std2` = `Std1` + Auto White Priority and Auto Ambience Priority |
| `0xD19C` | Colour Temperature | 2 | `Std1` = a 31-value list; `Std2` = a **continuous range**, not a list |
| `0xD195` | Grain Effect | 2 | Variant governs whether a grain **size** axis exists at all |
| `0xD19D` | Highlight Tone | 2 | `Std2` adds half-steps |
| `0xD19E` | Shadow Tone | 2 | `Std2` adds half-steps |
| `0xD1A1` | High ISO NR | 2 | **Identical** — the variants do not differ |
| — | File Type | 3 | Not sent to the camera at all |

**The remaining fourteen block properties have no generation-bound table.** The capability data
records only supported / not-supported for them:

`0xD190` Dynamic Range · `0xD191` Dynamic Range Priority · `0xD193` Mono Warm/Cool ·
`0xD194` Mono Magenta/Green · `0xD196` Colour Chrome Effect · `0xD197` Colour Chrome FX Blue ·
`0xD198` Smooth Skin Effect · `0xD19A` WB Shift Red · `0xD19B` WB Shift Blue · `0xD19F` Colour ·
`0xD1A0` Sharpness · `0xD1A2` Clarity · `0xD1A3` Lens Modulation Optimiser · `0xD1A4` Colour Space

For those, the only cross-generation question is whether the body has the property — not what a
value means.

---

## 5. Film Simulation (`0xD192`)

Map `DAT_18049d248`, array `0x1803e5c10`–`0x1803e6c78`, **105 / 105 entries**.

**CONFIRMED.** The six variants are a strictly nested chain. Each adds exactly one simulation, and
numbering is identical across all of them — value `1` is Provia on every body.

| Variant | Count | Legal values | Newly added |
|---|---:|---|---|
| `Std1` | 15 | 1–15 | — |
| `Std2` | 16 | 1–16 | 16 Eterna |
| `Std3` | 17 | 1–17 | 17 Classic Neg |
| `Std4` | 18 | 1–18 | 18 Eterna Bleach Bypass |
| `Std5` | 19 | 1–19 | 19 Nostalgic Neg |
| `Std6` | 20 | 1–20 | 20 Reala Ace |

Names are from [properties.md](../properties.md#film-simulation-0xd192); the numbering is
independently corroborated by a separate label table giving the monochrome filters as
`BW=6, BYe=7, BR=8, BG=9`.

### External validation

The chain matches the real-world debut of each simulation, which is strong evidence the extraction is
correct:

| Added | Simulation | First variant | First bodies in that variant |
|---|---|---|---|
| 16 | Eterna | `Std2` | X-H1, X-T3, X-T30 |
| 17 | Classic Neg | `Std3` | X-Pro3, X100V |
| 18 | Eterna Bleach Bypass | `Std4` | X-T4 |
| 19 | Nostalgic Neg | `Std5` | GFX100S |
| 20 | Reala Ace | `Std6` | GFX100 II |

Each simulation's first appearance in the table is the camera it actually launched on.

### Practical consequence

Because the chain is nested with stable numbering, a value from a newer body written to an older one
is **out of range, not misinterpreted**. It will be rejected, not silently applied as a different
simulation.

| Variant | Bodies |
|---|---|
| `Std1` | X-T2, X-Pro2, X-T20, X-E3, X100F, GFX50S (fw 1–2), GFX50R (fw 1) |
| `Std2` | X-H1, X-T3, X-T30, GFX100 (fw 1) |
| `Std3` | X-Pro3, X100V, GFX50S (fw 3), GFX50R (fw 2) |
| `Std4` | X-T4, X-S10, X-E4, X-T30II, GFX100 (fw 2) |
| `Std5` | X-H2 (fw 1), X-T5 (fw 1), X-H2S (fw 1), X-S20 (fw 1), GFX100S, GFX50SII, GFX100 (fw 3) |
| `Std6` | X-H2 (fw 2), X-T5 (fw 2), X-H2S (fw 2), X-S20 (fw 2), X-T50, X100VI, X-E5, X-M5, X-T30III, GFX100 II, GFX100S II, GFX100RF |

---

## 6. Image Size (`0xD18E`)

> **Not a film-simulation setting.** Image Size carries no recipe data and recipe clients should skip
> it. It is documented here for one reason only: it is the property Fuji's compatibility fallback
> exists for, so it is the one place where a client writing the full block can trip. Read §6.2 for
> that, and skip the rest.

Map `DAT_18049e068`, array `0x1803e1440`–`0x1803e24f8`, **107 / 107 entries**.

This is the one property whose value space genuinely fragments. See
[current-shooting-state.md](../current-shooting-state.md) for the fallback mechanism.

### 6.1 The value labels

**CONFIRMED.** A wide-string label table (`FUN_180007cd0`, array based at `0x1803e0e50`) names every
value. Labels are `<size><width>x<height>` — `L`/`M`/`S` for large/medium/small.

| Value | Label | Value | Label | Value | Label |
|---:|---|---:|---|---:|---|
| 1 | S3x2 | 11 | S65x24 | 21 | M7x6 |
| 2 | S16x9 | 12 | S5x4 | 22 | L3x4 |
| 3 | S1x1 | 13 | S7x6 | 23 | L17x6 |
| 4 | M3x2 | 14 | L4x3 | 24 | M3x4 |
| 5 | M16x9 | 15 | L65x24 | 25 | M17x6 |
| 6 | M1x1 | 16 | L5x4 | 26 | S3x4 |
| 7 | L3x2 | 17 | L7x6 | 27 | S17x6 |
| 8 | L16x9 | 18 | M4x3 | 28 | INSTAX_MINI |
| 9 | L1x1 | 19 | M65x24 | 29 | INSTAX_SQ |
| 10 | S4x3 | 20 | M5x4 | 30 | INSTAX_WIDE |

Values 1–27 are the full cross product of 3 sizes × 9 aspect ratios. 28–30 are INSTAX print sizes.

### 6.2 The fallback table decoded

**CONFIRMED.** Fuji's 27-entry lookup table decomposes a composite Image Size value into a column
`1–9` and a row `1–3`. Overlaying the labels above resolves both axes completely:

```
          col1    col2    col3    col4    col5    col6    col7    col8    col9
         (3:4)   (1:1)   (7:6)   (5:4)   (4:3)   (3:2)  (16:9) (65:24)  (17:6)
row 1 :   L3x4    L1x1    L7x6    L5x4    L4x3    L3x2   L16x9  L65x24   L17x6
row 2 :   M3x4    M1x1    M7x6    M5x4    M4x3    M3x2   M16x9  M65x24   M17x6
row 3 :   S3x4    S1x1    S7x6    S5x4    S4x3    S3x2   S16x9  S65x24   S17x6
```

Raw values, for reference:

```
row 1 :    22       9      17      16      14       7       8      15      23
row 2 :    24       6      21      20      18       4       5      19      25
row 3 :    26       3      13      12      10       1       2      11      27
```

**Row = image size (L / M / S). Column = aspect ratio.** All 27 cells are named, every row resolves
to a single size prefix, and every column to a single aspect ratio, with no contradictions.

This explains the fallback's purpose: older bodies exposed size and aspect ratio as **two separate
properties**, so the client decomposes the composite and sends the parts. Newer bodies accept the
composite in a single write to `0xD18E`.

The two paths are not symmetric:

| Path | Sends | Carries |
|---|---|---|
| Live / C0 | `0xD03A` = column, `0xD03B` = row | size **and** aspect ratio |
| Slot C1–C7 | `0xD1A8` = row only | size only — the aspect ratio is discarded |

The slot block has no aspect-ratio counterpart, so on that path the column is computed, used only to
test whether the lookup succeeded, and never transmitted. The matching read reconstructs from the row
alone and therefore always yields column 1 — the 3:4 aspect — regardless of the camera's actual
setting. See [current-shooting-state.md](../current-shooting-state.md) for the read-side detail.

There is no read path for the aspect ratio anywhere in the binaries, so the loss is structural — the
SDK recovers only the size class, and the 3:4 aspect it substitutes is a placeholder. Fuji's client
discards it and re-uses the aspect it already holds. Only GFX100RF can reach this path.

> If you ever read Image Size back on such a body, treat `0xD1A8` as **size class only, aspect
> unknown**. Using the returned value verbatim reports a crop the camera is not set to.

Note also that `Std4`'s INSTAX values (28, 29, 30) fall outside this 27-entry table entirely. If a
camera rejected one, the decomposition would find nothing and the error would stand.

`Ext3` (GFX100RF) is the only variant carrying all 27 combinations, and its entries partition exactly
into the three rows above — an independent confirmation of the row structure.

### 6.3 Variants

| Variant | Count | Values | Notes |
|---|---:|---|---|
| `Std1` | 9 | 1–9 | Defined in code; **no body uses it** |
| `Std2` | 9 | 1–9 | 3:2, 16:9 and 1:1 only, in L/M/S |
| `Std3` | 15 | 1–10, 12, 14, 16, 18, 20 | Adds 4:3 and 5:4 |
| `Std4` | 12 | 1–9, 28, 29, 30 | `Std2` set plus the three INSTAX sizes |
| `Ext1` | 14 | 1–3, 7–17 | GFX |
| `Ext2` | 21 | 1–21 | GFX |
| `Ext3` | 27 | 1–27 | GFX; the complete space |

| Variant | Bodies |
|---|---|
| *unsupported* | X-T2, X-Pro2, X-T20, X-E3, X100F |
| `Std2` | X-H1, X-T3, X-T30, X-Pro3, X100V, X-T4, X-S10, X-E4, X-T30II, X-H2S, X-S20, X-M5 |
| `Std3` | X-H2, X-T5, X-T50, X100VI, X-E5 |
| `Std4` | X-T30III |
| `Ext1` | GFX50S, GFX50R, GFX50SII |
| `Ext2` | GFX100, GFX100S, GFX100 II, GFX100S II |
| `Ext3` | GFX100RF |

Note that `Std2` and `Std3` are the split that matters for X-Trans: an X-H2 (`Std3`) accepts fifteen
values where an X-T4 (`Std2`) accepts nine, and the nine are a subset. `Std4` is not a superset of
anything — it swaps the extra aspect ratios for INSTAX sizes.

---

## 7. Highlight Tone (`0xD19D`) and Shadow Tone (`0xD19E`)

Maps `DAT_18049dcd8` and `DAT_18049ce88`, **20 / 20 entries each**. Both properties carry identical
tables.

**CONFIRMED.** Values are the display dial × 10, matching
[properties.md](../properties.md#scaled-signed-dials). The variants differ only in step size.

| Variant | Count | Values | Dial |
|---|---:|---|---|
| `Std1` | 7 | −20, −10, 0, 10, 20, 30, 40 | −2 … +4 in whole steps |
| `Std2` | 13 | −20, −15, −10, −5, 0, 5, 10, 15, 20, 25, 30, 35, 40 | −2 … +4 in half steps |

`Std2` is a strict superset. Encoding is unchanged, so a whole-step value written to a `Std1` body
works; only half-step values are out of range there.

| Variant | Bodies |
|---|---|
| `Std1` | X-T2, X-Pro2, X-T20, X-E3, X100F, X-H1, X-T3, X-T30, X-Pro3, X100V, GFX50S, GFX50R, GFX100 (fw 1–2) |
| `Std2` | X-T4, X-S10, X-E4, X-T30II, X-H2, X-H2S, X-T5, X-S20, X-T50, X100VI, X-E5, X-M5, X-T30III, GFX100 (fw 3), GFX100S, GFX50SII, GFX100 II, GFX100S II, GFX100RF |

---

## 8. High ISO NR (`0xD1A1`)

Map `DAT_18049d5e8`, **18 / 18 entries**.

**CONFIRMED.** `Std1` and `Std2` contain the **same nine values in the same order**. The variant
distinction is recorded in the capability data but has no effect on the legal value set.

| Order | Wire | Dial |
|---:|---:|---:|
| 1 | 20480 | +4 |
| 2 | 24576 | +3 |
| 3 | 0 | +2 |
| 4 | 4096 | +1 |
| 5 | 8192 | 0 |
| 6 | 12288 | −1 |
| 7 | 16384 | −2 |
| 8 | 28672 | −3 |
| 9 | 32768 | −4 |

This matches the non-linear lookup in [properties.md](../properties.md#high-iso-nr-0xd1a1) exactly,
which is a useful independent check on the whole extraction: these are wire values, not GUI numbers.

---

## 9. White Balance (`0xD199`)

Map `DAT_18049e458`, **26 / 26 entries**.

**CONFIRMED.**

| Variant | Count | Values (hex) |
|---|---:|---|
| `Std1` | 12 | `0x0002`, `0x0004`, `0x0006`, `0x0008`, `0x8001`, `0x8002`, `0x8003`, `0x8006`, `0x8007`, `0x8008`, `0x8009`, `0x800A` |
| `Std2` | 14 | `Std1` plus `0x8020`, `0x8021` |

> **Graduated.** All fourteen modes have since been confirmed on an X-H2 (firmware 5.20) by writing
> each one, reading it back and restoring the original — including the five that existed only in
> Fuji's label table: `0x8020`, `0x8021` and Custom 1-3 (`0x8008`-`0x800A`). The confirmed set now
> lives in [properties.md](../properties.md#white-balance-0xd199); this section is kept for the
> derivation only.
>
> The X-H2 is a `Std2` body, so accepting all fourteen is exactly what this table predicts — the
> result confirms the `Std2` set rather than contradicting the variant split. Custom 1-3 sit in both
> `Std1` and `Std2`, so confirming them says nothing about generation either way. The two modes that
> would actually test the boundary are `0x8020` and `0x8021`, which are `Std2`-only: whether a
> `Std1` body such as an X-T3 rejects them is still untested, and would be the first direct check of
> a variant boundary against real firmware.

A wide-string label table in `FUN_180003930` names every mode, which resolves the whole set:

| Value | Label | Value | Label |
|---|---|---|---|
| `0x0002` | Auto | `0x8003` | Fluorescent 3 |
| `0x0004` | Daylight | `0x8006` | Shade |
| `0x0006` | Incandescent | `0x8007` | Colour Temperature |
| `0x0008` | Underwater | `0x8008` | Custom 1 |
| `0x8001` | Fluorescent 1 | `0x8009` | Custom 2 |
| `0x8002` | Fluorescent 2 | `0x800A` | Custom 3 |
| `0x8020` | **Auto White Priority** | `0x8021` | **Auto Ambience Priority** |

So the `Std2` addition is the two Auto-priority modes introduced on later bodies. `Std1` is the other
twelve, and `Std2` is a strict superset.

`0x0002`, `0x0004`, `0x0006` and `0x0008` are the PTP-standard White Balance values.

Body split is *nearly* the same as Highlight/Shadow Tone, with one exception: **GFX100 firmware 3
uses `Std1` for White Balance while using `Std2` for the tone dials** — see §14.

---

## 10. Colour Temperature (`0xD19C`)

Map `DAT_18049cd08`, **31 / 31 entries**. One variant only.

**CONFIRMED.** Kelvin values, descending as stored:

```
10000  9100  8300  7700  7100  6700  6300  5900  5600  5300
 5000  4800  4500  4300  4200  4000  3800  3700  3600  3400
 3300  3200  3100  3000  2950  2850  2800  2700  2650  2550
 2500
```

### `Std2` is a continuous range, not a list

**CONFIRMED.** Most configurations declare `type="Std2"`, for which the multimap holds nothing —
because `Std2` does not use the map at all. The parser `FUN_180059cb0` branches on the literal
`"Std2"` and writes a range instead of a list:

```c
*(rec + 0x1d9) = 1;        // "continuous range" flag
*(rec + 0x1f8) = 10000;    // maximum
*(rec + 0x1fc) = 0x9c4;    // 2500, minimum
```

`CapabilityClass::GetWBColorTemp` branches on that flag and returns **min 2500, max 10000, step 10**
rather than an enumerated set.

So the generational difference is the opposite of a restriction: older `Std1` bodies are limited to
the 31 fixed steps above, while newer `Std2` bodies accept any Kelvin value in 2500–10000 at
10 K granularity.

---

## 11. Grain Effect (`0xD195`)

**CONFIRMED** — read directly in the block builder `FUN_1800c55f0` (§15), which writes index `[7]`,
the slot that becomes `0xD195`.

Grain reaches the camera as a single composite value, but X RAW STUDIO holds it as two fields:

| `lGrainEffect` (`0x1078`) | | `lGrainEffectSize` (`0xf48`) | |
|---:|---|---:|---|
| 1 | OFF | 1 | SMALL |
| 2 | WEAK | 2 | LARGE |
| 3 | STRONG | | |

The builder combines them:

| Grain | Size | Wire value |
|---:|---:|---:|
| 1 OFF | *any* | **1** |
| 2 WEAK | 1 SMALL | 2 |
| 3 STRONG | 1 SMALL | 3 |
| 2 WEAK | 2 LARGE | 4 |
| 3 STRONG | 2 LARGE | 5 |

Exactly matches [properties.md](../properties.md#grain-effect-0xd195): `1` = Off, `2`–`5` =
weak/strong × small/large.

> **Correction.** An earlier revision of this page claimed Off + Large produced composite `7`. That
> came from `FUN_1800addf0`, a *different* serialiser that feeds a larger parameter array, not the
> SDK block. On the block path Off yields `1` regardless of size, and **no value `7` is produced**.

### The variant controls the size axis, not the strength list

**CONFIRMED.** The parser `FUN_180058ff0` performs **two** lookups against **two different maps**:

| Map | Keyed by | Contents | Meaning |
|---|---|---|---|
| `DAT_18049cdc8` | element text `"true"` | `1, 2, 3` | grain **strength** — not generation-bound |
| `DAT_18049d028` | type `"Std2"` | `1, 2` | grain **size** — generation-bound |

The strength list is identical on every body. The second lookup runs **only** when the type is
`Std2`, and additionally sets a flag in the capability record. `XRFC_CapGrainEffect` and
`XRFC_CapGrainEffectSize` are separate exports reading the two vectors, and `GetGrainEffectSize`
explicitly rejects when strength is `1` (Off).

So `Std1` is not a missing table. **`Std1` means the body has no grain-size axis at all** — which is
why the 11 configurations using it are all pre-2019 bodies. On those bodies the size component does
not exist, so the composites `4` and `5` (weak/strong × large) are unreachable and only `1`, `2`,
`3` can be produced.

---

## 12. Image Quality (`0xD18F`) and File Type

> **Neither is a film-simulation setting.** Recipe clients should skip both. File Type is never sent
> to the camera at all. Recorded here for completeness, and because Image Quality is one of only two
> fields the block builder transforms rather than copies.

**Image Quality**, map `DAT_18049d0e8`, **5 / 5 entries**:

| Variant | Values | Bodies |
|---|---|---|
| `Std1` | 2, 3 | all X-series that support it |
| `Ext1` | 6, 2, 3 | all GFX |

**CONFIRMED** from the wide-string label table in `FUN_180007b70`, which is complete:

| Value | Label |
|---:|---|
| 2 | Fine |
| 3 | Normal |
| 6 | SuperFine |

So `Ext1` (GFX) adds SuperFine on top of the Fine/Normal pair every X-series body has.

### Image Quality is remapped before it reaches the wire

**CONFIRMED** in `FUN_1800c55f0` (§15). Image Quality is the **only** property in the block that is
not copied verbatim. Depending on a context byte `c = *(param_4 + 4)`:

- If `c > 7`, or bit `c` of the mask `0xB2` is clear — i.e. `c ∉ {1, 4, 5, 7}` — the value is passed
  through unchanged.
- Otherwise it is remapped: `2 → 4`, `3 → 5`, `6 → 7`, and **any other value → 4**.

So the wire can carry `4`, `5` or `7` for `0xD18F` even though the capability tables only ever list
`2`, `3` and `6`. Any client comparing a read-back against the variant table must account for this.

**UNRESOLVED:** what `param_4` is. It is passed down from
`XRFCClass::SetCustomSettingsBy{Attached,Registered}Profile` and is not the `RAWSettings` pointer.

**File Type**, map `DAT_18049e448`, **10 / 10 entries**:

| Variant | Values | Decoded | Bodies |
|---|---|---|---|
| `Std1` | 7, 9 | JPG, TIF | GFX50S, GFX50R |
| `Ext1` | 7, 9, 11 | JPG, TIF, TIF_16BIT | GFX100 (fw 1–3), GFX100S, GFX50SII, X-Pro3, X-T4 |
| `Ext2` | 7, 18, 9, 11 | JPG, HIF, TIF, TIF_16BIT | X-H2, X-H2S, X-T5, X-S20, X-T50, X100VI, X-E5, X-M5, X-T30III, GFX100 II, GFX100S II, GFX100RF |

All four labels are **CONFIRMED**: `JPG = 7`, `TIF = 9`, `TIF_16BIT = 11`, `HIF = 18`. `TIF_16BIT`
appears with value `0xb` in both the narrow-string table (`FUN_180060410(&DAT_1803e4c30,
"TIF_16BIT", 9)` → `_DAT_1803e4c50 = 0xb`) and the wide-string table used for profile XML.

The array also contains one entry keyed `"false"` with value `7`, i.e. a JPG default for bodies where
File Type is unsupported. **UNRESOLVED:** which code path queries the map with that key.

---

## 13. Variants that are not backed by a value list

Four variants are declared in the XML with no matching key in their property's multimap. **None of
them is a missing table or a bug.** In each case the variant selects an alternative representation,
and the parser handles it in a branch alongside the `equal_range` call.

| Property | Variant | What the parser actually does |
|---|---|---|
| Colour Temperature | `Std2` | Writes a continuous range (min 2500, max 10000, step 10) and sets a range flag — §10 |
| Grain Effect | `Std1` | Means "no grain-size axis"; the strength list is keyed by element text, not by variant — §11 |
| CustomSetting | `Std2` | Stores the scalar `2` in the capability record; its map is keyed `true`/`false` |
| DigitalTeleConv | `Std2`, `Std3` | Stores the scalar `2` or `3`; its map is keyed `true` |

The `equal_range` miss path was traced and is never taken for any of these.

> **Correction.** An earlier revision of this page presented these four as "declared-but-missing
> tables" and called them "the most likely place for a bug in Fuji's own client". That was wrong. The
> analysis had stopped at "no `Std2` key in the multimap" without reading the parser's else-branch,
> which sits in the same function and contains the answer.

---

## 14. Complete per-device variant matrix

**CONFIRMED**, decoded from `XRFC.DAT`. `NO` = property not supported; blank columns omitted.
Firmware suffix is the capability key's, e.g. `X-H2_0200` is the `_0200` capability record.

| Device | ImageSize | ImageQual | FilmSim | Grain | WB | WBTemp | HiTone | ShTone | NR | FileType |
|---|---|---|---|---|---|---|---|---|---|---|
| X-T2_0100 | NO | NO | Std1 | Std1 | Std1 | Std1 | Std1 | Std1 | Std1 | NO |
| X-Pro2_0100 | NO | NO | Std1 | Std1 | Std1 | Std1 | Std1 | Std1 | Std1 | NO |
| X-T20_0100 | NO | NO | Std1 | Std1 | Std1 | Std1 | Std1 | Std1 | Std1 | NO |
| X-E3_0100 | NO | NO | Std1 | Std1 | Std1 | Std1 | Std1 | Std1 | Std1 | NO |
| X100F_0100 | NO | NO | Std1 | Std1 | Std1 | Std1 | Std1 | Std1 | Std1 | NO |
| X-H1_0100 | Std2 | Std1 | Std2 | Std1 | Std1 | Std1 | Std1 | Std1 | Std1 | NO |
| X-T3_0100 | Std2 | Std1 | Std2 | Std1 | Std1 | Std1 | Std1 | Std1 | Std1 | NO |
| X-T30_0100 | Std2 | Std1 | Std2 | Std1 | Std1 | Std1 | Std1 | Std1 | Std1 | NO |
| X-Pro3_0100 | Std2 | Std1 | Std3 | Std2 | Std1 | Std2 | Std1 | Std1 | Std1 | Ext1 |
| X100V_0100 | Std2 | Std1 | Std3 | Std2 | Std1 | Std2 | Std1 | Std1 | Std1 | NO |
| X100V_0200 | Std2 | Std1 | Std3 | Std2 | Std1 | Std2 | Std1 | Std1 | Std1 | NO |
| X-T4_0100 | Std2 | Std1 | Std4 | Std2 | Std2 | Std2 | Std2 | Std2 | Std2 | Ext1 |
| X-S10_0100 | Std2 | Std1 | Std4 | Std2 | Std2 | Std2 | Std2 | Std2 | Std2 | NO |
| X-E4_0100 | Std2 | Std1 | Std4 | Std2 | Std2 | Std2 | Std2 | Std2 | Std2 | NO |
| X-T30II_0100 | Std2 | Std1 | Std4 | Std2 | Std2 | Std2 | Std2 | Std2 | Std2 | NO |
| X-H2S_0100 | Std2 | Std1 | Std5 | Std2 | Std2 | Std2 | Std2 | Std2 | Std2 | Ext2 |
| X-H2S_0200 | Std2 | Std1 | Std6 | Std2 | Std2 | Std2 | Std2 | Std2 | Std2 | Ext2 |
| X-H2_0100 | Std3 | Std1 | Std5 | Std2 | Std2 | Std2 | Std2 | Std2 | Std2 | Ext2 |
| X-H2_0200 | Std3 | Std1 | Std6 | Std2 | Std2 | Std2 | Std2 | Std2 | Std2 | Ext2 |
| X-T5_0100 | Std3 | Std1 | Std5 | Std2 | Std2 | Std2 | Std2 | Std2 | Std2 | Ext2 |
| X-T5_0200 | Std3 | Std1 | Std6 | Std2 | Std2 | Std2 | Std2 | Std2 | Std2 | Ext2 |
| X-S20_0100 | Std2 | Std1 | Std5 | Std2 | Std2 | Std2 | Std2 | Std2 | Std2 | Ext2 |
| X-S20_0200 | Std2 | Std1 | Std6 | Std2 | Std2 | Std2 | Std2 | Std2 | Std2 | Ext2 |
| X-T50_0100 | Std3 | Std1 | Std6 | Std2 | Std2 | Std2 | Std2 | Std2 | Std2 | Ext2 |
| X100VI_0100 | Std3 | Std1 | Std6 | Std2 | Std2 | Std2 | Std2 | Std2 | Std2 | Ext2 |
| X-E5_0100 | Std3 | Std1 | Std6 | Std2 | Std2 | Std2 | Std2 | Std2 | Std2 | Ext2 |
| X-M5_0100 | Std2 | Std1 | Std6 | Std2 | Std2 | Std2 | Std2 | Std2 | Std2 | Ext2 |
| X-T30III_0100 | Std4 | Std1 | Std6 | Std2 | Std2 | Std2 | Std2 | Std2 | Std2 | Ext2 |
| GFX50S_0100 | Ext1 | Ext1 | Std1 | Std1 | Std1 | Std1 | Std1 | Std1 | Std1 | Std1 |
| GFX50S_0200 | Ext1 | Ext1 | Std1 | Std1 | Std1 | Std1 | Std1 | Std1 | Std1 | Std1 |
| GFX50S_0300 | Ext1 | Ext1 | Std3 | Std1 | Std1 | Std1 | Std1 | Std1 | Std1 | Std1 |
| GFX50R_0100 | Ext1 | Ext1 | Std1 | Std1 | Std1 | Std1 | Std1 | Std1 | Std1 | Std1 |
| GFX50R_0200 | Ext1 | Ext1 | Std3 | Std1 | Std1 | Std1 | Std1 | Std1 | Std1 | Std1 |
| GFX50SII_0100 | Ext1 | Ext1 | Std5 | Std2 | Std2 | Std2 | Std2 | Std2 | Std2 | Ext1 |
| GFX100_0100 | Ext2 | Ext1 | Std2 | Std1 | Std1 | Std1 | Std1 | Std1 | Std1 | Ext1 |
| GFX100_0200 | Ext2 | Ext1 | Std4 | Std2 | Std1 | Std1 | Std1 | Std1 | Std1 | Ext1 |
| GFX100_0300 | Ext2 | Ext1 | Std5 | Std2 | Std1 | Std1 | Std2 | Std2 | Std2 | Ext1 |
| GFX100S_0100 | Ext2 | Ext1 | Std5 | Std2 | Std2 | Std2 | Std2 | Std2 | Std2 | Ext1 |
| GFX100II_0100 | Ext2 | Ext1 | Std6 | Std2 | Std2 | Std2 | Std2 | Std2 | Std2 | Ext2 |
| GFX100SII_0100 | Ext2 | Ext1 | Std6 | Std2 | Std2 | Std2 | Std2 | Std2 | Std2 | Ext2 |
| GFX100RF_0100 | Ext3 | Ext1 | Std6 | Std2 | Std2 | Std2 | Std2 | Std2 | Std2 | Ext2 |

### Reading the matrix

- **Firmware changes the variant.** X-H2 moves `Std5` → `Std6` for Film Simulation between capability
  records `_0100` and `_0200`, gaining Reala Ace. The camera's PTP identity string carries the
  firmware component, so the client picks a different table for the same body after an update.
- **X-Trans V is not uniform.** X-H2/X-T5/X-T50/X100VI/X-E5 are `Std3` for Image Size while
  X-H2S/X-S20/X-M5 are `Std2`. Sensor generation does not determine the variant.
- **GFX100 fw 3 is inconsistent.** It moves to `Std2` for the tone dials and NR but stays `Std1` for
  White Balance and Colour Temperature, unlike every other body that made that transition.

---

## 15. The block builder — `FUN_1800c55f0`

**CONFIRMED.** This is the single function that turns a `RAWSettings` structure into the 23-int array
handed to `XSDK_SetCustomSettingParameter`. It is the authoritative source for the block's field
order and for every transform applied on the way out.

It is called from `XRFCClass::SetCustomSettingsByAttachedProfile` and
`XRFCClass::SetCustomSettingsByRegisteredProfile`, in both cases between the logged
`XSDK_GetCustomSettingParameter` and `XSDK_SetCustomSettingParameter` calls. Its `param_2` output
buffer is the one passed to the setter.

| Index | Source | Field | PTP (slot / live) |
|---:|---|---|---|
| 0 | `0x1058` | `lImageSize` | `0xD18E` / `0xD1A5` |
| 1 | `0x105c` | `lImageQuality` — **remapped**, see §12 | `0xD18F` / `0xD018` |
| 2 | `0x1064` | `lDynamicRange` | `0xD190` / `0xD007` |
| 3 | `0x1068` | `lWideDynamicRange` | `0xD191` / `0xD02E` |
| 4 | `0x106c` | `lFilmSimulation` | `0xD192` / `0xD001` |
| 5 | `0x1070` | `lBlackImageTone` | `0xD193` / `0xD104` |
| 6 | `0x1074` | `lMonochromaticColor_RG` | `0xD194` / `0xD031` |
| 7 | `0x1078` + `0xf48` | grain composite — **combined**, see §11 | `0xD195` / `0xD023` |
| 8 | `0x107c` | `lColorChromeEffect` | `0xD196` / `0xD029` |
| 9 | `0x1080` | `lColorChromeBlue` | `0xD197` / `0xD030` |
| 10 | `0x1084` | `lSmoothSkinEffect` | `0xD198` / `0xD189` |
| 11 | `0x108c` | `lWhiteBalance` | `0xD199` / `0x5005` |
| 12 | `0x1090` | `lWBShift_R` | `0xD19A` / `0xD00B` |
| 13 | `0x1094` | `lWBShift_B` | `0xD19B` / `0xD00C` |
| 14 | `0x1098` | `lWBColorTemp` | `0xD19C` / `0xD017` |
| 15 | `0x109c` | `lHighLightTone` | `0xD19D` / `0xD320` |
| 16 | `0x10a0` | `lShadowTone` | `0xD19E` / `0xD321` |
| 17 | `0x10a4` | `lColorMode` | `0xD19F` / `0xD008` |
| 18 | `0x10a8` | `lSharpness` | `0xD1A0` / `0x5015` |
| 19 | `0x10ac` | `lNoiseReduction` | `0xD1A1` / `0xD01C` |
| 20 | `0x10b0` | `lClarity` | `0xD1A2` / `0xD032` |
| 21 | `0x10b4` | `lLMOMode` | `0xD1A3` / `0xD34D` |
| 22 | `0x10b8` | `lColorSpace` | `0xD1A4` / `0xD00A` |

Exactly 23 entries. `lFileType` (`0x1054`) is never read, and `lExposureBias` (`0x1060`) and
`lWBShootCond` (`0x1088`) are skipped mid-run — which is why the block is the offset range
`0x1058`–`0x10b8` minus those two.

### Emit order

The SDK writes the block in ascending code order with one exception: Colour Temperature is pulled
forward and sent immediately after White Balance, ahead of the WB shifts. Both branches do it.

```text
slot :  … 0xD198, 0xD199, 0xD19C, 0xD19A, 0xD19B, 0xD19D …
live :  … 0xD189, 0x5005, 0xD017, 0xD00B, 0xD00C, 0xD320 …
```

**This is what Fuji does, not a requirement.** Write order has not been found to matter on X-Trans V,
where implementations write in plain ascending order successfully. The reordering is presumably
defensive on some body or generation, but nothing in the binaries says which, and no camera has been
observed rejecting a write for ordering reasons.

Distinct from ordering, and hardware-confirmed: Colour Temperature is only *writable* while White
Balance is in colour-temperature mode. That is a state prerequisite, not a sequence requirement —
see [current-shooting-state.md](../current-shooting-state.md).

### What this settles

This function replaces several claims that were previously derived from positional alignment against
`RAWSettingsClass::OutputLog`. They are now read directly:

- Block row 1 is `lImageSize` and row 2 is `lImageQuality`.
- `0xD193` is `lBlackImageTone`; `0xD194` is `lMonochromaticColor_RG`.
- `lFileType` is genuinely not sent to the camera.
- Twenty-one of the 23 fields are verbatim copies. Only Image Quality and Grain Effect are
  transformed, so for every other property the RAWSettings value *is* the wire value.

## 16. Open questions

On the recipe properties:

- **`NoiseReduction` `Std1` and `Std2` are byte-identical.** What the variant name distinguishes, if
  anything, is unresolved — no other consumer of it was found.

On Image Size, Image Quality and File Type — none of which carry recipe data, listed only so the
loose ends are on record and nobody re-derives them:

- `ImageSize` `Std1` and `Std2` are byte-identical, and no body uses `Std1`.
- The `FileType` array has a tenth entry keyed `"false"` (value 7) that appears unreachable.
- `Std4`'s INSTAX values (28–30) sit outside the 27-cell table, so the fallback cannot decompose them.
- The vendor property names for `0xD03A`, `0xD03B` and `0xD1A8` appear nowhere in the binaries; their
  meanings here come from the table decomposition, not from a symbol.

### Values the application knows but no capability set lists

`FUJIFILM_X_RAW_STUDIO.exe` carries a complete set of value→label maps (managed code, under its
logging component). They agree with `XRFC.dll`'s tables everywhere the two overlap — including all 30
Image Size codes, the File Type set, and High ISO NR's non-linear keys — which is a useful third
source. But three of them contain values that appear in **no** capability variant:

| Property | Extra values | Label |
|---|---|---|
| **White Balance** | 36865 (`0x9001`) | "as-shot white balance" |
| **Grain Effect Size** | 0 | OFF, alongside 1 SMALL and 2 LARGE |
| Image Quality | 20–23 | HEIF and its fine/normal variants — not recipe data |

Whether these are reachable on any camera, or are application-side states that never go on the wire,
is unresolved. Grain Effect Size `0` is at least consistent with the decode-only composite `7` noted
in §11. The two that matter for recipes are White Balance and Grain.

### Dynamic Range Priority: the client has no Auto

`32768` appears in `XRFC.dll` in exactly one place — the High ISO NR table, where it means `-4`.
There is **no `32768` in any Dynamic Range Priority path in Fuji's client**, while hardware testing on
an X-H2 established `32768` = Auto for `0xD191`
([properties.md](../properties.md#dynamic-range-priority-0xd191)).

That is not a contradiction between two accounts of the same thing. The block builder copies
`lWideDynamicRange` verbatim to `0xD191`, so the client sends exactly what its profile holds — and a
RAW converter has no use for Auto. Auto is a capture-time decision the camera resolves when the frame
is taken; by conversion time it has already become a concrete level. So the camera property accepts a
value the desktop profile format never needs to store.

**Practical reading:** `32768` is valid on the wire (tested), and a client that writes it is not
following a path Fuji's own software exercises. Whether older bodies accept it is untested.

**Not fully resolved.** The application's DR-Priority label map reads `0`–`3` rather than
`0`/`1`/`2`/`32768`. A four-entry table `0=0, P1=1, P2=2, P3=3` exists in `XRFC.dll`
(`FUN_180002a60`), but its map global is only constructed and copied — never queried anywhere that
could be traced — so it could not be bound to `WideDynamicRange` from `XRFC.dll` alone. Whether the
camera accepts `3`, and what it would mean, is untested.
- **None of this is hardware-verified.** Every table is Fuji's client-side view. Confirming even one
  variant boundary on a real non-X-Trans-V body — for example that an X-T4 rejects Film Simulation
  `19` — would convert this from protocol evidence into documented behaviour.
