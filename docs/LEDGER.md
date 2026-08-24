# 📒 Traianus Ledger — Operational Delta Register

> **Canonical record:** append-only ledger of operational deltas (`Δ_n`). This file mirrors the
> immutable revision sequence of `manifold_nodes` in the persistence layer: entries are only ever
> **appended** (increasing `seq`); existing rows are never modified or deleted.

## Ownership boundaries

| Document | Role |
|---|---|
| **LEDGER.md** (this file) | Operational delta history (append-only) |
| **docs/audit/AUDIT.md** | Per-finding audit snapshots and remediation status |
| **docs/audit/remediation/** | Session evidence records (findings→fixes maps, gate case-id ledgers) |
| **docs/INDEX.md** | Structural index and traceability matrix |
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
  (enforcement via `opencode.jsonc` global permissions + boundary-validator MCP + SEC-M-13).
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
   `pytest tests/ -m "model"` → 1 passed; `python tools/audit/audit_harness.py` → C1 guard GREEN;
   `python tools/experiments/validate_c1_semantics.py` → GREEN.
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
   - `python tools/audit/audit_harness.py` → **C1 GUARD PASSED IN GREEN (45%, 9/20)** ✔
   - `python tools/experiments/validate_c1_semantics.py` → **WP0 VALIDATION PASSED (53%, 9/17)** ✔
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
   - `python tools/audit/audit_harness.py` → **C1 GUARD PASSED IN GREEN (45%, 9/20 over 20 distinct notes)**
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
   - `python tools/audit/audit_harness.py` → **C1 GUARD PASSED IN GREEN (45%, 9/20)**
   - `python tools/experiments/validate_c1_semantics.py` → **WP0 VALIDATION PASSED (53%, 9/17)**
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
   `(n=20)` comment in `tools/experiments/validate_c1_semantics.py` converted to English.
- **New tests** (`tests/test_storage_hardening.py`, +3): `init_db()` alone creates
  `geodesic_axes`; `anchor_in_sqlite` is self-sufficient on a fresh DB;
  consolidation on an empty basis returns 400.
- **Gate (measured):**
  - `pytest tests/ -m "not model"` → **64 passed / 1 deselected** (+3)
  - `pytest tests/ -m "model"` → **1 passed**
   - `python tools/audit/audit_harness.py` → **C1 GUARD PASSED IN GREEN (45%, 9/20)**
   - `python tools/experiments/validate_c1_semantics.py` → **WP0 VALIDATION PASSED (53%, 9/17)**
- **Status:** `Consolidated`.

### seq 8 — 2026-08-08 — Meta-Governance Moratorium and Structural Sanitation
* **Context:** The document architecture and agent bureaucracy (5 radicals, MCP, RFC 2119) grew disproportionately relative to the product, obscuring the empirically unvalidated mathematical core ($\sigma^2 \ge \theta_{dyn}$).
* **Action:** Declaration of total meta-governance moratorium.
   * Issue #1, #5, #6: Technical debt purge, sanitation of `tools/experiments/ingest_manifest.py` (CLI-agnostic), obsolete agent architecture archived to `legacy_docs`, and permission restriction in `opencode.jsonc` (Zero-Trust).
  * Issue #2, #3: Official freeze of the representation layer at 384D (`all-MiniLM-L6-v2`, offline) to prepare the ground.
* **Next Step:** Deployment of WP1 empirical research (Issue #4) to falsify the consolidation hypothesis over a real corpus.

### seq 9 — 2026-08-08 — WP1 Empirical Research Closure (Falsification of Hypothesis B_0)
 * **Context:** Deployment of `tools/experiments/validate_wp1_empirical.py` to evaluate the C1 gate ($\sigma^2 \ge \theta_{\text{dyn}}$) over 384D (`all-MiniLM-L6-v2`) with a real labeled corpus of 111 paragraphs (Cat A: Technical Focus n=45, Cat B: Conversational Prose n=46, Cat C: Stochastic Noise n=20).
* **Empirical Results:**
  * Cat C (Noise): $\sigma^2 = 0.002021$, consolidation rate **0%** (0/20). C1 acts effectively as a filter against stochastic noise.
  * Cat B (Prose): $\sigma^2 = 0.002582$, consolidation rate **15%** (7/46). High dispersion due to concentration of general primitives.
  * Cat A (Technical): $\sigma^2 = 0.002176$, consolidation rate **7%** (3/45). Semantic mass distributes homogeneously over the prosthetic octagon ($S_0$).
* **Scientific Verdict:** The initial hypothesis on the static basis $B_0$ is **falsified in the data**. Variance over $B_0$ does not measure "technical focus" but dispersion over Wierzbicka primitives. The need to derive geodesic axes dynamically from the user corpus is scientifically demonstrated (ADR-017).
 * **Status:** Immediate roadmap (Issues #1 to #6) completed at 100%. Hermetic suite (65 passed) and `tools/audit/audit_harness.py` in GREEN.

### seq 10 — 2026-08-09 — EAS-01 Fase 1b/1c: Sparse Lexical Substrates Falsified, NCD Coupling Validated

* **Context:** EAS-01 Fase 1 roadmap. Three candidate substrates for the
  substrate-side key (Llave 1) evaluated over the 111-note control corpus
   (Cat A: 45, Cat B: 46, Cat C: 20) via `tools/experiments/exp_logographic_nonortho.py`
   and `tools/experiments/exp_entropy_spectral.py`. Every probe ships its own
  falsification controls (C1–C6); headline numbers are not reported alone.

* **Fase 1b — Non-orthogonal sparse basis (FALSIFIED):**
  - Relaxing strict orthogonality **did** rescue the spectral key: the Gram
    off-diagonal rises to mean 0.0163 (max 0.1311) and
    $\theta_{dyn} = 0.000980$, versus exactly $0.000000$ under the one-hot
    basis of Fase 1. $\rho$ becomes continuous (40 distinct values in Cat A
    vs 2 previously). Confirms that $\theta_{dyn} = 0$ on any strictly
    orthogonal basis is an algebraic identity, not a tuning defect.
  - **C4 still fails:** one injected domain term consolidates pure noise
    ($\rho = 0.0309$, passes); a word salad with two terms reaches
    $\rho = 0.1457$. **C3 still inverts:** axes rebuilt from Category B
    vocabulary give Cat B 46/46 consolidation and drop Cat A to 15/45.
  - **Verdict:** non-orthogonality fixes the geometry but not the dictionary
    dependence. Any lexicon-based $\rho$ remains a keyword filter.

* **Fase 1c — Markov spectral gap (FALSIFIED):**
  - Reference-free eigenvalue gap of each note's own character-bigram
    transition matrix. No comparison reaches significance:
    gap A vs B AUC 0.414 ($p = 0.16$), A vs C AUC 0.619 ($p = 0.13$);
    spectral entropy A vs B AUC 0.556, A vs C AUC 0.468.
  - Cat B shows a **higher** mean gap (0.0904) than Cat A (0.0811),
    contradicting the Wigner-matrix prediction for noise.
  - **Verdict:** the gap measures orthographic regularity, not conceptual
    structure. English word salad is still English at the bigram level.

* **Fase 1c — NCD coupling (VALIDATED):**
  - $\text{NCD}(x,y) = \frac{C(xy) - \min(C(x),C(y))}{\max(C(x),C(y))}$,
    reported as coupling $1 - \text{NCD}$ against a **held-out half** of the
    reference corpus. Zero lexicon, zero tokenizer, byte level.
  - Separation is consistent across three independent compressors:

    | Compressor | A vs B | A vs C | C4 terms to defeat |
    |---|---|---|---|
    | zlib | AUC 0.953, $p=9.8\times10^{-10}$ | AUC 0.967, $p=1.6\times10^{-7}$ | 8 |
    | bz2 | AUC 0.922, $p=1.3\times10^{-8}$ | AUC 0.946, $p=5.7\times10^{-7}$ | 8 |
    | lzma | AUC 0.922, $p=5.0\times10^{-9}$ | AUC 0.933, $p=9.6\times10^{-7}$ | 4 |

  - **C4 defeated:** injections of 1, 2 and 4 domain terms into noise all
    fail to consolidate under zlib/bz2 (0.0504 / 0.0549 / 0.0593 against a
    Cat A p25 floor of 0.0628). First substrate of five to resist trivial
    keyword injection.
  - **C3b reference symmetry (decisive):** the coupling matrix is fully
    diagonal — Cat A couples most to an A reference (0.0651), B to B
    (0.0668), C to C (0.0996). Reference-dependence is a **symmetric
    property of the coupling operator**, i.e. designed field physics
    ($E_{int}$ against $\Phi$), not a Category A artifact.

* **Documented limitations (NOT resolved):**
  - **Length confound:** $r(\text{NCD}, \text{len}) = +0.396$ within Cat A.
    Length normalization is a precondition for production use.
  - **Language drift:** C6 gives ES/EN deltas up to 0.0204 on
    meaning-identical pairs, ~30% of the inter-category range. NCD is far
    less language-sensitive than dense embeddings but is **not** invariant.
  - **8-term injection succeeds** under every compressor: resistance is
    graded, not absolute.
  - $\Phi$ (§4.2) and the full $E_{int} = \int \rho\Phi\,dV$ integral remain
    unimplemented; only pairwise coupling to a static reference was measured.

* **Gate (measured):** `pytest tests/ -m "not model"` → **64 passed**.
  No modification to `traianus/core.py` or existing tests.

* **Status:** `Consolidated`. EAS-01 promoted `Propuesto` → `Aceptado` on
  this evidence.

### seq 11 — 2026-08-10 — Logographic Restructure: tools/ Subdivision and .data/ Isolation

* **Context:** `tools/` had grown as a flat directory of 14+ scripts with no
  semantic grouping; runtime artifacts (`traianus.db`, `-shm`, `-wal`) lived at
  the repository root, violating logographic hygiene.
* **Action:**
  - `tools/` subdivided into `audit/`, `experiments/`, `mcp/` — each with its
    own `__init__.py` for Python import resolution.
  - Root artifacts relocated: `traianus-simulation.py` → `tools/experiments/`;
    `traianus.db` (+ `-shm`, `-wal`) → `.data/` (gitignored).
  - `docs/EAS-01_LOGOGRAPHIC_PHYSICS.md` → `docs/specifications/`.
  - All path references updated across `opencode.jsonc`, `AGENTS.md`,
    `IMPLEMENTATION_STATUS.md`, `README.md`, `LOGOGRAPHY.md`, `LEDGER.md`,
    `docs/development/`, `docs/exploring/root_clutter/`, and `.opencode/skills/`.
  - Cross-package imports updated in 6 experiment files + 1 test file.
* **Scope (files moved):** 11 files under `tools/`, 1 under `docs/`,
  1 root script. Zero modifications to `traianus/` source or `tests/` logic.
* **Gate (measured):**
  - `pytest tests/` → **68 passed** (full suite, hermetic + model).
   - No functional delta; pure structural refactor (logographic hygiene).
* **Status:** `Consolidated`.

### seq 12 — 2026-08-11 — Observability Layer for `/ingesta/vector`

* **Context:** The `/ingesta/vector` endpoint shipped without structured
  logging or trace propagation — blind insertion into production. Without
  observability, collisions and latency spikes go undetected.
* **Action:**
  - New module `traianus/observability.py`: structlog JSON logger with
    `request_id` binding.
  - Endpoint instrumented: `X-Request-ID` generated/propagated, logs emitted
    at 3 phases (ingress, projection, persist) with duration, gate result,
    and outcome.
  - `insert_node_revision` in `traianus/storage.py`: retry-on-conflict logic
    (3 attempts) for safe concurrent ingestion.
  - `pyproject.toml`: `[project.optional-dependencies] observability` declared
    (structlog).
* **Deliberately excluded:** Prometheus counters/histograms. Metrics
  infrastructure is in initial research phase — scraping strategy, `/metrics`
  endpoint with auth, and retention policies are undefined. Shipping
  metric objects now would register counters nobody scrapes (orphaned data).
  Structured logging ships first because it's immediately useful with zero
  infrastructure (stdout/stderr, consumable by any log aggregator).
* **Scope (files):** 1 new (`observability.py`), 2 modified (`app.py`,
  `storage.py`), 1 new test file (`test_observability_vector.py`).
* **Gate (measured):**
  - `pytest tests/ -m "not model"` → **94 passed** (+5 observability tests).
  - `python tools/audit/audit_harness.py` → C1 GUARD GREEN (45%, 9/20).
  - Concurrency test: 8 workers same label → 1 node_id, seq 1..8, zero duplicates.
* **Status:** `Consolidated`.
### seq 13 — 2026-08-12 — H1 Vorticity-Pressure Experiment (exp_vorticity_pressure.py)

* **Context:** First empirical test of the theoretical framework's Hypothesis H1,
  verifying that increasing data density in fixed dimensions monotonically increases
  the kinetic distortion metric K_cin.
* **Experiment:** `tools/experiments/exp_vorticity_pressure.py` generated two regions
  in R^384: a laminar (free-flow) region and a high-compression region with
  compression_factor=3.0. K_cin = 0.5 * ||Δv||^2 * (1 + Var(v · B_0^T)).
* **Results:**
  - Free/labor region: K_cin promedio = 0.006115
  - High compression region: K_cin promedio = 0.032985
  - K_cin increases by factor of ~5.4 when density/compression rises.
* **Verdict:** H1 VALIDA — higher data density produces proportionally higher
  kinetic distortion, confirming the theoretical prediction.
* **Status:** `Consolidated`. Empirical base for C1 gate threshold calibration.

### seq 14 — 2026-08-12 — H2 Dimensional Relief Experiment (exp_dimensional_relief.py)

* **Context:** Second empirical test of the theoretical framework's Hypothesis H2,
  verifying that projection of compressed vectors to R^{d+1} via dimensional relief
  (appending K_cin) reduces orthogonality loss and relaminates the trajectory.
* **Theory:** In the Traianus substrate, B_0 is a reduced basis (k < d) representing
  the "piscina" (rest substrate). Measuring orthogonality loss against a full
  identity base I_d is trivial (variance = 0). A reduced basis (k=96 < d=384)
  captures "disalignment" from the known subspace, enabling meaningful metrics.
* **Experiment:** `tools/experiments/exp_dimensional_relief.py` generated a compressed
  region in R^384 (high compression factor 3.0, n=80 points) and measured:
  1. Orthogonality loss in R^384 relative to reduced base B_0 (k=96): 0.001397
  2. Applied dimensional relief: mapped each vector v ∈ R^384 to v̂ ∈ R^385 by
     appending K_cin as the (d+1)-th coordinate: v̂ = (v, K_cin)
  3. Orthogonality loss in R^385 with augmented base I_{385}: 0.000611
  4. Laminarity proxy (mean squared Δv): R^384 = 0.065969, R^385 = 0.074549
* **Results:** K_cin absorption in the (d+1)-th coordinate reduced orthogonality
  loss by 0.000786 (56% improvement) and increased laminarity, confirming that
  the relief mapping relaminates the trajectory as predicted by the theory.
* **Verdict:** H2 VALIDA — proyección a R^{d+1} mediante aumento escalar cinético
  reduce la pérdida de ortogonalidad y relamina la trayectoria, validando el
  mecanismo de alivio dimensional descrito en el marco teórico.
* **Status:** `Consolidated`. Empirical basis for C1 gate threshold calibration
  and dimensional relief mechanism design.


### seq 15 — 2026-08-12 — H3 Novelty Discrimination Experiment (exp_discriminative_novelty.py)

* **Context:** Third and final empirical test of the theoretical framework's Hypothesis H3,
  verifying that the ratio between projection distance outside the base B_0 and
  kinetic dissipation K_cin quantitatively separates transient noise/anomalies
  from real structural base updates.
* **Theory:** In the Traianus substrate, when new data points arrive, they either:
  - Represent transient noise/local turbulence → high K_cin but vectors fall within
    the subespacio abarcado por B_0 (get absorbed/rejected)
  - Represent structural novelty → consistent directional changes with moderate
    K_cin AND significant projection distance outside B_0, triggering base B_0 update
  The K_cin vs. projection-distance relationship creates a discriminative boundary.
* **Experiment:** `tools/experiments/exp_discriminative_novelty.py` generated two regions
  in R^384 (n=60 each) with reduced base B_0 (k=96):
  1. Noise region: random perturbations per step → high K_cin avg = 0.042556,
     proj dist avg = 0.521772
  2. Structural update region: consistent gradual rotation → very low K_cin avg =
     0.000012, proj dist avg = 0.455373
  The separation in K_cin = 0.042544 and projection distance = 0.066398 confirms
  that the ratio ||v - v · B_0^T B_0|| / K_cin discriminates between noise and
  structural updates.
* **Results:** Noise has high K_cin (transient turbulence) but moderate projection
  distance. Structural updates have very low K_cin (smooth rotation) with consistent
  projection outside B_0. The ratio metric successfully separates the two regimes.
* **Verdict:** H3 VALIDA — la relación entre disipación cinética K_cin y la
  distancia de proyección a la base separa estrictamente el ruido/anomalías
  transitorias de las actualizaciones estructurales reales de la base.
* **Status:** `Consolidated`. Empirical base for complete H1∧H2∧H3 framework validation.

### seq 16 — 2026-08-13 — Integrated Cinematic Pipeline validation (H1∧H2∧H3)

* **Context:** Verification that the H1/H2/H3 core kernels hold under a
  continuous, non-homogeneous stream of synthetic events (`tests/test_cinematic_pipeline.py`),
  exercising the 200-event 5-phase dataset against the pure core operators
  (`compute_kinetic_resistance`, `ortho_distance`, `discrimination_ratio`).
* **Phases (t ranges):**
  1. Laminar [1..40] — smooth displacement, max K_cin < θ_dyn.
  2. Estática [41..70] — v_t = v_{t-1} ⇒ K_cin ≈ 0.0 exact (Δv = 0).
  3. Enquistamiento [71..110] — micro-oscillations, min K_cin > θ_dyn.
  4. Ruido [111..150] — stochastic jumps, low discrimination ratio (mean dr < θ_struct).
  5. Novedad [151..200] — geodesic rotation outside B_0, dr ≥ θ_struct.
* **Scope note:** the test validates the **core computational kernels**
  (numpy-only, pure) per phase. `project_dimensional_relief` (H2) is imported
  but not asserted by this test; lifecycle routing assertions
  (`quarantine_noise`/`structural_candidate`) are NOT covered here and belong
  to the integration layer.
* **Gate (measured):** `pytest tests/test_cinematic_pipeline.py` → **5 passed**;
  full suite `pytest tests/` → **110 passed** (hermetic + model).
* **Status:** `Consolidated`. Integrated-kernel regression coverage for
  H1∧H2∧H3 as pure operators.

### seq 17 — 2026-08-14 — Phase 2: Representation protocol, DI and geometry/governance split (issues #44..#49)

* **Context:** decouple the substrate from the concrete embedding engine and
  separate observational geometry from the dual-key governance gate, without
  breaking the existing suite.
* **Δ executed:**
  - **Packaging:** `[tool.setuptools.packages.find]` replaces
    `packages = ["traianus"]` so subpackages install (previously latent defect,
    issue #44).
  - **Representation layer:** `traianus/representation/protocol.py` defines the
    `RepresentationProvider` protocol (`dimension`, `encode`, `encode_batch`,
    native float32 output). `sentence_transformer.py` wraps all-MiniLM-L6-v2
    (offline M3: `local_files_only=True`), centralizing `MODEL_ID` /
    `MODEL_REVISION`; `mock_provider.py` is the deterministic hermetic double
    (absorbs `tests/helpers/fake_encoder.py`, now an alias) (issues #45..#46).
  - **DI:** `traianus/app.py` and `traianus/bootstrap.py` consume the provider
    via lazy `get_provider()`; direct `sentence_transformers` imports removed;
    `_encode_vector` validates against `provider.dimension` (was hardcoded 384).
    Seam migrated in the same step: conftest `_hermetic_model`, cinematic
    pipeline, audit harness, `validate_c1_semantics` (issue #47).
  - **Geometry/governance split:** six pure observables moved to
    `traianus/geometry/observables.py` (K_cin, ortho distance, discrimination
    ratio, dimensional relief, ε-adjacency, threshold calibration); the dual-key
    C1 gate moved to `traianus/governance/gate.py` with canonical
    `evaluate_gate` and compat alias `evaluate_gate_v01`. `traianus/core.py`
    remains a re-export shim so legacy imports resolve unchanged (issues #48..#49).
  - **Remediation (post-review):** `traianus/app.py` consumes the canonical
    symbols directly (`evaluate_gate` from `traianus/governance/gate.py`,
    `calibrate_critical_threshold` / `compute_kinetic_resistance` from
    `traianus/geometry/observables.py`); offline construction is verified
    behaviorally (kwargs capture of `local_files_only=True`, no
    `inspect.getsource`); the M3 import side-effect (`HF_HUB_OFFLINE=1`) is
    declared in the provider module docstring; dead compat helpers
    (`build_mock_provider`, `build_fake_encoder`) removed; doc line references
    in `IMPLEMENTATION_STATUS.md` re-anchored to the refactored source.
* **Gate (measured, reproducible):**
  - `pytest tests/` → **126 passed** (hermetic + model, was 110 before).
  - `python3 tools/audit/audit_harness.py` → **C1 GUARD PASSED IN GREEN (45%, 9/20)**.
  - `grep -c "sentence_transformers" traianus/app.py traianus/bootstrap.py` → **0**.
* **Status:** `Consolidated`.

### seq 18 — 2026-08-14 — Phase 3.3: Representation Independence central experiment (issue #53)

* **Context:** prove that governance RULES are invariant under total
  representation replacement (ASSERT layer) while measuring the outcome
  coupling quantitatively (REPORT layer), over the same WP1 corpus and the
  same ephemeral DB seeded with the frozen realistic 384D geodetic basis.
* **Δ executed:**
  - **Harness:** `tools/experiments/exp_representation_independence.py` runs
    four scenarios — **A** `SentenceTransformerProvider` (all-MiniLM-L6-v2,
    384D, offline), **B** `MockRepresentationProvider` (isomorphic 384D),
    **C.1** `SyntheticHeteroProvider(128)` zero-padded through the full
    pipeline, **C.2** `SyntheticHeteroProvider(512)` fail-closed at the
    boundary — each against a fresh ephemeral DB. ASSERT invariants
    (violation = RED/exit 1): A. seq contiguous 1..N per id + append-only
    replay diff; B. dual-key (`EthicalKey=False → incubating` unconditionally);
    C. persisted states ⊆ {pending_approval, incubating, consolidated,
    telemetry_error}; D. fail-closed ingress (415 non-text/plain, 400 null
    byte); E. ε-edge set deterministic and equal to
    `storage.rebuild_epsilon_edges(0.8)`. REPORT layer (never fails):
    κ per provider/category, σ² distribution, edge density, edge-set Jaccard,
    rate spread.
  - **Bug fixed en route:** `allowed_states` in `_snapshot_nodes` read column
    index `r[2]` (text) instead of `r[4]` (lifecycle_state); corrected.
  - **Hermetic smoke:** `tests/test_representation_independence.py` re-runs
    scenarios B, C.1, C.2 over a six-note corpus (no model, no network) and
    re-asserts the governance and rejection invariants.
* **Gate (measured, reproducible):**
  - Runner (scenario A + B + C.1 + C.2, full WP1 corpus):
    - `[a]` κ=0.090 states={incubating:101, consolidated:10}
    - `[b]` κ=0.018 states={incubating:109, consolidated:2}
    - `[c1]` κ=0.054 states={incubating:105, consolidated:6}
    - `[c2]` vector_422=422, node_rows_written=0, telemetry_error_rows=1
    - `edge_jaccard={'a<->b': 1.0, 'a<->c1': 1.0, 'b<->c1': 1.0}` —
      vacuous 1.0: every scenario yielded `edge_count=0` at ε=0.8 over the
      WP1 corpus; `edges_deterministic` still holds.
    - `rate_spread = 0.072` (a 0.090 − c1 0.054, − b 0.018).
    - σ² means per category — a: A 0.002176 / B 0.002582 / C 0.002021;
      b: A 0.001682 / B 0.001817 / C 0.001722; c1: A 0.001939 / B 0.001931 /
      C 0.001613 — all within the ~0.0016–0.0026 band.
    - `pytest tests/` → **142 passed, 5 deselected** (hermetic, was 139 in 3.2).
    - BoundaryValidator gate cases: `0f6298d3` (runner), `85a2f81f` (smoke).
* **Status:** `Consolidated`. Representation Independence promoted to
  **B. Experimental** in `docs/STATUS.md`.

### seq 19 — 2026-08-14 — Red Team remediation: degenerate ε-edges made vacuous (pre-tag v1.0.0)

* **Context:** Red Team finding before the v1.0.0 tag — the Representation
  Independence experiment reported `edge_count=0` at ε=0.8 over the 384D
  L2-normalized WP1 corpus, so the E. determinism ASSERT and the edge-set
  Jaccard (1.0) were VACUOUS: two empty graphs always compare as identical
  (∅=∅), proving nothing about representation independence.
* **Δ executed:**
  - **RED test:** `tests/test_representation_independence.py::
    test_epsilon_edge_set_is_non_vacuous_under_mock_provider` failed with
    `edge_count=0` on the pre-fix harness (gate `b203e42e`).
  - **Calibration:** `calibrate_epsilon(vectors, target_density=0.05)` in
    `exp_representation_independence.py` returns the k-th smallest pairwise
    L2 distance over the L2-normalized corpus vectors (k = max(1,
    int(density·n_pairs))), stepping one rank further so the float32→float64
    drift of persisted `vector_blob` cannot push the k-th closest pair
    outside `dist <= ε` (gate `994edf3d`); normalization added so raw
    non-normalized providers cannot calibrate over un-normalized distances
    and yield a degenerate full graph (gate `0fb0662b`).
  - **Seam injection:** the calibrated ε is patched into
    `main_module.EPSILON_EDGE` inside `try/finally` (restored after the
    scenario), mirroring the provider-injection seam; the E. determinism
    check now compares the live endpoint against
    `storage.rebuild_epsilon_edges(calibrated_eps)`.
  - **Hardened ASSERT:** `assert_invariants` now enforces
    `non_vacuous_edges` (`edge_count > 0`), so a degenerate graph is a
    governance-rule violation (RED), not a silent pass.
* **Gate (measured, reproducible):**
  - Calibrated ε-edges (density ≈ 5%): `[a]` ε=1.1786 edges=305;
    `[b]` ε=1.3538 edges=306; `[c1]` ε=1.3109 edges=305; `[c2]` unchanged
    (422 / 0 node rows / 1 telemetry_error).
  - **Edge-set Jaccard now real:** a↔b=0.0252, a↔c1=0.0252, b↔c1=0.0269
    (was a vacuous 1.0). Findings: the governance RULES are invariant across
    representations (all ASSERTs green, κ spread 0.018–0.090 unchanged),
    while the local E_n structure is HIGHLY representation-dependent
    (~2.5% of the 5%-density neighborhoods coincide) — the vacuous 1.0 had
    masked this coupling.
  - `pytest tests/` → **143 passed, 5 deselected** (was 142 in seq 18).
* **Status:** `Consolidated`.

### seq 20 — 2026-08-14 — Red Team remediation II: κ coupling semantics + realistic-basis tooling (pre-tag v1.0.0)

* **Context:** two Red Team findings before the v1.0.0 tag — (P2) a
  conceptual mismatch: κ variation across providers was misread as a
  governance-invariance failure; (P3) tooling debt: `exp_vorticity_pressure.py`
  (H1) measured K_cin against a full-rank identity (one-hot) basis.
* **Δ executed:**
  - **P2 (κ = coupling index, REPORT):** the 3.3 runner now labels kappa
    spread explicitly as the REPRESENTATION COUPLING index: the JSON report
    carries `coupling_index` alongside `rate_spread` and the run prints a
    REPORT line stating that κ variation quantifies how each embedding space
    deforms consolidation geometry while the governance RULES (ASSERT layer)
    are invariant and independent of κ. The ASSERT layer covers only the
    rules (state machine, Dual-Key C1, WAL order, boundary rejections,
    non-vacuous deterministic ε-edges); κ spread never fails the run.
  - **P3 (realistic basis for synthetic runs):** `exp_vorticity_pressure.py`
    replaces `B_0 = np.eye(dim)` (full-rank identity/one-hot) with the frozen
    realistic geodetic basis `tests/fixtures/nsm_axes_8.json` (8 × 384) via
    `load_realistic_basis()`, with a fail-loud dimension guard. Deterministic
    RNG (seeds 42 / 42+1000) is preserved — determinism is a feature for
    reproducibility. The Red Team's own untracked diagnostic
    (`exp_cinematic_analysis.py`) and the falsified sparse-lexicon substrate
    (seq 10) are intentionally left untouched.
* **Gate (measured, reproducible):**
  - H1 re-validated under the realistic basis: free K_cin = 0.006115,
    compressed K_cin = 0.032985 → **H1 VALIDA** (verdict and values unchanged:
    the frozen NSM axes are near-orthogonal, so Var(v·B_0ᵀ) ≈ Var(v)).
  - Runner GREEN: `coupling_index = rate_spread = 0.072`, edge-jaccard
    a↔b=0.025, a↔c1=0.025, b↔c1=0.027 — reported as coupling measurements,
    not rule failures.
  - `pytest tests/` → **143 passed, 5 deselected** (unchanged).
  - BoundaryValidator gates: `d04ed591` (P2 labeling), `7eadd5a7` (P3 migration),
    `2e6dae44` (docs).
* **Status:** `Consolidated`.

### seq 21 — 2026-08-14 — Phase 5: Brand Decontamination and 100% English Standardization (TA-5.1 / TA-5.2 / TA-5.3 / TA-5.4 / TA-5.5)
- **TA-5.1 (Brand Decontamination):** Eliminated all traces of the "TridenGuard" brand name across the codebase, replacing it with the neutral technical term "BoundaryValidator / boundary-validator". Renamed `.opencode/skills/tridenguard-5-radicales/` to `.opencode/skills/boundary-validator/`. Renamed `tests/security/test_tridenguard_validator.py` to `tests/security/test_boundary_validator.py`. Updated references in `AGENTS.md`, `opencode.jsonc`, `traianus/security/`, `tests/security/`, `tests/helpers/`, `pyproject.toml`, and `docs/`.
- **TA-5.2 (Code and Language Audit — 100% English Policy):** Ran `python3 tools/audit/audit_spanish_terms.py` which identified Spanish-occurring terms across the codebase. Translated genuine Spanish narrative content in `tools/experiments/exp_manifesto_tomo0.py`, `tools/experiments/exp_vorticity_pressure.py`, and `tests/integration/test_h1_pressure_integration.py` to strict English. Enforced English docstrings, comments, and narrative throughout `traianus/`, `tools/`, and `tests/`.
- **TA-5.3 (Documentation Audit — 100% English):** Reviewed `docs/` and translated any remaining narrative sections to English. Verified relative links between `README.md` and `docs/` files. Synced `STATUS.md`, `LEDGER.md`, and `AUDIT.md` to ensure final metrics (143/143 hermetic tests passed, consolidation rate κ ≈ 0.025, κ REPORT) and the new `tests/` structure match reality exactly.
- **TA-5.4 (Agent Verification and Test Suite):** Executed `pytest tests/` (143/143 hermetic tests passed). Ran `python3 tools/audit/audit_harness.py` confirming C1 guard GREEN (non-degenerate, 9/20 consolidation rate). Confirmed no obsolete imports or dead code remain post-refactor.
- **TA-5.5 (Documentation Record):** Added seq 21 entry documenting the full phase5 decontamination and audit process. Final commit: `audit(phase5): brand decontamination, 100% english standardization, and full agent governance audit`.

**Gate:** hermetic suite green + C1 guard green + invariants verified.

- **Status:** `Consolidated`. All brand decontamination, language standardization, and governance audit phases complete.

### seq 22 — 2026-08-19 — WP1 Latency Decomposition (validate_wp1_empirical.py)

* **Context:** Empirical measurement of the H3 I/O stability hypothesis to isolate SQLite WAL persistence latency from sentence-transformer encoding latency.
* **Method:** Modified `tools/experiments/validation/validate_wp1_empirical.py` to use a persistent SQLite connection with `PRAGMA wal_autocheckpoint = 0`, measuring `encode_latency_us` and `sqlite_persist_latency_us` separately over the 111-note WP1 corpus.
* **Results:**
  - `sqlite_persist_latency_us`: p50=459μs, p95=989μs, p99=1,693μs, max=2,495μs
  - `encode_latency_us`: p50=11,546μs, p95=33,022μs, p99=39,940μs, max=54,025μs
  - `total_latency_us`: p50=11,956μs, p95=33,455μs, p99=40,397μs, max=56,520μs
* **Verdict:** **H3 I/O stability VALIDATED for SQLite persistence** (p50 < 1ms, p95 < 1ms). The encoding latency is a provider-layer concern (sentence-transformer), not a control-plane defect. Architecture correctly isolates WAL I/O via persistent connection.
* **Status:** `Consolidated`. Telemetry at `docs/audit/telemetry_real_corpus_v1.json`.

### seq 23 — 2026-08-24 — Post-v1.0.0 audit remediation: security-suite DB isolation + strict 5-Radicals gate conformance

* **Context:** Independent repository audit found (A) every `validate_proposal()`
  call in the security suite wrote its audit row into the real repo-root
  `traianus.db` (~4k polluted rows): `validator.py` bound `DB_PATH` by value at
  import time, immune to the autouse `isolate_db` monkeypatch; (B) the
  Zero-Trust gate accepted schema-violating payloads fail-open: an empty `{}`
  payload returned EXECUTE_SAFE and an invented `Intent_Class` (e.g. "HACK")
  skipped the mandatory literal-grounding gate.
* **Δ executed:**
  - Lazy DB resolution: `_persist_audit` reads `storage.DB_PATH` at call time;
    the MCP stdio integration test (SEC-M-06) runs under an isolated CWD so the
    spawned server never touches the repo-root database.
  - Strict conformance: `AgentMutationProposal.model_validate` runs after
    content screening; `Target_File` is merged out-of-band (MCP argument);
    unknown enums, extra fields and non-dict payloads return INVALID_JSON;
    a present-but-invalid `Safety_Abort` returns BLOCKED_BY_SAFETY_GATE.
  - Contract alignment: `IntentClass` gains AUDIT (validator SEC-M-07 logic,
    MCP tool docs and committed tests already treated it as a grounding-gated
    mutating intent; only the normative schema lagged behind).
  - Ordering fix: forbidden-token screening now precedes protocol conformance.
* **Finding registered:** the denylist makes any proposal containing its own
  literals (e.g. future edits to the token list itself) ungateable — a
  self-referential blind spot. This session restructured around the list
  without touching it; a durable governance decision for modifying the list
  remains open.
* **Gate:** hermetic suite **160 passed, 5 deselected** (6 new regressions in
  `tests/security/test_db_isolation.py`); repo-root `audit_log` delta across a
  full suite run = 0 (previously grew on every run).
* **Status:** `Consolidated`.

### seq 24 — 2026-08-24 — Backlog remediation: error masking, label contract, C1 dedup, doc decontamination

* **Context:** Medium/low findings from the post-v1.0.0 independent audit:
  six endpoints leaked exception internals via `detail=str(e)`; the
  `/ingesta/vector` label flowed verbatim into persistent node/edge ids; the
  spectral-math MCP server re-implemented the C1 kernel (divergent-copy risk);
  tracked docs carried Spanish residue despite the seq 21 English policy;
  `contracts/` violated the logographic one-primary-md rule.
* **Δ executed:**
  - app.py: all six broad handlers now answer a fixed `Internal server error.`
    detail (regressions in `tests/security/test_internal_error_masking.py`).
  - app.py: `/ingesta/vector` label contract `[A-Za-z0-9_-]{1,64}` else 422;
    empty label keeps routing to the digest node-id path by design.
  - tools/mcp/spectral_math_mcp.py: delegates `critical_threshold` to
    `traianus.geometry.observables.calibrate_critical_threshold`; presentation
    stats computed locally (non-authoritative). Guard tests in
    `tests/unit/test_spectral_math_mcp.py`.
  - observables.py: kernel hardening uncovered by dedup — bases with k=1 no
    longer produce NaN (`np.var([])` skipped); empty basis returns 0.0.
  - AUDIT.md / ARCHITECTURE.md / PROJECT_IDENTITY.md: Spanish headings and
    invariant names translated to English. LEDGER history intentionally left
    untouched (append-only doctrine).
  - contracts/: POC_FREEZE_v1.md moved to isolated subfolder `freeze/`
    (logographic rule); README + INDEX links updated.
* **Gate:** hermetic suite **177 passed, 5 deselected** (+17 regressions);
  zero Spanish residue outside this ledger.
* **Status:** `Consolidated`.

### seq 25 — 2026-08-24 — Monorepo coexistence policy + terminology canon

* **Context:** Operator decisions on RefApp-01 PoC material living inside the
  Traianus tree: keep everything in one repository, with an explicit boundary
  instead of loose untracked files. Also: canonical English terms for the
  H2/H1/H3 experiment vocabulary.
* **Δ executed:**
  - Quarantine via `.gitignore`: global `node_modules/`, `.vite/`, `dist/`
    patterns; RefApp-01 local materials (`tools/results/`,
    `docs/manifesto/TOMO_0.md`, `Ethics_1.md`) ignored — durable, not lost,
    never committed by accident.
  - Promoted to tracked code: the ε-bridge audit TDD pair
    (`tools/analyze_bridges.py` + `tests/unit/test_analyze_bridges.py`).
    CI collection == local collection == **177** for the first time.
  - `frontend/` (Ulpia client layer) adopts a SOURCES-ONLY policy:
    only `package.json`, lockfile, vite config, `index.html` and `src/` will
    ever be committed; vendored/build artifacts stay ignored. Sources pending
    regeneration by the operator (none exist on disk today).
  - Terminology canon: `piscina` → **basin**, `relaminate` →
    **relaminarize** (fluid-dynamics term); verdict literals across H1/H2/H3
    experiments → `VALIDATED` / `FALSIFIED` (no consumers parse them;
    verified before rename).
* **Gate:** hermetic suite **177 passed, 5 deselected**; Spanish residue in
  tracked `.py` = 0; runtime smoke of `exp_dimensional_relief.py` prints
  English end-to-end (`Verdict: H2 VALIDATED`).
* **Status:** `Consolidated`.

### seq 26 — 2026-08-24 — NGI/NLnet grant infrastructure (code 2026-08-198)

* **Context:** Traianus was submitted to the NLnet Foundation
  (Fediversity_Fund call, €17,500 / 6 months, WP1–WP4) on 2026-07-31. The
  pre-session main tip (`a40a577`) is exactly what reviewers received.
* **Δ executed:**
  - Annotated tag `ngi-proposal-2026-08` pinned to `a40a577` — immutable
    snapshot of the submitted state.
  - Development branch `ngi` created from current main (`6807e49`, includes
    all seven post-audit hardening commits): future home of WP1–WP4 work.
  - Redundant pointer branch `NGI` deleted (superseded by the tag; case-
    collision on APFS forced deletion-before-recreation anyway).
  - Proposal-text corrections owned by the OPERATOR before resubmission:
    GPL-3.0 → AGPL-3.0-or-later (matches LICENSE/pyproject); "bitwise
    reproducible" → runtime determinism under pinned environment (finding
    M1). flake.nix restoration DEFERRED until grant outcome is known.
* **Status:** `Consolidated`.

### seq 27 — 2026-08-24 — Unification: origin/main (ulpia line) merged into hardened main

* **Context:** Discovery during push planning — `origin/main` pointed at the
  tip of the local-only `ulpia` branch (`d3c448b`, published directly as
  main), while the eight post-audit hardening commits existed only locally.
  The public repo and the hardened line had diverged; leaving that split
  visible during the NLnet review window was worse than integrating.
* **Classification (freeze coherence):** the ulpia substrate additions are
  CLIENT-FACING OBSERVATIONAL HELPERS (`svd_reduce`, chromatic scaling in
  `traianus/geometry/observables.py`; pure functions for Ulpia canvas
  projection) plus their tests — additive read-side tooling, NOT state-
  governance modifications. No gate semantics, storage schema, or state
  transition changed; POC_FREEZE §4 remains honored.
* **Δ executed:**
  - Pushed `ulpia` branch to origin (preservation) BEFORE any integration.
  - Pushed `ngi` branch + annotated tag `ngi-proposal-2026-08`.
  - Merged `origin/main` into local main: single conflict resolved in
    `ortho_distance` docstring (kept `k × d` typographic sign + `B_0 basin`
    phrasing; both lines had independently converged on `basin`).
    `.gitignore` auto-merged (local version is a strict superset).
  - Frontend sources (`package.json`, lockfile, vite config, `index.html`,
    `src/`) now live on main per the seq 25 sources-only policy.
* **Gate:** hermetic suite **190 passed, 5 deselected** (+13 from
  `tests/unit/test_svd_projection.py` and module-split additions).
* **Status:** `Consolidated`.

### seq 28 — 2026-08-24 — Hygiene wave N1–N10 + release 1.0.1 (patch)

* **Context:** Exhaustive re-audit of the unified main surfaced findings the
  pre-unification passes could not see (SVD helpers never audited, frontend
  now tracked, multi-epoch visualization path). Operator chose a PATCH bump:
  stability/security/hygiene corrections with zero functional-scope change
  to the sealed Control Plane.
* **Δ executed:**
  - Docs: current suite figures, ~12ms p50 latency, README layout (+frontend,
    ε-bridge auditor), INDEX traceability rows + remediation node, ownership
    table phantom entries replaced by real owners.
  - ε single source of truth: `traianus.config.resolve_epsilon_edge()`
    consumed by HTTP layer, `tools/analyze_bridges.py` and experiments —
    closes the divergent-copy class for ε that C1 closed for θ_dyn.
  - SVD hardening: ValueError on empty/non-finite input; svd_flip sign
    canonicalization mirrored in `frontend/src/projection.ts`; docstring
    corrections ((n,k) shape, d>=k domain); duplicated line removed.
  - analyze_bridges CLI: clean exits for missing DB / <2 nodes; percentile
    range validation; O(n²) adjacency computed once per mode.
  - Append-only static scanners cover `manifold_edges`; background ingestion
    logs via structlog instead of bare print; all SVD tests seeded.
  - Kernel namespace: svd_reduce/sigmoid_scale/project_to_5d removed from
    `traianus.core.__all__` (canonical home = geometry.observables);
    regression pins core exports to the v1.0.0 surface byte-for-byte.
* **Classification (patch-bump audit trail):** fixes = security/stability/
  hygiene incl. fail-closed gate conformance and ingress label contract;
  additive non-normative tooling = svd_* lab helpers (geometry only),
  bridge-audit pair, [viz] extra; governance semantics, storage schema and
  kernel namespace = UNCHANGED vs v1.0.0.
* **Gate:** hermetic suite **201 passed, 5 deselected** (+11: epsilon
  resolution ×4, SVD guards/sign ×4, bridges CLI ×2, frozen-kernel pin).
* **Status:** `Consolidated`.

### seq 29 — 2026-08-24 — NLnet clarifications sent; flake.nix flips to conditional commitment

* **Context:** Operator emailed NLnet (Re: Proposal 2026-08-198) attaching
  four exact before/after clarifications ahead of review:
  1. License → AGPL-3.0-or-later (matches LICENSE / pyproject.toml).
  2. Abstract determinism → deterministic state transitions reproducible at
     runtime under an identical pinned environment (finding M1 wording).
  3. "What is new in Traianus" → runtime-deterministic reproducibility
     invariant to vector origin (RH-0/1/2) — closes the surviving bitwise
     claim flagged in review.
  4. Ecosystem → reproducible developer environments WILL BE provided via
     Nix (flake.nix) as an infrastructure milestone during grant execution.
* **Decision flip (supersedes seq 26 deferral):** flake.nix is now a
  COMMITMENT conditional on funding — to be delivered on the `ngi` branch as
  an infrastructure milestone, with its own LEDGER entry and AGENTS §1.5
  reconciliation when implemented. Until then the repo remains flake-free by
  design; the proposal no longer claims it exists today.
* **Status:** `Consolidated`.

### seq 30 — 2026-08-24 — Research datasets dir; Spinoza Ethics corpus frozen (Parts I+II)

* **Dataset unification:** `Ethics_1.md` (operator-local, gitignored) moved to
  `data/spinoza/part1_god.md` and versioned; `/Ethics_1.md` exception removed
  from `.gitignore`. `tests/fixtures/` remains reserved for harness artifacts;
  `data/spinoza/` is the new research-dataset node.
* **Part II ("On the Nature and Origin of the Mind") frozen:** continuous text
  `part2_mind.md` + immutable sentence-level manifest `part2_mind_manifest.json`
  ({label -> chunk}, insertion order == reading order; ONE SENTENCE = ONE CHUNK).
  Source: Project Gutenberg eBook #3800 (Elwes translation, public domain);
  builder `tools/experiments/tooling/build_spinoza_part2_corpus.py` (offline,
  no network primitives, AGENTS §2.1). Label scheme: neutral metadata only,
  never embedded — `PART2_MIND_{DEF|AX|LEMMA|POST|PNN_PROP|_DEMO|_COR|_ESC}`.
  472 sentence-chunks (median 31 words); Elwes editorial "N.B." notes excluded.
* **Ephemeral SQLite work artifacts** stay under `.data/` (ignored); the frozen
  substrate at repo root is untouched.
* **Gate:** hermetic suite **201 passed, 5 deselected**.
* **Status:** `Consolidated`.

### seq 31 — 2026-08-24 — Fases 1-3 executed on Part II manifold; lab-analyst skill born

* **Fase 1 (ingestion):** `tools/experiments/tooling/ingest_spinoza_part2.py`
  (+ `tests/unit/test_ingest_spinoza_part2.py`) ran all 472 sentence-chunks
  through the real pipeline into scratch DB `.data/spinoza_part2.db`
  (epoch PROSTHETIC_NSM_V1 from the frozen nsm_axes_8 fixture; root substrate
  untouched). Result: 472 nodes, 698 persisted auto-edges (epsilon=0.8),
  dual-key gate 57/472 consolidated (12.1%, non-degenerate).
* **Fase 2 (diagnosis):** bridge audit — E_n=698 with 639 non-contiguous
  bridges vs 59 sequential (resonance-dominated manifold); adaptive epsilon
  p5 saturates (105k edges) on the narrow-cone embedding cloud, fixed mode
  retained. Pressure: definitions and P24-P31 (mind-body) hottest; max
  sigma^2=0.0172 at DEF_05 (duration) = 4x theta_dyn.
* **Fase 3 (static SVD):** `tools/experiments/tooling/export_svd_projection.py`
  (+ tests); PC1-3 = 7.05/5.94/4.92% of variance; reading-order continuity
  ratio 0.64 (consecutive steps shorter than random pairs); mind-body zone
  most separated cluster — coherent with its pressure maximum.
* **Fase 4 (skill):** `.opencode/skills/lab-analyst/SKILL.md` registered in
  AGENTS.md §6.5; companion tool `chromatic_audit.py` (+ tests): effective 5D
  (X,Y spatial + R,G,B singular-value-weighted PC3-PC5), collision rescue
  141/148 (95.3%, delta_rgb > 0.15), Sammon stress 2D->5D gain 43.1%
  (0.4837 -> 0.2751), falsifiable ontological alignment currently neutral
  (soma r=-0.05, duration r=-0.12 [n=2], potestas r=-0.06).
* **Gate:** hermetic suite **210 passed, 5 deselected**.
* **Status:** `Consolidated`.

### seq 32 — 2026-08-24 — Provenance correction + dataset hardening (review remediation)

* **Provenance blocker resolved:** `part1_god.md` contained globalgreyebooks.com
  hyperlink footnotes contradicting the declared PG#3800/Elwes source.
  Part I **re-derived from PG#3800** via the builder's new `--part {1,2}`
  flag; Gutenberg footnote markers/text blocks (`[N]`, editorial notes)
  stripped from both parts. `data/spinoza/PROVENANCE.md` added as the
  canonical source-of-truth document; superseded sources documented.
* **Drift guard:** `tests/unit/test_spinoza_dataset_consistency.py` asserts
  build(md) == manifest for both parts (dual-source-of-truth closed); part1
  now ships its own frozen manifest (`part1_god_manifest.json`).
* **Tooling dedup:** shared `_common.py` (load_nodes / load_labels /
  explained_variance_ratios with zero-variance guard) replaces duplicated
  copies in export_svd_projection.py and chromatic_audit.py; inline
  __import__ removed; Spinoza zone patterns renamed
  SPINOZA_ZONE_PATTERNS and documented as a corpus-specific falsifiable
  hypothesis; labels[nid] access made loud (no .get() masking).
* **CWD robustness:** ingest_spinoza_part2.py scratch/telemetry paths
  anchored to REPO_ROOT (was relative to the caller's directory).
* **Governance:** AGENTS.md 1.2 now codifies the deliberate exception for
  frozen datasets under data/** (incl. data/spinoza manifests).
* **Re-run on purified corpus (474 chunks):** 474 nodes / 703 auto-edges /
  gate 12.0%; Sammon gain 43.0%; collision rescue 142/149 (95.3%);
  ontological alignment still neutral — prior Fase 2-4 conclusions hold.
* **Gate:** hermetic suite green (see commit).
* **Status:** `Consolidated`.

### seq 33 — 2026-08-24 — Part III (De Affectibus) frozen; dual-mode manifold diagnostics

* **Corpus:** `part3_affects.md` + `part3_affects_manifest.json` derived via
  the generalized builder (`--part 3`): 647 sentence-chunks, labels
  `PART3_AFFECTS_*` incl. the 48 Definitions of the Emotions (`DEFEMO_NN`)
  and the closing General Definition (`GENDEF`). ROMAN map extended to LXXX;
  N.B. filter scoped to AXIOMS/POSTULATES (elsewhere it is Spinoza's own
  text — recovered Def. III activity/passion note). Parts I/II byte-identical
  under the generalized builder; drift guard extended to part3.
* **Runner:** `ingest_spinoza_part2.py` now parametrized (`--part {1,2,3}`,
  `--accumulate`) with per-part scratch DB/labels/telemetry conventions.
* **Isolated mode** (`.data/part3_affects.db`): 647 nodes / 726 auto-edges;
  gate 65/647 consolidated (10.0%, non-degenerate); bridges resonance-
  dominated as in Part II (670 vs 56 contiguous); chromatic rescue 98.6%
  (146 collisions); Sammon gain 45.2%.
* **Accumulated mode** (`.data/spinoza_full.db`, parts 1+2+3 in reading
  order): 1539 nodes / 2251 auto-edges; gate 199/1539 (12.9%). Inter-part
  epsilon edges: GOD<->MIND 132, MIND<->AFFECTS **199**, GOD<->AFFECTS 64
  (the Mind-Emotions continuum is the densest inter-part resonance).
  Densification impact: Sammon gain 45.2% -> 39.8% while collision rescue
  holds at ~96% — chromatic channels scale with the manifold.
* **Ontological hypothesis for Part III:** deliberately deferred until the
  affect-domain data is inspected (falsifiability discipline).
* **Gate:** hermetic suite **220 passed, 5 deselected**; invariant verifier
  GREEN (exit 0).
* **Status:** `Consolidated`.

### seq 34 — 2026-08-24 — External-audit remediation: honest naming, version truth, frozen evidence

* **Trigger:** external agent audit of `feature/pkm-spinoza-part3-affects`
  (naming debt, doc drift, Ulpia contradiction, unversioned evidence).
* **Honest naming:** `build_spinoza_part2_corpus.py` -> `build_spinoza_corpus.py`;
  `ingest_spinoza_part2.py` -> `ingest_spinoza_corpus.py` (tests renamed in
  step). No shims: tooling is unreleased; historical LEDGER mentions left
  untouched (append-only).
* **Version truth:** README badge/text and IMPLEMENTATION_STATUS header
  reconciled with pyproject v1.0.1 (substrate frozen at v1.0.0; zero scope
  change). IMPLEMENTATION_STATUS amended 2026-08-24.
* **Ulpia status corrected:** the "no UI code" claim replaced by the actual
  state — a client prototype exists under `frontend/` (ulpia-line merge);
  its integration with the read-only observation contract remains RESEARCH /
  FUTURE ROADMAP, out of substrate scope.
* **Evidence freeze:** `data/spinoza/telemetry/v1.json` (via committed
  `freeze_telemetry.py`) distills the ephemeral `.data/` artifacts into a
  versioned dataset: per-run nodes/edges/gate/sigma^2, chromatic Sammon +
  rescue rates, inter-part edge distribution (MIND<->AFFECTS = 199, densest
  continuum) and top cross-part bridges. Epistemic scope recorded: findings
  are conditional on the MiniLM-L6-v2 representation provider.
* **Not remediated (documented):** root-level `traianus.db` retained — it is
  the substrate-default DB_PATH of `traianus/storage.py`; CONTRIBUTING.md
  deferred to its own post-merge cycle.
* **Gate:** hermetic suite green (see commit); invariant verifier GREEN.
* **Status:** `Consolidated`.

### seq 35 — 2026-08-24 — Part IV (Of Human Bondage) frozen; 4-part accumulated manifold

* **Corpus:** `part4_bondage.md` + `part4_bondage_manifest.json` via
  `build_spinoza_corpus.py --part 4`: 549 sentence-chunks, labels
  `PART4_BONDAGE_*`, 73/73 propositions, full Appendix (72 chunks).
* **Parser hardening (PG#3800 punctuation variants):** trailing-period
  section headers (`PROPOSITIONS.`, `APPENDIX.`, singular `AXIOM.`) now
  matched; unnumbered single-item families auto-numbered instead of
  dropped. Side-effect fix on Part I: a spurious `PROPOSITIONS.` header
  chunk absorbed into AX_07 eliminated (418 -> 417 clean chunks).
* **Isolated mode** (`.data/part4_bondage.db`): 549 nodes / 382 edges;
  gate 86/549 consolidated (15.7%); chromatic rescue 97.9%; Sammon gain
  44.3%; zero stylistic duplicates.
* **Accumulated mode** (`.data/spinoza_full.db`, parts 1+2+3+4): 2087
  nodes / 2931 edges; gate 285/2087 (13.7%). Inter-part epsilon edges:
  **AFFECTS<->BONDAGE = 223, densest continuum** (MIND<->AFFECTS 199,
  GOD<->MIND 132) — Part IV's doctrine of the bondage to passions is the
  most strongly coupled layer, as its subject matter predicts.
* **Chromatic scalability gate:** collision rescue at n=2087 is 97.7%
  over 2352 collisions — holds above the 95% bar. Densification trend of
  Sammon gain: 45.2% (n=647) -> 39.8% (n=1539) -> 38.4% (n=2087).
* **Memory-safety fix:** `pairwise_dists` switched to the projected
  |x|^2+|y|^2-2xy form after the (n,n,d) intermediate OOM-killed the
  accumulated audit at n=2087 (~104MB peak after fix).
* **Evidence freeze:** `data/spinoza/telemetry/v2.json` supersedes v1.
* **Gate:** hermetic suite green (see commit); invariant verifier GREEN.
* **Status:** `Consolidated`.

### seq 36 — 2026-08-24 — Syntactic segmentation hardening; reproducibility source committed

* **Trigger:** operator-directed segmentation strategy + second audit round
  (drift-guard gap on Part IV, no builder reproducibility guard, fragile
  auto-number heuristic, pairwise_dists equivalence unpinned, Sammon trend
  provenance mixing).
* **Segmentation hardening** (`build_spinoza_corpus.py`): root-cause fix in
  `split_sentences` — the boundary-evidence window was anchored at the last
  emitted sentence, hiding the whitespace that abbreviation anchors require;
  window is now absolute. Abbreviation set extended (N.B., cf., vol., p./pp.,
  l./ll., n., ed., transl., St./Mr./Dr., roman numerals up to 6 chars for
  appendix items); citation debris ("Pollock.", "Gloria.", "N.B.") merges
  backwards into its carrier sentence. Lossless property (joined sentences ==
  normalized input) enforced by tests/unit/test_build_spinoza_corpus.py.
* **Corpus regenerated under the hardened tokenizer:** Part I 417 -> 409,
  Part II 474 -> 458, Part III 647 -> 627, Part IV 549 -> 507 (total 2001);
  <=2-word debris census now zero except the legitimate "Man thinks."
  All four scratch DBs re-ingested; chromatic audits re-run.
* **Reproducibility guard:** PG#3800 snapshot committed at
  `data/spinoza/source/pg3800.txt` (SHA-256 647f0227...);
  tests/unit/test_builder_reproducibility.py asserts byte-exact manifest
  reproduction for all four parts, documented proposition counts
  (36/49/59/73), the 48 Definitions of the Emotions, Part IV Appendix
  presence, and source-snapshot integrity.
* **Drift-guard gap closed:** test_part4_bondage_md_matches_manifest added
  (Part IV was the only part without md<->manifest enforcement).
* **pairwise_dists equivalence pinned:** projected form matches the naive
  formula within rtol=1e-9 / atol=1e-5 (documented catastrophic-cancellation
  trade-off); exact-zero clamp tested.
* **Evidence freeze:** `data/spinoza/telemetry/v3.json` supersedes v2
  (per-part runs under the new conventions: part1_god/part2_mind/
  part3_affects/part4_bondage + spinoza_full). Isolated Sammon gains:
  46.8% / 45.4% / 45.1%; accumulated (n=2001): 39.4% with rescue 97.4%
  over 1909 collisions. Inter-part edges: AFFECTS<->BONDAGE 215 remains
  the densest continuum. Note: the seq 35 densification midpoint (n=1539)
  was measured during the v1-era corpus and is retained as historical.
* **Gate:** hermetic suite **243 passed, 5 deselected**.
* **Status:** `Consolidated`.

### seq 37 — 2026-08-24 — Part V (Of the Power of the Intellect) frozen; Ethics corpus complete

* **Corpus:** `part5_power.md` + `part5_power_manifest.json` via
  `build_spinoza_corpus.py --part 5`: 220 sentence-chunks, labels
  `PART5_POWER_*`, 42/42 propositions, zero debris. Boundary end =
  "End of the Ethics" line. The five-part Ethics corpus is now complete
  (2001 + 220 = 2221 chunks).
* **Isolated mode** (`.data/part5_power.db`): 220 nodes / 143 edges;
  gate 21/220 consolidated (9.5%); chromatic rescue 93.1% over only
  29 collisions (small-sample floor; accumulated mode governs);
  Sammon gain 47.4% — highest of all parts.
* **Accumulated mode** (`.data/spinoza_full.db`, parts 1-5): 2221 nodes /
  3195 edges; gate 299/2221 (13.5%); rescue 97.3% over 2566 collisions;
  Sammon gain 39.4%. Inter-part matrix completed:
  **MIND<->POWER = 126** — second-strongest continuum overall, ahead of
  GOD<->MIND (122): the intellect-power doctrine of Part V resonates
  primarily with Part II, as its subject predicts. AFFECTS<->POWER 76,
  BONDAGE<->POWER 60, GOD<->
  POWER 14 (weakest link).
* **Evidence freeze:** `data/spinoza/telemetry/v4.json` supersedes v3.
* **Gate:** hermetic suite **246 passed, 5 deselected**.
* **Status:** `Consolidated`.
