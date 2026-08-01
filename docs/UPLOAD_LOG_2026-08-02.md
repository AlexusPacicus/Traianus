# 📤 Traianus — Upload Log 2026-08-02 (`ngi-candidacy` → `origin/main`)

> **Versionable governance document.** Prepared by `@logographer` to record **everything that
> will be uploaded** to GitHub on the 2026-08-02 cycle: the branch `ngi-candidacy` with its
> **unique base commit `d349350`** (result of **squashing the 8 commits** of the pre-candidacy
> history against `origin/main` `e2ab8bc`), the aggregated diff summary (**108 archivos,
> +10079/−936**), the validation state, and the Doc-Drift findings that must be resolved
> (or explicitly accepted) before the push.
>
> **Methodological note (shell access):** this `@logographer` session **did not have a `bash`
> execution tool** in its environment. `git status`/`git diff`/`git log` could not be executed
> as commands. The git state below was **reconstructed from readable `.git/` internals and the
> filesystem** (`.git/HEAD`, `.git/refs/heads/ngi-candidacy`, `.git/refs/heads/backup/pre-squash-8`,
> `.git/refs/remotes/origin/main`, `.git/logs/HEAD`, `.git/COMMIT_EDITMSG`, `.gitignore`, full
> working-tree inventory) plus the **user-verified context** (clean `git status --short`;
> `git show --stat d349350` → **108 archivos, +10079/−936**; hermetic suite measured on
> 2026-08-02).
>
> **Scope:** ONLY documentation (`docs/`). This cycle does not modify source code, does not
> re-run `pytest`, and does not create commits (AGENTS.md §4). The only working-tree change
> resulting from this session is this document.

---

## 1. Governance Header

| Field | Value |
| --- | --- |
| **Purpose** | Register the GitHub upload of cycle 2026-08-01/02: branch `ngi-candidacy` vs `origin/main` |
| **Origin branch** | `ngi-candidacy` (local only; no remote ref `origin/ngi-candidacy`) |
| **Base (upstream)** | `origin/main` @ `e2ab8bc554fd6d31443b58d0e9a2c786e951d9c3` |
| **HEAD / base commit** | `d3493509917d0d8145a9041544936c768a2f0213` (`d349350`) — `feat(candidatura): base Traianus/TridenGuard — substrate espacial determinista + firewall neuro-simbólico (NGI)` |
| **History** | **Squashed**: the 8 pre-candidacy commits (`cd6aad5`…`5e12912`) were unified into `d349350`; the original history is preserved **locally** at `backup/pre-squash-8` (tip `5e12912`) — **NOT uploaded** |
| **Commits pending upload** | **1** (unique base commit `d349350`) |
| **Working tree** | Clean before this session (user-verified); after this edit: only `docs/UPLOAD_LOG_2026-08-02.md` modified |
| **Validation** | `pytest tests/ -m "not model" -q` → **169 passed / 2 skipped / 7 deselected** (verified 2026-08-02; tree byte-identical to the already-validated pre-squash tree) |
| **Next bitacora record** | **#016** (⚠️ see note in Section 6.1: the context assumed #014, but the gitignored `bitacora.md` already contains Records #014 and #015) |

---

## 2. Git State Measured

Source: `.git/HEAD`, `.git/refs/heads/ngi-candidacy`, `.git/refs/heads/backup/pre-squash-8`, `.git/refs/remotes/origin/main`, `.git/logs/HEAD` (lines 30–32).

| Ref | Hash | Observation |
| --- | --- | --- |
| `ngi-candidacy` (HEAD) | `d3493509917d0d8145a9041544936c768a2f0213` (`d349350`) | Current working branch — **unique base commit** post-squash (`.git/refs/heads/ngi-candidacy`) |
| `origin/main` | `e2ab8bc554fd6d31443b58d0e9a2c786e951d9c3` (`e2ab8bc`) | Diff base — unchanged |
| `backup/pre-squash-8` | `5e12912a155fd1740881430721f7257be84929ea` (`5e12912`) | **Local** branch (`.git/refs/heads/backup/pre-squash-8`) preserving the original 8-commit history — **NOT uploaded** |
| `main` (local) | identical to `origin/main` (`e2ab8bc`) | Fast-forward merge of `fix/axis-key-parsing-and-ethical-key` |

