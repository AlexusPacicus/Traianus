# 🗺️ Traianus Logography: Master Knowledge Map

> **Canonical Index:** Unified entry point for architecture, research, methodology, data contracts, and system audits.

---

## 📐 1. Identity (`docs/identity/`)
* **[PROJECT_IDENTITY.md](./identity/PROJECT_IDENTITY.md):** Substrate definition, Non-Goals, official taxonomy, and fossil purge table.

## 🔬 2. Research (`docs/research/`)
* **[RESEARCH_HYPOTHESIS.md](./research/RESEARCH_HYPOTHESIS.md):** Grounding in Conceptual Spaces (Gärdenfors) and Hypotheses (RH-0 to RH-3).
* **[RESEARCH_PROGRAM.md](./research/RESEARCH_PROGRAM.md):** R&D Roadmap (WP1 - WP4) and multi-provider benchmarking matrix.
* **[NEXT_RESEARCH.md](./research/NEXT_RESEARCH.md):** Exploration and future research backlog.

## 🏗️ 3. Architecture & Engineering (`docs/architecture/`)
* **[Project_architecture.md](./architecture/Project_architecture.md):** Mathematical formulation of state $S_n = (V_n, E_n, K_n)$ and transactional persistence.
* **[CONTRACTS_AND_PRISMS.md](./architecture/contracts/CONTRACTS_AND_PRISMS.md):** Pydantic Contracts (`RawDump`, `RefinedEntity`) and Zero-Trust Customs.
* **[ADR.md](./architecture/ADR/ADR.md):** *Append-only* ledger of Architecture Decision Records (ADR-001 to ADR-027).
* **[opencode_architecture.md](./architecture/opencode_architecture.md):** OpenCode repository configuration specification (agents, Zero-Trust permissions, MCP tridenguard-validator v1.2.0).

## 👁️ 3b. Observation (`docs/observation/`)
* **[ULPIA_OVERVIEW.md](./observation/ULPIA_OVERVIEW.md):** Native mathematical observation framework — Layer 3 ($O_n = P_\theta(S_n)$), ADR-022/ADR-024 projection independence, zero-side-effect reads, and implementation status.

## ⚙️ 4. Development & Methodology (`docs/development/`)
* **[METHODOLOGY.md](./development/methodology/METHODOLOGY.md):** Specification of the 4-phase neuro-symbolic flow (Analysis, ASD, TDD Specification, and Red/Green/Refactor Cycle).
* **[working_tree.md](./development/working_tree.md):** Conceptual consolidation and ontological decisions of the working tree.
* **[bitacora.md](./development/bitacora.md):** Historical record and consolidated changelog.
* **Test Specifications (`./development/tests/`):** SPEC-template.md and SPEC-{global, ingestion, consolidation, relations, mutation, observability, bootstrap, claims, security}.md — RFC 2119 normative spec that each test file references in its header (Normative/Coverage).

## 🛡️ 5. Audit & Neuro-Symbolic Firewall (`docs/` and `tools/`)
* **[STATE_CONSOLIDATION_2026-08-01.md](./STATE_CONSOLIDATION_2026-08-01.md):** Consolidation of the 2026-08-01 cycle — git state, AGENTS.md invariant matrix, Doc-Drift catalog D1–D10, and routable recommendations R1–R5.
* **[STATE_CONSOLIDATION_2026-08-03.md](./STATE_CONSOLIDATION_2026-08-03.md):** Consolidation of the 2026-08-03 restoration cycle — restoration of the OpenCode governance layer (config, AGENTS.md, agents/commands/skills) from `ea43df6^`, empirical verification and findings W1–W4.
* **[Dual Boundary Pattern — Deterministic Execution via Binary Verification.md](./Dual%20Boundary%20Pattern_%20Deterministic%20Execution%20via%20Binary%20Verification.md):** Physical byte-level execution verification — path canonicalization (`Path.resolve(strict=True)`), repo-root containment (`is_relative_to`), UTF-8 binary subsequence matching over `read_bytes()`, `\x00` sanitization, and silent denial.
* **[TRAIANUS_AUDIT.md](../TRAIANUS_AUDIT.md):** Static and empirical technical audit report (Finding C1, H1–H5) + 2026-08-01 cycle remediation status.
* **[README_CODE_ENGINE.md](../README_CODE_ENGINE.md):** TridenGuard V4 Compiler Specification (5 Radicals and 3 Physical Gates).
* **[audit_harness.py](../tools/audit_harness.py):** Hermetic empirical harness — C1 regression guard (consolidation rate in `[5%, 95%]`) over ephemeral SQLite.
* **H4 Regression (append-only):** `tests/genericos/test_g5_append_only.py` + `tests/bloques/consolidacion/test_especificos.py` — append-only revision log (`seq` increasing per `id`, no UPDATE/REPLACE/DELETE on nodes).
* **Audit Sources (`./audit/`):** Harness reference material — [README_CODE_ENGINE.md](./audit/README_CODE_ENGINE.md) (compiler source, with mirror in root) and `triden_guard_code_engine_v4.json` (engine schema).

