# Traianus Theoretical Framework: Field Hydrodynamics, Helmholtz Decomposition, and Dimensional Relief (d→d+1)

**Status:** Draft / Specification

**Domain:** Substrate Physics & Core Algebra

**Authors:** Traianus Core Team

## 1. The Unified Field and the Rest Frame ("The Pool")

Traianus does not model the state space as a collection of discrete vectors in an empty space, but as a continuous, unified geometric manifold.

- **Monist Manifold:** Incoming data vectors **v** and accumulated state **S_n** are local projections of a single higher-dimensional entity.
- **Rest Frame (B₀):** The substrate maintains a geodesic orthogonal basis **B₀** ∈ ℝ^{k×d} representing the system in an undeformed equilibrium.
- **Irrotational Regime:** At equilibrium, the field behaves as an irrotational potential flow:

$$\nabla \times \mathbf{v} = 0$$

In this regime, information traverses the substrate with zero internal friction and zero dysmorphia.

## 2. Spatial Pressure, Dysmorphia, and Vorticity ("The River")

When new perturbations enter the substrate under high flow density, spatial compression forces trajectories to deviate from orthogonality.

- **Dysmorphia (D):** Compression-induced shear over local orthogonal axes.
- **Solenoidal Flow and Vorticity (ω):** Over-compression prevents straight-line relaxation, folding energy into local vorticity:

$$\omega = \nabla \times \mathbf{v} \neq 0$$

- **Kinetic Resistance (K_cin):** The physical metric of the kernel. Measures the internal friction/work required to re-assimilate the vortex into the substrate:

$$K_{cin} = \frac{1}{2} \|\Delta \mathbf{v}\|^2 \cdot (1 + \text{Var}(\mathbf{v} \cdot B_0^T))$$

## 3. Dimensional Relief and Re-orthogonalization (d→d+1)

To prevent manifold tearing or performance collapse under high spatial pressure, the substrate activates a scalar augmentation valve.

- **Augmentation Mapping:** The coordinate vector **v** ∈ ℝ^d is unconditionally mapped to **v̂** ∈ ℝ^{d+1}:

$$\hat{\mathbf{v}} = (v_1, v_2, \ldots, v_d, K_{cin})$$

- **Vortex Unrolling:** The (d+1)-th coordinate absorbs solenoidal kinetic energy. What manifests as a turbulent vortex in d dimensions relaminarizes into a smooth, orthogonal trajectory in d+1 dimensions.

- **Gating via θ_dyn:** The dynamic threshold θ_dyn evaluates the (d+1)-th coordinate to determine whether the state is consolidated, quarantined, or denied:

$$\text{State Gate} = \begin{cases} \text{Consolidate} & \text{if } K_{cin} \leq \theta_{dyn} \\ \text{Quarantine / Adapt} & \text{if } K_{cin} > \theta_{dyn} \end{cases}$$

## 4. Dual Taxonomy of Novelty

```
                            ┌── Dynamic Novelty (Vorticity / Temporal Pressure)
                            │   ├─ Local kinetic agitation within d dimensions.
                            │   └─ Absorbed in the (d+1) coordinate via K_cin.
Taxonomy of Novelty ───────┤
                            └── Structural Novelty (Manifold Discovery)
                                ├─ Revelation of hidden axes of the entity.
                                └─ Triggers update of basis B₀.
```

- **Dynamic Novelty:** Transient turbulence caused by flow velocity or local noise. Measured via K_cin without modifying B₀.
- **Structural Novelty:** Expansion of the visible territory of the domain. Requires re-aligning B₀ to incorporate the new orthogonal axes of the hyperdimensional entity.

## 5. Falsifiable Experimental Hypotheses

- **H1 (Pressure and Vorticity):** Increasing point density within fixed d dimensions monotonically increases vorticity ω and kinetic dysmorphia K_cin.
- **H2 (Dimensional Relief):** Projecting over-compressed vectors onto ℝ^{d+1} via kinetic scalar augmentation restores relative orthogonality and increases trajectory laminarity.
- **H3 (Novelty Discrimination):** The ratio between K_cin dissipation and base projection distance strictly separates transient noise/anomalies from actual structural base updates.
