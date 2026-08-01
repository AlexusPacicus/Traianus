# SPEC — CONSOLIDATION Block

> Normative (RFC 2119). Findings: C1 (self-calibrated threshold), M7 (404),
> H4 (append-only), ADR-022 (dual key), ADR-025#1.

## Scope

Dual-key consolidation `/nodos/{id}/consolidar`, critical-threshold
self-calibration and the append-only revision log.

## Normative requirements

- **CO-01** MUST: Consolidating an existing node returns SUCCESS with new_state in {consolidated, incubating} and a coherent dual key (ADR-022).
- **CO-02** MUST: auto_calibrate_critical_threshold excludes the self-projection (j != i); with a one-hot basis the threshold is 0.0 (C1).
- **CO-03** MUST: Consolidating a nonexistent node responds 404, not a false SUCCESS (M7).
- **CO-04** MUST: Consolidating without an ethical_key responds 422 and leaves the state intact.
- **CO-05** MUST: With ethical_key=False the state remains incubating (ADR-022).
- **CO-11** MUST: ADR-022 key symmetry: neither the Topological nor the Ethical key has unilateral authority — with the ethical key but without the topological key (variance < threshold) the state remains incubating.
- **CO-06** MUST: Consolidating INSERTS a new revision with increasing seq (append-only, H4).
- **CO-07** MUST NOT: The production code uses UPDATE/REPLACE/DELETE over manifold_nodes (H4).
- **CO-08** MUST: The registry of generics applicable to the block matches the SPEC (endpoint_registry).
- **CO-09** MUST: The block endpoints respond without 5xx or 401 with a valid token.
- **CO-10** MUST: The consolidation E2E journey with a real model completes offline (Phase 6, @pytest.mark.model).
- **CO-12** MUST: Consolidating a node rebuilds and persists E_n (auto-edge-* edges with state='auto') over the current MAX(seq) revisions, without altering the manual edge-* edges (H5/ADR-023).
