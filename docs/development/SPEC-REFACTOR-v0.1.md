# SPEC-REFACTOR-v0.2 — Substrate Realignment & Machine-Checkable Invariants (Integrated)

**Status:** Approved (v0.2)
**Scope:** `traianus/`, `tests/`, `tools/audit/audit_harness.py`, `docs/`
**Narrative superseded:** ADR-017, ADR-022, ADR-023, ADR-007 (see §1.4)

## Objective

Eliminate the divergence between the theoretical narrative and the executable code, fix immutable numeric contracts in SQLite, prune documentary bureaucracy ("selling smoke"), and formally supersede the miscalibrated ADRs.

---

## 1. Realignment Principles & Documentary Cleanup

### 1.1 Strict Domain Separation

The backend (`traianus/`) operates exclusively on:

- L2-normalized vectors v ∈ S^{d−1}
- Spectral signatures (projection spectra)
- `text/plain` payloads
- Deterministic state transitions

Domain concepts such as "idea", "diffuse thought", or "hyperfocus" are relegated to the application client (RefApp-01). The substrate does not legislate semantics.

### 1.2 Explicit Bootstrap Prosthesis

The current 8 axes extracted via farthest-point greedy over NSM phrases are formally defined as the **Epoch 0 Seed** (`PROSTHETIC_NSM_V1`). They are **not** absolute dimensions of semantic quality; they are a provisional, disposable geometric reference frame. Corpus-driven redimensionalization (WP1) is the destination of the system.

### 1.3 Liquidation of "Governance Theater" & Narrative Correction

- **Honest pitch.** Remove from README.md and documentation any pretense of "multimodal providers, sensors, DNA, or LiDAR". Honest positioning: **deterministic state engine over text embeddings (384D)**.
- **Ceremony cut.** Freeze cosmetic renaming programs (Visualize → Project, PKM → RefApp-01) and reduce AGENTS.md to the minimum executable technical content.
- **North-star sentence (README).** "The NSM basis is a provisional prosthesis; the destination is a basis derived from the data the substrate governs (WP1)."

### 1.4 Normative ADR Amendment (Superseding Amendment v0.1)

Embed an explicit amendment at the **top of the ADR ledger** (`docs/architecture/ADR/ADR.md`) — append-only, prevailing over history without erasing traceability.

#### Amendment — Superseding Amendment v0.1

**Status:** Approved (prevails over ADR-017, ADR-022, ADR-023, ADR-007)

1. **Substitution of ADR-017 (Geodesic Axes):** the 8 geodesic axes do not represent "quality dimensions of the human mind (Gärdenfors)". They are relabeled `PROSTHETIC_NSM_V1`: a provisional 384D bootstrap basis, disposable at WP1.
2. **Substitution of ADR-022 (Dual-Key Gate C1):** the Topological Key (σ²) is not an "infallible algorithmic judge"; it is defined as a **Provisional Informational Geometric Score**. **The dual gate is preserved in v0.1: consolidation requires the simultaneous satisfaction of the Topological Key (σ² ≥ θ_dyn) AND the Ethical Key (HITL). Neither acts alone.** The score is reported as `PROVISIONAL_INFORMATIONAL_SCORE` but remains a necessary condition alongside human approval.
3. **Substitution of ADR-023 (Local Adjacency E_n):** ε = 0.8 adjacency is declared a purely observational artifact for `/relations` (L2 distance). It does not govern runtime state transitions in v0.1.
4. **Annulment of ADR-007:** the theoretical justification about glyph processing inside transformers (ADR-007, mislabeled "ADR-I5" in the v0.1 draft) is dismissed — it does not correspond to the actual `text/plain` flow of the substrate.

---

## 2. Technical Decision Matrix & Remediation

