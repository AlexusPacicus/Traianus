# 🧭 Traianus — State Consolidation and Logographic Synchronization (2026-08-01)

> **Versionable governance document.** Produced by `@logographer` as Phase 1 of the
> Action Plan issued by `@plan-architect` (branch `ngi-candidacy`). It records the verified
> git state, the diff summary by area, the `AGENTS.md` invariant matrix,
> the *Doc-Drift* catalog D1–D10, and the routable recommendations R1–R5 (pending
> execution by `@fixer`/`@orchestrator`).
>
> **Scope:** this cycle (Phases 1–3) only modifies `docs/` (this document,
> `docs/LOGOGRAPHY.md`, `docs/architecture/opencode_architecture.md`, and
> `docs/development/bitacora.md`). It does NOT touch `traianus/`, `tests/`, `tools/`, or `.gitignore`.

---

## 1. Git State

| Ref | Hash | Note |
| --- | --- | --- |
| `ngi-candidacy` (HEAD) | `76845a612c91d9c3a04880b8a0cce4fd90749c7b` (`76845a6`) | Current working branch (`.git/HEAD` → `refs/heads/ngi-candidacy`) |
| `origin/main` | `e2ab8bc554fd6d31443b58d0e9a2c786e951d9c3` (`e2ab8bc`) | Diff base |
| `main` (local) | identical to `origin/main` (`e2ab8bc`) | Fast-forward merge of `fix/axis-key-parsing-and-ethical-key` |

**Branch not pushed to origin:** `ngi-candidacy` has no remote ref (`origin/ngi-candidacy`); the full
diff is **10057 lines / 90 files** against `origin/main` (measurement from the verified
`@plan-architect` report).

### 1.1 Reflog of the 5 `ngi-candidacy` commits (from `e2ab8bc`)

| # | Short hash | Full hash | Date (epoch) | Message |
| --- | --- | --- | --- | --- |
| 1 | `cd6aad58` | `cd6aad583e7d82d460814f9ecd49a7ca9d1f4cf4` | 1785606203 | `Audit cycle F1-F3: green C1 harness, append-only node log (H4), synced audit` |
| 2 | `b9a0f89b` | `b9a0f89b899d55e5610b1e866f7c42f8b0b10b83` | 1785611956 | `Harden opencode cycle #008: MCP validator v1.1.0, 5 subagents Zero-Trust, CI, quickstart` |
| 3 | `9983359` | `998335960fb4db25bb82b4ec9c0954363f33caad` | 1785611958 | `Sync AGENTS.md constitution with 5-agent topology (plan-architect, orchestrator)` |
| 4 | `75b2809` | `75b2809f18ef6043a326f210489ac1532dfaa56a` | 1785612293 | `Materialize opencode commands/skills (F3-F4) and harden config (F5): permissions, providers, mcp_timeout` |
| 5 | `76845a6` | `76845a612c91d9c3a04880b8a0cce4fd90749c7b` | 1785615022 | `feat(audit): refactor traianus package, spec-first test suite and mcp validator v1.1.0aa` |

Source: `.git/logs/HEAD` (lines 23–27).

---

## 2. Diff summary by area

| Area | Scope | Status |
| --- | --- | --- |
| **Code** | `py/main.py` → `traianus/app.py`; `py/geodesic_bootstrap.py` → `traianus/bootstrap.py` (M4, real package) | ✅ Refactored |
| **Audit fixes C1/H1/H2/H3/M3/M5/M6/M7** | C1 (self-projection excluded), H1 (503 on persistence), H2 (allowlist `text/plain`), H3 (enumerated CORS + operator token), M3 (offline/local_files_only), M5 (5xx/telemetry token), M6 (`action_potential` without magic scale), M7 (consolidation inserts a revision) | ✅ Applied with deterministic tests |
| **H4 / H5** | H4: `manifold_nodes` as append-only log `(id, seq)`; H5: deterministic `E_n` (`_compute_epsilon_edges`/`rebuild_epsilon_edges`/`persist_epsilon_edges`, RE-08/RE-09) | 🟠 Partial: `manifold_edges` remains mutable; `K_n` unimplemented |
| **L6 / CL-I62** | `dim_in > dim_db` → explicit rejection (422 in `/nodos/{id}/consolidar`; telemetry_error in ingestion) | ✅ Implemented and verified by `test_afirmaciones_CL_I62_*` |
| **Spec-First tests** | `tests/` restructure (Phases 0–6): conftest, helpers, G1–G9, blocks, meta-guardians, claims, security, e2e, 2-job CI | ✅ **174 passed / 2 skipped** |
| **Ops / Governance** | `opencode.jsonc` (instructions, local MCP, permissions), `.opencode/agents/*` (5 Zero-Trust subagents), `AGENTS.md` (constitution), MCP `tridenguard-validator` v1.1.0, `.github/workflows/ci.yml` | ✅ Configured |

