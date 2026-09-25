# Derivations

Every shortcut a record relies on, stated as an equality between the full form and the shortcut,
with its conditions and proof. A record may use a shortcut only if it has an entry here; phase 2
requires a passing unit test per entry, on random inputs that satisfy the conditions. Notation:
definitions.md.

**Tolerance rule for the tests.** Corpus vectors are float32 used as float64, so ‖v‖ = 1 holds
only to ≈ 1e-7. Every equality is tested within a stated tolerance: absolute 1e-9 on inputs
constructed exactly in float64; relative to the terms' magnitude (e.g. ‖r‖²) on corpus-derived
inputs; D4 is never tested in the regime d_esc/‖r‖ < 1e-6, where its scalar form cancels
(polar_projector.py:287-289).

```
D1  r = P⊥(v − c₁) = P⊥v.
    Conditions: c₁ ≠ 0 (so ĉ₁ exists).
    Proof: c₁ = ‖c₁‖ĉ₁ and P⊥ĉ₁ = ĉ₁ − ⟨ĉ₁, ĉ₁⟩ĉ₁ = 0; P⊥ is linear.

D2  ⟨r, w⟩ = ⟨v, w⟩ for w = v_dipole, hence λ (unclipped) = ⟨v, w⟩ / ‖w‖².
    Conditions: w ⊥ ĉ₁ and ‖w‖² > 0 (prepare rejects ‖w‖² ≤ 0, polar_projector.py:241-245).
    w ⊥ ĉ₁ holds in both branches, given ‖ĉ₁‖ = 1 (_normalize_anchor, :85) and
    P⊥x = x − ⟨x, ĉ₁⟩ĉ₁ (_project_perp, :100): non-collinear, w = P⊥c_A − P⊥c_B ∈ ĉ₁⊥;
    fallback, w = 2δ·u⊥ with u⊥ from _canonical_u_perp (:131): for k = argmin|ĉ₁[k]|,
    s = ĉ₁[k] (|s| < 1), R = √(1 − s²), u⊥ = (−s/R)·ĉ₁ with component k set to R, so
    ⟨u⊥, ĉ₁⟩ = (−s/R)(1 − s²) + R·s = 0 and ‖u⊥‖ = 1.
    Note: in the fallback w does not depend on c_A, c_B, so λ's sign is not tied to pole order.
    Proof: ⟨P⊥v, w⟩ = ⟨v, P⊥w⟩ (P⊥ symmetric) and P⊥w = w for w ⊥ ĉ₁; then D1.

D3  ‖r‖² = 1 − y², y = ⟨v, ĉ₁⟩.
    Conditions: ‖v‖ = 1, ‖ĉ₁‖ = 1 (corpus: ‖v‖ = 1 to ≈ 1e-7, see tolerance rule).
    Proof: v = ⟨v, ĉ₁⟩ĉ₁ + P⊥v, orthogonal parts; Pythagoras.

D4  For each dipole k: d_esc,k² = 1 − y² − ‖w_k‖²·λ_k², w_k = v_dipole,k; for k = 1, λ₁ = x.
    Conditions: ‖v‖ = 1; λ_k unclipped, i.e. |⟨v, w_k⟩| ≤ ‖w_k‖² (at equality the clip is
    inactive).
    Proof: ‖r − λw‖² = ‖r‖² − 2λ⟨r, w⟩ + λ²‖w‖², and ⟨r, w⟩ = λ‖w‖² when λ is unclipped (D2);
    so d_esc² = ‖r‖² − λ²‖w‖²; then D3.

D5  ‖v − q‖² = ‖v‖² + ‖q‖² − 2‖q‖⟨v, q̂⟩: ordering notes by y = ⟨v, q̂⟩ (descending) is
    ordering them by Euclidean distance to q (ascending).
    Conditions: every note has the same norm (here 1) and q ≠ 0. Near-ties can swap under float32
    norms; a top-k cut must break ties by the same rule in both orderings.
    Proof: expand; with ‖v‖ fixed, the distance is strictly decreasing in ⟨v, q̂⟩.

D6  R² of an OLS fit with intercept is unchanged by invertible linear maps of the non-intercept
    columns plus intercept shifts (in particular per-column a·x + b, a ≠ 0) and by affine maps of
    the response (a·y + b, a ≠ 0).
    Conditions: the intercept is in the design; the response is not constant (SS_tot > 0).
    Proof: the design's column space, hence the fitted projection, is unchanged; since 1 is in
    the design, resid(a·y + b·1) = a·resid(y), so SS_res and SS_tot both scale by a².

D7  R²(m_ρ) = ρ for m_ρ = a·z(ĥ) + b·z(n⊥), a² / (a² + b²) = ρ.
    Conditions: ĥ ∈ span(B), not constant; n⊥ ⊥ span(B) in-sample, n⊥ ≠ 0; B contains the
    constant; z(·) centres and scales to unit population s.d.; a² + b² > 0; R² from an OLS fit
    of m_ρ on exactly B (or an affine re-map of it, D6).
    Proof: z(ĥ) ∈ span(B) (B has the constant); z(n⊥) = n⊥ / sd ∈ span(B)⊥, so it has mean 0
    and is orthogonal to z(ĥ); the fit is a·z(ĥ), the residual b·z(n⊥), so SS_res = b²·n and
    SS_tot = (a² + b²)·n.

D8  P(a value exchangeable with 1,000 null values exceeds the 989th smallest) = 12/1001
    ≈ 0.011988 (a cutoff at α ≈ 0.012, not 0.01).
    Conditions: the 1,001 values are exchangeable. With ties, under randomised tie-breaking,
    P(strictly exceeds) ≤ 12/1001, so the bound form needs no no-ties condition.
    Proof: its rank among the 1,001 is uniform on 1…1001; it exceeds the 989th null value iff its
    rank is ≥ 990: 12 of 1,001 ranks.

D9  The overlap count K between a uniform random 15-subset and a fixed 15-subset of the same
    M = 1,109 notes (R4's recall@15 is this count, 0–15) is Hypergeometric(M, 15, 15):
    E[K] = 225 / M ≈ 0.20289, Var[K] = 15·(15/M)·(1 − 15/M)·(M − 15)/(M − 1) ≈ 0.19762.
    (As a fraction K/15: mean 15/M ≈ 0.013526, variance Var[K]/225 ≈ 8.783e-4.)
    Conditions: the random subset is the first 15 of a uniform permutation of the same M notes
    that contain the fixed subset.
    Proof: sampling 15 without replacement from M items of which 15 are marked.

D10 u_j = P_q⊥e_j / ‖P_q⊥e_j‖ is orthogonal to q, and q sits at horizontal coordinate 0 in both
    R4 arms (operator: ⟨q, w⟩ / ‖w‖²; random: ⟨q, u_j⟩).
    Conditions: ‖q‖ = 1; e_j not parallel to q; for the operator, c₁ = q (or a positive multiple).
    Proof: ⟨P_q⊥e, q⟩ = ⟨e, q⟩ − ⟨e, q⟩⟨q, q⟩ = 0. Operator: r = P⊥(q − q) = 0 exactly, so
    λ = 0 and d_esc = 0 even in floating point (exact, unlike the route through D2).

D11 With λ clipped to s = ±1: d_esc² = 1 − y² − 2s⟨v, w⟩ + ‖w‖².
    Conditions: ‖v‖ = 1.
    Proof: ‖r − s·w‖² = ‖r‖² − 2s⟨r, w⟩ + ‖w‖², then D2 and D3. (K6's positive control h uses the
    clipped λ₁: D4 where unclipped, D11 where clipped.)

D12 λ is never clipped when ‖w‖ ≥ √(1 − y²), in particular whenever ‖w‖ ≥ 1.
    Conditions: ‖v‖ = 1.
    Proof: Cauchy–Schwarz with D2: |⟨v, w⟩| = |⟨P⊥v, w⟩| ≤ √(1 − y²)·‖w‖ ≤ ‖w‖².

    (D13–D16 belong to the frozen K8 record, on branch feat/k8-z-axis; the numbers stay reserved.)

D17 For c ∈ ℝⁿ and Var(c) = (1/n) Σ_k (c_k − c̄)², c̄ = (1/n) Σ_k c_k:
    ∇Var(c) = (2/n)(c − c̄·1). For n = 8: ∇Var(c) = ¼(c − c̄·1).
    Conditions: none.
    Proof: ∂Var/∂c_k = (2/n)(c_k − c̄) − (2/n)·(1/n)·Σ_j (c_j − c̄), and Σ_j (c_j − c̄) = 0.

D18 For Pos(t) = (1 − t)A + tB + 4t(1 − t)D, f = 1 + Var and τ(D) = ∫₀¹ √f(Pos(t)) ‖Pos'(t)‖ dt:
    ∂τ/∂D = ∫₀¹ [ 4t(1 − t) · ‖Pos'‖ · ∇f(Pos) / (2√f(Pos)) + 4(1 − 2t) · √f(Pos) · Pos'/‖Pos'‖ ] dt,
    with Pos'(t) = (B − A) + 4(1 − 2t)D and ∇f = ∇Var (D17).
    Conditions: Pos'(t) ≠ 0 for almost every t (Pos' is affine in t, so it vanishes at most at one
    t unless it vanishes identically, which requires A = B and D = 0); f ≥ 1 > 0.
    Proof: ∂Pos/∂D = 4t(1 − t)·I and ∂Pos'/∂D = 4(1 − 2t)·I; the chain rule on √f(Pos) and on ‖Pos'‖
    (∇‖x‖ = x/‖x‖ for x ≠ 0); the integrand's derivative is bounded on [0, 1] away from the single
    possible zero of Pos', so differentiation under the integral holds.

D19 τ(0, t) = ∫₀ᵗ √f(Pos(s)) ‖Pos'(s)‖ ds is continuous and strictly increasing on [0, 1], so t*
    with τ(0, t*) = τ(0, 1)/2 exists and is unique.
    Conditions: f ≥ 1; Pos continuous on [0, 1] and, piece by piece, affine or quadratic in t, with
    Pos' zero or undefined at finitely many points at most (a straight segment, a parabola, or two
    straight legs joined at a point, where Pos' is undefined).
    Proof: the integrand is ≥ 0 and is 0 or undefined only at finitely many points; an integral of
    a function positive except at finitely many points is strictly increasing; continuity and the
    intermediate value theorem give existence.

D20 For P ≠ Q and the straight leg Λ(s) = P + s(Q − P), s ∈ [0, 1]:
    τ_seg(P, Q) = ‖Q − P‖ ∫₀¹ √f(Λ(s)) ds, and with u = (Q − P)/‖Q − P‖:
    ∇_Q τ_seg = u ∫₀¹ √f(Λ) ds + ‖Q − P‖ ∫₀¹ s · ∇f(Λ) / (2√f(Λ)) ds,
    ∇_P τ_seg = −u ∫₀¹ √f(Λ) ds + ‖Q − P‖ ∫₀¹ (1 − s) · ∇f(Λ) / (2√f(Λ)) ds,
    with ∇f = ∇Var (D17) when f = 1 + Var. Additivity: for R = P + r(Q − P), r ∈ [0, 1],
    τ_seg(P, Q) = τ_seg(P, R) + τ_seg(R, Q). Reversal: τ_seg(P, Q) = τ_seg(Q, P). Radial rate:
    d/dr τ_seg(P, P + r·u) = √f(P + r·u) ≥ 1.
    Node-sum form: for a rule with nodes s_i ∈ [0, 1] and weights w_i,
    τ_seg(P, Q) = ‖Q − P‖ Σ_i w_i √f(Λ(s_i)) has the exact gradients of the same form, each ∫₀¹ … ds
    replaced by Σ_i w_i … at s = s_i; reversal holds when the rule is symmetric under s ↦ 1 − s
    (Gauss–Legendre is); additivity and the radial rate hold only up to the rule's error.
    Conditions: P ≠ Q (for the gradients); f ≥ 1 and continuously differentiable (f = 1 + Var is
    a polynomial).
    Proof: τ of the leg is ∫₀¹ √f(Λ(s)) ‖Λ'(s)‖ ds with ‖Λ'‖ = ‖Q − P‖ constant. ∂Λ/∂Q = s·I,
    ∂Λ/∂P = (1 − s)·I, ∂‖Q − P‖/∂Q = u = −∂‖Q − P‖/∂P; the integrand is smooth in P and Q for
    P ≠ Q, so differentiation under the integral holds. Additivity: split ∫₀¹ at r and substitute
    s = r·σ and s = r + (1 − r)·σ. Reversal: substitute s = 1 − σ; ‖P − Q‖ = ‖Q − P‖. Radial rate:
    substituting σ = r·s, τ_seg(P, P + r·u) = r ∫₀¹ √f(P + r·s·u) ds = ∫₀ʳ √f(P + σu) dσ, whose
    derivative in r is the integrand at σ = r (fundamental theorem of calculus; √f is continuous).
    Node-sum form: differentiate the finite sum term by term with the same ∂Λ/∂Q, ∂Λ/∂P and
    ∂‖Q − P‖; reversal maps node s_i to 1 − s_i, which the symmetric rule contains with the same
    weight.

D21 With τ_A(m) = τ_seg(A, m), τ_B(m) = τ_seg(m, B), S = τ_A + τ_B and E = τ_A − τ_B: at a local
    minimiser m* of S subject to E = 0 there is μ with ∇S(m*) = μ∇E(m*), i.e.
    (1 − μ)∇τ_A(m*) = −(1 + μ)∇τ_B(m*), and μ ≠ ±1. The two gradients are parallel, so the level
    sets {τ_A = r} and {τ_B = r}, r = τ_A(m*) = τ_B(m*), share their tangent hyperplane at m*: two
    friction-time hyperspheres of equal radius, one around A and one around B, touch at m*. For
    |μ| < 1 the gradients point in opposite directions (the two touch from outside); for |μ| > 1
    in the same direction (one touches the other from inside). The shared hyperplane is not the
    route's direction at m*: the two-leg route has a corner there.
    Conditions: m* ∉ {A, B} (D20's gradients exist); ∇E(m*) ≠ 0 (constraint qualification). The
    level sets are hypersurfaces automatically: by D20's radial rate, ⟨∇τ_A(m), (m − A)/‖m − A‖⟩ =
    √f(m) ≥ 1, and likewise for τ_B = τ_seg(B, ·) (D20's reversal) with (m − B)/‖m − B‖, so neither
    gradient vanishes; each level set is star-shaped around its centre. On the segment AB,
    ⟨∇E, u⟩ = 2√f > 0 (u the unit chord), so ∇E ≠ 0 there.
    Proof: the Lagrange multiplier theorem for one equality constraint; μ = ±1 would make one of
    the two gradients zero, which the radial rate excludes; a hypersurface's tangent hyperplane is
    the orthogonal complement of its gradient, and parallel gradients give the same complement.

D22 Merit with a non-decreasing penalty. For φ_ρ(m) = S(m) + ρ|E(m)|, penalties
    ρ_1 ≤ ρ_2 ≤ … ≤ ρ_K and iterates m_0, m_1, …, m_K where each step k satisfies
    φ_{ρ_k}(m_k) ≤ φ_{ρ_k}(m_{k−1}):
    φ_{ρ_K}(m_K) ≤ φ_{ρ_1}(m_0) + Σ_{k=2}^{K} (ρ_k − ρ_{k−1}) · |E(m_{k−1})|.
    Conditions: ρ non-decreasing; each step accepted under its own ρ_k.
    Proof: φ_{ρ_k}(m_{k−1}) = φ_{ρ_{k−1}}(m_{k−1}) + (ρ_k − ρ_{k−1})|E(m_{k−1})|, so
    φ_{ρ_k}(m_k) ≤ φ_{ρ_{k−1}}(m_{k−1}) + (ρ_k − ρ_{k−1})|E(m_{k−1})|; chain from k = K down to 2 and
    use φ_{ρ_1}(m_1) ≤ φ_{ρ_1}(m_0).

D23 E is strictly increasing along chords' parallels inside a tube. With τ_A, τ_B and E as in D21,
    d = ‖B − A‖, u = (B − A)/d, Y ⊥ u, h = ‖Y‖ and m(ξ) = A + ξ·u + Y: if 0 < d < 4√2 and
    h ≤ h_max(d) = (4√2 − d)·√(d / (8√2 − d)), then ⟨∇E(m(ξ)), u⟩ > 0 for every ξ ∈ [0, d]
    (ξ ∈ (0, d) when h = 0), so ξ ↦ E(m(ξ)) is strictly increasing there and has at most one zero
    in [0, d]. Its existence is not claimed. The tube is sufficient, not necessary. The same holds
    when every τ_seg is a quadrature ‖Q − P‖·Σ_i w_i √f(Λ(s_i)) with nodes s_i ∈ [0, 1], weights
    w_i > 0, Σ_i w_i = 1 and Σ_i w_i s_i = ½ (Gauss–Legendre mapped to [0, 1] qualifies), D20's
    gradients taken on the same nodes.
    Conditions: f continuously differentiable (D20), with f ≥ 1 and ‖∇√f‖ < G := 1/(2√2) on every
    leg A → m(ξ) and m(ξ) → B of the statement (everywhere suffices; f = 1 + Var over 8 components
    meets both everywhere, step (i)); m(ξ) ∉ {A, B} (D20's gradients), which h > 0 or ξ ∈ (0, d)
    ensures. For axis coordinates of unit vectors |c_k| ≤ 1, so d ≤ 4√2.
    Proof: (i) ∇√f = ∇f/(2√f) and, by D17, ‖∇Var‖² = Var/2, so
    ‖∇√f‖ = (1/(2√2))·√(Var/(1 + Var)) < G. (ii) By D20, with r_A = ‖m − A‖, r_B = ‖B − m‖,
    û_A = (m − A)/r_A, û_B = (B − m)/r_B and I_A, I_B ≥ 1 the two legs' ∫₀¹ √f ds:
    ∇E = I_A·û_A + I_B·û_B + r_A ∫₀¹ s·∇√f(Λ_A) ds − r_B ∫₀¹ (1 − s)·∇√f(Λ_B) ds. On [0, d],
    ⟨û_A, u⟩ = ξ/r_A ≥ 0 and ⟨û_B, u⟩ = (d − ξ)/r_B ≥ 0, so by (i)
    ⟨∇E, u⟩ > Φ(ξ) := ξ/r_A + (d − ξ)/r_B − (G/2)(r_A + r_B), r_A = √(ξ² + h²),
    r_B = √((d − ξ)² + h²). With the quadrature, I_A, I_B = Σ_i w_i √f ≥ 1 and the two interior
    terms are at most r_A·G·Σ_i w_i s_i = r_A·G/2 and r_B·G·Σ_i w_i(1 − s_i) = r_B·G/2 in size
    (each w_i·s_i and w_i·(1 − s_i) is ≥ 0, as s_i ∈ [0, 1]), so the same Φ bounds it. (iii) For h = 0, Φ = 2 − Gd/2 > 0 on (0, d). For h > 0,
    ξ/√(ξ² + h²) is concave on ξ ≥ 0 and (d − ξ)/√((d − ξ)² + h²) on ξ ≤ d; r_A and r_B are convex;
    so Φ is concave on [0, d], its minimum is at an end, and Φ(0) = Φ(d) by ξ ↔ d − ξ. (iv) With
    η = h/d, Φ(0) ≥ 0 ⟺ √(1 + η²)(η + √(1 + η²)) ≤ 2/(Gd) = 4√2/d; with η = sinh θ the left side
    is (e^{2θ} + 1)/2, so the condition is e^{2θ} ≤ W := 8√2/d − 1, i.e.
    η ≤ sinh(½ ln W) = (W − 1)/(2√W), which is h ≤ h_max(d).

D24 The search in the tube is the constrained problem. With d, u, S, E as in D21 and D23, Z_N an
    8 × 7 matrix with orthonormal columns spanning the hyperplane orthogonal to u, and
    m(z) = A + ξ(z)·u + Z_N z, where ξ(z) is the zero of ξ ↦ E(A + ξ·u + Z_N z) in [0, d] (unique by D23 for ‖z‖ ≤ h_max(d)): ξ is
    continuously differentiable with ∇ξ = −Z_Nᵀ∇E / ⟨∇E, u⟩, and g(z) = S(m(z)) has
    ∇g = Z_Nᵀ(∇S − μ̂∇E), μ̂ = ⟨∇S, u⟩ / ⟨∇E, u⟩.
    ∇g(z) = 0 iff ∇S(m(z)) = μ̂∇E(m(z)): the critical points of g are D21's Lagrange points in the
    tube, with μ = μ̂. z ↦ m(z) is one-to-one onto {E = 0} ∩ {0 ≤ ⟨m − A, u⟩ ≤ d,
    ‖Z_Nᵀ(m − A)‖ ≤ h_max(d)}, with inverse z = Z_Nᵀ(m − A), so local minimisers of g and of S on
    that set correspond. First order: for m′ = m + Δξ·u with E(m′) = 0,
    S(m′) − S(m) = −μ̂·E(m) + O(E(m)²).
    Conditions: those of D23; the zero exists in [0, d] at z (checked, not implied); m ∉ {A, B}.
    Proof: E is continuously differentiable away from A and B (D20) and ∂E(m(z))/∂ξ = ⟨∇E, u⟩ > 0
    (D23), so the implicit function theorem gives ξ continuously differentiable with
    ⟨∇E, u⟩∇ξ + Z_Nᵀ∇E = 0; the chain rule gives ∇g = Z_Nᵀ∇S + ⟨∇S, u⟩∇ξ. If ∇g = 0, the vector
    ∇S − μ̂∇E has no component orthogonal to u (along the columns of Z_N) and, by μ̂'s definition,
    none on u, so it is 0; conversely ∇S = μ∇E gives μ = μ̂ (take ⟨·, u⟩, with ⟨∇E, u⟩ ≠ 0) and ∇g = 0. One-to-one:
    Z_Nᵀ(m − A) = z because Z_Nᵀu = 0, and D23 makes the zero on each parallel unique; both maps are
    continuous. First order: −E(m) = E(m′) − E(m) = ⟨∇E, u⟩Δξ + O(Δξ²), and
    S(m′) − S(m) = ⟨∇S, u⟩Δξ + O(Δξ²).

D25 Neighbourhood a zoom keeps at every scale, against a zoom with no information (co-ranking: Lee
    and Verleysen, Neurocomputing 72, 2009; the weights 1/K: Lee et al., Neurocomputing 169, 2015;
    both cited from memory, not verified). U is the set of notes that can be shown (N_U of them),
    M ⊆ U the notes in view (N_M), j ∈ M, N_c = N_U − 1 the candidates. For K = 1, …, N_U − 2:
    hyp_j(K) = j's K nearest in 384-d among U \ {j} (its hypersphere, the same whatever the view);
    K′ = min(K, N_M − 1); shown_j(K) = j's K′ nearest on the displayed plane among M \ {j};
    O_j(K) = |hyp_j(K) ∩ shown_j(K)|;
    R_j(K) = (O_j(K)/K − K′/N_c) / (1 − K′/N_c),   R_NX(K) = (1/N_M) Σ_{j∈M} R_j(K),
    AUC = [Σ_K R_NX(K)/K] / [Σ_K 1/K] = (1/N_M) Σ_{j∈M} AUC_j,   AUC_j = [Σ_K R_j(K)/K] / [Σ_K 1/K].
    (a) R_j(K) ≤ 1, with equality iff K′ = K and shown_j(K) = hyp_j(K): a view with fewer than
    K + 1 notes cannot reach 1 at scale K. With M = U and shown_j(K) = hyp_j(K) for every j and K,
    AUC = 1.
    (b) If the view and its order carry no information — shown_j(K) is the first K′ of a uniformly
    random arrangement of N_M − 1 notes out of U \ {j}, independent across j — then
    E[R_j(K)] = 0 and Var[R_j(K)] = K′(N_c − K) / (K(N_c − K′)(N_c − 1)) ≤ 1/(N_U − 2), so
    E[AUC] = 0, Var[AUC_j] ≤ 1/(N_U − 2) and Var[AUC] ≤ 1/(N_M(N_U − 2)).
    (c) With M = U, K′ = K and R_j(K) = (N_c·O_j(K)/K − K)/(N_c − K); at K = 15,
    R_NX(15) = (Ō₁₅ − 225/N_c)/(15 − 225/N_c), Ō₁₅ = (1/N_U) Σ_j O_j(15), 225/N_c being the mean
    of O_j(15) under (b) (D9 with N_c candidates).
    Conditions: N_U ≥ 3 (K = 1 exists and K < N_c); N_M ≥ 2 (K′ ≥ 1).
    Proof: (a) O_j(K) ≤ K′ ≤ K and R_j(K) is increasing in O_j(K); at O_j(K) = K′ it equals
    (K′/K − K′/N_c)/(1 − K′/N_c), which is 1 iff K′ = K. (b) Under the null shown_j(K) is a uniform
    random K′-subset of the N_c others, so O_j(K) is Hypergeometric(N_c, K, K′): mean K′K/N_c,
    variance K′K(N_c − K)(N_c − K′)/(N_c²(N_c − 1)); R_j(K) is affine in O_j(K) with slope
    1/(K(1 − K′/N_c)), which gives mean 0 and the variance stated; K′(N_c − K) ≤ K(N_c − K′) since
    K′ ≤ K. AUC_j is a weighted mean of the R_j(K) with weights summing to 1, and the standard
    deviation of a sum is at most the sum of the standard deviations (Minkowski); the AUC_j are
    independent across j, so Var[AUC] = Σ_j Var[AUC_j]/N_M². (c) Substitute K′ = K; at K = 15
    divide the numerator and the denominator by N_c/15.

D26 A world where the benchmark's middle is the answer. With S and E as in D21, f = 1 + Var (D17)
    and m₀ the τ-midpoint of the segment AB (D19): if A = a·1 and ⟨B − A, 1⟩ = 0 with B ≠ A, then
    S(m) ≥ τ_seg(A, B) = S(m₀) for every m ∈ ℝ⁸, and m₀ is the only minimiser of S subject to
    E = 0. Quadrature form (every τ_seg by one rule, D20's node-sum form; g, Z_N and mid(z) as in
    D24 and the record): g(−z) = g(z), so ∇g(0) = 0; and S(m) ≥ S(π(m)) node by node, π below,
    with a gap of at least h²/(‖m − A‖ + ξ) + h²/(‖B − m‖ + d − ξ), h = ‖m − π(m)‖,
    ξ = ⟨π(m) − A, u⟩ ∈ [0, d], d = ‖B − A‖. What is lost is only the constancy of S along the
    segment, which additivity gave: it holds up to the rule's error, so z = 0 minimises g up to
    that error.
    Conditions: A on the diagonal; B − A orthogonal to it; B ≠ A; for the quadrature form, the
    rule's nodes in [0, 1], positive weights summing to 1.
    Proof: u = (B − A)/‖B − A‖, π(x) = A + ⟨x − A, u⟩·u, Π = I − 11ᵀ/8, so Var(x) = ‖Πx‖²/8,
    ΠA = 0 and Πu = u. For x = A + ξ·u + Y with Y ⊥ u: Πx = ξ·u + ΠY and ⟨u, ΠY⟩ = ⟨Πu, Y⟩ = 0, so
    Var(x) = (ξ² + ‖ΠY‖²)/8 ≥ ξ²/8 = Var(π(x)). π is 1-Lipschitz, so projecting the route A → m → B
    does not raise √f and does not lengthen it; the projection runs along the line from A to B,
    covers the segment AB, and so takes at least τ_seg(A, B). Equality needs the route to stay on
    the line (a leg with a component orthogonal to u is strictly longer than its projection, and
    f ≥ 1) and not to turn back, i.e. m on the segment, where S = τ_seg(A, B) (D20 additivity) and
    E, strictly increasing (D21: ⟨∇E, u⟩ = 2√f), is zero only at m₀ (D19). Quadrature form: the
    reflection R(x) = 2π(x) − x is an affine isometry that fixes A and B and turns Y into −Y, so
    Var(R(x)) = Var(x); it maps the nodes of each leg onto those of the reflected leg, so S and E
    computed by the rule are R-invariant; ℓ_{−z} = R(ℓ_z), the zero on ℓ_{−z} is the image of the
    zero on ℓ_z (unique, D23), and g(−z) = g(z); an even differentiable function has ∇g(0) = 0.
    π is affine with π(A) = A, so it maps the nodes of the leg A → m onto those of A → π(m), and
    likewise for m → B; node by node √f does not rise, and the leg's length drops by
    ‖m − A‖ − ξ = h²/(‖m − A‖ + ξ) (likewise for the other leg); with Σ_i w_i √f ≥ 1 on the
    projected leg, each drop bounds that leg's share of the gap.
```