## 🧪 6. Test Structure (Spec-First)
* **`tests/conftest.py`:** Shared fixtures — `operator_token_env`, `isolate_db`, `client`, `auth_headers`, `_hermetic_model` (autouse, excludes `@pytest.mark.model`).
* **`tests/helpers/`:** `db_factory.py` (single source of DDL), `fake_encoder.py` (L1 hermetic), `endpoint_registry.py` (G1–G9 catalog × blocks).
* **`tests/genericos/`:** G1–G9 parameterized catalog by block (Phase 1) + ADR-025 invariants.
* **`tests/bloques/{ingesta,consolidacion,relaciones,mutacion,observabilidad,bootstrap}/`:** Per-block skeleton — `test_genericos`, `test_especificos`, `test_e2e` (Phases 2, 5, and 6).
* **`tests/meta/`:** Structure guardians (`_spec_lib.py` + `test_guardianes_estructura.py`): SPECs parse, normative headers, 1:1 MUST↔test traceability, no orphans.
* **`tests/afirmaciones/`:** Documentary claims (Phase 4) — `claims_registry.py` (CL-C41, CL-I5, CL-I61, CL-I62, CL-R1, CL-R2, CL-WP1, CL-TR1, CL-LIT1) with states ACTIVE/RED/WP; **CL-I62 ACTIVE** (CODE_FIX applied: provider dimension > basis → HTTP 422; verified by `test_afirmaciones_CL_I62_*` in `test_cl_i62_dimension_provider.py`).
* **`tests/security/`:** Zero-Trust Gate (SEC-M-01..12) on `tools/tridenguard_validator.py` (Phase 5) + MCP stdio JSON-RPC server.
* **`tests/security/test_tridenguard_dual_boundary.py`:** Dual Boundary Gate (SEC-M-08..12) — canonical path containment (`..` traversal and symlink escapes via `Path.resolve(strict=True)` + `is_relative_to`), `\x00` sanitization (raw and JSON-escaped `\u0000`), 21-token network denylist, UTF-8 binary subsequence grounding over `read_bytes()`, and silent denial (no path/OS leakage).
* **`tests/security/test_opencode_permissions.py`:** Config perimeter (SEC-M-13) — the `opencode.jsonc` bash permission matrix MUST NOT grant a `git *` wildcard allow; only explicit read/inspection subcommands (status, diff, log, show, rev-parse, grep, blame, ls-files, add) MAY be allowed; deny primitives persist.
* **`tests/e2e/`:** C1 Guard (G10) ported from harness — consolidation rate in [5%, 95%] with real model (Phase 6); per-block `test_e2e.py` implement `@pytest.mark.model` journeys.
* **`tests/fixtures/nsm_axes_8.json`:** Real axes (8×384) exported for L1 tests.
* **CI:** `.github/workflows/ci.yml` — 2 jobs: hermetic (`pytest tests/ -m "not model"`, no model/offline) and real-model E2E (`pytest tests/ -m "model"` + `tools/audit_harness.py`, model cached via `actions/cache` + HF prefetch).
* **[TEST_OVERVIEW.md](./development/tests/TEST_OVERVIEW.md):** Living document of the suite — measured state (204 passed / 2 skipped full; 197 passed / 2 skipped / 7 deselected hermetic), bootstrap map, G1–G9 catalog, blocks × categories, claims, meta-guardians, and Spec-First contribution guide.
