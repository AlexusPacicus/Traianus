# 📒 Traianus Ledger — Operational Delta Register

> **Canonical record:** append-only ledger of operational deltas (`Δ_n`). This file mirrors the
> immutable revision sequence of `manifold_nodes` in the persistence layer: entries are only ever
> **appended** (increasing `seq`); existing rows are never modified or deleted.

## Ownership boundaries

| Document | Role |
|---|---|
| **LEDGER.md** (this file) | Operational delta history (append-only) |
| **LOGOGRAPHY.md** | Structural index; mutates only when the file-tree topology changes |
| **TRAIANUS_AUDIT.md** | Per-finding snapshots and remediation status |
| **IMPLEMENTATION_STATUS.md** | Declared implemented capabilities vs. R&D roadmap |

## Ledger entries

### seq 1 — 2026-08-04 — OSS Readiness Phase 0 closure (TA-03 / TA-04 / TA-05)

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
- **Gate:** hermetic + meta suites green.

### seq 2 — 2026-08-05 — Single-agent realignment (agent layer archived)

- The `.opencode/agents/` role definitions (14 files) were archived to
  `docs/exploring/legacy_docs/opencode/agents/` and are no longer loaded as live subagents.
- Traianus is governed by a single executing agent; `AGENTS.md` §6 updated accordingly
  (enforcement via `opencode.jsonc` global permissions + tridenguard validator MCP + SEC-M-13).
- **Gate:** hermetic suite green.

### seq 3 — 2026-08-05 — SPEC-M2-DELTA-0-1 (Approved)

- **Δ0 (Governance):** governance domain boundaries delimited; LEDGER.md created; LOGOGRAPHY.md
  reduced to a structural index (Milestones moved to this ledger).
- **Δ1 (Persistence):** SQLite persistence extracted from `traianus/app.py` into
  `traianus/storage.py`; pure geometry moved to `traianus/core.py`; `traianus/bootstrap.py`
  migrated to the single `storage.DB_PATH` owner; test harness repointed to
  `traianus.storage.DB_PATH`.
- **Scope (Δ1):** `traianus/storage.py` — `DB_PATH` (sole owner), `get_db_connection()`,
  `init_db()`/`init_relational_tables()`, sequence helpers, epoch/axis reads, ε-edge
  persistence, and fine-grained persistence functions; `traianus/core.py` — `_compute_epsilon_edges`,
  `calibrate_critical_threshold`; `traianus/app.py` — orchestration + encoding + routes + re-export
  shims (no `sqlite3`).
- **Gate (S0 → S1):** `grep -c "sqlite3.connect\|import sqlite3" traianus/app.py` == 0;
  `DB_PATH` exclusive to `traianus/storage`; `pytest tests/ -m "not model"` → 50 passed / 1 deselected;
  `pytest tests/ -m "model"` → 1 passed; `python tools/audit_harness.py` → C1 guard GREEN;
  `python tools/validate_c1_semantics.py` → GREEN.
- **Status:** `Approved`.

### seq 4 — 2026-08-05 — SPEC-M2-DELTA-0-1 (Consolidated)

- **Δ0 executed:** `docs/LEDGER.md` created (this ledger); `docs/LOGOGRAPHY.md` reduced to a
  structural index referencing the ledger (Milestones relocated to seq 1/seq 2 above).
- **Δ1 executed:** `traianus/storage.py` created as the sole persistence owner (`DB_PATH`,
  `get_db_connection()`, canonical DDL + migrations, revision sequences, epoch/axis reads,
  ε-edge persistence, fine-grained persistence functions); pure geometry moved to
  `traianus/core.py` (`compute_epsilon_edges`, `calibrate_critical_threshold`);
  `traianus/app.py` reduced to orchestration + encoding + routes with re-export shims;
  `traianus/bootstrap.py` migrated to `storage.get_db_connection()`; harness repointed to
  `traianus.storage.DB_PATH` (conftest, test_substrate, test_e2e, audit_harness,
  validate_c1_semantics).
- **Gate (measured, S0 → S1):**
  - `grep -c "sqlite3.connect\|import sqlite3" traianus/app.py` → **0** ✔
  - `DB_PATH = "traianus.db"` defined exclusively in `traianus/storage.py` ✔
  - `pytest tests/ -m "not model"` → **50 passed / 1 deselected** ✔
  - `pytest tests/ -m "model"` → **1 passed** ✔
  - `python tools/audit_harness.py` → **C1 GUARD PASSED IN GREEN (45%, 9/20)** ✔
  - `python tools/validate_c1_semantics.py` → **WP0 VALIDATION PASSED (53%, 9/17)** ✔
  - Full combined run: **51 passed** ✔
- **Status:** `Consolidated`. System enabled for Δ2 (HTTP route extraction).

> **Consolidation rule:** a delta reaches `Consolidated` only when its declared gate is satisfied
> (simultaneous-key style, mirroring §3.5 of the constitution). The consolidation is recorded by
> appending a new `seq` entry, never by editing the delta's own row.

### seq 5 — 2026-08-05 — Persistence hardening (Δ1 acceptance-gap closure)

