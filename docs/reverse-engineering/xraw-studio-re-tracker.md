# X RAW STUDIO Reverse-Engineering Tracker

Track the status of the reverse-engineering work behind the X RAW STUDIO protocol documentation.
Review open items before starting new work.

Terms are defined in
[xraw-studio-call-chain.md](xraw-studio-call-chain.md#glossary).

Legend: ✅ done and verified &nbsp;·&nbsp; 🟡 partially done &nbsp;·&nbsp; ⬜ not started

## Decompilation reproduction

Regenerate the per-function decompile dumps (`allfuncs_*.txt`) locally. They are too large to check
into the repository. Use Ghidra 12.1.3 headless to import and auto-analyze each binary from the
application directory. Run the `DumpAllFunctions.java` post-script from a short filesystem path.
Budget a few minutes per binary. See [methodology.md](methodology.md).

## Live testing bench

Live-verified findings rely on a test bench built into the FujiSync Android app. This bench reads
properties `0xD186`, `0xD187`, `0xD184`, `0xD36A`, `0xD36B`, and `0xD235` over a PTP transport.
It displays raw hex, decoded interpretations, and PTP response codes. All testing uses a single
body (X-H2, fw 2.00). Findings represent single data points, not cross-generation surveys.

## Binary coverage

~140 of ~19,200 functions are individually reviewed. Unreviewed functions are primarily third-party
internals (OpenCV, Boost, CRT).

| Binary | Functions | Individually reviewed | Notes |
|---|---:|---:|---|
| `FTLPTP.dll` | 599 | ~30 | Transport fully mapped. 17 PTP opcode builders enumerated. Worker-thread transaction model traced. HRESULT to PTP error mapping resolved. WPD GUIDs resolved. `OpenSession` and `CloseSession` stubs aliased. |
| `XGFXAPI.dll` | 2,052 | ~100 | 126 exports swept. Internal command IDs recovered for all 126. Dispatcher core, handle registry, and param-object layout traced. Value-shape constraint and 31-slot FTL binding table traced. `0xD235` and `FTLPTPIP.dll` load path traced. |
| `XRFC.dll` | 14,496 | ~15 | `CapabilityClass::ReadCapabilityFile` decode routine traced. `XRFCClass::OpenUSB` connect sequence traced. `XSDKClass::LoadXSDK` traced. `RAWSettingsClass::OutputLog` recovered, giving the full named struct layout. `RAWSettings` to parameter-array serializer traced. |
| `FUJIFILM_X_RAW_STUDIO.exe` | 2,047 | ~10 | **Mixed-mode C++/CLI — the Ghidra dump covers only ~4.5 % of `.text`.** See the note below. UI logic, the camera-write selector, and the value→label maps were recovered by reading CLI metadata and IL instead. |

### The `.exe` is not a native binary

`FUJIFILM_X_RAW_STUDIO.exe` is **mixed-mode C++/CLI**. Its COR20 header is present with
`COMIMAGE_FLAGS_ILONLY` clear, and the CLI metadata holds 13,217 MethodDefs, 2,927 TypeDefs and 408
P/Invoke rows. Only 858 `RUNTIME_FUNCTION` entries exist, covering 96,103 bytes — about **4.5 % of
the 2.1 MB `.text` section**. The rest is CIL bytecode.

Ghidra has no CIL decompiler, so re-running it will not improve coverage, and linear disassembly of
`.text` desynchronises immediately. Use ILSpy, `ildasm` or dnSpy for the managed half. A native
sweep of all 858 functions found no reference to the XRFC import thunks, the controller log strings,
or the label tables — everything of interest on that side is managed code.

## Verified findings

- ✅ Binary architecture and dynamic-linkage chain traced from `.exe` to `FTLPTP.dll`.
  [xraw-studio-sdk.md](xraw-studio-sdk.md#dynamic-linkage-chain)
- ✅ Tether check code properties `0xD186` and `0xD187` return the camera identity string on the
  wire. [xrfc-capability-database.md](xrfc-capability-database.md#return-values)
- ✅ ~60 live-shooting property IDs recovered from the export sweep.
  [xsdk-live-shooting-properties.md](xsdk-live-shooting-properties.md)
- ✅ Battery info properties `0xD36A` and `0xD36B` traced to `GetDevicePropValue` and confirmed on
  the wire.
  [xsdk-live-shooting-properties.md](xsdk-live-shooting-properties.md#battery-info-0xd36a-0xd36b)
- ✅ `GetSerialNo` behavior reads a pre-populated in-memory cache without a live PTP transaction.
  [xsdk-live-shooting-properties.md](xsdk-live-shooting-properties.md#serial-number-retrieval)
- ✅ `XRFC.DAT` cipher fully recovered and verified against real files.
  [xrfc-capability-database.md](xrfc-capability-database.md)
- ✅ `FTLPTPIP.dll` traced end-to-end as a pluggable second transport loaded in parallel with
  `FTLPTP.dll`. [xraw-studio-sdk.md](xraw-studio-sdk.md#dynamic-linkage-chain)
- ✅ `0xD184` property confirmed as two paired 8-character codes carried per-shot in the
  `RAWSettings` struct.
  [xrfc-capability-database.md](xrfc-capability-database.md#getiopcode-0xd184)
- ✅ `0xD235` multi-property read mechanism traced and confirmed unsupported by X-H2 (fw 2.00).
  [xraw-studio-sdk.md](xraw-studio-sdk.md#property-discovery-0xd235)
- ✅ End-to-end call chain traced from app to wire, binding 21 of 126 exports.
  [xraw-studio-call-chain.md](xraw-studio-call-chain.md)
- ✅ `FTL_PTP_OpenSession` and `FTL_PTP_CloseSession` are the same no-op function and never touch
  the wire.
  [xraw-studio-call-chain.md](xraw-studio-call-chain.md#session-handling-wpd)
- ✅ Complete PTP opcode inventory generated for `FTLPTP.dll` showing no Fuji vendor-specific
  opcodes.
- ✅ `_0100` suffix synthesized client-side in `XRFC.DAT` capability key generation.
  [xrfc-capability-database.md](xrfc-capability-database.md#full-device-to-config-map)
- ✅ SDK property value shapes constrained to a 1–6 byte scalar or a `0xffff` variable-length
  string.
- ✅ `RAWSettingsClass::OutputLog` in `XRFC.dll` recovered — names every `RAWSettings` field with its
  struct offset. The 23-property block is `0x1058`–`0x10b8` in order, skipping `lExposureBias` and
  `lWBShootCond`.
- ✅ Block builder `FUN_1800c55f0` located — the function that turns `RAWSettings` into the 23-int
  array passed to `XSDK_SetCustomSettingParameter`. Read directly, it settles row 1 = `lImageSize`,
  row 2 = `lImageQuality`, `0xD193` = `lBlackImageTone`, `lFileType` never sent, and shows that 21 of
  23 fields are verbatim copies.
  [xrfc-value-tables.md](xrfc-value-tables.md#15-the-block-builder--fun_1800c55f0)
- ✅ Only two fields are transformed on the way out: the grain composite (`0xD195`) and a conditional
  Image Quality remap (`0xD18F`, `2→4`/`3→5`/`6→7`).
- ✅ The live / C0 write is a shipped X RAW STUDIO feature, not dead SDK code. Selector bit 15
  (`0x8000`) requests it, built directly from the *Copy to CAMERA SETTING* checkbox; bits 0–14 carry
  the slot. Both can be set in one call.
  [current-shooting-state.md](../current-shooting-state.md#fujis-own-app-writes-the-live-state)
- ✅ `0xD1A8`'s reconstructed aspect ratio is a placeholder that Fuji's client overwrites; there is no
  read path for the aspect at all. [xrfc-value-tables.md](xrfc-value-tables.md)
- ✅ `0xD193` identified as `lBlackImageTone` and `0xD194` as `lMonochromaticColor_RG`. Corrects an
  earlier claim that `BlackImageTone` was not carried.
- ✅ Slot block bounded at `0xD18E`–`0xD1A4`; `0xD1A5` belongs to the live block. Confirmed from the
  emit order of both write branches.
- ✅ Row-1-only scope of the fallback confirmed structurally: the writer is unrolled straight-line
  code, and `0xD03A`/`0xD03B`/`0xD1A8` appear exactly 4 times in the whole binary.
- ✅ Per-property generation risk derived from the capability table — 5 universal properties, 7 with
  varying encodings, 10 absent on some bodies.
  [protocol-status.md](../protocol-status.md#which-properties-differ-by-generation)
- ✅ Image Size fallback axes resolved: row = image size (L/M/S), column = aspect ratio, all 27 cells
  named from a wide-string label table. [xrfc-value-tables.md](xrfc-value-tables.md)
- ✅ Ten generation-bound properties identified; the other fourteen in the block have no
  variant-keyed table and vary only by presence.
- ✅ Colour Temperature `0xD19C` is emitted out of numeric order, immediately after White Balance
  `0xD199`, confirming the prerequisite ordering rule. [properties.md](../properties.md#suggested-write-order)

## Open tasks

- 🟡 `CapabilityClass` accessor list enumerated and `0xD186` lookup key traced. Missing fallback
  behavior for a missing capability record and exact error condition paths in `OpenUSB`.
- ⬜ The RAW conversion round-trip sequence and completion polling model on the wire.
  `XSDK_SendRAWFromPC`, `SetRAWSettings`, and `ConvertRAWImage` are bound but untraced.
- 🟡 `RAWSettingsClass` in `XRFC.dll`. Struct layout fully recovered from `OutputLog`, and the
  `XRFC_{Clear,Get,Save,Load,Renew}RAWSettings` exports located. The on-disk profile save/load format
  is still untraced — an XML serializer writing `ConversionProfile.PropertyGroup.*` keys is present
  and is the obvious next thread for a plain-text recipe interchange format.
- 🟡 **Per-generation value tables recovered** for all ten generation-bound properties, at 100 %
  entry coverage, and bound to properties via their `<xmlattr>.type` parsers.
  [xrfc-value-tables.md](xrfc-value-tables.md). Remaining: four declared variants have no table in
  the binary (Colour Temperature `Std2`, Grain Effect `Std1`, CustomSetting, DigitalTeleConv) and the
  `equal_range` miss path is untraced.
- ⬜ `XGFXAPI.dll` command classes for aperture, shutter speed, dynamic range, and RAW send. Manual
  vtable tracing required.
- ⬜ `0xD185` unused property in the tether block. Requires probing on a live body.
- 🟡 `FUJIFILM_X_RAW_STUDIO.exe`. The camera-write selector, the *Copy to CAMERA* dialog logic and
  the complete value→label maps are recovered. License, update and telemetry logic are untouched, and
  need a CIL tool rather than Ghidra.
- 🟡 Live USB packet capture of X RAW STUDIO traffic. Required to confirm firmware-level rejections
  on older bodies, diagnose X-Pro3 write failures, and verify `0xD186` and `0xD187` string matching
  across bodies.

## Tracker updates

Move an item from open to done only once it is verified. Decompile the code and cross-check against
real output. Link the documentation file and section containing the finding.