---

## 3. `AGENTS.md` invariant matrix

| # | Invariant | Status | Evidence (path:line) |
| --- | --- | --- | --- |
| 1 | Consult `TRAIANUS_AUDITORIA_ES.md` before refactoring `traianus/app.py` | ⚠️ **Doc-Drift D1**: the file is referenced but ABSENT from the working tree (see §4) | `opencode.jsonc:6`, `docs/architecture/opencode_architecture.md:52,140,199`, content in `CHANGES_FULL.diff:841-1283` |
| 2 | Exclude the self-projection ($i = j$, value 1.0) when calibrating `auto_calibrate_critical_threshold()` | ✅ Verified | `traianus/app.py:255-264`, literal quote in `traianus/app.py:262` — `for j, other in enumerate(vectors) if j != i`; regression `test_auto_calibrate_excludes_self_projection` |
| 3 | Zero-Trust and network: block external requests; Uvicorn on `127.0.0.1`; no wildcard CORS with credentials | ✅ Verified | `opencode.jsonc:8-16` (local stdio MCP); `TRAIANUS_AUDIT.md:75-76` (MIME allowlist and enumerated CORS); `tools/tridenguard_validator.py` (Zero-Trust Gate) |
| 4 | Literal grounding: the quote in `Topological_Grounding` must exist exactly in the source | ✅ Verified | Validator's Grounding Gate (REFACTOR/FIX/AUDIT with `target_file`); tests `tests/afirmaciones/test_cl_lit1_grounding_literal.py` (CL-LIT1) |
| 5 | Immutable persistence (*Append-Only*): no `UPDATE`/`DELETE` on history; revisions with increasing `seq` | ✅ Verified (H4 partial) | `traianus/app.py:126-140` — `PRIMARY KEY (id, seq)`; H4 regression in `tests/genericos/test_g5_append_only.py` + `tests/bloques/consolidacion/test_especificos.py` |

---

## 4. Doc-Drift catalog D1–D10

