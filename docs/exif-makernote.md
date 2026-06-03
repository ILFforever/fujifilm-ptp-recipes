# Fujifilm EXIF MakerNote — Recipe Parameters

This document maps Fujifilm MakerNote EXIF tags to the recipe parameters described in
[properties.md](properties.md). It is useful when importing recipes from shot JPEGs rather than
reading them live over USB.

MakerNote tags and PTP recipe properties are completely separate encodings. Never use a raw EXIF
value directly as a PTP wire value — the scales and formats differ.

## 1. Standard MakerNote Fields

These appear in the Fujifilm MakerNote and are decoded by common EXIF libraries:

| MakerNote field | Example decoded value | Recipe parameter | PTP code |
|---|---|---|---|
| `Film Mode` | string — see lookup below | Film Simulation | `0xD192` |
| `White Balance` | `"Daylight"` | White Balance | `0xD199` |
| `White Balance Fine Tune` | `"R B"` space-separated ints | WB Shift R / B | `0xD19A` / `0xD19B` |
| `Color Saturation` | string or raw int — see lookups below | Color / film-sim variant | `0xD19F` / `0xD192` |
| `Sharpness` | string or raw int — see lookup below | Sharpness | `0xD1A0` |
| `Tone (Contrast)` | `"Normal"` | Legacy combined field — not used on X-H2; ignore | — |
| `Dynamic Range` | `"Standard"` | DR setting | `0xD190` |
| `Development Dynamic Range` | `400` | Actual DR value in use (100/200/400) | `0xD190` |
| `High ISO Noise Reduction` | string or raw int — see lookup below | High ISO NR | `0xD1A1` |

### WB Fine Tune encoding

Raw EXIF value = dial × 20. For example, R+2 B+2 reads as `"40 40"`.

Do not use these values directly as PTP wire values. `WB_SHIFT_RED (0xD19A)` and
`WB_SHIFT_BLUE (0xD19B)` take the dial click value (range −9..+9), not the ×20 EXIF scale.

### Film Simulation lookup (X-H2, fully verified)

Identify film sim from the `Film Mode` field first. For Monochrome/ACROS variants and Sepia,
`Film Mode` is absent — fall back to `Color Saturation`.

| Film simulation | EXIF `Film Mode` | PTP code | Notes |
|---|---|---|---|
| Provia/Standard | `"F0/Standard (Provia)"` | 1 | |
| Velvia/Vivid | `"F2/Fujichrome (Velvia)"` | 2 | |
| Astia/Soft | `"F1b/Studio Portrait Smooth Skin Tone (Astia)"` | 3 | |
| Pro Neg Hi | `"Pro Neg. Hi"` | 4 | |
| Pro Neg Std | `"Pro Neg. Std"` | 5 | |
| Monochrome | absent — use `Color Saturation: "None (B&W)"` | 6 | |
| Monochrome+Y | absent — use `Color Saturation: "B&W Yellow Filter"` | 7 | |
| Monochrome+R | absent — use `Color Saturation: "B&W Green Filter"` | 8 | ⚠️ library label is wrong — raw value is Red |
| Monochrome+G | absent — use `Color Saturation: "B&W Blue Filter"` | 9 | ⚠️ library label is wrong — raw value is Green |
| Sepia | absent — use `Color Saturation: Unknown (784)` | 10 | no Film Mode field written |
| Classic Chrome | `"Classic Chrome"` | 11 | |
| ACROS | absent — use `Color Saturation: Unknown (1280)` | 12 | |
| ACROS+R | absent — use `Color Saturation: Unknown (1281)` | 13 | |
| ACROS+Y | absent — use `Color Saturation: Unknown (1282)` | 14 | |
| ACROS+G | absent — use `Color Saturation: Unknown (1283)` | 15 | |
| Eterna | `"Eterna"` | 16 | |
| Classic Neg | `"Classic Negative"` | 17 | |
| Eterna Bleach Bypass | `"Bleach Bypass"` | 18 | |
| Nostalgic Neg | `"Nostalgic Neg"` | 19 | |
| Reala Ace | `Unknown (2816)` | 20 | not decoded by common EXIF libraries |

