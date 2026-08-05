# Traianus Test Suite — Current State

> **Living document.** State measured as of 2026-08-01 (commit `9983359`). This
> document describes the REAL test suite of the repository, verified
> empirically. Every claim is grounded in the code and in the cited commands
> (AGENTS.md §2.4: `Topological_Grounding` citations must exist exactly,
> character by character, in the cited source file).

---

## 1. Goal and Spec-First philosophy

The suite implements the 4-phase neuro-symbolic methodology of
`docs/development/methodology/METHODOLOGY.md`:

- **Phase 3 — TDD Specification:** "Translation of the contracts and rules of
  the architecture into an explicit matrix of unit/integration tests"
  (METHODOLOGY.md:57-58). Each SPEC in `docs/development/tests/SPEC-*.md`
  PRECEDES the tests that implement it (Spec-First).
- **Phase 4 — Atomic TDD Operational Cycle:** write the test that exposes the
  failure (RED) before the patch (GREEN) and refactor with deterministic
  validation (`tools/tridenguard_validator.py` and `tools/audit_harness.py`).

The normative mandate that anchors the suite is line 131 of ADR-025
(`docs/architecture/ADR/ADR.md`):

> "Integration test suites must validate these five invariants on every build pipeline."

The five non-negotiable state invariants of ADR-025 (monotonic append-only,
zero observation mutagenicity, provider isolation, control-plane centrality
with dual key, and bitwise determinism) are validated in
`tests/genericos/test_invariantes_adr025.py` (INV1–INV5, see §3).

Operational principles of the harness:

- **L1 Hermeticity:** the unit tests inject a fake encoder
  (`tests/helpers/fake_encoder.py`) and an ephemeral SQLite database per test
  (`tests/conftest.py::isolate_db`); only the `@pytest.mark.model` partition
  loads the real `all-MiniLM-L6-v2` model (offline, cached).
- **1:1 Traceability:** each normative ID of a SPEC is covered by exactly one
  test file, with no gaps or duplicates (see §6).
- **Single DDL:** `tests/helpers/db_factory.py` is the only place in the test
  tree where `CREATE TABLE` statements are defined; the rest of the harness
  consumes `create_schema()` / `create_test_db()` (finding L1).
- **Test geometries:** `seed="onehot"` preserves the historical behavior of
  the unit tests; `seed="realistic"` seeds the frozen real NSM geometry from
  `tests/fixtures/nsm_axes_8.json` (8×384, off-diagonal cosine ≈ 0.23)
  without loading the model.

---

## 2. Bootstrap map

Configuration declared in `pyproject.toml` (`[tool.pytest.ini_options]`):

- `testpaths = ["tests"]`
- Markers:
  - `model`: "tests that require the real all-MiniLM-L6-v2 model (offline, cached)"
  - `security`: "TridenGuard Zero-Trust validator tests (SEC-M-01..13)"
- `filterwarnings = ["ignore::DeprecationWarning"]`

Verified commands (2026-08-01):

| Command | Measured result |
|---|---|
| `pytest -q` | 176 passed, 2 skipped |
| `pytest -m "not model"` | 169 passed, 2 skipped, 7 deselected |
| `pytest -m model` | 7 passed |
| `python3 tools/audit_harness.py` | GUARDIA C1 PASADO EN VERDE (30% rate, 6/20, range [5%, 95%]) |

The 2 skips are intentional: the `bootstrap` block exposes no HTTP surface
(`tests/helpers/endpoint_registry.py` → `ENDPOINTS_BY_BLOCK["bootstrap"] == []`),
so the block-parameterized generic tests G1 are skipped with
`pytest.skip("bootstrap no expone superficie HTTP (cubierto por G6)")` in
`test_g1_block_endpoints_require_token` and
`test_g1_block_endpoints_accept_valid_token`.

Root fixtures (`tests/conftest.py`):

- `operator_token_env` (autouse): sets `TRAIANUS_TOKEN=test-operator-token`;
  fail-closed for the protected routes (H3).
- `isolate_db` (autouse): ephemeral SQLite database per test with the canonical
  schema (`create_test_db`) and monkeypatch of `main.DB_PATH`.
