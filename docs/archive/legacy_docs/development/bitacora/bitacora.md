# Work Log and Document Audit (Consolidated)

## Record #001 — README.md

- **Path:** `README.md`
- **Status:** Consolidated
- **Changes:**
  1. **3-Layer Model:** Explicit definition of Ulpia as the native mathematical observation framework ($O_n = P_\theta(S_n)$) at Layer 3, decoupled from the domain RefApps.
  2. **Substrate Formulation ($S_n$):** Synchronization with ADR-023: $S_n = (V_n, E_n, K_n)$.
  3. **Fossil Purge:** Replacement of `RefinedIdeaTOON` with `RefinedEntity`; test updated to `tests/test_control_plane.py`.
  4. **`SUA_POTESTAS.md` Purge:** Removal of the `foundations/` folder from the documentation map.
  5. **ADR Range:** Formal update to the full range ADR-001 through ADR-025.
  6. **Affirmative Postulate:** Statement: "Traianus does not define how reality is represented. It operates upon coordinate vectors $\mathbf{v} \in \mathbb{R}^d$ emitted by external representation providers to govern spatial state deterministically."

---

## Record #002 — `docs/research/RESEARCH_HYPOTHESIS.md`

- **Path:** `docs/research/RESEARCH_HYPOTHESIS.md`
- **Status:** Consolidated
- **Changes:**
  1. **Bounded Gärdenfors (Section 2.1):** Bounding of Gärdenfors' theory (2000) to the Conceptual Level (Geometric/Topological), formalized as $S_n = (V_n, E_n, K_n)$ (ADR-023).
  2. **SOTA Critique & Inverse Adaptation Error (Section 3):** Restructuring of the SOTA critique by paradigm and formal inclusion of the *Inverse Adaptation Error* concept.
  3. **Corollaries (Section 4.1):** Explicit preservation of the `4.1 Corollaries` category (RH-1, RH-2, RH-3).

---

## Record #003 — `docs/architecture/Project_architecture.md`

- **Path:** `docs/architecture/Project_architecture.md`
- **Status:** Consolidated
- **Changes:**
  1. **Flow Scheme (Section 3.3):** Positioning of Ulpia as the native mathematical observation engine over the RefApps.
  2. **Adjective Purge:** Removal of redundant qualifiers ("strictly enforces", "Strict Boundary", "Strictly deterministic").
  3. **Dual-Key Consolidation (Section 2.1):** Clean wording of the quarantine (`lifecycle_state = 'incubating'`) in the absence of key concurrency (ADR-022).
  4. **`manifold_nodes` Table (Section 4):** Explicit reference to the official Pydantic contracts (`RawDump` / `RefinedEntity`).

---

## Record #004 — `docs/architecture/contracts/CONTRACTS_AND_PRISMS.md`

- **Path:** `docs/architecture/contracts/CONTRACTS_AND_PRISMS.md`
- **Status:** Consolidated
- **Changes:**
  1. **Dramatic Metaphor Purge (Section 1):** Substitution of "Prohibition of Generative Models" and "Customs Architecture" with neutral technical terms: "Deterministic Execution Boundaries" and "Two-Tier Ingress Validation".
  2. **Markdown Syntax Fix (3.1 and 3.2):** Restoration of Python code blocks for `RawDump` and `RefinedEntity`.
  3. **Enum `lifecycle_state`:** Incorporation of the `'archived'` state to keep exact symmetry with the `manifold_nodes` table.

---

## Record #005 — `docs/research/RESEARCH_PROGRAM.md`

- **Path:** `docs/research/RESEARCH_PROGRAM.md`
- **Status:** Consolidated
- **Changes:**
  1. **Bootstrapping Transition:** Replaced the old "Technical Triad" meta-explanation with a direct introductory sentence.
  2. **Markdown Format:** Deliverables and Benchmarking tables converted to clean Markdown.
  3. **Cross-Family Invariant:** Explicit synchronization of the transition function $S_{n+1} = f(S_n, \mathbf{v}_n)$ over $S_n = (V_n, E_n, K_n)$ (ADR-023).

---

## Record #006 — `tests/test_control_plane.py`

- **Path:** `tests/test_control_plane.py`
- **Status:** Consolidated
- **Changes:**
  1. **Total Fossil Purge:** Removal of `clinical_diagnosis`, `RefinedIdeaTOON`, informal jargon ("Operación Ferrari", "Génesis Logográfica") and comments in Spanish.
  2. **Official Contracts:** Direct integration of `RawDump` and `RefinedEntity`.
  3. **Test Engineering Preserved:** Retention of the isolation via SQLite fixture (`tmp_path`) and the ADR-002, ADR-014, ADR-015 and ADR-020 verifications.

---

## Record #007 — TDD execution cycle (F1–F3): green harness + append-only + synchronized audit

