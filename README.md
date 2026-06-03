# Fuji PTP Recipes

Community documentation for reading and writing Fujifilm custom recipe slots over USB PTP.

This is not official Fujifilm documentation. It is a public record of observed behavior from
real camera tests and app implementation work. Treat every body/firmware combination as unknown
until tested.

## What This Documents

- USB PTP connection requirements for Fuji cameras.
- The PTP packet and transaction shapes used for recipe-slot access.
- Slot selection through Fuji vendor property `0xD18C`.
- Preset-name reads/writes through `0xD18D`.
- Recipe property reads/writes in `0xD18E..0xD1A5`.
- Known property encodings for film simulation, white balance, dynamic range, tone, color,
  sharpness, clarity, high ISO NR, grain, color chrome, smooth skin, and WB shift.
- Preset-name limits and safe character rules.
- Tested camera bodies and known failures.

## Start Here

| Document | Purpose |
|---|---|
| [Protocol](docs/protocol.md) | Full USB/PTP protocol flow, packet format, session handling, read/write traces. |
| [Properties](docs/properties.md) | Complete known recipe property table and value encodings. |
| [EXIF MakerNote](docs/exif-makernote.md) | Maps Fujifilm MakerNote EXIF tags to recipe parameters for JPEG import. |
| [Name rules](docs/name-rules.md) | Preset-name length, allowed characters, normalization, and gotchas. |
| [Implementation notes](docs/implementation-notes.md) | Practical guidance for building a reader/writer. |
| [Tested bodies](docs/tested-bodies.md) | Body/firmware compatibility matrix. |
| [Testing checklist](docs/testing-checklist.md) | Step-by-step process for testing a new body or firmware. |
| [Python reference snippets](examples/python/ptp_recipe_reference.py) | Constants, encoders, and write/read pseudocode. |

## Current Tested Body Matrix

| Body | Firmware | Read slots | Write props | Write names | Notes |
|---|---:|---|---|---|---|
| X-H2 | 5.20 | OK | OK | OK | 0 ms inter-property delay worked in app testing. Preset names appear capped at 25 characters. |
| X-T5 | 4.20 | OK | OK | OK | Confirmed working in app testing. |
| X-Pro3 | 2.00 | Fails so far | Fails so far | Fails so far | Does not work with the current protocol path so far. Needs more diagnosis. |

## Safety

Read operations should be low risk. Write operations can overwrite camera custom settings.

Before running write tests:

1. Back up C1-C7.
2. Record the camera body and firmware.
3. Start with read-only slot dumps.
4. Write a single slot before writing all slots.
5. Restore your original slots afterwards.

## Contribution Priorities

The most useful contributions are:

- body/firmware test reports
- failing-body diagnostics, especially X-Pro3 and X-Trans III bodies
- complete property dumps from C1-C7
- corrections to property values or write rules
- minimal examples in Python, Kotlin, Rust, Go, or C#

See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

Documentation is licensed under CC BY 4.0. Example code is licensed under MIT.