| ID | Dimension | Audit Diagnosis | Architecture Decision | Direct Action |
|---|---|---|---|---|
| DOC-a | Docs | Excess ceremony (~1,700 doc lines + 25 ADRs for ~1,000 code lines) | Dismantle governance theater; amend ADRs | Embed Superseding Amendment v0.1; simplify README.md and AGENTS.md |
| DOC-b | Docs | Multimodal "Provider Agnosticism" promises (LiDAR/DNA) | Honest repitch | Redefine the substrate as a deterministic 384D text-embedding state engine |
| M-a | Math | `/mutate` silently alters the gate via UPDATE statements | Strict per-epoch geodesic immutability | Remove UPDATE on `geodesic_axes`; make mutations append-only |
| M-b/M-e | Math | Magic ε = 0.8 and mixed metrics (cosine vs L2) | Accept and document in v0.1 | E_n treated as purely observational for `/relations`; does not affect state decisions; decoupled from the consolidation transaction |
| M-c/M-d | Math | σ² has no declared direction or justification | Define the intent of the score | `variance` (single term in code and API) measures the deviation from uniform spectral energy. Keeps σ² ≥ θ_dyn **as a falsifiable working hypothesis** (rewarding non-flat signatures), pending WP0 validation. No new vocabulary. |
| M-f | Math | Non-orthogonal basis (cos ≈ 0.23) invalidates cross-epoch comparisons | Epoch-scoped determinism | Nodes evaluated under different epochs are not mutually comparable. Spectral signature and raw vector are preserved immutable. |
| A-a | Arch | Gate decision logic coupled to I/O and DB | Extract pure kernel (avoid scope trap) | Create pure function `evaluate_gate_v01` with no SQLite/FastAPI dependencies |
| A-b | Arch | "Provider agnosticism" is an abstraction without interface | Apply YAGNI (avoid scope trap) | Do not create abstract classes. Validate input contract (384D, L2, text/plain) at the HTTP endpoint |
| A-c | Security | Fire-and-forget ingestion exposed to duplicates from network retries | Ingress idempotency | Require/process `X-Idempotency-Key` on `/ingesta`; UNIQUE constraint in `ingestion_queue`; retry returns the same ingestion_id/node |
| A-e | Contract | `archived` state in enum with no transitions | Prune dead states | Remove `archived` from the DB schema, the Python `LifecycleState` Literal, and the Pydantic contracts |
| SEC-a | Security | Ingress trusts the string parser; no physical byte verification | Byte-level verification (Dual Boundary, minimal) | Raw `text/plain` body at `/ingesta`; null-byte scan; strict UTF-8; vector binary invariant (384D, float32, L2) before DB write; dry fail-closed rejection; append-only error logs |

---

## 3. Component Technical Specification

### 3.1 SQLite Persistence Schema (`traianus/app.py`, `bootstrap.py`)

- `geodesic_axes`: add `epoch_provenance TEXT NOT NULL DEFAULT 'PROSTHETIC_NSM_V1'` and `created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP`. The table MUST support multiple epochs (one immutable row set per `epoch_provenance`): `/mutate` inserts a complete new basis tagged `PROSTHETIC_NSM_V2` without UPDATE on existing rows (M-a, §3.3).
- `manifold_nodes`: add `epoch_provenance TEXT NOT NULL DEFAULT 'PROSTHETIC_NSM_V1'` — decisions (not only axes) are anchored to their base epoch.
- Lifecycle: `CHECK (state IN ('pending_approval', 'incubating', 'consolidated', 'telemetry_error'))`, mirrored in the `LifecycleState` Literal and the Pydantic contracts. `telemetry_error` is a legitimate persisted state: the spectral processor writes error revisions to `manifold_nodes` and `/telemetry` reads them. Excluding it from the CHECK would break the fail-loud ingestion path (H1) and the migration of existing `telemetry_error` rows.
- **Dual-source DDL discipline:** every schema change MUST be mirrored character-by-character in `tests/helpers/db_factory.py` (`SCHEMA_STATEMENTS`, L1). SQLite cannot add a CHECK via ALTER — apply it as a table-rebuild migration (`ALTER TABLE ... RENAME` → recreate → copy → drop), following the existing `seq` migration pattern in `init_relational_tables`.

### 3.2 Pure Decision Kernel (`traianus/core.py`)

