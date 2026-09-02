# X RAW STUDIO reverse engineering

**TL;DR** — Reverse engineering findings from FUJIFILM X RAW STUDIO. Findings here act as protocol
evidence. Confirmed protocol behavior belongs in `docs/`.

## Folder scope

X RAW STUDIO is the official Windows application for tethered RAW conversion. It communicates with
cameras over PTP. Analyzing its binaries yields protocol evidence. Protocol evidence differs from
confirmed camera firmware behavior.

## Confidence labels

Every claim carries one of three labels:

- **CONFIRMED** — read directly in the code, or observed on a real camera.
- **INFERRED** — strongly implied by structure, not directly read.
- **UNRESOLVED** — not determined.

## File index

### Protocol

| File | Description |
|---|---|
| [xraw-studio-call-chain.md](xraw-studio-call-chain.md) | Connection flow, protocol layers, PTP opcode list, and data-type table. |
| [xsdk-live-shooting-properties.md](xsdk-live-shooting-properties.md) | Live tethered shooting property codes (exposure, ISO, metering, drive mode, movie mode, battery). |

### Per-camera features

| File | Description |
|---|---|
| [xrfc-capability-database.md](xrfc-capability-database.md) | Camera identification (`0xD186`) and shipped feature support table across 41 camera/firmware combinations (X-Trans III, IV, V, GFX). |
| [xrfc-value-tables.md](xrfc-value-tables.md) | Per-generation legal-value tables for the ten generation-bound recipe properties, the decoded Image Size fallback grid, and the body-to-variant matrix. |
| [decode_xrfc_capabilities.py](decode_xrfc_capabilities.py) | Decoder for `XRFC.DAT`. |
| [reference/xrfc-capabilities.xml](reference/xrfc-capabilities.xml) | Decoded feature table. |

### Background and status

| File | Description |
|---|---|
| [xraw-studio-sdk.md](xraw-studio-sdk.md) | Binary architecture, dynamic linkage chain, internal SDK name, and the dormant `0xD235` multi-property read. |
| [methodology.md](methodology.md) | Reverse-engineering techniques: string extraction, Ghidra decompilation, vtable resolution, data tables, cipher verification. |
| [xraw-studio-re-tracker.md](xraw-studio-re-tracker.md) | Settled findings, open questions, and coverage per binary. |

## Reproduction instructions

Decompiled dumps are not checked in. Generate them using a Windows installation of X RAW STUDIO,
Ghidra, and Python with `pefile`. Hardware cameras are not required. See [methodology.md](methodology.md).

## Legal note

This repository contains interoperability reverse engineering of freely distributed software. The
purpose is to document an unpublished protocol.

No binaries, installers, or copyrighted creative content are redistributed. Checked-in content
consists of protocol facts (property numbers, opcodes, data layouts), a decoded functional feature
table, and custom code. The warranty warning in the root [README.md](../../README.md) applies.