**Squash event (reflog):** the 8 pre-candidacy commits `cd6aad5` → `5e12912` were unified.
`.git/logs/HEAD` lines 30–32 record: `5e12912` (pre-squash tip) → `reset: moving to origin/main`
→ `commit: feat(candidatura): base Traianus/TridenGuard …` (`d349350`).

> **🔍 Transparency note (pre-squash hashes):** any hash cited in earlier sections of this
> document (`cd6aad5`, `b9a0f89`, `9983359`, `75b2809`, `76845a6`, `8d0ba22`, `b7adf44`,
> `5e12912`) belongs to the **pre-squash history**, preserved locally at
> `backup/pre-squash-8` (branch tip `5e12912`). Those commits are **not parents of `HEAD`**
> anymore (rewritten history); they exist only on the local backup branch and are referenced
> here for transparency/traceability of the squashed content.

### 2.1 The unique base commit `d349350` (squash of 8 commits)

Commit message body (`.git/COMMIT_EDITMSG`):

```
feat(candidatura): base Traianus/TridenGuard — substrate espacial determinista + firewall neuro-simbólico (NGI)

Branch base para candidatura NGI (unica commit; historia previa en backup/pre-squash-8).

Contenido:
- Traianus: package traianus/ (app.py + bootstrap), topologia E_n (adyacencia-epsilon) persistida atomicamente en consolidacion (H5/WP2), C1 threshold sin auto-proyeccion, WAL, append-only node log (H4), grounding literal.
- TridenGuard: MCP validator v1.1.0aa (tools/tridenguard_validator.py), Zero-Trust gate (5 Radicales).
- Suite spec-first: 108 tests (genericos G1-G9, bloques, afirmaciones CL-*, meta-guardians, security), 169 passed / 2 skipped / 7 deselected (hermetico).
- Gobernanza: AGENTS.md 5-agentes, opencode commands/skills, CI (2 jobs), docs (STATE_CONSOLIDATION, DIF_LOG, UPLOAD_LOG, TRAIN_AUDIT, Logography), SPECs + METHODOLOGY versionados (R1/D2).
```

**8 commits absorbed** (from reflog; full decomposition preserved in `backup/pre-squash-8`):

| # | Short Hash | Message (first line) |
| --- | --- | --- |
| 1 | `cd6aad5` | `Audit cycle F1-F3: green C1 harness, append-only node log (H4), synced audit` |
| 2 | `b9a0f89` | `Harden opencode cycle #008: MCP validator v1.1.0, 5 subagents Zero-Trust, CI, quickstart` |
| 3 | `9983359` | `Sync AGENTS.md constitution with 5-agent topology (plan-architect, orchestrator)` |
| 4 | `75b2809` | `Materialize opencode commands/skills (F3-F4) and harden config (F5): permissions, providers, mcp_timeout` |
| 5 | `76845a6` | `feat(audit): refactor traianus package, spec-first test suite and mcp validator v1.1.0aa` |
| 6 | `8d0ba22` | `feat(topologia): materializar adyacencia-epsilon E_n atomicamente en consolidacion (H5 / WP2)` |
| 7 | `b7adf44` | `docs(governance): consolidar ciclo 2026-08-01/02 — rename TRAIANUS_AUDIT, STATE_CONSOLIDATION+DIF_LOG, deburocratizacion contract-mining y sync docs/opencode (R1-R5)` |
| 8 | `5e12912` | `fix(ci): versionar SPECs + METHODOLOGY (R1/D2) y limpiar artefactos locales` |

---

## 3. What Will Be Uploaded

One commit — the **unique base commit `d349350`** — whose scope aggregates the 8 squashed
commits above:

| Hash | Message | Scope — key files | What it does (aggregated) |
| --- | --- | --- | --- |
| `d349350` | `feat(candidatura): base Traianus/TridenGuard — substrate espacial determinista + firewall neuro-simbólico (NGI)` | `traianus/` (`app.py`, `bootstrap.py`, `__init__.py`); `tools/` (`audit_harness.py`, `tridenguard_validator.py`, `export_nsm_axes.py`); `tests/` (59 `.py` — spec-first suite); `.opencode/` (5 agents + 3 commands + 2 skills); `opencode.jsonc`, `AGENTS.md`, `.github/workflows/ci.yml`, `pyproject.toml`, `README.md`, `README_CODE_ENGINE.md`, `TRAIANUS_AUDIT.md`, `IMPLEMENTATION_STATUS.md`; `docs/` (Logography, STATE_CONSOLIDATION, DIF_LOG, UPLOAD_LOG, **SPECs + METHODOLOGY versionados**) | **Traianus:** refactor `py/` → `traianus/`; topología `E_n` (adyacencia-epsilon) persistida atómicamente en consolidación (H5/WP2); C1 threshold sin auto-proyección; WAL; nodos append-only `(id, seq)` (H4); grounding literal. **TridenGuard:** MCP validator v1.1.0aa + Zero-Trust gate (5 Radicales). **Suite spec-first:** 108 tests (G1–G9, bloques, afirmaciones CL-*, meta-guardians, security, e2e G10); CL-I62 ACTIVE (`dim_in > dim_db` → 422). **Gobernanza:** 5 agentes Zero-Trust, commands/skills, CI 2 jobs, SPECs + METHODOLOGY versionados (R1/D2), docs de consolidación |

