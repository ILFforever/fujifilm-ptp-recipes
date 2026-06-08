# Recipe Properties

All known recipe settings are read or written after selecting a slot with `0xD18C`.

The known recipe block spans:

```text
0xD18E..0xD1A5
```

Known mapped properties:

| Hex | Dec | Name | Encoding | Wire default | Display meaning |
|---|---:|---|---|---|---|
| `0xD190` | 53648 | Dynamic Range | `uint16LE` | 100 | DR Auto/100/200/400 |
| `0xD191` | 53649 | Dynamic Range Priority | `uint16LE` | 0 | Off/Weak/Strong/Auto |
| `0xD192` | 53650 | Film Simulation | `uint16LE` | 1 (Provia) | Film simulation enum |
| `0xD193` | 53651 | Mono WC | `int16LE` | 0 | Warm/Cool monochrome color, dial×10 |
| `0xD194` | 53652 | Mono MG | `int16LE` | 0 | Magenta/Green monochrome color, dial×10 |
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

Unmapped but in the observed read range:

```text
0xD18E, 0xD18F, 0xD1A3, 0xD1A4, 0xD1A5
```

Log these values when developing. They may be unused, body-specific, or related to settings not
yet mapped.

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

Dynamic Range Priority overrides manual Dynamic Range. Confirmed behavior on X-H2 firmware 5.20:

- Writing `0xD191` returns `0x2001` and reads back the selected priority value.
- Writing `0xD190` while `0xD191` is Weak/Strong/Auto returns `0x201C`.
- Reading `0xD190` after the rejected write returns the previous DR value.
- Reading `0xD191` after the rejected DR write shows priority remains active.

Writer rule: if `0xD191 != 0`, omit `0xD190` from the write set. If priority is Off, `0xD190`
may be written normally as `0`, `100`, `200`, or `400`.

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

When White Balance is Color Temperature (`0x8007`), write Kelvin to `0xD19C`.

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
