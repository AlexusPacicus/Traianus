# Full-Repo Audit Remediation (Normative Specification)

**Status:** Executed 2026-09-18 (LEDGER seq 46, 48–51); one half open: INV-4's
key-based deduplication. Pending operator approval for §7 (INDEX wiring).
**Origin:** 8-angle full-repo code review (traianus/, tests/, tools/) + 13-candidate
1-vote verification pass, 2026-09-13/14. 11 CONFIRMED, 2 REFUTED (discarded).
**Companion:** each delta below closes with a `docs/LEDGER.md` `seq` entry on
consolidation, per the existing SPEC-M2-DELTA-0-1 convention (Defect → Why →
Fix → TDD → Gate → Status).

---

## 1. Scope

This specification governs remediation of five defect clusters found by a
full-repository review, scoped to `traianus/`, `tools/hooks/`, and
`docs/audit/AUDIT.md`. It covers:

- Δ1 — Zero-Trust gate integrity (`traianus/security/validator.py`,
  `traianus/security/hook_gate.py`, `tools/hooks/require_boundary_validation.py`).
- Δ2 — Ingestion integrity (`traianus/app.py` `/ingesta`, `/ingesta/vector`,
  `/relations`).
- Δ3 — Audit-trail fidelity (`traianus/app.py` `consolidate_sovereignty`,
  `docs/audit/AUDIT.md`).
- Δ4 — Resource hardening (`traianus/app.py` `/relations`,
  `traianus/geometry/observables.py`).
- Δ5 — Connection and error-handling hygiene (`traianus/security/validator.py`,
  `traianus/storage/sqlite_engine.py`, `traianus/app.py`).