- `client`: FastAPI `TestClient` over the real app.
- `auth_headers`: valid `X-Traianus-Token` header.
- `_hermetic_model` (autouse): injects `FakeSentenceTransformer` in all
  tests except those marked `@pytest.mark.model`.

CI (`.github/workflows/ci.yml`): two jobs — `test-hermetic`
(`HF_HUB_OFFLINE=1 pytest tests/ -m "not model" -q`) and `test-e2e-model`
(model prefetch + `HF_HUB_OFFLINE=1 pytest tests/ -m "model" -q`), both
on Python 3.11.

---

## 3. Generic catalog G1–G9 and ADR-025 invariants

The catalog lives in `tests/genericos/` and is parameterized by block via
`tests/helpers/endpoint_registry.py` (`GENERIC_DEFINITIONS`,
`GENERICS_BY_BLOCK`, `ENDPOINTS_BY_BLOCK`). The canonical norm is
`docs/development/tests/SPEC-global.md`.

| ID | Name | Origin finding | Normative MUST (SPEC-global) |
|---|---|---|---|
| G1 | authentication | H3 | Every route that mutates state or exposes sensitive observability requires the operator token; without a valid token it responds 401 (fail-closed). |
| G2 | enumerated CORS | H3 | MUST NOT: the CORS policy uses the "*" wildcard with credentials; the allowed origins are explicitly enumerated. |
| G3 | WAL | L2 | Every handler that opens the database executes PRAGMA journal_mode=WAL before operating. |
| G4 | no-fake-200 | H1/M5 | MUST NOT: a persistence/DB failure returns a synthetic 200; it propagates a noisy 5xx. |
| G5 | append-only | H4/ADR-025#1 | The node history is append-only: every transition INSERTs a revision with increasing seq; UPDATE/REPLACE/DELETE on manifold_nodes is prohibited. |
| G6 | offline | M3 | The encoder is built with local_files_only=True and HF_HUB_OFFLINE=1; no network downloads at runtime. |
| G7 | determinism | M1 | Given the same state and the same inputs, the projections and the resulting state are identical. |
| G8 | contracts/ADR-007 | ADR-007 | The Pydantic contracts validate rigidly; the glyph (toon_factor) is a single character; action_potential derives from the spectrum without magic constants (ADR-005/M6). |
| G9 | TridenGuard Zero-Trust | AGENTS.md §2.3 | The TridenGuard gate blocks fragments with fetch/axios/urllib.request/import requests and verifies literal grounding. |

Representative tests of the catalog (real test_ids):

- G1: `test_g1_block_endpoints_require_token`, `test_g1_get_nodos_is_public_observation`
- G2: `test_g2_cors_enumerated_no_wildcard`
- G3: `test_g3_handlers_open_db_in_wal`, `test_g3_bootstrap_anchors_in_wal`
- G4: `test_g4_no_fake_200_on_db_error`
- G5: `test_g5_no_destructive_statements_on_nodes`, `test_g5_consolidation_inserts_new_revision`, `test_g5_observation_no_state_mutation`
- G6: `test_g6_encoder_offline_local_files_only`
- G7: `test_g7_repetition_deterministic`
- G8: `test_g8_refinedentity_contract_rigid`, `test_g8_toon_factor_is_single_character`, `test_g8_action_potential_is_variance_no_magic`
- G9: `test_g9_blocks_network_access`, `test_g9_safety_abort_blocks`, `test_g9_grounding_literal`

Applicability matrix by block (`GENERICS_BY_BLOCK`):

| Block | Applicable generics |
|---|---|
| ingesta | G1, G2, G3, G4, G6, G7 |
| consolidacion | G1, G2, G3, G5, G7, G8 |
| relaciones | G1, G3, G5, G8 |
| mutacion | G1, G3, G5, G8 |
| observabilidad | G1, G2, G3, G4, G5, G7 |
| bootstrap | G3, G6, G7, G8 |

ADR-025 invariants (`tests/genericos/test_invariantes_adr025.py`, coverage
INV1–INV5):

