# Project Identity & Technical Scope

## 1. Scope & Purpose
This document establishes the constitutional boundaries, operational invariants, taxonomy, and explicit Non-Goals governing **Traianus**.

**Live Document Delegations:**
* For state machine mathematics, SQLite schema, and persistence contracts, see [docs/architecture/ARCHITECTURE.md](./architecture/ARCHITECTURE.md).
* For empirical validation, spectral findings, and NCD coupling, see [docs/specifications/EAS-01_LOGOGRAPHIC_PHYSICS.md](./specifications/EAS-01_LOGOGRAPHIC_PHYSICS.md) and [docs/LEDGER.md](./LEDGER.md).
* For architecture decision history, see [docs/architecture/ADR/ADR.md](./architecture/ADR/ADR.md).

---

## 2. Canonical Definition
**Traianus** is an open-source, offline-first, deterministic **Spatial Control Plane and Immutable State Engine** for vector coordinate systems in $\mathbb{R}^d$.

It operates as an independent execution layer above external representation providers (e.g., neural embeddings or physical sensor telemetry), decoupling representation generation from spatial lifecycle governance, dynamic variance thresholding, and transactional persistence.

---

## 3. Ontological Postulate: Decoupling Representation from Governance
Traianus does not construct or modify external representations of reality. It preserves state continuity for externally generated coordinate vectors within a deterministic spatial control plane.

* **Content & Domain Agnosticism:** Core algebraic operations operate strictly on $L_2$-normalized coordinate vectors $\mathbf{v} \in \mathbb{R}^d$, regardless of whether they represent natural language embeddings or continuous physical telemetry.
* **Separation of Concerns:** Representation generation (encoders/sensors) exists outside Traianus. State governance, temporal sequencing (`seq`), and persistence exist strictly inside Traianus.

---

## 4. Core System Invariants

* **Invariante Append-Only (`(id, seq)`):**
  State updates and coordinate changes are persisted exclusively as incremental append-only events in SQLite WAL (`PRIMARY KEY (id, seq)`). Operating `UPDATE` or `DELETE` queries on historical records is strictly prohibited.

* **Invariante C1 (Self-Projection Exclusion):**
  Dynamic variance thresholding ($\theta_{\text{dyn}}$) explicitly excludes diagonal auto-projections ($i \neq j$) to prevent synthetic threshold inflation caused by trivial self-similarity.

* **Cold-Start to Corpus Base Transition (ADR-017):**
  At initialization ($t=0$), the system utilizes a fixed 8D octagonal bootstrap basis ($\mathbf{B}_0$) as a temporary scaffold. As vector density grows, emerging corpus axes progressively replace the synthetic seed without violating historical sequence continuity.

* **Modality Specialization (EAS-01 Finding):**
  Spectral projection variance ($\sigma^2$) governs continuous coordinate signals and physical telemetry. Local natural language text similarity is governed via Normalized Compression Distance (NCD) coupling.

---

## 5. Boundaries & Non-Goals

### 5.1 What Traianus Is NOT
* **Not a Large Language Model (LLM):** Performs zero probabilistic text completion, token generation, or prompt processing.
* **Not a Standard Vector Database:** Does not perform static top-k nearest-neighbor retrieval; operates as an active spatial state controller.
* **Not a Graph Database:** Avoids manual triple extraction (subject-predicate-object) or rigid external schemas.
* **Not an Execution Agent Framework:** Executes zero autonomous external tools, network API calls, or unmonitored background tasks.
* **Not a User Interface Framework:** Contains zero UI, rendering, or layout code. External application or inspection layers operate strictly as clients over standard APIs.

### 5.2 Operational Boundaries
* **Zero Cloud Runtime Dependencies:** Executes fully offline on local edge hardware ($\le 8\text{ GB}$ RAM) with zero network connectivity required.
* **Deterministic Reproducibility:** Given identical vector sequences, initial state, and execution semantics, the core state transition is deterministic (no bitwise reproducibility claim across hardware revisions).