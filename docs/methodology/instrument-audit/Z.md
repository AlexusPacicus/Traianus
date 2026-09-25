# Z — three-point zoom against a two-point benchmark

The question, hypothesis and refuters live in the RefApp-01 repository (`ZOOM.md`), which a blind
reviewer never opens (definitions.md, Not allowed).

## Instrument audit record (revision 5)

```
Instrument audit — Z1 (neighbourhood kept along a zoom) and Z2 (zoom latency) (revision 5)

Scope: two arms that zoom from the barycentre to a note by different routes, each judged at the
  start, the middle and the end of its route. Z1 measures, for each displayed note, how much of its
  real neighbourhood — its nearest notes in 384-d among all EVAL notes, at every scale — the zoom
  keeps nearest to it on the displayed plane, against a zoom with no information (D25); Z2
  measures compute time in this script (numpy, one thread), not the client's end-to-end latency.
  Not measured: colour, legibility, anything shown while the camera moves, and the smooth curve a
  client may draw through the three points (see Routes).
Symbols used here, chosen not to collide with definitions.md: S and E the search's objective and
  constraint; u the unit chord, as in D21–D26 (the unit roundoff is written ε/2); ν the rounding
  bound of a route's τ, ν_g that of the search's objective; ω₁ ≥ ω₂ ≥ … eigenvalues; Γ the Gram
  array; X_E the EVAL matrix; U the EVAL notes, N_U = 1,110; M the EVAL notes in view, N_M of them;
  N_f the number of displayed frames; N_boot the number of bootstrap resamples; L a block length;
  o_j a coordinate vector; σ a Voronoi site; β the known world's scale.
Script: tools/experiments/zoom_three_point.py; unit tests: tests/unit/test_zoom_three_point.py;
  the tests of D17, D19, D20, D21, D23, D24, D25 and D26 in tests/unit/test_audit_derivations.py.
  The script sets OMP_NUM_THREADS = OPENBLAS_NUM_THREADS = VECLIB_MAXIMUM_THREADS = 1 itself,
  before its first numpy import. It imports, and does not copy, check_digests, load_inputs and
  validate_inputs from tools/experiments/k6_colour_predictability.py (reviewed code); after the
  import it hashes the file the module was loaded from (module.__file__) and refuses to run unless
  its sha256 = 6289c596792154f6bb799606265c68719c6b8c7ae8b69084116dfb23c77876d2. Declared limits:
  this checks the file on disk, not the bytes the interpreter loaded (a stale bytecode cache is not
  seen); the "read once, hash and parse the same bytes" rule of contracts.md §0 cannot apply to an
  imported module; and importing it runs its top-level code, which sets the thread variables again
  (to the same values) and imports traianus.geometry.polar_projector, which the pin does not cover
  and the three imported functions do not use. Result: data/refapp/Z_result.json, committed.
Data: definitions.md (2,221 vectors, 8-axis basis). The script refuses to run, writing no result,
  unless sha256(embeddings.npy) = eafb0e97172830f2404e96fa08d74bf6cccc0b6cbe84d47b790a476603e7d8d1,
  sha256(labels.json) = 1d60699353d810f089730c6203ee28f9c416e3004b60781bc965cec284097f4f and
  sha256(tests/fixtures/nsm_axes_8.json) =
  b14e5d6700d1a7478a357ca26f0f38f5240f97a42daad45722d21f1c3f964e35 hold, and unless
  validate_inputs accepts the inputs (contracts.md §0, null elimination). Conversions as
  contracts.md §0: rows cast to float64 and renormalised; â_k = a_k / ‖a_k‖. FIT = even indices
  (1,111), EVAL = odd indices (1,110): everything fitted (barycentre, T, cells) uses FIT notes
  only; every displayed and judged note, every note's neighbourhood, and every target, is an EVAL
  note. None of this is read before the known world (Controls, null_world) has passed.
Space: axis coordinates c(v) = (⟨v, â_1⟩, …, ⟨v, â_8⟩) ∈ ℝ⁸. Barycentre p₀ = mean over FIT of c.
  Friction factor f(c) = 1 + Var(c), Var the population variance of the 8 components (ddof = 0).
  Declared: the engine applies the same factor to the stored axis vectors — its caller builds B_0
  from the geodetic matrix (traianus/app.py:619-622) and compute_kinetic_resistance
  (traianus/geometry/observables.py:77-92) uses B_0's rows as given — while this record uses â_k;
  the eight ‖a_k‖ are reported, so the difference has a size. Declared likewise: the engine's
  dominant attractor (traianus/app.py:282-285, :551-554) is the argmax of ⟨v, a_k⟩ over the stored,
  unnormalised axis vectors, a tie going to the first key in the matrix's iteration order; this
  record uses â_k and the lower axis index (States).
Friction-time along a straight leg (D20): τ_seg(P, Q) = ‖Q − P‖ ∫₀¹ √f(P + s(Q − P)) ds, computed
  with the 64 Gauss–Legendre nodes and weights of numpy.polynomial.legendre.leggauss(64) mapped to
  [0, 1] (128 in the quadrature control only). Rounding bound, for 64 nodes and evaluated at the
  current route: ν = γ₂₅₆ · max(1, C²) · τ, γ_m = m(ε/2) / (1 − m(ε/2)),
  ε = np.finfo(np.float64).eps, C the largest absolute axis coordinate among the route's
  quadrature points, τ the route's total. Count, to first order, per node: Var, with the rounding
  of the node's coordinates and of their mean, has an absolute error of about 19ε·C²; the
  subtraction c_k − c̄ can cancel, so the bound is written against C² and not against Var, and
  f ≥ 1 turns it into a relative error of f; the square root, the leg length (one norm of 8
  components per leg) and the products bring the relative error of a node's term to about
  (19·max(1, C²) + 72)·ε/2. The sum of 64 positive terms adds γ₆₃ (Higham, Accuracy and Stability
  of Numerical Algorithms, 2nd ed., §4.2): about (19·max(1, C²) + 135)·ε/2 in all, below
  128·max(1, C²)·ε for every C. An upper bound, not a tight one. The errors of the two legs, e_A
  and e_B, satisfy |e_A + e_B| ≤ ν and |e_A − e_B| ≤ ν, so S and E below each carry at most ν.
Targets: every q in EVAL, in index order (1,110 zooms). Each zoom goes from A = p₀ to B = c(q),
  d = ‖B − A‖. A target with d = 0 is excluded and counted (no route); the smallest d over targets
  is reported. d < 4√2 is D23's condition; |c_k| ≤ 1 gives d ≤ 4√2, and a target with d ≥ 4√2
  fails tube_defined (a code or data error).
Routes (the only difference between the arms): both use the same line and the same bisection.
  u = (B − A)/d; Z_N = the last 7 columns of the complete Q of numpy.linalg.qr(u as an 8 × 1
  matrix, mode="complete"), an orthonormal basis of u⊥, fixed per target. For z ∈ ℝ⁷ the line
  ℓ_z(t) = A + t(B − A) + Z_N z. mid(z): bisection on t ∈ [0, 1] keeping the invariant
  E(ℓ_z(lo)) < 0 ≤ E(ℓ_z(hi)), from lo = 0, hi = 1, until hi − lo ≤ ε; t = (lo + hi)/2,
  mid(z) = ℓ_z(t). E(m) = τ_seg(A, m) − τ_seg(m, B) (D21).
  two-point (benchmark): the segment A → B, with middle m₀ = mid(0). On the segment E < 0 exactly
    where τ_seg(A, ·) < τ_seg(A, B)/2 (D20 additivity), so m₀ is the segment's τ-midpoint, unique
    (D19); the quadrature estimate may depart from monotone by its own error, which the quadrature
    control covers.
  three-point: two straight legs A → m → B, with m ∈ ℝ⁸ free (author, 2026-09-24): m is where two
    friction-time hyperspheres of equal radius, one around A and one around B, touch. Written as:
    minimise S(m) = τ_seg(A, m) + τ_seg(m, B) subject to E(m) = 0; at a local solution the
    gradients of the two legs' τ are parallel, so the two level sets share their tangent
    hyperplane at m (D21; they touch from outside when the multiplier |μ| < 1, from inside when
    |μ| > 1). That hyperplane is not the route's direction: the two-leg route has a corner at m.
    S alone does not identify m (it is constant along the whole segment AB, D20 additivity); the
    constraint does (on the segment ⟨∇E, u⟩ = 2√f > 0, D21), and off the segment each m gives a
    different route, which may bend to either side of the bisector of A and B. τ-equidistance
    holds by the constraint, so m is also the τ-midpoint of its own route (D20 additivity, D19).
    A client may draw a smooth curve through A, m and B — the author's
    Pos(t) = mix(A, B, t) + 4t(1 − t)(m − (A + B)/2), with the easing ease(t) = 3t² − 2t³ — but τ and
    every judged state are computed on the two legs, not on that curve.
  Search for m (revision 5): every point it visits satisfies E = 0 by construction, so it is a
    search without constraint over z.
    Domain, the tube (D23): ‖z‖ ≤ h_max(d) = (4√2 − d)·√(d/(8√2 − d)), and E(ℓ_z(0)) < 0 ≤
    E(ℓ_z(1)). Inside it the zero of E on each line in [0, 1] is unique (D23); the second condition
    is its existence, which D23 does not give. z = 0 is inside (E(A) = −τ_seg(A, B) < 0 < E(B)).
    The tube is where the search can guarantee its answer, not part of m's definition: a search
    that ends against its edge fails search_converged (below), and h/h_max = ‖z‖/h_max(d) at the
    found m is reported per target.
    Objective g(z) = S(mid(z)), both legs on the 64 nodes. Gradient (D24): ∇g = Z_Nᵀ(∇S − μ̂∇E),
    μ̂ = ⟨∇S, u⟩/⟨∇E, u⟩, at mid(z), with ∇S and ∇E by D20 on the same nodes (the exact gradients
    of the 64-node τ). ⟨∇E, u⟩ > 0 in the domain (D23): a computed value ≤ 0 fails search_code.
    The critical points of g are D21's Lagrange points, with μ = μ̂ (D24); μ̂ is reported and
    |μ̂| ≥ 1 counted.
    Rounding of g at the current z: ν_g = (1 + |μ̂|)·ν + ½·|⟨∇S, u⟩|·d·ε. Count, to first order: S
    at the computed point carries ν; the bisection's signs are right wherever |E| > ν, so the
    computed point lies on its line within ½·d·ε (half its last interval) of a point where |E| ≤ ν;
    moving along u to the exact zero changes S by −μ̂·E (D24, first order), at most
    |μ̂|·ν + ½·|⟨∇S, u⟩|·d·ε. A comparison between two evaluations of g uses 2ν_g.
    Hessian H of g: central differences of ∇g with step h = ε^{1/3}·d per coordinate (the problem's
    length scale; Nocedal and Wright, Numerical Optimization, 2nd ed., §8.1), taken as the
    representable h₊ = (z_j + h) − z_j and h₋ = z_j − (z_j − h): column j =
    (∇g(z + h₊o_j) − ∇g(z − h₋o_j))/(h₊ + h₋), o_j the j-th coordinate vector; then symmetrised. A difference point outside the
    domain means the search is at the edge: it fails search_converged.
    Iteration, from z = 0 (so the search starts on the benchmark's middle), each step in this
    order: (1) at z: mid(z), g, ∇g and H. (2) Stop: H positive definite (a Cholesky factorisation
    succeeds) and the Newton decrement ½∇gᵀH⁻¹∇g ≤ 2ν_g/(1 − 2c₁), c₁ = 10⁻⁴: converged (Boyd and
    Vandenberghe, Convex Optimization, §9.5.1). (3) Direction: p = −H⁻¹∇g if H is positive
    definite, otherwise p = −∇g; Dg = ∇gᵀp is negative for either unless ∇g = 0. ∇g = 0 with H not
    positive definite is a critical point not certified as a minimum: it fails search_converged.
    Dg ≥ 0 otherwise is a code error: it fails search_code. (4) Step length: from α = 1, halving;
    a trial z + αp is rejected when it leaves the domain or fails Armijo,
    g(z + αp) ≤ g(z) + c₁·α·Dg (Nocedal and Wright, Algorithm 3.1; c₁ is the textbook's default,
    declared); the first trial that passes is the step. The halving ends at α·|Dg| ≤ 2ν_g, below
    which a change of g is rounding: that floor stop fails search_converged. A search that works
    stops at (2) first: at a Newton step the computed change of g is −½∇gᵀH⁻¹∇g, plus the
    quadratic model's remainder, plus at most 2ν_g of rounding, so above (2)'s bound the full step
    passes Armijo unless the remainder exceeds the margin — and near a minimum the remainder is of
    third order in the step. (5) A cap of 100 iterations, a guard: reaching it fails
    search_converged.
    m = mid(z) at the stop, and |E(m)| ≤ ν + ½·⟨∇E, u⟩·d·ε holds by construction, not by a stop
    rule. m is the local solution the search reaches from m₀; S need not be convex (each leg's
    integrand is a product of positive convex functions of m), so it is not claimed to be the
    global one. Reported per target: iterations, the decrement at the stop, μ̂, h/h_max,
    ⟨∇E, u⟩ and |E(m)| at m, t, the steps that fell back to −∇g, and, for a failed search, why.
States, the same definition in both arms:
  start: P = A. middle: P = m₀ (benchmark) or m (three-point). end: P = B.
  If the search ends at z = 0, m = m₀ bit for bit and D_q = 0 for that target.
Notes in view, one Voronoi level per state. The dominant attractor of a note, of q or of a point
  is argmax_k of its axis coordinates, ties to the lower axis index. For the middle P, the argmax
  margin (first minus second largest coordinate) is reported per target and arm next to the size
  of the last move that fixed P, in the same coordinate units: for the benchmark d·ε (the
  bisection's last interval), for the three-point arm the larger of d·ε and ‖Z_N αp‖∞ of the
  search's last accepted step (d·ε when it took none); targets whose margin is below it are
  counted, since their cell could depend on that residual.
  start (level 0): all notes.
  middle (level 1): the axis cell of P, k* = its dominant attractor; in view, the notes whose
    dominant attractor is k* (FIT for fitting, EVAL for display).
  end (level 2): inside q's axis cell, a centroidal Voronoi partition of that cell's FIT notes
    around P = c(q). T_cell = ½ Σ (c_i − P)(c_i − P)ᵀ over them; its eigenvectors from
    numpy.linalg.eigh, ordered by eigenvalue descending, e₁…e₈; 16 starting sites in the order +e₁,
    −e₁, +e₂, −e₂, …, +e₈, −e₈; first assignment of each FIT note to the site σ with the largest
    ⟨c_i − P, σ⟩ (ties: lower site index). Then, repeatedly: empty cells are dropped, each site
    moves to the mean of its notes, and every FIT note moves to the nearest mean (Euclidean),
    keeping its current cell on a tie; until no note changes cell. From the first mean step on,
    every change strictly lowers the within-cell sum of squares and the partitions are finitely
    many, so the iteration terminates; a cap of 1,000 iterations is kept as a guard (reaching it
    fails lloyd_converged). The EVAL notes of q's axis cell are then assigned to the nearest final
    mean (ties: lower mean index); in view, q's cell. If q's axis cell holds no FIT note, the end
    state is degenerate (below).
Frame at a state: T = ½ Σ (c_i − P)(c_i − P)ᵀ over the FIT notes in view; e₁, e₂ its two leading
  eigenvectors (eigh, eigenvalues descending, ω₁ ≥ ω₂ ≥ …). A state is degenerate when it has
  fewer than 2 FIT notes in view (T is centred at P, so two notes can already span a plane) or
  ω₂ ≤ 8ε · ω₁ (8ε the scale of eigh's backward error on an 8 × 8 matrix): it has no frame, is not
  scored, and every figure it would produce is written as null (never NaN, which contracts.md §0's
  result format forbids). Otherwise the displayed coordinates of an EVAL note j in view are
  (⟨c_j − P, e₁⟩, ⟨c_j − P, e₂⟩), and the relative gap (ω₂ − ω₃)/ω₁ is reported; below 8ε the
  plane follows the basis eigh returns: the state is still scored there, and such states are
  counted.
Z1's score (D25), per target, arm and state. A state is scored iff it is not degenerate and
  N_M ≥ 2 (D25's condition); otherwise it is counted per arm and state. For each j in M and
  K = 1, …, N_U − 2 = 1,108: ν_j(K) = its K nearest in 384-d among U \ {j} (largest ⟨v_j, v_i⟩
  from one Gram array Γ = X_E X_Eᵀ over the EVAL rows; ties by lower index) — j's hypersphere, the
  same in both arms and at every state; K′ = min(K, N_M − 1); n_j(K) = its K′ nearest on the
  displayed plane among M \ {j} (Euclidean; ties by lower index); O_j(K) = |ν_j(K) ∩ n_j(K)|;
  r_j(K) = (O_j(K)/K − K′/(N_U − 1)) / (1 − K′/(N_U − 1)); R_NX(K) = the mean over j in M of
  r_j(K); the state's score AUC = [Σ_K R_NX(K)/K] / [Σ_K 1/K]. It is 1 when the zoom keeps every
  note's hypersphere in order, 0 on average for a zoom with no information (a random view shown
  in a random order, D25), and below 0 when the zoom does worse than that. It judges the whole
  zoom: a view that cuts a note's real neighbours off scores lower even with a perfect display,
  and a view of fewer than K + 1 notes cannot reach 1 at scale K. The weights 1/K count every
  scale factor about alike (1–10 weighs about as much as 10–100); a uniform weight would give
  nearly all the weight to the largest neighbourhoods.
Statistic (Z1): D_q = AUC_middle(q, three-point) − AUC_middle(q, two-point), over the targets whose
  middle state is scored in both arms. At the start and at the end both arms have the same P and
  the same notes in view by construction, so their displays must be identical (control below) and
  no difference is computed there.
Dependence between targets: EVAL alternates chunks of a sequential text, so nearby targets share
  neighbourhoods and their D_q are correlated. Block bootstrap over the n targets scored in both
  arms, in EVAL index order, cut into ⌈n / L⌉ contiguous blocks of that filtered list (the last
  may be shorter; a block can join chunks that are not adjacent in the text, declared). Grid
  L ∈ {1, 2, 5, 10, 20, 50}: L = 1 is independence; 50 is the largest value of the 1-2-5 grid that
  leaves at least 20 blocks at n = 1,110 (23). Twenty blocks is a declared minimum (with fewer
  resampling units a percentile interval tends to undercover): only the L with ⌈n / L⌉ ≥ 20 are
  used. N_boot = 10,000 resamples per L; D̄_b = mean of D_q over the targets of the drawn blocks,
  with multiplicity.
Rule (Z1): for each L used, interval = [sorted(D̄_b)[249], sorted(D̄_b)[9749]]. Z1 refuted iff the
  upper bound < 0 at every L; the three-point route keeps more iff the lower bound > 0 at every L;
  otherwise inconclusive. The rank of a 2.5% or 97.5% quantile has Monte Carlo s.d.
  √(10,000 · 0.025 · 0.975) ≈ 15.6 ranks, so sorted[233], [265], [9733] and [9765] are reported to
  show whether a decision hinges on Monte Carlo noise.
Controls (Z1):
  null_world, run first, before the real data are read: the whole pipeline — targets, search,
    states, score, bootstrap, rule and Z1's other controls — on a synthetic corpus built in memory
    by formula, with no draws, where D26 fixes the answer. o_k is the k-th coordinate vector of
    ℝ³⁸⁴, and the axes are â_k = o_k (k = 1…8). For each unordered pair {p, q} of axis indices (28)
    and each β ∈ {0.1, 0.2, 0.3}, four notes in this order: FIT (p, q, β), EVAL (p, q, β),
    FIT (q, p, β), EVAL (q, p, β), where (p, q, β) has axis coordinates c = 0.1·1 + β(o_p − o_q)
    and vector v = Σ_k c_k o_k + √(1 − ‖c‖²)·o_{8+i}, i the note's position (1…336), so ‖v‖ = 1
    and the parts beyond the axes are orthogonal between notes. FIT = even positions (168),
    EVAL = odd (168). Each mirror pair (p, q, β), (q, p, β) lies in the same half, so the FIT
    barycentre is 0.1·1, on the diagonal, and every target has B − A orthogonal to it: by D26 m₀
    is the only answer, for every target. The values 0.1 and β only make the notes distinct with
    ‖c‖ < 1; any values meeting D26's conditions give the same expected result. Expected: every
    search stops at (2) at z = 0 with no step, so every D_q is exactly 0; every middle state is
    scored (its cell holds the 21 EVAL notes that share the target's leading axis); Z1 is
    inconclusive at every L used; tube_defined, search_converged, search_code, lloyd_converged,
    Z1's n_scored, arms_share_start_end, identity, permutation and quadrature hold. Z2 and
    search_reproduced are not run there: a clock is never deterministic. Its draws come from its
    own generator (Draws), so the real run's draws are untouched. Any other outcome:
    valid = false, and the real data are not read.
  arms_share_start_end: for every target, the start states of the two arms are equal and so are
    the end states — same notes in view and the same coordinates bit for bit, or both degenerate.
  identity: at the start state (M = U), the score applied to the 384-d vectors themselves as the
    "displayed" coordinates (Euclidean on unit vectors orders as the dot product, D5) gives
    r_j(K) = 1 for every note and scale (D25 (a)). A note out of order counts as a tie iff its
    similarity to j and that of the note it swapped with lie within 1e-12 of each other. The
    worst-case float64 error of a 384-term dot product of unit vectors is γ₃₈₄ ≈ 4.3e-14, and the
    Euclidean side adds rounding of the same order, so 1e-12 leaves a margin of ≈ 10–20× (not
    more); ties are reported. Any other mismatch fails.
  permutation: at the start state (M = U), each note's display order replaced by
    rng.permutation(1109) indexed into U \ {j} in index order, scored by the same function: the
    AUC must lie in ±4/√(N_U(N_U − 2)) = ±0.003607. By D25 (b) its mean is 0 and its variance at
    most 1/(N_U(N_U − 2)), the notes' permutations being independent; with the normal
    approximation over 1,110 independent notes, a correct score falls outside with probability
    below ≈ 6e-5 (the variance is an upper bound, so the true probability is lower).
  quadrature: the found m is kept (no new search); m₀ = mid(0), the benchmark's middle state, the
    two legs' τ, |E(m)| and ∇g at m are recomputed with 128 nodes; then D_q and the Z1 decision at
    every L, reusing the same bootstrap draws. Passes iff the set of targets scored in both arms is
    unchanged and the Z1 decision is the same at every L; targets whose k* or score change are
    counted, and |E(m)| and ‖∇g‖ at 128 nodes are reported. A decision, not a figure, is compared,
    so no tolerance is needed.
Z2 (latency), per target with a route, on the three-point route with the m found above.
  time.perf_counter_ns; the timer overhead (the median of 1,000 empty timed calls) subtracted from
  every timing and timestamp difference. Warm-up: the first 10 EVAL targets run once, search and
  both arms, untimed and discarded; then every target is timed. N_f = 60 displayed frames at
  t_f = f/(N_f − 1), f = 0, …, N_f − 1, evenly spaced in t without easing (a 1-second zoom at 60
  frames per second; both choices declared: easing would change which frames fall before the
  middle). On the three-point route t ∈ [0, ½] runs linearly along A → m and t ∈ [½, 1] along
  m → B, so the middle is at t = ½.
  search: the search for m, whose first step computes m₀ = mid(0), re-run in the timed pass; it
    must reproduce the m of the Z1 pass bit for bit (search_reproduced). Timed once per target and
    shared: both arms start after it.
  keyframes: the three states (notes in view, T, display; level 2 includes its Lloyd partition),
    a timestamp once the third state exists, then the N_f frames: a frame with t_f ≤ ½ interpolates
    between the start and middle displays with weight w = 2t_f, one with t_f > ½ between the middle
    and end displays with w = 2t_f − 1; position (1 − w)·x_prev + w·x_next for the EVAL notes in
    both displays, and, for a note in only one of the two, the position it has in that one.
  per-step: the same level-2 partition, computed and timed in this arm too; then at each frame the
    notes in view, T and the display recomputed from scratch at the route's point P(t_f): level 0
    while t_f < ½; level 1, the axis cell of the current P, while ½ ≤ t_f < 1; level 2 at t_f = 1.
  One timed call per arm per target; the arms interleaved per target, keyframes first at even
    positions of EVAL order and per-step first at odd positions, so drift affects both alike.
  Statistics: Δ_q = time_keyframes(q) − time_per-step(q), paired per target; ready(q) =
    time_search(q) + the keyframes arm's time up to its timestamp. Medians by numpy.median (the
    mean of the two middle values for an even count), percentiles by numpy.percentile with its
    default (linear) method. The median of Δ_q and the 95th percentile of ready are each
    block-bootstrapped over the n targets with a route, as for Z1 (same grid and ⌈n / L⌉ ≥ 20
    filter, N_boot = 10,000, their own draws, intervals [249] and [9749]).
  Rule (Z2): refuted iff, at every L used, the lower bound of the median-Δ interval ≥ 0
    (keyframes not faster), or iff, at every L used, the lower bound of the ready-p95 interval
    > 100 ms. Otherwise, confirmed (keyframes faster, and fast enough) iff at every L used the
    upper bound of the median-Δ interval < 0 and the upper bound of the ready-p95 interval
    ≤ 100 ms. Otherwise inconclusive. The 100 ms is the author's choice, the response-time limit
    for an instantaneous feel usually attributed to Miller (1968) and Nielsen (Usability
    Engineering, 1993), citations not verified; the 95th percentile is a declared choice. ready is
    compute only, so meeting 100 ms is necessary, not sufficient, for the client. Machine, numpy
    configuration and thread settings are recorded; the decision holds for that machine only. The
    known world does not decide Z2: a clock is never deterministic.
Validity, checked in this order, every failure listed: null_world; tube_defined (every target);
  search_converged (every target); search_code (every target); lloyd_converged (every target);
  n_scored (Z1's n ≥ 20 and Z2's n ≥ 20); arms_share_start_end; identity; permutation; quadrature;
  search_reproduced. Any failure: valid = false, and neither Z1 nor Z2 is decided. Counts
  reported: targets excluded (no route), degenerate states and states not scored per arm and
  state, states with a near-zero eigenvalue gap, failed searches by reason, steps that fell back
  to −∇g, |μ̂| ≥ 1, middle cells decided inside the last move.
Reported, not deciding: the score per arm and state (mean over targets); per L used, D̄, the
  interval and the margins of its bounds to 0, n and n_blocks(L); the middle cells k* per arm,
  N_M per arm, the targets whose middle cells differ and D̄ over those whose cells agree; per
  target scored in both arms, the scales K where R_NX(K) of the three-point middle minus that of
  the benchmark's changes sign (where one route starts keeping more than the other), summarised
  over targets; the middle cells' argmax margins; τ₂ = τ_seg(A, B), τ₃ = S(m) and their ratio; t;
  ‖m − m₀‖; h/h_max; the search diagnostics above; the eigenvalue gaps; Lloyd iterations and
  cells per end state; the leading direction of T at the start state (the corpus's dominant
  spread seen through the axes); the eight ‖a_k‖; the smallest d; for Z2, the median of Δ_q and
  the 95th percentile of ready with their intervals per L and their margins (to 0 and to 100 ms),
  and the timer overhead.
Draws: rng = numpy.random.default_rng(20260924) (PCG64; this record overrides the seed of
  contracts.md §0, as its contract will state), in this order and nowhere else: for each EVAL note
  in index order, rng.permutation(1109) (permutation control); then, for Z1, for each L used in
  ascending order and b = 1…N_boot, rng.integers(0, n_blocks(L), n_blocks(L)); then the same loop
  twice for Z2 with its n, first for the median of Δ, then for the 95th percentile of ready. The
  quadrature control reuses Z1's draws and draws nothing. The known world has its own generator,
  numpy.random.default_rng(20260925), for its permutation control (rng.permutation(167) for each
  of its 168 EVAL notes) and then its Z1 bootstrap, in the same order.
Unit tests (committed with the script, reviewed in phase 2; they can fail). In
  tests/unit/test_audit_derivations.py: D17, D19, D20, D21, D23, D24, D25 and D26, each on inputs
  satisfying its conditions and with a negative case, tolerances by derivations.md's rule; D20's
  gradients against central finite differences, its additivity, reversal and radial rate; D21 on
  a synthetic friction whose touching point is known; D23's slope on random parallels inside the
  tube, and h_max against its closed form; D24's gradient against finite differences of g
  computed through the bisection; D25 (b) exactly, by enumerating every arrangement for small N_U
  and N_M (no draws), and D25 (a) with a view smaller than K + 1; D26 on random chords
  orthogonal to the diagonal. In tests/unit/test_zoom_three_point.py, for the search: (i) a search
  that does not work must fail — with A and B off the diagonal, where m₀ is not a solution
  (∇g(0) ≠ 0), the search must end at (2) with g(z) < g(0) − 2ν_g; a search that returns its
  input fails this test; (ii) through D21's synthetic friction, injected in the test, from its
  own m₀, ending within √(2b/ω_min(H)) of the known touching point, b the bound of (2) — the
  distance to the minimum that the decrement allows; (iii) the known answers where m₀ is the
  solution, which the search must return with no step — A and B on the diagonal (f = 1 on the
  segment, ≥ 1 elsewhere, and the sum of the two legs grows off it) and B − A orthogonal to the
  diagonal from A on it (D26); (iv) search_code fires on a gradient with its sign flipped and on a forced
  ⟨∇E, u⟩ ≤ 0; (v) mid(0) is the τ-midpoint of the segment, the bisection keeps its invariant, and
  the two arms' middles are equal bit for bit when the search takes no step; (vi) a trial outside
  the tube, or on a line without a sign change, is rejected; a search forced against the tube's
  edge, a floor stop, and a critical point with H not positive definite each fail
  search_converged. For the score: the definition against a direct count on hand-built views,
  including ties by lower index and a view smaller than K + 1; the crossing scales on hand-built
  curves. Also: the first assignment and the Lloyd iteration on a hand-built cell with a known
  answer, including a tie that must keep its current cell; degenerate states written as null;
  notes in view never include a FIT note and fitting never uses an EVAL note; a note j never
  appears in its own neighbour lists; the block counts and the L filter by n; the first three
  entries of the first permutation from seeds 20260924 and 20260925 match values recorded in the
  test; the timer overhead is subtracted; the arms' interleaving order; search_reproduced; the
  known world's corpus meets D26's conditions and its null_world passes, and fails with an
  arm-dependent search; that each control can fail — identity with a score that counts j among
  its own neighbours, permutation with an off-by-one index, arms_share_start_end with an
  arm-dependent start, quadrature with a changed decision; tube_defined with d ≥ 4√2; file-layer
  integrity per contracts.md §0 — a single-bit flip at the header, the first and the last data
  byte and a random position of each of the three data files and of the K6 module's file is
  refused, writing nothing. The memory-layer cases are those of the imported validate_inputs,
  covered by tests/unit/test_k6_colour_predictability.py; one test checks that this script calls
  it (a NaN row is refused before writing).

Same thing in every arm?   Both arms share targets, space, friction factor, quadrature, the line
                           and its bisection, the state definitions, the level rule, T, the display
                           and the score, with each note's hypersphere the same in both; they
                           differ only in the route (the segment against the two legs through the
                           searched m), hence in the middle state's point and possibly its cell.
                           Z2's two arms share the route, the search and the level-2 partition, and
                           differ only in how the N_f frames are produced.
Leakage?                   Barycentre, T and cells are fitted on FIT; displays, neighbourhoods and
                           hyperspheres are EVAL only; no label is read. FIT and EVAL are disjoint
                           but not independent (adjacent chunks of one text in both halves). The
                           route depends on the target q through B = c(q), in both arms alike.
Comparable arms?           Valid only if every condition in Validity holds. Z1 can only differ at
                           the middle: start and end are shared by construction, and the control
                           checks it. When the middle cells differ, both arms are still judged
                           against the same hyperspheres over all EVAL notes and at the same
                           scales (D25). Z2's keyframes arm computes 3 states against the per-step
                           arm's N_f by design; the comparison asks whether the interpolation eats
                           that saving, and the 100 ms bound whether the search and the three
                           states are fast enough.
Text matches code?         Checked at review (phase 2).
Reviewed by:               instrument-auditor (blind subagent, review package built at be7a611),
                           2026-09-24; phase 1 (specification), round 1 of 3; commit be7a611
                           (revision 1); CHANGES, 3 blocking, 16 non-blocking; D17–D19 verified.
                           instrument-auditor (blind subagent, review package built at c44725f),
                           2026-09-24; phase 1 (specification), round 2 of 3; commit c44725f
                           (revision 2); PASS, 0 blocking, 14 non-blocking; round-1 items
                           addressed.
                           instrument-auditor (blind subagent, review package built at aa89b67),
                           2026-09-24; phase 1 (specification), round 3; commit aa89b67
                           (revision 3); CHANGES, 2 blocking, 15 non-blocking; D20–D21 verified.
                           Under the rule then in force the record froze and carried its items to
                           phase 2; the rule amended in e54261c counts rounds per design, so this
                           was round 1 on revision 3's design, and its blocking items kept the
                           record in phase 1.
                           instrument-auditor (blind subagent, review package built at 9307b04),
                           2026-09-24; phase 1 (specification), round 4 (round 2 of 3 on
                           revision 3's design); commit 9307b04 (revision 4); CHANGES, 2 blocking,
                           10 non-blocking; round-3 blocking items resolved; D22 verified.
                           Revision 5 changes the search's design and Z1's score (the author,
                           2026-09-25): its review is round 1 of 3 on that design.
```

