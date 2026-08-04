# 🗺️ Traianus Logography: Master Knowledge Map

> **Canonical Index:** Unified entry point for architecture, data contracts, governance, test structure, and system audits.

---

## 📌 1. Live Documentation

* **[PROJECT_IDENTITY.md](./PROJECT_IDENTITY.md):** Substrate definition, Non-Goals, official taxonomy, and fossil purge table.
* **[ARCHITECTURE.md](./architecture/ARCHITECTURE.md):** Mathematical formulation of state $S_n = (V_n, E_n, K_n)$ and transactional persistence.
* **[CONTRACTS_AND_PRISMS.md](./architecture/contracts/CONTRACTS_AND_PRISMS.md):** Pydantic Contracts (`RawDump`, `RefinedEntity`) and Zero-Trust Customs.
* **[ADR.md](./architecture/ADR/ADR.md):** *Append-only* ledger of Architecture Decision Records (ADR-001 to ADR-027).
* **Root governance:** [AGENTS.md](../AGENTS.md) (agent constitution, role matrix, mandatory proposal schema) and [TRAIANUS_AUDIT.md](../TRAIANUS_AUDIT.md) (technical audit + remediation status).
* **[IMPLEMENTATION_STATUS.md](../IMPLEMENTATION_STATUS.md):** Transparent declaration of what is implemented vs. what is R&D roadmap.

## 🗄️ 2. Archive (historical — not referenced by live tooling)

* **Research** (`./archive/legacy_docs/research/`): RESEARCH_HYPOTHESIS.md (Gärdenfors Conceptual Spaces, RH-0..RH-3), RESEARCH_PROGRAM.md (WP1-WP4 roadmap), NEXT_RESEARCH.md (backlog).
* **Methodology & Tests** (`./archive/legacy_docs/development/`): METHODOLOGY.md (4-phase neuro-symbolic flow), working_tree.md, bitacora.md, TEST_OVERVIEW.md, and the 9 RFC 2119 `SPEC-*.md` normative specs consumed by `tests/meta/_spec_lib.py`.
* **Agents & Templates** (`./archive/legacy_docs/agents/`): agents_constitution.md (13-role SRP matrix) and templates/operational_templates.md.
* **Observation** (`./archive/legacy_docs/observation/ULPIA_OVERVIEW.md`): Layer 3 ($O_n = P_\theta(S_n)$) mathematical observation framework.
* **Code Engine** (`./archive/legacy_docs/audit/code_engine/`): README_CODE_ENGINE.md (TridenGuard V4 Compiler Specification — 5 Radicals and 3 Physical Gates) and `triden_guard_code_engine_v4.json`.
* **Consolidations** (`./archive/legacy_docs/consolidation/`): STATE_CONSOLIDATION_2026-08-01.md and STATE_CONSOLIDATION_2026-08-03.md.
* **Dual Boundary Pattern** (`./archive/legacy_docs/Dual%20Boundary%20Pattern_%20Deterministic%20Execution%20via%20Binary%20Verification.md`): physical byte-level execution verification.
* **OpenCode architecture** (`./archive/legacy_docs/opencode/opencode_architecture.md`): OpenCode repository configuration specification (agents, Zero-Trust permissions, MCP tridenguard-validator v1.2.0).
* **Root clutter** (`./archive/root_clutter/`): copies of AGENTS.md, TRAIANUS_AUDIT.md and README_CODE_ENGINE.md from their previous root locations.

## 🧪 3. Test Structure (Spec-First)

