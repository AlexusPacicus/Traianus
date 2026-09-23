# Technical Specification: Semantic Control Simplex & Dual-Speed Parabolic Corrector

This document specifies the mathematical and architectural consolidation of the **Traianus** spatial control substrate following the definitive purge of heuristic dependencies. A continuous cellular control model is established based on a **Semantic Control Simplex** (with self-bounded deviation faces) and an asynchronous reconstruction engine accelerated by a **3-Point Parabolic Corrector**.

---

## 1. The Semantic Control Simplex (Geometric Decision Cell)

In response to the instability of discrete decision thresholds and the rigidity of global variance ratios, Traianus redefines the local control context as a **continuous, self-bounded topological polyhedron** (an $n$-simplex, typically a triangle in the three-point projection).

### 1.1 Local Polyhedron Structure
In the local tangent hyperplane of dimension $d-1$ (projected via the rank-1 orthogonal projector $P^\perp = I - \hat{c}_1 \hat{c}_1^T$), the active neighbourhood is defined by three immutable codebook vertices:
*   **$c_1^\perp$:** Base anchor centroid (the origin in the local subspace).
*   **$c_A^\perp$:** Dipolar charge extremum A.
*   **$c_B^\perp$:** Dipolar charge extremum B.

The edges or link vectors connect these vertices to trace the principal dipole axis ($c_A^\perp \leftrightarrow c_B^\perp$) and the radial transition paths.

### 1.2 Local Density & Deviation Spheres
Each simplex vertex carries its own internal variance ($\sigma_1^2, \sigma_A^2, \sigma_B^2$), computed asynchronously from the stimuli grouped under its domain in the Data Plane. These variances define "influence spheres" or deviation bounds around each vertex.

### 1.3 Semantic Overlap & Intersection
The semantic intersection margin ($M_{ij}$) between two adjacent deviation domains is defined as the ratio between the sum of their standard deviations and the Euclidean distance between their projected centres:

$$M_{ij} = (\sigma_i + \sigma_j) - \|c_i^\perp - c_j^\perp\|_2$$

*   **$M_{ij} > 0$ (Intersection):** The standard-deviation fields overlap, defining a common region where concepts legitimately coexist.
*   **$M_{ij} < 0$ (Gap):** A spatial transition gap or semantic void exists between the domains.

### 1.4 Dimensionless Control Metric (Local Z-Score)
For any continuous input stimulus $v_n$ projected onto the tangent plane ($v_n^\perp$), we compute its normalised deviation (Z-score) with respect to each control vertex simultaneously:

$$z_i = \frac{\|v_n^\perp - c_i^\perp\|_2}{\sigma_i}, \quad \text{for } i \in \{1, A, B\}$$

This formulation guarantees:
1.  **Scale Invariance:** The control plane is independent of the embedding-space dimensionality ($d=384, 768, 1536$), self-calibrating according to the actual corpus density.
2.  **Anti-Evasion (Hardening):** Any misaligned or perturbative stimulus directly increases the individual Z-scores, crossing the polyhedron "faces".
3.  **Active Hysteresis:** The bidirectional Schmitt Trigger monitors whether the system abandons the overlap region when Z-scores simultaneously exceed the critical threshold ($z_i > 1.0$), forcing an anchor transition or recalibration in SQLite.

---

## 2. The 3-Point Parabolic Corrector (Major-Space Reconstruction)

To keep the control plane at sub-millisecond latencies and smooth 60 FPS visual output, the asynchronous reconstruction of the "major space" in the background cannot afford to project dense point-by-point trajectories. A **piecewise quadratic interpolation with deviation correction** is implemented.

### 2.1 Control Points & Baseline
For a trajectory segment with continuous traversal parameter $t \in [0, 1]$, we locate exactly three real positions in the continuous major space:
*   **$v_{ini}$:** Initial position ($t = 0.0$).
*   **$v_{mid}$:** Intermediate position ($t = 0.5$).
*   **$v_{fin}$:** Final position ($t = 1.0$).

We trace a baseline linear interpolation (straight line) between the endpoints:

$$v_{\text{line}}(t) = (1 - t) v_{ini} + t v_{fin}$$

### 2.2 Curvature Deviation Vector ($\mathbf{D}_{mid}$)
We compute the real spatial deviation or curvature of the exact midpoint relative to the linear segment centroid:

$$\mathbf{D}_{mid} = v_{mid} - \left(\frac{v_{ini} + v_{fin}}{2}\right)$$

This vector represents the "semantic tension" or distortion accumulated by the space's attractor structure.

### 2.3 General Parabolic Corrector Equation
We model the deviation along the entire segment via a parabolic function that vanishes at the endpoints ($t=0, t=1$) and reaches its maximum amplitude exactly at the midpoint:

$$\text{Correction}(t) = 4t(1 - t) \mathbf{D}_{mid}$$

The position of any reconstructed intermediate node in the major space resolves instantaneously on GPU or CPU via a clean linear combination:

$$v_{\text{reconst}}(t) = (1 - t) v_{ini} + t v_{fin} + 4t(1 - t) \mathbf{D}_{mid}$$

This formula reduces the computational complexity of sequential projections from $O(N \cdot d)$ to a single elementary vector sum of negligible cost, preserving geometric immanence and organic trajectory flow.

---

## 3. Local Isotropy via SVD Filter (Anisotropy Reduction)

Natural-language embedding spaces tend to suffer from anisotropy (collapsing into a narrow, elongated form where all vectors share common directions that carry no information). This deforms the escape-distance $d_{esc}$ calculations in the Polar Projector.

The ingestion pipeline actively incorporates **Dynamic Spurious Component Subtraction (SVD-Filter)**:
1.  For the active local context, a background thread computes the covariance matrix of the neighbourhood.
2.  Through Singular Value Decomposition (SVD), it extracts the first singular vector or dominant principal component ($\mathbf{u}_1$), representing the common bias axis or semantic inertia.
3.  The Polar Projector removes this spurious component from stimulus vectors before orthogonal projection, guaranteeing that the tangent space is strictly **isotropic** and that escape distances reflect only pure conceptual novelty.

---

## 4. Telemetry & Systems Test Bench (Validation Plan)

The Traianus substrate is validated locally through four automatic, user-interface-independent experiments:

1.  **Parabolic Fidelity Test (Accuracy vs. Speed):**
    *   Measures the Mean Squared Error (MSE) between the $v_{\text{reconst}}(t)$ approximation and exact point-by-point projections on complex trajectories, evaluating CPU microseconds saved.
2.  **Z-Score Telemetry Test (Anti-Evasion Safety):**
    *   Simulates normal semantic injections and misaligned noise bursts to verify whether individual control-simplex Z-scores exceed the 1.0 threshold without suffering the prior ratio collapse.
3.  **SVD Isotropy Test:**
    *   Quantitatively verifies the cleanliness and increase in escape-distance sensitivity pre- and post-SVD filtering on a real data corpus.
4.  **SQLite Concurrency Stress Test (WAL):**
    *   Runs massive, simultaneous simulations of Data Plane ingestion and asynchronous Control Plane re-projections to validate usability at ultra-low latencies (< 0.1 ms) without local-disk locking.