- **Path:** `tools/audit_harness.py`, `traianus/app.py`, `traianus/bootstrap.py`, `tests/test_append_only_log.py`, `tests/test_control_plane.py`, `TRAIANUS_AUDITORIA_ES.md`, `docs/LOGOGRAPHY.md`
- **Status:** Consolidated
- **Changes:**
  1. **Empirical harness repaired and hermetic (C1, F1):** operator token at `/ingesta` (H3), empirically calibrated varied corpus (6/20 = 30% consolidation, within [5%, 95%]), and `DB_PATH` redirected to ephemeral SQLite (`tempfile`) so as not to contaminate `traianus.db`. `python3 tools/audit_harness.py` → `✅ GUARDIA C1 PASADO EN VERDE`.
  2. **Append-only invariant (H4, F2):** `manifold_nodes` converted into a revision log with composite PK `(id, seq)`; every transition (ingestion, consolidation, dimensional expansion at `/mutate`) INSERTs a new revision with increasing `seq`; "current state" exposed via `MAX(seq)` per id. Removed `INSERT OR REPLACE` and `UPDATE manifold_nodes`. `bootstrap.py` without `DELETE FROM geodesic_axes` (INSERT OR IGNORE).
  3. **TDD:** `tests/test_append_only_log.py` written first (🔴 red against the UPDATE-based code) and verified green (🟢) after the implementation; full suite 34 passed.
  4. **`traianus.db` migration:** derived artifact migrated to the `(id, seq)` schema preserving the 23 pre-existing nodes as `seq=1` revisions (no data deletion).
  5. **Synchronized audit:** `TRAIANUS_AUDITORIA_ES.md` with cycle status table (C1/H1/H2/H3/M3/M4/M5/M6/M7 ✅; H4 partial; H5/M8/L1–L6 open).

---

## Record #008 — OpenCode configuration hardening cycle (real MCP, plan-architect rename, Zero-Trust permissions)

- **Path:** `opencode.jsonc`, `.opencode/agents/*.md`, `tools/tridenguard_validator.py`, `docs/development/bitacora.md`
- **Status:** Consolidated
- **Changes:**
  1. **D1 (CRITICAL):** `tools/tridenguard_validator.py` rewritten as a real MCP stdio server (JSON-RPC 2.0 over lines) v1.1.0: `initialize` (capabilities.tools.listChanged=false + serverInfo), `ping`, `tools/list`, `tools/call` (inputSchema `proposal` required / `target_file` optional; indented text), standard errors -32601/-32602/-32603 and notifications without response. `validate_proposal` kept intact (lines 7–35; forbidden tokens: `fetch(`, `axios`, `urllib.request`, `import requests`). CLI branch with args preserved for regression.
  2. **D2 (CRITICAL):** Renamed `.opencode/agents/plan_arquitect.md` → `plan-architect.md` (the name derives from the filename) and removed the misleading `name:` frontmatter. Final permissions: `edit: deny` + `bash: deny`.
  3. **D3 (CRITICAL) + D4 (MAJOR):** The 5 agents declare `mode: subagent` and explicit `permission:` without `name:` (plan-architect: `edit: deny` + `bash: deny`; orchestrator: `edit: deny` + `bash: ask`; fixer and antigravity-compiler: `edit: allow` + `bash: allow`; logographer: `edit: allow` + `bash: deny`).
  4. **D5 (MAJOR):** `opencode.jsonc` loads `"instructions": ["TRAIANUS_AUDITORIA_ES.md", "docs/LOGOGRAPHY.md"]` after `small_model`; MCP block pointing at the validator (now functional after D1). JSONC parseable.
  5. **D8 (MINOR):** Doc-drift fixed in this work log: paths of Records #003 and #004 normalized to the `docs/architecture/` directory; the same adjustment applied in `docs/development/working_tree.md` (`Project_architecture.md`).
  6. **D6 (MINOR, pending consent):** Inert global `~/.config/opencode/node_modules` (61M) was NOT touched; requires an explicit decision from the User.
- **Regression:** `python3 -m pytest tests/ -q` → 34 passed; `python3 tools/audit_harness.py` → GUARDIA C1 VERDE; MCP `serverInfo` handshake OK (v1.1.0).
- **Pending:** Restart of opencode to reload configuration (no hot reload) and User confirmation of the diff before any commit.

---

## Record #009 — OpenCode Architectural Specification

- **Path:** `docs/architecture/opencode_architecture.md`, `docs/LOGOGRAPHY.md`
- **Status:** Consolidated
- **Changes:**
  1. **Architectural specification created (`docs/architecture/opencode_architecture.md`):** 10-section document that fixes the contract of the hardened OpenCode configuration (2026-08-01): configuration topology (`model: opencode/big-pickle`, `small_model: opencode/ling-3.0-flash-free`, instructions `TRAIANUS_AUDITORIA_ES.md` + `LOGOGRAPHY.md`, MCP `tridenguard-validator` v1.1.0), topology of the 5 agents with Zero-Trust permission matrix, orchestration flow, validator JSON-RPC contract (decisions `EXECUTE_SAFE`/`INVALID_JSON`/`BLOCKED_BY_SAFETY_GATE`/`ABORTED_VIOLATES_ZERO_TRUST`/`ABORTED_GROUNDING_FAILED`; errors -32601/-32602/-32603), `AGENTS.md` invariants and validation criteria.
  2. **Logography updated (`docs/LOGOGRAPHY.md`):** added the `opencode_architecture.md` entry in section 3 (Architecture and Engineering), without restructuring the rest of the index.
  3. **Veracity verification:** every configuration quote, agent frontmatter and validator decision was cross-checked against the source file (literal Topological Grounding); C1 harness re-run → `✅ GUARDIA C1 PASADO EN VERDE`; historical suite (without `tests/bloques/`, in progress in another cycle) green.
- **Regression:** `python3 tools/audit_harness.py` → GUARDIA C1 VERDE (30% consolidation within [5%, 95%]); no changes in `traianus/`, `tests/` or `tools/`.
- **Pending:** review of the specification by `@plan-architect`/`@orchestrator`; commit when the User confirms the diff of cycle #008.

---

## Record #010 — Spec-First reorganization of the test harness (Phases 0–6)

