# Traianus — Technical Audit Report and Remediation Plan

**Repository:** `AlexusPacicus/Traianus` @ `main` (commit `e2ab8bc`)
**Scope:** Full audit — code, tests, documentation, packaging, security, and the mathematics behind the claims.
**Method:** Static review of all files + **empirical execution** of real code paths against the real `all-MiniLM-L6-v2` model. Every quantitative datum in this report was **measured**, not estimated. The reproduction harness is in **Appendix A**.
**Overall Assessment:** The PoC core works, but **the flagship feature does not operate on real data (measured: 0%)**, several declared "non-negotiable" invariants are contradicted by the code itself, and the documentation oversells the system by a wide margin.

---

## How to read this report

| Severity | Meaning |
|---|---|
| 🔴 **Critical** | Core functionality broken or real security exposure. Fix before any external use. |
| 🟠 **High** | Incorrect/misleading behavior, data loss, or a claim directly contradicted by code. |
| 🟡 **Medium** | Correctness/reproducibility/packaging defects that will affect real users. |
| 🔵 **Low** | Quality, hygiene, consistency. |
| ⚪ **Info** | Documentation/positioning calibration. |

Each finding includes **Evidence** (with measured data where applicable), **Impact**, and a **Fix** you can apply directly.

---

## Executive Summary

Traianus is, in its implementation: a FastAPI service that (1) generates text embeddings with MiniLM, (2) dot-products the embedding against 8 reference vectors derived from NSM primitives, (3) saves the result to SQLite, and (4) lets a human flip a boolean to "consolidate" a node. That is a reasonable proof of concept.

The problems are:

1. **The flagship feature does not work.** The "Dual-Key Consolidation → `consolidated`" path is unreachable with realistic inputs. Measured: **0 of 20** notes consolidated *even with human approval on all of them*, because the autocalibrated threshold sits ~16× above the maximum achievable input value. Root cause identified; two fixes provided with measured approval rates (2/20 and 8/20).
2. **Several "non-negotiable invariants" are false in code** — append-only/immutable, orthonormal basis, bitwise determinism, `<1ms` latency, offline operation, and the ingress firewall "rejects non-`text/plain`" are each contradicted by the implementation (all measured).
3. **The formal model is mostly unimplemented.** State is defined as a simplicial complex `S_n = (V_n, E_n, K_n)`, but the code never computes edges `E_n` (ε-adjacency) or faces `K_n`. Edges are drawn only by hand.
4. **The doc-to-code ratio is inverted** (~840 lines of docs vs ~575 of code) and the docs describe a much larger system than exists.

None of this is fatal to the *idea*. The fastest path to credibility is **making the claims match the code**: fix the consolidation bug, delete or implement every contradicted invariant, and rewrite the prose to fit the PoC.

---

## Findings Summary

