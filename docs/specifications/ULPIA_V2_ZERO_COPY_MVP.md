# Ulpia V2 Zero-Copy MVP (Draft Specification)

> **Status:** Draft, not normative. Door to Normative opens only on a GREEN verification (skill `spec-first`).
> **Decision fixed here:** `src=0, dst=0` reserved for the node-batch MVP. The batch-index
> alternative was rejected for MVP (see §1): it overloads `src` with an ephemeral ordinal
> that V2-full must reinterpret as an edge endpoint.

## 1. Scope

Governs the read-only V2 packet that the client (RefApp-01, own repository since LEDGER seq 56 —
`README.md:121-124`, `docs/LEDGER.md:1721-1738`) packs from `GET /spatial`
(`traianus/app.py:804-863`) without any motor change.

Explicit non-goals: no edit to `traianus/geometry/zero_copy.py:25` v1 (`<6f32s8x`); no new
endpoint; no binary ingest; no WebGL UBO `std140` direct mapping; no new physics
(`tau`, `theta_g`, `spiral_step`, `sigma_d`/`Cmax`, bitmask semantics stay out); no second
dipole (`z` frozen per `docs/adrs/ADR-026-spatial-render-calibration.md` §2.1).

`src/dst` choice: `00` reserved (this SPEC) vs batch index (rejected). With `00`, node identity
stays in the JS sidecar (`string[]` in the order `GET /spatial` serves, already sorted by id —
`traianus/app.py:863`); picking resolves via `instanceID -> sidecar[i]`. With an index, the pack
step would need the sorted id list as input, the golden bytes would carry `src=i` LE, the decode
would return an ordinal, and the docs would have to declare it ephemeral per batch (never
persisted, never sent back, full repack on membership change) — semantic debt for zero saved
lookups, since the label array is needed for tooltips either way.

## 2. Normative Requirements

- Packet layout MUST be 16 DWORDs / 64 bytes, little-endian, struct `<IIIIfffffffffffI`
  (4 `I` + 11 `f` + 1 `I`). The 12-`f` spelling (`<IIIIffffffffffffI`, 68 bytes) MUST NOT be used.
- `0x00 magic` MUST be `0x54524132` (`TRA2`). `0x04 bitmask` MUST be `0x00000000`.
  `0x08 src` and `0x0C dst` MUST be `0`; consumers MUST ignore both DWORDs.
- Block 1 (`tau`, `d_esc`, `lambda`, `rotation`) MUST be `0.0` (reserved, pending instrument audit).
  `GET /spatial` exposes `{x, y, z, l, c, h}`, not raw polar channels, and the client holds no
  384D basis to recompute them.
- Block 2 MUST be `x=nodes[i].x`, `y=nodes[i].y`, `z=nodes[i].z` (the API serves `0.0`),
  `step=0.0`, with `x, y` from the frozen epoch frame (`traianus/geometry/spatial_observables.py:171-187`).
- Block 3 MUST be `l=nodes[i].l`, `c=nodes[i].c`, `h=nodes[i].h`, `crc32` IEEE over bytes 0–59.
- Decode MUST use `DataView` with explicit little-endian reads, never overlapping typed-array views.
- Transport MUST be one `ArrayBuffer(N*64)` per corpus (n=2221 → ~142 KB), single upload, packed
  in serve order. Direction MUST be server-to-client read-only (`mode=ro`); the motor perimeter
  (`traianus/app.py:85` enumerated CORS, `traianus/app.py:131` ingress allowlist,
  `traianus/app.py:148` operator token) is unchanged.

## 3. Mathematical Formulation

State $S_n=(V_n,E_n)$, observation $O_n=P_\theta(S_n)$. The MVP packet of node $i$ is the tuple
$p_i=(m,b,s,d,\tau,e,\lambda,\rho,x,y,z,t,l,c,h,k)$ with
$(m,b,s,d)=(0\mathrm{x}54524132,0,0,0)$, $(\tau,e,\lambda,\rho,t)=(0,0,0,0,0)$,
$(x,y,z,l,c,h)$ the frozen-frame observables, $k=\mathrm{CRC32}(p_i[0{:}60])$.
The batch is the concatenation $B=p_0\Vert\cdots\Vert p_{N-1}$.

## 4. Invariants

- `block_size == 64`; `magic == 0x54524132`; `bitmask == 0`; `src == 0 and dst == 0`.
- `z == 0.0`; `l, c, h` in `[0,1]`; `x, y` in `[-1,1]` (frozen-frame clip).
- CRC over bytes 0–59 detects any single-bit flip of the golden vectors.
- v1 contract byte-identical (`traianus/geometry/zero_copy.py:25`, `tests/unit/geometry/test_zero_copy_exporter.py`).
- No `traianus/`, `tests/`, `AGENTS.md` edit accompanies this SPEC.

## 5. Verification

- RefApp-01 (owner of the implementation): `packSpatialBatch`/`unpack` round-trip on two fixed
  `GET /spatial` samples → expected hex; `byteLength == 64*N`; `z == 0`; range asserts; CRC
  catches a 1-bit flip; `npm run typecheck && npm run build` green.
- This repository: `pytest tests/unit/test_check_doc_citations.py -q` green (no `TRACEABILITY.md`
  touch); hermetic suite `pytest tests/ -m "not model" -q` green by no-touch (AGENTS.md 1.4).
  CI needs no new partition (AGENTS.md 1.6): docs-only, existing hermetic + model jobs stand.