- INV1 `test_invariant_1_append_only_monotonic`
- INV2 `test_invariant_2_zero_observation_mutagenicity`
- INV3 `test_invariant_3_provider_isolation`
- INV4 `test_invariant_4_dual_key_consolidation_centrality`
- INV5 `test_invariant_5_bitwise_state_determinism`

---

## 4. Domain blocks × categories

Each block has three files: `test_genericos.py` (registry coherence and
endpoint smoke), `test_especificos.py` (domain requirements of its SPEC) and
`test_e2e.py` (complete journey with the real model, `pytestmark = pytest.mark.model`).
The endpoints per block are defined in `ENDPOINTS_BY_BLOCK`.

| Block | SPEC | Endpoints | Representative examples (real test_ids) |
|---|---|---|---|
| ingesta | SPEC-ingesta.md | POST /ingesta | `test_ingestion_IN01_accepts_plain_text`, `test_ingestion_IN04_503_on_persistence_failure`, `test_ingestion_IN07_double_underscore_no_spectrum_collapse`, `test_e2e_ingestion_IN11_full_journey` |
| consolidacion | SPEC-consolidacion.md | POST /nodos/{node_id}/consolidar | `test_consolidation_CO02_threshold_excludes_self_projection`, `test_consolidation_CO03_missing_node_404`, `test_consolidation_CO06_inserts_new_revision`, `test_consolidation_CO11_key_symmetry_adr022`, `test_e2e_consolidation_CO10_full_journey` |
| relaciones | SPEC-relaciones.md | GET/POST /relations | `test_relations_RE01_endpoints_relations`, `test_relations_RE07_dangling_edge_rejected`, `test_relations_RE08_epsilon_edges_deterministic`, `test_e2e_relations_RE06_full_journey` |
| mutacion | SPEC-mutacion.md | POST /mutate/{new_symbol} | `test_mutation_MU01_logographic_genesis`, `test_e2e_mutation_MU04_full_journey` |
| observabilidad | SPEC-observabilidad.md | GET /nodos; GET /telemetry | `test_observability_OB01_cors_enumerated`, `test_observability_OB04_nodes_excludes_telemetry_max_seq`, `test_observability_OB05_db_error_real_5xx`, `test_observability_OB06_telemetry_requires_token` |
| bootstrap | SPEC-bootstrap.md | (no HTTP surface) | `test_bootstrap_BO01_roundtrip_serialization`, `test_bootstrap_BO04_encoder_app_offline`, `test_bootstrap_BO07_does_not_expose_http_endpoints` |

The per-block E2E journeys (IN11, CO10, RE06, MU04, OB09, BO08) run with
the real model and frozen realistic geometry (`seed="realistic"`), without
network (`HF_HUB_OFFLINE=1`).

---

## 5. Claims layer

`tests/afirmaciones/claims_registry.py` declares each documentary claim of the
Traianus sources with a state: **ACTIVE** (verified by test), **RED** (not
met; `disposition` = `CODE_FIX | DOC_FIX`) or **WP** (explicit scope
exclusion in the PoC). Norm: `docs/development/tests/SPEC-afirmaciones.md`.

As of 2026-08-01 the 9 claims of the registry are **ACTIVE**, all with a test:

| Claim | Source | Test file |
|---|---|---|
| CL-C41 | CONTRACTS_AND_PRISMS.md C-4.1 | `test_cl_c41_telemetry.py` |
| CL-I5 | PROJECT_IDENTITY.md I-5 | `test_cl_i5_zero_ui.py` |
| CL-I61 | ADR-016 | `test_cl_i61_zero_llm.py` |
| CL-I62 | I-6.2 / L6 | `test_cl_i62_dimension_provider.py` |
| CL-R1 | README R-1 / M4 | `test_cl_r1_quickstart_bootstrap.py` |
| CL-R2 | README R-2 / M4 | `test_cl_r2_quickstart_uvicorn.py` |
| CL-WP1 | PROJECT_IDENTITY.md WP | `test_cl_wp1_exclusiones.py` |
| CL-TR1 | SPEC-afirmaciones CL-TR1 | `test_cl_tr1_trazabilidad.py` |
| CL-LIT1 | AGENTS.md §2.4 | `test_cl_lit1_grounding_literal.py` |

