# Kernel Simulation over the Real Geodetic Basis — Test Data

**Script:** `traianus-simulation.py` (repo root)
**Date:** 2026-08-06
**DB:** `traianus.db` — table `geodesic_axes` (read-only, no mutation)
**Kernel:** `traianus/core.py` (`calibrate_critical_threshold`, `evaluate_gate_v01`)

---

## 1. Test objective

Replace the synthetic axes (`np.random` + Gram-Schmidt, orthonormal) with the 8
real BLOBs from `geodesic_axes` and measure: tissue density (θ_dyn), dual-key
gate behavior, and validity of the Dimensional Valve 384D → 385D.

## 2. Real geodetic basis loaded

8 axes, dimension 384, L2-normalized (norm = 1.0):

| Axis | Symbol | Tag | Dim | \|\|v\|\|₂ |
|---|---|---|---|---|
| AXIS_1 | ▲ | _SOMETHING | 384 | 1.000000 |
| AXIS_2 | △ | _BE_BELOW | 384 | 1.000000 |
| AXIS_3 | ▴ | _TRUE | 384 | 1.000000 |
| AXIS_4 | ▵ | _BE_BIG | 384 | 1.000000 |
| AXIS_5 | ▶ | _HERE | 384 | 1.000000 |
| AXIS_6 | ▷ | _LONG_TIME | 384 | 1.000000 |
| AXIS_7 | ▸ | _BECAUSE | 384 | 1.000000 |
| AXIS_8 | ▹ | _KIND_OF | 384 | 1.000000 |

**Measured non-orthonormality:** mean off-diagonal cosine **0.2267**, max **0.3362**.
(Previous simulation basis: orthonormal → cosine 0.0. Fiction.)

## 3. Tissue density (dynamic threshold)

`calibrate_critical_threshold()` — variance of the basis **cross** projections,
excluding self-projection (i ≠ j, audit C1):

```
theta_dyn = 0.004292
```

- With the synthetic orthonormal basis: `theta_dyn = 0.000000` (degenerate gate).
- With the simulation's old formula (`mean(cross²)`): `0.056346` (wrong scale).

## 4. Test vector and projection spectrum

Test vector = convex mixture of two real primitives (AXIS_1 + AXIS_2),
L2-normalized (simulates a focused ingestion).

| Projection | Value |
|---|---|
| p₁ (<v_d, e₁>) | +0.772054 |
| p₂ (<v_d, e₂>) | +0.772054 |
| p₃ (<v_d, e₃>) | +0.248010 |
| p₄ (<v_d, e₄>) | +0.325321 |
| p₅ (<v_d, e₅>) | +0.377084 |
| p₆ (<v_d, e₆>) | +0.225004 |
| p₇ (<v_d, e₇>) | +0.295496 |
| p₈ (<v_d, e₈>) | +0.299192 |

```
Spectral mean (p_bar)   = +0.414277
Variance (sigma^2)      = 0.044516   (friction)
```

## 5. Dual-Key Gate

| Key | Value |
|---|---|
| Condition (σ² ≥ θ_dyn) | `True` (0.044516 ≥ 0.004292) |
| Ethical Key (HITL) | `True` |
| State | **CONSOLIDATED** |

**Contrast (gate now discriminant):** uniform "noisy" vector (seed 42) →
variance ≈ 0.003 < 0.004292 → **INCUBATING**. The real threshold separates a
focused note from a generic one; it is no longer a gate that always passes.

## 6. Dimensional Valve (384D → 385D)

1. Zero-pad the entity: `v_d+1 = [v_d; 0.0]` → shape `(385,)`.
2. Re-pad the 8 real axes (each `[e_i; 0.0]`).
3. Inject the canonical axis `e_9 = [0, ..., 0, 1.0]`.
4. Recompute the spectrum in R³⁸⁵ (9 axes): p₁..p₈ identical, **p₉ = +0.000000**.

```
New spectral variance (sigma^2) = 0.056520
```

## 7. Physical invariants (all GREEN)

| Invariant | Result | Value |
|---|---|---|
| 1. \|\|v₃₈₅\|\|₂ == 1.0 | ✅ | 1.000000 |
| 2. dim(e₉) == 385 | ✅ | — |
| 3. \|B_n+1\| == 9 | ✅ | — |
| 4. max\|⟨e_old, e_new⟩\| == 0 | ✅ | 0.00e+00 |
| 5. ⟨v_d+1, e_new⟩ == 0 | ✅ | 0.00e+00 |

**TEST RESULT: PASSED (GREEN)**

## 8. Conclusions

1. The real basis is not orthonormal; the Gram-Schmidt model was unrealistic and
   fabricated a degenerate gate (θ = 0.0).
2. θ_dyn = 0.0043 is an exclusive property of the basis (8 real BLOBs): stable and auditable.
3. The gate now discriminates: spectral variance = "friction"; consolidation
   requires friction ≥ tissue density.
4. The Dimensional Valve is a mathematically consistent protocol: exact L2 = 1.0,
   absolute orthogonality of the new axis, deterministic spectrum.
5. Validation pending: the test vector is synthetic. The criterion still needs to
   be run over real note embeddings (`tools/audit_harness.py`) to confirm that the
   variance predicts something useful (audit WP1).
