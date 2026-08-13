# Traianus — Technical Audit Report and Remediation Plan

**Repository:** `AlexusPacicus/Traianus` @ `main`
**Audit Date:** 2026-08-13
**Commit Hash:** `git rev-parse HEAD`
**Scope:** Full audit — code, tests, documentation, packaging, security, and the mathematics behind the claims.

**Method:** Static review + empirical execution against `all-MiniLM-L6-v2`. Every quantitative datum was measured.
**Overall Assessment:** The PoC core works. Several declared "non-negotiable" invariants were contradicted by the code; all have been remediated (see status below).

> **Hallazgos detallados:** Véase las secciones [Hallazgos Resueltos](./AUDIT.md#hallazgos-resueltos) y [Hallazgos Abiertos](./AUDIT.md#hallazgos-abiertos) arriba.

---

## Severity Legend

| Severity | Meaning |
|---|---|
| 🔴 **Critical** | Core functionality broken or real security exposure. |
| 🟠 **High** | Incorrect/misleading behavior, data loss, or claim contradicted by code. |
| 🟡 **Medium** | Correctness/reproducibility/packaging defects. |
| 🔵 **Low** | Quality, hygiene, consistency. |
| ⚪ **Info** | Documentation/positioning calibration. |

---

## Hallazgos Resueltos

Los siguientes hallazgos han sido cerrados con corrección de código y verificación por prueba determinista o el harma empírica:

| ID | Título | Status |
|---|---|---|
| C1 | Consolidation gate dead code (threshold scale mismatch) | ✅ Resolved |
| H1 | `/ingesta` swallows errors, returns fake 200 | ✅ Resolved |
| H2 | Ingress firewall is denylist, not allowlist | ✅ Resolved |
| H3 | CORS wildcard + credentials, no auth | ✅ Resolved |
| M3 | Offline claim false on first run | ✅ Resolved |
| M4 | Packaging misconfigured | ✅ Resolved |
| M6 | Magic number `*10.0` contradicts ADR-005 | ✅ Resolved |

## Hallazgos Abiertos

Los siguientes hallazgos permanecen abiertos y requieren atención adicional:

| ID | Título | Status |
|---|---|---|
| M1 | "Bitwise determinism" not guaranteeable — redefinido | 🟡 Open |
| M2 | "<1ms" claim false (~13ms measured) | 🟡 Open |
| M8 | No CI, unpinned flake.nix | 🟡 Open |
| L1 | Tests don't test real system | 🔵 Open |
| L3 | Mixed languages in API | 🔵 Open |
| L4 | NSM basis near-duplicates | 🔵 Open |

---

## Remediation Status

Resolution criterion: fix implemented in code **and** verified by a deterministic test or the empirical harness (`tools/audit/audit_harness.py`).

| ID | Status | Evidence |
|---|---|---|
| C1 | ✅ Resolved | `auto_calibrate_critical_threshold()` excludes self-projection; harness green; regression `test_auto_calibrate_excludes_self_projection`. |
| H1 | ✅ Resolved | `/ingesta` fails loudly with `503`; regression `test_ingesta_returns_503_on_persistence_failure`. |
| H2 | ✅ Resolved | `ALLOWED_INGRESS_TYPES = {"text/plain"}` allowlist; 415 otherwise; regressions `test_ingesta_endpoint_rejects_non_plain_text_payloads`. |
| H3 | ✅ Resolved | CORS enumerated; operator token on mutating routes; regressions `test_cors_origins_are_enumerated_no_wildcard`. |
| H4 | ✅ Resolved | `manifold_nodes` + `manifold_edges` are append-only revision logs `(id, seq)`; tests `tests/genericos/test_g5_append_only.py`. |
| H5 | ✅ Resolved | `_compute_epsilon_edges`/`rebuild_epsilon_edges`/`persist_epsilon_edges` implemented; ε-adjacency persisted as `auto-edge-*`. |
| M3 | ✅ Resolved | `HF_HUB_OFFLINE=1` + `local_files_only=True`; regressions `test_encoder_constructed_offline_local_files_only`. |
| M4 | ✅ Resolved | Real package `traianus/`; `pyproject.toml` with `traianus-bootstrap`; quickstart documented. |
| M5 | ✅ Resolved | `/nodos` returns 5xx; `/telemetry` requires token; regressions `test_nodos_returns_500_on_db_error`. |
| M6 | ✅ Resolved | `action_potential = float(variance)` without `*10.0`; regression `test_action_potential_is_variance_not_scaled`. |
| M7 | ✅ Resolved | Consolidation INSERTS revision; missing node → 404; regression `test_consolidar_missing_node_returns_404`. |
| L2 | ✅ Resolved | Dangling edges rejected (404); edges append-only; WAL everywhere; tests `tests/genericos/test_g3_wal.py`. |
| L5 | ✅ Resolved | `projections_json` derives from `validated_entity.projections` (Pydantic contract is single source of truth). |
| L6 | ✅ Resolved | `dim_in > dim_db` rejected with HTTP 422 / `ValueError`; tests `tests/afirmaciones/test_cl_i62_dimension_provider.py`. |

**Open items:** M1, M2, M8, L1, L3, L4 — see [findings](./AUDIT.md#hallazgos-abiertos) for details and recommended fixes.

---

## Key Invariants (Agent Reference)

Before refactoring `traianus/app.py`, verify these hold:

1. **C1 invariant:** `auto_calibrate_critical_threshold()` MUST exclude self-projection (`i ≠ j`).
2. **Append-only:** `manifold_nodes` and `manifold_edges` use `(id, seq)` — never UPDATE/DELETE.
3. **Lifecycle states:** `pending_approval | incubating | consolidated | telemetry_error` (CHECK constraint).
4. **Dual-key consolidation:** `Consolidated ⟺ (σ² ≥ θ_dyn) ∧ (EthicalKey == True)`.
5. **Epoch provenance:** active seed tagged `epoch_provenance = 'PROSTHETIC_NSM_V1'`.

---

*For measured data, code-level evidence, and fix implementations, see the [Hallazgos Abiertos](./AUDIT.md#hallazgos-abiertos) section above.*