| ID | Sev | Title | Location |
|---|---|---|---|
| C1 | 🔴 | Consolidation gate is dead code on real data: 0% approval (threshold scale mismatch) | `traianus/app.py:134-143`, `:280` |
| H1 | 🟠 | `/ingesta` swallows all errors and returns **fake HTTP 200**; ingestion failures lost silently | `traianus/app.py:248-249` |
| H2 | 🟠 | Ingress "firewall" is a 2-element denylist, not a `text/plain` allowlist (accepts JSON, PNG, HTML) | `traianus/app.py:237` |
| H3 | 🟠 | CORS reflects **any** origin **with credentials**; no auth; `/mutate` is destructive and unauthenticated | `traianus/app.py:12-18`, `:401` |
| H4 | 🟠 | Code violates its invariant #1: append-only/immutable (uses REPLACE/UPDATE on nodes, axes, edges) | `traianus/app.py:195,298,421,390` |
| H5 | 🟠 | Formal model unimplemented: no `E_n` (ε-adjacency) or `K_n` (faces) in code | `traianus/app.py` (absent) |
| M1 | 🟡 | "Bitwise determinism across environments" false — vertices are torch float32 outputs, not portable | `traianus/app.py:20`, measured |
| M2 | 🟡 | "`<1ms` full governance" false — measured 13.3 ms/encode | measured |
| M3 | 🟡 | "Offline / zero cloud dependency" false — first run downloads model from HF Hub; no offline guard | `traianus/app.py:20` |
| M4 | 🟡 | Packaging misconfigured: `pip install -e .` exposes `py.main`, not `main`; server/bootstrap undocumented | `pyproject.toml`, README |
| M5 | 🟡 | More silent failures: `/nodos` returns empty `SUCCESS` on error; `/telemetry` leaks traces unauthenticated | `traianus/app.py:342,345-363` |
| M6 | 🟡 | Magic numbers and unjustified metric (`action_potential = variance*10.0`) contradict ADR-005 | `traianus/app.py:183,291` |
| M7 | 🟡 | Consolidation overwrites node vector/text with client input; no row check (consolidate missing node → SUCCESS) | `traianus/app.py:298-316` |
| M8 | 🟡 | No CI; `flake.nix` unpinned (`nixos-unstable`, no `flake.lock`) → "reproducible" is false | repo, `flake.nix` |
| L1 | 🔵 | Tests exercise geometry production never generates; flagship test accepts "any result"; not hermetic | `tests/…:82-88,192` |
| L2 | 🔵 | `forge_relation` allows dangling edges; edges mutable; inconsistent WAL usage | `traianus/app.py:379-395` |
| L3 | 🔵 | Public API in mixed Spanish/English (`/ingesta`, `/nodos`, `/consolidar`, `simbolo`) | whole repo |
| L4 | 🔵 | NSM list has 64 entries with near-duplicates; a duplicate (`BE_BELOW`) was picked as axis | `traianus/bootstrap.py:10-32` |
| L5 | 🟡 | `RefinedEntity` validation is decorative (validated `.projections` list is not what gets saved) | `traianus/app.py:185-203` |
| L6 | 🟡 | Dimensional brittleness: only `dim_db > dim_in` handled; other providers (the selling point) break dot products | `traianus/app.py:162-166` |
| I1-I6 | ⚪ | Rhetoric/positioning: grandiose renaming program, ADR theater, doc-vs-doc contradictions, decorative citations | docs |

---

## Remediation Status — 2026-08-01 cycle (TDD execution cycle)

Synced with the cycle commit (see `git log`). Resolution criterion: the fix is implemented in code **and** verified by a deterministic test or by the empirical harness (`tools/audit_harness.py` → `✅ C1 GUARD PASSED IN GREEN`, rate 30% = 6/20 on calibrated corpus).

