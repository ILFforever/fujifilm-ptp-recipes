# XRFC capability database (`XRFC.DAT`)

`XRFC.DAT` ships next to `XRFC.dll` in the official FUJIFILM X RAW STUDIO install (`C:\Program Files\FUJIFILM X RAW STUDIO\` on Windows). It is the per-model compatibility table behind the tether check codes. It defines exactly which controls each body/firmware combination gets. X RAW STUDIO restricts the recipe and RAW-conversion controls it offers based on this table.

The file is decoded by `CapabilityClass::ReadCapabilityFile` in `XRFC.dll`. The decoded output is well-formed XML. See [decode_xrfc_capabilities.py](decode_xrfc_capabilities.py) for the cipher details and working decoder. The full decoded XML output is in [reference/xrfc-capabilities.xml](reference/xrfc-capabilities.xml). Unfamiliar terms are defined in [xraw-studio-sdk.md](xraw-studio-sdk.md#terms-used-in-this-doc).

## Tether check codes (`0xD186`, `0xD187`)

`0xD186` and `0xD187` are the per-camera gating properties. X RAW STUDIO uses them to decide whether tethered RAW processing is allowed and whether individual capabilities are accepted or rejected for the connected body.

Debug strings from `XRFC.dll` confirm the per-property checks:

```text
The connected camera does not support the USB-RAW mode, tetherRAWConditionCode=%s
There is no capability definition of the connected camera, tetherRAWConditionCode=%s
DynamicRange is rejected, tetherRAWConditonCode=%s
Clarity is rejected, tetherRAWConditonCode=%s
Color is rejected, tetherRAWConditonCode=%s
```

Decompiled from `XGFXAPI.dll` (exports #80 and #81):

```c
// RVA 0x28fb0, export #80
undefined4 XSDK_GetTetherRAWConditionCode(longlong param_1,undefined8 param_2)
{
  ...
  FUN_1800194e0(local_58,0x1386,param_1,0xd186,0xffff,1);
  local_40 = 0x100;
  local_48 = param_2;
  lVar2 = FUN_18001b3a0(param_1,'\x01');
  uVar1 = FUN_18001b730(lVar2,local_58);
  ...
}

// RVA 0x29040, export #81
undefined4 XSDK_GetTetherRawCompatibilityCode(longlong param_1,undefined8 param_2)
{
  ...
  FUN_1800194e0(local_58,0x1387,param_1,0xd187,0xffff,1);   // 0x1387 == 4999 decimal
  ...
  uVar1 = FUN_18001b730(lVar2,local_58);
  ...
}
```

Both route through `FUN_1800194e0` and dispatch via `FUN_18001b730` with `typeFlag=1` (string) and `bufferSize=0xffff`. They are read as strings, not integers.

| Property | Internal cmd | Encoding | Confirmed live value (X-H2, fw 2.00) |
|---|---|---|---|
| `0xD186` | `0x1386` | string | `"X-H2_0200"` |
| `0xD187` | `0x1387` | string | `"X-H2_0200"` |

These sit immediately below the slot-selector/recipe block (`0xD18C`+). They are read once per session after connecting, before any recipe reads or writes.

### Return values

**CONFIRMED on hardware.** Read from an X-H2 on firmware 2.00 across separate runs:

```text
0xD186  raw: 0A 58 00 2D 00 48 00 32 00 5F 00 30 00 32 00 30 00 30 00 00 00
        decoded: "X-H2_0200"
0xD187  raw: 0A 58 00 2D 00 48 00 32 00 5F 00 30 00 32 00 30 00 30 00 00 00
        decoded: "X-H2_0200"
```

Both return the literal string `"X-H2_0200"`. The camera identifies itself as `"<Model>_<FirmwareGeneration>"`. This exactly matches the `Device="..."` key format in `<Compatibilitys>`. `X-H2_0200` maps to `X-H2Config2`.

The camera returns no capability verdict. It states its identity. The client decides supported features by looking up the string in `XRFC.DAT`. Accept and reject logic happens entirely on the PC.

### Standard PTP read

**CONFIRMED.** This is a standard PTP `GetDevicePropValue` (opcode `0x1015`) read. Decompiling `FTLPTP.dll`'s `FTL_PTP_GetDevicePropValue` down to the request-builder (`FUN_180008f80`) confirms the opcode:

```c
// FUN_180008f80, called from FTL_PTP_GetDevicePropValue via FUN_180008f40
*(undefined4 *)(param_1 + 0x20) = 0x1015;   // PTP_OC_GetDevicePropValue, ISO 15740
*(uint *)(param_1 + 0x28) = (uint)param_2;  // the property code (e.g. 0xD186) as the operation parameter
```

The request object's vtable is `CMTPOpGetDevicePropValue` (standard Windows Portable Devices MTP operation). `0xD186` and `0xD187` use the same `GetDevicePropValue` transaction as documented recipe properties.

### Unresolved behaviors

**UNRESOLVED.**
* Whether the check is purely informational in X RAW STUDIO, or whether the camera firmware independently refuses recipe-property writes.
* Whether `0xD186` and `0xD187` ever differ from each other on any body or firmware. They are identical on the tested X-H2.

The `XRFC_Cap*` functions consult `XRFC.DAT` using the identity string read from the camera. This file defines what X RAW STUDIO attempts for a given body.

## GetIOPCode (`0xD184`)

Property `0xD184` (`GetIOPCode`, internal cmd `0x1385`) uses the identical call shape as `0xD186` and `0xD187`. It uses the same builder (`FUN_1800194e0`), the same dispatcher (`FUN_18001b730`), and the same `0xffff`/string encoding. It executes via the standard `GetDevicePropValue` (`0x1015`) mechanism.

`0xD184` differs semantically from the session-level check codes:
* `XRFC.dll` stores it (`strIOPCode`) in the per-image `RAWSettings` struct immediately after `lStructVer`.
* It is read and written by every `XSDK_GetRAWSettings` and `XSDK_SetRAWSettings` call.
* It is persisted to on-disk recipe/profile XML under `ConversionProfile.PropertyGroup.IOPCode`.
* It is carried with every subsequent RAW-settings/conversion operation as per-shot metadata.

**CONFIRMED live** (X-H2, fw 2.00):

```text
raw: 12 46 00 46 00 31 00 37 00 39 00 35 00 30 00 31 00 2C 00 46 00 41 00 31 00 37 00 39 00 35 00 30 00 31 00 00 00
decoded: "FF179501,FA179501"
```

The property returns two comma-separated 8-character codes. The codes share a 6-digit suffix (`179501`) but differ in a 2-letter prefix (`FF` vs `FA`).

**INFERRED.** The string pattern suggests a paired hardware-component identifier, such as a sensor and image-processor calibration pairing. This matches its usage as per-shot metadata. "IOP" remains unexpanded in the decompiled binaries.

## Obfuscation cipher

`XRFC.DAT` uses a fixed, reversible cipher. The decoding logic is in `CapabilityClass::ReadCapabilityFile`.

| Offset | Size | Field |
|---|---|---|
| 0 | 8 | Magic (must equal `0xFEDCBA9876543210`) |
| 8 | 8 | `RandomValue` (per-file XOR seed) |
| 16 | 8 | `Time` (logged, unused in decoding) |
| 24 | N | Payload |

Decoding operates on 8-byte (64-bit) chunks:
1. XOR the chunk against the `RandomValue` seed, then against a fixed constant `0xAA559966AA559966`. This yields `natural`.
2. For every full chunk except the last, permute the 8 bytes: `output[i] = natural[i XOR PHASE_MASK[chunk_index % 4]]`. The `PHASE_MASK` array is `[7, 1, 4, 2]`.
3. Process the final, possibly-partial chunk using `natural` directly without permutation.

See [decode_xrfc_capabilities.py](decode_xrfc_capabilities.py) for the implementation.

## Database contents

The decoded file is a `<ConversionCaps Application="Tether-RAW" Version="1.9">` XML document containing two sections:

* `<Compatibilitys>`: Maps `"<Model>_<FirmwareHex>"` strings (e.g. `X-T2_0100`, `GFX50S_0300`) to a named `<PropertyGroup>` config. It specifies a `<DefaultConfig>StdConfig1</DefaultConfig>` fallback, but `StdConfig1` is undefined. Unrecognized combinations resolve to an empty config.
* `<PropertyGroups>`: Contains one `<PropertyGroup Config="...">` per named config. Each config is a flat list of `<PropertyName [type="StdN"/"ExtN"]>true|false</PropertyName>` flags.

Property names exactly match the `XRFC_Cap*` exports (`XRFC_CapDynamicRange`, `XRFC_CapClarity`, `XRFC_CapColorChromeBlue`, etc.).

## Full device to config map

| Device (Model_Firmware) | Config |
|---|---|
| X-H1_0100 | X-H1Config1 |
| X-T3_0100 | X-T3Config1 |
| X-T2_0100 | X-T2Config1 |
| X-Pro2_0100 | XPro2Config1 |
| X100F_0100 | X100FConfig1 |
| GFX50S_0100, GFX50S_0200 | GfxConfig1 |
| GFX50S_0300 | GfxConfig2 |
| GFX50R_0100 | GfxConfig1 |
| GFX50R_0200 | GfxConfig2 |
| X-T30_0100 | X-T30Config1 |
| X-T20_0100 | X-T20Config1 |
| X-E3_0100 | X-E3Config1 |
| GFX100_0100 | Gfx100Config1 |
| GFX100_0200 | Gfx100Config2 |
| GFX100_0300 | Gfx100Config3 |
| X-Pro3_0100 | XPro3Config1 |
| X100V_0100 | X100VConfig1 |
| X100V_0200 | X100VConfig2 |
| X-T4_0100 | X-T4Config1 |
| X-S10_0100, X-E4_0100, X-T30II_0100 | X-S10Config1 |
| X-H2S_0100 | X-H2SConfig1 |
| X-H2S_0200 | X-H2SConfig2 |
| X-H2_0100 | X-H2Config1 |
| X-H2_0200 | X-H2Config2 |
| X-T5_0100 | X-T5Config1 |
| X-T5_0200 | X-T5Config2 |
| X-S20_0100 | X-S20Config1 |
| X-S20_0200 | X-S20Config2 |
| GFX100S_0100 | Gfx100SConfig1 |
| GFX50SII_0100 | Gfx50SIIConfig1 |
| GFX100II_0100 | Gfx100IIConfig1 |
| GFX100SII_0100 | Gfx100SIIConfig1 |
| GFX100RF_0100 | Gfx100RFConfig1 |
| X-T50_0100 | X-T50Config1 |
| X100VI_0100 | X100VIConfig1 |
| X-M5_0100 | X-M5Config1 |
| X-E5_0100 | X-E5Config1 |
| X-T30III_0100 | X-T30IIIConfig1 |

Modern bodies report the full key directly (e.g. `"X-H2_0200"` from `0xD186`). Older bodies fail the SDK call with error `0x1005`. `XRFCClass::OpenUSB` synthesizes the key for older bodies by appending `"_0100"` to the model name. This explains why older bodies only have `_0100` entries. See [xraw-studio-call-chain.md](xraw-studio-call-chain.md#the-_0100-fallback--how-pre-0xd187-cameras-get-a-lookup-key). The table lookup uses an exact string comparison over fixed `0x448`-byte records based on the condition code.

The `_0100` suffix denotes a firmware generation, not the display version string. Multiple display versions map to the same suffix. Firmware updates can trigger a newer generation suffix, granting a richer config in X RAW STUDIO entirely client-side.

## X-Trans III vs IV vs V vs GFX

| Property | X-Trans III (X-T2/X-Pro2/X100F/X-T20/X-E3) | X-H1 (X-Trans III, own config) | X-Trans IV (X-T3/X-T30, `_0100`) | X-Trans IV+ (X-Pro3/X100V/X-T4/X-S10) | X-Trans V (X-H2/X-T5/X-S20/X-T50/...) |
|---|---|---|---|---|---|
| `ImageSize`/`ImageQuality` (remote-settable output size/quality) | **false** | true (`Std2`/`Std1`) | true | true | true (`Std3`) |
| `FileType` (remote-settable output type, e.g. HEIF) | false | false | false | true on X-Pro3 (`Ext1`) only | true (`Ext2`) |
| `WideDynamicRange` | **false** | true | true | true | true |
| `FilmSimulation` type version | `Std1` | `Std2` | `Std2` | `Std3` (X-Pro3/X100V) | `Std5`/`Std6` (more sims: Nostalgic Neg, Reala Ace, ...) |
| `MonochromaticColor` (Mono WC/MG) | absent | absent | absent | present, true (X-Pro3/X100V/X-T4/X-S10) | present, true |
| `ColorChromeBlue` | absent | absent | absent | present, true | present, true |
| `Clarity` | absent | absent | absent | present, true | present, true |
| `CustomSetting` | absent | absent | absent | present, true | present, true |
| `HDR` | absent | absent | absent | present, true (false on some GFX) | present, true (false on some GFX) |
| `BlackImageTone` | false | false | **true** (both X-T3 and X-T30) | false | false |
| `ChromeEffect` (Color Chrome) | false | false | **true** | true | true |
| `WhiteBalance`/`HighlightTone`/`ShadowTone`/`NoiseReduction` type version | `Std1` | `Std1` | `Std1` | `Std1` (`Std2` from X-T4 on) | `Std2` |
| `DigitalTeleConv` | absent | absent | absent | present on X100V only (true) | present on several (X-H2/X-T5/X-T50/X-E5) |
| `PortraitEnhancer` | absent | absent | absent | absent | present only on X-M5, X-T30III (true) |
| `SmoothSkinEffect` | false | false | false | false | no clean generational pattern -- true on X-H2/X-T5/X-T50/X100VI/X-E5, false on X-H2S/X-S20/X-M5/X-T30III; GFX is mostly true except the original `GfxConfig1` |

Full property-by-property detail is in [reference/xrfc-capabilities.xml](reference/xrfc-capabilities.xml).

### Notable irregularities

* **X-H1 capability tracks processor, not sensor.** Despite having an X-Trans III sensor, `X-H1Config1` matches the X-T3 baseline (`ImageSize`/`ImageQuality` true, `WideDynamicRange` true, `FilmSimulation Std2`).
* **X-T3 firmware `_0100` lacks advanced flags.** `X-T3Config1` completely lacks `Clarity`, `MonochromaticColor`, `ColorChromeBlue`, `CustomSetting`, and `HDR`. The real X-T3 gained Clarity via a firmware update, but `XRFC.DAT` only has one `X-T3_0100` row.
* **`BlackImageTone` is exclusively true in four configs.** It appears only in `X-T3Config1`, `X-T30Config1`, `Gfx100Config1`, and `Gfx100Config2`. It is false or absent everywhere else.
* **GFX configs have a separate lineage.** GFX uses `Ext1`/`Ext2`/`Ext3` types instead of `Std*` for `FileType` and `ImageSize`. GFX100-family configs include a `<Battery>Type2</Battery>` tag.

## Unresolved capability limits

This is the client-side tether-RAW-conversion feature table. It directly backs the `XRFC_Cap*` functions. It suggests, but does not prove, what the camera firmware accepts over the wire for the recipe-slot protocol (`0xD18E`-`0xD1A5`). X RAW STUDIO's client-side limitations may differ from the camera's hardware limitations. Confirm firmware rejections via live USB capture.
