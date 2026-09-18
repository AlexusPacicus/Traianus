# Derivations

Every shortcut a record relies on, stated as an equality between the full form and the shortcut,
with its conditions and proof. A record may use a shortcut only if it has an entry here; phase 2
requires a passing unit test per entry, on random inputs that satisfy the conditions. Notation:
definitions.md.

```
D1  r = P⊥(v − c₁) = P⊥v.
    Conditions: none (c₁ = ‖c₁‖ĉ₁).
    Proof: P⊥c₁ = ‖c₁‖(ĉ₁ − ⟨ĉ₁, ĉ₁⟩ĉ₁) = 0; P⊥ is linear.

D2  ⟨r, v_dipole⟩ = ⟨v, v_dipole⟩, hence λ (unclipped) = ⟨v, v_dipole⟩ / ‖v_dipole‖².
    Conditions: v_dipole ⊥ ĉ₁ — holds in both branches: P⊥c_A − P⊥c_B ∈ ĉ₁⊥, and the fallback
    2δ·u⊥ with u⊥ ⊥ ĉ₁.
    Proof: ⟨P⊥v, w⟩ = ⟨v, P⊥w⟩ (P⊥ symmetric) and P⊥w = w for w ⊥ ĉ₁; then D1.

D3  ‖r‖² = 1 − y², y = ⟨v, ĉ₁⟩.
    Conditions: ‖v‖ = 1.
    Proof: ‖P⊥v‖² = ‖v‖² − ⟨v, ĉ₁⟩² (Pythagoras on v = ⟨v, ĉ₁⟩ĉ₁ + P⊥v).

D4  d_esc² = 1 − y² − ‖v_dipole‖²·x², x = λ.
    Conditions: ‖v‖ = 1; λ not clipped.
    Proof: ‖r − λw‖² = ‖r‖² − 2λ⟨r, w⟩ + λ²‖w‖², and ⟨r, w⟩ = λ‖w‖² when λ is unclipped
    (w = v_dipole); so d_esc² = ‖r‖² − λ²‖w‖²; then D3.

D5  ‖v − q‖² = 2 − 2⟨v, q⟩: ordering notes by y = ⟨v, q̂⟩ (descending) is ordering them by
    Euclidean distance to q (ascending).
    Conditions: ‖v‖ = ‖q‖ = 1.
    Proof: expand ‖v − q‖² = ‖v‖² − 2⟨v, q⟩ + ‖q‖².

D6  R² of an OLS fit with intercept is unchanged by per-column affine maps of the regressors
    (a·x + b, a ≠ 0) and of the response (a·y + b, a ≠ 0).
    Conditions: the intercept is in the design.
    Proof: the column space of the design, and so the fitted projection, is unchanged; SS_res
    and SS_tot both scale by a² under the response map.

D7  R²(m_ρ) = ρ for m_ρ = a·z(ĥ) + b·z(n⊥), a² / (a² + b²) = ρ.
    Conditions: ĥ ∈ span(B); n⊥ ⊥ span(B) in-sample; B contains the constant; z(·) centres and
    scales to unit population s.d.
    Proof: z(ĥ) ∈ span(B) (B has the constant); n⊥ ⊥ constant ⇒ mean 0, and ⊥ z(ĥ) ⇒ zero
    covariance; the fit of m_ρ is a·z(ĥ), so SS_reg = a²·n and SS_tot = (a² + b²)·n.

D8  P(a value exchangeable with 1,000 null values exceeds the 989th smallest of them) = 12/1001.
    Conditions: the 1,001 values are exchangeable with no ties.
    Proof: its rank among the 1,001 is uniform on 1…1001; it exceeds the 989th null value iff its
    rank is ≥ 990, i.e. 12 of 1,001 ranks.

D9  Recall of a random 15-subset against a fixed 15-subset of M = 1,109 notes: mean 225 / M,
    variance 15·(15/M)·(1 − 15/M)·(M − 15)/(M − 1).
    Conditions: the random subset is uniform (first 15 of a uniform permutation).
    Proof: the overlap is hypergeometric (population M, 15 successes, 15 draws).

D10 u_j = P_q⊥e_j / ‖P_q⊥e_j‖ is orthogonal to q, and q sits at horizontal coordinate 0 in both
    R4 arms.
    Conditions: ‖q‖ = 1; P_q⊥e_j ≠ 0.
    Proof: ⟨P_q⊥e, q⟩ = ⟨e, q⟩ − ⟨e, q⟩⟨q, q⟩ = 0; for the operator, ⟨q, v_dipole⟩ = 0 by D2's
    condition with ĉ₁ = q.
```

Used by: K6 (D2, D4, D6, D7, D8), R4 (D2, D5, D6, D9, D10).
