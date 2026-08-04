# Traianus — Meta-Governance Restoration Consolidation (2026-08-03)

> **Versionable governance document.** Restoration cycle of the OpenCode layer
> that commit `ea43df6` ("prune of meta-governance and honest reframing") had
> removed. Restores, as-is, the OpenCode configuration, its constitution
> (`AGENTS.md`) and the referenced governance documents, taken from the parent
> of the pruning commit (`ea43df6^`).
>
> **Scope:** only restores already-versioned files from `ea43df6^` plus this
> document and the Logography record. Does NOT touch `traianus/`, `tests/`,
> `tools/` or `.github/`. The restored files are not modified relative to the
> pre-pruning tree (the historical anchors of `opencode_architecture.md` §10,
> frozen on 2026-08-01, are preserved).

---

## 1. Git State

| Ref | Hash | Note |
| --- | --- | --- |
| `chore/restore-opencode-governance` (HEAD) | `8341a6d` | Branch created from `chore/readme-quickstart-docs` |
| `origin/main` | `ea43df6ad79e5a69ded7ff1a004d805a9423684d` (`ea43df6`) | Origin HEAD, base of the diff |
| `ea43df6^` | `6447987626e682d1ee09a02cff455425e7313f99` (`6447987`) | Restoration source (pre-pruning tree) |

**Work that was uncommitted at cycle time** (belongs to the work-in-progress of
the `chore/readme-quickstart-docs` / candidacy streams): `README.md`,
`docs/architecture/ADR/ADR.md`, `tests/genericos/test_g5_append_only.py`,
`tests/helpers/db_factory.py`, `traianus/app.py` (modified), `docs/templates/`
and `tools/traianus_invariant_verifier.py` (untracked). Since then each stream
was committed on its own branch: `chore/readme-quickstart-docs`,
`chore/h4-append-only-edges`, `chore/l1-hermetic-imports`.

---

## 2. What Was Restored (from `ea43df6^`)

| Layer | Files | State |
| --- | --- | --- |
| **Root config** | `opencode.jsonc` (model `opencode/big-pickle`, `small_model`, `instructions`, local MCP `tridenguard-validator`, permissions, `mcp_timeout`) | Restored |
| **Constitution** | `AGENTS.md` (domain, 5 invariants, 5 roles, format) | Restored |
| **Agents** | `.opencode/agents/{plan-architect,orchestrator,fixer,antigravity-compiler,logographer}.md` — 5 Zero-Trust subagents | Restored |
| **Commands** | `.opencode/command/{plan,orchestrate,verify}.md` | Restored |
| **Skills** | `.opencode/skills/{tdd-cycle,tridenguard-5-radicales}/SKILL.md` | Restored |
| **Audit** | `TRAIANUS_AUDIT.md` (C1/H1–H5 report + remediation status) | Restored |
| **Logography** | `docs/LOGOGRAPHY.md` (master index) | Restored |
| **Specification** | `docs/architecture/opencode_architecture.md` (config contract) | Restored |
| **Prior consolidation** | `docs/STATE_CONSOLIDATION_2026-08-01.md` (08-01 cycle, referenced by LOGOGRAPHY) | Restored |
| **Compiler** | `README_CODE_ENGINE.md`, `docs/audit/README_CODE_ENGINE.md`, `docs/audit/triden_guard_code_engine_v4.json` (5 Radicals) | Restored |
| **Methodology** | `docs/development/methodology/METHODOLOGY.md` | Restored |

**Total: 20 files** restored from `ea43df6^`, unmodified (byte for byte
relative to the pre-pruning tree).

**Not restored (historical, outside live references):** `docs/DIF_LOG_2026-08-01.md`
and `docs/UPLOAD_LOG_2026-08-02.md`.

---

## 3. Empirical Verification (measured, not estimated)

| Check | Command | Result |
| --- | --- | --- |
| Config parseable | `python3 -c "import json; json.load(open('opencode.jsonc'))"` | JSON OK |
| `instructions` references exist | `TRAIANUS_AUDIT.md`, `docs/LOGOGRAPHY.md` | present |
| OpenCode layer references exist | `tools/tridenguard_validator.py`, `tools/audit_harness.py`, `docs/architecture/opencode_architecture.md` | present |
| MCP validator | `tools/tridenguard_validator.py` | `SERVER_VERSION = "1.1.0"` (matches `opencode_architecture.md` §7) |
| Full suite | `.venv/bin/python -m pytest tests/ -q` | **181 passed, 2 skipped** |
| Hermetic partition | `.venv/bin/python -m pytest tests/ -m "not model" -q` | **174 passed, 2 skipped, 7 deselected** |
| C1 guard | `.venv/bin/python tools/audit_harness.py` | **C1 GUARD PASSED IN GREEN — 45% (9/20)**, within `[5%, 95%]` |

