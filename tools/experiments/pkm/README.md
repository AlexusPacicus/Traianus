# PKM — Portable Knowledge Management (NotebookLM origin)

> **Origin:** experimentation from a NotebookLM notebook, intended as a
> personal-knowledge-management packaging layer. It was carried into the
> Ulpia 3D render path by mistake.

**This is NOT a subset of the Traianus substrate contract.** The backend
(`traianus/`) stores the 384D semantic vectors as **float64 blobs**
(`astype(float64).tobytes()`, 3072 B) and exposes semantic projections via
`/nodos` → `projections_json`. The 64-byte layout here is a **portable
local-first packaging format** used only for the `.purgativa` stream and the
clinical/somatic sanitization regex.

## Scope

- `purgative_core.py` — 64-byte `ffffff32s8x` record layout, OKLCH mapping,
  `sanitize_somatic_flow`, Arrhenius/MTBF thermodynamics, H0 pulsation probe.
- Client-side equivalent lives under `frontend/src/pkm/` (`bin.ts`,
  `storage.ts`, `exodus.ts`) for `.purgativa` export/import as an optional
  data-port utility independent of the render loop.

## Invariant

The Ulpia 3D render and the `useUlpiaStore` must derive node geometry from
**semantic projections (`projections_json` → XYZ/LCH)**, not from this 64B
struct. This module is a standalone data-portability concern.
