# 🔬 Research Programme: Spatial State Governance & R&D Roadmap

> **Engineering Specifications for the Deterministic Computational Substrate.**

This research programme specifies the R&D roadmap, work packages, and multi-provider benchmarks for Traianus' spatial control plane.

---

## 1. Work Package Specifications

### Work Package 1 (WP1): Dynamic Basis Extraction & Adaptive Spatial Core

* **Research Objective:** Investigate whether the geometric substrate can adapt its basis vectors dynamically to the input corpus without distorting historical spatial relationships or requiring model retraining.
* **Proposed Mechanism:** Background worker process running spectral decomposition over incoming coordinates, applying iterative min-max greedy farthest-point calculations before updating active axes in `traianus.core.basis` (ADR-017).
* **Execution Boundary:** Axis updates execute asynchronously outside the main control plane execution thread ($<1\text{ms}$ latency target). Axis updates abort if corpus variance falls below the critical threshold ($\sigma^2 < \sigma^2_{\min}$), reverting to the prior basis state $\mathbf{B}_{n-1}$.

---

### Work Package 2 (WP2): Persistent Topology & Dimension Discovery

* **Research Objective:** Evaluate whether local space expansion ($N \to N+1$) can be computed directly from point-cloud topology, removing reliance on arbitrary dimensional hyperparameters.
* **Proposed Mechanism:** Computation of $H_1$ persistent homology lifespans over local vector neighborhoods using compiled `GUDHI` C++ bindings integrated into `traianus.tda` (ADR-018, ADR-019).
* **Execution Boundary:** Computes topological density and persistent lifespans exclusively without assigning domain labels to newly generated unit vectors. Filtration computation is capped within a maximum neighborhood radius ($\epsilon_{\max}$) to prevent $O(N^3)$ scaling.

---

### Work Package 3 (WP3): Clock-Independent Metrics

* **Research Objective:** Explore whether entity state decay, quarantine retention, and relational obsolescence can be decoupled from wall-clock time and system clock manipulation.
* **Proposed Mechanism:** Calculation of local Riemannian metric tensors $g_{ij}(x)$ and $k$-NN vector density integrals in `traianus.metrics` to govern `action_potential` decay within `manifold_nodes` (ADR-020).
* **Execution Boundary:** Applies solely to autonomous substrate state decay and archival; it does not override explicit human-in-the-loop state management (Ethical Key / HITL).

---

### Work Package 4 (WP4): Local-First State Replication & Synchronization

* **Research Objective:** Propose a mechanism for independent local substrate nodes to synchronize geometric states bidirectionally without requiring a central server or altering local routing invariants.
* **Proposed Mechanism:** Client-side delta synchronization (SQLite-to-IndexedDB) using state-based CRDT logs over `manifold_nodes` (`traianus.replication`).
* **Execution Boundary:** Does not resolve Byzantine consensus across untrusted public networks. Synchronization is restricted to peer-to-peer user instances and explicitly authorized federated pairs.

---

## 2. Technical Risk & Mitigation Matrix

| Risk ID | Risk Event | Failure Mechanism | Mitigation & Boundary |
| :---: | :--- | :--- | :--- |
| **R-01** | Topological filtration stalls control plane. | $O(N^3)$ complexity on large point clouds during $H_1$ persistence computation. | Cap filtration radius $\epsilon_{\max}$ and offload calculation to background threads. |
| **R-02** | Basis drift causes spatial collapse. | Angular collapse during dynamic greedy farthest-point recalculation. | Roll back to previous basis state $\mathbf{B}_{n-1}$ if total variance drops below $\sigma^2_{\min}$. |
| **R-03** | Synchronization state divergence. | Out-of-order delta execution during offline multi-device sync. | Append-only delta logs with state-based CRDT resolution in transactional storage log. |
| **R-04** | Build non-reproducibility. | Unpinned native C++ compilation dependencies (`GUDHI` / `glibc`). | Enforce hash pinning of C++ libraries within declarative `flake.nix`. |

---

## 3. Deliverables & Verification Matrix

| Milestone | Module / Component | Verification Mechanism |
| :--- | :--- | :--- |
| **M1 (WP1)** | `traianus.core.basis` | Automated test verifying orthogonal basis substitution without mutating existing node coordinates. |
| **M2 (WP2)** | `traianus.tda` | CLI diagnostic generating deterministic $H_1$ persistence diagrams from synthetic point clouds. |
| **M3 (WP3)** | `traianus.metrics` | Test suite verifying state stability across simulated system clock shifts ($\pm 10$ years). |
| **M4 (WP4)** | `traianus.replication` | End-to-end integration test verifying multi-device offline delta merge via transactional state logs. |

---

## 4. Multi-Provider Benchmarking Matrix

* **Purpose:** Evaluates RH-1 (Provider Agnosticism) by testing whether the control plane governs state deterministically across four distinct input representation families.

| Input Family | Example Providers | Vector Type ($\mathbf{v} \in \mathbb{R}^d$) | Benchmark Property & Purpose |
| :--- | :--- | :--- | :--- |
| **1. Neural (Latent)** | Sentence-Transformers, E5, CLIP | Dense, continuous ($d \approx 384\text{--}1536$) | Evaluates isolation of anisotropy and training noise from latent space. |
| **2. Lexical / Statistical** | BM25, TF-IDF, SPLADE | Sparse, discrete ($d = \|V\| \approx 50,000$) | Deterministic frequency baseline; evaluates sparse geometry without latent noise. |
| **3. Symbolic / Logical** | Graph Kernels (Weisfeiler-Lehman), OWL Ontologies | Discrete, structured | Evaluates topological states without statistical approximation. |
| **4. Direct Physical Signal** | Fourier/Wavelet transforms, LiDAR, IMU, ECG | Dense/Sparse (sensor-dependent) | Evaluates applicability in robotics, IoT, and industrial telemetry. |

* **Cross-Family Invariant:** The Spatial Control Plane aims to maintain deterministic state transitions ($S_{n+1} = f(S_n, \mathbf{v}_n)$) over the simplicial complex $S_n = (V_n, E_n, K_n)$ across all four families using identical routing logic. The variable under test is the origin of $\mathbf{v}$, never the state-governance mechanism itself.