| ID | Status | Evidence |
|---|---|---|
| C1 | ✅ **Resolved** | `auto_calibrate_critical_threshold()` excludes self-projection (`traianus/app.py`); harness green with rate 6/20 (30%) within `[5%, 95%]`; regression `test_auto_calibrate_excludes_self_projection`. |
| H1 | ✅ **Resolved** | `/ingesta` fails loudly with `503` on persistence failure (`raise HTTPException(status_code=503) ... from e`); regression `test_ingesta_returns_503_on_persistence_failure`. |
| H2 | ✅ **Resolved** | `ALLOWED_INGRESS_TYPES = {"text/plain"}` as allowlist; 415 for everything else; regressions `test_ingesta_endpoint_rejects_non_plain_text_payloads` and `..._rejects_application_json_at_perimeter`. |
| H3 | ✅ **Resolved** | CORS enumerated without wildcard (`ALLOWED_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]`); operator token `require_token` on mutating routes; server documented on `127.0.0.1`; regressions `test_cors_origins_are_enumerated_no_wildcard` and `test_protected_endpoints_*`. |
| H4 | ✅ **Resolved** | `manifold_nodes` AND `manifold_edges` converted to append-only revision logs (composite PK `(id, seq)`, every transition INSERTS a new revision, "current state" = `MAX(seq)` per id); `geodesic_axes` mutable ONLY inside `logographic_genesis` (ADR-025 decision B), `bootstrap.py` uses `INSERT OR IGNORE` (no DELETE); legacy migration preserves pre-existing rows as `seq=1`. Tests: `tests/genericos/test_g5_append_only.py`. |
| H5 | ✅ **Resolved** | Deterministic E_n implemented: `_compute_epsilon_edges`/`rebuild_epsilon_edges`/`persist_epsilon_edges` (ε-adjacency, ||v_i − v_j||₂ ≤ ε, server-side `EPSILON_EDGE`), persisted as `auto-edge-*` rows with `removed` tombstones; K_n deferred to WP2 (ADR-018/019). Tests: relations block + ε-edge persistence. |
| M1 | 🟡 **Open** | Bitwise determinism not guaranteeable across environments (torch float32 outputs); no model/torch pins. |
| M2 | 🟡 **Open** | `<1ms` still false for `model.encode()` (~13 ms); no benchmark script. |
| M3 | ✅ **Resolved** | `os.environ.setdefault("HF_HUB_OFFLINE", "1")` and `local_files_only=True` in `app.py` and `bootstrap.py`; regressions `test_encoder_constructed_offline_local_files_only` and `test_bootstrap_encoder_constructed_offline_local_files_only`. |
| M4 | ✅ **Resolved** | Real package `traianus/` (renamed from `py/`); `pyproject.toml` with `[project.scripts] traianus-bootstrap` and `packages = ["traianus"]`; quickstart `traianus-bootstrap → uvicorn traianus.app:app --host 127.0.0.1`. |
| M5 | ✅ **Resolved** | `/nodos` returns 5xx on DB error (`test_nodos_returns_500_on_db_error`); `/telemetry` requires operator token (`test_telemetry_requires_operator_token`). |
| M6 | ✅ **Resolved** | `action_potential = float(variance)` without the magic `*10.0` constant; regression `test_action_potential_is_variance_not_scaled`. |
| M7 | ✅ **Resolved** | Consolidation INSERTS a new revision (original not destroyed, H4); missing node → `404` (`test_consolidar_missing_node_returns_404`). |
| M8 | 🟡 **Open** | No CI; `flake.nix` without committed `flake.lock`. |
| L1 | 🔵 **Open** | One-hot fixture persists in unit tests; harness (`tools/audit_harness.py`) adds real-base integration coverage (hermetic, no writes to `traianus.db`). Missing fake encoder injection in unit tests. |
| L2 | ✅ **Resolved** | Dangling edges rejected (`forge_relation` validates both endpoints → 404); edges are an append-only revision log (no UPDATE / ON CONFLICT DO UPDATE); every DB handler executes `PRAGMA journal_mode=WAL`. Tests: `tests/genericos/test_g3_wal.py`, relations block. |
| L3 | 🔵 **Open** | Mixed languages in public API. |
| L4 | 🔵 **Open** | NSM inventory with near-duplicates. |
| L5 | ✅ **Resolved** | `RefinedEntity` validated `projections` are what gets persisted: `projections_json` derives from `validated_entity.projections` (the Pydantic contract is the single source of truth). |
| L6 | ✅ **Resolved** | Provider dimension > basis rejected explicitly: HTTP 422 in `/nodos/{node_id}/consolidar`, `ValueError` in the spectral processor (`dim_in > dim_db`); the `dim_db > dim_in` padding direction preserved. Tests: `tests/afirmaciones/test_cl_i62_dimension_provider.py` (CL-I62). |

**Decision on `traianus.db` (derived artifact):** the local DB is regenerated/migrated as a derived artifact (gitignored). Schema migration to `(id, seq)` preserves the 23 pre-existing rows as `seq=1` revisions — no data was deleted. Not committed.

---

## 🔴 Critical

### C1 — The consolidation gate is dead code on real data

**Evidence (measured).** Running the real app with an initialized NSM basis and a corpus of 20 personal knowledge notes:

```
autocalibrated dynamic threshold σ²_dyn = 0.069242
input variance σ²:  min=0.000325  mean=0.002611  max=0.006783
Topological Key PASSED (σ² ≥ threshold): 0/20  (0%)
With Ethical Key = TRUE on ALL nodes: consolidated=0  incubating=20
```

Every input variance is **between 10× and 200× below** the threshold. The `consolidated` state is unreachable regardless of human approval.

**Root cause.** `auto_calibrate_critical_threshold()` (`traianus/app.py:134-143`) builds the threshold by projecting each axis onto **all** axes *including itself*. For an L2-normalized axis, the projection onto itself is exactly `1.0`, so each axis's projection list looks like `[1.0, 0.23, 0.07, …]` (variance ≈ 0.069). But a real input is never one of the axes — its projections top out at ~0.34 (measured off-diagonal cosine: mean 0.227, max 0.336), giving a variance ≈ 0.0026. **The threshold is computed on a scale the input can never reach.** The `1.0` self-projection term inflates it ~16×.

**Impact.** The central thesis — deterministic dual-key state consolidation — yields zero consolidations. The test suite masks this by accepting `new_state in ["consolidated", "incubating"]` (see L1).

