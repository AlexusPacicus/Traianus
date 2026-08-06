# 🗺️ Traianus Logography: Master Knowledge Map

> **Canonical Index:** Unified entry point for architecture, data contracts, governance, test structure, and system audits.

---

## 📌 1. Live Documentation

* **[LEDGER.md](./LEDGER.md):** Append-only operational delta register (`Δ_n`), structural mirror of the immutable `manifold_nodes` sequence.
* **[PROJECT_IDENTITY.md](./PROJECT_IDENTITY.md):** Substrate definition, Non-Goals, official taxonomy, and fossil purge table.
* **[ARCHITECTURE.md](./architecture/ARCHITECTURE.md):** Mathematical formulation of state $S_n = (V_n, E_n, K_n)$ and transactional persistence.
* **[CONTRACTS_AND_PRISMS.md](./architecture/contracts/CONTRACTS_AND_PRISMS.md):** Pydantic Contracts (`RawDump`, `RefinedEntity`) and Zero-Trust Customs.
* **[ADR.md](./architecture/ADR/ADR.md):** *Append-only* ledger of Architecture Decision Records (ADR-001 to ADR-027).
* **Root governance:** [AGENTS.md](../AGENTS.md) (agent constitution, role matrix, mandatory proposal schema) and [TRAIANUS_AUDIT.md](../TRAIANUS_AUDIT.md) (technical audit + remediation status).
* **[IMPLEMENTATION_STATUS.md](../IMPLEMENTATION_STATUS.md):** Transparent declaration of what is implemented vs. what is R&D roadmap.

## 🗄️ 2. Exploring (historical — not referenced by live tooling)

* **Research** (`./exploring/legacy_docs/research/`): RESEARCH_HYPOTHESIS.md (Gärdenfors Conceptual Spaces, RH-0..RH-3), RESEARCH_PROGRAM.md (WP1-WP4 roadmap), NEXT_RESEARCH.md (backlog).
* **Methodology & Tests** (`./exploring/legacy_docs/development/`): METHODOLOGY.md (4-phase neuro-symbolic flow), working_tree.md, bitacora.md, TEST_OVERVIEW.md, and the 9 RFC 2119 `SPEC-*.md` normative specs consumed by `tests/meta/_spec_lib.py`.
* **Agents & Templates** (`./exploring/legacy_docs/agents/`): agents_constitution.md (13-role SRP matrix) and templates/operational_templates.md.
* **Observation** (`./exploring/legacy_docs/observation/ULPIA_OVERVIEW.md`): Layer 3 ($O_n = P_\theta(S_n)$) mathematical observation framework.
* **Code Engine** (`./exploring/legacy_docs/audit/code_engine/`): README_CODE_ENGINE.md (TridenGuard V4 Compiler Specification — 5 Radicals and 3 Physical Gates) and `triden_guard_code_engine_v4.json`.
* **Consolidations** (`./exploring/legacy_docs/consolidation/`): STATE_CONSOLIDATION_2026-08-01.md and STATE_CONSOLIDATION_2026-08-03.md.
* **Dual Boundary Pattern** (`./exploring/legacy_docs/Dual%20Boundary%20Pattern_%20Deterministic%20Execution%20via%20Binary%20Verification.md`): physical byte-level execution verification.
* **OpenCode architecture** (`./exploring/legacy_docs/opencode/opencode_architecture.md`): OpenCode repository configuration specification (agents, Zero-Trust permissions, MCP tridenguard-validator v1.2.0).
* **Root clutter** (`./exploring/root_clutter/`): copies of AGENTS.md, TRAIANUS_AUDIT.md and README_CODE_ENGINE.md from their previous root locations.

## 🧪 3. Test Structure (Spec-First)

* **`tests/conftest.py`:** Shared fixtures — `operator_token_env`, `isolate_db`, `client`, `auth_headers`, `_hermetic_model` (autouse, injects a fake encoder; the real model only enters under `@pytest.mark.model`).
* **`tests/test_substrate.py`:** Flat hermetic substrate suite — C1 self-projection exclusion (`test_c1_threshold_excludes_self_projection`), append-only revision log (`test_append_only_revision_log`), ε-edge adjacency (`test_epsilon_edges_adjacency`).
* **`tests/test_e2e.py`:** Real-model journey (`pytestmark = pytest.mark.model`) — full pipeline (ingesta → consolidation → relations).
* **`tests/test_security.py` + `tests/security/`:** Zero-Trust Gate (SEC-M-01..18) on `traianus/security/validator.py` + MCP stdio JSON-RPC server; Structured Outputs contract (SEC-M-14..18) on `traianus/security/schemas/parser.py`; Dual Boundary Gate (SEC-M-08..12); config perimeter (SEC-M-13) on `opencode.jsonc`.
* **`tests/helpers/`:** `db_factory.py` (single source of DDL), `fake_encoder.py` (L1 hermetic), `endpoint_registry.py`.
* **`tests/fixtures/nsm_axes_8.json`:** Real axes (8×384) exported for L1 tests.
* **CI:** `.github/workflows/ci.yml` — 2 jobs: hermetic (`pytest tests/ -m "not model"`, no model/offline) and real-model E2E (`pytest tests/ -m "model"` + `tools/audit_harness.py`, model cached via `actions/cache` + HF prefetch).
* **Legacy suite (archived):** the previous G1–G9 catalog, per-block skeletons, `tests/meta/` structure guardians, and `tests/afirmaciones/` claims registry were archived by the flat-suite restructure into `docs/exploring/legacy_docs/tests/` and are not referenced by live tooling.
* **[TEST_OVERVIEW.md](./exploring/legacy_docs/development/tests/TEST_OVERVIEW.md):** Archived living map of the legacy suite (measured states, bootstrap map, G1–G9 catalog, claims, meta-guardians, Spec-First contribution guide).
* **[audit_harness.py](../tools/audit_harness.py):** Hermetic empirical harness — C1 regression guard (consolidation rate in `[5%, 95%]`) over ephemeral SQLite.
* **H4 Regression (append-only):** covered live by `tests/test_substrate.py::test_append_only_revision_log` (`seq` increasing per `id`, no UPDATE/REPLACE/DELETE on nodes).

---

## 📌 4. Milestones

Operational deltas and historical milestones are recorded in the append-only
**[LEDGER.md](./LEDGER.md)**. This index does not carry history; it only references it.
