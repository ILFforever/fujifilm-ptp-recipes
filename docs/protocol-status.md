# Protocol status: what is finished and what is not

**TL;DR** — **Everything in this repo that is known to work, works on X-Trans V.** The one
non-X-Trans-V body tested so far fails outright. Treat every other generation as unproven, for
C1–C7 as well as for the newer current-shooting-state (C0) work.

This page records the maturity of each area explicitly, so it does not have to be inferred from the
tone of the other documents. Read it before building on anything here.

## Status by area

| Area | Status | Confirmed on |
|---|---|---|
| [Connection and PTP transport](protocol.md) | Working | X-H2, X-T5 |
| [C1–C7 slot read/write](properties.md) | Working **on X-Trans V** | X-H2, X-T5. **X-Pro3 (X-Trans IV) fails** |
| [Preset names](name-rules.md) | Working **on X-Trans V** | X-H2, X-T5 |
| [EXIF MakerNote mapping](exif-makernote.md) | Usable | Independent of camera generation |
| [Current shooting state (C0)](current-shooting-state.md) | **Work in progress** | X-H2 only (firmware 5.20) |

## Cross-generation applicability

All bodies confirmed working are X-Trans V: X-H2 and X-T5. The one non-X-Trans-V body reported, an
X-Pro3 (X-Trans IV), fails at C1–C7 — reads, property writes and name writes all fail. No X-Trans III
body has been tested.

Three observations indicate that behaviour differs by generation, independent of test coverage:

- Fuji's application implements a compatibility fallback for `0xD18E`, the first property in the
  block. The fallback exists because some bodies reject the value written to it.
- The per-model capability data Fuji ships records seven encoding variants for that field, and marks
  it unsupported on X-Trans III bodies.
- Tethering work by this project's authors has succeeded on sensor generation 5 and failed on every
  earlier generation tested.

The constraint applies to C1–C7 as well as C0. C0 is additionally unfinished, but `0xD18E` is common
to both paths.

Working implementations of the C1–C7 path write `0xD190`–`0xD1A2` only. `0xD18E` (Image Size),
`0xD18F` (Image Quality), `0xD1A3` (Lens Modulation Optimiser) and `0xD1A4` (Color Space) are
identified, but their [value encodings are unmapped](properties.md); they are read and logged, never
written. A client extending coverage to the full block encounters `0xD18E` first.

The fallback is the only compatibility shim Fuji implements. It does not account for the full extent
of generational variation, which the next section quantifies.

## Which properties differ by generation

Fuji ships a per-model capability table with X RAW STUDIO covering 36 configurations across 41
camera/firmware combinations. It records, for each setting, whether a body supports it and which
*encoding variant* that body uses. Decoded, it partitions the block into three groups.

**Present on all configurations, single encoding.**

`0xD190` Dynamic Range · `0xD19A`/`0xD19B` WB Shift · `0xD19F` Color · `0xD1A0` Sharpness ·
`0xD1A4` Color Space

**Present on all configurations, encoding varies by generation.** A write is accepted on any body,
but the value may be interpreted differently.

| Code | Property | Encoding variants |
|---|---|---:|
| `0xD192` | Film Simulation | **6** |
| `0xD195` | Grain Effect | 2 |
| `0xD199` | White Balance | 2 |
| `0xD19C` | Colour Temperature | 2 |
| `0xD19D` | Highlight Tone | 2 |
| `0xD19E` | Shadow Tone | 2 |
| `0xD1A1` | High ISO NR | 2 |

**Absent on some bodies entirely.** Supported on N of 36 configurations:

| Code | Property | Supported |
|---|---|---:|
| `0xD193` | Mono Warm/Cool (`BlackImageTone`) | **4 / 36** |
| `0xD198` | Smooth Skin Effect | 16 / 36 |
| `0xD194` | Mono Magenta/Green | 24 / 36 |
| `0xD1A2` | Clarity | 24 / 36 |
| `0xD197` | Color Chrome FX Blue | 25 / 36 |
| `0xD191` | Dynamic Range Priority | 29 / 36 |
| `0xD196` | Color Chrome Effect | 30 / 36 |
| `0xD18E` | Image Size (+ 7 encodings) | 31 / 36 |
| `0xD18F` | Image Quality (+ 2 encodings) | 31 / 36 |
| `0xD1A3` | Lens Modulation Optimiser | 31 / 36 |

`0xD18E` and `0xD18F` are Image Size and Image Quality. They are not film-simulation settings and are
of low relevance to recipe work; most implementations omit them. They are listed for completeness and
because `0xD18E` carries Fuji's compatibility shim.

Two entries warrant specific attention.

`0xD193` is supported on 4 of 36 configurations — the narrowest support in the block. Most
non-X-Trans-V bodies are expected to reject it.

`0xD192` Film Simulation is present on every configuration but carries six encoding variants. A write
therefore succeeds on any body while potentially selecting a different simulation than intended. This
is the only property in the block where a generational mismatch produces an incorrect result rather
than an error.

`0xD18E` is the sole property that is both heavily fragmented (7 encodings) and frequently absent,
which is consistent with it being the only one Fuji shipped a compatibility shim for.

**Scope of this evidence.** The source is X RAW STUDIO's tether-RAW conversion capability table: the
feature set Fuji's application offers for a given body in that workflow. It is Fuji's own data and is
strong evidence of camera support, but it is not a direct statement about whether a PTP property
exists on the wire. It is a risk ranking, not a compatibility guarantee.

None of it has been verified against a non-X-Trans-V body.

## What is unfinished in the C0 work

- **The fallback table's meaning is unknown.** Its 27 entries decompose into a 1–9 axis and a 1–3
  axis, but nothing in Fuji's binaries names what either axis enumerates.
- **The per-generation value tables are missing.** Fuji's capability data names which encoding
  variant a body uses, but no binary contains the value-to-meaning table for any variant other than
  the one X-Trans V uses. Property codes are known for every body; correct *values* are not.
- **One property is untested by choice.** Lens Modulation Optimiser is read but never written,
  because its effect is not understood.
- **No non-X-Trans-V body has been tested at all.**

## If you are building on this

- **Assume X-Trans V.** If you are on anything else, expect to be doing original testing rather than
  following documentation. That is true for C1–C7, not only for C0.
- **Detect, do not assume.** `GetDeviceInfo` (`0x1001`) returns the camera's supported-property
  list. Check the codes you intend to use appear in it before writing anything.
- **Write only what you can map.** Sticking to `0xD190`–`0xD1A2` keeps you clear of `0xD18E`, the
  one property Fuji shipped a compatibility shim for.
- **Sequence bring-up by the table above.** On a new generation, establish the five universal
  properties first, treat the ten sometimes-absent ones as optional, and verify `0xD192` Film
  Simulation by reading back the applied simulation rather than the response code.
- **Read back after writing.** A camera can return OK without applying a value. Do not treat a
  successful response as confirmation.
- Check [tested bodies](tested-bodies.md) before assuming your body behaves like the ones here.

## Helping

The single most useful contribution right now is **C0 results from a non-X-Trans-V body** — an X-T3,
X-T4, X-Pro3, X-S10 or any X-Trans III camera. Even a clean failure is valuable, because it tells us
whether the whole block is generation-specific or only the first property.

See the [testing checklist](testing-checklist.md) for the procedure and
[tested bodies](tested-bodies.md) for the report template.
