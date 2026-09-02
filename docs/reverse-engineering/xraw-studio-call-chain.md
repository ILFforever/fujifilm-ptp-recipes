# X RAW STUDIO call chain

**TL;DR**
FUJIFILM X RAW STUDIO sends standard PTP over USB. There is no secret Fuji protocol. Fuji-specific behavior depends entirely on which property numbers are read and written. This file traces the execution path from the application to the wire.

For the recipe property codes themselves, see [current-shooting-state.md](../current-shooting-state.md).

## Terms

| Term | Meaning |
|---|---|
| **PTP** | Picture Transfer Protocol (ISO 15740). The standard protocol cameras speak over USB. Every camera vendor uses it. |
| **MTP** | Media Transfer Protocol. Microsoft's superset of PTP. On Windows the two are handled by the same plumbing. |
| **Opcode** | A PTP command number. `0x1015` means "get a property value". |
| **Property code** | Which setting you are reading or writing. `0x5005` is standard White Balance; `0xD190` is a Fuji-specific one. Codes starting `0xD` are vendor-defined. |
| **Response code** | What the camera answers. `0x2001` means OK. `0x200A` means "I don't have that property". |
| **WPD** | Windows Portable Devices. The Windows framework for talking to cameras and phones. Built on COM. |
| **Ghidra** | A free tool that turns compiled programs back into readable, approximate C. |
| **Export** | A function a DLL makes callable from outside. |
| **vtable** | In compiled C++, an object's table of function pointers. Resolving one identifies the target function of a method call. |
| **RVA** | An address as an offset from where a DLL loads in memory. |

## Confidence labels

- **CONFIRMED** — read directly in the decompiled code, or observed on real hardware.
- **INFERRED** — the structure strongly implies it, but it was not read directly.
- **UNRESOLVED** — not determined.

## Binaries

| File | Description |
|---|---|
| `FUJIFILM_X_RAW_STUDIO.exe` | The app window. 2,047 functions. |
| `XRFC.dll` | RAW conversion engine. Drives the connect sequence. ~14,500 functions. |
| `XGFXAPI.dll` | Fuji's camera SDK ("XSDK"). 126 exported functions. |
| `FTLPTP.dll` | The PTP transport. Writes bytes to the wire. |
| `XRFC.DAT` | Obfuscated table of supported features per camera model. |

## Layer overview

```text
  FUJIFILM_X_RAW_STUDIO.exe        the app
        |  links directly to XRFC.dll
        v
  XRFC.dll                         runs the connect sequence; owns the per-model feature table
        |  loads XGFXAPI.dll at runtime, binds 21 of its 126 functions
        v
  XGFXAPI.dll  ("the XSDK")        builds one C++ command object per call and dispatches it
        |  loads FTLPTP.dll at runtime, binds 31 entry points
        v
  FTLPTP.dll                       one worker thread per camera; owns the PTP transaction
        |  COM
        v
  Windows Portable Devices         Windows owns the USB endpoint and the MTP session
        v
  USB — standard PTP (ISO 15740)
```

**CONFIRMED.** Each transition is verified from the binary's import table and load code.

Every layer above the cable is a Fuji-specific abstraction inside the Windows app. Traffic reaching the body is standard PTP.

## Layer 1: app and connect sequence

### Bound functions

**CONFIRMED.** `XSDKClass::LoadXSDK` (`FUN_1800d3d80` in `XRFC.dll`) loads `XGFXAPI.dll` and binds exactly 21 of 126 available functions. Missing functions cause immediate failure.

| Purpose | Functions |
|---|---|
| Lifecycle | `XSDK_Init`, `XSDK_Exit`, `XSDK_Detect`, `XSDK_OpenEx`, `XSDK_Close`, `XSDK_GetErrorNumber` |
| Identity | `XSDK_GetDeviceInfo`, `XSDK_GetSerialNo`, `XSDK_GetIOPCode`, `XSDK_GetTetherRAWConditionCode`, `XSDK_GetTetherRawCompatibilityCode` |
| Images | `XSDK_ReadImageInfo`, `XSDK_ReadImage`, `XSDK_DeleteImage`, `XSDK_SendRAWFromPC`, `XSDK_ConvertRAWImage` |
| Settings | `XSDK_GetRAWSettings`, `XSDK_SetRAWSettings`, `XSDK_GetCustomSettingParameter`, `XSDK_SetCustomSettingParameter` |
| Other | `XSDK_CheckBatteryInfo` |

