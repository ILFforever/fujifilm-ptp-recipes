# X RAW STUDIO / XSDK Binary Architecture

Static analysis (string extraction + Ghidra decompilation) of the official FUJIFILM X RAW STUDIO
Windows app. Property IDs and call shapes below are recovered from compiled code, not from live
USB traffic. Treat values as very likely correct until confirmed against real hardware.

See [xraw-studio-re-tracker.md](xraw-studio-re-tracker.md) for verification status.

## Source binaries

X RAW STUDIO for Windows, as installed by the public Fujifilm installer:

| Binary | Description | Functions |
|---|---|---:|
| `FUJIFILM_X_RAW_STUDIO.exe` | GUI, no exports | 2,047 |
| `FTLPTP.dll` | Low-level PTP/WPD transport wrapper | 599 |
| `XGFXAPI.dll` | XSDK — tethered shooting and RAW SDK, 126 exports | 2,052 |
| `XRFC.dll` | RAW conversion engine (OpenCV-based), wraps `XGFXAPI.dll` | 14,496 |
| `XRFC.DAT` / `xrfc_settings.ini` | Data/config for the conversion engine | — |

## Dynamic linkage chain

**CONFIRMED.** Verified via each binary's PE import table (`pefile`) plus decompiled load logic.
Linkage is dynamic (`LoadLibraryA`/`GetProcAddress`) at every layer except the top:

```text
FUJIFILM_X_RAW_STUDIO.exe
        |  statically links only XRFC.dll (127 imports = the XRFC_* API)
        v
   XRFC.dll  (XRFC_* exports: XRFC_GetDynamicRange, XRFC_ConvertImage, XRFC_CapClarity, ...)
        |  dynamically LoadLibrary's XGFXAPI.dll at runtime (XSDKClass::LoadXSDK /
        |  LoadLibraryForWin -- XGFXAPI.dll does NOT appear in XRFC.dll's static import table)
        v
  XGFXAPI.dll  (XSDK_* exports: this IS Fuji's XSDK -- tethered shooting/RAW SDK)
        |  two independent, unconditional dynamic-load paths, traced to the literal LoadLibraryA
        |  calls (both live in XGFXAPI.dll's own generic module-loader, FUN_18001a070):
        |   1. tries "FTLPTP_X.dll" first, falls back to "FTLPTP.dll" -- the main transport
        |   2. separately also loads "FTLPTP.dll" AND "FTLPTPIP.dll" in parallel (both, not
        |      either/or), each into its own transport-handle slot, tolerating either missing
        v
   FTLPTP.dll / FTLPTP_X.dll / FTLPTPIP.dll  (FTL_PTP_* exports: raw PTP/WPD transport --
                GetDevicePropValue, SetDevicePropValue, VendorExtensionOperation, GetObject,
                InitiateCapture, ...). FTLPTPIP.dll's name and its GetProcAddress'd surface
                (identical FTL_* exports expected) are consistent with a second, pluggable
                PTP-IP-style transport, but the binary itself doesn't ship in this installer
                (only FTLPTP.dll is present in C:\Program Files\FUJIFILM X RAW STUDIO\) so its
                actual network behavior can't be confirmed from what's here.
```

## Internal SDK name

**CONFIRMED.** `FTLPTP.dll` embeds a PDB path confirming the internal project name and toolchain:

```text
C:\Users\1010401maruta\Desktop\20240705_work\spx9\XSDK\SDK\XSDK\FTLPTP\FTLPTP_WPD\Release64\Ftlptp.pdb
```

The Windows SDK is built on Windows Portable Devices (WPD), not a raw USB driver. `XGFXAPI.dll`
statically links only `KERNEL32.dll`, `USER32.dll`, `ole32.dll` (`CoInitialize`/`CoUninitialize`),
and `VERSION.dll`. No PTP or USB library is statically linked.

## XGFXAPI.dll scope

`XGFXAPI.dll` contains the full tethered SDK surface: remote shutter release, live-view preview
read, image download, firmware/lens-firmware update, movie-mode properties, and RAW conversion.
This exceeds what `docs/protocol.md` currently covers.

## Property discovery (`0xD235`)

**Not used by X RAW STUDIO.** A real X-H2 (firmware 2.00) returns `0x200A`
(`DevicePropNotSupported`). `XSDK_GetPropertyValue` and `XSDK_SetPropertyValue`, the two driving
functions, are not among the 21 SDK functions X RAW STUDIO binds.

`0xD235` is a dormant two-step "select, then fetch" mechanism for reading multiple properties in
one round trip:

| Step | Operation | Detail |
|---|---|---|
| Set | `XSDK_SetPropertyValue` (`0x1512`) | Packs a comma-separated property-code string into a binary buffer, writes with `SetDevicePropValue` (`0x1016`) |
| Get | `XSDK_GetPropertyValue` (`0x1513`) | Reads back `uint16 recordCount` + per-record `uint32 valueLength`, `uint16 propCode`, raw value bytes |

Cross-generation capability adaptation is handled by the static `XRFC.DAT` table instead. See
[xrfc-capability-database.md](xrfc-capability-database.md).
