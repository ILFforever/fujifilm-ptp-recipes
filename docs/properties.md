# Recipe Properties

All known recipe settings are read or written after selecting a slot with `0xD18C`.

The known recipe block spans:

```text
0xD18E..0xD1A4
```

That is 23 properties. Do not extend a **write** past `0xD1A4`: `0xD1A5` belongs to the live / C0
block ([current-shooting-state.md](current-shooting-state.md)), so writing it as if it were slot data
changes the camera's current shooting state instead. Reading it is harmless.

Known mapped properties:

| Hex | Dec | Name | Encoding | Wire default | Display meaning |
|---|---:|---|---|---|---|
| `0xD190` | 53648 | Dynamic Range | `uint16LE` | 100 | DR Auto/100/200/400 |
| `0xD191` | 53649 | Dynamic Range Priority | `uint16LE` | 0 | Off/Weak/Strong/Auto |
| `0xD192` | 53650 | Film Simulation | `uint16LE` | 1 (Provia) | Film simulation enum |
| `0xD193` | 53651 | Mono WC | `int16LE` | 0 | Warm/Cool monochrome color, dial×10, range −180..180 |
| `0xD194` | 53652 | Mono MG | `int16LE` | 0 | Magenta/Green monochrome color, dial×10, range −180..180 |
| `0xD195` | 53653 | Grain Effect | `uint16LE` | 1 | Combined grain strength and size |
| `0xD196` | 53654 | Color Chrome | `uint16LE` | 1 (Off) | Off/Weak/Strong |
| `0xD197` | 53655 | Color Chrome FX Blue | `uint16LE` | 1 (Off) | Off/Weak/Strong |
| `0xD198` | 53656 | Smooth Skin | `uint16LE` | 1 (Off) | Off/Weak/Strong |
| `0xD199` | 53657 | White Balance | `uint16LE` | 2 (Auto) | WB mode enum |
| `0xD19A` | 53658 | WB Shift Red | `int16LE` | 0 | Direct signed dial, range −9..+9 |
| `0xD19B` | 53659 | WB Shift Blue | `int16LE` | 0 | Direct signed dial, range −9..+9 |
| `0xD19C` | 53660 | Color Temperature | `uint16LE` | 5600 | Kelvin |
| `0xD19D` | 53661 | Highlight Tone | `int16LE` | 0 | Dial×10 |
| `0xD19E` | 53662 | Shadow Tone | `int16LE` | 0 | Dial×10 |
| `0xD19F` | 53663 | Color | `int16LE` | 0 | Dial×10 |
| `0xD1A0` | 53664 | Sharpness | `int16LE` | 0 | Dial×10 |
| `0xD1A1` | 53665 | High ISO NR | `uint16LE` | 8192 | Non-linear lookup |
| `0xD1A2` | 53666 | Clarity | `int16LE` | 0 | Dial×10 |

### Remaining codes in the block

The block also carries `0xD18E`, `0xD18F`, `0xD1A3` and `0xD1A4`. These are not film-simulation
settings. Working implementations read and log them but never write them, and their value encodings
are unmapped.

Provisional identifications for all four, derived from static analysis and **not hardware-tested**,
are in [xrfc-value-tables.md](reverse-engineering/xrfc-value-tables.md).

## Film Simulation (`0xD192`)

| Code | Label | Monochrome-like |
|---:|---|---|
| 1 | Provia / Standard | no |
| 2 | Velvia / Vivid | no |
| 3 | Astia / Soft | no |
| 4 | Pro Neg Hi | no |
| 5 | Pro Neg Std | no |
| 6 | Monochrome | yes |
| 7 | Monochrome + Y | yes |
| 8 | Monochrome + R | yes |
| 9 | Monochrome + G | yes |
| 10 | Sepia | yes |
| 11 | Classic Chrome | no |
| 12 | Acros | yes |
| 13 | Acros + Y | yes |
| 14 | Acros + R | yes |
| 15 | Acros + G | yes |
| 16 | Eterna | no |
| 17 | Classic Neg | no |
| 18 | Eterna Bleach Bypass | no |
| 19 | Nostalgic Neg | no |
| 20 | Reala Ace | no |

When writing a monochrome-like simulation, skip color-only settings.

## Dynamic Range (`0xD190`)

| Wire | Meaning |
|---:|---|
| 0 | DR Auto |
| 100 | DR100% |
| 200 | DR200% |
| 400 | DR400% |

When Dynamic Range Priority (`0xD191`) is Weak, Strong, or Auto, do not write `0xD190`. The
camera rejects direct Dynamic Range writes while priority is active.

## Dynamic Range Priority (`0xD191`)

| Wire | Payload | Meaning |
|---:|---|---|
| 0 | `00 00` | Off |
| 1 | `01 00` | Weak |
| 2 | `02 00` | Strong |
| 32768 | `00 80` | Auto |

