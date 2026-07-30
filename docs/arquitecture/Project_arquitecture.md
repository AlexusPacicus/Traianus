# System Architectural Formulation
## 1. Header & Scope
Purpose: This document specifies the discrete state machine, governance layers, dual-key consolidation mechanics, and transactional persistence model of the Deterministic Computational Substrate for Autonomous Spatial State Governance.
Domain: Spatial state transitions ($S_n \to S_{n+1}$), $L_2$ orthogonal projection, dynamic variance circuit breaking, and transactional persistence.
Explicit Delegations:
For system identity, non-goals, and boundary taxonomy, see ../identity/PROJECT_IDENTITY.md.
For scientific foundations and theoretical grounding, see ../research/RESEARCH_HYPOTHESIS.md.
For engineering decision records, see ../ADR/ADR.md.
For Pydantic data contracts and Zero Trust ingress rules, see ../contracts/CONTRACTS_AND_PRISMS.md.

## 2. Invariants

* **Representation Invariance Principle:** Traianus never modifies the latent space coordinates emitted by external representation methods. The control plane exclusively governs entity state, spatial topology, and lifecycle transitions within the substrate.

* **Observation Invariant:** External observation layers evaluate read-only perspective projections $O_n = P_\theta(S_n)$ over the state $S_n$. The substrate governs state $S_n$ autonomously and continuously, independently of whether or how the state is observed. The core substrate contains zero visualization logic and computes no 2D/3D render coordinates.

### 2.1 Dual-Key Consolidation Invariant
Transitioning an entity state to `'consolidated'` requires two concurrent validations (ADR-022):

* **Topological Key (Algebraic):** Spatial variance. Projection mass variance must satisfy the dynamic threshold: $\sigma^2 \geq \sigma^2_{\text{dynamic}}$.
* **Ethical Key (HITL):** Human validation. Explicit operator intervention: `revision_milestone = 1`.

If an entity satisfies only one key, the substrate retains it in quarantine (`lifecycle_state = 'incubating'`), preventing both unvalidated mathematical drift and operator mutation.

## 3. Mechanism & Specification

### 3.1 Mathematical Formulation of System State ($S_n$)
Traianus executes as a discrete, deterministic state machine. Following ADR-023, the computational state at ordinal sequence step $n$ ($n \in \mathbb{N}$) is defined as a finite simplicial complex:
$S_n = (V_n, E_n, K_n)$
Where:
$V_n \subset \mathbb{R}^d$ — Finite set of $L_2$-normalized coordinate vectors (vertices).
$E_n \subseteq V_n \times V_n$ — Deterministic adjacency edges formed strictly where $d(\mathbf{v}_i, \mathbf{v}_j) \leq \epsilon$.
$K_n$ — Higher-order simplicial faces formed by sets of mutually adjacent vertices.
The active spatial basis matrix $B_n \in \mathbb{R}^{d \times k}$ is maintained in parallel by the Spatial Control Plane to calculate read-only projections $O_n = P_\theta(S_n)$ without mutating $S_n$.

### 3.2 Deterministic Transition Function
Given a sequence input $e_n$ (containing a coordinate vector $v \in \mathbb{R}^d$ emitted by an external representation provider), the state transition follows:
$S_{n+1} = f(S_n, e_n)$
Given an identical initial state $S_0$ and sequence $E = \{e_0, e_1, \dots, e_k\}$, f yields exactly the same state $S_{k+1}$ without stochastic variation. The index n represents the discrete transition ordinal, completely decoupled from wall-clock time (ADR-020).

### 3.3 Control Plane Subsystems & Topology Flow

```text
┌──────────────────────────────────────────────────────────────────────────────────┐
│ 3. Observation Layer (Ulpia Native Mathematical Observation / RefApps) │
│ Evaluates perspective projections On = Pθ(Sn) & feeds back HITL validations │
└────────────────────────────────────────┬─────────────────────────────────────────┘
 │
 ▼ (External Input Payload / Action)
┌──────────────────────────────────────────────────────────────────────────────────┐
│ Ingress Customs Gate (DUA) │
│ Synchronous Zero-Trust firewall validating payload integrity prior to ingestion. │
└────────────────────────────────────────┬─────────────────────────────────────────┘
 │
 ▼ (Coordinates v ∈ ℝᵈ from External Provider)
┌──────────────────────────────────────────────────────────────────────────────────┐
│ 2. Spatial Control Plane (Traianus Substrate) │
│ ├── Spectral Variance Circuit Breaker (L₂ projection & dynamic thresholding) │
│ └── Orthogonalization & Basis Engine (Dynamic axis extraction & accretion) │
└────────────────────────────────────────┬─────────────────────────────────────────┘
 │
 ▼ (State Transition Sn → Sn+1)
┌──────────────────────────────────────────────────────────────────────────────────┐
│ Local Transactional Persistence Substrate │
│ Transactional logging, state serialization, and immutable delta storage. │
└──────────────────────────────────────────────────────────────────────────────────┘
```
* **Ingress Customs Gate (DUA):** Synchronous integrity firewall filtering non-conforming payloads prior to coordinate processing.