**Non-goals:** this spec does not reopen the two AGENTS.md §1.3-documented
exception catches in `validator.py` (`_persist_audit`'s fail-open on
`sqlite3.Error`, `validate_proposal`'s closing generic catch) — those remain
correct as designed. It does not change the 384D vector math, the C1
self-projection exclusion, or the dual-key consolidation formula in
`traianus/core.py` — none of those were found defective. It does not restore
the naive precision expectation on stored float32 vectors (found REFUTED: the
~1e-7 deviation is the documented float32 precision, not a bug).

---

## 2. Normative Requirements

1. **R1 (Δ1).** The audit-database path used by `traianus/security/validator.py`
   `_persist_audit` MUST resolve to the same file as the path used by
   `traianus/security/hook_gate.py` `_db_path`, independent of either
   process's current working directory.
2. **R2 (Δ1).** `tools/hooks/require_boundary_validation.py` MUST return a
   blocking exit code for every input it cannot fully parse and verify —
   including malformed JSON on stdin — not only for a parseable payload that
   fails the governed-path/receipt check.
3. **R3 (Δ2).** `POST /ingesta` MUST reject a request lacking
   `X-Idempotency-Key` with an HTTP 4xx status. `POST /ingesta/vector` MUST
   enforce the same idempotency-key contract as `/ingesta`.
4. **R4 (Δ2).** A node's current `lifecycle_state` MUST NOT silently regress
   from `consolidated` to `incubating` or `pending_approval` as a side effect
   of re-ingestion; any transition out of `consolidated` MUST be an explicit,
   auditable action.
5. **R5 (Δ2).** The function mapping an unordered pair of node ids to an
   `edge_id` MUST be injective over the full space of valid node-id strings
   (i.e., no two distinct valid pairs may produce the same `edge_id`).
6. **R6 (Δ3).** `action_potential` MUST be computed as
   `float(gate["topological_key"]["variance"])` at every site that writes a
   `manifold_nodes` revision, with no path-dependent override.
7. **R7 (Δ3).** Every regression-test name cited as evidence in
   `docs/audit/AUDIT.md` MUST correspond to a test id collectible by
   `pytest --collect-only`, or MUST be corrected to the test that actually
   covers the claim. Where §7's audit finds no covering test exists at all,
   `AUDIT.md` MUST say so rather than cite a non-existent name.
8. **R8 (Δ4).** `GET /relations` MUST NOT recompute the full O(n²) epsilon-edge
   set from scratch on every request once the current-node count exceeds a
   documented bound; edge maintenance MUST be incremental (computed once per
   write, not once per read) or explicitly cached with a documented
   invalidation rule.
9. **R9 (Δ5).** Every `sqlite3.connect(...)` call MUST have a corresponding
   deterministic `close()` on every exit path (normal and exceptional),
   matching the existing pattern in `traianus/storage/_storage.py`'s
   `get_db_connection()` and `sqlite_engine.py`'s `_transaction()`.
10. **R10 (Δ5).** Any `except Exception` clause with no re-raise and no
    observable side effect MUST be either documented as an intentional
    fail-open exception in AGENTS.md §1.3, or changed to have at least one
    observable side effect (a narrower exception type, a log line, or a
    metric) before being merged.

---

## 3. Mathematical Formulation

No application-domain concepts are introduced (AGENTS.md §3.2); all predicates
below are stated over engine-internal state (node ids, lifecycle states,
connection handles, request cost).

**3.1 Idempotency (R3).** Let `K` be the idempotency-key domain and `k` the
key presented with a request. Require the guard predicate
`P(k) = (k ≠ ∅) ∧ (|{rows : idempotency_key = k}| ≤ 1)` to be enforced at the
API boundary for both `/ingesta` and `/ingesta/vector`, rejecting `k = ∅`
rather than treating it as "no key" (SQLite's `UNIQUE` constraint already
treats `NULL` as pairwise-distinct, so `P` cannot be satisfied by the
constraint alone).

**3.2 Lifecycle monotonicity (R4).** Let `rank : LifecycleState → {0,1,2}`
with `rank(pending_approval)=0`, `rank(incubating)=1`, `rank(consolidated)=2`
(`telemetry_error` is terminal and excluded from ranking). For a node `n`
with revisions ordered by `seq`, require: for every pair of consecutive
revisions `(rev_i, rev_{i+1})` of the same node written by an ingestion path
(not an explicit demotion action), `rank(rev_{i+1}.state) ≥ rank(rev_i.state)`.

*Enforced scope (Δ2).* R4 constrains only exits from `consolidated`, and that
is what is enforced. Re-ingestion may still move a node between
`pending_approval` and `incubating` in either direction: that change is driven
by the new content's own topological key, not by a side effect, and forbidding
it would remove the ability to revise an unconsolidated node.

**3.3 Edge-id injectivity (R5).** Let `φ(a,b) = "edge-" ++ sort(a,b)[0] ++ "-" ++ sort(a,b)[1]`
be the current encoding, where `++` is string concatenation and label
characters are drawn from `[A-Za-z0-9_-]`. `φ` is **not** injective: the
delimiter `-` collides with the allowed label alphabet, giving a
constructible counter-example
`φ(("VEC_x","VEC_y-VEC_z")) = φ(("VEC_x-VEC_y","VEC_z"))`. Require a revised
`φ'` that is injective over the same domain (e.g. a length-prefixed encoding
`len(a) ++ ":" ++ a ++ len(b) ++ ":" ++ b`, or a delimiter outside the label
alphabet with the label alphabet correspondingly restricted).

**3.4 DB-path resolution symmetry (R1).** Let `W` be the path
`traianus/security/validator.py::_persist_audit` opens for writing and `R`
the path `traianus/security/hook_gate.py::_db_path` opens for reading.
Require `resolve(W) = resolve(R)` for all values of `cwd(process_W)` and
`cwd(process_R)` — i.e. resolution must be a pure function of `REPO_ROOT`,
not of either process's working directory.

**3.5 Fail-closed totality (R2).** Let `D : Input → {ALLOW, BLOCK}` be the
hook's decision function over the space of all possible stdin payloads
`Input` (well-formed and malformed). AGENTS.md §6.2 claims `D` fails closed.
Totality requires `D(i) = BLOCK` for every `i` that is not a positively
verified, governed-path, recent-`EXECUTE_SAFE` case. Currently
`D(malformed_json) = ALLOW`, so `D` is partial with respect to its own
stated contract; R2 requires `D` to be total.

**3.6 Connection lifecycle (R9).** For every call site `c` that executes
`open = sqlite3.connect(...)`, require a corresponding `close` such that
`close` executes on every control-flow path leaving `c`'s enclosing scope,
including exception propagation — i.e. `open` and `close` counts are equal
after any finite number of calls to `c`, independent of exceptions raised.

**3.7 Read cost bound (R8).** Let `n = |current_nodes|`. The current cost of
`GET /relations` is `C_read(n) = Θ(n²)` (full recomputation via
`compute_epsilon_edges`). Require an incremental scheme where the cost of
processing one new node is `C_write(1) = O(n)` (computing that node's
distance to existing nodes only) and `C_read(n)` for an unchanged node set is
`O(1)` relative to `n` (serving the persisted/cached edge set).

**3.8 Action-potential path-independence (R6).** Let `AP(rev)` be the
`action_potential` written for revision `rev`, and `v(rev)` the true
topological-key variance at that revision. Require `AP(rev) = float(v(rev))`
for all `rev`, independent of which of the three ingestion/consolidation
call sites produced `rev` (currently one call site sets
`AP(rev) = 1.0` unconditionally on successful consolidation, violating this
for that path).

---

## 4. Invariants

Concrete, machine-checkable, tied to exact locations found during the audit:

| ID | File : Line | Invariant | Current state |
|---|---|---|---|
| INV-1 | `traianus/security/validator.py:59` | DB path resolves identically to `hook_gate.py:70` regardless of process cwd | **Resolved** (seq 46) |
| INV-2 | `tools/hooks/require_boundary_validation.py:39` | `except json.JSONDecodeError` returns a blocking exit code | **Resolved** (seq 46) |
| INV-3 | `traianus/app.py:395` | `/ingesta` rejects (4xx) when `X-Idempotency-Key` header is absent | **Resolved** (seq 48) |
| INV-4 | `traianus/app.py:419` (`vector_ingestion_endpoint`) | `/ingesta/vector` enforces an idempotency-key contract | **Partial** (seq 48): header now required; key-based dedup deferred |
| INV-5 | `traianus/app.py:504` | Re-ingesting a label already `consolidated` does not silently produce `incubating` as the new current state | **Resolved** (seq 48) |
| INV-6 | `traianus/app.py:782` | `edge_id(a,b) = edge_id(c,d)` implies `{a,b} = {c,d}` | **Resolved** (seq 48) |
| INV-7 | `traianus/app.py:651` | `action_pot = float(gate["topological_key"]["variance"])` at every write site | **Resolved** (seq 49) |
| INV-8 | `docs/audit/AUDIT.md` (Remediation Status table) | Every cited test name is collectible via `pytest --collect-only` | **Resolved** (seq 49): 0 of 8 cited names were collectible; 3 claims were covered under other names, 4 had no covering test under any name and a fifth only half (M5's `/telemetry` token) |
| INV-9 | `traianus/app.py:729` | `GET /relations` cost does not scale `Θ(n²)` per request as `current_nodes` grows | **Resolved** (seq 50) |
| INV-10 | `traianus/security/validator.py:59`, `traianus/storage/sqlite_engine.py:141`, `traianus/storage/sqlite_engine.py:188` | Every `sqlite3.connect(...) as conn` closes `conn` on all exit paths | **Resolved** (seq 51): 3 sites, as drafted; the `sqlite_engine.py` ones are `with self._connect() as conn:`, so a search for the literal `sqlite3.connect` misses them |
| INV-11 | `traianus/app.py:379` | Every broad `except Exception` clause is either documented in AGENTS.md §1.3 or has an observable side effect | **Resolved** (seq 51) |

---

## 5. Verification

Each invariant above gets a deterministic regression test before its fix
lands (TDD, AGENTS.md §1.4), collected under `tests/security/` or
`tests/unit/` as noted, plus the existing full-suite and C1-harness gate:

| Invariant | New test (RED before fix, GREEN after) |
|---|---|
| INV-1 | `tests/security/test_hook_gate.py::test_audit_db_path_matches_validator_regardless_of_cwd` |
| INV-2 | `tests/security/test_hook_gate.py::test_malformed_stdin_json_blocks` |
| INV-3, INV-4 | `tests/security/test_ingesta_idempotency.py::test_ingesta_rejects_missing_idempotency_key`, `::test_ingesta_vector_enforces_idempotency_key` |
| INV-5 | `tests/unit/test_substrate.py::test_reingesting_consolidated_label_does_not_regress_state` |
| INV-6 | `tests/unit/test_substrate.py::test_edge_id_is_injective_over_hyphenated_labels` |
| INV-7 | `tests/unit/test_substrate_invariants.py::test_consolidar_action_potential_is_true_variance` |
| INV-8 | `tests/meta/test_audit_citations_collectible.py::test_all_cited_test_names_exist` (a `pytest --collect-only` cross-check against `docs/audit/AUDIT.md`) |
| INV-9 | `tests/unit/test_storage_hardening.py::test_relations_does_not_recompute_full_epsilon_set_on_unchanged_nodes` |
| INV-10 | `tests/unit/storage/test_sqlite_engine_concurrency.py::test_get_data_plane_closes_connection`, `::test_get_control_plane_closes_connection`, `tests/security/test_hook_gate.py::test_persist_audit_closes_connection` |
| INV-11 | `tests/security/test_internal_error_masking.py::test_error_log_persistence_failure_is_logged_not_swallowed` (behavioural: both failures are forced and the log line is required; moved from `test_config_perimeter.py`, which holds another session's uncommitted work and is about the permission matrix) |

**Gate (per delta, on consolidation):** `pytest tests/` full suite green;
`ruff` clean; `mypy traianus/` clean; `python tools/audit/audit_harness.py`
C1 guard green — matching the measured-gate convention already used for
every `Consolidated` entry in `docs/LEDGER.md`.

---

## 6. Delta Execution Plan

Execution order follows dependency, not severity: Δ1 hardens the mechanism
that gates every subsequent edit's audit trail, so it closes first.

### Δ1 — Zero-Trust gate integrity
- **Defect:** INV-1, INV-2.
- **Why:** a gate whose own receipt-matching can silently diverge by cwd, or
  that allows on unparseable input, undermines the evidentiary basis for
  every `EXECUTE_SAFE` this document and future deltas rely on.
- **Fix:** anchor `_persist_audit`'s DB path to `REPO_ROOT` the same way
  `hook_gate._db_path` already does; change
  `require_boundary_validation.py`'s `JSONDecodeError` handler to return the
  same blocking exit code used for a failed governed-path check.
- **TDD:** INV-1/INV-2 tests written RED first, confirmed RED for the stated
  reason, then GREEN after the minimal fix.
- **Gate:** see §5. `pytest tests/` 1146 passed / 5 deselected; `ruff` clean
  on the touched files (pre-existing debt elsewhere untouched); `mypy
  traianus/` clean (32 files); C1 guard PASSED.
- **Side effect found and fixed:** anchoring `_persist_audit` to `REPO_ROOT`
  removed the cwd-based isolation `tests/security/test_boundary_validator.py
  ::test_security_SEC_M_06_mcp_stdio_jsonrpc` relied on to keep its spawned
  MCP-server call out of the real repo-root audit DB (verified empirically:
  the row count went 91 -> 92 before the fix). That test now deletes its own
  row by `case_id` instead of relying on `chdir`.
- **Status:** `Consolidated` (LEDGER seq 46).

### Δ2 — Ingestion integrity
- **Defect:** INV-3, INV-4, INV-5, INV-6.
- **Why:** these four defects each let a client silently corrupt or bypass
  the ingestion contract (duplicate ingestion, state regression, or history
  collision) without any error surfaced.
- **Fix:** make `X-Idempotency-Key` a required header on `/ingesta` (422 if
  absent) and add the same parameter/check to `/ingesta/vector`; make
  `/ingesta/vector`'s state transition respect §3.2's monotonicity
  invariant (either reject re-ingestion of a consolidated label, or require
  an explicit re-consolidation step); replace `φ` in the edge-id builder
  with an injective encoding per §3.3.
- **TDD:** INV-3..INV-6 tests written RED first (each confirmed RED for the
  stated reason: 200/201 instead of 422, 201 instead of 409, colliding
  `edge-VEC_x-VEC_y-VEC_z`), then GREEN after the minimal fix.
- **As executed:**
  - INV-3: `X-Idempotency-Key` is now a required header on `/ingesta` (422).
  - INV-4 **(partial, by decision)**: the header is now required on
    `/ingesta/vector` (422) — 36 call sites across 5 test files updated. The
    other half of §3.1's `P(k)`, rejecting a *repeated* key, is **not**
    implemented: unlike `/ingesta`, the vector endpoint writes straight to
    `manifold_nodes`, which has no `idempotency_key` column, so real
    deduplication needs a `UNIQUE` column plus the rename→recreate→copy→drop
    migration this repo already uses for `ingestion_queue`. Deferred to its
    own delta rather than bundled here.
  - INV-5: `insert_node_revision(..., guard_consolidated=True)` makes the check
    part of the `INSERT` statement, so a concurrent consolidation cannot slip
    between a read and the write; `/ingesta/vector` maps the refusal to 409.
    The explicit `/consolidar` demotion path is unchanged.
  - INV-6: `storage.build_edge_id(prefix, a, b)` escapes `~`→`~t` and `-`→`~d`
    inside each endpoint, so the joining `-` is unambiguous. It is the
    identity on labels containing neither character, so pre-existing ids stay
    valid (a length-prefixed encoding would have re-keyed every edge). Applied
    to the `auto-edge-*` sites as well — the same collision existed there.
- **Gate:** see §5. `pytest tests/` 1152 passed / 5 deselected, model partition
  5 passed; `ruff` clean on the exact CI scope; `mypy traianus/` clean; C1
  guard PASSED (9/20). `tools/audit/audit_harness.py` and
  `tools/experiments/validation/validate_c1_semantics.py` also had to send the
  now-mandatory header (the harness failed loudly at 0/0 until fixed).
- **Status:** `Consolidated` except the INV-4 dedup half (LEDGER seq 48).

### Δ3 — Audit-trail fidelity
- **Defect:** INV-7, INV-8.
- **Why:** `action_potential` and `docs/audit/AUDIT.md`'s own citations are
  the evidentiary record this project uses to claim findings are resolved;
  both were found to assert something the code does not do.
- **Fix:** `consolidate_sovereignty` computes `action_pot` the same way the
  other two ingestion paths do (§3.8); `AUDIT.md`'s Remediation Status table
  is corrected to cite the test names that actually exist, and the four rows
  with no covering test are flagged as newly-open (not silently re-marked
  Resolved) until §5's INV-7/INV-9/etc. tests exist.
- **TDD:** INV-7 test written RED first (stored `1.0` vs measured `0.00263`),
  then GREEN after the one-line fix. INV-8: the meta-test was written RED first
  (all 8 cited names missing) and goes GREEN once `AUDIT.md` is corrected.
- **As executed, and where it departs from the draft:**
  - INV-8's check is a name-level AST scan of the test functions under
    `tests/`, not a `pytest --collect-only` run: the meta-test cannot spawn a
    process, and for the naming convention in use the two agree.
  - The draft said to flag the rows with no covering test as newly-open. Every
    such behaviour turned out to be implemented, only unverified, so instead of
    demoting the claims, five small characterization tests were written under
    the names `AUDIT.md` already cited (`test_ingesta_returns_503_on_persistence_failure`,
    `test_consolidar_missing_node_returns_404`,
    `test_cors_origins_are_enumerated_no_wildcard`,
    `test_action_potential_is_variance_not_scaled`, plus
    `test_telemetry_requires_token` for M5's second half). Four citations that
    named a test that exists under a different name were corrected (C1, H2, M3,
    M5). The M6 row now says the background text-ingestion path has no direct
    assertion.
  - Found while doing this: `tests/helpers/endpoint_registry.py` (generic
    requirements G1–G4) is consumed by no test. Not touched.
- **Gate:** see §5. `pytest tests/` 1159 passed / 5 deselected; `mypy
  traianus/` clean; C1 guard PASSED (9/20).
- **Status:** `Consolidated` (LEDGER seq 49).

### Δ4 — Resource hardening
- **Defect:** INV-9.
- **Why:** `manifold_nodes` is append-only by design (AGENTS.md §4.1) and
  never shrinks, so an O(n²)-per-request cost is a standing risk to the
  ≤8GB envelope (AGENTS.md §3.1) that gets worse the longer the system runs.
- **Fix:** serve `GET /relations` from the already-implemented
  `persist_epsilon_edges` incremental log instead of recomputing via
  `rebuild_epsilon_edges` on every request; compute new edges only for newly
  ingested nodes.
- **TDD:** INV-9 test written RED first (assert bounded read cost / call
  count to the O(n²) path stays flat as node count grows). Confirmed RED:
  3 recomputations over 3 reads of an unchanged log.
- **Correction to the drafted fix.** The premise above is wrong on two counts.
  `persist_epsilon_edges` is not incremental — it recomputes the full
  `compute_epsilon_edges` and diffs against the stored rows — and it is
  deliberately absent from the request path: SPEC M-a makes E_n observational
  and "computed on read" (a test pins `/consolidar` not persisting `auto-edge-*`
  and another pins `/relations` computing them on read). Serving the read from
  it would have turned a read into a write path and still cost Θ(n²) per write.
- **As executed:** R8's other branch, "explicitly cached with a documented
  invalidation rule". `rebuild_epsilon_edges` caches its result under
  `(db path, epsilon, MAX(rowid) of manifold_nodes)`. The log is append-only, so
  `MAX(rowid)` is a strictly increasing version; an unchanged log costs one O(1)
  query per read, and the version is read from the database each call, so a
  second process writing to the same file invalidates it. Not achieved: §3.7's
  preferred `C_write(1) = O(n)`; the first read after a write still pays Θ(n²).
  True incremental maintenance needs its own design (revised vectors change and
  remove existing edges, not only add them).
- **Gate:** see §5. `pytest tests/` 1160 passed / 5 deselected at this delta.
- **Status:** `Consolidated` via the cache branch of R8 (LEDGER seq 50).

### Δ5 — Connection and error-handling hygiene
- **Defect:** INV-10, INV-11.
- **Why:** both are long-running-process risks (leaked file descriptors,
  silently vanishing telemetry) that degrade gradually rather than failing
  loudly, which is the failure mode AGENTS.md §1.3 is meant to prevent.
- **Fix:** wrap the three bare `with sqlite3.connect(...) as conn:` sites in
  `contextlib.closing` (matching `hook_gate.py`'s own pattern) or an explicit
  `finally: conn.close()`; give the `except Exception: pass` at
  `traianus/app.py:379` an observable side effect (e.g. a `logger.error` call)
  or document it in AGENTS.md §1.3 as a third sanctioned exception.
- **TDD:** INV-10/INV-11 tests written RED first; all four confirmed RED for the
  stated reason (`DID NOT RAISE ProgrammingError` on a supposedly closed
  connection ×3; empty stdout/stderr where a log line was required).
- **As executed:** `contextlib.closing` at the three sites — `_persist_audit`
  (`with closing(sqlite3.connect(p)) as conn, conn:`, the inner `conn` keeping
  the commit that `closing` alone would drop) and the two `SQLiteEngine` reads.
  The `except Exception: pass` now emits `ingestion_error_log_failed` through the
  structured logger; the alternative (a third sanctioned exception in AGENTS.md
  §1.3) was not taken, since that section is reserved for fail-open paths that
  are deliberately silent.
- **Gate:** see §5. `pytest tests/` 1164 passed / 5 deselected, model partition
  5 passed; `ruff` clean on the CI scope; `mypy traianus/` clean; C1 guard
  PASSED (9/20).
- **Status:** `Consolidated` (LEDGER seq 51).

---

## 7. Traceability

On approval, this document is wired into `docs/INDEX.md`'s traceability
matrix (Concept → Code → Test) with one row per delta, and each delta's
consolidation is recorded as a new `seq` entry in `docs/LEDGER.md`, per
existing convention.
