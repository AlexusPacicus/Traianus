# Z — three-point zoom against a two-point benchmark

The question, hypothesis and refuters live in the RefApp-01 repository (`ZOOM.md`), which a blind
reviewer never opens (definitions.md, Not allowed).

## Instrument audit record (revision 4)

```
Instrument audit — Z1 (neighbourhoods kept along a zoom) and Z2 (zoom latency) (revision 4)

Scope: two arms that zoom from the barycentre to a note by different routes, each judged at the
  start, the middle and the end of its route. Z1 measures how many of each displayed note's 15
  nearest 384-d neighbours stay among its 15 nearest on the displayed plane; Z2 measures compute
  time in this script (numpy, one thread), not the client's end-to-end latency. Not measured:
  colour, legibility, anything shown while the camera moves, and the smooth curve a client may
  draw through the three points (see Routes).
Symbols used here, chosen not to collide with definitions.md: S and E the search's objective and
  constraint; ν the rounding bound; ω₁ ≥ ω₂ ≥ … eigenvalues; κ the column of Z1; Γ the Gram array;
  X_E the EVAL matrix; N_f the number of displayed frames; N_boot the number of bootstrap
  resamples; L a block length.
Script: tools/experiments/zoom_three_point.py; unit tests: tests/unit/test_zoom_three_point.py;
  the tests of D17, D19, D20, D21 and D22 in tests/unit/test_audit_derivations.py. The script sets
  OMP_NUM_THREADS = OPENBLAS_NUM_THREADS = VECLIB_MAXIMUM_THREADS = 1 itself, before its first
  numpy import. It imports, and does not copy, check_digests, load_inputs and validate_inputs from
  tools/experiments/k6_colour_predictability.py (reviewed code); after the import it hashes the
  file the module was loaded from (module.__file__) and refuses to run unless its sha256 =
  6289c596792154f6bb799606265c68719c6b8c7ae8b69084116dfb23c77876d2. Declared limits: this checks
  the file on disk, not the bytes the interpreter loaded (a stale bytecode cache is not seen); the
  "read once, hash and parse the same bytes" rule of contracts.md §0 cannot apply to an imported
  module; and importing it runs its top-level code, which sets the thread variables again (to the
  same values) and imports traianus.geometry.polar_projector, which the pin does not cover and the
  three imported functions do not use. Result: data/refapp/Z_result.json, committed.
Data: definitions.md (2,221 vectors, 8-axis basis). The script refuses to run, writing no result,
  unless sha256(embeddings.npy) = eafb0e97172830f2404e96fa08d74bf6cccc0b6cbe84d47b790a476603e7d8d1,
  sha256(labels.json) = 1d60699353d810f089730c6203ee28f9c416e3004b60781bc965cec284097f4f and
  sha256(tests/fixtures/nsm_axes_8.json) =
  b14e5d6700d1a7478a357ca26f0f38f5240f97a42daad45722d21f1c3f964e35 hold, and unless
  validate_inputs accepts the inputs (contracts.md §0, null elimination). Conversions as
  contracts.md §0: rows cast to float64 and renormalised; â_k = a_k / ‖a_k‖. FIT = even indices
  (1,111), EVAL = odd indices (1,110): everything fitted (barycentre, T, cells) uses FIT notes
  only; every displayed and judged note, and every target, is an EVAL note.
Space: axis coordinates c(v) = (⟨v, â_1⟩, …, ⟨v, â_8⟩) ∈ ℝ⁸. Barycentre p₀ = mean over FIT of c.
  Friction factor f(c) = 1 + Var(c), Var the population variance of the 8 components (ddof = 0).
  Declared: the engine applies the same factor to the stored axis vectors — its caller builds B_0
  from the geodetic matrix (traianus/app.py:619-622) and compute_kinetic_resistance
  (traianus/geometry/observables.py:77-92) uses B_0's rows as given — while this record uses â_k;
  the eight ‖a_k‖ are reported, so the difference has a size.
Friction-time along a straight leg (D20): τ_seg(P, Q) = ‖Q − P‖ ∫₀¹ √f(P + s(Q − P)) ds, computed
  with the 64 Gauss–Legendre nodes and weights of numpy.polynomial.legendre.leggauss(64) mapped to
  [0, 1] (128 in the quadrature control only). Rounding bound, for 64 nodes and evaluated at the
  current route: ν = γ₂₅₆ · max(1, C²) · τ, γ_m = m·u / (1 − m·u), u = ε/2,
  ε = np.finfo(np.float64).eps, C the largest absolute axis coordinate among the route's
  quadrature points, τ the route's total. Count, to first order, per node: Var, with the rounding
  of the node's coordinates and of their mean, has an absolute error of about 38u·C²; the
  subtraction c_k − c̄ can cancel, so the bound is written against C² and not against Var, and
  f ≥ 1 turns it into a relative error of f; the square root, the leg length (one norm of 8
  components per leg) and the products bring the relative error of a node's term to about
  (19·max(1, C²) + 72)u. The sum of 64 positive terms adds γ₆₃ (Higham, Accuracy and Stability of
  Numerical Algorithms, 2nd ed., §4.2): about (19·max(1, C²) + 135)u in all, below
  256·max(1, C²)·u for every C. An upper bound, not a tight one. The errors of the two legs, e_A
  and e_B, satisfy |e_A + e_B| ≤ ν and |e_A − e_B| ≤ ν, so S and E below each carry at most ν, and
  a comparison between two evaluations of either uses 2ν.
Targets: every q in EVAL, in index order (1,110 zooms). Each zoom goes from A = p₀ to B = c(q).
  A target with ‖B − A‖ = 0 is excluded and counted (no route); the smallest ‖B − A‖ over targets
  is reported.
Routes (the only difference between the arms):
  two-point (benchmark): the segment A → B. Its middle is its τ-midpoint m₀ = A + t*(B − A), with
    τ_seg(A, m₀) = τ_seg(A, B)/2: bisection on t ∈ [0, 1] keeping the invariant
    τ_seg(A, A + lo(B − A)) < τ_seg(A, B)/2 ≤ τ_seg(A, A + hi(B − A)), from lo = 0, hi = 1, until
    hi − lo ≤ ε; t* = (lo + hi)/2. The exact τ along the segment is strictly increasing (D19); the
    quadrature estimate may depart from monotone by its own error, which the quadrature control
    covers.
  three-point: two straight legs A → m → B, with m ∈ ℝ⁸ free (author, 2026-09-24): m is where two
    friction-time hyperspheres of equal radius, one around A and one around B, touch. Written as:
    minimise S(m) = τ_seg(A, m) + τ_seg(m, B) subject to E(m) = τ_seg(A, m) − τ_seg(m, B) = 0; at a
    local solution the gradients of the two legs' τ are parallel, so the two level sets share their
    tangent hyperplane at m (D21; they touch from outside when the multiplier |μ| < 1, from inside
    when |μ| > 1; μ is reported and |μ| ≥ 1 counted). That hyperplane is not the route's direction:
    the two-leg route has a corner at m. What identifies m: S alone is constant along the whole
    segment AB (additivity, D20) — every point of it gives the same route — but E is not: on the
    segment ⟨∇E, u⟩ = 2√f > 0 (u the unit chord, D21), so the constraint picks one point there, and
    off the segment each m gives a different route. The route may bend to either side of the
    bisector of A and B. τ-equidistance holds by the constraint, so m is also the τ-midpoint of its
    own route (D20 additivity, D19). A client may draw a smooth curve through A, m and B — the
    author's Pos(t) = mix(A, B, t) + 4t(1 − t)(m − (A + B)/2), with the easing s(t) = 3t² − 2t³ —
    but τ and every judged state are computed on the two legs, not on that curve.
  Search for m: local sequential quadratic programming (Newton on the Lagrange conditions,
    Nocedal and Wright, Numerical Optimization, 2nd ed., §18.1), from m₀ (so the search starts on
    the benchmark route) with multiplier μ = 0. Gradients ∇S and ∇E by D20 on the 64 nodes of each
    leg. Hessian W of the Lagrangian S − μE by central differences of its gradient, step
    h = ε^{1/3} · ‖B − A‖ per coordinate (the problem's length scale; ibid. §8.1), used as the
    representable h′ = (m_j + h) − m_j; symmetrised. Null-space basis Z_N: the last 7 columns of
    the complete Q of numpy.linalg.qr(∇E/‖∇E‖ as an 8 × 1 matrix, mode="complete"). Step: the
    solution p of the KKT system [W, −∇E; ∇Eᵀ, 0][p; Δμ] = [−(∇S − μ∇E); −E] when it is
    nonsingular and Z_Nᵀ W Z_N is positive definite (a Cholesky factorisation succeeds); otherwise
    the fallback p = −(I − ĝĝᵀ)∇S − ĝ·E/‖∇E‖, ĝ = ∇E/‖∇E‖ (a descent step on S within the
    constraint's tangent plane, plus the step that restores the constraint to first order:
    ∇Eᵀp = −E), with Δμ = 0. If ‖∇E‖ = 0 at an iterate, the search stops and fails
    search_converged (it cannot restore the constraint).
  Merit and penalty: φ_ρ(m) = S(m) + ρ|E(m)|, with ρ non-decreasing over the search:
    ρ_k = max(ρ_{k−1}, |μ + Δμ| + 1) after a KKT step and
    ρ_k = max(ρ_{k−1}, |μ| + 1, |∇Sᵀ∇E|/‖∇E‖² + 1) after a fallback step; ρ_1 set by the first step
    alone. ρ > |μ + Δμ| is what makes φ an exact penalty (ibid. §18.3); ρ > |∇Sᵀ∇E|/‖∇E‖² makes the
    fallback a descent direction for φ when E ≠ 0 (its directional derivative is
    −‖(I − ĝĝᵀ)∇S‖² − (∇Sᵀĝ)·E/‖∇E‖ − ρ|E|); the +1 is a declared margin. The rounding bound of φ is
    (1 + ρ)ν.
  Step length: before each line search the directional derivative Dφ = ∇Sᵀp − ρ|E| is checked;
    Dφ ≥ 0 is a code error and fails search_descent. Backtracking from α = 1, halving; a step is
    accepted iff φ(m + αp) ≤ φ(m) + 1e-4 · α · Dφ (Armijo, ibid. Algorithm 3.1; the textbook's
    default constant, declared). The halving stops once α · |Dφ| ≤ 2(1 + ρ)ν: below that a change of
    φ is rounding, and the search ends there ("noise floor").
  Stop: every stop requires |E| ≤ 2ν — the τ-equidistance that makes m the middle — or it fails
    search_converged. Stops: (a) decrement: Z_Nᵀ W Z_N positive definite and the predicted decrease
    ½ p_Nᵀ W p_N ≤ 2ν, p_N = Z_N Z_Nᵀ p (the Newton decrement of an equality-constrained problem,
    Boyd and Vandenberghe, Convex Optimization, §10.2); (b) noise floor (above); (c) the cap of 100
    iterations, a guard, which fails search_converged. m is therefore the local solution the search
    reaches from m₀, fixed only up to changes worth less than 2(1 + ρ)ν; S need not be convex (each
    leg's integrand is a product of positive convex functions of m), so it is not claimed to be the
    global one. Reported per target: iterations, the stop kind, |E| and the projected gradient
    ‖Z_Nᵀ(∇S − μ∇E)‖ at the stop, the final decrement, μ, the final ρ, and whether Z_Nᵀ W Z_N was
    positive definite at the stop (counted when not: such a stop may be a saddle).
States, the same definition in both arms:
  start: P = A. middle: P = m₀ (benchmark) or m (three-point). end: P = B.
  If the search ends at m = m₀, the two arms coincide and D_q = 0 for that target.
Notes in view, one Voronoi level per state. The dominant attractor of a note, of q or of a point
  is argmax_k of its axis coordinates, ties to the lower axis index. For the middle P, the argmax
  margin (first minus second largest coordinate) is reported per target and arm next to
  2‖αp‖∞ of the search's last accepted step (the size of its last move in the same coordinate
  units); targets whose margin is below it are counted, since their cell could depend on the
  search's residual.
  start (level 0): all notes.
  middle (level 1): the axis cell of P, k* = its dominant attractor; in view, the notes whose
    dominant attractor is k* (FIT for fitting, EVAL for display).
  end (level 2): inside q's axis cell, a centroidal Voronoi partition of that cell's FIT notes
    around P = c(q). T_cell = ½ Σ (c_i − P)(c_i − P)ᵀ over them; its eigenvectors from
    numpy.linalg.eigh, ordered by eigenvalue descending, e₁…e₈; 16 starting sites in the order +e₁,
    −e₁, +e₂, −e₂, …, +e₈, −e₈; first assignment of each FIT note to the site with the largest
    ⟨c_i − P, s⟩ (ties: lower site index). Then, repeatedly: empty cells are dropped, each site
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
  plane follows the basis eigh returns: κ is still scored there, and such states are counted.
Column "κ" (Z1), per target, arm and state: M = the EVAL notes in view. A state is scored iff it
  is not degenerate and |M| ≥ 16; otherwise it is counted per arm and state. For each j in M: its
  15 nearest in 384-d among M \ {j} (largest ⟨v_j, v_i⟩ from one Gram array Γ = X_E X_Eᵀ over the
  EVAL rows; ties by lower index) and its 15 nearest on the displayed plane among M \ {j}
  (Euclidean; ties by lower index); recall(j) = the size of their intersection, 0–15.
  κ = mean over j in M of recall(j). k = 5 and 50 reported only on states with |M| ≥ k + 1; the
  others counted.
Statistic (Z1): D_q = κ_middle(q, three-point) − κ_middle(q, two-point), over the targets whose
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
  arms_share_start_end: for every target, the start states of the two arms are equal and so are
    the end states — same notes in view and the same coordinates bit for bit, or both degenerate.
  identity: at the start state, the recall function applied to the 384-d vectors themselves as
    the "displayed" coordinates (Euclidean on unit vectors orders as the dot product, D5) gives 15
    for every note. A swapped pair counts as a tie iff both notes' similarities lie within 1e-12
    of the 15th-place similarity. The worst-case float64 error of a 384-term dot product of unit
    vectors is γ₃₈₄ ≈ 4.3e-14, and the Euclidean side adds rounding of the same order, so 1e-12
    leaves a margin of ≈ 10–20× (not more); ties are reported. Any other mismatch fails.
  permutation: at the start state (M = all 1,110 EVAL notes), each note's displayed neighbour list
    replaced by the first 15 entries of rng.permutation(1109) indexed into M \ {j} in index order,
    scored by the same recall function: the mean must lie in [0.149, 0.257]. Expected
    225/1109 = 0.2029, per-note s.d. ≈ 0.445 (hypergeometric, D9), s.d. of the mean over 1,110
    notes ≈ 0.0133; ± 4 s.d., widened to those bounds: a correct recall function falls outside
    with probability ≈ 6e-5.
  quadrature: the found m is kept (no new search); m₀, the benchmark's middle state, the two legs'
    τ, |E(m)| and the projected gradient ‖Z_Nᵀ(∇S − μ∇E)‖ at m are recomputed with 128 nodes; then
    D_q and the Z1 decision at every L, reusing the same bootstrap draws. Passes iff the set of
    targets scored in both arms is unchanged and the Z1 decision is the same at every L; targets
    whose k* or κ change are counted, and |E(m)| and the projected gradient at 128 nodes are
    reported. A decision, not a figure, is compared, so no tolerance is needed.
Code check: merit_bound: for every target, φ_{ρ_K}(m) ≤ φ_{ρ_1}(m₀) + Σ_{k=2}^{K} (ρ_k − ρ_{k−1}) ·
  |E(m_{k−1})| + 2(1 + ρ_K)ν (D22, with the rounding of the two evaluations compared); a failure is
  a code error, not a measurement. τ₂ = τ_seg(A, B) and τ₃ = S(m) are reported.
Z2 (latency), per target with a route, on the three-point route with the m found above.
  time.perf_counter_ns; the timer overhead (the median of 1,000 empty timed calls) subtracted from
  every timing and timestamp difference. Warm-up: the first 10 EVAL targets run once, search and
  both arms, untimed and discarded; then every target is timed. N_f = 60 displayed frames at
  t_f = f/(N_f − 1), f = 0, …, N_f − 1, evenly spaced in t without easing (a 1-second zoom at 60
  frames per second; both choices declared: easing would change which frames fall before the
  middle). On the three-point route t ∈ [0, ½] runs linearly along A → m and t ∈ [½, 1] along
  m → B, so the middle is at t = ½.
  search: the bisection for m₀ and the search for m, re-run in the timed pass; it must reproduce
    the m of the Z1 pass bit for bit (search_reproduced). Timed once per target and shared: both
    arms start after it.
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
    configuration and thread settings are recorded; the decision holds for that machine only.
Validity, checked in this order, every failure listed: search_converged (every target);
  search_descent (every target); lloyd_converged (every target); n_scored (Z1's n ≥ 20 and Z2's
  n ≥ 20); arms_share_start_end; identity; permutation; merit_bound; quadrature;
  search_reproduced. Any failure: valid = false, and neither Z1 nor Z2 is decided. Counts
  reported: targets excluded (no route), degenerate states and states not scored per arm and
  state, states with a near-zero eigenvalue gap, searches that stopped with Z_Nᵀ W Z_N not
  positive definite, stops by kind, |μ| ≥ 1, middle cells decided inside the last move.
Reported, not deciding: κ per arm and state (mean over targets); per L used, D̄, the interval and
  the margins of its bounds to 0, n and n_blocks(L); the middle cells k* per arm and their argmax
  margins; τ₂, τ₃ and their ratio; t*; ‖m − m₀‖; the search diagnostics above; the eigenvalue
  gaps; Lloyd iterations and cells per end state; the leading direction of T at the start state
  (the corpus's dominant spread seen through the axes); the eight ‖a_k‖; the smallest ‖B − A‖;
  k = 5 and 50; for Z2, the median of Δ_q and the 95th percentile of ready with their intervals
  per L and their margins (to 0 and to 100 ms), and the timer overhead.
Draws: rng = numpy.random.default_rng(20260924) (PCG64; this record overrides the seed of
  contracts.md §0, as its contract will state), in this order and nowhere else: for each EVAL note
  in index order, rng.permutation(1109) (permutation control); then, for Z1, for each L used in
  ascending order and b = 1…N_boot, rng.integers(0, n_blocks(L), n_blocks(L)); then the same loop
  twice for Z2 with its n, first for the median of Δ, then for the 95th percentile of ready. The
  quadrature control reuses Z1's draws and draws nothing.
Unit tests (committed with the script, reviewed in phase 2; they can fail). In
  tests/unit/test_audit_derivations.py: D17, D19, D20, D21 and D22, each on random inputs
  satisfying its conditions and with a negative case, tolerances by derivations.md's rule; D20's
  gradients against central finite differences, its additivity on a split leg and its radial
  rate; D21 on a synthetic friction whose touching point is known. In
  tests/unit/test_zoom_three_point.py, for the search: (i) a search that does not work must fail —
  with A and B off the diagonal, where m₀ is not a solution (∇S(m₀) has a component in the null
  space of ∇E), the search must end with S(m) < S(m₀) − 2(1 + ρ)ν, |E(m)| ≤ 2ν and a projected
  gradient within the tolerance rule; a search that returns its input fails this test; (ii) the
  same through D21's synthetic friction, injected in the test, from its own m₀, ending at the
  known touching point; (iii) the known answer where m₀ is the solution — with A = a·1 and
  B = b·1 every point of the segment has Var = 0, so f = 1 there, and for m off the segment the
  sum of the two legs grows (one leg can be shorter; their sum cannot) with f ≥ 1, so m₀ is the
  unique solution and the search must end at it; (iv) search_descent fires on a gradient with its
  sign flipped; (v) ρ never decreases, and merit_bound holds along a recorded search and fails when
  a step is forced to raise φ; (vi) every stop has |E| ≤ 2ν, and a stop without it fails
  search_converged. Also: the bisection's invariant and output; the first assignment and the
  Lloyd iteration on a hand-built cell with a known answer, including a tie that must keep its
  current cell; degenerate states written as null; notes in view never include a FIT note and
  fitting never uses an EVAL note; a note j never appears in its own neighbour lists; recall ties
  by lower index; the block counts and the L filter by n; the first three entries of the first
  permutation from seed 20260924 match values recorded in the test; the timer overhead is
  subtracted; the arms' interleaving order; search_reproduced; that each control can fail —
  identity with a recall that counts j among its own neighbours, permutation with an off-by-one
  index, arms_share_start_end with an arm-dependent start, quadrature with a changed decision;
  file-layer integrity per contracts.md §0 — a single-bit flip at the header, the first and the
  last data byte and a random position of each of the three data files and of the K6 module's
  file is refused, writing nothing. The memory-layer cases are those of the imported
  validate_inputs, covered by tests/unit/test_k6_colour_predictability.py; one test checks that
  this script calls it (a NaN row is refused before writing).

Same thing in every arm?   Both arms share targets, space, friction factor, quadrature, the state
                           definitions, the level rule, T, the display and the recall function;
                           they differ only in the route (the segment against the two legs through
                           the searched m), hence in the middle state's point and possibly its
                           cell. Z2's two arms share the route, the search and the level-2
                           partition, and differ only in how the N_f frames are produced.
Leakage?                   Barycentre, T and cells are fitted on FIT; displays and neighbours are
                           EVAL only; no label is read. FIT and EVAL are disjoint but not
                           independent (adjacent chunks of one text in both halves). The route
                           depends on the target q through B = c(q), in both arms alike.
Comparable arms?           Valid only if every condition in Validity holds. Z1 can only differ at
                           the middle: start and end are shared by construction, and the control
                           checks it. Z2's keyframes arm computes 3 states against the per-step
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
                           2026-09-24; phase 1 (specification), round 3 of 3; commit aa89b67
                           (revision 3); CHANGES, 2 blocking, 15 non-blocking; record frozen for
                           phase 1, items carried to phase 2, verdict open; D20–D21 verified.
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