D18 is not used by Z since its revision 3 (the three-point route became two straight legs); it
stays as verified. D22 is not used by Z since its revision 5 (the search keeps every point on
E = 0, so there is no merit function); it stays as verified.

Used by: K6 (D2, D4, D6, D7, D8, D11), R4 (D2, D5, D6, D9, D10), Z (D5, D17, D19, D20, D21, D23,
D24, D25, D26).

## En palabras

- **D1** Restar el ancla antes de proyectar no cambia nada: la proyección ya elimina todo lo que
  apunta en la dirección del ancla.
- **D2** Para medir cuánto se inclina una nota hacia un polo da igual usar la nota entera o su
  parte ortogonal al ancla, porque el dipolo no tiene componente en el ancla (tampoco el de
  respaldo). Por eso λ se calcula con un solo producto escalar.
- **D3** En la esfera unidad, lo que queda de una nota tras quitarle el ancla mide 1 − y².
- **D4** Si λ no se recorta, la distancia de escape queda fijada por la posición (x, y): no aporta
  información nueva.
- **D5** Con todas las notas de la misma longitud, ordenar por similitud con q es lo mismo que
  ordenar por distancia a q.
- **D6** Cambiar de unidades o desplazar las columnas no altera el R², siempre que haya término
  constante.
- **D7** Los controles de calibración se construyen para que su R² sea exactamente el valor que se
  quiere, así que cualquier desviación señala un fallo del código.