**Fix (measured).** Exclude self-projection from calibration. Minimal change:

```python
def auto_calibrate_critical_threshold() -> float:
    matrix = get_geodetic_matrix_db()
    if not matrix:
        raise RuntimeError("[Traianus Core] Error: Geodetic matrix empty. Aborting autocalibration.")
    vectors = [entry["vector"] for entry in matrix.values()]
    base_variances = []
    for i, axis_vector in enumerate(vectors):
        # Cross projections only. Self-projection (dot == 1.0 for an
        # L2-normalized axis) inflated the baseline to an unreachable scale
        # for inputs, forcing the Topological Key to a 0% approval rate on
        # real corpora. See finding C1.
        projections = [
            float(np.dot(axis_vector, other))
            for j, other in enumerate(vectors) if j != i
        ]
        base_variances.append(np.var(projections))
    return float(np.mean(base_variances))
```

Measured results of candidate fixes on the same corpus:

| Threshold definition | value | approval rate |
|---|---|---|
| Current (with self-projection) | 0.06924 | **0/20 (0%)** |
| Fix (a): exclude self-projection | 0.00429 | 2/20 (10%) |
| Fix (b): 60th percentile of observed input σ² | 0.00238 | 8/20 (40%) |

Fix (a) removes the scale bug with a one-line intention. **Fix (b)** (calibrate threshold from empirical distribution of ingested variances, persisted and updated as a rolling quantile) is more defensible because it targets a *controllable consolidation rate* rather than an arbitrary geometric constant. Recommend (a) now, (b) for WP1.

**Deeper problem.** There is no evidence that "projection variance" correlates with anything meaningful about a note's value. Before promoting this to a core mechanism, define what the gate is for and validate it. Until then, keep it but make it functional and add the regression test below.

**Regression test (protects against silent return to 0%).** See Appendix A — asserts that consolidation rate on a real corpus is in `[0.05, 0.95]`.

---

## 🟠 High

### H1 — `/ingesta` returns fake success and silently discards ingestion failures

**Evidence.** `traianus/app.py:239-249`:

```python
    except Exception:
        return {"status": 200, "data": "Empty synthetic success"}
```

Any exception in the ingestion endpoint (DB locked, disk full, schema drift) returns **HTTP 200** with a synthetic body and **logs nothing** — the async telemetry path (ADR-002) never fires because the failure happens before/around it. `CONTRACTS_AND_PRISMS.md` claims a "dual channel" that always persists a telemetry node; for ingestion failures that is false.

**Impact.** Silent data loss. A client thinks every note was accepted; some were never enqueued. This is the opposite of "forensic sovereignty".

**Fix.** Fail loudly, or persist a telemetry node *and* return a real error. Don't fabricate 200s:

```python
@app.post("/ingesta")
async def frontend_ingestion_endpoint(dump: RawDump, background_tasks: BackgroundTasks):
    if dump.type not in ALLOWED_INGRESS_TYPES:            # see H2
        raise HTTPException(status_code=415, detail="Only text/plain is accepted at ingress.")
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("PRAGMA journal_mode=WAL;")
            cur = conn.execute("INSERT INTO ingestion_queue (payload) VALUES (?)", (dump.text,))
            ingestion_id = cur.lastrowid
    except sqlite3.Error as e:
        raise HTTPException(status_code=503, detail="Ingress persistence unavailable.") from e
    background_tasks.add_task(async_spectral_processor, ingestion_id, dump.text)
    return {"status": "accepted", "ingestion_id": ingestion_id}
```

Apply the same principle to M5 (`/nodos`, `/telemetry`).

### H2 — The "Zero-Trust" ingress firewall is a 2-element denylist

**Evidence (measured).** `traianus/app.py:237` is `if dump.type in ["audio/ogg", "audio/m4a"]: reject`. Probing the live endpoint:

```
type='text/plain'          -> 200 accepted
type='application/json'    -> 200 accepted
type='image/png'           -> 200 accepted
type='text/html; <script>' -> 200 accepted
type='audio/ogg'           -> 400 rejected
```

The docs say "Synchronous reject if `type != text/plain`" and "Non-plaintext payloads rejected at perimeter". In reality **everything is accepted except two audio MIME types.**

**Fix.** Make it an allowlist (this also fixes the H1 signature):