The app ignores all other SDK functions.

### Connect sequence

**CONFIRMED.** `XRFCClass::OpenUSB` (`FUN_1800b3a10` in `XRFC.dll`) executes the sequence. Fuji debug logging confirms this order.

1. **`XSDK_Detect`** — Determine attached body count.
2. **`XSDK_GetSerialNo`** — Read serial number and model name from cache (no wire traffic).
3. **`XSDK_OpenEx`** — Obtain camera handle and USB mode.
4. **`XSDK_GetDeviceInfo`** — Fetch device info.
5. **`XSDK_ReadImageInfo`** — Loop and delete to clear transfer buffer. Stop when image format byte reads `5`.
6. **`XSDK_GetIOPCode`** — Read property `0xD184` (e.g., `"FF179501,FA179501"`).
7. **`XSDK_GetTetherRAWConditionCode`** — Read property `0xD186` (e.g., `"X-H2_0200"`).
8. **`XSDK_GetTetherRawCompatibilityCode`** — Read property `0xD187` (e.g., `"X-H2_0200"`).
9. **Feature lookup** — Apply features.

### Body identification

**CONFIRMED.** Properties `0xD186` and `0xD187` return a string identifying the body and firmware generation (e.g., `"X-H2_0200"`).

This string is the lookup key into `XRFC.DAT`, mapping features to body models. The match requires an exact string comparison against fixed 0x448-byte records.

When reading older bodies fails with SDK error `0x1005`, the app appends `"_0100"` to the model name to synthesize the key.

See [xrfc-capability-database.md](xrfc-capability-database.md).

## Layer 2: internal command numbers

**CONFIRMED.** Every `XSDK_*` function assigns a 16-bit internal command ID.

These IDs route calls within the DLL and never reach the wire.

| Range | Area |
|---|---|
| `0x10xx` | Startup, shutdown, enumerate, open, close, device info, battery |
| `0x11xx` | Shutter release and capture |
| `0x12xx` | Image transfer |
| `0x13xx` | Settings. Stills `0x130x`–`0x133x`, movie `0x134x`–`0x136x`, RAW/tether `0x138x` |
| `0x14xx` | Generic property access |
| `0x15xx` | Serial number, property list |
| `0x41xx` | Firmware update |

The `0x138x` block (tethered-RAW feature set) is contiguous:

| ID | Function | Property |
|---|---|---|
| `0x1381` | `XSDK_SendRAWFromPC` | — |
| `0x1382` | `XSDK_SetRAWSettings` | — |
| `0x1383` | `XSDK_GetRAWSettings` | — |
| `0x1384` | `XSDK_ConvertRAWImage` | `0xD183` |
| `0x1385` | `XSDK_GetIOPCode` | `0xD184` |
| `0x1386` | `XSDK_GetTetherRAWConditionCode` | `0xD186` |
| `0x1387` | `XSDK_GetTetherRawCompatibilityCode` | `0xD187` |
| `0x1388` | `XSDK_SetCustomSettingParameter` | the recipe block |
| `0x1389` | `XSDK_GetCustomSettingParameter` | the recipe block |

Property `0xD185` is unused by the SDK.

## Layer 3: request object mapping

**CONFIRMED.** The ~119 wire-capable SDK functions share this structure:

```c
construct(cmdObj, INTERNAL_CMD_ID, handle);
/* ... */
session = resolveSession(handle);
result  = dispatch(session, cmdObj);
destruct(cmdObj);
```

`resolveSession` (`FUN_18001b3a0`) retrieves the session pointer from an array of handles.

`dispatch` (`FUN_18001b430`) acquires the session lock, requests a transaction ID, builds the request, hands it to the transport, parses the response, and releases the lock.

### Request object

**CONFIRMED.**

```text
+0x18  internal command ID
+0x1c  15000                     default command timeout in milliseconds
+0x20  camera handle
+0x28  uint16 property code      <-- reaches the camera
+0x2a  uint16 PTP data type
```

### Data types

**CONFIRMED.** The type field maps to standard PTP DataType codes (ISO 15740):

| Code | Type | On the wire |
|---|---|---|
| `3` (`0x0003`) | `INT16` | 2 bytes, signed |
| `4` (`0x0004`) | `UINT16` | 2 bytes, unsigned |
| `5` (`0x0005`) | `INT32` | 4 bytes, signed |
| `6` (`0x0006`) | `UINT32` | 4 bytes, unsigned |
| `0xFFFF` (`65535`) | `STR` | 1-byte length, then UTF-16LE characters |

