# Protocol status: what is finished and what is not

**TL;DR** — **Everything in this repo that is known to work, works on X-Trans V.** The one
non-X-Trans-V body tested so far fails outright. Treat every other generation as unproven, for
C1–C7 as well as for the newer current-shooting-state (C0) work.

This page exists so nobody has to infer maturity from how confidently a document is written. Read it
before building on anything here.

## Status by area

| Area | Status | Confirmed on |
|---|---|---|
| [Connection and PTP transport](protocol.md) | Working | X-H2, X-T5 |
| [C1–C7 slot read/write](properties.md) | Working **on X-Trans V** | X-H2, X-T5. **X-Pro3 (X-Trans IV) fails** |
| [Preset names](name-rules.md) | Working **on X-Trans V** | X-H2, X-T5 |
| [EXIF MakerNote mapping](exif-makernote.md) | Usable | Independent of camera generation |
| [Current shooting state (C0)](current-shooting-state.md) | **Work in progress** | X-H2 only (firmware 5.20) |

## The generation problem applies to C1–C7 too

It would be easy to read this repo as "C1–C7 is solved, C0 is experimental". That is not the
situation.

Every body confirmed working is **X-Trans V** — X-H2 and X-T5. The only non-X-Trans-V body anyone
has reported, an **X-Pro3 (X-Trans IV), fails at C1–C7 entirely**: reads, property writes and name
writes all fail with the current protocol path. No X-Trans III body has been tested at all.

So the honest summary is: this protocol is confirmed on X-Trans V and unproven everywhere else. C0
is *additionally* unfinished, but it is not the only part with a generation question mark.

### One nuance about the block's first property

The C1–C7 path that is known to work does **not** write the whole documented block. `0xD18E`,
`0xD18F`, `0xD1A3`, `0xD1A4` and `0xD1A5` are [unmapped](properties.md) — read and logged, never
written. Working implementations write `0xD190`–`0xD1A2` only.

That matters because `0xD18E` is exactly the property Fuji's own app wraps in a compatibility
fallback. Anyone extending a client to write the full documented block, rather than the mapped
subset, is stepping onto the one property with a known cross-generation encoding problem — on the
C1–C7 path just as much as on the C0 path.

## Why C0 is expected to break outside X-Trans V

It is not simply untested. There is positive evidence that other generations differ:

- **Fuji's own app carries a compatibility fallback** for the first property in the block. A fallback
  exists because some bodies reject that value. Which ones is unknown, but their existence is the
  point.
- **The encoding of that field varies by generation.** The per-model capability data Fuji ships
  distinguishes at least seven variants of it (`Std1`–`Std4`, `Ext1`–`Ext3`), and **X-Trans III
  bodies have it marked unsupported entirely**.
- **Field reports match.** Tethering work by this project's authors has succeeded on sensor
  generation 5 and failed on every earlier generation tested.

Note the scope of that evidence: it concerns **the first property in the block specifically**. The
other 22 codes have no evidence for or against working on older bodies — they are simply untested
off X-Trans V. An X-Trans IV body might work fine. Nobody has checked.

## What is unfinished in the C0 work

- **Two properties are unidentified.** Rows 1 and 2 of the block are two of Fuji's `FileType`,
  `ImageSize` and `ImageQuality` fields. Which two, and in which order, is not established.
- **The fallback table's meaning is unknown.** Its 27 entries decompose into a 1–9 axis and a 1–3
  axis, but nothing in Fuji's binaries names what either axis enumerates.
- **One property is untested by choice.** Lens Modulation Optimiser is read but never written,
  because its effect is not understood.
- **No non-X-Trans-V body has been tested at all.**

## If you are building on this

- **Assume X-Trans V.** If you are on anything else, expect to be doing original testing rather than
  following documentation. That is true for C1–C7, not only for C0.
- **Detect, do not assume.** `GetDeviceInfo` (`0x1001`) returns the camera's supported-property
  list. Check the codes you intend to use appear in it before writing anything.
- **Write only what you can map.** Sticking to `0xD190`–`0xD1A2` keeps you clear of `0xD18E`, the
  one property with a known generational encoding problem.
- **Read back after writing.** A camera can return OK without applying a value. Do not treat a
  successful response as confirmation.
- Check [tested bodies](tested-bodies.md) before assuming your body behaves like the ones here.

## Helping

The single most useful contribution right now is **C0 results from a non-X-Trans-V body** — an X-T3,
X-T4, X-Pro3, X-S10 or any X-Trans III camera. Even a clean failure is valuable, because it tells us
whether the whole block is generation-specific or only the first property.

See the [testing checklist](testing-checklist.md) for the procedure and
[tested bodies](tested-bodies.md) for the report template.
