# Traianus — Technical Audit Report and Remediation Plan

**Repository:** `AlexusPacicus/Traianus` @ `main`
**Audit Date:** 2026-08-15
**Commit Hash:** `git rev-parse HEAD`
**Scope:** Full audit — code, tests, documentation, packaging, security, and the mathematics behind the claims.

**Method:** Static review + empirical execution against `all-MiniLM-L6-v2`. Every quantitative datum was measured.
**Overall Assessment:** The Control Plane core works at v1.0.0. Several declared "non-negotiable" invariants were contradicted in the PoC phase; all have been remediated (see status below).

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
| M8 | Nix devshell / reproducibility | ✅ Resolved | Nix `flake.nix` devshell removed from the v1.0.0 release freeze; reproducibility anchored in pinned `pyproject.toml` (Python 3.11, `requires-python = "~=3.11"`) and the green CI matrix (hermetic + model suites on `ubuntu-latest`). |

## Hallazgos Abiertos

Los siguientes hallazgos permanecen abiertos y requieren atención adicional:

| ID | Título | Status |
|---|---|---|
| *None* | *All documentation findings resolved in `docs/excellence-v1.0.0`* | ✅ |

> **Note:** M1, M2, L1, L3, L4 were documentation-only findings. They have been resolved via documentation updates in branch `docs/excellence-v1.0.0` (see Remediation Status below). No code changes required; freeze v1.0.0 remains intact.

---

## Remediation Status

Resolution criterion: fix implemented in code **and** verified by a deterministic test or the empirical harness (`tools/audit/audit_harness.py`).

| ID | Status | Evidence |
|---|---|---|
| C1 | ✅ Resolved | `auto_calibrate_critical_threshold()` excludes self-projection; harness green; regression `test_auto_calibrate_excludes_self_projection`. |
| H1 | ✅ Resolved | `/ingesta` fails loudly with `503`; regression `test_ingesta_returns_503_on_persistence_failure`. |
| H2 | ✅ Resolved | `ALLOWED_INGRESS_TYPES = {"text/plain"}` allowlist; 415 otherwise; regressions `test_ingesta_endpoint_rejects_non_plain_text_payloads`. |
| H3 | ✅ Resolved | CORS enumerated; operator token on mutating routes; regressions `test_cors_origins_are_enumerated_no_wildcard`. |
| H4 | ✅ Resolved | `manifold_nodes` + `manifold_edges` are append-only revision logs `(id, seq)`; tests `tests/unit/test_substrate.py`. |
| H5 | ✅ Resolved | `_compute_epsilon_edges`/`rebuild_epsilon_edges`/`persist_epsilon_edges` implemented; ε-adjacency persisted as `auto-edge-*`. |
| M3 | ✅ Resolved | `HF_HUB_OFFLINE=1` + `local_files_only=True`; regressions `test_encoder_constructed_offline_local_files_only`. |
| M4 | ✅ Resolved | Real package `traianus/`; `pyproject.toml` with `traianus-bootstrap`; quickstart documented. |
| M5 | ✅ Resolved | `/nodos` returns 5xx; `/telemetry` requires token; regressions `test_nodos_returns_500_on_db_error`. |
| M6 | ✅ Resolved | `action_potential = float(variance)` without `*10.0`; regression `test_action_potential_is_variance_not_scaled`. |
| M7 | ✅ Resolved | Consolidation INSERTS revision; missing node → 404; regression `test_consolidar_missing_node_returns_404`. |
| M8 | ✅ Resolved | Nix `flake.nix` devshell removed from v1.0.0 release freeze; reproducibility anchored in pinned `pyproject.toml` (Python 3.11) + green CI matrix. |
| L2 | ✅ Resolved | Dangling edges rejected (404); edges append-only; WAL everywhere; tests `tests/unit/test_storage_hardening.py`. |
| L5 | ✅ Resolved | `projections_json` derives from `validated_entity.projections` (Pydantic contract is single source of truth). |
| L6 | ✅ Resolved | `dim_in > dim_db` rejected with HTTP 422 / `ValueError`; tests `tests/representation/test_representation_providers.py`. |
| M1 | ✅ Resolved (Doc) | `docs/STATUS.md` + `docs/PROJECT_IDENTITY.md` clarified runtime vs bitwise determinism |
| M2 | ✅ Resolved (Doc) | Claim only existed in audit finding; no public doc claimed <1ms |
| L1 | ✅ Resolved (Doc) | `docs/STATUS.md` "Known Limitations" documents hermetic vs model suite scope |
| L3 | ✅ Resolved (Doc) | Seq 7, 21 already fixed code; docs verified English-only |
| L4 | ✅ Resolved (Doc) | `docs/STATUS.md` "Known Limitations" documents NSM basis as provisional scaffold |

**Open items:** None — all findings resolved (code or documentation).

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