Dynamic Range Priority takes over the tone curve. While it is active the camera owns three
properties and refuses writes to all of them. Confirmed on X-H2 firmware 5.20:

- Writing `0xD191` returns `0x2001` and reads back the selected priority value.
- While `0xD191` is Weak/Strong/Auto, writes to **`0xD190` Dynamic Range, `0xD19D` Highlight Tone
  and `0xD19E` Shadow Tone** are all rejected with `0x201C` — including values that are legal for
  this body.
- Setting `0xD191` to Off makes all three writable again. Verified by a controlled pair of runs:
  with priority on Auto the three rejected; with priority Off, the same values were accepted.
- Reading `0xD190` while priority is active returns `65535` (`0xFFFF`), a placeholder rather than a
  real setting. With priority Off it reads the true value.

The rejection is `InvalidDevicePropValue`, the same response an out-of-range value produces, so a
locked property is easy to mistake for an unsupported one. Check `0xD191` before concluding that a
tone dial is missing.

Writer rule: if `0xD191 != 0`, omit `0xD190`, `0xD19D` and `0xD19E` from the write set — or write
`0xD191 = 0` first, then the three, then restore priority. If priority is Off, `0xD190` may be
written normally as `0`, `100`, `200`, or `400`.

## White Balance (`0xD199`)

| Code | Hex | Label |
|---:|---|---|
| 2 | `0x0002` | Auto |
| 32800 | `0x8020` | Auto White Priority |
| 32801 | `0x8021` | Ambience Priority |
| 4 | `0x0004` | Daylight |
| 6 | `0x0006` | Incandescent |
| 8 | `0x0008` | Underwater |
| 32769 | `0x8001` | Fluorescent 1 |
| 32770 | `0x8002` | Fluorescent 2 |
| 32771 | `0x8003` | Fluorescent 3 |
| 32774 | `0x8006` | Shade |
| 32775 | `0x8007` | Color Temperature |
| 32776 | `0x8008` | Custom 1 |
| 32777 | `0x8009` | Custom 2 |
| 32778 | `0x800A` | Custom 3 |

When White Balance is Color Temperature (`0x8007`), write Kelvin to `0xD19C`.

All fourteen modes are confirmed on X-H2 (firmware 5.20). Each was written in turn, read back
unchanged, and the camera's original mode restored afterwards.

Custom 1-3 recall a white balance the photographer has measured and stored on the camera. A body
with an empty custom slot may reject the mode it otherwise supports, so treat a rejection there as
inconclusive rather than as evidence the mode is missing.

## Direct Signed Dials

WB Shift Red and WB Shift Blue use direct signed values with no scaling.

Observed camera dial range: `-9..+9`.

| Dial | Wire |
|---:|---:|
| -9 | -9 |
| -1 | -1 |
| 0 | 0 |
| +1 | 1 |
| +9 | 9 |

Encoding: `int16LE`.

Validate or clamp to `-9..+9` before writing. Do not scale these — they are the only two signed
dial properties that use 1:1 (not ×10) encoding.

### WB shift is not stored per preset on X-T3 and older

**NOT VERIFIED BY THIS PROJECT.** Reported behaviour, corroborated by Fuji's own capability data.
Nobody has yet measured it over PTP. It is documented here because the failure mode is silent and
destructive, so an implementer should know before writing these properties.

From the X-Pro3 onward, a white-balance shift is saved with each C1–C7 preset. On **X-T3, X-T30,
X-H1 and X-Trans III bodies it is not**: the camera stores one shift *per white-balance type*,
globally. Set Auto WB with R+2/B−4 in C1 and every other preset using Auto WB inherits that shift.
No firmware update ever changed this for the X-T3 or X-T30.

Why this matters more than an ordinary unsupported property:

- The write is expected to **succeed**. It returns `0x2001`; the value lands. It simply lands on the
  white-balance type rather than on the preset.
- **Read-back cannot detect it.** Select the slot, read `0xD19A`, and the value you wrote comes
  back — because the shift genuinely is active for that WB type. The usual "write then read back to
  confirm" check passes while other presets have been quietly changed.