## Review history

- **Revision 1** — `instrument-auditor` subagent, blind by construction (package built from
  `be7a611`, lock set), 2026-09-24, phase 1, round 1: **CHANGES**, 3 blocking, 16 non-blocking;
  D17–D19 verified. Blocking: (1) the search's stopping rule and cap are not derived and rounding
  decides them — the objective is exactly flat along D = s(B − A), |s| ≤ ¼ (τ is a length, so a
  change of speed along the chord leaves it unchanged), so the minimising D is not identified and
  steepest descent is ill-conditioned there, and the Armijo test drops below τ's rounding long
  before the ε step rule can stop it; (2) Z2's arms are not fully specified (whether per-step
  computes t* and the level-2 partition, the level-1 view per frame, the keyframe schedule and
  interpolation weights, execution order, timing granularity, warm-up targets) and the median
  comparison has zero margin and no treatment of timing noise; (3) the quadrature control re-runs
  the rounding-decided search, leaves the repeat's draws unspecified and demands identity with no
  derived tolerance. Non-blocking: tie rules for dominant attractors; Lloyd's site order, empty
  cells, the EVAL notes assigned, and ties that can make it cycle; the bisection's output; the
  descent check is a code check; near-zero eigenvalue gaps; small n in the bootstrap; the 1e-12
  tie tolerance and Monte Carlo ranks restated; the seed as an override of contracts.md §0; the
  engine's K_cin evidence is its caller (app.py:619-622), with the axes' norms to report; missing
  reported margins and search diagnostics; the 100 ms citations unverified and compute-only;
  k = 5 and 50 when |M| is small; unit tests (bit flips, negative cases, D18's known answers);
  D19's redundant condition; and, outside Z, contracts.md §0's binary32 wording against the freeze
  script, and review packages that include prior results (data/refapp/*_result.json).
  Addressed in revision 2: (1) D restricted to (B − A)⊥, which removes the flat direction and puts
  the route's parameter midpoint on the plain bisector (the author's λ = 0); Newton with a
  finite-difference Hessian, stopped at τ₆₄'s rounding bound δ = γ₁₂₈·τ₆₄ (derived) or when no step
  beats δ, cap 100 as a guard; (2) Z2 rewritten: the search timed once and shared, t* and the
  level-2 partition in both arms, the level-1 view per frame, the keyframe schedule and weights,
  one timed call per arm, interleaving, warm-up targets, and a paired statistic with a block
  bootstrap of the median difference; (3) the quadrature control re-evaluates at the found D with
  the same draws and compares decisions. Every non-blocking item addressed in place; §0's wording
  corrected in contracts.md; the packaging item is a tooling change, tracked separately.
- **Revision 2** — `instrument-auditor` subagent, blind by construction (package built from
  `c44725f`, lock set), 2026-09-24, phase 1, round 2: **PASS**, 0 blocking, 14 non-blocking; every
  round-1 item addressed. The reviewer disclosed that its session context held the user's memory
  index, which states outcomes of other records (R4, R5), nothing about Z. Non-blocking, to fix
  before phase 2 (items 6 and 8 before any code): (1) D ⊥ (B − A) restricts the search to arcs
  symmetric about the bisector, not only the flat direction — declare it, and that "λ" here is the
  bisector plane in ℝ⁸, not definitions.md's λ; (2) τ₆₄ is not guaranteed convex: D is the local
  minimiser reached from w = 0, and a stop with H not positive definite needs its own report;
  (3) the backtracking needs a floor, and δ against a difference of two evaluations may be 2δ;
  report the middle's argmax margin; (4) δ derived for n = 64 only, with the cancellation argument
  written; (5) the Hessian step should scale with ‖B − A‖; (6) empty or degenerate cells (no FIT
  notes, T = 0, a NaN gap) undefined; (7) the tie tolerance's margin is ≈ 10–20× (γ₃₈₄), not
  1,000×; (8) Z2 details — the ready timestamp, whether the timed search re-runs Z1's, the
  warm-up, Z2's n and the n_scored scope, median and percentile methods, three outcomes;
  (9) no noise treatment for ready's 95th percentile; (10) Z2's frames evenly spaced in t,
  without easing; (11) hash the imported K6 module's own file and set the thread variables before
  numpy; (12) tests that each control can fail, a known-answer test for the search, an entry for
  τ(s(B − A)) = τ(0), and a wording fix; outside Z, (13) contracts.md §0's engine-path paragraph
  is stale after b3be386 (the engine normalises in binary32; its citations moved to
  app.py:204-205 and :273-274); (14) the package still carries prior results.
- **Changes in revision 3** — the author's design change after round 2, and every round-2 item.
  Item 1 showed that the constraint D ⊥ (B − A) did more than remove the flat direction: it
  confined the three-point arm to arcs symmetric about the bisector of A and B. The author chose
  to free it: the middle point m is where two friction-time hyperspheres of equal radius, around A
  and around B, touch — found by derivatives (the Lagrange condition, D21) — and the route is the
  two straight legs A → m → B (τ along a leg, D20). The unknown is a point, so there is no flat
  direction and the route may bend to either side; m is τ-equidistant by the constraint. The
  parabola and D18 left the measured route (D18 stays as a verified entry); the author's curve
  survives as what a client may draw, not measured. Round-2 items: (2) local solution from m₀,
  non-positive-definite stops reported and counted; (3) a backtracking floor at 2δ, 2δ for
  comparisons, the middle's argmax margin reported; (4) δ derived for 64 nodes at the current
  route, with the cancellation handled through C²; (5) the Hessian step scaled by ‖B − A‖, the
  smallest ‖B − A‖ reported; (6) degenerate states defined (fewer than 3 FIT notes in view or
  λ₂ = 0), written as null; (7) the tie margin corrected to ≈ 10–20×; (8) Z2: the ready timestamp
  inside the keyframes call, the timed search re-runs and must reproduce m (search_reproduced),
  the warm-up, Z2's own n and n_scored for both, numpy's median and percentile methods, three
  outcomes; (9) the 95th percentile of ready block-bootstrapped with its own draws; (10) frames
  evenly spaced in t without easing, declared; (11) the K6 module's own file hashed after import,
  the limit declared, the thread variables set by the script before numpy; (12) tests that each
  control can fail, the search's known answer, D20's additivity instead of the parabola's
  flat-direction identity, and "a note j" in the wording; (13) contracts.md §0's engine-path
  paragraph corrected (outside Z); (14) the packaging item stays tracked separately. This revision
  changes the three-point arm, so it goes back to a blind phase-1 review (round 3 of 3).
- **Revision 3** — `instrument-auditor` subagent, blind by construction (package built from
  `aa89b67`, lock set), 2026-09-24, phase 1, round 3 of 3: **CHANGES**, 2 blocking, 15
  non-blocking; D20–D21 verified; round-2 items addressed except 13 (contracts.md cites app.py one
  line early). Third round: the record freezes for phase 1 and the items carry to phase 2, verdict
  open. Blocking: (1) no check can fail for a search that does not work — a noise-floor stop is
  valid whatever |G|, an ascent step ends silently at the floor (the halving tests an absolute
  value), merit descent and search_reproduced pass for a search that never moves, and the
  known-answer test starts at its own answer: a search returning m₀ gives D_q = 0 everywhere and
  passes every check; (2) φ is not one function — ρ is recomputed per iteration and can fall, so
  the code check can fail for a correct search; the noise floor is derived for F, not φ (whose
  rounding is (1 + ρ)δ); and the fallback's ρ need not make its step a descent direction.
  Non-blocking: the stated reason for "no flat direction" (F is constant on the whole segment; the
  constraint removes it); D21's wording (star-shaped level sets, internal tangency |μ| > 1,
  ‖∇G‖ = 0, the tangent hyperplane is not the route's direction); which acceptance test decides a
  step; the argmax margin in coordinate units against a residual in τ units; δ's itemisation
  understates the count (the bound still holds); the degenerate-state test (a tolerance for
  λ₂ = 0; two notes span a plane); name collisions (F, G, B, λ, δ, L, V); the quadrature control
  barely re-examines m; "both legs longer" should be "the sum grows"; the representable
  finite-difference step and the null-space basis; notes present in only one display; the K6
  import's side effects; D19's wording at the joint; outside Z, contracts.md:72 one line early and
  the prior results still packaged.
- **Changes in revision 4** — the author did not accept carrying blocking items into code (the
  review of revision 3 was the third round, but on a redesigned arm), and made it a rule in
  METHODOLOGY.md: rounds count per design, and a blocking item never passes to phase 2. So the
  record stays in phase 1 and goes to a fourth round. Blocking (1): every stop now requires
  |E| ≤ 2ν or fails search_converged; the directional derivative of the merit is checked before
  each line search (Dφ ≥ 0 fails search_descent); the acceptance test is Armijo on a negative Dφ,
  and the halving floor only ends the search; unit tests where a search that does not work must
  fail (m₀ not a solution, A and B off the diagonal; D21's synthetic friction; a flipped gradient),
  besides the known answer where m₀ is the solution. Blocking (2): ρ is non-decreasing, with the
  code check against D22's bound (new), noise floors of 2(1 + ρ)ν (φ's rounding), and the
  fallback's ρ large enough to make it a descent direction. Non-blocking: the reason S does not
  identify m (constant on the segment; E does, with ⟨∇E, u⟩ = 2√f > 0 there); D21 rewritten (μ ≠ ±1,
  external and internal tangency with μ reported and |μ| ≥ 1 counted, star-shaped level sets from
  D20's radial rate, ‖∇E‖ = 0 stops the search, the hyperplane is not the route's direction; also
  corrected in ZOOM.md); one acceptance test; the argmax margin compared with the last move in the
  same units; δ renamed ν and its count written out, which needed γ₂₅₆ instead of γ₁₂₈ once the
  summation is included; degenerate states at fewer than 2 FIT notes or ω₂ ≤ 8ε·ω₁; symbols renamed
  (S, E, ν, ω, κ, Γ, X_E, N_f, N_boot; D20's leg Λ); the quadrature control also re-examines the
  projected gradient at m; "the sum grows"; the representable finite-difference step and the
  null-space basis named; notes in one display keep that display's position; the K6 import's side
  effects declared; D19's wording at the joint; contracts.md's app.py citation moved to :273-274.
  The packaging item stays tracked separately.
- **Revision 4** — `instrument-auditor` subagent, blind by construction (package built from
  `9307b04`, lock set), 2026-09-24, phase 1, round 4 (round 2 of 3 on revision 3's design):
  **CHANGES**, 2 blocking, 10 non-blocking; both round-3 blocking items resolved; D22 verified.
  Blocking, both introduced by the fix: (1) the stop rules do not reach |E| ≤ 2ν — the decrement
  of stop (a) falls below its bound about one iteration before |E| does (after a KKT step E is of
  second order in the step), so a working search would fail search_converged; the noise floor of
  stop (b) can end the search with |E| up to 2(1 + ρ)ν / (ρ − |μ + Δμ|); the order of the stop
  test and the Dφ check is unstated (Dφ = 0 at a stationary point would fire search_descent on a
  correct search); 2ν on |E| is not derived; (2) Dφ = ∇Sᵀp − ρ|E| has no derivations.md entry,
  and nothing makes it negative for the KKT step: Dφ ≤ −pᵀWp − (ρ − |μ + Δμ|)|E|, and positive
  definiteness on the null space does not control pᵀWp once E ≠ 0. Non-blocking: first-order
  stationarity is reported but not bounded, and test (i)'s tolerance must come from the stop
  rule; κ's chance level is 225/(|M| − 1), so when the middle cells differ between the arms D_q
  mixes in a difference of chance levels (report |M| per arm, the targets with different k*, D̄ on
  equal k*; whether to correct for chance is the author's decision before code); merit_bound's ν,
  a search with no step, the benchmark's margin, D22's unneeded condition; symbols still
  colliding (u, s, M, k); the finite-difference step's backward point; the engine's dominant
  attractor uses unnormalised axes and dict order (declare, as for friction); D20 and D21 wording
  (leg reversal, the radial rate's proof); the round-3 entry describes the superseded rule; outside
  Z, definitions.md cites _storage.py:114 for geodesic_axes (created at :123), and the package
  still carries prior results.
- **Changes in revision 5** — the author's design change after round 4 (2026-09-25). The search
  had blocking items in three rounds, all from carrying the constraint and the objective at once,
  so the author made the design the question (METHODOLOGY.md, as amended in e54261c). The new
  search keeps every point it visits on E = 0 by construction: m on a line parallel to the chord,
  fixed by the same bisection as the benchmark's middle (both arms now call one function, so
  m₀ = mid(0) and a search that takes no step reproduces it bit for bit), and a search without
  constraint over the 7 offsets orthogonal to the chord. D23 (new) makes the zero on each line
  unique inside a tube of radius h_max(d); D24 (new) shows that the unconstrained search has
  exactly D21's Lagrange points as critical points, with μ = μ̂, and gives the rounding of its
  objective, ν_g. Newton with a finite-difference Hessian throughout, stopped by its own
  decrement against 2ν_g/(1 − 2c₁); L-BFGS was considered and rejected: a stop by ‖∇g‖ against its
  rounding cannot be reached by a search that compares values of g (it resolves m only to about
  the square root of the rounding), and a Hessian certificate after L-BFGS checks Newton's
  direction, not L-BFGS's. The tube is the search's domain and its validity zone, not part of m's
  definition (the author): trials outside it are rejected, a search against its edge fails, and
  h/h_max is reported. Round-4 blocking items: (1) |E| ≤ ν + ½⟨∇E, u⟩·d·ε holds at every point by
  construction, and the only converged stop is the decrement, with its order in the iteration
  fixed; (2) there is no merit function: the Newton step with H positive definite and the −∇g
  fallback are descent directions by algebra, so φ, ρ, D22 and merit_bound go (D22 stays as a
  verified entry). Z1's score changed (the author): recall@15 inside the cell became D25 (new),
  each note's hypersphere over all EVAL notes at every scale K = 1…1,108, corrected against a zoom
  with no information and averaged with weights 1/K — so the arms are judged against the same
  neighbourhoods and scales even when their middle cells differ, the cut a view makes counts, the
  scoring threshold N_M ≥ 16 (where recall@15 is 15 whatever the display) becomes N_M ≥ 2, and
  the chance level of round 4's N2 is part of the score. The permutation control's bounds are now
  derived (D25 (b)). New: the known world, D26 (new) and the null_world control, run before the
  real data are read; tube_defined. Round-4 non-blocking: first-order stationarity is bounded by
  the stop and test (i)–(ii)'s tolerances come from it; merit_bound, the search with no step and
  D22's condition went with the merit; the benchmark's argmax margin is compared with d·ε;
  symbols (u is the chord only, the unit roundoff written ε/2; the easing is ease(t); sites σ;
  coordinate vectors o_j; U, M and N_M as in D25; k only indexes axes); both finite-difference
  points are representable; the engine's dominant attractor declared (app.py:282-285, :551-554);
  D20 gains its reversal and a direct proof of the radial rate, D21 cites the reversal; the
  round-3 entry now states the rule it was reviewed under; definitions.md's geodesic_axes
  citation moved to _storage.py:123. The packaging item stays tracked separately. This revision
  changes the three-point arm's search and Z1's score, so it goes to a blind phase-1 review as
  round 1 of 3 on its design.
