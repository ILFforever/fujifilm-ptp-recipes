# Current shooting state (C0): applying a recipe without a slot

**TL;DR** — The camera's current shooting state, what you get in P/A/S/M, is often called "C0". It
is **not** a slot. There is no slot number `0`. The live state has its own set of property codes,
one per setting, running in parallel to the C1–C7 block.

Applying a recipe live is the same values you would write to a slot, sent to **different property
codes**, with **no slot selector**.

## The two paths

| | C1–C7 (stored) | Live / C0 (current state) |
|---|---|---|
| Select first | write `0xD18C` = `1`–`7` | nothing — there is no selector |
| Name | `0xD18D` (string) | not applicable |
| Settings | `0xD18E`–`0xD1A4` | the live codes in the table below |
| Operation | `SetDevicePropValue` (`0x1016`) | identical |
| Value format | 2 bytes, little-endian | identical |

The mechanism is the same. Only the property numbers change.

They are genuinely separate stores. On an X-H2 in a single session, slot Film Simulation (`0xD192`,
with C7 selected) read `12` while live Film Simulation (`0xD001`) read `4` — the camera was shooting
one recipe while C7 held another.

## Property map

`INT16` values are signed and must be decoded as such. `UINT16` are unsigned. Both are 2 bytes
little-endian on the wire.

| Setting | Slot code | Live code | Type |
|---|---|---|---|
| Image Size | `0xD18E` | `0xD1A5` | UINT16 |
| Image Quality | `0xD18F` | `0xD018` | UINT16 |
| Dynamic Range | `0xD190` | `0xD007` | UINT16 |
| Wide D-Range / D-Range Priority | `0xD191` | `0xD02E` | UINT16 |
| Film Simulation | `0xD192` | `0xD001` | UINT16 |
| Monochromatic Color — Warm/Cool | `0xD193` | `0xD104` | INT16 |
| Monochromatic Color — Magenta/Green | `0xD194` | `0xD031` | INT16 |
| Grain Effect | `0xD195` | `0xD023` | UINT16 |
| Color Chrome Effect | `0xD196` | `0xD029` | UINT16 |
| Color Chrome FX Blue | `0xD197` | `0xD030` | UINT16 |
| Smooth Skin Effect | `0xD198` | `0xD189` | UINT16 |
| White Balance | `0xD199` | `0x5005` | UINT16 |
| WB Shift — Red | `0xD19A` | `0xD00B` | INT16 |
| WB Shift — Blue | `0xD19B` | `0xD00C` | INT16 |
| Color Temperature | `0xD19C` | `0xD017` | UINT16 |
| Highlight Tone | `0xD19D` | `0xD320` | INT16 |
| Shadow Tone | `0xD19E` | `0xD321` | INT16 |
| Color | `0xD19F` | `0xD008` | INT16 |
| Sharpness | `0xD1A0` | `0x5015` | INT16 |
| Noise Reduction | `0xD1A1` | `0xD01C` | UINT16 |
| Clarity | `0xD1A2` | `0xD032` | INT16 |
| Lens Modulation Optimiser | `0xD1A3` | `0xD34D` | UINT16 |
| Color Space | `0xD1A4` | `0xD00A` | UINT16 |

The first two rows, Image Size and Image Quality, are not film-simulation settings and are of low
relevance to recipe work; most implementations omit them. They are listed because they are part of
the block and because row 1 is the property Fuji's compatibility fallback applies to.

Value encodings are shared with the slot properties — see [properties.md](properties.md). Dynamic
Range is the literal percentage (`100`/`200`/`400`, `0` = Auto); White Balance uses `0x8007` for
colour-temperature mode; the tone dials are the dial position × 10.

## Common pitfalls

**Nine properties are signed.** Decode them as `INT16`. Reading them as unsigned turns Highlight
Tone `-10` into `65526` and WB Shift `-2` into `65534`.

**Some properties require a prerequisite property to be set first:**

| Property | Requires |
|---|---|
| Color Temperature (`0xD017`) | White Balance (`0x5005`) set to `0x8007` |
| Mono WC (`0xD104`), Mono MG (`0xD031`) | a monochrome film simulation active |

Writing the property before its prerequisite is set returns `InvalidDevicePropValue` (`0x201C`),
which is easy to mistake for a wrong property code. Distinguish the two:

- `0x201C` — the property exists; the **value** is invalid.
- `0x200A` — the property does not exist on this body.

**Values are not contiguous.** `current + 1` is usually invalid: Grain Effect is an enum (`1` = Off,
`2`–`5` = weak/strong × small/large), High ISO NR is a non-linear lookup, and the tone dials step by
10. Use the encodings in [properties.md](properties.md).

## Discovering what a body supports