---

## 4. Diff Summary of the Upload (`origin/main...HEAD`)

### 4.1 Measured total

`git show --stat d349350` (vs parent `origin/main` `e2ab8bc`) → **108 archivos / +10079 −936**
(user-verified 2026-08-02; the tree is byte-identical to the already-validated pre-squash tree,
so the measured stat of the 8-commit history carries over to the single squashed commit).

### 4.2 Per-block inventory of the uploaded tree (measured in this session)

File counts from the full working-tree inventory (versioned content; `bitacora.md`,
`working_tree.md`, `SYNC_PLAN.md`, `TEST_OVERVIEW.md`, caches and runtime artifacts are
gitignored — `.gitignore:20–24`).

| Block | Files in the uploaded tree | What enters the diff |
| --- | --- | --- |
| `docs/` | **25** (24 `.md` + `docs/audit/triden_guard_code_engine_v4.json`) | Logography, UPLOAD_LOG, governance docs (STATE_CONSOLIDATION, DIF_LOG), **11 development docs versionados (10 `SPEC-*.md` + `METHODOLOGY.md`, R1/D2)** — the rest of `docs/development/` (`bitacora.md`, `working_tree.md`, `TEST_OVERVIEW.md`) remains gitignored (D2) |
| `tests/` | **59** `.py` | Spec-first suite: conftest, helpers, genericos G1–G9, 6 blocks × 3 categories, meta-guardians, afirmaciones (claims), security, e2e |
| `tools/` | **4** | `audit_harness.py`, `tridenguard_validator.py`, `export_nsm_axes.py`, `__init__.py`; `contract_obligation_verifier.py` **deleted** (Record #013) |
| `traianus/` | **3** | `app.py` (incl. `E_n` atomic persistence), `bootstrap.py`, `__init__.py` (renamed from `py/`) |
| `.opencode/` | **10** (5 agents + 3 commands + 2 skills) | New in the hardened opencode cycle |
| CI | **1** | `.github/workflows/ci.yml` (2 jobs: hermetic / real-model) |
| Root | **10** | `AGENTS.md`, `opencode.jsonc`, `pyproject.toml`, `README.md`, `README_CODE_ENGINE.md`, `LICENSE`, `flake.nix`, `IMPLEMENTATION_STATUS.md`, `TRAIANUS_AUDIT.md`, `requirements.txt` |

**Tree total ≈ 112** (25 + 59 + 4 + 3 + 10 + 1 + 10); the **authoritative measured diff** is
**108 archivos / +10079 −936** (`git show --stat d349350`). The small difference is expected:
the tree count includes files unchanged relative to `origin/main` (pre-existing
`docs/identity/`, `docs/research/`, `docs/architecture/`, etc.) that are therefore not listed
by the stat, plus rename/delete detection (`TRAIANUS_AUDITORIA_ES.md` → `TRAIANUS_AUDIT.md`;
`tools/contract_obligation_verifier.py` deleted).

---

## 5. Validation State

| Check | Result | Source |
| --- | --- | --- |
| Hermetic suite | `pytest tests/ -m "not model" -q` → **169 passed / 2 skipped / 7 deselected** | User-verified **2026-08-02**; consistent with Record #013 and the `d349350` commit message |
| C1 guard (harness) | Green — consolidation rate in `[5%, 95%]` (30% = 6/20 calibrated corpus) | `tools/audit_harness.py` (unchanged in the squash) |
| E2E real-model job | `-m "model"` partition → **7 tests** (CI job 2, with cached model) | `pyproject.toml` markers; `.github/workflows/ci.yml` |
| **⚠️ Fresh-clone risk** | **RESOLVED by the squash (R1/D2):** `docs/development/methodology/METHODOLOGY.md` and `docs/development/tests/SPEC-*.md` are now versioned (`.gitignore:20–24`), so `tests/meta/_spec_lib.py` finds `SPEC_DIR` on a fresh clone | `.gitignore:21–24`; `tests/meta/_spec_lib.py:13` |

---

## 6. Governance Notes and Doc-Drift Findings

### 6.1 Working tree cleanliness and context corrections

- **Clean tree before this session:** `git status --short` verified clean by the user after the
  squash (`d349350`); the filesystem inventory confirms that all non-ignored files are part of
  the committed tree (`TRAIANUS_AUDITORIA_ES.md` is gone — rename applied; `flake.lock` does
  not exist).
- **After this session:** the working tree contains **exactly one modification** —
  `docs/UPLOAD_LOG_2026-08-02.md` (this document).
- **⚠️ Bitacora record correction (context drift):** the instruction context assumed the next
  record in `docs/development/bitacora.md` would be **#014**, but the gitignored bitacora
  already contains **Records #014** (Spanish docstrings reversion) and **#015** (mixed English
  identifiers). The next append-only record is **#016** — reference only; bitacora was NOT
  modified (gitignored, per the cycle rules).