```python
ALLOWED_INGRESS_TYPES = {"text/plain"}
# ...
if dump.type not in ALLOWED_INGRESS_TYPES:
    raise HTTPException(status_code=415, detail="Only text/plain is accepted at ingress.")
```

### H3 — CORS reflects any origin with credentials; no auth; `/mutate` destructive

**Evidence (measured).** With the exact config (`allow_origins=["*"]`, `allow_credentials=True`, `allow_methods=["*"]`, `traianus/app.py:12-18`), a request from `Origin: https://evil.example` receives:

```
Access-Control-Allow-Origin: https://evil.example
Access-Control-Allow-Credentials: true
```

Starlette reflects **any** origin when the wildcard is combined with credentials. No endpoint has authentication. `POST /mutate/{symbol}` (`traianus/app.py:401`) permanently resizes **all** axes and nodes.

**Impact.** Any website the user visits can fire cross-origin credentialed calls to the local API — including the destructive `/mutate` and `/consolidar`. For a single-user localhost PoC the blast radius is small, but this directly contradicts the "Zero-Trust" framing and is trivially exploitable via CSRF/DNS-rebinding.

**Fix.** (1) Drop the wildcard, enumerate the observation client origin(s). (2) Bind uvicorn to `127.0.0.1`. (3) Protect mutating endpoints with a local token.

```python
ALLOWED_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]  # Ulpia/RefApp dev origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# Minimal local auth for routes that mutate state:
from fastapi import Header, Depends
import os, secrets
_TOKEN = os.environ.get("TRAIANUS_TOKEN")  # set at boot; refuse boot if missing in non-dev
def require_token(x_traianus_token: str = Header(default="")):
    if not _TOKEN or not secrets.compare_digest(x_traianus_token, _TOKEN):
        raise HTTPException(status_code=401, detail="Missing/invalid operator token.")

@app.post("/mutate/{new_symbol}", dependencies=[Depends(require_token)])
async def logographic_genesis(new_symbol: str): ...
```

Boot: `uvicorn traianus.app:app --host 127.0.0.1 --port 8000`.

### H4 — Code violates its own "Monotonic Append-Only / Immutable" invariant

**Evidence.** Invariant #1 of `ADR-025` and §6.2 declare historical vertices, edges, and faces immutable, and evolution append-only. The code mutates in at least four places:

- `INSERT OR REPLACE INTO manifold_nodes` — `traianus/app.py:195`
- `UPDATE manifold_nodes SET text=…, vector_blob=…` (consolidate) — `traianus/app.py:298`
- `UPDATE geodesic_axes SET vector_blob` (mutate basis) — `traianus/app.py:421`
- `ON CONFLICT(id) DO UPDATE SET state` (edges) — `traianus/app.py:390`
- plus `DELETE FROM geodesic_axes` in bootstrap — `traianus/bootstrap.py:102`

**Impact.** The determinism/audit narrative rests on append-only immutability; the storage layer is fully mutable and history is destroyed on consolidate.

**Fix (pick one, with honesty).**
- **Cheaper:** delete the immutability claim from ADR-025/PROJECT_IDENTITY for the PoC. Don't claim what you don't deliver.
- **Real:** convert `manifold_nodes` to an append-only event log (`INSERT` a new revision row per state change with monotonically increasing `seq`; never `UPDATE`/`REPLACE`). Expose "current state" via a view that picks `MAX(seq)` per `id`. This also gives you the audit trail the docs promise.

### H5 — The simplicial complex `S_n = (V_n, E_n, K_n)` is not implemented

**Evidence.** `Project_architecture.md:34` and `ADR-023` define `E_n` as automatic adjacency where `d(v_i, v_j) ≤ ε`, and `K_n` as faces of mutually adjacent vertices. Search the code: no distance computation, no `ε`, no adjacency, no faces. `manifold_edges` is written **only** from the manual `POST /relations` (`traianus/app.py:379`). Therefore `E_n` (as defined) and `K_n` do not exist.

**Impact.** The central object the entire theory is written about is absent from the running system. What exists is "a set of vertices + a hand-curated edge list".

**Fix.** Either implement a minimal deterministic ε-graph, or reframe the model honestly.