`GetDeviceInfo` (`0x1001`) returns the camera's full supported-property list. Every live code above
appears in it on a supporting body, which makes it a reliable capability check.

**Do not rely on `GetDevicePropDesc` (`0x1014`).** The X-H2 lists it as a supported operation but
returns an empty data phase followed by `GeneralError` (`0x2002`) for every property, including
PTP-standard ones. The request is well formed and the session is unaffected — the operation is
simply a stub on that body.

A workable substitute: read the same setting from slots C1–C7. Those are values the camera is
already holding, so they are legal for that body by definition.

## Verification status

Confirmed on an **X-H2, firmware 5.20** (capability key `X-H2_0200`):

- All 23 live codes appear in the camera's own `DeviceInfo` supported-property list.
- All 23 read back correct values.
- All 23 verified by write — a different value written, read back changed, then restored. This
  includes every conditional property, once its prerequisite was set.

Not yet tested on any other body. Live codes are expected to be stable across models in the same way
the slot codes are, but that is an assumption until someone checks. Results from other bodies are
welcome — see [testing-checklist.md](testing-checklist.md).

### Restore order matters for gated properties

Colour Temperature (`0xD017`) reads `0` when White Balance is not in colour-temperature mode, and
`0` is not a writable Kelvin value.

So if you change it and want to put things back, **restore the temperature first, while White
Balance is still `0x8007`, and revert White Balance last.** Reverting White Balance first makes the
temperature unwritable, and the camera keeps whatever you last set.

The same rule applies to Mono WC/MG under a monochrome film simulation: restore the gated property
before the property gating it.

## Why these pairings are trustworthy

The mapping was recovered from FUJIFILM X RAW STUDIO, Fuji's own desktop app. Its
`XSDK_SetCustomSettingParameter` function writes the stored block and the live block from **the same
source struct, at the same memory offsets, in the same order** — offset `0x08` feeds slot `0xD190`
and live `0xD007`, offset `0x38` feeds slot `0xD19C` and live `0xD017`, and so on for all 23. That
offset-for-offset correspondence is what pairs each code with its counterpart.

Four pairs land on codes documented independently, from unrelated work, which is a useful check that
the table is not self-confirming:

- `0xD007` was already known as the live Dynamic Range property.
- `0xD017` was already known as the live white-balance colour temperature.
- `0x5005` is `WhiteBalance` in the PTP standard itself (ISO 15740).
- `0x5015` is `Sharpness` in the PTP standard.

None of those were chosen to make the table work — they fall out of it. The signed/unsigned type
also agrees on all 23 rows, and every value has since been confirmed on hardware.

Setting names come from Fuji's own XML serializer, which writes the same struct out using names like
`ConversionProfile.PropertyGroup.DynamicRange`.

### The block is derivable from the struct

A debug routine in Fuji's `XRFC.dll`, `RAWSettingsClass::OutputLog`, prints every `RAWSettings` field
by name with its offset. The recipe fields occupy one contiguous run:

```text
0x1050 lShootCondition          0x1088 lWBShootCond
0x1054 lFileType                0x108c lWhiteBalance
0x1058 lImageSize               0x1090 lWBShift_R
0x105c lImageQuality            0x1094 lWBShift_B
0x1060 lExposureBias            0x1098 lWBColorTemp
0x1064 lDynamicRange            0x109c lHighLightTone
0x1068 lWideDynamicRange        0x10a0 lShadowTone
0x106c lFilmSimulation          0x10a4 lColorMode
0x1070 lBlackImageTone          0x10a8 lSharpness
0x1074 lMonochromaticColor_RG   0x10ac lNoiseReduction
0x1078 lGrainEffect             0x10b0 lClarity
0x107c lColorChromeEffect       0x10b4 lLMOMode
0x1080 lColorChromeBlue         0x10b8 lColorSpace
0x1084 lSmoothSkinEffect
```

The 23-property block corresponds to **`0x1058` through `0x10b8` in order, skipping `0x1060`
(`lExposureBias`) and `0x1088` (`lWBShootCond`)**. The field count agrees:
`(0x10b8 − 0x1058) / 4 + 1 = 25`, less the two skipped fields, gives 23.

Mapping that run onto the property codes reproduces the established meaning at every position —
`lDynamicRange` at `0xD190`, `lFilmSimulation` at `0xD192`, `lColorMode` at `0xD19F`, `lColorSpace`
at `0xD1A4`, and so on for 21 of the 23. Those 21 independent agreements fix the alignment, which
determines the identity of the two remaining positions:

- **Row 1 (`0xD18E` / `0xD1A5`) is `lImageSize`.**
- **Row 2 (`0xD18F` / `0xD018`) is `lImageQuality`.**