- **Path:** `tests/` (complete restructuring), `docs/development/tests/SPEC-*.md`, `tools/audit_harness.py` (intact), `README.md`, `pyproject.toml`, `.github/workflows/ci.yml`, `docs/LOGOGRAPHY.md`
- **Status:** Consolidated
- **Changes:**
  1. **Phase 0 (Foundations):** `tests/conftest.py` (fixtures `operator_token_env`, `isolate_db`, `client`, `auth_headers`, `_hermetic_model`), `tests/helpers/{db_factory,fake_encoder,endpoint_registry}.py`, `tests/fixtures/nsm_axes_8.json` (frozen real geometry 8×384, off-diagonal cosine ≈ 0.23), `tools/export_nsm_axes.py`, `[tool.pytest.ini_options]` with `model`/`security` markers. Single DDL: grep `CREATE TABLE` == 1 file.
  2. **Phase 1 (Generic catalog):** `tests/genericos/` G1–G9 + ADR-025 invariants, parameterized by 6 blocks. **CODE_FIX L2:** `PRAGMA journal_mode=WAL` in `/relations` handlers (`traianus/app.py`).
  3. **Phase 2 (Per-block skeleton):** `tests/bloques/{ingesta,consolidacion,relaciones,mutacion,observabilidad,bootstrap}/{test_genericos,test_especificos,test_e2e}.py` with `__init__.py`; removed `tests/test_control_plane.py` and `tests/test_append_only_log.py` (34 tests moved WITHOUT changing assertions).
  4. **Phase 3 (SPECs + guardians):** 9 RFC 2119 SPECs in `docs/development/tests/`; `tests/meta/_spec_lib.py` + `test_guardianes_estructura.py` (4 guardians: SPEC parsing, Normative/Coverage headers, incremental `ACTIVE_SPECS` 1:1 MUST↔test traceability, no orphan tests). Headers injected into the 28 test files.
  5. **Phase 4 (Claims):** `tests/afirmaciones/claims_registry.py` (CL-C41, CL-I5, CL-I61, CL-I62, CL-R1, CL-R2, CL-WP1, CL-TR1, CL-LIT1) with states ACTIVE/RED/WP. **DOC_FIX README:** quickstart now documents `traianus-bootstrap` + `uvicorn traianus.app:app --host 127.0.0.1` (CL-R1/R2 move to ACTIVE). **Pending RED:** CL-I62 (dimension greater than the basis without explicit handling, disposition CODE_FIX).
  6. **Phase 5 (Specifics + Security):** RE-07 dangling edge→404 (**CODE_FIX L2** in `forge_relation`: node existence validation), RE-08 `rebuild_epsilon_edges` (**deterministic E_n ADR-023/H5** in `traianus/app.py`), CO-11 ADR-022 key symmetry, MIME firewall expanded to 7 types (IN-02), `tests/security/test_tridenguard_validator.py` (SEC-M-01..06 incl. MCP stdio server).
  7. **Phase 6 (E2E + CI):** `tests/e2e/test_e2e_global_G10_c1_consolidation_guard.py` (C1 guard ported from the harness, `@pytest.mark.model`), complete per-block E2E journeys (IN11, CO10, RE06, MU04, OB09, BO08), `.github/workflows/ci.yml` with 2 jobs (`-m "not model"` / `-m "model"` with model prefetch). CLI harness intact.
- **Regression:** `pytest tests/ -q` → **171 passed, 2 skipped, 1 xfailed** (documented CL-I62 RED). Partitions: `-m "not model"` → 164 passed; `-m "model"` → 7 passed. `tools/audit_harness.py` → GUARDIA C1 VERDE (30% consolidation in [5%, 95%]).
- **Pending:** CODE_FIX CL-I62 (explicit `dim_in > dim_db` handling); diff review by `@plan-architect`; commit when the User confirms.

---

## Record #011 — `docs/development/tests/TEST_OVERVIEW.md` (living map of the suite)

- **Path:** `docs/development/tests/TEST_OVERVIEW.md`, `docs/LOGOGRAPHY.md`
- **Status:** Consolidated
- **Changes:**
  1. **Document created (`docs/development/tests/TEST_OVERVIEW.md`):** "Suite de Tests de Traianus — Estado Actual" (2026-08-01, commit `9983359`), empirically verified description of the suite: Spec-First philosophy (grounding in METHODOLOGY.md Phase 3 and ADR.md:131), bootstrap map (`model` marker, partitions, `pyproject.toml` config, CI), G1–G9 catalog + ADR-025 invariants (INV1–INV5), 6 blocks × categories with literal test_ids, claims layer (CL-C41..CL-LIT1, ACTIVE/RED/WP), meta-guardians (4), security SEC-M-01..06, e2e G10, measured health state and contribution guide.
  2. **Logography updated (`docs/LOGOGRAPHY.md`):** added the `TEST_OVERVIEW.md` entry in section 6 (Test Structure), without restructuring the index.
  3. **Doc-drift finding (not fixed in this cycle):** `docs/LOGOGRAPHY.md:33` claims "CL-I62 permanece RED (CODE_FIX pendiente: dimensión mayor que la base)", but `tests/afirmaciones/claims_registry.py` and `test_cl_i62_dimension_provider.py` declare CL-I62 **ACTIVE** (the `dim_in > dim_db` CODE_FIX has already been applied; see test `test_afirmaciones_CL_I62_consolidar_rechaza_dim_mayor`). It is recommended to correct that line in a future documentation synchronization cycle.
- **Regression:** documentation only (`docs/`); no changes in `traianus/`, `tests/`, `tools/`, `pyproject.toml` or `.github/` — the suite does not change (174 passed / 2 skipped in the verified context of the cycle).
- **Pending:** correct the obsolete CL-I62 line in `docs/LOGOGRAPHY.md`; diff review by `@orchestrator`/`@plan-architect`.

