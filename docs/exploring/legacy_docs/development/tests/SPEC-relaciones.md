# SPEC — RELATIONS Block

> Normative (RFC 2119). Findings: L2 (dangling edges, WAL), ADR-014
> (multichannel spectrum), ADR-020 (schema/metric), ADR-023 (E_n/K_n).

## Scope

Relations graph `/relations` (GET/POST), edge integrity and the dimensional
schema.

## Normative requirements

- **RE-01** MUST: POST /relations creates the edge-<src>-<tgt> edge with the given state; GET /relations returns it (ADR-002).
- **RE-02** MUST: The multichannel projection spectrum is preserved on the node (ADR-014).
- **RE-03** MUST: The manifold_nodes schema includes action_potential, revision_milestone and sys_internal_timestamp (ADR-020).
- **RE-04** MUST: The registry of generics applicable to the block matches the SPEC (endpoint_registry).
- **RE-05** MUST: The block endpoints respond without 5xx or 401 with a valid token.
- **RE-07** MUST NOT: POST /relations creates dangling edges; if source or target do not exist as nodes it responds 4xx (L2).
- **RE-08** MUST: rebuild_epsilon_edges(epsilon) rebuilds E_n deterministically: (v_i, v_j) ∈ E_n iff ||v_i − v_j||₂ ≤ epsilon (ADR-023/H5).
- **RE-06** MUST: The relations E2E journey with a real model completes offline (Phase 6, @pytest.mark.model).
- **RE-09** MUST: persist_epsilon_edges(epsilon) persists E_n deterministically: writes auto-edge-<src>-<tgt> with state='auto', excludes nodes with lifecycle_state='telemetry_error', replaces only the previous auto set and preserves the manual edges (H5/H4).