- **Squash decision:** the 8-commit history was unified into `d349350` for a clean candidacy
  base; the original history remains recoverable at the local branch `backup/pre-squash-8`
  (tip `5e12912`). **The backup branch must NOT be pushed.**

### 6.2 Pending items detected for this upload (Doc-Drift)

| ID | Severity | Description | Literal grounding | Status |
| --- | --- | --- | --- | --- |
| **M8 / R5** | 🟡 | `flake.lock` still unversioned (only `flake.nix` exists) → Nix reproducibility claim open | `flake.nix` present; `docs/STATE_CONSOLIDATION_2026-08-01.md:95` (R5) | PENDING (needs `nix flake lock` on a Nix host) |
| **D10 / R3** | 🟠 | `TRAIANUS_AUDIT.md:78` (H5) still says `` `E_n` (ε-adjacency) and `K_n` (faces) still unimplemented `` while `E_n` is implemented and atomically persisted (ADR-023/H5, absorbed in `d349350`) | `TRAIANUS_AUDIT.md:78`; `traianus/app.py:48` (`EPSILON_EDGE`), `traianus/app.py:561` | PENDING sync (documentation-of-documentation: audit vs code) |
| **D11** | 🟡 | `docs/LOGOGRAPHY.md:25` lists `SPEC-{…, claims, …}.md`; the actual file is `SPEC-afirmaciones.md` (canonical in `tests/meta/_spec_lib.py:23`) | `docs/LOGOGRAPHY.md:25` — `…, bootstrap, claims, security}` | PENDING (minor; now that SPECs are versioned, visible to reviewers) |
| **D7 / D12** | 🟡 | `docs/development/tests/TEST_OVERVIEW.md` (gitignored) anchors stale commits/counts (`174 passed` at line 46 of LOGOGRAPHY vs `176 passed / 2 skipped` total and `169 / 2 / 7` hermetic) | `docs/LOGOGRAPHY.md:46` — `measured state (174 passed / 2 skipped)` | PENDING (gitignored — not part of the upload) |
| **D8** | 🟡 | `bitacora.md` has duplicate `Registro #011` numbering | `docs/development/bitacora.md:132` and `:145` | PENDING (append-only; renumbering needs `@orchestrator` consent) |
| **Logography sync** | — | This document (`docs/UPLOAD_LOG_2026-08-02.md`) is not yet referenced in `docs/LOGOGRAPHY.md` §5 | — | After `@orchestrator` approval |

### 6.3 Resolved in this cycle (verified in the uploaded tree)