---

## Record #011 — Pilot: Contract → Code Mining Kit

- **Path:** `docs/templates/contract-mining/` (README, plantilla_mineria.md, ejemplo_mineria_state_2.1.md, obligaciones_state_2.1.json, logs/), `tools/contract_obligation_verifier.py`
- **Status:** Consolidated (verifiable pilot)
- **Changes:**
  1. **Mining kit:** template for extracting RFC 2119 clauses → structured obligations `{tipo, sujeto, condición, verificación, cita}` per archetype (state/phase/system/runtime/node).
  2. **Pilot on `Contrato_State_v2.1`** (AI Papers Engine, FROZEN): mined **33 obligations** (1 domain + 18 writers + 7 invariants + 5 existence + 1 pipeline) with literal grounding.
  3. **Verifier** (`tools/contract_obligation_verifier.py`): checks a transition log (node → written keys) against the obligations: closed domain, single writer, write-once abort, dominant abort, immutability by phases, HITL invariants and existence per gate.
  4. **Demos:** `logs/demo_conforme.json` → GREEN (exit 0); `logs/demo_violaciones.json` → RED (exit 1) with 5 findings (ghost key, writer collision, non-dominant abort, missing abort_reason, post-abort output).
- **Regression:** `pytest tests/ -q` → **174 passed, 2 skipped** (no changes in `tests/`); verifier green/red demonstrated empirically.
- **Drift detected:** `hitl_selected_items` is a ghost key (in phase prohibitions, absent from the State §2 domain).
- **Pending:** mine phase contracts (Retrieval/HITL/Summarize) and Runtime; verifier integration with the audit harness; commit when the User confirms.

---

## Record #012 — Logographic synchronization 2026-08-01 (Phases 1–3 of the Action Plan)

- **Path:** `docs/STATE_CONSOLIDATION_2026-08-01.md` (new), `docs/LOGOGRAPHY.md`, `docs/architecture/opencode_architecture.md`
- **Status:** Consolidated
- **Changes:**
  1. **Consolidation document created (`docs/STATE_CONSOLIDATION_2026-08-01.md`):** git state (ngi-candidacy=76845a6, origin/main=e2ab8bc), reflog of the 5 commits, per-area diff summary, AGENTS.md invariant matrix with path:line evidence, Doc-Drift catalog D1–D10 with literal citations, routable recommendations R1–R5 (for `@fixer`), acceptance criteria and verified grounding citations.
  2. **Logography corrected (`docs/LOGOGRAPHY.md`):** D3 (CL-I62 → ACTIVE, verified by `test_afirmaciones_CL_I62_*` in `test_cl_i62_dimension_provider.py`), D4 (`tests/claims/` → `tests/afirmaciones/`), D5 (sections reordered 1→2→3→4→5→6), and registration of the consolidation document in section 5 (Audit).
  3. **OpenCode specification updated (`docs/architecture/opencode_architecture.md`):** §9 adds a reference to the consolidation document and a note on the pending restoration of `TRAIANUS_AUDITORIA_ES.md` (R2); §10 anchors the current state (**174 passed / 2 skipped**) preserving the historical #008 (**34 passed**).
- **Regression:** documentation only (`docs/`); no changes in `traianus/`, `tests/`, `tools/`, `pyproject.toml`, `.github/` or `.gitignore` — the suite does not change (174 passed / 2 skipped; C1 harness green, 30% rate in [5%, 95%]).
- **Pending:** R1–R5 routed to `@fixer` (remove `docs/development/` from `.gitignore:19`; restore `TRAIANUS_AUDITORIA_ES.md` from `CHANGES_FULL.diff:841-1283`; sync `TRAIANUS_AUDIT.md:77-78`; update schema in `Project_architecture.md:92-102`; commit `flake.lock`); D7/D8 documented as pending; diff review by `@orchestrator`/`@plan-architect`.

---

## Record #013 — Debureaucratization of the Test Suite (Governance Decision)

- **Path:** `tools/contract_obligation_verifier.py` (removed), `docs/templates/contract-mining/` (removed)
- **Status:** Consolidated
- **Changes:**
  1. **Dead matter removed:** contract-mining pilot retired — `tools/contract_obligation_verifier.py` (205 lines) and the `docs/templates/contract-mining/` folder (README, template, example, `obligaciones_state_2.1.json`, `logs/`). It does not run in the substrate runtime or in the Pytest suite; conceptual weight without contribution to the real executable.
  2. **No new bureaucracy:** adding a "freezing" rule to `AGENTS.md`/`METHODOLOGY.md` was rejected — codifying an anti-bureaucracy rule would, in itself, be bureaucracy. The decision reduces to removing the dead matter and moving on.
- **Regression:** `pytest tests/ -m "not model" -q` → **169 passed, 2 skipped, 7 deselected** (verified after the removal; the hermetic layer at ~3.2s — `fake_encoder.py` + `nsm_axes_8.json` — intact). The verifier had no tests of its own in the suite.
- **Pending:** R1–R5 remain routed to `@fixer`; diff review by `@orchestrator`/`@plan-architect`.

---

## Record #014 — Reversion to Spanish of docstrings, comments and assertion messages of the test harness and tooling