Two consequences follow:

- `lFileType` (`0x1054`) sits one field before the block starts, so it is **not sent to the camera**.
  X RAW STUDIO selects the output file type on the PC side.
- The two monochrome codes are Fuji's `lBlackImageTone` (`0xD193`) and `lMonochromaticColor_RG`
  (`0xD194`) — the warm/cool and magenta/green axes respectively.

Corroborating the row 1 result: `lImageSize` defaults to `7` in Fuji's code, and the X-H2 write test
read row 1 as `7` before moving it to `8`. `lImageSize` is also the field with seven capability
variants, which is what the fallback below exists to paper over.

## The fallback path

Three property codes — `0xD03A`, `0xD03B` and `0xD1A8` — are not settings. They exist only as a
recovery step for cameras that reject the composite value in row 1.

### Only row 1 has a fallback

The fallback is **not** a general retry applied to every setting. It exists for exactly one property.

| Function | Property accesses | Fallback checks |
|---|---|---|
| `SetCustomSettingParameter` | 51 | **2** — one per branch, both on row 1 |
| `GetCustomSettingParameter` | 26 | **1** — on row 1 |

Every other setting is written or read once, with no recovery. If one fails, it simply fails and the
error is recorded for that property; the function carries on to the next. Only row 1 gets a second
attempt in a different form.

This is settled, not an assumption. The writer is fully unrolled straight-line code — each property
is a fixed five-instruction block that builds the request, supplies the value from its struct offset,
sends it, and stores the result. Only the row 1 blocks have an `if` after them. Across the entire
2,052-function binary, `0xD03A`, `0xD03B` and `0xD1A8` appear **four times total**: twice in the live
write branch, once in the slot write branch, once in the read branch. Nothing else references them.

### The same fallback, implemented per destination

It is not two different mechanisms. It is the *same* recovery step, written once in the C1–C7 branch
and once in the live branch, because each destination has its own property codes.

Row 1 of the block carries a **composite value**. If writing it fails, the client looks that value up
in a fixed 27-entry table, which maps every value `1`–`27` to a **column** `1`–`9` and a **row**
`1`–`3`, and then sends those components separately.

```text
             col1 col2 col3 col4 col5 col6 col7 col8 col9
   row 1 :    22    9   17   16   14    7    8   15   23
   row 2 :    24    6   21   20   18    4    5   19   25
   row 3 :    26    3   13   12   10    1    2   11   27
```

The table is a genuine lookup, not a formula: values `1`–`9` occupy three columns, `10`–`21` four,
and `22`–`27` two, so the axes cannot be recovered arithmetically.

### It exists for C1–C7 too, but it is lossy and looks buggy

Two separate SDK functions are involved, and each has its own fallback. **Neither reads back to
verify a write** — Fuji's app never confirms a write by re-reading it.

| Function | Covers | Row 1 property | Its fallback |
|---|---|---|---|
| `SetCustomSettingParameter` | C1–C7 **and** live | `0xD18E` / `0xD1A5` | slot: `0xD1A8` = row only · live: `0xD03A` = col **and** `0xD03B` = row |
| `GetCustomSettingParameter` | **C1–C7 only** | `0xD18E` | reads `0xD1A8` and reconstructs |

The asymmetry is not that the live path lacks a read fallback. **There is no live read at all.** The
reader is unconditional and touches only the stored block — `0xD18C`, `0xD18D`, `0xD18E`–`0xD1A4`,
plus `0xD1A8`. It contains no live property codes whatsoever, and none of the branching the writer
has.

So Fuji's app can read a stored slot back, but never reads the camera's current shooting state
through this API. That is a limitation of their SDK surface, not of the camera: reading the live
codes directly with `GetDevicePropValue` works fine, and all 23 were confirmed readable on an X-H2.

**The slot write drops the column.** This is not a misreading: the decompiled code computes the
column index, uses it only to test whether the lookup succeeded, then never sends it. So the slot
fallback transmits one of the two components. The live fallback transmits both.

**The slot read reconstructs from the row alone.** Reading `0xD18E` and getting error `0x2C` makes
the client read `0xD1A8` instead, then rebuild a composite value by indexing the same 27-entry table
at `[value * 9]` — the first column of that row. That is consistent with the write side only ever
sending the row: the pair is designed to round-trip the row and assume column 1.

It also appears to be **off by one**. The value read from `0xD1A8` is a 1-based row (the write side
sends `row + 1`, and the read side validates `1..3`), but it is used as the multiplier directly:

| `0xD1A8` reads | Code indexes | Yields | Column 1 of that row is |
|---|---|---|---|
| `1` | `table[9]` | `24` | `22` |
| `2` | `table[18]` | `26` | `24` |
| `3` | `table[27]` | `0` — **past the end of the 27-entry table** | `26` |