* **Spectral Variance Circuit Breaker:**
  * Computes $L_2$-normalized orthogonal scalar projections onto active basis axes $B_n$.
  * Evaluates mass variance $\sigma^2$ against the critical dynamic threshold $\sigma^2_{\text{dynamic}}$ (ADR-017).
  * Routing Execution Logic:
    * $\sigma^2 \geq \sigma^2_{\text{dynamic}}$ AND revision_milestone = 1 ⟹ Transition to `'consolidated'`.
    * $\sigma^2 < \sigma^2_{\text{dynamic}}$ ⟹ Transition to `'incubating'` while preserving full multichannel projection spectrum in `projections_json`.

* **Orthogonalization & Calibration Subsystem:** Dynamic axis calculation and space accretion (N→N+1) via greedy farthest-point projection (ADR-017).

## 4. Persistence Substrate Schema (manifold_nodes)
The canonical relational table maintaining entity state persistence within the transactional log:
```sql
CREATE TABLE IF NOT EXISTS manifold_nodes (
 id TEXT PRIMARY KEY,
 text TEXT NOT NULL,
 toon_factor TEXT NOT NULL,
 lifecycle_state TEXT NOT NULL,
 action_potential REAL NOT NULL,
 revision_milestone INTEGER NOT NULL,
 vector_blob BLOB NOT NULL,
 projections_json TEXT NOT NULL,
  sys_internal_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);
```
| Field | Logical Type | Technical Purpose |
| :--- | :--- | :--- |
| `id` | Unique Identifier | Deterministic primary key (`NODE_{ingestion_id}`). |
| `text` | Plain Text / Payload | Structured entity payload content (`RawDump` / `RefinedEntity`). |
| `toon_factor` | Single Character | Orthogonal Unicode symbol assigned via projection (`len == 1`). |
| `lifecycle_state` | State Enum | Lifecycle attribute: `'pending_approval'`, `'consolidated'`, `'incubating'`, `'telemetry_error'`, or `'archived'`. |
| `action_potential` | Continuous Scalar | Action potential for decay via Riemannian metric density (ADR-020). |
| `revision_milestone` | Boolean / Integer | Ethical Key validation marker for human-in-the-loop intervention (HITL). |
| `vector_blob` | Dense Binary Array | Dense float64 BLOB storage of normalized vector $v \in \mathbb{R}^d$. |
| `projections_json` | Multichannel Structure | Log of multi-axis projection spectrum onto active basis $B_n$. |
| `sys_internal_timestamp` | Substrate Index | Low-level transaction index and local delta synchronization marker. |

## 5. Boundaries & Failure Modes

| ID | Failure Mode | Root Mechanism | Mitigation & Boundary |
| :---: | :--- | :--- | :--- |
| **F-01** | High-dimensional distance concentration ($d \gg k$). | Relative variance loss due to the curse of dimensionality in raw vector space. | Variance evaluation executed over reduced projection space $k$, isolating scale from $d$, followed by periodic subspace re-projection (WP1/WP2). |
| **F-02** | Transaction queue saturation. | Input burst exceeding local storage I/O throughput. | Load shedding at Ingress Customs Gate (DUA) upon reaching maximum capacity buffer limits. |
| **F-03** | Angular collapse of spatial basis. | Axis drift during asynchronous basis update calculations. | Automatic rollback to prior basis state $B_{n-1}$ if total projection variance drops below $\sigma^2_{\min}$. |

## 6. Architectural Execution Guarantees

| Core Claim | Execution Mechanism | Boundary |
| :--- | :--- | :--- |
| **Deterministic State Transition** | State function $S_{n+1} = f(S_n, e_n)$ executed via deterministic linear algebra operations. | Deterministic; zero stochastic token sampling or LLM completion in the control plane. |
| **Persistence Isolation** | Write operations routed via transactional write-ahead logging and atomic state queues. | Single-node local concurrency isolation; no distributed consensus required at core level. |
| **Multichannel Spectrum Integrity** | Full projection spectrum logged in `projections_json` without lossy compression. | Preserves directional projections; does not assign semantic labels to raw geometric projections. |