| ID | Status | Evidence |
| --- | --- | --- |
| **R1 / D2** | ✅ **Resolved (in the squash)** | `docs/development/methodology/METHODOLOGY.md` + `docs/development/tests/SPEC-*.md` (10) are versioned; `.gitignore:20–24` keeps only `bitacora.md`, `working_tree.md`, `SYNC_PLAN.md`, `TEST_OVERVIEW.md` ignored → hermetic CI reads the SPECs on a fresh clone (committed in `5e12912` → `d349350`) |
| D1 / R2 | ✅ Resolved | `TRAIANUS_AUDIT.md` exists (rename absorbed in `d349350`); `opencode.jsonc:6` → `"instructions": ["TRAIANUS_AUDIT.md", "docs/LOGOGRAPHY.md"]` |
| D3 / D4 / D5 | ✅ Resolved | `docs/LOGOGRAPHY.md` — CL-I62 ACTIVE, `tests/afirmaciones/`, sections ordered 1→6 |
| D9 | ✅ Resolved | `docs/architecture/opencode_architecture.md` anchors current state |
| Record #013 | ✅ Applied | `tools/contract_obligation_verifier.py` and `docs/templates/contract-mining/` deleted (absorbed in `d349350`) |

---

## 7. Literal Citations Verified in This Session (CL-LIT1)

Each citation was checked character-by-character against `.git/` internals or the working tree:

| Path:Line | Verified Citation |
| --- | --- |
| `.git/refs/heads/ngi-candidacy` | `d3493509917d0d8145a9041544936c768a2f0213` |
| `.git/refs/heads/backup/pre-squash-8` | `5e12912a155fd1740881430721f7257be84929ea` (local; NOT uploaded) |
| `.git/refs/remotes/origin/main` | `e2ab8bc554fd6d31443b58d0e9a2c786e951d9c3` |
| `.git/logs/HEAD:30` | `b7adf44… 5e12912… commit: fix(ci): versionar SPECs + METHODOLOGY (R1/D2) y limpiar artefactos locales` |
| `.git/logs/HEAD:31` | `5e12912… e2ab8bc… reset: moving to origin/main` |
| `.git/logs/HEAD:32` | `e2ab8bc… d349350… commit: feat(candidatura): base Traianus/TridenGuard — substrate espacial determinista + firewall neuro-simbólico (NGI)` |
| `.git/COMMIT_EDITMSG:1` | `feat(candidatura): base Traianus/TridenGuard — substrate espacial determinista + firewall neuro-simbólico (NGI)` |
| `.gitignore:20` | `# Development internals (not uploaded); SPECs + METHODOLOGY ARE versioned (R1)` |
| `.gitignore:21–24` | `docs/development/bitacora.md`, `docs/development/working_tree.md`, `docs/development/SYNC_PLAN.md`, `docs/development/tests/TEST_OVERVIEW.md` |
| `tests/meta/_spec_lib.py:13` | `SPEC_DIR = os.path.join(ROOT, "docs", "development", "tests")` |
| `docs/LOGOGRAPHY.md:25` | `SPEC-{global, ingestion, consolidation, relations, mutation, observability, bootstrap, claims, security}.md` (D11) |
| `docs/LOGOGRAPHY.md:46` | `measured state (174 passed / 2 skipped)` (D7/D12 family) |
| `docs/STATE_CONSOLIDATION_2026-08-01.md:24` | `the full diff is **10057 lines / 90 files** against \`origin/main\`` (historical baseline at `76845a6`) |
| `TRAIANUS_AUDIT.md:78` | `` `E_n` (ε-adjacency) and `K_n` (faces) still unimplemented `` (D10/R3) |
| `flake.nix` (root) | present; `flake.lock` **absent** (M8/R5) |

---

## 8. Pre-Push Verification Checklist (run on the shell before `git push`)

```bash
# 1. Confirm the tree is clean (except this document)
git status --short

# 2. Confirm the unique base commit and the diff base
git log --oneline origin/main..HEAD        # expect exactly 1 commit (d349350)

# 3. Confirm the exact upload diff (108 archivos, +10079/−936)
git show --stat d349350
git diff --numstat origin/main...HEAD | tail -20

# 4. Re-confirm the hermetic suite (169 passed / 2 skipped / 7 deselected)
pytest tests/ -m "not model" -q

# 5. The backup branch is LOCAL and must NOT be pushed:
#    push only ngi-candidacy, never backup/pre-squash-8.
```

**Push command (after checklist):** `git push -u origin ngi-candidacy:main` — or open a PR
`ngi-candidacy → main` (the branch has no remote ref; see Section 2).

---

*Prepared by `@logographer` on 2026-08-02. Historical baseline: `docs/STATE_CONSOLIDATION_2026-08-01.md`
(fixed HEAD at `76845a6`) and `docs/DIF_LOG_2026-08-01.md` (seeded this cycle). Pre-squash
history: `backup/pre-squash-8` (`5e12912`) — local only.*