The `CustomSetting` element in `XRFC.DAT` splits on exactly this boundary — absent on every
configuration below the X-Pro3, true from the X-Pro3 onward. That is independent corroboration from
Fuji's own data, though what the flag *means* is inferred from the correlation rather than traced
through the binary. See
[xrfc-capability-database.md](reverse-engineering/xrfc-capability-database.md#customsetting-tracks-per-preset-wb-shift).

**Writer guidance.** On a body below the X-Pro3, either omit `0xD19A`/`0xD19B`, or warn that writing
them changes every preset sharing that white-balance mode. The workaround photographers use is to
give each preset a different white-balance type, which makes the per-type storage behave like
per-preset storage.

Sources: [Fuji X Weekly — My White Balance Shift Solution](https://fujixweekly.com/2019/11/06/my-white-balance-shift-solution/),
[Fujifilm White Balance Shift: What It Is + How To Use It](https://fujixweekly.com/2020/08/19/fujifilm-white-balance-shift-what-it-is-how-to-use-it/),
[FujiX-Forum thread](https://www.fujix-forum.com/threads/white-balance-shift-for-custom-settings-x-t3.153075/).

## Scaled Signed Dials

These properties use `dial * 10`:

- Mono WC
- Mono MG
- Highlight Tone
- Shadow Tone
- Color
- Sharpness
- Clarity

Examples:

| Dial | Wire | Little-endian int16 payload |
|---:|---:|---|
| -2 | -20 | `EC FF` |
| -1.5 | -15 | `F1 FF` |
| -1 | -10 | `F6 FF` |
| 0 | 0 | `00 00` |
| +1 | 10 | `0A 00` |
| +1.5 | 15 | `0F 00` |
| +2 | 20 | `14 00` |

The signed default/unset sentinel `-32768` may appear. Treat it as default/unknown rather than a
real dial value.

## Monochrome Toning (`0xD193` / `0xD194`)

Confirmed on an X-H2 (firmware 5.20) by setting the camera by hand and reading back, then by a write
sweep.

| | |
|---|---|
| `0xD193` | Warm / Cool |
| `0xD194` | Magenta / Green |
| Encoding | `int16LE`, dial × 10 |
| Dial range | −18 … +18, so **−180 … +180** on the wire |
| Legal values | **multiples of 10 only** |
| Storage | per slot |

Setting the camera to warm/cool `+5` and magenta/green `−3` reads back as `0xD193 = 50` and
`0xD194 = -30`, which fixes both the axis assignment and the scale.

**The camera accepts only exact dial positions.** A write sweep on both codes gave identical
results — `0`, `10`, `20`, `50`, `90`, `100` and `-90` accepted; `1`, `2`, `5`, `9` and `-9` all
rejected with `InvalidDevicePropValue` (`0x201C`). Round any dial to a whole number before scaling.

Both are refused under a colour film simulation, the mirror of the colour-only rule above. Set the
film simulation to a monochrome one first, or omit them.

### The `BlackImageTone` name is a feature, not an axis

`0xD193`'s field name in Fuji's own structures is `lBlackImageTone`, and the capability database
marks a `BlackImageTone` flag supported on only four configurations — X-T3, X-T30 and GFX100
firmware 1–2. That is not a statement about the property code.

BlackImageTone was the **single-axis** black-and-white toning those 2018–2019 bodies had. The
two-axis Warm/Cool + Magenta/Green control succeeded it, and `0xD193` was carried forward to be the
warm/cool axis while keeping its original field name. So on an X-H2 the flag is correctly false
while the code works normally.

The general trap, worth stating because it will catch other properties: **capability flags name
features, the block names property codes, and a code outlives the feature it was introduced for.**
A false flag is not evidence that a code is unsupported.

## Off / Weak / Strong Properties

Used by:

- Color Chrome
- Color Chrome FX Blue
- Smooth Skin

| Wire | Meaning |
|---:|---|
| 1 | Off |
| 2 | Weak |
| 3 | Strong |

## Grain Effect (`0xD195`)

| Wire | Meaning | Write status |
|---:|---|---|
| 1 | Off | write this for Off |
| 2 | Weak Small | OK |
| 3 | Strong Small | OK |
| 4 | Weak Large | OK |
| 5 | Strong Large | OK |
| 6 | Off/default read-back | do not write; rejected in tests |

Important: a camera may read `6` for Off on default slots. Write `1` for Off.

## High ISO NR (`0xD1A1`)

High ISO NR is not linear.

| Wire | Dial |
|---:|---:|
| 32768 | -4 |
| 28672 | -3 |
| 16384 | -2 |
| 12288 | -1 |
| 8192 | 0 |
| 4096 | +1 |
| 0 | +2 |
| 24576 | +3 |
| 20480 | +4 |

Do not write the display dial directly. For example, dial `0` should write wire `8192`, not wire
`0`.

## Suggested Write Order

1. Slot selector `0xD18C`
2. `GET_DEVICE_INFO`
3. Film Simulation `0xD192`
4. Dynamic Range Priority `0xD191`
5. Dynamic Range `0xD190`, only when priority is Off
6. Effect properties
7. White Balance mode and dependent WB properties
8. Tone/color/detail properties
9. Preset name `0xD18D`

The exact order after Film Simulation is less critical, but writing Film Simulation first avoids
range/dependency problems.

