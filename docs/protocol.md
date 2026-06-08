# Fuji PTP Recipe Protocol

This document describes the observed USB PTP protocol used to read and write Fujifilm custom
recipe slots.

Custom recipe slots are exposed as standard PTP device properties in a Fuji vendor range — not as
a single backup blob. A slot selector property chooses which custom slot subsequent reads and
writes operate on.

## 1. Status And Scope

Confirmed scope:

- Read custom slot names.
- Read known custom recipe properties.
- Write known custom recipe properties.
- Write custom slot names.
- Work with C1-C7 style custom slots on tested bodies.

Known out of scope for this first protocol writeup:

- Full camera backup/restore blobs.
- In-camera RAW conversion / darkroom object upload.
- General camera remote control.
- Full EXIF MakerNote recipe reconstruction.

## 2. USB Layer

| Item | Observed value |
|---|---|
| Fujifilm USB vendor ID | `0x04CB` |
| PTP interface class | `0x06` |
| Mass storage interface class | `0x08` |
| Required endpoints | bulk OUT and bulk IN |
| Optional endpoint | interrupt IN |
| Typical bulk chunk size | 16 KiB |
| Typical command timeout | 5 seconds |

The camera must expose a Still Image / PTP interface. If it exposes only a mass-storage interface,
the host should report that the camera is in the wrong USB mode.

The required camera USB mode is listed in the camera menu as:

- **USB RAW CONV./BACKUP RESTORE**

This is a single combined option. Other modes (such as card reader / MTP) will not expose the PTP
interface.

## 3. PTP Container Format

All observed traffic uses standard little-endian PTP bulk containers.

```text
offset  size  field
0       4     length, including the 12-byte header
4       2     container type
6       2     operation code or response code
8       4     transaction id
12      ...   params or data payload
```

Container types:

| Type | Meaning |
|---:|---|
| 1 | Command |
| 2 | Data |
| 3 | Response |
| 4 | Event |

Command params and response params are 32-bit little-endian values. Data payloads are raw bytes.

Validation rules used by a defensive implementation:

- container length must be at least 12
- container type must be 1..4
- received data should be accumulated until the declared container length has arrived
- command/data/response transaction ids should match within a transaction

## 4. Transaction Shapes

### 4.1 Command + Response

Used for commands with no data payload.

```text
host -> camera: Command(code, txId, params)
camera -> host: Response(responseCode, txId, params)
```

Example:

```text
OPEN_SESSION 0x1002, params=[1]
```

### 4.2 Command + Data In + Response

Used for reads such as `GET_DEVICE_INFO` and `GET_DEVICE_PROP_VALUE`.

```text
host -> camera: Command(code, txId, params)
camera -> host: Data(code, txId, payload)
camera -> host: Response(RESPONSE_OK, txId)
```

Example:

```text
GET_DEVICE_PROP_VALUE 0x1015, params=[0xD18D]
```

### 4.3 Command + Data Out + Response

Used for writes such as `SET_DEVICE_PROP_VALUE`.

```text
host -> camera: Command(code, txId, params)
host -> camera: Data(code, txId, payload)
camera -> host: Response(RESPONSE_OK or error, txId)
```

Example:

```text
SET_DEVICE_PROP_VALUE 0x1016, params=[0xD18C], data=<uint16 slot>
```

## 5. Important Opcodes

| Hex | Decimal | Symbol | Direction |
|---|---:|---|---|
| `0x1001` | 4097 | `GET_DEVICE_INFO` | Data IN |
| `0x1002` | 4098 | `OPEN_SESSION` | Response only |
| `0x1003` | 4099 | `CLOSE_SESSION` | Response only |
| `0x1014` | 4116 | `GET_DEVICE_PROP_DESC` | Data IN |
| `0x1015` | 4117 | `GET_DEVICE_PROP_VALUE` | Data IN |
| `0x1016` | 4118 | `SET_DEVICE_PROP_VALUE` | Data OUT |

Response codes:

| Hex | Decimal | Meaning |
|---|---:|---|
| `0x2001` | 8193 | OK |
| `0x2002` | 8194 | General Error |
| `0x2003` | 8195 | Session Not Open |
| `0x201C` | 8220 | observed non-OK response when writing Dynamic Range while DR Priority is active |
| `0x201E` | 8222 | Session Already Open |

## 6. Fuji Recipe Properties

| Hex | Decimal | Meaning |
|---|---:|---|
| `0xD18C` | 53644 | Slot selector |
| `0xD18D` | 53645 | Preset name |
| `0xD18E..0xD1A5` | 53646..53669 | Per-slot recipe property block |
| `0xD190` | 53648 | Dynamic Range |
| `0xD191` | 53649 | Dynamic Range Priority |

The slot selector is the central control point. Write `0xD18C` first, then read or write the name
and recipe properties for that selected slot.