`(value - 1) * 9` would yield `22`, `24`, `26` — the first column of rows 1, 2 and 3, which is
clearly the intent. As written, every row resolves one row too far and row 3 reads out of bounds.

**Do not copy this.** If you ever implement the slot fallback, send and reconstruct both components,
and index the table with `(value - 1) * 9`.

### When it applies

The fallback only runs when the camera rejects the composite value written to row 1. Whether that
happens depends on the body's `ImageSize` variant (see below).

**Confirmed not to apply on X-H2 (`Std3`):** the composite is accepted directly at `0xD1A5` and
`0xD18E` — a write test moved it from `7` to `8` — and none of `0xD03A`, `0xD03B` or `0xD1A8` appear
in that camera's `DeviceInfo` property list.

**Expected to apply on older bodies**, most likely those on the `Std2` variant. Untested; no body
has yet been observed triggering it.

If you are implementing a client:

- Write row 1 normally. If the camera accepts it, you are done and the fallback is irrelevant.
- If a camera rejects it, this is the recovery Fuji performs — but implement it from the corrected
  description above, not by copying their code: send **both** components on the slot path, and index
  the table with `(value - 1) * 9` on read.
- The trigger Fuji uses is SDK error `0x2C`, an internal Fuji result code rather than a PTP response.
  A third-party client cannot see that code; you will see whatever PTP error the camera returned, so
  key your own fallback on the write failing rather than on a specific value.

These three codes are referenced in exactly two places in the entire SDK — the two write branches and
the one read branch described above. Nothing else in Fuji's software touches them.

### Why it exists: older bodies use a different encoding

**INFERRED, but well supported.** Fuji ships a per-model capability table with X RAW STUDIO, and it
records which *variant* of each setting a given body uses. `ImageSize` has **seven** variants across
the 41 bodies listed — far more than any comparable field:

| ImageSize variant | Bodies |
|---|---|
| `Std1` = **false** | X-T2, X-Pro2, X100F, X-T20, X-E3 — not supported at all |
| `Std2` | X-H1, X-T3, X-T30, X-Pro3, X100V, X-T4, X-S10, X-E4, X-T30II, X-H2S, X-S20, X-M5 |
| `Std3` | X-H2, X-T5, X-T50, X100VI, X-E5 |
| `Std4` | X-T30III |
| `Ext1` / `Ext2` / `Ext3` | GFX bodies |

For comparison, `ImageQuality` has two variants and `FileType` three. **Only `ImageSize` is
fragmented enough to need a compatibility shim** — which is consistent with the fallback existing on
row 1 and nowhere else.

The picture that fits:

- The composite encoding belongs to the newer variants. An X-H2 is `Std3` and accepts it directly —
  confirmed by write test.
- A body on an older variant would reject that composite value, at which point the client decomposes
  it into two components and sends those instead.
- Consistently, the three fallback codes are not advertised by an X-H2 at all. A body that needs
  them would presumably expose them.

This is consistent with row 1 being `lImageSize`, established independently above from the struct
layout: `ImageSize` is the only field in the block whose encoding varies enough to explain a shim.

Still not confirmed: no enum or string table in any binary names what either axis enumerates, and no
older body has been tested to see the fallback actually fire.

## Open questions

- **What the two axes of the fallback table enumerate.** A 9-way and a 3-way axis are consistent
  with image size (aspect ratios × L/M/S), but nothing in the binaries names them.
- **The value tables behind the capability variants.** Fuji records which *variant* of each setting a
  body uses — `0xD192` Film Simulation has six — but no binary contains the value-to-meaning table
  for a variant other than the one X-Trans V uses. The property codes are known for every body; the
  correct values are known only for X-Trans V.
- **Which bodies actually need the fallback.** Older `Std2` bodies are the likely candidates; none
  has been tested.
- **Other camera bodies.** Everything here is one X-H2 on firmware 5.20.

## Settings this path does not carry

Fuji's profile format includes these, but the function never sends them to the camera:
`FileType`, `ExposureBias`, `WBShootCond`, `GrainEffectSize`, `HDR`, `DigitalTeleConv`,
`PortraitEnhancer`, `RotationAngle`, `Rating`.

`ExposureBias` and `WBShootCond` are skipped from inside the block's offset run; the rest sit outside
it entirely. `GrainEffectSize` is not dropped so much as folded in — Fuji combines it with
`GrainEffect` into the single composite value written to `0xD195`.

If you are looking for a property code for one of those, it is not part of this path.

Note that `BlackImageTone` **is** carried, as `0xD193`. An earlier revision of this document listed
it here in error.