> Note: the restored `opencode_architecture.md` §10 anchor (2026-08-01) declares
> **174 passed / 2 skipped**; the current working-tree measurement is **181
> passed / 2 skipped** (the difference comes from the uncommitted candidacy
> changes). For fidelity to the byte-for-byte restoration, §10 keeps its
> historical anchor and the current measurement is recorded in this document
> (§3 and finding W1).

---

## 4. `AGENTS.md` Invariant Matrix

| # | Invariant | State | Evidence |
| --- | --- | --- | --- |
| 1 | Consult `TRAIANUS_AUDIT.md` before refactoring `traianus/app.py` | Restored | `AGENTS.md:11`; `TRAIANUS_AUDIT.md` present in the tree |
| 2 | Exclude self-projection ($i = j$, value 1.0) in `auto_calibrate_critical_threshold()` | Restored | `AGENTS.md:14-16`; C1 guard green (§3) |
| 3 | Zero-Trust and network: block external network; Uvicorn on `127.0.0.1`; no CORS wildcard with credentials | Restored | `AGENTS.md:18-22`; `opencode.jsonc:18-22` (webfetch/websearch deny, local MCP) |
| 4 | Literal grounding: the `Topological_Grounding` citation must exist exactly in the source | Restored | `AGENTS.md:24-25`; validator Grounding Gate |
| 5 | Immutable persistence (*Append-Only*): no `UPDATE`/`DELETE` over history; revisions with increasing `seq` | Restored | `AGENTS.md:27-28`; `(id, seq)` log in `traianus/app.py` |

---

## 5. Cycle Findings

| ID | Severity | Description | Citation (path:line) | Resolution |
| --- | --- | --- | --- | --- |
| **W1** | Yellow | `opencode_architecture.md` §10 anchors numbers frozen on 2026-08-01 (**174 passed / 2 skipped**); the current tree measures **181 passed / 2 skipped** (includes uncommitted candidacy changes) | `docs/architecture/opencode_architecture.md:214` | Kept as historical anchor (byte-for-byte restoration); the current measurement is recorded in §3 |
| **W2** | Blue | `docs/development/bitacora.md`, `working_tree.md` and `TEST_OVERVIEW.md` are in `.gitignore` (unversioned); `LOGOGRAPHY.md` references them | `.gitignore:19-21`; `docs/LOGOGRAPHY.md:24,46` | Documented (R1 of the 08-01 cycle stayed partial: SPECs + METHODOLOGY versioned, the rest still local) |
| **W3** | Blue | `README_CODE_ENGINE.md` / `docs/audit/` / `METHODOLOGY.md` restored with pre-pruning tree content; the sources (`tools/tridenguard_validator.py`, `tests/`) did not change relative to that version | — | Accepted: byte-for-byte restoration, no drift |
| **W4** | Blue | `bitacora.md` has two duplicated `Record #011` entries (inherited finding D8 of the 08-01 cycle); append-only policy prevents renumbering | `docs/development/bitacora.md:132,145` | Pending (agreed in the 08-01 cycle) |

---

## 6. Pending Items

1. **OpenCode restart** already done by the User (the restored config loads at startup; no hot-reload).
2. **Commit** of the restoration on the `chore/restore-opencode-governance` branch (this cycle commits the 20 restored files + the Logography docs; the candidacy changes stay out).
3. The structural audit backlog (partial H4, H5 `K_n`, M1/M2/M8, L1–L6) remains in `TRAIANUS_AUDIT.md` — unchanged this cycle.

---

## 7. Acceptance Criteria

1. The restored OpenCode layer is **identical** to the `ea43df6^` tree (verified by `git checkout ea43df6^ -- <files>`).
2. All references of `opencode.jsonc` (`instructions`), `AGENTS.md` and the `.opencode/` layer resolve to present files (grep verified).
3. Suite: **181 passed / 2 skipped** (full), **174 passed / 2 skipped / 7 deselected** (hermetic); C1 guard **green (45%)**.
4. This cycle's commit does not include the uncommitted candidacy changes (`README.md`, `ADR.md`, `tests/*`, `traianus/app.py`, `docs/templates/`, `tools/traianus_invariant_verifier.py`).
