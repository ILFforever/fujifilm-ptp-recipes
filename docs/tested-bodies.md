# Tested Bodies

Please add body reports with exact camera model, firmware, USB mode, and result.

| Body | Firmware | USB mode | Read C1-C7 | Write props | Write names | Notes |
|---|---:|---|---|---|---|---|
| X-H2 | 5.20 | USB RAW Conv. / Backup Restore | OK | OK | OK | 0 ms inter-property delay worked in app testing. Camera name entry appears capped at 25 characters. |
| X-T5 | 4.20 | USB RAW Conv. / Backup Restore | OK | OK | OK | Confirmed working in app testing. |
| X-Pro3 | 2.00 | USB RAW Conv. / Backup Restore | Fails so far | Fails so far | Fails so far | Does not work with the current protocol path so far. Needs more diagnosis. |

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