### Monochrome filter sub-lookup (`Color Saturation` field)

| Fuji filter | EXIF `Color Saturation` |
|---|---|
| STD (no filter) | `"None (B&W)"` |
| Yellow | `"B&W Yellow Filter"` |
| Red | `"B&W Green Filter"` ⚠️ label is wrong — this raw value is Red, not Green |
| Green | `"B&W Blue Filter"` ⚠️ label is wrong — this raw value is Green, not Blue |

Do not trust the string label for Red/Green Monochrome filters. Use the string as an opaque key
and map it via this table only.

### ACROS filter sub-lookup (`Color Saturation` field)

| Fuji filter | EXIF `Color Saturation` |
|---|---|
| ACROS STD | `Unknown (1280)` |
| ACROS+R | `Unknown (1281)` |
| ACROS+Y | `Unknown (1282)` |
| ACROS+G | `Unknown (1283)` |

ACROS variants appear as raw integers (no decoded label). No label confusion possible.

### White Balance lookup (X-H2, 11 isolation shots)

| WB mode | EXIF `White Balance` | PTP code |
|---|---|---|
| Auto | `"Auto"` | `0x0002` |
| Auto White Priority | `Unknown (1)` | `0x8020` |
| Ambience Priority | `Unknown (2)` | `0x8021` |
| Daylight | `"Daylight"` | `0x0004` |
| Shade | `"Cloudy"` ← library maps to standard EXIF label | `0x8006` |
| Incandescent | `"Incandescence"` | `0x0006` |
| Underwater | `Unknown (1536)` | `0x0008` |
| Fluorescent 1 | `"Daylight Fluorescent"` | `0x8001` |
| Fluorescent 2 | `"Day White Fluorescent"` | `0x8002` |
| Fluorescent 3 | `"White Fluorescent"` | `0x8003` |
| Color Temp (Kelvin) | `"Kelvin"` | `0x8007` |

When `White Balance == "Kelvin"`, a separate `Color Temperature` EXIF field contains the actual
Kelvin value (e.g. `4700`).

### Color Saturation (dial) lookup (Pro Neg Hi, X-H2 — 9 isolation shots)

| Dial | `Color Saturation` EXIF value |
|---:|---|
| +4 | 224 |
| +3 | 192 |
| +2 | `"High"` |
| +1 | `"Medium High"` |
| 0 | `"Normal"` |
| −1 | `"Medium Low"` |
| −2 | 1024 |
| −3 | 1216 |
| −4 | 1248 |

Common EXIF libraries decode known values to strings and return raw integers for others. Use this
table as a direct lookup — map each string or integer to its dial position, then encode for PTP
as `dial × 10` (int16LE) per [properties.md](properties.md).

### High ISO NR lookup (X-H2 — 9 isolation shots)

| Dial | `High ISO Noise Reduction` EXIF value |
|---:|---|
| +4 | `Unknown (480)` |
| +3 | `Unknown (448)` |
| +2 | `"Strong"` |
| +1 | `Unknown (384)` |
| 0 | `"Normal"` |
| −1 | `Unknown (640)` |
| −2 | `"Weak"` |
| −3 | `Unknown (704)` |
| −4 | `Unknown (736)` |

Map each value to its dial position, then encode for PTP using the non-linear wire lookup in
[properties.md](properties.md). Do not use the EXIF value directly as a PTP wire value.

### Sharpness lookup (X-H2 — 9 isolation shots)

| Dial | `Sharpness` (MakerNote) EXIF value |
|---:|---|
| +4 | `Unknown (6)` |
| +3 | `"Hardest"` |
| +2 | `"Hard"` |
| +1 | `"Medium Hard"` |
| 0 | `"Normal"` |
| −1 | `"Medium Soft"` |
| −2 | `"Soft"` |
| −3 | `"Softest"` |
| −4 | `Unknown (0)` |

Map to dial position, then encode for PTP as `dial × 10` (int16LE).