```python
def rebuild_epsilon_edges(epsilon: float) -> None:
    """Deterministic E_n: (v_i, v_j) ∈ E_n iff ||v_i - v_j||_2 <= epsilon."""
    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute("SELECT id, vector_blob FROM manifold_nodes "
                            "WHERE lifecycle_state != 'telemetry_error'").fetchall()
    ids = [r[0] for r in rows]
    V = [np.frombuffer(r[1], dtype=np.float64) for r in rows]
    edges = []
    for a in range(len(V)):
        for b in range(a + 1, len(V)):
            if np.linalg.norm(V[a] - V[b]) <= epsilon:
                pair = sorted((ids[a], ids[b]))
                edges.append((f"edge-{pair[0]}-{pair[1]}", pair[0], pair[1], "auto"))
    with sqlite3.connect(DB_PATH) as conn:
        conn.executemany(
            "INSERT INTO manifold_edges (id, source, target, state) VALUES (?,?,?,?) "
            "ON CONFLICT(id) DO NOTHING", edges)
```

Defer `K_n` (faces / persistent homology) to WP2 as the docs already say — but then stop putting `K_n` in the PoC state definition.

---

## 🟡 Medium

### M1 — "Bitwise determinism across environments" is not achievable as built
Vertices stored in state are outputs of `model.encode()`. Measured dtype is **float32** (torch), then converted to float64 for storage. PyTorch results are **not** guaranteed bitwise identical across CPU/GPU, BLAS backend, thread count, or library version. No model revision pin, no torch pin, no seed, no `torch.use_deterministic_algorithms`. **Fix:** dial the claim down to "deterministic given identical input vectors" (which is true — `np.dot`/`np.var` are), pin `sentence-transformers`, model `revision=`, and torch; record provenance (model id + revision + dimensions) alongside each vector.

### M2 — "`<1ms` full governance" latency is ~13× off reality
Measured: `model.encode()` = **13.28 ms/call**; pure control-plane projection = **0.0092 ms**. The `<1ms` claim only holds for the dot-product step, which is not "full governance". **Fix:** expose both numbers separately, or drop the composite `<1ms` claim. Add a benchmark script so the number is defensible.

### M3 — "Offline / zero cloud dependency at runtime" is false on first run
The audit harness had to **download** `all-MiniLM-L6-v2` from the HF Hub on the first call to `SentenceTransformer(...)`. No `HF_HUB_OFFLINE`, no `local_files_only=True`, no bundled weights. **Fix:** add a one-time `make setup` that prefetches and pins the model; then put:
```python
os.environ.setdefault("HF_HUB_OFFLINE", "1")
model = SentenceTransformer("all-MiniLM-L6-v2", revision="<pin-a-commit-sha>", local_files_only=True)
```
and document the setup step. Only then is the "offline sovereignty" claim true.

### M4 — Packaging is misconfigured and the run path is undocumented
Measured: after `pip install -e .`, top-level `import main` is **False**; setuptools flat-layout auto-detection exposes an accidental `py` package (`import py.main` works). No `console_scripts`, README never shows how to start the server (`uvicorn`), and never says you must run `traianus/bootstrap.py` first (without it, every ingestion becomes `telemetry_error`). **Fix:**
- Move code to a real package: `traianus/app.py` → `traianus/app.py`, add `traianus/__init__.py`.
- `pyproject.toml`:
  ```toml
  [tool.setuptools]
  packages = ["traianus"]
  [project.scripts]
  traianus-bootstrap = "traianus.bootstrap:main"
  ```
- README: document `traianus-bootstrap` → `uvicorn traianus.app:app --host 127.0.0.1` as the real quickstart, before `pytest`.

### M5 — More silent failures that swallow errors
`/nodos` returns `{"status": "SUCCESS", "nodes": []}` on **any** exception (`traianus/app.py:342`) — a DB error is indistinguishable from an empty store. `/telemetry` (`traianus/app.py:345-363`) returns full stack traces to any unauthenticated caller, contradicting the ADR-002 purpose of "preventing external information leakage". **Fix:** return appropriate 5xx on real errors; put `/telemetry` behind the same operator token as H3.

### M6 — Magic numbers and an unvalidated metric contradict ADR-005
`action_potential = float(variance * 10.0)` (`traianus/app.py:183,291`) is a literal magic constant; ADR-005 explicitly claims the design avoids "manually injected magic numbers". The `*10.0` has no declared meaning. **Fix:** drop the constant or define and document the unit; derive `action_potential` from something with semantics, or drop the field until WP3 (its declared Riemannian decay purpose is unimplemented).

