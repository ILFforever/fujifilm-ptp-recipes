# Current shooting state (C0): applying a recipe without a slot

**TL;DR** — The camera's current shooting state, what you get in P/A/S/M, is often called "C0".

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

**There is no bulk live read.** Fuji's SDK has no operation that reads the current shooting state as
a block. Read each live code individually with `GetDevicePropValue` (`0x1015`).

**Nine properties are signed.** Decode them as `INT16`. Reading them as unsigned turns Highlight
Tone `-10` into `65526` and WB Shift `-2` into `65534`.

**Some properties require a prerequisite property to be set first:**

| Property | Requires |
|---|---|
| Color Temperature (`0xD017`) | White Balance (`0x5005`) set to `0x8007` |
| Mono WC (`0xD104`), Mono MG (`0xD031`) | a monochrome film simulation active |
| Dynamic Range (`0xD007`), Highlight Tone (`0xD320`), Shadow Tone (`0xD321`) | D Range Priority (`0xD02E`) set to Off (`0`) |

D Range Priority is the widest of these: while it is anything but Off the camera owns all three of
those properties and refuses every write. Dynamic Range also reads `65535` in that state rather than
a real value. Both confirmed on an X-H2 by running the same writes with priority Auto and then Off.

Writing the property before its prerequisite is set returns `InvalidDevicePropValue` (`0x201C`),
which is easy to mistake for a wrong property code. Distinguish the two:

- `0x201C` — the property exists; the **value** is invalid.
- `0x200A` — the property does not exist on this body.

**Restore order matters.** When reverting gated properties, restore the gated property first, while
its prerequisite is still set. For example, restore Colour Temperature (`0xD017`) while White Balance
is still `0x8007`, then revert White Balance last. Reverting White Balance first makes the temperature
unwritable (`0` is not a valid Kelvin value), and the camera keeps whatever you last set. The same
applies to Mono WC/MG under a monochrome film simulation.

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
at `[(value - 1) * 9]` — the first column of that row. That is consistent with the write side only
ever sending the row: the pair is designed to round-trip the row and assume column 1.

The indexing is correct. Reading `1`, `2`, `3` from `0xD1A8` yields `22`, `24` and `26` — column 1 of
rows 1, 2 and 3 — and the row is validated as `1..3` before use.

> This is worth stating explicitly because the arithmetic is easy to misread in a decompiler. The
> machine code at `0x180004460` in `XGFXAPI.dll` is:
>
> ```asm
> 48 8d 14 c9            lea  rdx, [rcx+rcx*8]        ; rdx = row * 9
> 48 8d 05 93 42 04 00   lea  rax, [rip+0x44293]      ; -> table at 0x180048700
> 8b 44 90 dc            mov  eax, [rax+rdx*4-0x24]   ; -0x24 = -9 ints
> ```
>
> The `-0x24` displacement makes the effective address `table + (row - 1) * 9 * 4`. A decompiler may
> fold that displacement into a spurious base symbol and render the expression as `table[value * 9]`,
> which looks like an off-by-one and an out-of-bounds read on row 3. It is neither.

**If you implement the slot fallback**, the one thing not to copy is the dropped column: send and
reconstruct both components rather than assuming column 1.

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
- If a camera rejects it, this is the recovery Fuji performs. Their table indexing is correct and can
  be followed as-is (`(value - 1) * 9` on read); the one thing to improve on is sending **both**
  components on the slot path rather than the row alone.
- The trigger Fuji uses is SDK error `0x2C`, an internal Fuji result code rather than a PTP response.
  A third-party client cannot see that code; you will see whatever PTP error the camera returned, so
  key your own fallback on the write failing rather than on a specific value.

These three codes are referenced exactly four times in the entire SDK — twice in the live write
branch, once in the slot write branch, once in the read branch. Nothing else in Fuji's software
touches them.

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

Both axes are now identified. A wide-string label table in `XRFC.dll` names all 27 values as
`<size><aspect>` — `L3x2`, `M4x3`, `S16x9` and so on — which resolves the table's rows to image size
(L/M/S) and its columns to aspect ratio (3:4, 1:1, 7:6, 5:4, 4:3, 3:2, 16:9, 65:24, 17:6). The
derivation is in
[xrfc-value-tables.md](reverse-engineering/xrfc-value-tables.md#62-the-fallback-table-decoded).

Still not confirmed: no older body has been tested to see the fallback actually fire.

## Open questions

- **Which bodies actually need the fallback.** Older `Std2` bodies are the likely candidates; none
  has been tested.
- **Whether the values a newer body uses are accepted by an older one.** Fuji's own per-generation
  value tables have been recovered — see
  [xrfc-value-tables.md](reverse-engineering/xrfc-value-tables.md) — but they describe what Fuji's
  client considers legal, not what camera firmware accepts. No non-X-Trans-V body has been tested
  against them.
- **Other camera bodies.** Everything hardware-verified here is one X-H2 on firmware 5.20.

## Settings this path does not carry

Fuji's profile format includes these, but the function never sends them to the camera:
`FileType`, `ExposureBias`, `WBShootCond`, `GrainEffectSize`, `HDR`, `DigitalTeleConv`,
`PortraitEnhancer`, `RotationAngle`, `Rating`.

`ExposureBias` and `WBShootCond` are skipped from inside the block's offset run; the rest sit outside
it entirely. `GrainEffectSize` is not dropped so much as folded in — the builder combines it with
`GrainEffect` into the single composite written to `0xD195`: Off → `1` regardless of size, then
weak/strong × small/large → `2`, `3`, `4`, `5`.

Twenty-one of the 23 fields are copied verbatim, so for those the stored value is the wire value. The
two exceptions are that grain composite and `0xD18F` Image Quality, which is conditionally remapped
(`2→4`, `3→5`, `6→7`) — see
[xrfc-value-tables.md](reverse-engineering/xrfc-value-tables.md#image-quality-is-remapped-before-it-reaches-the-wire).

If you are looking for a property code for one of those, it is not part of this path.

Note that `BlackImageTone` **is** carried, as `0xD193`. An earlier revision of this document listed
it here in error.
