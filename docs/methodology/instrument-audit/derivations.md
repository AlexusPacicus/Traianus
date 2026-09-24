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

D19 τ(0, t) = ∫₀ᵗ √f(Pos(s)) ‖Pos'(s)‖ ds is continuous and strictly increasing on [0, 1] when
    τ(0, 1) > 0, so t* with τ(0, t*) = τ(0, 1)/2 exists and is unique.
    Conditions: f ≥ 1; Pos affine or quadratic in t with Pos' not identically zero.
    Proof: the integrand is ≥ 0 and is 0 only where Pos'(s) = 0, which happens at most at one s
    (D18's condition); an integral of a function positive except at one point is strictly
    increasing; continuity and the intermediate value theorem give existence.
```

Used by: K6 (D2, D4, D6, D7, D8, D11), R4 (D2, D5, D6, D9, D10), Z (D5, D9, D17, D18, D19).

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

Verified by the `instrument-auditor` subagent (maths only), 2026-09-18, at `e2f6d70`: D9 defect
(count vs. fraction) and missing conditions in D1, D2, D4, D6, D7, D10; D11, D12, the D8 tie form
and the tolerance rule added from its report.
