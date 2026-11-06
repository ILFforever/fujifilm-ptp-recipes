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

**Present on all configurations, supported set varies by generation.** The encoding itself is stable
— value *N* means the same thing on every body — so a value an older body does not support is
rejected as out of range rather than misinterpreted. Per-variant value lists are in
[xrfc-value-tables.md](reverse-engineering/xrfc-value-tables.md).

| Code | Property | How it varies |
|---|---|---|
| `0xD192` | Film Simulation | 6 variants, strictly nested `1`–`15` … `1`–`20` |
| `0xD19D` | Highlight Tone | Older bodies whole steps only; newer add half steps |
| `0xD19E` | Shadow Tone | Same as Highlight Tone |
| `0xD199` | White Balance | Newer bodies add Auto White Priority and Auto Ambience Priority |
| `0xD19C` | Colour Temperature | Older bodies 31 fixed steps; **newer accept any Kelvin 2500–10000 in steps of 10** |
| `0xD195` | Grain Effect | Strength `1`–`3` on every body; the variant decides whether a *size* axis exists, so `4` and `5` are unreachable on older bodies |
| `0xD1A1` | High ISO NR | **No actual difference** — both variants hold identical values |

Note that two of these do not fit the "older bodies accept fewer values" summary. Colour Temperature
gets *less* restrictive on newer bodies by switching from a list to a continuous range, and High ISO
NR does not vary at all despite being recorded as having two variants.

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

`0xD192` Film Simulation is present on every configuration and carries six variants, but they form a
strictly nested chain — `1`–`15` on the oldest bodies through `1`–`20` on the newest, each adding one
simulation, with identical numbering throughout. Value `1` is Provia everywhere. A recipe from a
newer body is therefore rejected as out of range on an older one, not applied as a different
simulation.

`0xD18E` is the sole property that is both heavily fragmented (7 encodings) and frequently absent,
which is consistent with it being the only one Fuji shipped a compatibility shim for.

**Scope of this evidence.** The source is X RAW STUDIO's tether-RAW conversion capability table: the
feature set Fuji's application offers for a given body in that workflow. It is Fuji's own data and is
strong evidence of camera support, but it is not a direct statement about whether a PTP property
exists on the wire. It is a risk ranking, not a compatibility guarantee.

None of it has been verified against a non-X-Trans-V body.

## What is unfinished in the C0 work

- **Which bodies actually need the fallback.** The table's axes are now resolved — row is image size
  (L/M/S), column is aspect ratio — but no body has been observed triggering the fallback.
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
  properties first, treat the ten sometimes-absent ones as optional, and clamp values on the
  range-varying properties to what the body's generation accepts — the per-variant lists are in
  [xrfc-value-tables.md](reverse-engineering/xrfc-value-tables.md).
- **Read back after writing.** A camera can return OK without applying a value. Do not treat a
  successful response as confirmation.
- Check [tested bodies](tested-bodies.md) before assuming your body behaves like the ones here.

## Helping

The single most useful contribution right now is **C0 results from a non-X-Trans-V body** — an X-T3,
X-T4, X-Pro3, X-S10 or any X-Trans III camera. Even a clean failure is valuable, because it tells us
whether the whole block is generation-specific or only the first property.

See the [testing checklist](testing-checklist.md) for the procedure and
[tested bodies](tested-bodies.md) for the report template.
