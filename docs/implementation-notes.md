# Implementation Notes

These notes are for developers building independent readers/writers.

## Minimal Reader Architecture

You need:

- USB device discovery
- permission / open-device flow
- PTP interface claim
- bulk OUT sender
- bulk IN receiver
- transaction id allocator
- PTP command builder
- PTP data-out builder
- PTP response parser
- PTP string parser
- value decoder for known properties

## Minimal Writer Architecture

In addition to reader pieces, you need:

- recipe model
- display-to-wire value mapper
- write-order planner
- color-only suppression logic
- color-temperature suppression logic
- per-property error reporting
- preset-name sanitizer
- slot backup / restore workflow

## Defensive Checks

Before writing:

1. Confirm USB vendor id `0x04CB`.
2. Confirm PTP interface class `0x06`.
3. Open session.
4. Read DeviceInfo.
5. Confirm `0xD18C` exists in supported properties.
6. Confirm the target slot number is in the range you intend to write.
7. Sanitize preset name.
8. Convert all display values to raw PTP wire values.
9. Validate each display value against the camera dial limits before writing.

## Recommended Error Reporting

Report failures by property code, not just as a total.

Useful fields:

- slot
- property code
- display name
- payload bytes
- response code
- transaction id
- camera model
- firmware
- delay used

## Common Bugs

### Writing display dials directly

Wrong:

```text
Color +2 -> write integer 2
```

Correct:

```text
Color +2 -> write integer 20 as int16LE
```

### Writing High ISO NR linearly

Wrong:

```text
High ISO NR 0 -> write 0
```

Correct:

```text
High ISO NR 0 -> write 8192
```

### Writing Grain Off as 6

Wrong:

```text
Grain Off -> write 6
```

Correct:

```text
Grain Off -> write 1
```

### Writing color-only props for monochrome simulations

Suppress color-only writes when the film simulation is monochrome-like.

### Trusting camera text UI for PTP name writes

The camera UI and PTP name write path do not necessarily accept the same practical set. Use the
safe rules in [name-rules.md](name-rules.md).

## Body Compatibility Strategy

For each new camera body:

1. Record body and firmware.
2. Confirm USB mode.
3. Read DeviceInfo.
4. Confirm `0xD18C`.
5. Read all slots.
6. Write only a preset name to one sacrificial slot.
7. Read back and compare.
8. Write one simple property.
9. Restore original slot.
10. Only then run all-slot write benches.

## Suggested Test Names

Use targeted names:

| Case | Purpose |
|---|---|
| `NAMEBENCH-BASIC` | Basic ASCII |
| 25-character ASCII string | Length boundary |
| punctuation group A | Allowed punctuation |
| punctuation group B | Allowed punctuation |
| accented text | Accent folding |
| smart apostrophe | Apostrophe folding |
| emoji in text | Unsupported character collapse |

## Suggested Property Bench

Use a simple color recipe with known values:

- Film Simulation: Velvia
- Dynamic Range: DR100
- Grain: Off, write `1`
- Color Chrome: Off
- Color Chrome FX Blue: Off
- Smooth Skin: Off
- WB: Auto
- WB Shift R: +1
- WB Shift B: 0
- Highlight: +1 -> wire `10`
- Shadow: 0 -> wire `0`
- Color: +2 -> wire `20`
- Sharpness: 0 -> wire `0`
- High ISO NR: 0 -> wire `8192`
- Clarity: 0 -> wire `0`

## Open Questions

- Why X-Pro3 fails with the current path.
- Whether X-Trans III bodies expose the same slot-selector property.
- Whether older bodies have fewer custom slots.
- Whether any body accepts a wider preset-name character set over PTP.
- Meaning of unmapped properties in `0xD18E..0xD1A5`.