Function examples (real test_ids):

- CL-I62: `test_afirmaciones_CL_I62_consolidate_rejects_higher_dim` (L6
  regression: a provider with `dim_in > dim_db` responds with explicit 422),
  `test_afirmaciones_CL_I62_ingestion_higher_dim_logs_telemetry_error`.
- CL-C41: `test_afirmaciones_CL_C41_telemetry_no_traceback_leak`.
- CL-LIT1: `test_afirmaciones_CL_LIT1_literal_quote_exists` (parameterized
  over `claims_registry.LITERAL_QUOTES`).

CL-TR1 is the meta-guardian of the package: it derives the real coverage from
the test names (`test_afirmaciones_(CL_[A-Z]+\d+)`) and compares it with the
registry; it also validates that the states are `{ACTIVO, RED, WP}` and that
every RED declares `disposition`.

---

## 6. Meta-guardians, security and E2E

**Meta-guardians** (`tests/meta/`): `_spec_lib.py` (SPEC and header parsing)
+ `test_guardianes_estructura.py` with 4 guardians:

1. `test_specs_exist_and_parse` — the SPECs exist, are canonical and their
   normative IDs are unique.
2. `test_every_test_file_has_normative_header` — every test declares
   `Normative:` + `Coverage:` and an RFC 2119 word (MUST/MUST NOT/SHOULD).
3. `test_each_must_has_exactly_one_covering_file` — 1:1 traceability:
   no orphan MUSTs, no duplicates, no invented IDs (over `ACTIVE_SPECS`).
4. `test_no_test_function_is_orphan` — every `test_*` function
   references an ID from its Coverage.

**Security** (`tests/security/test_tridenguard_validator.py`): Zero-Trust
gate `tools/tridenguard_validator.py` (SEC-M-01..06, SPEC-security.md):

- SEC-M-01 invalid JSON → `INVALID_JSON`
- SEC-M-02 Safety_Abort → `BLOCKED_BY_SAFETY_GATE`
- SEC-M-03 external network → `ABORTED_VIOLATES_ZERO_TRUST`
- SEC-M-04 non-literal grounding → `ABORTED_GROUNDING_FAILED`
- SEC-M-05 valid grounding → `EXECUTE_SAFE` with `and_gate_ok`
- SEC-M-06 MCP stdio JSON-RPC server (initialize / tools/list / tools/call)
- SEC-M-07 mutating intents require target_file (no fail-open)
- SEC-M-08 canonical containment (symlinks + `..` resolved) → `ABORTED_GROUNDING_FAILED`
- SEC-M-09 null-byte (`\x00` / `\u0000`) sanitization → `ABORTED_VIOLATES_ZERO_TRUST`
- SEC-M-10 expanded network denylist (httpx/socket/urllib3/subprocess/curl/...) → `ABORTED_VIOLATES_ZERO_TRUST`
- SEC-M-11 UTF-8 binary subsequence over `read_bytes()` (fail-closed on non-UTF-8)
- SEC-M-12 silent denial (no target path / OS details in decisions)

**Security config perimeter** (`tests/security/test_opencode_permissions.py`):
Zero-Trust bash matrix of `opencode.jsonc` (SEC-M-13): no `git *` wildcard
allow; only explicit read/inspection subcommands may be `allow`, broad-first
ordering, deny primitives persist.

**Global E2E** (`tests/e2e/test_c1_consolidation_guard.py`): G10, port of the
harness `tools/audit_harness.py`, `pytestmark = pytest.mark.model`. Asserts
that with the real model and realistic geometry the dual-key consolidation rate
stays within the `[5%, 95%]` gate (C1 regression).

---

## 7. Measured health state

**Date:** 2026-08-03. **Branch:** `oss-readiness`. **Model:** `all-MiniLM-L6-v2`
offline (`HF_HUB_OFFLINE=1`, `local_files_only=True`).

Historical anchors (2026-08-01, commit `9983359`): full suite **176 passed /
2 skipped**, hermetic **169 passed / 2 skipped / 7 deselected**, model
partition **7 passed**, C1 harness **30% (6/20)**.

