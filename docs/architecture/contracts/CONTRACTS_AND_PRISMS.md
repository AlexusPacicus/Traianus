# Data Contracts, Pydantic Schemas, and Geometric Ingress Customs

> **Specification of Ingress Firewalls, Pydantic Data Contracts, and Zero Trust Validation Rules.**

---

## 1. Purpose and Zero Trust Ingress Principle

This document specifies the data contracts and validation boundaries governing Traianus' ingress perimeter and internal control plane.

* **Provider Agnosticism (RH-1):** The ingress layer receives coordinate vectors $\mathbf{v} \in \mathbb{R}^d$ emitted by external representation providers (e.g., neural embeddings, sparse lexical encoders, symbolic ontologies, or physical sensors) without modifying or relying on provider-internal parameters.
* **Deterministic Execution Boundaries:** The control plane strictly governs the intrinsic spatial state continuity of the substrate ($S_n = (V_n, E_n, K_n)$). It executes zero probabilistic token completion, text generation, or payload parsing. State transitions and spatial routing are driven purely by $L_2$-normalized orthogonal projections and dynamic variance thresholding.
* **Two-Tier Ingress Validation:** External HTTP ingress validates raw text payloads (`RawDump`) at the perimeter endpoint. Internal state updates satisfy the refined entity contract (`RefinedEntity`) prior to persistent storage.

---

## 2. Geodetic Baseline and L2 Bias Elimination

### 2.1 Canonical Bootstrap Basis ($\mathbf{B}_0 \in \mathbb{R}^{d \times k}$)
To initialize the spatial control plane without domain or semantic bias, Traianus initializes the active spatial basis $\mathbf{B}_0$ via farthest-point greedy selection over embeddings of 64 NSM primitives produced by MiniLM (all-MiniLM-L6-v2). The resulting basis is **not orthogonal**; it is a set of $k$ $L_2$-normalized vectors derived from semantic primitives:

$$\mathbf{B}_0 = [\hat{\mathbf{b}}_1, \hat{\mathbf{b}}_2, \dots, \hat{\mathbf{b}}_k] \in \mathbb{R}^{d \times k}, \quad \text{where } \hat{\mathbf{b}}_i \cdot \hat{\mathbf{b}}_j \neq \delta_{ij} \text{ for } i \neq j$$

Empirically observed off-diagonal cosine similarities: mean ≈ 0.23, max ≈ 0.34. The basis vectors serve as neutral geometric reference directions for evaluating projection variance. The substrate assigns zero semantic tags, labels, or domain categorizations to the basis axes.

### 2.2 Mathematical Mitigation of Frequency and Volume Bias
* **Proposed Mechanism:** Aims to mitigate frequency bias, magnitude distortion, and scale discrepancies originating from external representation models or physical sensors.
* **Mathematical Execution:** $L_2$-normalization of both the input coordinate vector $\mathbf{v}$ and active basis vectors $\mathbf{B}_n$ prior to scalar projection evaluation on the unit hypersphere $S^{d-1}$:
  $$p_i = \hat{\mathbf{v}} \cdot \hat{\mathbf{b}}_i = \frac{\mathbf{v} \cdot \mathbf{b}_i}{\Vert{}\mathbf{v}\Vert{}_2 \Vert{}\mathbf{b}_i\Vert{}_2}$$
  This isolates purely angular directional relationships ($\theta$), completely neutralizing vector magnitude ($\Vert{}\mathbf{v}\Vert{}_2$).
* **Spectrum Retention (ADR-014):** The full scalar projection vector $\mathbf{p} = [p_1, p_2, \dots, p_k]^\top$ is persisted within the state log (`projections_json`) without lossy scalar compression or category assignment.

---

## 3. Pydantic Contract Specifications

The validation architecture enforces a separation between external API ingress and internal state refinement.

### 3.1 External Ingress Contract (`RawDump`)
Exposed at the `/ingesta` perimeter endpoint. Filters structural noise and non-text payloads before invoking external vector representation.

```python
from pydantic import BaseModel, Field

class RawDump(BaseModel):
    text: str = Field(
        ..., 
        description="Raw external entity payload content in plain text."
    )
    type: str = Field(
        default="text/plain", 
        description="MIME payload type. Non-plain text payloads are rejected at perimeter."
    )
```

### 3.2 Internal Control Plane Refinement Contract (RefinedEntity)
Constructed internally by the control plane after coordinate projection and circuit breaker evaluation. Enforces Ethical Key tracking (HITL) and structural completeness prior to state persistence.
```python
from pydantic import BaseModel, Field
from typing import List

class RefinedEntity(BaseModel):
    text: str = Field(
        ..., 
        description="Structured entity payload content in plain text."
    )
    lifecycle_state: str = Field(
        ..., 
        description="State attribute: 'pending_approval', 'consolidated', 'incubating', or 'telemetry_error'."
    )
    revision_milestone: bool = Field(
        default=False, 
        description="TRUE only when validated by explicit external/human interaction (Ethical Key)."
    )
    projections: List[float] = Field(
        ..., 
        description="Full multi-axis projection spectrum array p = [p_1, ..., p_k]."
    )
```

## 4. Validation Trident (Defense-in-Depth)
```text
[External Payload / HTTP Ingress]
       │
       ▼ (Layer 1: External Ingress Gate - RawDump)
┌──────────────────────────────────────────┐
│ Structural & Content-Type Filter         │ ──► Synchronous rejection if type != text/plain.
└──────────────┬───────────────────────────┘
               │
               ▼ (Layer 2: Vector Projection & Circuit Breaker)
┌──────────────────────────────────────────┐
│ L₂ Cosine Similarity + Spectral Variance │ ──► Computes projection array p ∈ ℝᵏ & variance σ².
└──────────────┬───────────────────────────┘
               │
               ▼ (Layer 3: Internal State Contract - RefinedEntity & Silent Denial)
┌──────────────────────────────────────────┐
│ Pydantic Validation & Telemetry          │ ──► Internal error logging / ADR-002 enforcement.
└──────────────┴───────────────────────────┘
```

### 4.1 Silent Denial and Internal Telemetry (ADR-002)

* **External Behavior:** Upon validation failure or non-conforming structural drift, the system suppresses technical stack traces toward external callers to prevent interface lockups and information leakage.

* **Telemetry Persistence:** The failure is logged atomically in the local database as an internal system telemetry node under `lifecycle_state = 'telemetry_error'`, granting the operator local observability over pipeline faults (ADR-002).

## 5. Contract Execution Guarantees

| Contract Rule | Claim | Mechanism | Boundary |
| :--- | :--- | :--- | :--- |
| **Ingress Type Isolation** | Filters non-text at perimeter. | `RawDump` validates `type == 'text/plain'` at perimeter endpoint. | Filters MIME headers; deep payload processing executes downstream. |
| **Multichannel Integrity** | Preserves 100% of directional projection spectrum. | Stores complete float array $p \in \mathbb{R}^k$ in `RefinedEntity.projections`. | Avoids lossy scalar compression or category assignment. |
| **Silent Denial (ADR-002)** | Prevents external technical information leaks. | Suppresses HTTP tracebacks, persisting internal system node under `'telemetry_error'`. | Hides stack traces from external callers; requires local log inspection for forensics. |