A validation function rejects any type outside 1–6 or `0xFFFF`.

## Layer 4: transport

### Binding table

**CONFIRMED.** The SDK binds 31 functions in `FTLPTP.dll`. Missing functions throw exceptions.

| Offset | Function |
|---|---|
| `0xd0` | `FTL_PTP_GetDevicePropValue` |
| `0xd8` | `FTL_PTP_SetDevicePropValue` |

### Session handling (WPD)

**CONFIRMED.** `FTL_PTP_OpenSession` and `FTL_PTP_CloseSession` point to the same address and do nothing:

```c
if (handle invalid) return error;
lastResponse = 0x2001;              // hardcode "PTP OK"
EnterCriticalSection(...); LeaveCriticalSection(...);
return 0;
```

Opcodes for OpenSession (`0x1002`) and CloseSession (`0x1003`) are absent from the binary.

**INFERRED.** Windows Portable Devices (WPD) opens the MTP session automatically.

### Worker thread model

**CONFIRMED.** Each body spawns a dedicated worker thread for USB traffic.

Callers submit work and block:

```c
device.pendingOperation = op;
SetEvent(device.submitEvent);                    // wake worker
WaitForSingleObject(device.doneEvent, INFINITE); // block
return device.result;
```

PTP calls are serialized per body.

### Error handling

**CONFIRMED.** The transport tracks an internal error code and the raw PTP response code.

- Non-`0x2001` PTP response codes are returned to the caller.
- Windows error `E_ACCESSDENIED` translates to PTP `0x200F` (`AccessDenied`).

## Layer 5: wire protocol

### WPD identification

**CONFIRMED.** COM identifiers confirm WPD usage: `CLSID_PortableDevice`, `IID_IPortableDevice`, `CLSID_PortableDeviceManager`, `IID_IPortableDeviceValues`.

### Supported opcodes

**CONFIRMED.** Each transport function specifies a literal PTP opcode:

```c
request.opcode = 0x1015;       // PTP GetDevicePropValue
request.param1 = propertyCode; // e.g. 0xD186
```

All 17 opcodes are standard ISO 15740:

| Opcode | Operation | | Opcode | Operation |
|---|---|---|---|---|
| `0x1001` | GetDeviceInfo | | `0x100e` | InitiateCapture |
| `0x1004` | GetStorageIDs | | `0x1014` | **GetDevicePropDesc** |
| `0x1005` | GetStorageInfo | | `0x1015` | **GetDevicePropValue** |
| `0x1006` | GetNumObjects | | `0x1016` | **SetDevicePropValue** |
| `0x1007` | GetObjectHandles | | `0x1017` | ResetDevicePropValue |
| `0x1008` | GetObjectInfo | | `0x1018` | TerminateOpenCapture |
| `0x1009` | GetObject | | `0x101c` | InitiateOpenCapture |
| `0x100a` | GetThumb | | | |
| `0x100b` | DeleteObject | | | |

### Vendor opcode absence

**CONFIRMED.** The transport provides `FTL_PTP_VendorExtensionOperation`, but the SDK routes all property reads and writes through `0x1015` / `0x1016`. There is no secret Fuji opcode.

### Property description access

Send `0x1014` (`GetDevicePropDesc`) to query property data types, writability, and acceptable values (ranges or enumerations).

Layout:

```text
uint16 propertyCode | uint16 dataType | uint8 getSet (1 = writable)
value factoryDefault | value current
uint8 form  (0 = none, 1 = range, 2 = enumeration)
  form 1: value min, value max, value step
  form 2: uint16 count, then count values
```

Each `value` length matches `dataType`.

## Worked example

```text
 1. XRFC.dll   XRFCClass::OpenUSB calls the SDK
 2. XGFXAPI    XSDK_GetTetherRAWConditionCode
 3.            build request: property 0xD186, type 0xFFFF (string)
 4.            resolve session from camera handle
 5.            dispatch
 6.            type 0xFFFF is legal -> proceed
 7.            call transport slot +0xd0
 8. FTLPTP     FTL_PTP_GetDevicePropValue
 9.            request.opcode = 0x1015, request.param1 = 0xD186
10.            queue it, wake worker thread, block
11.            worker calls WPD
12. WPD -> USB
13.            camera answers: response 0x2001,
                 data 0A 58 00 2D 00 48 00 32 00 5F 00 30 00 32 00 30 00 30 00 00 00
14.            response is 0x2001 -> success
15.            decode as PTP string -> "X-H2_0200"
16. XRFC.dll   look "X-H2_0200" up in XRFC.DAT -> X-H2Config2 -> apply model feature flags
```