### M7 — Consolidation destroys the original and doesn't check existence
`consolidate_sovereignty` re-encodes the client-supplied `body.text` and overwrites the node's `vector_blob`/`text` (`traianus/app.py:298-304`). The originally ingested content and its vector are lost. Also, the `UPDATE` affects 0 rows for a missing `node_id` but still returns `SUCCESS`. **Fix:** treat the edit as a new revision (see H4), and check `cursor.rowcount == 1` or return `404`.

### M8 — No CI; Nix flake is not reproducible
No workflows in `.github/`, yet ADR-025 says invariant tests "must be validated … in every build pipeline". `flake.nix` tracks `nixos-unstable` **without a committed `flake.lock`**, so environments drift; `RESEARCH_PROGRAM.md` R-04 even promises a hash-pin that isn't there. **Fix:** commit `flake.lock`; add a GitHub Actions job that runs the suite (with model cached) on every push; pin model + torch.

---

## 🔵 Low

- **L1 — Tests don't test the real system.** Fixture seeds **orthonormal one-hot** axes (`tests/test_control_plane.py:82-88`) that production bootstrap never produces (measured off-diagonal cosine ≈ 0.23, not 0). Flagship consolidation test accepts `new_state in ["consolidated","incubating"]` (`:192`) — passes whatever happens. Tests import `main`, which loads the model and writes `traianus.db` to CWD at import time, and need network on first run. **Fix:** add an integration test with the real base (see Appendix A) asserting a non-degenerate consolidation rate; make unit tests hermetic by injecting a fake encoder.
- **L2 — Edge integrity.** `forge_relation` (`traianus/app.py:379`) creates edges between arbitrary strings without checking nodes exist (dangling edges), edges are mutable, and `/relations` handlers omit the WAL pragma used elsewhere. **Fix:** validate node existence; decide edge mutability per H4.
- **L3 — Mixed languages in public API.** `/ingesta`, `/nodos`, `/consolidar`, column `simbolo`, Spanish comments in `flake.nix` vs English elsewhere. **Fix:** pick one language for the API surface (English recommended for OSS) and alias the rest.
- **L4 — NSM basis is sloppy.** 64 entries with near-duplicate semantics (`"be above"`/`"above"`, `"be below"`/`"below"`); the greedy selector actually picked `BE_BELOW` as an axis in our run. Embedding multi-word phrases with a sentence encoder and calling those directions "quality dimensions" has no link to Gärdenfors. **Fix:** use a vetted NSM inventory, deduplicate, and justify (or drop) the "conceptual spaces" framing.
- **L5 — Decorative validation.** `RefinedEntity(... projections=list(...))` is constructed and validated but the code saves the raw dict JSON, not the validated list (`traianus/app.py:185-203`). The contract does almost nothing. **Fix:** save what you validate, or drop the intermediate model.
- **L6 — Dimensional brittleness.** Only the `dim_db > dim_in` case is padded (`traianus/app.py:162`); a provider that emits a different dimension — the whole "provider agnostic" selling point — falls through the `else` and breaks dot products. **Fix:** handle/validate both directions and explicitly reject dimension mismatches.

---

## ⚪ Informational — documentation calibration

- **I1** The docs run a mandatory renaming program (table "Fossil Purge", "Dosing Rule" in `PROJECT_IDENTITY.md`) that turns ordinary components into grandiose terms ("Model Agnosticism → Provider Agnosticism", "Visualize → Project/Observe/Inspect"). This reads as positioning, not engineering, and invites exactly the scrutiny that surfaced C1–H5.
- **I2** The ADR ledger announces skipped numbers ("006, 008, 009, 011–013 … internal exploration drafts") and an "immutable append-only decisions" philosophy, but the repo has 15 commits by a single author with all core+docs+tests in a single "Initial commit". The evolutionary frame is retrofitted.
- **I3** The docs contradict themselves: orthonormal basis (`CONTRACTS §2.1`, `b_i·b_j=δ_ij`) vs NSM embedding axes (`ADR-017`, measured non-orthogonal); "Zero Observation Mutagenicity" (`ADR-025.2`) vs "observation interactions generate vector mutations" (`ADR-024`).
- **I4** Gärdenfors "Conceptual Spaces" is cited as foundation, but the method (farthest-point greedy over sentence embeddings with MiniLM) has no connection to conceptual spaces quality dimensions.
- **I5** `ADR-007` justifies a single-character glyph via "length bias and asymmetric attention weights inside residual streams" — the glyph never enters any transformer. Fabricated justification.
- **I6** Performance/RAM claims (`<1ms`, `≤8GB`) appear repeatedly without any benchmark artifact. Add benchmarks or soften the language.