```python
def evaluate_gate_v01(spectrum: list[float], ethical_key: bool, threshold: float) -> dict:
    """Evaluates the dual gate C1 for v0.1.

    The Topological Key acts as a provisional informational geometric score.
    The dual gate is preserved: consolidation requires BOTH keys simultaneously.
    """
    mean = sum(spectrum) / len(spectrum) if spectrum else 0.0
    variance = sum((x - mean) ** 2 for x in spectrum) / len(spectrum) if spectrum else 0.0

    topological_passed = variance >= threshold
    is_consolidated = topological_passed and ethical_key  # dual-key (AND)

    return {
        "state": "consolidated" if is_consolidated else "incubating",
        "topological_key": {
            "status": "PROVISIONAL_INFORMATIONAL_SCORE",
            "variance": variance,
            "threshold": threshold,
            "passed": topological_passed,
        },
        "ethical_key": ethical_key,
    }
```

### 3.3 HTTP API Endpoints

- **`/ingesta`:** require `Content-Type: text/plain` with a raw body (see §3.4); process `X-Idempotency-Key` (UNIQUE in `ingestion_queue`; retries return the same ingestion_id); validate input dimension v ∈ R^384.
- **`/consolidar`:** expose `PROVISIONAL_INFORMATIONAL_SCORE` inside the existing `dual_key_status` response namespace: `dual_key_status.topological_key` becomes `{status: "PROVISIONAL_INFORMATIONAL_SCORE", variance, threshold, passed}`; `dual_key_status.ethical_key` and `dual_key_status.consolidated` remain unchanged. Dual-key semantics (both keys required).
- **`/mutate`:** no UPDATE statements. The endpoint inserts a COMPLETE new axis basis — the current axes re-padded to the expanded dimension plus the new canonical axis — tagged with a fresh `epoch_provenance` (`PROSTHETIC_NSM_V2`). The `PROSTHETIC_NSM_V1` rows remain immutable (M-a). Nodes keep their original `epoch_provenance`; cross-epoch comparisons are prohibited (M-f). `persist_epsilon_edges` decoupled from the consolidation transaction (observational E_n, computed on read).

### 3.4 Ingress Byte-Level Verification (Dual Boundary, minimal)

Narrative wrapper stripped ("Triarii", "TridenGuard", "Harvard Architecture"); only the physical, low-level checks survive.

**Principle 1 — Physical byte verification at ingress.** The substrate must not trust the string parser. The raw body is read as bytes, scanned for `\x00`, and decoded with strict UTF-8 before any processing:

```python
raw_bytes = await request.body()
if b"\x00" in raw_bytes:
    raise HTTPException(status_code=400, detail="Invalid binary payload (null byte detected)")
try:
    text = raw_bytes.decode("utf-8", errors="strict")
except UnicodeDecodeError as e:
    raise HTTPException(status_code=400, detail="Invalid UTF-8 payload.") from e
```

**Contract change:** `/ingesta` accepts a raw `text/plain` body (`Content-Type: text/plain`) instead of the JSON `RawDump` wrapper. The MIME allowlist check (H2) moves from the JSON `type` field to the `Content-Type` header.

**Test-harness adaptation (BEFORE the DDL migrations):** there is no shared ingestion helper today — 5 live call sites repeat `client.post("/ingesta", json={"type": "text/plain", "text": ...}, headers=auth_headers)`: `tests/test_substrate.py`, `tests/test_e2e.py`, `tests/test_security.py` (×2), `tools/audit/audit_harness.py`. Create a single fixture in `tests/conftest.py` and migrate all of them to it:

```python
def ingesta(client, auth_headers, text: str):
    return client.post(
        "/ingesta",
        content=text.encode("utf-8"),
        headers={**auth_headers, "Content-Type": "text/plain"},
    )
```

Affected live surfaces (must all migrate): `tests/test_substrate.py` (ingesta call sites), `tests/test_e2e.py` (C1 guard, `@pytest.mark.model`), and `tools/audit_harness.py`. The legacy per-block call sites (~20, previously `tests/bloques/*`, `tests/genericos/*`, `tests/e2e/`, `tests/afirmaciones/`) were archived by the flat-suite restructure to `docs/exploring/legacy_docs/tests/` and are no longer part of the live suite.