Current measurement (2026-08-03, OSS Readiness cycle — Fase A baseline):

* Full suite **204 passed / 2 skipped** (203 at Fase A baseline + 1 hermeticity guard added by the cycle).

| Verification | Command | Result |
|---|---|---|
| Full suite | `HF_HUB_OFFLINE=1 pytest -q` | 204 passed, 2 skipped |
| Hermetic partition | `HF_HUB_OFFLINE=1 pytest -m "not model"` | 197 passed, 2 skipped, 7 deselected |
| Model partition | `pytest -m model` | 7 passed |
| C1 guard (harness) | `python3 tools/audit_harness.py` | GUARDIA C1 PASADO EN VERDE — 45% rate (9/20), within [5%, 95%] |
| Invariant verifier (static) | `python3 tools/traianus_invariant_verifier.py` | TR-H4-001, TR-C1-001, TR-ZT-001, TR-ZT-002 OK (RED only on absent derived `traianus.db`) |
| Impact map (Fase D insumo) | `python3 tools/check_impact.py tools/tridenguard_validator.py` | 14 references (MCP, tests, docs) — validator stays in `tools/` |

The hermetic partition (197 + 7 = 204) covers Phases 0–5 of the harness; the
`model` partition covers Phase 6 (C1 guard G10 + per-block E2E journeys). The
`197 + 7 = 204` consistency and the intentional `2 skips` (bootstrap without
HTTP surface) are the health invariants of the suite.

Hermeticity hardening (OSS Readiness Fase A): `tests/conftest.py` now forces
`os.environ.setdefault("HF_HUB_OFFLINE", "1")` before importing
`traianus.app`, guarded by `test_conftest_forces_hf_hub_offline`
(`tests/meta/test_hermetic_import.py`, coverage HERMETIC-IMPORT).

---

## 8. How to contribute

Normative rules (RFC 2119) for adding a new test without breaking the suite:

- **Location:** the test MUST live in the directory of its layer:
  `tests/genericos/` (G1–G9 catalog or invariants), `tests/bloques/<bloque>/`
  (specific or E2E), `tests/afirmaciones/` (claims), `tests/security/`
  (TridenGuard gate) or `tests/e2e/` (global guards).
- **Normative header:** every test file MUST declare in its header docstring
  `Normative: docs/development/tests/SPEC-<bloque>.md` and
  `Coverage: <ID1>, <ID2>, ...`, and include an RFC 2119 word
  (MUST/MUST NOT/SHOULD) — this is verified by
  `test_every_test_file_has_normative_header`.
- **Naming (mixed convention):** identifiers (test function names,
  variables, constants and dict keys) MUST be in English; docstrings,
  comments, assertion messages, `print` statements and string literals may be
  in Spanish. The function MUST follow
  `test_<BLOQUE>_<ID>_<behavior>` (e.g.
  `test_ingestion_IN01_accepts_plain_text`), or reference the ID in its
  docstring — this is verified by `test_no_test_function_is_orphan`.
- **1:1 Traceability:** if the test covers a new MUST, the ID MUST be added to
  the corresponding SPEC BEFORE the test (Spec-First); each MUST of
  `ACTIVE_SPECS` MUST have exactly one covering file — this is verified by
  `test_each_must_has_exactly_one_covering_file`.
- **DDL and geometry:** if the test needs tables, it MUST use
  `helpers/db_factory.create_test_db` (single DDL source); for realistic
  geometry use `seed="realistic"` (fixture `nsm_axes_8.json`), do not invent
  one-hot axes outside the C1 regression tests that require them.
- **Hermeticity:** unit tests MUST NOT load the real model nor access the
  network; use `@pytest.mark.model` only for the E2E journeys that require
  cached MiniLM. In CI, the hermetic partition (`-m "not model"`) and the
  model partition (`-m "model"`) are independent.
- **Claims:** a new documentary claim MUST be declared in
  `tests/afirmaciones/claims_registry.py` with state ACTIVE/RED/WP and an
  associated test; if RED, it MUST include `disposition` (`CODE_FIX | DOC_FIX`).