- **Δ2 executed:** closure of the gaps found in the Δ1 review:
  - Dead re-export shims removed from `traianus/app.py` (`DB_PATH`, `persist_epsilon_edges`);
    `traianus.storage` is the sole owner of the SQLite lifecycle.
  - Unmasked storage failures (AGENTS.md §1.3): `get_geodetic_matrix_db` no longer swallows
    `OperationalError`; `get_current_dimension_db` no longer silently returns a magic 384 on error.
  - Atomicity restored: node revision + queue-status update commit in a single transaction in
    `async_spectral_processor` (they were split across two connections).
  - Race-free idempotency: `enqueue_ingest` now uses `INSERT ... ON CONFLICT(idempotency_key) DO NOTHING`
    (a concurrent duplicate could previously raise a UNIQUE-constraint error → 503).
  - Harness corpus deduplicated to 20 **distinct** notes; the "expected ~30%" comment (which
    contradicted the measured 45%) removed; the consolidation rate is restated as corpus-dependent.
- **Gate (measured):**
  - `pytest tests/ -m "not model"` → **57 passed / 1 deselected** (7 new hardening tests)
  - `pytest tests/ -m "model"` → **1 passed**
  - `python tools/audit_harness.py` → **C1 GUARD PASSED IN GREEN (45%, 9/20 over 20 distinct notes)**
- **Status:** `Consolidated`.

### seq 6 — 2026-08-06 — Connection-lifecycle hardening (Δ1 review follow-up)

- **Connection-per-operation made deterministic:** `traianus/storage.get_db_connection()`
  is now a closing `@contextmanager` (commit on success / rollback on exception /
  always `close()`). Previously `sqlite3.Connection.__exit__` committed but never
  closed, leaving handles open until garbage collection; closure now never depends
  on the interpreter GC.
- **Explicit `PRAGMA busy_timeout = 5000`** documents the WAL write-retry contract
  (the `sqlite3.connect(timeout=5.0)` default already provided it; now it is
  self-documenting in code).
- **Callers migrated:** `traianus/bootstrap.py::anchor_in_sqlite` and
  `traianus/storage.persist_epsilon_edges` now use `with get_db_connection() as conn:`
  (manual `commit()`/`close()` removed); no caller treats it as a raw factory.
- **`persist_epsilon_edges` fate resolved:** kept as the documented RE-09/H5 contract
  primitive (live `/relations` E_n path remains observational per SPEC M-a); its
  docstring now states it is exercised by the regression suite and available for a
  future server-side persistence delta. No dead code: the function is the RE-09
  regression target (`tests/test_substrate.py::test_epsilon_edges_adjacency`).
- **New tests** (`tests/test_storage_hardening.py`, +4): connection closed after
  `with`-block (ProgrammingError on use), busy_timeout == 5000, commit on normal
  exit, rollback on exception.
- **Gate (measured):**
  - `pytest tests/ -m "not model"` → **61 passed / 1 deselected** (+4 connection tests)
  - `pytest tests/ -m "model"` → **1 passed**
  - `python tools/audit_harness.py` → **C1 GUARD PASSED IN GREEN (45%, 9/20)**
  - `python tools/validate_c1_semantics.py` → **WP0 VALIDATION PASSED (53%, 9/17)**
- **Status:** `Consolidated`.

### seq 7 — 2026-08-06 — Canonical-DDL ownership + consolidation guard (Δ1 review, findings #1/#2)

- **Finding #1 (canonical DDL split) resolved:** `geodesic_axes` DDL + the epoch-PK
  migration moved from `traianus/bootstrap.py::anchor_in_sqlite` into
  `traianus/storage.py` (`_init_geodesic_axes`, called at the end of
  `init_relational_tables`). `storage.init_db()` now creates the FULL schema.
  `bootstrap.anchor_in_sqlite` calls `init_db()` itself (self-sufficient in every
  call path) and only `INSERT OR IGNORE`s the axes. Verified: DDL still matches
  `tests/helpers/db_factory.py` character-by-character (no drift).
- **Finding #2 (consolidation on empty basis) resolved:** `/nodos/{id}/consolidar`
  now fails loud with HTTP 400 ("Geodetic basis not initialized … run
  `traianus-bootstrap`") when `geodesic_axes` is empty, instead of a generic 500
  from `max({}.keys())`.
- **Language normalization (audit L3):** Spanish docstrings/comments in
  `traianus/app.py`, `tests/test_substrate.py`, `tests/test_e2e.py` and the
  `(n=20)` comment in `tools/validate_c1_semantics.py` converted to English.
- **New tests** (`tests/test_storage_hardening.py`, +3): `init_db()` alone creates
  `geodesic_axes`; `anchor_in_sqlite` is self-sufficient on a fresh DB;
  consolidation on an empty basis returns 400.
- **Gate (measured):**
  - `pytest tests/ -m "not model"` → **64 passed / 1 deselected** (+3)
  - `pytest tests/ -m "model"` → **1 passed**
  - `python tools/audit_harness.py` → **C1 GUARD PASSED IN GREEN (45%, 9/20)**
  - `python tools/validate_c1_semantics.py` → **WP0 VALIDATION PASSED (53%, 9/17)**
- **Status:** `Consolidated`.
