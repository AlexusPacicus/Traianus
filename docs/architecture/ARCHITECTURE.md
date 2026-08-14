# System Architectural Formulation

## 1. Header & Scope
Purpose: This document specifies the discrete state machine, algebraic governance, variance thresholding, and transactional persistence model of **Traianus**.
Domain: Spatial state transitions ($S_n \to S_{n+1}$), $L_2$ orthogonal projection, dynamic variance circuit breaking, and SQLite WAL append-only persistence.

**Live Document Delegations:**
* For constitutional boundaries and Non-Goals, see [../PROJECT_IDENTITY.md](../PROJECT_IDENTITY.md).
* For empirical falsification records and NCD findings, see [../specifications/EAS-01_LOGOGRAPHIC_PHYSICS.md](../specifications/EAS-01_LOGOGRAPHIC_PHYSICS.md) and [../LEDGER.md](../LEDGER.md).
* For architectural decision records, see [./ADR/ADR.md](./ADR/ADR.md).
* For Pydantic data schemas and Zero-Trust validation, see [./contracts/CONTRACTS.md](./contracts/CONTRACTS.md).

---

## 2. Architectural Invariants

* **Representation Invariance:** Traianus never modifies input vector coordinates emitted by external providers. The control plane exclusively governs lifecycle states, spatial adjacencies, and historical sequences.
* **Invariante Append-Only (`PRIMARY KEY (id, seq)`):** State mutations are written strictly as incremental append-only events. Operating `UPDATE` or `DELETE` queries on historical records is forbidden.
* **Invariante C1 (Self-Projection Exclusion):** Dynamic variance calibration ($\theta_{\text{dyn}}$) explicitly excludes diagonal auto-projections ($i \neq j$) to prevent threshold inflation caused by trivial self-similarity.
* **Observation Isolation:** Read-only projections $O_n = P_\theta(S_n)$ operate over state $S_n$. The substrate contains zero 2D/3D rendering code or layout logic.

---

## 3. Mathematical Formulation of System State ($S_n$)

Traianus operates as a discrete, deterministic state machine. At ordinal sequence step $n$ ($n \in \mathbb{N}$), the active spatial state is defined as:

$$S_n = (V_n, E_n)$$

Where:
* $V_n \subset \mathbb{R}^d$: Finite set of $L_2$-normalized coordinate vectors (vertices).
* $E_n \subseteq V_n \times V_n$: Deterministic adjacency edges formed strictly where $d(\mathbf{v}_i, \mathbf{v}_j) \le \epsilon$.
* *(Higher-order simplicial complexes $K_n$ are roadmap I+D scope under WP2).*

The active geodetic basis $\mathbf{B}_n \in \mathbb{R}^{d \times k}$ is maintained by the Spatial Control Plane to calculate projections without mutating $S_n$.

### 3.1 Deterministic State Transition
Given an incoming payload $e_n$ containing a coordinate vector $\mathbf{v} \in \mathbb{R}^d$, the state transition follows:

$$S_{n+1} = f(S_n, e_n)$$

Given identical initial state $S_0$, identical input vectors and identical execution semantics, $f$ yields the same state $S_{k+1}$. Sequence ordinal $n$ is completely decoupled from wall-clock time.

---

## 4. Subsystem & Data Flow

```text
+--------------------------------------------------------------------+
| 1. External Representation Layer (Encoders / Sensors)               |
| Emits coordinate vectors v in R^d                                   |
+------------------------------------------+-------------------------+
                                           |
                                           v Payload Ingestion
+--------------------------------------------------------------------+
| 2. Zero-Trust Ingress Customs Gate (traianus/security/validator.py)|
| Validates UTF-8, null-byte absence, and Pydantic v2 schemas        |
+------------------------------------------+-------------------------+
                                           |
                                           v Clean Vector v in R^d
+--------------------------------------------------------------------+
| 3. Geometry & Governance (traianus/geometry/ + traianus/governance/) |
| |-- Observables: K_cin, ortho distance, E_n (purely observational)   |
| |-- Gate C1 Dual-Key: σ² ≥ θ_dyn ∧ EthicalKey (governance/gate.py)   |
+------------------------------------------+-------------------------+
                                           |
                                           v Atomic State Transition
+--------------------------------------------------------------------+
| 4. Transactional Persistence Substrate (traianus/storage.py)       |
| Append-only SQLite WAL storage with composite PK (id, seq)         |
+--------------------------------------------------------------------+
```

---

## 5. Persistence Schema (`manifold_nodes`)

The canonical relational table in `traianus/storage.py` maintaining entity state persistence:

```sql
CREATE TABLE IF NOT EXISTS manifold_nodes (
    id TEXT NOT NULL,
    seq INTEGER NOT NULL,
    state TEXT CHECK(state IN ('pending_approval', 'incubating', 'consolidated', 'telemetry_error')),
    vector BLOB NOT NULL,
    projection_var REAL NOT NULL,
    PRIMARY KEY (id, seq)
);
```

| Field | Type | Purpose |
| :--- | :--- | :--- |
| `id` | TEXT | Entity identifier (`NODE_{ingestion_id}`). |
| `seq` | INTEGER | Monotonically increasing revision sequence per `id` (current state = `MAX(seq)`). |
| `state` | TEXT | Lifecycle enum: `pending_approval`, `incubating`, `consolidated`, or `telemetry_error`. |
| `vector` | BLOB | Binary float array storing $L_2$-normalized vector $\mathbf{v} \in \mathbb{R}^d$. |
| `projection_var` | REAL | Calculated spectral projection variance $\sigma^2$. |

---

## 6. Execution Determinism & Boundaries

| Core Claim | Execution Mechanism | Boundary |
| :--- | :--- | :--- |
| Deterministic Transition | Pure operators in `traianus/geometry/observables.py` and gate C1 in `traianus/governance/gate.py`. | Zero stochastic token completion in the control plane. |
| Append-Only Integrity | SQLite composite primary key `(id, seq)`. | Operations `UPDATE` and `DELETE` are forbidden. |
| Hermetic Execution | Local SQLite WAL transactions. | Operates fully offline with zero cloud runtime network dependencies. |