## App-level call: camera-write selector

**CONFIRMED.** Recovered from `FUJIFILM_X_RAW_STUDIO.exe` (mixed-mode C++/CLI; CLI metadata and IL,
not the Ghidra native dump — see the note in
[xraw-studio-re-tracker.md](xraw-studio-re-tracker.md#binary-coverage)).

X RAW STUDIO's *Copy to CAMERA* dialog has two checkboxes:

- **"Copy to CAMERA SETTING"** — write to the camera's current shooting state (live / C0).
- **"Copy to CAMERA CUSTOM SETTING"** — write to a stored slot (C1–C7).

The app builds a single 16-bit selector from these two checkboxes and passes it to
`XSDK_SetCustomSettingParameter`:

```text
selector = (custom checked ? slot : 0) | (current checked ? 0x8000 : 0)
```

| Bits | Meaning |
|---|---|
| 0–14 | Slot number `1`–`7`, or `0` if not writing a slot |
| 15 (`0x8000`) | Apply to the camera's current shooting state |

So the possible values are:

| Selector | Effect |
|---|---|
| `0x0001`–`0x0007` | Slot only |
| `0x8000` | Live only |
| `0x8001`–`0x8007` | Both slot **and** live in one call |

The UI disables OK when neither checkbox is ticked, so `0` never reaches the SDK.

Two things follow:

1. Writing the live state is a **shipped feature** of Fuji's own app, not an undocumented side road.
2. There is **no live read** in this API. The reader (`XSDK_GetCustomSettingParameter`) is
   unconditional and touches only the stored block — `0xD18C`, `0xD18D`, `0xD18E`–`0xD1A4`, plus
   `0xD1A8`. It contains no live property codes and no branching. Reading the live codes directly
   with `GetDevicePropValue` (`0x1015`) works fine.

This is what the SDK dispatches into: when bit 15 is set, `SetCustomSettingParameter` writes the
23-property block to the live codes (see
[current-shooting-state.md](../current-shooting-state.md#property-map)); when bits 0–14 carry a
slot, it writes the same block to the slot codes (`0xD18E`–`0xD1A4`) after selecting the slot via
`0xD18C`.

## Client implementation notes

- **Send `OpenSession` (`0x1002`).** WPD handles this automatically for Fuji's app. Third-party clients must send it explicitly.
- **Query `GetDevicePropDesc` (`0x1014`) before writing.** Property support varies across body generations.
- **Serialize PTP operations.** Send one operation at a time per body.
- **Format values correctly.** Recipe properties are 2-byte little-endian. Strings use a 1-byte length followed by UTF-16LE characters.
- **Expect `<Model>_<Firmware>` from `0xD186`.** Older bodies will fail this read.
- **Use standard opcodes.** Access Fuji property codes using `0x1015` and `0x1016`.

## Reproducing this

**Read DLL exports and imports.** Use Python `pefile` to parse `IMAGE_DIRECTORY_ENTRY_EXPORT` and `..._IMPORT`. Decompiler dumps can skip stub functions or misrepresent shared addresses.

**Decompile.** Run Ghidra headless (`analyzeHeadless`) with a Java post-script. Iterate `getFunctionsNoStubs(true)` and output functions to a single text file. Search this file with `grep`. Use a short path (e.g., `C:\ghidra\`) to avoid script loader failures.

**Resolve C++ methods.** Find the vtable address through constructor memory references. Read the address as an array of 8-byte pointers. Resolve each pointer to a function.

**Read COM GUIDs.** Parse the raw 16-byte values in `.rdata` using `pefile.get_data(rva, 16)` and format as UUIDs (`bytes_le`).

## Unresolved

- Whether `0xD186` and `0xD187` differ. They are identical on a tested X-H2.
- What "IOP" stands for in `0xD184`.
- The RAW conversion round-trip (`SendRAWFromPC` → `SetRAWSettings` → `ConvertRAWImage` → `ReadImage`). The wire sequence and completion model remain untraced.

See [current-shooting-state.md](../current-shooting-state.md#open-questions) for open questions on the recipe block.