**Principle 2 — Vector binary invariant at the encoding boundary.** The invariant is verified on the NATIVE encoder output (text/plain → vector), before normalization, padding, or serialization: dimension == 384, dtype float32 (native model output), finite values, non-zero norm. Storage keeps the current float64 serialization (`serialize_vector`) — a float32 check "before DB write" would be unverifiable after the float32→float64 cast. Dimension compliance at projection time is enforced against the active epoch basis (dim_in == dim_db; padding per L6). A vector failing any check is rejected before it reaches `manifold_nodes`.

**Principle 3 — Fail-closed posture with immutable logs.**
- Dry rejection: non-`text/plain` → 415; null/corrupt payload → 400; persistence failure → 503; missing/invalid token → 401. All with fixed, generic detail strings (no internal paths, no stack traces).
- No synthetic success. The Dual Boundary doc's Silent Denial (synthetic "Success") applies to the agent-proposal context; on the HTTP ingress surface it would re-introduce the fake-200 bug (H1).
- Errors and audit data persist in isolated append-only tables (telemetry_error revisions in `manifold_nodes` remain append-only).

**Architectural principle (not a low-level check) — Neurons Propose, Rules Dispose.** The client (RefApp-01 / LLM / operator) proposes states or queries; only the deterministic dual gate (Topological Key + Ethical Key, HITL) in the control plane authorizes state changes in the DB. This justifies the strict domain separation of §1.1 and the dual gate of §1.4.2.

---

## 4. Machine Verification Harness

Implemented in `tests/test_substrate.py` (live flat suite), against the real API with the repo fixtures:

```python
def test_claim_cl_prosthetic_basis_and_gate_status(client, auth_headers, isolate_db):
    # 1. All geodesic axes labeled as prosthesis
    for axis in db.get_geodesic_axes():
        assert axis["epoch_provenance"] == "PROSTHETIC_NSM_V1"

    # 2. Real consolidation (dual-key v0.1) exposes the provisional score
    node_id = seed_node_with_fake_encoder()  # existing node with a valid vector
    resp = client.post(
        f"/nodos/{node_id}/consolidar",
        headers=auth_headers,
        json={"text": "...", "ethical_key": True},
    )
    body = resp.json()
    assert resp.status_code == 200
    tk = body["dual_key_status"]["topological_key"]
    assert tk["status"] == "PROVISIONAL_INFORMATIONAL_SCORE"
    assert body["new_state"] == (
        "consolidated" if tk["passed"] and body["dual_key_status"]["ethical_key"]
        else "incubating"
    )
    assert body["dual_key_status"]["consolidated"] == (
        tk["passed"] and body["dual_key_status"]["ethical_key"]
    )
```

---

## 5. Sequential Execution Plan

**Step 1 — Documentary cleanup & ADR amendment (immediate)**

- README.md: honest positioning + north-star sentence: *"The NSM basis is a provisional prosthesis; the destination is a basis derived from the data the substrate governs (WP1)."*
- Register Superseding Amendment v0.1 at the top of the ADR ledger.

**Step 2 — Issue #0 (code and DB invariants)**

- DDL migration (`epoch_provenance` on axes and nodes; removal of `archived`).
- Extract `evaluate_gate_v01` in `traianus/core.py`.
- Append-only `/mutate`; idempotency in `/ingesta`.
- Ingress byte-level verification (raw `text/plain` body, null scan, strict UTF-8, vector binary invariant).
- Run the full pytest suite.

**Step 3 — Issue #1 (platform hygiene & CI)**

- Extend the existing `.github/workflows/ci.yml` (2 jobs: hermetic + real-model E2E with model cache).
- Pin explicit versions in `pyproject.toml`, including the sentence-transformers model `revision=` and torch pins (M1 bitwise determinism).

**Step 4 — WP0 experiment (empirical validation)**

- Create `tools/experiments/validate_c1_semantics.py` to measure the real validity of σ² over the Epoch 0 Seed on real data before approaching WP1.