- **Path:** `tests/` (helpers, meta, security, genericos, bloques/*, afirmaciones, e2e, conftest, __init__.py), `tools/` (audit_harness.py, tridenguard_validator.py, export_nsm_axes.py), `traianus/__init__.py`, `traianus/bootstrap.py`
- **Status:** Consolidated (pending pytest verification)
- **Changes:**
  1. **Complete idiomatic reversion:** all module/function docstrings, comments, assertion messages and `print` statements of the test harness and tooling returned to Spanish ("tiene que estar todo en español"). Affects: `tests/conftest.py`, `tests/helpers/{db_factory,endpoint_registry,fake_encoder}.py`, `tests/meta/{_spec_lib,test_guardianes_estructura}.py`, `tests/security/test_tridenguard_validator.py`, `tests/genericos/*.py` (10), `tests/bloques/{ingesta,consolidacion,mutacion,relaciones,observabilidad,bootstrap}/*.py` (18), `tests/afirmaciones/{claims_registry + 9 test_*.py}`, `tests/e2e/test_c1_consolidation_guard.py`, `tests/helpers/__init__.py`, `tools/*.py` (3), `traianus/__init__.py` and `traianus/bootstrap.py`.
  2. **Normative identifiers intact:** G1–G9, INV1–INV5, SEC-M-01..06, CO/RE/MU/OB/BO/IN and CL-* unchanged; English test function names (pytest convention) preserved; `tests/bloques/*` directories already in Spanish, not renamed.
  3. **Data contracts preserved:** block keys in `endpoint_registry.py` (`ingestion`, `consolidation`, …), response strings asserted by tests (`"Only text/plain is accepted at ingress"`, `"Ingress persistence unavailable"`, `"expanded to 385D"`), calibrated harness and E2E corpus (`Something happens.`, 20-note C1 G10 corpus), `LITERAL_QUOTES` of CL-LIT1 (verified character by character) and MCP values (`EXECUTE_SAFE`, `validate_proposal`).
  4. **Claims registry in Spanish:** the `must` values of `CLAIMS` in `claims_registry.py` translated (documentary data; no test asserts the text, only the IDs).
  5. **Out of scope:** `traianus/app.py` NOT modified (production code; English docstrings intact — protected by AGENTS.md invariants #1 and #4 and outside the User's list).
  6. **LOGOGRAPHY.md reviewed (requirement 5):** it does not reference English test identifiers that have changed (test names remain in English), so it does not require updating; the only record with English names (`docs/DIF_LOG_2026-08-01.md`) is historical and remains accurate.
- **Regression:** PENDING — `pytest tests/ -m "not model"` must be run → **169 passed, 2 skipped** (no shell available in the editing cycle; manual verification required).
- **Pending:** run the hermetic suite to confirm 169 passed / 2 skipped; diff review by `@orchestrator`; commit when the User confirms.

---

## Record #016 — README.md Quickstart rewritten (venv + pip canonical path)

- **Path:** `README.md` (section 5 only; rest of the document untouched)
- **Branch:** `chore/readme-quickstart-docs`
- **Status:** Consolidated (documentation-only; no pytest run required)
- **Changes:**
  1. **Minimal setup (venv + pip):** `python -m venv .venv && source .venv/bin/activate`, `pip install -e .`, test extra `pip install -e ".[test]"`, and `traianus-bootstrap` as offline model prefetch (bootstrap and server use `local_files_only=True`). Nix demoted to an optional alternative.
  2. **Server boot (Zero-Trust):** `TRAIANUS_TOKEN=your-secret uvicorn traianus.app:app --host 127.0.0.1 --port 8000`; documented that `TRAIANUS_TOKEN` is **mandatory** for the protected routes — `/ingesta`, `/consolidar`, `/mutate`, `/relations`, `/telemetry` — with fail-closed `401`.
  3. **Environment variables table:** `TRAIANUS_TOKEN` (required, string) and `TRAIANUS_EPSILON_EDGE` (optional, float, default `0.8` — synchronized with `traianus/app.py:48`).
  4. **Test commands:** hermetic `pytest tests/ -m "not model"` (no model, offline) and E2E `pytest tests/ -m "model"` (requires cached model; marker registered in `pyproject.toml`).
- **Doc-Drift guard (verified against source):** `traianus-bootstrap` console script exists (`pyproject.toml:27-28`); protected-route list matches every `dependencies=[Depends(require_token)]` in `traianus/app.py` (`/ingesta`, `/consolidar`, `/mutate`, `/relations`, `/telemetry`); `EPSILON_EDGE` default read from `app.py:48`.
- **Deviation to escalate to `@orchestrator`:** the requested default `0.45` for `TRAIANUS_EPSILON_EDGE` does **not** match the code (`0.8`, `traianus/app.py:48`; tests `tests/bloques/relaciones/test_especificos.py:22` also use `0.8`). The README documents `0.8` (code truth) to avoid Doc-Drift. If the intent is to change the default, `@fixer` must update `app.py:48` + regressions, and only then should the README be updated to `0.45`.
- **Pending:** diff review by `@orchestrator`; commit when the User confirms.

- **Path:** `tests/` (test function renames), `docs/development/tests/TEST_OVERVIEW.md`, `docs/LOGOGRAPHY.md`, `docs/development/bitacora.md`
- **Status:** Consolidated (pending manual pytest verification)
- **Changes:**
  1. **Mixed convention applied to the harness:** docstrings, comments, assertion messages and `print` statements remain in Spanish; identifiers (test function names, variables, constants and dict keys) in English.
  2. **Test function renames (33 functions; normative IDs intact):**
     - `tests/security/test_tridenguard_validator.py` (SEC-M-01..05): `json_invalido_rechazado` → `invalid_json_rejected`, `safety_abort_bloquea` → `safety_abort_blocks`, `red_externa_bloqueada` → `external_network_blocked`, `grounding_literal_exigido` → `literal_grounding_required`, `grounding_valido_aprueba` → `valid_grounding_approved`; SEC-M-06 already in English.
     - `tests/afirmaciones/` (CL-I62 ×4, CL-TR1 ×2, CL-R1 ×3, CL-R2 ×2, CL-LIT1 ×1): `test_afirmaciones_CL_` prefix kept (the CL-TR1 meta-guardian derives coverage from that prefix).
     - `tests/bloques/ingesta/test_especificos.py` (IN01–IN08 ×9): `test_ingestion_` prefix (acepta→accepts, rechaza→rejects, crea→creates, registra→logs, `doble_guion_bajo_no_colapsa_espectro`→`double_underscore_no_spectrum_collapse`, `es_varianza`→`is_variance`).
     - `tests/bloques/{consolidacion,mutacion,relaciones,observabilidad}/test_e2e.py` (CO10/MU04/RE06/OB09): `viaje_completo` → `full_journey` with English prefixes (`test_e2e_consolidation_*`, `test_e2e_mutation_*`, `test_e2e_relations_*`, `test_e2e_observability_*`).
     - `tests/bloques/bootstrap/test_especificos.py` (BO01–BO03): `roundtrip_serializacion` → `roundtrip_serialization`, `rawdump_contrato` → `rawdump_contract`, `refinedentity_valida_lifecycle` → `refinedentity_validates_lifecycle`.
  3. **Variables already conformant:** verified that `tests/helpers/{db_factory,endpoint_registry,fake_encoder}.py`, `tests/conftest.py`, `tests/genericos/*`, `tests/e2e/*`, `tests/meta/*` and `tools/{audit_harness,tridenguard_validator}.py` already use English identifiers; no variable renames were necessary.
  4. **Doc-drift fixed (`docs/development/tests/TEST_OVERVIEW.md`):** the representative test_ids of G1–G9, blocks, claims and meta-guardians referenced Spanish names that do not exist in the code (remnants of cycle #014); synchronized with the real identifiers. Contribution guide §8 updated to the mixed convention.
  5. **LOGOGRAPHY.md:** TEST_OVERVIEW measured state updated (hermetic `-m "not model"` 169 passed / 2 skipped; total 176 passed / 2 skipped).
  6. **Out of scope:** `traianus/app.py` intact (AGENTS.md invariants #1 and #4); `tests/bloques/*` directories in Spanish, not renamed; normative IDs G1–G9, INV1–INV5, SEC-M-01..06, CO/RE/MU/OB/BO/IN and CL-* unchanged; documents dated 2026-08-01 (`DIF_LOG`, `STATE_CONSOLIDATION`, `opencode_architecture.md` anchors) kept as historical record.
- **Regression:** PENDING — `pytest tests/ -m "not model"` must be run → **169 passed, 2 skipped** (no shell available in the editing cycle; manual verification required).
- **Pending:** run the hermetic suite to confirm 169 passed / 2 skipped; diff review by `@orchestrator`; commit when the User confirms.

---

## Record #017 — Restoration of the OpenCode governance layer (cycle 2026-08-03)

- **Path:** `opencode.jsonc`, `AGENTS.md`, `.opencode/` (5 agents, 3 commands, 2 skills), `TRAIANUS_AUDIT.md`, `docs/LOGOGRAPHY.md`, `docs/STATE_CONSOLIDATION_2026-08-01.md`, `docs/architecture/opencode_architecture.md`, `README_CODE_ENGINE.md`, `docs/audit/`, `docs/development/methodology/METHODOLOGY.md`, `docs/STATE_CONSOLIDATION_2026-08-03.md` (new), `docs/development/bitacora.md`
- **Branch:** `chore/restaurar-gobierno-opencode` (created from `chore/readme-quickstart-docs` @ `ea43df6`)
- **Status:** Consolidated (pending commit; documentation-only)
- **Changes:**
  1. **Restoration of the poda (`ea43df6`):** the OpenCode configuration layer deleted by the commit "poda del meta-gobierno" is restored byte-by-byte from `ea43df6^` (20 files): `opencode.jsonc` (model `opencode/big-pickle`, `small_model`, instructions, local MCP `tridenguard-validator`, permissions, `mcp_timeout`), `AGENTS.md`, the 5 Zero-Trust subagents, the 3 commands (`plan`, `orchestrate`, `verify`), the 2 skills (`tdd-cycle`, `tridenguard-5-radicales`), and the referenced governance docs (`TRAIANUS_AUDIT.md`, `LOGOGRAPHY.md`, `opencode_architecture.md`, `STATE_CONSOLIDATION_2026-08-01.md`, `README_CODE_ENGINE.md`, `docs/audit/*`, `METHODOLOGY.md`).
  2. **Consolidation document created (`docs/STATE_CONSOLIDATION_2026-08-03.md`):** git state, table of restored files, empirical verification (suite **181 passed / 2 skipped**, hermetic **174 passed / 2 skipped / 7 deselected**, C1 GUARD **45% / 9-20**), invariant matrix and cycle findings (W1–W4).
  3. **LOGOGRAPHY.md updated:** registration of `STATE_CONSOLIDATION_2026-08-03.md` in section 5 (Audit).
  4. **Out of scope:** the uncommitted candidatura changes (`README.md` — quickstart, `docs/architecture/ADR/ADR.md`, `tests/*`, `traianus/app.py`, `docs/templates/`, `tools/traianus_invariant_verifier.py`) remain in the working tree, NOT part of this branch's commit. This record is local (`.gitignore` excludes `docs/development/bitacora.md`; versioned governance is `STATE_CONSOLIDATION_*.md`).
- **Regression:** `pytest tests/ -q` → **181 passed, 2 skipped**; `pytest tests/ -m "not model" -q` → **174 passed, 2 skipped, 7 deselected**; `tools/audit_harness.py` → **✅ C1 GUARD PASSED IN GREEN (45% / 9-20)**.
- **Pending:** diff review by `@plan-architect`/`@orchestrator`; commit on `chore/restaurar-gobierno-opencode` when the User confirms; merge decision on the candidatura changes.

---

## Record #018 — Dual Boundary Pattern citations (Phase 2, Action Plan 2026-08-03)

- **Path:** `AGENTS.md`, `docs/development/tests/SPEC-security.md`, `docs/LOGOGRAPHY.md`, `docs/development/bitacora.md`
- **Status:** Consolidated (pending pytest verification)
- **Changes:**
  1. **AGENTS.md §2.3 (Zero-Trust and Network Security):** formal citation of `docs/Dual Boundary Pattern_ Deterministic Execution via Binary Verification.md` added as a bullet; the forbidden network token list extended with `httpx`, `socket`, `urllib3`, `subprocess`, `curl`, `wget`, `aiohttp`, `importlib`, `os.system`, `os.popen` (existing bullet format preserved).
  2. **AGENTS.md §2.4 (Literal Grounding Guarantee):** physical (byte-level) verification required — path canonicalization (`Path.resolve(strict=True)`), repo-root containment (`is_relative_to`), UTF-8 binary subsequence matching over `read_bytes()`, null-byte (`\x00`) sanitization, and silent denial (validator responses must not reveal internal paths). Numbering and style preserved.
  3. **SPEC-security.md:** formal citation of the Dual Boundary Pattern in the header blockquote + scope note that SEC-M-08..12 will be added in Phase 3. No new normative MUSTs introduced — the 1:1 MUST↔test traceability (SEC-M-01..07, SEC-M-13) is unchanged.
  4. **LOGOGRAPHY.md:** Dual Boundary Pattern registered in §5 (Audit & Neuro-Symbolic Firewall); `tests/security/test_opencode_permissions.py` (SEC-M-13) registered in §6; the `tests/security/` bullet corrected from SEC-M-01..06 to SEC-M-01..07 (Doc-Drift: SEC-M-07 was already normative in SPEC-security.md and covered by `test_tridenguard_validator.py`).
  5. **Out of scope:** `tools/tridenguard_validator.py` NOT modified (Phase 4); historical `docs/STATE_CONSOLIDATION_*` untouched (append-only).
- **Regression:** `python3 -m pytest tests/meta/ -q` — pending verification by `@orchestrator` (logographer role: `bash: deny`). Static analysis: the SPEC-security citation sits outside the parsed `## Normative requirements` section (`tests/meta/_spec_lib.py:parse_spec_ids`), no new MUSTs added, and no test header was modified.
- **Pending:** run `python3 -m pytest tests/meta/ -q` and `rg -n "Dual Boundary" AGENTS.md docs/LOGOGRAPHY.md`; diff review by `@orchestrator`; commit when the User confirms.

---

## Record #019 — Dual Boundary Action Plan: Phase 3 RED + Phase 4 GREEN (validator v1.2.0)

- **Path:** `tools/tridenguard_validator.py`, `tests/security/test_tridenguard_dual_boundary.py`, `.opencode/command/verify.md`, `docs/architecture/opencode_architecture.md`, `docs/LOGOGRAPHY.md`, `pyproject.toml`, `docs/development/bitacora.md`
- **Status:** Consolidated (pending orchestrator confirmation of the pending commands)
- **Changes:**
  1. **Phase 3 (RED):** `tests/security/test_tridenguard_dual_boundary.py` written first — SEC-M-08..12, 8 tests (canonical containment with `..`/symlink escapes, `\x00` sanitization raw and JSON-escaped, expanded network denylist, UTF-8 binary subsequence over `read_bytes()` with fail-closed on non-UTF-8, silent denial without path/OS leakage). 8/8 failed against v1.1.0 as intended (RED proven).
  2. **Phase 4 (GREEN):** `tools/tridenguard_validator.py` refactored to **v1.2.0** — Dual Boundary Gate: `Path.resolve(strict=True)` + `is_relative_to(REPO_ROOT)` containment + exact UTF-8 binary subsequence over `read_bytes()` + `\x00` sanitization (raw and `\u0000`) + silent denial via `_grounding_failure()` without `reason`; network denylist expanded to **21 tokens** (`fetch(`, `axios`, `urllib.request`, `import requests`, `httpx`, `socket`, `urllib3`, `subprocess`, `curl`, `wget`, `aiohttp`, `importlib`, `os.system`, `os.popen`, `requests.`, `http.client`, `webbrowser`, `telnet`, `nc `, `ftp`, `xmlrpc`); `SERVER_VERSION = "1.2.0"`.
  3. **Doc sync (Phase 4, logographer):** `.opencode/command/verify.md` expected MCP serverInfo → v1.2.0; `docs/architecture/opencode_architecture.md` §3.3/§6.2/§6.3/§7.1/§9/§10 version + gates/tokens synchronized with the Dual Boundary Pattern; `docs/LOGOGRAPHY.md` `v1.1.0` → `v1.2.0` (section 3), `tests/security/` range SEC-M-01..07 → SEC-M-01..12 and registration of `test_tridenguard_dual_boundary.py` (SEC-M-08..12); `pyproject.toml` `security` marker SEC-M-01..06 → SEC-M-01..12.
  4. **Historical preserved (append-only):** v1.1.0 mentions in `docs/STATE_CONSOLIDATION_2026-08-01.md` and `docs/STATE_CONSOLIDATION_2026-08-03.md` (and in bitacora Records #008/#009) are historical record; NOT modified.
- **Regression:** `pytest tests/ -q` → **198 passed** (cycle data; 8 new Dual Boundary tests green, SEC-M-08..12); `python3 -m pytest tests/meta/ -q` green (guardians: coverage headers parse, 1:1 MUST↔test traceability).
- **Pending:** confirm `rg -n "1\.1\.0|SEC-M-01\.\.06"` clean in the living sources (historical `STATE_CONSOLIDATION_*` excluded); diff review by `@orchestrator`; commit when the User confirms.

---

## Record #020 — OSS Readiness cycle: baseline, hermeticity, doc-drift, ADR-027, TridenGuard decision (Fases A–E)

- **Path:** `tests/conftest.py`, `tests/meta/test_hermetic_import.py`, `docs/development/tests/TEST_OVERVIEW.md`, `docs/LOGOGRAPHY.md`, `README.md`, `docs/architecture/opencode_architecture.md` (promoted v1.2.0), `docs/archive/` (obligations JSON + `opencode_architecture_v1.md`), `docs/architecture/ADR/ADR.md` (ADR-027), `docs/Dual Boundary Pattern_ Deterministic Execution via Binary Verification.md` (Triarii purge), `docs/observation/ULPIA_OVERVIEW.md` (new), `docs/development/bitacora.md`
- **Branch:** `oss-readiness`
- **Status:** Consolidated (pending final verification and commit)
- **Changes:**
  1. **Fase A — Real baseline (measured, not estimated):** full `HF_HUB_OFFLINE=1 pytest -q` → **203 passed / 2 skipped**; hermetic `-m "not model"` → **196 passed / 2 skipped / 7 deselected**; model partition → **7 passed**; `tools/audit_harness.py` → **✅ C1 GUARD PASSED IN GREEN (45% / 9-20)**; `tools/traianus_invariant_verifier.py` → TR-H4-001 / TR-C1-001 / TR-ZT-001 / TR-ZT-002 **OK** (RED only on the absent derived `traianus.db`); `tools/check_impact.py tools/tridenguard_validator.py` → **14 references**. The user's claimed baseline (181 passed) was stale: it predates the uncommitted candidacy files (`test_config_integrity.py`, `test_audit_status_sync.py`, `tools/check_impact.py`, `tools/audit_spanish_terms.py`).
  2. **Fase A — Hermeticity hardening:** `tests/conftest.py` now forces `os.environ.setdefault("HF_HUB_OFFLINE", "1")` before importing `traianus.app` (defense-in-depth over the `setdefault` in `app.py`/`bootstrap.py`); regression guard `test_conftest_forces_hf_hub_offline` (HERMETIC-IMPORT, `tests/meta/test_hermetic_import.py`).
  3. **Fase B — Doc-drift:** `docs/architecture/opencode_architecture.md` restored as canonical from the v1.2.0 (2026-08-03) version; historical `opencode_architecture_v1.md` (2026-08-01) archived to `docs/archive/`; TEST_OVERVIEW §7 + LOGOGRAPHY updated to the measured state (203/196/7, C1 45%); README ADR range → ADR-001 to ADR-027. `AGENTS.md` NOT moved (opencode loads it from the repo root; the move would break the auto-load and ~8 relative links) — the plan's Fase 1 was discarded by `@plan-architect` and confirmed here.
  4. **Fase C — Archive + ADR-027:** `docs/archive/` created; `docs/templates/contract-mining/traianus_poc_obligations.json` moved to `docs/archive/traianus_poc_obligations.json` (historical dead matter, verifier does not read it at runtime); **ADR-027 "Dual Boundary Pattern & Binary Verification Gate"** registered (Date 2026-08-03, Author AlexusPacicus, Status Approved / Active) — physical byte verification, `Path.resolve(strict=True)` + `is_relative_to`, UTF-8 subsequence over `read_bytes()`, `\x00` sanitization, silent denial, fail-closed; Triarii references purged from the Dual Boundary Pattern doc (external component not in this repo).
  5. **Fase D — TridenGuard decision (documented, NO move):** `tools/tridenguard_validator.py` **stays in `tools/`**. Rationale (validated by `@plan-architect`): the Dual Boundary binary verification (SEC-M-08..12, validator v1.2.0) is **already implemented**; moving to `traianus/security/validator.py` would break 14 live references (MCP `opencode.jsonc:13`, `tests/security/*` ×2, `tests/genericos/test_g9_zero_trust.py`, `pyproject.toml`, SPEC-security, METHODOLOGY, LOGOGRAPHY, verify.md, consolidations) and would silently shrink `REPO_ROOT` containment to `traianus/` unless `parents[2]` is used — a security regression, not an improvement. The "Fase 4.3 text-to-binary refactor" in the original plan is **redundant**: it describes work already committed (Record #019, v1.2.0).
  6. **Fase E — Observation layer:** `docs/observation/ULPIA_OVERVIEW.md` created ($O_n = P_\theta(S_n)$ per ADR-022/ADR-024); IMPLEMENTATION_STATUS.md and LOGOGRAPHY updated.
- **Regression:** `pytest tests/meta/ -q` → green (13 passed) after Fases B/C; final verification: `tools/traianus_invariant_verifier.py` → static GREEN (exit 0; RED only on absent derived `traianus.db`); `HF_HUB_OFFLINE=1 pytest -q` → **204 passed / 2 skipped** (197 hermetic + 7 model); `tools/audit_harness.py` → **✅ C1 GUARD PASSED IN GREEN (45% / 9-20)**.
- **Pending:** diff review by `@orchestrator`; commit on `oss-readiness` when the User confirms.