Observed slot values:

| Slot | Value | Payload |
|---|---:|---|
| C1 | 1 | `01 00` |
| C2 | 2 | `02 00` |
| C3 | 3 | `03 00` |
| C4 | 4 | `04 00` |
| C5 | 5 | `05 00` |
| C6 | 6 | `06 00` |
| C7 | 7 | `07 00` |

Slot count may differ on older or lower-end bodies. Do not assume C1-C7 until the body is tested.

## 7. Session Setup

Recommended setup:

```text
1. Find USB device with vendor id 0x04CB.
2. Claim the PTP interface, class 0x06.
3. Find bulk OUT and bulk IN endpoints.
4. OPEN_SESSION with session id 1.
5. GET_DEVICE_INFO.
6. Parse model and SupportedDeviceProperties.
7. Confirm 0xD18C is present.
```

If `0xD18C` is missing, the connected camera/mode probably does not support this recipe-slot path.

## 8. Read Flow

Minimal read of one slot:

```text
OPEN_SESSION(session=1)
GET_DEVICE_INFO
SET_DEVICE_PROP_VALUE 0xD18C = slot number as uint16LE
GET_DEVICE_PROP_VALUE 0xD18D = preset name PTP string
for code in 0xD18E..0xD1A5:
    GET_DEVICE_PROP_VALUE code
CLOSE_SESSION
```

Detailed read notes:

- Select the slot before reading the name.
- Select the slot before reading the property block.
- After writing the slot selector, wait approximately 100 ms before reading. This lets the camera
  commit the slot switch internally. 50 ms was confirmed clean on X-H2 firmware 5.20; use 100 ms
  as the safe default for untested bodies. Revert to 100 ms if another body returns corrupt or
  blank slot data after a slot switch.
- The preset name is a PTP string, not a 2-byte integer.
- Known recipe properties are a mix of `uint16LE` and `int16LE`.
- Unknown properties in the block should be logged, not discarded silently, when developing.

### 8.1 Reading Live Current Values

To read the camera's current live property values independent of any stored slot, issue
`GET_DEVICE_PROP_VALUE` for each code in `0xD18E..0xD1A5` without writing the slot selector first.
This returns the active settings the camera is currently using, regardless of which custom slot was
last selected or whether the camera is in a custom slot at all.

This pattern is useful for editor views and for importing the camera's current state into the app
without committing to a slot selection first.

## 9. Write Flow

Minimal write of one slot:

```text
OPEN_SESSION(session=1)
GET_DEVICE_INFO
SET_DEVICE_PROP_VALUE 0xD18C = target slot number as uint16LE
GET_DEVICE_INFO
SET_DEVICE_PROP_VALUE 0xD192 = film simulation, if writing it
SET_DEVICE_PROP_VALUE <other properties>
SET_DEVICE_PROP_VALUE 0xD18D = preset name PTP string
CLOSE_SESSION
```

Recommended write rules:

- Always select the target slot first.
- Refresh with `GET_DEVICE_INFO` after selecting the slot.
- Write Film Simulation before dependent properties.
- Skip color-only properties for monochrome simulations.
- Skip Color Temperature unless White Balance is Color Temperature.
- Skip Dynamic Range `0xD190` when Dynamic Range Priority `0xD191` is Weak, Strong, or Auto.
- Use `int16LE` for signed properties.
- Use `uint16LE` for unsigned properties.
- Write the preset name last.
- Track per-property failures.

## 10. Color-Only Suppression

When Film Simulation is monochrome-like, skip:

- Color Chrome
- Color Chrome FX Blue
- Color
- WB Shift Red
- WB Shift Blue

Observed monochrome-like film simulation codes:

```text
6, 7, 8, 9, 10, 12, 13, 14, 15
```

## 11. Color Temperature Suppression

Only write `0xD19C` Color Temperature when White Balance is `0x8007`.

If the white balance mode is Auto, Daylight, Shade, Incandescent, Fluorescent, etc., suppress the
Color Temperature write even if a stale value exists locally.

## 12. Dynamic Range Priority

Dynamic Range Priority is exposed in the slot property block at `0xD191` as `uint16LE`.

| Wire | Meaning |
|---:|---|
| 0 | Off |
| 1 | Weak |
| 2 | Strong |
| 32768 (`0x8000`) | Auto |

When Dynamic Range Priority is not Off, the camera controls Dynamic Range and rejects direct writes
to `0xD190`.

Confirmed X-H2 firmware 5.20 bench sequence:

```text
SET_DEVICE_PROP_VALUE 0xD191 = 1 / Weak
<- RESPONSE_OK 0x2001
GET_DEVICE_PROP_VALUE 0xD191
<- 01 00 / Weak

SET_DEVICE_PROP_VALUE 0xD190 = 400 / DR400%
<- response 0x201C
GET_DEVICE_PROP_VALUE 0xD190
<- previous DR value unchanged
GET_DEVICE_PROP_VALUE 0xD191
<- 01 00 / Weak still active
```

