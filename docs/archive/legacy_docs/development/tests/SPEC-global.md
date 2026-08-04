# SPEC — Traianus Global Invariants

> Normative (RFC 2119). Grounding: docs/architecture/ADR/ADR.md:131 —
> "Integration test suites must validate these five invariants on every
> build pipeline." / TRAIANUS_AUDIT.md:35 — "making the claims match the
> code".

## Scope

Invariants that apply to ALL blocks (ingesta, consolidacion, relaciones,
mutacion, observabilidad, bootstrap). The generic G1–G9 catalog is
parameterized per block via `tests/helpers/endpoint_registry.py`.

## Normative requirements

- **G1** MUST: Every route that mutates state or exposes sensitive observability requires the operator token; without a valid token it responds 401 (H3, fail-closed).
- **G2** MUST NOT: The CORS policy uses the "*" wildcard with credentials; the allowed origins are explicitly enumerated (H3).
- **G3** MUST: Every handler that opens the database runs PRAGMA journal_mode=WAL before operating (L2).
- **G4** MUST NOT: A persistence/database failure returns a synthetic 200; it propagates a noisy 5xx (H1/M5).
- **G5** MUST: Node history is append-only: every transition INSERTS a revision with increasing seq; UPDATE/REPLACE/DELETE over manifold_nodes is prohibited (H4/ADR-025#1).
- **G6** MUST: The encoder is built with local_files_only=True and HF_HUB_OFFLINE=1; no network downloads at runtime (M3).
- **G7** MUST: Given the same state and the same inputs, the projections and the resulting state are identical (M1).
- **G8** MUST: Pydantic contracts validate rigidly; the glyph (toon_factor) is a single character (ADR-007); action_potential derives from the spectrum without magic constants (ADR-005/M6).
- **G9** MUST: The TridenGuard gate blocks fragments with fetch/axios/urllib.request/import requests and verifies literal grounding (AGENTS.md §2.3).
- **G10** MUST: With a real model and realistic NSM geometry, the dual-key consolidation rate does not degenerate: it stays in [5%, 95%] (C1 guard, harness port).
- **INV1** MUST: State evolution is monotonically append-only (ADR-025#1).
- **INV2** MUST: Observing (GET) produces zero side effects (ADR-025#2).
- **INV3** MUST: The external provider has no topology execution rights; the control plane operates only on L2 vectors (ADR-025#3).
- **INV4** MUST: Consolidation requires the concurrence of both keys; without an explicit Ethical Key the state is never consolidated (ADR-022/ADR-025#4).
- **INV5** MUST: The same input produces the same stored vector byte for byte (ADR-025#5).
