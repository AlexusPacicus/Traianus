# Formal Status of Traianus (Truth Map)

This document establishes the canonical and immutable classification of all components, modules, and hypotheses in the repository. Each element belongs to exactly one of three categories.


---


## A. Implemented (Control Plane / Canonical)
*Components present in `traianus/` with determinism verified by hermetic tests, and 143/143 tests passing.*


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


* **`shared/kinematics_engine.py`:** Laboratory development algebra engine for experiment runs.
* **Falsification Runners:** $H_1$ (`seq 13`, realistic NSM basis since `seq 20`), $H_2$ (`seq 14$), $H_3$ (`seq 15$) scripts and Integrated Pipeline (`seq 16$).
* **Logographic Experiments:** Reduced orthogonal basis probes and semantic dispersion.
* **NCD (Normalized Compression Distance) Tests:** Symbolic similarity comparatives.
* **Representation Independence (seq 18, seq 19, seq 20):** Governance-rule invariance under total embedding replacement (`exp_representation_independence.py`, scenarios A/B/C.1/C.2). Empirically validated GREEN: all governance ASSERTs hold across a 384D MiniLM model, the isomorphic mock, and the 128D hetero provider (zero-padded); 512D ingress is fail-closed (422, zero node side effects, one `telemetry_error` row). The ε-edge metric is calibrated to a 5% pair density per provider (seq 19) so the edge-set Jaccard is non-vacuous. κ spread is the representation coupling index (REPORT, seq 20): measured as κ 0.018–0.090 (spread 0.072), σ² means ~0.0016–0.0026, edge-Jaccard ≈ 0.025–0.027 between scenarios — the governance RULES are invariant while the local E_n structure is highly representation-dependent.


---


## C. Research / Future Roadmap (Work Packages WP1–WP4)
*Open research lines not implemented in the core. Explicitly declared **RESEARCH / FUTURE ROADMAP** — not part of Core/Control Plane v1.0.0 (see IMPLEMENTATION_STATUS.md §0/§4 for the 5-category formal classification).*


* **WP1 — Dynamic Geodetic Axes (ADR-017):** Transition from the fixed `PROSTHETIC_NSM_V1` bootstrap basis to corpus-derived axes; decoupling governance from representation (EAS-01).
* **WP2 — Persistent Homology & Simplicial Faces (K_n) (ADR-018, ADR-019, ADR-023):** Persistent Homology filtration over simplicial complexes in the substrate; dynamic k-discovery via $H_1$; native GUDHI C++ integration.
* **WP3 — Riemannian Metric Engine (ADR-020):** System clock eradication and geodesic metric tensor integration.
* **WP4 — Cross-Scope Invariant Preservation (ADR-025):** Architectural drift control for invariants across optimizations, language bindings, and hardware targets.
* **RH-1 — Multi-Provider Dynamic Switching:** Dynamic provider switching beyond the frozen 384D core.


---


## Official Determinism Guarantee
> **Official Definition:** Given identical initial state, identical input vectors, and identical execution semantics, the core state transitions are **100% deterministic and reproducible within a runtime**. Bitwise equality across different Python builds, hardware architectures, or floating-point implementations is **not guaranteed** (see audit finding M1 — "Bitwise determinism" redefined to **runtime determinism**).

## Known Limitations (v1.0.0 Freeze)

| ID | Limitation | Impact | Roadmap |
|----|------------|--------|---------|
| **M1** | Runtime determinism only; no bitwise cross-build guarantee | Cannot use for cross-platform state replication | WP4 (Cross-Scope Invariant Preservation) |
| **M2** | Measured pipeline latency ~12ms p50 (encoding ~11.5ms + SQLite WAL ~0.5ms); SQLite I/O <1ms satisfied | Encoding bottleneck in provider layer | RH-1 (Multi-Provider) |
| **L1** | Hermetic suite uses deterministic MockProvider; model suite uses cached all-MiniLM-L6-v2 | Real encoder drift not continuously tested | RH-1 (Multi-Provider) |
| **L4** | NSM bootstrap basis has near-duplicates (max off-diag cosine ~0.13) | Provisional scaffold; variance calibration affected | WP1 (Dynamic Geodetic Axes) |