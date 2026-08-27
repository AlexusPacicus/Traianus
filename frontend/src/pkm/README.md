# PKM — Portable Knowledge Management (frontend)

Client-side counterpart of `tools/experiments/pkm/`. NotebookLM-origin,
portable `.purgativa` data packaging. **Independent of the render loop.**

- `bin.ts` — 64-byte `ffffff32s8x` record layout, UTF-8-safe id truncation,
  `sanitizeSomaticFlow`.
- `sanitize.ts` — `CLINICAL_REGEX` single source.
- `storage.ts` — IndexedDB contiguous 64B store.
- `exodus.ts` — `.purgativa` export/import utility (optional data port).

## Contract boundary

The Ulpia 3D canvas and `useUlpiaStore` derive node geometry from semantic
projections (`projections_json` → XYZ/LCH) and **must not** read/write the
64B struct on the hot path. This module is a standalone portability concern.