- **D8** Un candidato que se comporte como una dirección al azar supera el valor 989 de 1.000 con
  probabilidad 12/1.001; con cuatro candidatos, el riesgo total queda en 4,80 %.
- **D9** Si se eligieran 15 vecinas al azar, coincidirían de media 0,203 con las 15 reales; es el
  control de permutación.
- **D10** Cualquier eje horizontal ortogonal a q deja a q en el centro horizontal de su propia
  perspectiva; con el operador, exactamente en cero.
- **D11** Si λ se recorta, la distancia de escape tiene otra fórmula.
- **D12** Si el dipolo mide al menos 1, λ nunca se recorta para notas unitarias.
- **D17** La varianza de las 8 coordenadas crece en la dirección que separa cada coordenada de su
  media; es lo que dice cómo cambia la fricción al mover el punto.
- **D18** Cuánto cambia el tiempo de fricción de la ruta al mover su punto medio: la fórmula que
  usa la búsqueda del camino más rápido.
- **D19** A lo largo de una ruta el tiempo de fricción solo crece, así que el punto que la parte en
  dos mitades de igual tiempo existe y es único.
- **D20** El tiempo de fricción de un tramo recto es su longitud por la fricción media a lo largo
  de él; se sabe cómo cambia al mover cualquiera de sus extremos, y partir el tramo no cambia el
  total.
