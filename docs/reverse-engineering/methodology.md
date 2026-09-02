# Reverse-engineering methodology

## String extraction

Read the DLL as raw bytes. Regex-match runs of printable ASCII (`[\x20-\x7e]{4,}`). No tooling
beyond a scripting language is needed.

**Yields:** check-code function names and internal PDB paths.

## Exported-function enumeration

Use Python's `pefile` package (`pip install pefile`). Read `IMAGE_DIRECTORY_ENTRY_EXPORT` — the
DLL header section listing every externally callable function.

**Always inspect exports via `pefile`, not a full-decompile dump.** The dump script iterates
`getFunctionsNoStubs(true)`, which by design omits stub and folded bodies. A real export can be
entirely absent from a dump while existing in the DLL.

**`pefile` also reveals aliases** — two exports sharing one address, produced by MSVC identical-code
folding. In `FTLPTP.dll`, `FTL_PTP_OpenSession` and `FTL_PTP_CloseSession` both reside at RVA
`0x1910`: one function serving two names. The export table shows this immediately; a dump cannot.

## Ghidra decompilation

Use Ghidra 12.1.3 headless (`analyzeHeadless`) with a custom Java post-script. Ghidra 12 dropped
Jython support for `.py` scripts in favor of PyGhidra. Writing the post-script as a `.java`
`GhidraScript` subclass avoids that dependency entirely.

**Run Ghidra from a short filesystem path** (e.g. `C:\ghidra\`, `C:\work\`). A deeply nested path
(e.g. under a long temp directory) causes Ghidra's internal script-bundling system (OSGi) to fail
silently, surfacing only a misleading "class could not be found" error with no compiler error in
the logs.

## Imported-function analysis

Also `pefile`, reading `IMAGE_DIRECTORY_ENTRY_IMPORT` — the header section listing what a DLL pulls
in from *other* DLLs at load time.

**Do not infer linkage from strings alone.** `XGFXAPI.dll` referencing `FTLPTP.dll` as a *string*
does not mean it is statically linked. The import table proved it is not. Decompiling the actual
`LoadLibraryA` call site confirmed runtime resolution via dynamic loading.

See [xraw-studio-sdk.md § Binary architecture](xraw-studio-sdk.md#binary-architecture).

## Full-binary decompilation

A second Java script (`DumpAllFunctions.java`) iterates `getFunctionsNoStubs(true)` to decompile
*every* function in a binary — not just named exports — and writes the output to a single text file
for `grep`/offset-based reading.

**Yields:** internal (non-exported) `CapabilityClass::ReadCapabilityFile` and its decode routine in
`XRFC.dll`, plus the `FTL_PTP_GetDevicePropValue` opcode constant in `FTLPTP.dll`. Neither is an
exported symbol.

**Large-binary performance.** `XRFC.dll` (with OpenCV statically linked: ~10k functions) is slow
but finishes in a few minutes headless. Run each binary's import → analyze → dump in its own Ghidra
project (not a shared project) to allow parallel decompilation without lock contention.

## Managed code: the `.exe` needs a different tool

**Check for a COR20 header before trusting a Ghidra dump's coverage.**
`FUJIFILM_X_RAW_STUDIO.exe` is mixed-mode C++/CLI: its `IMAGE_DIRECTORY_ENTRY_COM_DESCRIPTOR` is
present with `COMIMAGE_FLAGS_ILONLY` clear, and its CLI metadata holds ~13,200 MethodDefs. Only 858
`RUNTIME_FUNCTION` entries exist, covering about **4.5 %** of the 2.1 MB `.text` section — the rest
is CIL bytecode.

Ghidra has no CIL decompiler, so a dump of that binary looks complete while omitting almost
everything. Re-running it does not help, and linear disassembly of `.text` desynchronises within a
few instructions. Read the managed half with ILSpy, `ildasm` or dnSpy, or by parsing the ECMA-335
metadata streams directly.

A quick coverage check that catches this class of mistake:

```python
covered = sum(f.EndAddress - f.BeginAddress for f in pe.DIRECTORY_ENTRY_EXCEPTION)
# compare against the size of .text; a low ratio means the dump is not the whole story
```

**Yields:** the camera-write selector bitfield, the *Copy to CAMERA* dialog logic, and the complete
value→label maps — none of which appear in any native dump.

## Vtable resolution

**Goal:** given a virtual-method call, find the concrete function it dispatches to.

The decompiler's `ClassName::vftable` label (e.g.
`*param_1 = CCommandGetUSBSerialNumber::vftable;`) is a display-only annotation — not a real Ghidra
symbol. Looking it up via `SymbolTable.getSymbols(name)` returns nothing.

**Resolution steps:**

1. Read the constructor's actual memory references (`Instruction.getReferencesFrom()` over the
   function body) to locate the vtable's real data address.
2. Read that address as an array of 8-byte function pointers (`Memory.getLong`).
3. Resolve each pointer to a `Function` via `FunctionManager.getFunctionAt`.

**Yields:** concrete method targets behind the generic C++ virtual dispatch pattern
(`(**(code**)(*param_2+0x30))(...)`) used throughout this SDK. Resolved the `0xD36A`/`0xD36B`
battery properties and the `GetSerialNo` cache-read behavior.

See [xsdk-live-shooting-properties.md](xsdk-live-shooting-properties.md).

## Data-table resolution

The same memory-reference-then-resolve technique applies to data tables, not just vtables.

A decompiled loop indexing `(&PTR_s_something_<addr>)[i]` is a *display label* for a raw address —
same caveat as `ClassName::vftable`. Resolve the real address by tracing the memory references of
the function that builds or uses it. Read each slot with `Memory.getLong`. If a slot points at a C
string rather than a function, read that address's bytes as a string instead of calling
`FunctionManager.getFunctionAt`.

**Yields:** the `FTLPTPIP.dll` entry in a 2-element string-pointer table alongside `FTLPTP.dll`. A
flat text search for `"FTLPTPIP"` over the decompiled output missed it entirely — the name only
exists as *data*, never as a literal argument at a call site.

## Cipher-routine verification

Reimplement any recovered cipher standalone. Run it against the real file before trusting it.
Reading the decompiled algorithm is not sufficient — a routine can look correct and still be subtly
wrong.

Diff output byte-for-byte against expected plaintext. For `XRFC.DAT` the expected opening is
`<?xml version=`, making an incorrect decode obvious in the first eight bytes.