**Fix for all I:** one pass to make every claim match the code, move unbuilt mechanisms to a clearly labeled "Roadmap (not yet implemented)" section, and cut the vocabulary ~in half. This is the highest-impact change for external credibility.

---

## Remediation Roadmap

**Phase 0 — Fixes & Security (1–2 days)**
1. C1 — fix consolidation threshold; add regression test (Appendix A). *Without this the product does nothing.*
2. H1/H2/M5 — stop fabricating 200s; make ingress allowlist; return real errors.
3. H3 — drop wildcard CORS, bind to localhost, protect mutating routes with token.

**Phase 1 — Truth in Advertising (1–2 days)**
4. H4/H5/M1/M2/M3/I1–I6 — for each contradicted invariant, either **implement it** or **delete the claim**. Rewrite docs to the PoC. Add offline model prefetch + pins.
5. M4 — real package layout + documented quickstart `bootstrap → uvicorn → pytest`.

**Phase 2 — Engineering Hygiene (2–3 days)**
6. M8 — CI with cached model; commit `flake.lock`.
7. L1 — hermetic unit tests (inject fake encoder) + one integration test with real model.
8. M6/M7/L2/L5/L6 — metric/edge/dimension cleanups.

**Phase 3 — Truth Research (the interesting part)**
9. Implement `E_n`/`K_n` properly (WP2), a data-driven threshold (WP1), and — crucially — *validate* that the consolidation gate predicts something useful. That validation is what would turn this from a renamed embedding store into a research contribution.

---

## Appendix A — Reproduction and Regression Harness (the tool)

Save as `tools/audit_harness.py`. Requires real deps + one-time model download. Reproduces every measured number in this report and provides the C1 regression guard.

```python
# (This is the exact harness used for this audit; abbreviated to essentials.)
import os, sys, time, tempfile, sqlite3
import numpy as np
os.chdir(tempfile.mkdtemp()); sys.path.insert(0, "py")
import main, geodesic_bootstrap as gb
gb.model = main.model
gb.anchor_in_sqlite(gb.extract_pure_octagon())

mtx = main.get_geodetic_matrix_db()
vecs = [e["vector"] for e in mtx.values()]

# 1) basis orthogonality
M = np.stack(vecs); G = M @ M.T
off = G[~np.eye(len(M), dtype=bool)]
print("off-diagonal cosine mean/max:", round(off.mean(),4), round(off.max(),4), "(claim: 0)")

# 2) consolidation rate on real corpus  --> C1 REGRESSION GUARD
from fastapi.testclient import TestClient
client = TestClient(main.app)
corpus = [ ... 20 realistic notes ... ]
for t in corpus: client.post("/ingesta", json={"type":"text/plain","text":t})
nodes = client.get("/nodos").json()["nodes"]
consolidated = sum(
    client.post(f"/nodos/{n['id']}/consolidar",
                json={"text": n["text"], "ethical_key": True}).json()["new_state"] == "consolidated"
    for n in nodes)
rate = consolidated / len(nodes)
print(f"consolidation rate = {rate:.0%}")
assert 0.05 <= rate <= 0.95, f"CONSOLIDATION GATE DEGENERATE: {rate:.0%} (see audit C1)"
```

Measured baseline (before fix): orthogonality mean 0.227 / max 0.336; consolidation rate **0%** (assertion fails, as intended).

## Appendix B — Patch Order (smallest diffs first)

1. `traianus/app.py:134-143` — threshold fix (C1). ~2 lines.
2. `traianus/app.py:237` — allowlist (H2). ~2 lines.
3. `traianus/app.py:239-249` — drop fake 200 (H1). ~6 lines.
4. `traianus/app.py:12-18` — CORS + token dep (H3). ~15 lines.
5. `pyproject.toml` + move package (M4). ~30 min.
6. Docs pass (H4/H5/M1/M2/M3/I*) — delete-or-implement every claim.

---

*Prepared from commit `e2ab8bc`. All quantitative results reproducible with Appendix A against `all-MiniLM-L6-v2` (sentence-transformers 5.6.1, torch 2.13, numpy 2.5).*
