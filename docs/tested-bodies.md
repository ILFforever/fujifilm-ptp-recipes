# Tested Bodies

Please add body reports with exact camera model, firmware, USB mode, and result.

| Body | Firmware | USB mode | Read C1-C7 | Write props | Write names | Notes |
|---|---:|---|---|---|---|---|
| X-H2 | 5.20 | USB RAW Conv. / Backup Restore | OK | OK | OK | 0 ms inter-property delay worked in app testing. DR Priority `0xD191` confirmed: Off=0, Weak=1, Strong=2, Auto=32768. Active priority rejects writes to DR `0xD190` **and** Highlight `0xD19D` / Shadow `0xD19E` with `0x201C`; all three become writable once priority is Off, and `0xD190` reads `65535` while priority is active. All 14 White Balance modes confirmed by write, read-back and restore, including Custom 1-3 (`0x8008`-`0x800A`) and the Auto-priority pair (`0x8020`/`0x8021`). Camera name entry appears capped at 25 characters. Monochrome toning confirmed: `0xD193` is Warm/Cool, `0xD194` is Magenta/Green, dial × 10, range −180..180, **multiples of 10 only** (`1`/`2`/`5`/`9`/`-9` all rejected `0x201C`), stored per slot. Capability key `0xD186`/`0xD187` both return `X-H2_0200`; DeviceInfo lists 61 properties. |
| X-T5 | 4.20 | USB RAW Conv. / Backup Restore | OK | OK | OK | Confirmed working in app testing. |
| X-T30 II | 2.04 | USB RAW Conv. / Backup Restore | OK | OK | OK | X-Trans IV. DR Auto reads and writes as 65535 with priority Off. WB shift reads back per slot. `GetDeviceInfo` lists no properties in this mode, but reads and writes work. See the [X-T30 II report](#x-t30-ii-report) below. |
| X-Pro3 | 2.00 | USB RAW Conv. / Backup Restore | Fails so far | Fails so far | Fails so far | Does not work with the current protocol path so far. Needs more diagnosis. |

## X-T30 II report

```text
Body: X-T30 II
Firmware: 2.04
USB mode: USB RAW Conv. / Backup Restore
Host OS: macOS 26
Library/app/tool used: own Python script, pyusb on libusb 1.0

Read C1-C7: OK
Write properties: OK
Write names: OK
Inter-property delay tested: 0 ms, with a read-back straight after every write

Failures: none so far
Notes: see below
```

Tested 14 to 18 September 2026. The script selects a slot with `0xD18C`, writes the name, then
writes each property and reads it back at once. It stops if a value it wrote comes back different.

It writes `0xD190`, `0xD192`, `0xD195` through `0xD197`, `0xD199` through `0xD1A2`, and the name
`0xD18D`. `0xD19C` is written only when white balance is Color Temperature, and `0xD19F` is skipped
for monochrome simulations. It has never written `0xD18E`, `0xD18F`, `0xD191`, `0xD193`, `0xD194`,
`0xD198`, `0xD1A3`, `0xD1A4` or `0xD1A5`.

Values written and read back unchanged:

| Property | Values |
|---|---|
| Film Simulation `0xD192` | 1, 2, 11, 17, 18 |
| Dynamic Range `0xD190` | 100, 200, 400, 65535 (Auto, see below) |
| Grain `0xD195` | 1 (Off, reads back as 6), 2, 3, 5 |
| Color Chrome, FX Blue | 1, 2, 3 |
| White Balance `0xD199` | `0x0002`, `0x0004`, `0x8001`, `0x8007` (with 3200 K and 5900 K), `0x8020`, `0x8021` |
| WB Shift | red −6 to +5, blue −5 to +4 |
| Highlight, Shadow | whole and half steps, including −15, −5 and 5 on the wire |
| High ISO NR | dial −4, −2 and 0 |
| Clarity | −40, −30, −20, 0, 20, 50 |
| Name `0xD18D` | up to 14 characters written; an 18-character name entered on the camera reads back intact |

### DR Auto is 65535 with priority Off

`0xD191` reads 0 on all seven slots. A slot set to DR Auto on the camera reads 65535 in `0xD190`,
and writing 65535 was accepted and read back as 65535. Writing 0 was not tried. On the X-H2, 65535
is described as a placeholder that appears only while priority is active. On this body it is also
the value for Auto.

### WB shift reads back per slot

In a single read of all seven slots, C2 and C3 both use Auto (`0x0002`) and read different shifts:
R+2/B−4 and R+4/B−5. C1 and C6 both use Auto White Priority (`0x8020`) and read R+2/B−3 and
R+5/B−3. If the shift were stored per white balance type, as reported for the X-T3 and X-T30, each
pair would read the same value. This is what PTP reports. I have not compared photos shot with each
slot.

### `GetDeviceInfo` lists no properties

In this USB mode `GetDeviceInfo` lists no device properties, and `GetDevicePropDesc` returns
`0x200A` for the recipe codes. `GetDevicePropValue` and `SetDevicePropValue` work anyway. A client
that checks `GetDeviceInfo` before writing will refuse to write on this body.

### macOS holds the camera

`ptpcamerad` claims the camera, and `claim_interface` fails with access denied. A normal kill does
not free it. `kill -9` does, but launchd restarts the daemon, so run it right before claiming the
interface. Quit Photos and Image Capture first.

### Read-only values

Seen on this body, for anyone mapping the rest of the block: `0xD18E` 7 or 8, `0xD18F` 2 or 4,
`0xD191` 0, `0xD193` 0, `0xD194` 0, `0xD198` 1, `0xD1A3` 1, `0xD1A4` 1, `0xD1A5` 7.

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
