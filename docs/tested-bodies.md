# Tested Bodies

Please add body reports with exact camera model, firmware, USB mode, and result.

| Body | Firmware | USB mode | Read C1-C7 | Write props | Write names | Notes |
|---|---:|---|---|---|---|---|
| X-H2 | 5.20 | USB RAW Conv. / Backup Restore | OK | OK | OK | 0 ms inter-property delay worked in app testing. DR Priority `0xD191` confirmed: Off=0, Weak=1, Strong=2, Auto=32768. Active priority rejects writes to DR `0xD190` **and** Highlight `0xD19D` / Shadow `0xD19E` with `0x201C`; all three become writable once priority is Off, and `0xD190` reads `65535` while priority is active. All 14 White Balance modes confirmed by write, read-back and restore, including Custom 1-3 (`0x8008`-`0x800A`) and the Auto-priority pair (`0x8020`/`0x8021`). Camera name entry appears capped at 25 characters. |
| X-T5 | 4.20 | USB RAW Conv. / Backup Restore | OK | OK | OK | Confirmed working in app testing. |
| X-Pro3 | 2.00 | USB RAW Conv. / Backup Restore | Fails so far | Fails so far | Fails so far | Does not work with the current protocol path so far. Needs more diagnosis. |

## Current shooting state (C0)

The table above covers **C1–C7 slots only**. Applying a recipe to the camera's current shooting
state uses different property codes and has only been confirmed on an X-H2 (firmware 5.20). It is
expected to fail on other generations — see [protocol status](protocol-status.md).

C0 reports from any other body are especially wanted.

## Untested Families

- X-Trans III bodies are currently untested.
- Older bodies may expose different USB modes, slot counts, or supported device properties.

## Report Template

```text
Body:
Firmware:
USB mode:
Host OS:
Library/app/tool used:

Read C1-C7:
Write properties:
Write names:
Inter-property delay tested:

Failures:
Notes:
```