---

## Appendix A — Corrections Applied to the Draft

- §1.4.2: dual-key semantics preserved (AND); removed the false claim that the Ethical Key holds sole authority.
- §1.4: the amendment lives in the ADR ledger only; no new `docs/ARCHITECTURE.md`.
- §2 M-c/M-d: `variance` as the single code/API term (no new vocabulary); falsifiable-hypothesis framing.
- §3.1: `epoch_provenance` added to `manifold_nodes` as well as to the axes.
- §3.3: E_n decoupled from the consolidation transaction (observational).
- §3.4 (SEC-a): ingress byte-level verification added — raw `text/plain` body (breaking contract change), null-byte scan, strict UTF-8, vector binary invariant (384D, float32, L2) before DB write, dry fail-closed rejection (no Silent Denial synthetic success on HTTP — would re-introduce H1), "Neurons Propose, Rules Dispose" kept as the architectural authority principle, not a low-level check. Test-harness adaptation: new `ingesta()` fixture in `tests/conftest.py` (helper does not exist today), MIME allowlist moves to the `Content-Type` header, ~20 call sites + `tools/audit/audit_harness.py` migrate.
- §4: the verification test exercises the real API (path, auth, existing node, fixtures).

---

## Appendix B — Revision Annex (v0.2 justification)

The v0.1 → v0.2 bump consolidates the eight principal-architect review findings. Each row records the v0.1 defect and its resolution applied in this version.

| # | Finding (v0.1 defect) | Resolution in v0.2 |
|---|---|---|
| 1 | §3.1 `CHECK (state IN ('pending_approval','incubating','consolidated'))` omits `telemetry_error`, which the spectral processor persists in `manifold_nodes` (`async_spectral_processor`) and `/telemetry` reads. Enforcing the v0.1 CHECK would break the fail-loud H1 path and the migration of existing `telemetry_error` rows. | CHECK now includes `telemetry_error`; dual-source DDL discipline added (`tests/helpers/db_factory.py` mirror, table-rebuild migration for SQLite CHECK). |
| 2 | M-a required an "append-only /mutate" but §3.1 specified no mechanism: no `seq`, no revision log, no epoch identity on `geodesic_axes`. The action was unimplementable as written. | `/mutate` redesigned as **epoch-append**: inserts a complete new basis tagged `PROSTHETIC_NSM_V2`; no UPDATE on existing rows; cross-epoch comparison prohibited (M-f). |
| 3 | §3.4 P2 demanded a float32/384D/L2 invariant "before DB write", unverifiable because `serialize_vector` casts to float64 and `/mutate` expands dimensions. | Invariant moved to the **encoding boundary** (native float32 encoder output), before normalization/padding/serialization; dimension compliance enforced against the active epoch at projection time. |
| 4 | "~20 ingesta call sites" is factually wrong: the live suite has 5 (`test_substrate`×1, `test_e2e`×1, `test_security`×2, `tools/audit_harness.py`×1). The ~20 live in archived `docs/exploring/legacy_docs/tests/`. | §3.4 fixture-migration scope corrected to the 5 live call sites. |
| 5 | "ADR-I5" does not exist in the ADR ledger; the glyph justification is **ADR-007**. | §1.4 supersedes ADR-007 and notes the v0.1 mislabel. |
| 6 | §4 asserted `body["topological_key"]` / `body["state"]`, but `/consolidar` returns `body["dual_key_status"]` / `body["new_state"]`. | §4 aligned to the existing `dual_key_status` namespace; score embedded as `dual_key_status.topological_key.{status, variance, threshold, passed}`. |
| 7 | §3.1 did not mention the test-side DDL mirror or the SQLite table-rebuild mechanics required by a CHECK addition. | Both added (§3.1); `tests/helpers/db_factory.py` must mirror `traianus/app.py` character-for-character (L1). |
| 8 | Step 3 said "Configure CI" when `.github/workflows/ci.yml` already exists; and no model `revision=` pin for M1. | Step 3 reworded to "extend the existing CI"; pinning now includes the sentence-transformers `revision=` and torch pins. |