| ID | Severity | Description | Literal quote (path:line) | Recommendation |
| --- | --- | --- | --- | --- |
| **D1** | 🔴 Critical | `TRAIANUS_AUDITORIA_ES.md` referenced as a governance instruction but ABSENT from the working tree (content available in the diff) | `opencode.jsonc:6` — `"instructions": ["TRAIANUS_AUDITORIA_ES.md", "docs/LOGOGRAPHY.md"]`; `docs/architecture/opencode_architecture.md:52,140,199`; `CHANGES_FULL.diff:841` — `diff --git a/TRAIANUS_AUDITORIA_ES.md b/TRAIANUS_AUDITORIA_ES.md` | **R2** |
| **D2** | 🔴 Critical (breaks CI) | `.gitignore:19` ignores `docs/development/`, but the meta-guardians read it at runtime → the hermetic CI will fail on a fresh GitHub clone | `.gitignore:19` — `docs/development/`; `tests/meta/_spec_lib.py:13` — `SPEC_DIR = os.path.join(ROOT, "docs", "development", "tests")`; `tests/meta/test_guardianes_estructura.py:43-47,72-80` | **R1** |
| **D3** | 🟠 | `LOGOGRAPHY.md:33` declares CL-I62 RED; the registry and the code declare it ACTIVE (CODE_FIX applied) | `docs/LOGOGRAPHY.md:33` — `CL-I62 remains RED (CODE_FIX pending: dimension greater than basis).`; `tests/afirmaciones/claims_registry.py:33` — `"state": "ACTIVE"`; `traianus/app.py:390-397` — `raise HTTPException(status_code=422, ...)` | ✅ **Fixed in Phase 2** |
| **D4** | 🟠 | `LOGOGRAPHY.md:33` references `tests/claims/`; the real directory is `tests/afirmaciones/` | `docs/LOGOGRAPHY.md:33` — `` `tests/claims/` `` | ✅ **Fixed in Phase 2** |
| **D5** | 🟡 | `LOGOGRAPHY.md` has out-of-order sections: 4 → 6 → 5 | `docs/LOGOGRAPHY.md:21,27,40` | ✅ **Fixed in Phase 2** |
| **D6** | 🟠 | `Project_architecture.md` documents a legacy `id TEXT PRIMARY KEY` schema; the code uses a composite PK `(id, seq)` | `docs/architecture/Project_architecture.md:93` — `id TEXT PRIMARY KEY,`; `traianus/app.py:138` — `PRIMARY KEY (id, seq)` | **R4** |
| **D7** | 🟡 | `TEST_OVERVIEW.md` quotes commit `9983359`; HEAD is `76845a6` | `docs/development/tests/TEST_OVERVIEW.md:3,242` — `commit \`9983359\`` | Pending (future documentary adjustment, Logography cycle) |
| **D8** | 🟡 | `bitacora.md` has two `Registro #011` (duplicate numbering) | `docs/development/bitacora.md:132` and `:145` | Pending (append-only: previous entries are not renumbered; the current cycle records `#012`) |
| **D9** | 🟡 | `opencode_architecture.md:211` pins `34 passed` (historical) without anchoring the current state | `docs/architecture/opencode_architecture.md:211` — `ciclo #008 cerrado con \`python3 -m pytest tests/ -q\` → **34 passed**` | ✅ **Fixed in Phase 3** |
| **D10** | 🟠 | `TRAIANUS_AUDIT.md:78` (H5) claims `E_n` unimplemented; the code implements deterministic `E_n` (RE-08/RE-09) | `TRAIANUS_AUDIT.md:78` — `` `E_n` (ε-adjacency) and `K_n` (faces) still unimplemented ``; `traianus/app.py:591-659` — `_compute_epsilon_edges`/`rebuild_epsilon_edges`/`persist_epsilon_edges` | **R3** |

---

## 5. Routable recommendations R1–R5 (for `@orchestrator`/`@fixer`)

> These recommendations are NOT executed in this cycle (Phases 1–3 are documentation-only).
> They are routed to `@fixer` under `@orchestrator`'s direction, with deterministic validation
> (`pytest tests/ -q` and `python3 tools/audit_harness.py`).

| # | Recommendation | Grounding (path:line) | Impact |
| --- | --- | --- | --- |
| **R1** | Remove `docs/development/` from `.gitignore:19` (D2) | `.gitignore:19`; `tests/meta/_spec_lib.py:13` | Unblocks the hermetic CI on a fresh clone (the SPECs must be versioned) |
| **R2** | Restore `TRAIANUS_AUDITORIA_ES.md` from `CHANGES_FULL.diff:841-1283` (D1) | `opencode.jsonc:6`; `CHANGES_FULL.diff:841-846` (`new file mode 100644`, 436 lines) | Restores the root instruction of `AGENTS.md` Invariant 1 |
| **R3** | Sync `TRAIANUS_AUDIT.md:77-78` (H4/H5) with the current implementation (D10) | `TRAIANUS_AUDIT.md:77-78`; `traianus/app.py:126-140,591-659` | H5 is no longer "still unimplemented"; document partial progress and the pending `K_n`/`manifold_edges` |
| **R4** | Update the schema in `docs/architecture/Project_architecture.md:92-102` to PK `(id, seq)` (D6) | `Project_architecture.md:93`; `traianus/app.py:126-140` | Eliminates the documented-schema vs real-schema contradiction (H4) |
| **R5** | Commit `flake.lock` (M8) | `flake.nix:10` — `nixpkgs.url = "github:NixOS/nixpkgs/148bab9c1c3c53136ecb44a6ea356a0ed5b39b06"` | Closes M8 (Nix reproducibility); requires `nix flake lock` on a host with Nix |

**Additional pending items (not routed):** D7 (refresh the commit in `TEST_OVERVIEW.md:3,242` to `76845a6`) and
D8 (duplicate `Registro #011` in `bitacora.md`; renumbering falls outside append-only and will
be resolved in a future Logography cycle if `@orchestrator` approves it).

---

## 6. Acceptance criteria and literal grounding quotes

### 6.1 Verified literal quotes (CL-LIT1)

Each quote was checked character by character against the working tree in this cycle:

| Path:line | Verified quote |
| --- | --- |
| `docs/LOGOGRAPHY.md:33` | `CL-I62 remains RED (CODE_FIX pending: dimension greater than basis).` |
| `tests/afirmaciones/claims_registry.py:32-33` | `"source": "I-6.2 / L6"`, `"state": "ACTIVE"` (CL-I62) |
| `traianus/app.py:262` | `for j, other in enumerate(vectors) if j != i` (C1) |
| `traianus/app.py:126-140` | `CREATE TABLE IF NOT EXISTS manifold_nodes (... PRIMARY KEY (id, seq))` (append-only block H4) |
| `traianus/app.py:390-397` | `if dim_in > dim_db: raise HTTPException(status_code=422, ...)` (L6/CL-I62) |
| `traianus/app.py:591-659` | `_compute_epsilon_edges` / `rebuild_epsilon_edges` / `persist_epsilon_edges` (H5 partial, RE-08/RE-09) |
| `tests/meta/_spec_lib.py:13` | `SPEC_DIR = os.path.join(ROOT, "docs", "development", "tests")` |
| `.gitignore:19` | `docs/development/` |
| `opencode.jsonc:6` | `"instructions": ["TRAIANUS_AUDITORIA_ES.md", "docs/LOGOGRAPHY.md"]` |
| `CHANGES_FULL.diff:841-846` | `diff --git a/TRAIANUS_AUDITORIA_ES.md b/TRAIANUS_AUDITORIA_ES.md` / `new file mode 100644` |
| `docs/architecture/Project_architecture.md:92-102` | legacy `id TEXT PRIMARY KEY` schema (manifold_nodes) |
| `TRAIANUS_AUDIT.md:77-78` | H4 status rows (`Open (partial progress)`) and H5 (`Open` / `E_n ... still unimplemented`) |

### 6.2 Cycle acceptance criteria

1. **Phases 1–3 only touch `docs/`**: `docs/STATE_CONSOLIDATION_2026-08-01.md` (new),
   `docs/LOGOGRAPHY.md`, `docs/architecture/opencode_architecture.md`, and
   `docs/development/bitacora.md` (Registro #012). No changes in `traianus/`, `tests/`,
   `tools/`, or `.gitignore`.
2. **Green suite unchanged**: with no code modifications, `pytest tests/ -q` must remain at
   **174 passed / 2 skipped** and `python3 tools/audit_harness.py` at **GUARDIA C1 VERDE**
   (rate 30%, within `[5%, 95%]`).
3. **Meta-guardians independent of the Logography**: `tests/meta/_spec_lib.py` only reads
   `docs/development/tests/SPEC-*.md` and test headers; no test references
   `LOGOGRAPHY.md`, `STATE_CONSOLIDATION_2026-08-01.md`, `opencode_architecture.md`, or
   `Project_architecture.md` (verified by grep in `tests/`).
4. **Literal grounding**: every claim in this document exists character by character at the
   cited path:line (§6.1).
5. **D3/D4/D5 resolved** in `LOGOGRAPHY.md`; **D9 resolved** in `opencode_architecture.md`;
   **D1/D2/D6/D10** documented with recommendations R1–R5 for `@fixer`; **D7/D8** documented
   as pending.

---

## 7. De-bureaucratization of the test suite (governance decision, 2026-08-01)

> **Scope:** executive slimming cycle. Removes `tools/` and `docs/templates/` (Registro #013
> of `bitacora.md`). Adding a "freeze" rule to `AGENTS.md`/`METHODOLOGY.md` was rejected:
> codifying an anti-bureaucracy rule would, in itself, be bureaucracy.

| # | Decision | Executed action | Impact |
| --- | --- | --- | --- |
| **1** | Remove the *dead matter*: contract mining pilot | `tools/contract_obligation_verifier.py` (205 lines) and `docs/templates/contract-mining/` deleted | It does not run in the substrate runtime nor in the Pytest suite; conceptual weight with no contribution to the real executable |
| **2** | Do not add new governance bureaucracy | No changes in `AGENTS.md` or `METHODOLOGY.md` | The proposed rule 6 (*Test Suite Freeze*) was rejected: it is redundant and contradicts the goal of slimming down |

**Regression verified after removal:** `pytest tests/ -m "not model" -q` → 169 passed, 2 skipped
(without changing the hermetic-layer result; the removed verifier had no tests of its own in the suite).