* **`tests/conftest.py`:** Shared fixtures — `operator_token_env`, `isolate_db`, `client`, `auth_headers`, `_hermetic_model` (autouse, excludes `@pytest.mark.model`).
* **`tests/helpers/`:** `db_factory.py` (single source of DDL), `fake_encoder.py` (L1 hermetic), `endpoint_registry.py` (G1–G9 catalog × blocks).
* **`tests/genericos/`:** G1–G9 parameterized catalog by block (Phase 1) + ADR-025 invariants.
* **`tests/bloques/{ingesta,consolidacion,relaciones,mutacion,observabilidad,bootstrap}/`:** Per-block skeleton — `test_genericos`, `test_especificos`, `test_e2e` (Phases 2, 5, and 6).
* **`tests/meta/`:** Structure guardians (`_spec_lib.py` + `test_guardianes_estructura.py`): SPECs parse (from `docs/archive/legacy_docs/development/tests/`), normative headers, 1:1 MUST↔test traceability, no orphans.
* **`tests/afirmaciones/`:** Documentary claims (Phase 4) — `claims_registry.py` (CL-C41, CL-I5, CL-I61, CL-I62, CL-R1, CL-R2, CL-WP1, CL-TR1, CL-LIT1) with states ACTIVE/RED/WP; **CL-I62 ACTIVE** (CODE_FIX applied: provider dimension > basis → HTTP 422; verified by `test_afirmaciones_CL_I62_*` in `test_cl_i62_dimension_provider.py`).
* **`tests/security/`:** Zero-Trust Gate (SEC-M-01..18) on `traianus/security/validator.py` (Phase 5) + MCP stdio JSON-RPC server.
* **`tests/security/test_structured_outputs.py`:** Structured Outputs contract (SEC-M-14..18) — `build_response_format` strict json_schema shape/invariants, ordered `parse_proposal_json` pipeline, `JSONParsingError` on repaired-incomplete JSON, `parse_proposal` validation, and validator `INVALID_JSON`/safety-gate preservation.
* **`tests/security/test_tridenguard_dual_boundary.py`:** Dual Boundary Gate (SEC-M-08..12) — canonical path containment (`..` traversal and symlink escapes via `Path.resolve(strict=True)` + `is_relative_to`), `\x00` sanitization (raw and JSON-escaped `\u0000`), 21-token network denylist, UTF-8 binary subsequence grounding over `read_bytes()`, and silent denial (no path/OS leakage).
* **`tests/security/test_opencode_permissions.py`:** Config perimeter (SEC-M-13) — the `opencode.jsonc` bash permission matrix MUST NOT grant a `git *` wildcard allow; only explicit read/inspection subcommands (status, diff, log, show, rev-parse, grep, blame, ls-files, add) MAY be allowed; deny primitives persist.
* **`tests/e2e/`:** C1 Guard (G10) ported from harness — consolidation rate in [5%, 95%] with real model (Phase 6); per-block `test_e2e.py` implement `@pytest.mark.model` journeys.
* **`tests/fixtures/nsm_axes_8.json`:** Real axes (8×384) exported for L1 tests.
* **CI:** `.github/workflows/ci.yml` — 2 jobs: hermetic (`pytest tests/ -m "not model"`, no model/offline) and real-model E2E (`pytest tests/ -m "model"` + `tools/audit_harness.py`, model cached via `actions/cache` + HF prefetch).
* **[TEST_OVERVIEW.md](./archive/legacy_docs/development/tests/TEST_OVERVIEW.md):** Archived living map of the suite (measured states, bootstrap map, G1–G9 catalog, claims, meta-guardians, Spec-First contribution guide).
* **[audit_harness.py](../tools/audit_harness.py):** Hermetic empirical harness — C1 regression guard (consolidation rate in `[5%, 95%]`) over ephemeral SQLite.
* **H4 Regression (append-only):** `tests/genericos/test_g5_append_only.py` + `tests/bloques/consolidacion/test_especificos.py` — append-only revision log (`seq` increasing per `id`, no UPDATE/REPLACE/DELETE on nodes).

---

## 📌 Milestones

### [2026-08-04] — OSS Readiness Fase 0 closure (TA-03 / TA-04 / TA-05)

- **TA-03 (Structured Outputs templates):** `docs/templates/operational_templates.md` moved to
  `docs/agents/templates/operational_templates.md` and redesigned as the Structured Outputs
  contract (Template 1 via `build_response_format` + strict json_schema, DoD table, legacy mode).
- **TA-04:** `docs/agents/agents_constitution.md` created as the primary document of the
  `docs/agents/` node (13-role SRP matrix).
- **TA-05:** `AGENTS.md` restored to clean markdown (zero `MD`/`+ 1`/`[cite:` artifacts),
  includes `@plan-architect`, references `traianus/security/schemas/proposals.py` + `build_response_format`;
  9 new agent files added to `.opencode/agents/` (14 total).
- **Normative additions:** SEC-M-14..SEC-M-18 in `SPEC-security.md` (Structured Outputs
  contract), `traianus/security/schemas/parser.py` (`parse_proposal_json`/`parse_proposal`),
  `tests/security/test_structured_outputs.py`.
- **Verification:** hermetic suite 208 passed / 2 skipped / 7 deselected; `tests/meta` 13 passed.
