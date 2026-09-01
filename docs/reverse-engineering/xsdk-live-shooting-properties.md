# XSDK live-shooting properties

Recovered from static analysis (Ghidra decompilation) of `XGFXAPI.dll`, the Fuji XSDK inside
FUJIFILM X RAW STUDIO.

**Live shooting / tethering properties** — read during an active tethered session (remote shutter
release, live exposure control, movie mode). Mostly disjoint from the recipe-slot block in
[properties.md](../properties.md) (`0xD18E`–`0xD1A4`). Not yet confirmed against live USB traffic;
treat as INFERRED until cross-checked.

> **Scope caveat.** X RAW STUDIO binds only 21 of `XGFXAPI.dll`'s 126 exports. **None** of the
> live-shooting controls are among them. From this file, only `CheckBatteryInfo`, `GetSerialNo`,
> `GetIOPCode`, and the two tether check codes are exercised. These property IDs rest on decompiled
> call shape alone — no corroboration from app behaviour or captured traffic is possible.
> See [xraw-studio-call-chain.md](xraw-studio-call-chain.md#what-the-app-actually-binds) for the
> binding list.

## Recovered property map

All 126 `XSDK_*`/`XRFC_*` exports swept through the decompiler. Pattern-matching the
`FUN_1800194e0`-style call (`build(buffer, internalCmdId, cameraHandle, propertyId, bufferSize,
typeFlag)`) recovered the property ID for ~60 exports automatically. Standard PTP/MTP codes (ISO
15740 range `0x5001`–`0x501F`) cover basic exposure controls; everything else is a Fuji vendor
property in the `0xD0xx`–`0xD3xx` range.

| Function | Internal cmd | Property | Notes |
|---|---|---|---|
| `XSDK_CapAEMode` / `GetAEMode` / `SetAEMode` | `0x1301`+ | `0x500e` | standard PTP ExposureProgramMode |
| `XSDK_CapExposureBias` / `Get`/`Set` | `0x1307`-`0x1309` | `0x5010` | standard PTP ExposureBiasCompensation |
| `XSDK_CapSensitivity` / `Get`/`Set` | `0x1311`-`0x1313` | `0x500f` | standard PTP ExposureIndex (ISO) |
| `XSDK_CapMeteringMode` / `Get`/`Set` | `0x1317`-`0x1319` | `0x500b` | standard PTP ExposureMeteringMode |
| `XSDK_CapWBMode` / `Get`/`Set` | `0x1331`-`0x1333` | `0x5005` | standard PTP WhiteBalance |
| `XSDK_CapWBColorTemp` / `Get`/`Set` | `0x1334`-`0x1336` | `0xd017` | live WB color temp (cf. recipe-slot `0xD19C`) |
| `XSDK_CapDynamicRange` | `0x1314` | `0xd007` | live Dynamic Range (cf. recipe-slot `0xD190`) |
| `XSDK_CapLensZoomPos` | `0x1321` | `0xd38c` | zoom position capability/range |
| `XSDK_SetLensZoomPos` / `Get` | `0x1322`-`0x1323` | `0xd170` | zoom position, power-zoom lenses |
| `XSDK_CapMode` / `Get`/`Set` | `0x137a`-`0x137c` | `0xd037` | shooting mode (still/movie?) |
| `XSDK_GetErrorDetails` | `0x1033` | `0xd038` | error detail string |
| `XSDK_CapReleaseEx` | `0x1115` | `0xd039` | shutter release capability |
| `XSDK_CapReleaseStatus` / `Get` | `0x1113`-`0x1118` | `0xd224` | release/shutter status |
| `XSDK_CapRecordingStatus` / `Get` | `0x1114`,`0x1119` | `0xd22d` | movie recording status |
| `XSDK_CapDriveMode` / `Get`/`Set` | `0x1377`-`0x1379` | `0xd201` | drive mode |
| `XSDK_CapForceMode` / `Set` | `0x1371`-`0x1372` | `0xd230` | "force mode" (unknown purpose) |
| `XSDK_CapMediaRecord` / `Get`/`Set` | `0x1351`-`0x1353` | `0xd20c` | media/card record target |
| `XSDK_ConvertRAWImage` | `0x1384` | `0xd183` | triggers PC-assisted RAW conversion |
| `XSDK_GetIOPCode` | `0x1385` | `0xd184` | string, `0xffff` buf — recipe-domain property, see check-code section in [xrfc-capability-database.md](xrfc-capability-database.md) |
| `XSDK_GetTetherRAWConditionCode` | `0x1386` | `0xd186` | recipe-domain property, see check-code section in [xrfc-capability-database.md](xrfc-capability-database.md) |
| `XSDK_GetTetherRawCompatibilityCode` | `0x1387` | `0xd187` | recipe-domain property, see check-code section in [xrfc-capability-database.md](xrfc-capability-database.md) |
| Movie-mode family: `CapMovieAperture/Sensitivity/ExposureBias/WBMode/WBColorTemp/DynamicRange/MeteringMode` and their `Get`/`Set` | `0x1343`-`0x136b` | `0xd240`,`0xd242`,`0xd243`,`0xd26c`,`0xd26f`,`0xd271`,`0xd272` | movie-mode equivalents of the still-mode properties above |
| `XSDK_CheckBatteryInfo` (internal, 2 sub-reads) | `0x1046` (outer command) | `0xd36a`, `0xd36b` | see "Battery info" below |

## Battery info (`0xD36A`, `0xD36B`)

`XSDK_CheckBatteryInfo` is not a single property read. The underlying command class
(`CCameraCommandCheckBatteryInfo`) performs **two** `GetDevicePropValue` (`0x1015`) reads:

| Property | PTP DataType | Body |
|---|---|---|
| `0xD36A` | `6` = `UINT32` (4 bytes) | Four one-byte fields: body / grip / grip2 / body2 |
| `0xD36B` | `0xFFFF` = `STR` | Comma-separated battery percentages, same field order |

The "compound command" is purely internal code organisation. Invisible on the wire.

**CONFIRMED** on X-H2 (firmware 2.00), two sessions:

```text
0xD36A  raw: 0C 00 00 00
        decoded: body=12 grip=0 grip2=0 body2=0
0xD36B  raw: 07 39 00 37 00 2C 00 30 00 2C 00 30 00 00 00
        decoded: "97,0,0"
```

- **String had 3 fields, not 4.** This body reports `body,grip,grip2` with no `body2`. Field count
  varies by body. Parse defensively — fall back to the raw string rather than assuming a fixed count.
- Body percentage read `97` then `94` in a later session, consistent with real battery drain.

## Serial number retrieval

`XSDK_GetSerialNo` performs **no PTP transaction**. It validates a device index against an in-memory
table of fixed `0x211`-byte records and copies serial number and model name directly.

The table is populated during device enumeration. **INFERRED:** the source is the standard PTP
`GetDeviceInfo` (`0x1001`) response, which carries Manufacturer, Model, DeviceVersion, and
SerialNumber in one reply — the only operation that runs once per connect. The exact populating call
was not traced.

For a serial number in a custom client, read `GetDeviceInfo` directly.

## Not yet traced

`XSDK_GetAperture` / `CapAperture`, `XSDK_GetShutterSpeed`, `XSDK_GetDynamicRange`, and
`XSDK_SendRAWFromPC` use their own command classes rather than the simple request builder. The
automated sweep did not recover their property codes.

**INFERRED:** same `GetDevicePropValue` mechanism as everything else, routed through a different
class. No separate vendor-operation family exists in this binary. Resolving each class's vtable (as
done for `CheckBatteryInfo`) would confirm.