- **D21** Donde el camino más rápido por el punto medio tiene sus dos mitades iguales, las dos
  hiperesferas de tiempo de fricción, una alrededor del inicio y otra del final, se tocan y
  comparten el plano tangente en ese punto (el camino de dos tramos hace allí un vértice, así que
  ese plano no es la dirección del camino).
- **D22** Si la penalización del mérito solo crece, el mérito final queda acotado por el inicial
  más lo que añadió cada subida de la penalización: es lo que comprueba que la búsqueda bajó.
- **D23** Cerca de la cuerda, al mover el punto medio en paralelo a ella la diferencia de tiempo
  entre las dos patas solo crece, así que el punto donde se igualan es único. «Cerca» es un tubo
  cuyo radio depende solo de la longitud de la cuerda.
- **D24** Con el punto medio ajustado para que las dos patas tarden lo mismo, el tiempo total solo
  depende del desplazamiento perpendicular a la cuerda, y su gradiente se anula justo donde se
  tocan las dos hiperesferas: buscar sin restricción en 7 dimensiones encuentra los mismos puntos
  que D21.
- **D25** Cuántas vecinas reales de cada nota (su hiperesfera en el espacio completo, la misma en
  cualquier vista) conserva el zoom cerca de ella en pantalla, a todas las escalas: 1 si las
  conserva todas, 0 de media para un zoom que no sabe nada (vista y orden al azar). Una vista
  pequeña no llega a 1 en las escalas grandes, porque la hiperesfera entera no cabe en ella.
- **D26** Si el inicio está en la diagonal y el final se aparta de ella en perpendicular, ningún
  punto medio mejora el de la ruta recta: es el mundo sintético donde la respuesta se sabe de
  antemano.

Verified by the `instrument-auditor` subagent (maths only), 2026-09-18, at `e2f6d70`: D9 defect
(count vs. fraction) and missing conditions in D1, D2, D4, D6, D7, D10; D11, D12, the D8 tie form
and the tolerance rule added from its report.