For recipe writers: write `0xD191` first. If it is Weak, Strong, or Auto, omit `0xD190` from the
write set. Only write manual DR Auto/100/200/400 when `0xD191` is Off.

## 13. Timing

Known results:

- X-H2 firmware 5.20: 0 ms inter-property write delay worked in app testing.
- X-H2 firmware 5.20: slot-selector settle delay of 50 ms was confirmed clean across a full
  7-slot write bench with 0 errors.

Caution:

- Other bodies may need delay between `SET_DEVICE_PROP_VALUE` calls.
- If a body returns intermittent `GeneralError`, test small delays such as 5 ms, 10 ms, 20 ms,
  50 ms, and 100 ms.
- Slot switching requires a short settle delay before reading values. Start with 100 ms for
  untested bodies. 50 ms has been confirmed safe on X-H2 firmware 5.20.

## 14. PTP String Encoding

PTP strings are length-prefixed UTF-16LE with a null terminator.

```text
byte 0: character count including trailing null
then: UTF-16LE code units
last code unit: 0x0000
```

Example conceptual encoding for `C1`:

```text
03 43 00 31 00 00 00
```

Explanation:

- `03`: three UTF-16 code units including null
- `43 00`: `C`
- `31 00`: `1`
- `00 00`: null terminator

Preset names have stricter safety rules than generic PTP strings. See [name-rules.md](name-rules.md).

## 15. Complete Example Trace

Read C3:

```text
-> OPEN_SESSION tx=1 params=[1]
<- RESPONSE_OK tx=1

-> GET_DEVICE_INFO tx=2
<- DATA tx=2 payload=<DeviceInfo>
<- RESPONSE_OK tx=2

-> SET_DEVICE_PROP_VALUE tx=3 params=[0xD18C]
-> DATA tx=3 payload=03 00
<- RESPONSE_OK tx=3

-> GET_DEVICE_PROP_VALUE tx=4 params=[0xD18D]
<- DATA tx=4 payload=<PTP string>
<- RESPONSE_OK tx=4

-> GET_DEVICE_PROP_VALUE tx=5 params=[0xD18E]
<- DATA tx=5 payload=<value>
<- RESPONSE_OK tx=5

... repeat through 0xD1A5 ...

-> CLOSE_SESSION tx=N
<- RESPONSE_OK tx=N
```

Write C3 name and two properties:

```text
-> OPEN_SESSION tx=1 params=[1]
<- RESPONSE_OK tx=1

-> GET_DEVICE_INFO tx=2
<- DATA tx=2 payload=<DeviceInfo>
<- RESPONSE_OK tx=2

-> SET_DEVICE_PROP_VALUE tx=3 params=[0xD18C]
-> DATA tx=3 payload=03 00
<- RESPONSE_OK tx=3

-> GET_DEVICE_INFO tx=4
<- DATA tx=4 payload=<DeviceInfo>
<- RESPONSE_OK tx=4

-> SET_DEVICE_PROP_VALUE tx=5 params=[0xD192]
-> DATA tx=5 payload=<film simulation uint16LE>
<- RESPONSE_OK tx=5

-> SET_DEVICE_PROP_VALUE tx=6 params=[0xD19E]
-> DATA tx=6 payload=<shadow int16LE>
<- RESPONSE_OK tx=6

-> SET_DEVICE_PROP_VALUE tx=7 params=[0xD18D]
-> DATA tx=7 payload=<preset name PTP string>
<- RESPONSE_OK tx=7

-> CLOSE_SESSION tx=8
<- RESPONSE_OK tx=8
```

## 16. Known Failures / Open Areas

- X-Pro3 does not work with the current protocol path so far. Diagnosis needed.
- X-Trans III bodies are untested.
- Some unknown properties in `0xD18E..0xD1A5` remain unmapped.
- Some bodies may use fewer or different custom slots.
- Camera UI character entry and PTP name writes may not accept the same character set.

## 17. Session Teardown

Recommended disconnect sequence:

```text
1. Mark internal state as disconnected (reset pending state, connection handles).
2. Issue CLOSE_SESSION 0x1003.
3. Release the USB interface.
4. Close the USB connection.
```

The important ordering rule: clear application connection state **before** sending CloseSession,
not after. If the cable was yanked or the camera powered off, CloseSession will fail at the USB
level. Clearing state first means a failed CloseSession does not leave the application in an
inconsistent state. Swallow CloseSession errors — the camera will time out the session on its side.

When the USB cable is detached unexpectedly, CloseSession will most likely fail. That is expected.
The goal is to release the USB interface claim so the OS can recover the device handle cleanly.