## 2. MakerNote Hex Tags — Confirmed Mappings

These tags are not decoded by all EXIF libraries. Values confirmed from X-H2 firmware 5.20
isolation shots, varying one parameter group at a time.

| EXIF hex tag | Parameter | Encoding |
|---|---|---|
| `0x100f` | **Clarity** | raw = dial × 1000; +5 → 5000, 0 → 0, −5 → −5000. Dial range −5 to +5. |
| `0x1040` | **Shadow Tone** | raw = dial × (−16); +2.0 → −32, 0 → 0, −2.0 → +32. Dial range −2.0 to +2.0 in 0.5 steps. |
| `0x1041` | **Highlight Tone** | raw = dial × (−16); same encoding as Shadow Tone. |
| `0x1047` | **Grain Effect (strength)** | 0=Off · 32=Weak · 64=Strong |
| `0x104c` | **Grain Size** | 0=Off · 16=Small · 32=Large |
| `0x1048` | **Color Chrome Effect** | 0=Off · 32=Weak · 64=Strong |
| `0x104e` | **Color Chrome FX Blue** | 0=Off · 32=Weak · 64=Strong |
| `0x1049` | **Monochrome WC** (Warm/Cool) | signed int8 stored as uint8; dial value direct: +18 → 18, −18 → 238. Range −18 to +18. |
| `0x104a` | **Smooth Skin** | 0=Off · 32=Weak · 64=Strong |
| `0x104b` | **Monochrome MG** (Magenta/Green) | signed int8 stored as uint8; same encoding as `0x1049`. |

### Encoding notes

**Highlight and Shadow Tone EXIF vs. PTP:** The EXIF encoding (`raw = dial × −16`) is the inverse
of the PTP encoding (`wire = dial × 10`, int16LE). Do not mix them up.

**Sharpness and Color in EXIF are absolute, not dial-relative.** EXIF reports relative labels like
`"Normal"` and `"High"` because the film simulation's built-in offset is baked in. You cannot
recover the exact dial position from these fields without a per-simulation offset table. Prefer the
hex tag lookups above where available.

**WB Fine Tune scale:** EXIF stores R and B as separate integers, scale = ×20. The PTP wire uses
dial clicks (range −9..+9, 1:1 no scaling). For example: EXIF `"40 40"` → R+2 B+2 → PTP R=2 B=2.

**Grain:** EXIF uses two separate tags (`0x1047` strength, `0x104c` size). PTP uses one combined
`GRAIN_EFFECT (0xD195)` value. Mapping:

| EXIF strength | EXIF size | PTP wire |
|---|---|---|
| Off (0) | Off (0) | 1 |
| Weak (32) | Small (16) | 2 |
| Strong (64) | Small (16) | 3 |
| Weak (32) | Large (32) | 4 |
| Strong (64) | Large (32) | 5 |

If strength is non-zero but size is zero (invalid camera state), treat as Off (write PTP wire `1`).

## 3. Unknown Tags

| EXIF hex tag | Observed values | Notes |
|---|---|---|
| `0x1045` | 0 in most shots; 1 in some | Purpose unclear |
| `0x1046` | 1 in some shots, 0 in others | Purpose unclear |
| `0x104d` | 0 in all tested shots | Unknown |
| `0x1050` | 0 in all tested shots | Unknown |

## 4. Key Differences: EXIF vs. PTP

| Property | EXIF encoding | PTP wire encoding |
|---|---|---|
| Shadow / Highlight Tone | `dial × −16` | `dial × 10` (int16LE) |
| Clarity | `dial × 1000` | `dial × 10` (int16LE) |
| Color / Sharpness | absolute scale including sim offset | `dial × 10` (int16LE) |
| Mono WC / MG | signed int8 as uint8, direct dial | `dial × 10` (int16LE) |
| WB Shift R / B | `dial × 20` | direct dial (int16LE, range −9..+9) |
| Grain | two tags (strength + size) | one combined property `0xD195` |
| High ISO NR | non-linear string/int lookup | separate non-linear wire table |
