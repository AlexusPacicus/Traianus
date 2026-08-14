# Formal Status of Traianus (Truth Map)

This document establishes the canonical and immutable classification of all components, modules, and hypotheses in the repository. Each element belongs to exactly one of three categories.


---


## A. Implemented (Control Plane / Canonical)
*Components present in `traianus/` with deterministic proofs, execution guarantees, and 110/110 tests passing.*


* **Ingestion and HTTP Servability:** `/ingesta/vector` endpoint in `traianus/app.py`.
* **L2 Normalization and Spectral Projection:** Vector projection onto the geodetic basis $\mathbf{B}_0$.
* **Spectral Variance and Dismorphometry:** Local dismorphometry measurement $(\text{Var}(v \mathbf{B}_0^T))$.
* **Dual-Key C1 Gate:** Consolidation rule $(\sigma^2 \ge \theta_{\text{dyn}}) \land (\text{EthicalKey} == \text{True})$.
* **WAL Append-Only Persistence:** Immutable SQLite record (`traianus/storage.py`) restricted to 4 canonical states.
* **Deterministic $\epsilon$-edge Adjacency:** Observational similarity graph construction.
* **Kinetic Resistance ($K_{\text{cin}}$):** Kinetic friction evaluation by translation $\|\Delta v\|^2$ ($H_1$).
* **Dimensional Relief ($d \to d+1$):** `project_dimensional_relief` operator for cinematic decompression appending $K_{\text{cin}}$ to coordinate 385 ($H_2$).
* **Discriminative Novelty ($H_3$):** `ortho_distance` and `discrimination_ratio` operators with routing between `quarantine_noise` (`incubating`) and `structural_candidate` (`pending_approval`).


---


## B. Experimental (R&D Reproducible)
*Scripts and engines located in `tools/experiments/`. Empirically validated but outside the production control plane.*


* **`kinematics_engine.py`:** Laboratory development algebra engine for experiment runs.
* **Falsification Runners:** $H_1$ (`seq 13$), $H_2$ (`seq 14$), $H_3$ (`seq 15$) scripts and Integrated Pipeline (`seq 16$).
* **Logographic Experiments:** Reduced orthogonal basis probes and semantic dispersion.
* **NCD (Normalized Compression Distance) Tests:** Symbolic similarity comparatives.
* **Representation Independence (seq 18):** Governance-rule invariance under total embedding replacement (`exp_representation_independence.py`, scenarios A/B/C.1/C.2). Empirically validated GREEN: all governance ASSERTs hold across a 384D MiniLM model, the isomorphic mock, and the 128D hetero provider (zero-padded); 512D ingress is fail-closed (422, zero node side effects, one `telemetry_error` row). Coupling is measured (κ spread 0.018–0.090, σ² means ~0.0016–0.0026, edge-Jaccard 1.0 over empty ε-edge sets).


---


## C. Hypotheses / Future Research
*Open research lines not implemented in the core.*


* **Adaptive Dimensional Discovery:** Inertial and uninterrupted representation space expansion $N \to N+1$.
* **Persistent Topology over Manifolds:** Persistent Homology filtration over simplicial complexes in the substrate.


---


## Official Determinism Guarantee
> **Official Definition:** Given an identical sequence of input vectors, the same initial database state, and the same execution semantics, Traianus core state transitions are **100% deterministic and reproducible**.