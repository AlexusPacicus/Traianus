# Z — three-point zoom against a two-point benchmark

The question, hypothesis and refuters live in the RefApp-01 repository (`ZOOM.md`), which a blind
reviewer never opens (definitions.md, Not allowed).

## Instrument audit record (revision 3)

```
Instrument audit — Z1 (neighbourhoods kept along a zoom) and Z2 (zoom latency) (revision 3)

Scope: two arms that zoom from the barycentre to a note by different routes, each judged at the
  start, the middle and the end of its route. Z1 measures how many of each displayed note's 15
  nearest 384-d neighbours stay among its 15 nearest on the displayed plane; Z2 measures compute
  time in this script (numpy, one thread), not the client's end-to-end latency. Not measured:
  colour, legibility, anything shown while the camera moves, and the smooth curve a client may
  draw through the three points (see Routes).
Script: tools/experiments/zoom_three_point.py; unit tests: tests/unit/test_zoom_three_point.py;
  the tests of D17, D19, D20 and D21 in tests/unit/test_audit_derivations.py. The script sets
  OMP_NUM_THREADS = OPENBLAS_NUM_THREADS = VECLIB_MAXIMUM_THREADS = 1 itself, before its first
  numpy import. It imports, and does not copy, check_digests, load_inputs and validate_inputs from
  tools/experiments/k6_colour_predictability.py (reviewed code); after the import it hashes the
  file the module was loaded from (module.__file__) and refuses to run unless its sha256 =
  6289c596792154f6bb799606265c68719c6b8c7ae8b69084116dfb23c77876d2. Declared limit: this checks
  the file on disk, not the bytes the interpreter loaded (a stale bytecode cache is not seen); the
  "read once, hash and parse the same bytes" rule of contracts.md §0 cannot apply to an imported
  module. Result: data/refapp/Z_result.json, committed.
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
  [0, 1] (128 in the quadrature control only). Rounding bound, for n = 64 and evaluated at the
  current route: δ = γ₁₂₈ · max(1, C²) · τ, γ_m = m·(ε/2) / (1 − m·(ε/2)),
  ε = np.finfo(np.float64).eps, C the largest absolute axis coordinate among the route's
  quadrature points, τ the route's total. Derivation: at each node, Var's absolute error is at
  most a few γ₈ · C² (its terms are squares of coordinates of magnitude ≤ C), and f ≥ 1 turns that
  into a relative error of f at most γ₁₆ · max(1, C²) — the subtraction c_k − c̄ can cancel, which
  is why the bound is written against C² and not against Var itself; the square root, the leg
  length (computed once per leg, a norm of 8 components) and the product add at most γ₁₆ more; the
  sum of 64 positive terms adds γ₆₃ (Higham, Accuracy and Stability of Numerical Algorithms, 2nd
  ed., §4.2). γ₁₂₈ covers the total with room. An upper bound, not a tight one. A comparison
  between two evaluations uses 2δ, since each carries δ.
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
    minimise F(m) = τ_seg(A, m) + τ_seg(m, B) subject to G(m) = τ_seg(A, m) − τ_seg(m, B) = 0; at
    a local solution the gradients of the two legs' τ are parallel, so the two level sets share
    their tangent hyperplane (D21). The unknown is the point m, not a curve's coefficient, so each
    m gives a different route: no flat direction, and the route may bend to either side of the
    bisector of A and B. τ-equidistance holds by the constraint, so m is also the τ-midpoint of
    its own route (D20 additivity, D19). A client may draw a smooth curve through A, m and B —
    the author's Pos(t) = mix(A, B, t) + 4t(1 − t)(m − (A + B)/2), with the easing
    s(t) = 3t² − 2t³ — but τ and every judged state are computed on the two legs, not on that curve.
  Search for m: local sequential quadratic programming (Newton on the Lagrange conditions,
    Nocedal and Wright, Numerical Optimization, 2nd ed., §18.1), from m₀ (so the search starts on
    the benchmark route) with multiplier μ = 0. Gradients ∇F and ∇G by D20 on the 64 nodes of each
    leg. Hessian W of the Lagrangian F − μG by central differences of its gradient, step
    ε^{1/3} · ‖B − A‖ per coordinate (the problem's length scale; ibid. §8.1), symmetrised. Step:
    the solution p of the KKT system [W, −∇G; ∇Gᵀ, 0][p; Δμ] = [−(∇F − μ∇G); −G] when it is
    nonsingular and W is positive definite on the null space of ∇Gᵀ (checked by a Cholesky
    factorisation of the reduced matrix); otherwise the fallback
    p = −(I − ĝĝᵀ)∇F − ĝ·G/‖∇G‖, ĝ = ∇G/‖∇G‖ (a descent step on F within the constraint's tangent
    plane plus the step that restores the constraint to first order), and Δμ = 0. Step length:
    backtracking from 1, halving, on the ℓ1 merit φ = F + ρ|G| with ρ = |μ + Δμ| + 1 (ibid. §18.3;
    ρ > |μ| is required, the +1 a declared margin), sufficient-decrease constant 1e-4 (ibid.,
    Algorithm 3.1; the textbook's default, declared); the halving stops once
    α · |∇Fᵀp − ρ|G|| ≤ 2δ, and if no step lowers φ by more than 2δ the search ends there (below 2δ
    a change is rounding, not geometry).
  Stop: when |G| ≤ 2δ and, with W positive definite on the null space, the predicted decrease
    ½ p_Nᵀ W p_N ≤ 2δ, p_N the part of p in that null space (the Newton decrement of an
    equality-constrained problem, Boyd and Vandenberghe, Convex Optimization, §10.2); or when no
    step beats 2δ (above). m is therefore the local solution the search reaches from m₀, fixed
    only up to changes worth less than 2δ; F need not be convex (each leg's integrand is a product
    of positive convex functions of m), so it is not claimed to be the global one. Cap: 100
    iterations, a guard; reaching it fails search_converged. Reported per target: iterations,
    |G| at the stop, the final decrement, how the search ended (decrement, noise floor, cap), and
    whether W was positive definite on the null space at the stop (counted when not: such a stop
    may be a saddle).
States, the same definition in both arms:
  start: P = A. middle: P = m₀ (benchmark) or m (three-point). end: P = B.
  If the search ends at m = m₀, the two arms coincide and D_q = 0 for that target.
Notes in view, one Voronoi level per state. The dominant attractor of a note, of q or of a point
  is argmax_k of its axis coordinates, ties to the lower axis index; the argmax margin (first
  minus second largest coordinate) of the middle P is reported per target and arm, so a cell
  decided inside the search's 2δ residual shows up.
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
  eigenvectors (eigh, eigenvalues descending, λ₁ ≥ λ₂ ≥ …). A state is degenerate when it has
  fewer than 3 FIT notes in view or λ₂ = 0: it has no frame, is not scored, and every figure it
  would produce is written as null (never NaN, which contracts.md §0's result format forbids).
  Otherwise the displayed coordinates of an EVAL note j in view are (⟨c_j − P, e₁⟩, ⟨c_j − P, e₂⟩),
  and the relative gap (λ₂ − λ₃)/λ₁ is reported; below 8ε, the scale of eigh's backward error on
  an 8 × 8 matrix, the plane follows the basis eigh returns: V is still scored there, and such
  states are counted.
Column "V" (Z1), per target, arm and state: M = the EVAL notes in view. A state is scored iff it
  is not degenerate and |M| ≥ 16; otherwise it is counted per arm and state. For each j in M: its
  15 nearest in 384-d among M \ {j} (largest ⟨v_j, v_i⟩, one Gram array G = V Vᵀ over EVAL; ties by
  lower index) and its 15 nearest on the displayed plane among M \ {j} (Euclidean; ties by lower
  index); recall(j) = the size of their intersection, 0–15. V = mean over j in M of recall(j).
  k = 5 and 50 reported only on states with |M| ≥ k + 1; the others counted.
Statistic (Z1): D_q = V_middle(q, three-point) − V_middle(q, two-point), over the targets whose
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
  used. B = 10,000 resamples per L; D̄_b = mean of D_q over the targets of the drawn blocks, with
  multiplicity.
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
    τ and |G(m)| are recomputed with 128 nodes; then D_q and the Z1 decision at every L, reusing
    the same bootstrap draws. Passes iff the set of targets scored in both arms is unchanged and
    the Z1 decision is the same at every L; targets whose k* or V change are counted, and |G(m)| at
    128 nodes is reported. A decision, not a figure, is compared, so no tolerance is needed.
Code check: merit descent: φ(m) ≤ φ(m₀) for every target (the search starts at m₀ and accepts
  only steps that lower φ), a failure is a code error; τ₂ = τ_seg(A, B) and τ₃ = F(m) are reported.
Z2 (latency), per target with a route, on the three-point route with the m found above.
  time.perf_counter_ns; the timer overhead (the median of 1,000 empty timed calls) subtracted from
  every timing and timestamp difference. Warm-up: the first 10 EVAL targets run once, search and
  both arms, untimed and discarded; then every target is timed. F = 60 displayed frames at
  t_f = f/(F − 1), f = 0, …, F − 1, evenly spaced in t without easing (a 1-second zoom at 60 frames
  per second; both choices declared: easing would change which frames fall before the middle).
  On the three-point route t ∈ [0, ½] runs linearly along A → m and t ∈ [½, 1] along m → B, so the
  middle is at t = ½.
  search: the bisection for m₀ and the search for m, re-run in the timed pass; it must reproduce
    the m of the Z1 pass bit for bit (search_reproduced). Timed once per target and shared: both
    arms start after it.
  keyframes: the three states (notes in view, T, display; level 2 includes its Lloyd partition),
    a timestamp once the third state exists, then the F frames: a frame with t_f ≤ ½ interpolates
    between the start and middle displays with weight w = 2t_f, one with t_f > ½ between the middle
    and end displays with w = 2t_f − 1; position (1 − w)·x_prev + w·x_next for the EVAL notes in
    both displays, the others kept at their display position.
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
    filter, B = 10,000, their own draws, intervals [249] and [9749]).
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
  lloyd_converged (every target); n_scored (Z1's n ≥ 20 and Z2's n ≥ 20); arms_share_start_end;
  identity; permutation; merit descent; quadrature; search_reproduced. Any failure: valid = false,
  and neither Z1 nor Z2 is decided. Counts reported: targets excluded (no route), degenerate states
  and states not scored per arm and state, states with a near-zero eigenvalue gap, searches that
  stopped with W not positive definite on the null space.
Reported, not deciding: V per arm and state (mean over targets); per L used, D̄, the interval and
  the margins of its bounds to 0, n and n_blocks(L); the middle cells k* per arm and their argmax
  margins; τ₂, τ₃ and their ratio; t*; ‖m − m₀‖; the search diagnostics above; the eigenvalue gaps;
  Lloyd iterations and cells per end state; the leading direction of T at the start state (the
  corpus's dominant spread seen through the axes); the eight ‖a_k‖; the smallest ‖B − A‖; k = 5
  and 50; for Z2, the median of Δ_q and the 95th percentile of ready with their intervals per L
  and their margins (to 0 and to 100 ms), and the timer overhead.
Draws: rng = numpy.random.default_rng(20260924) (PCG64; this record overrides the seed of
  contracts.md §0, as its contract will state), in this order and nowhere else: for each EVAL note
  in index order, rng.permutation(1109) (permutation control); then, for Z1, for each L used in
  ascending order and b = 1…10,000, rng.integers(0, n_blocks(L), n_blocks(L)); then the same loop
  twice for Z2 with its n, first for the median of Δ, then for the 95th percentile of ready. The
  quadrature control reuses Z1's draws and draws nothing.
Unit tests (committed with the script, reviewed in phase 2; they can fail). In
  tests/unit/test_audit_derivations.py: D17, D19, D20 and D21, each on random inputs satisfying its
  conditions and with a negative case, tolerances by derivations.md's rule; D20's gradients against
  central finite differences and its additivity on a split leg; D21 on a synthetic friction whose
  touching point is known. In tests/unit/test_zoom_three_point.py: the search's known answer — with
  A = a·1 and B = b·1 every point of the segment has Var = 0, so f = 1 there and any m off the
  segment makes both legs longer with f ≥ 1: m₀ is the unique solution and the search must end at
  it; the search ends with |G| ≤ 2δ; the bisection's invariant and output; the first assignment and
  the Lloyd iteration on a hand-built cell with a known answer, including a tie that must keep its
  current cell; degenerate states written as null; notes in view never include a FIT note and
  fitting never uses an EVAL note; a note j never appears in its own neighbour lists; recall ties
  by lower index; the block counts and the L filter by n; the first three entries of the first
  permutation from seed 20260924 match values recorded in the test; the timer overhead is
  subtracted; the arms' interleaving order; search_reproduced; that each control can fail — identity
  with a recall that counts j among its own neighbours, permutation with an off-by-one index,
  arms_share_start_end with an arm-dependent start, quadrature with a changed decision; file-layer
  integrity per contracts.md §0 — a single-bit flip at the header, the first and the last data byte
  and a random position of each of the three data files and of the K6 module's file is refused,
  writing nothing. The memory-layer cases are those of the imported validate_inputs, covered by
  tests/unit/test_k6_colour_predictability.py; one test checks that this script calls it (a NaN
  row is refused before writing).

Same thing in every arm?   Both arms share targets, space, friction factor, quadrature, the state
                           definitions, the level rule, T, the display and the recall function;
                           they differ only in the route (the segment against the two legs through
                           the searched m), hence in the middle state's point and possibly its
                           cell. Z2's two arms share the route, the search and the level-2
                           partition, and differ only in how the F frames are produced.
Leakage?                   Barycentre, T and cells are fitted on FIT; displays and neighbours are
                           EVAL only; no label is read. FIT and EVAL are disjoint but not
                           independent (adjacent chunks of one text in both halves). The route
                           depends on the target q through B = c(q), in both arms alike.
Comparable arms?           Valid only if every condition in Validity holds. Z1 can only differ at
                           the middle: start and end are shared by construction, and the control
                           checks it. Z2's keyframes arm computes 3 states against the per-step
                           arm's F by design; the comparison asks whether the interpolation eats
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
- **Revision 3** — the author's design change after round 2, and every round-2 item. Item 1 showed
  that the constraint D ⊥ (B − A) did more than remove the flat direction: it confined the
  three-point arm to arcs symmetric about the bisector of A and B. The author chose to free it: the
  middle point m is where two friction-time hyperspheres of equal radius, around A and around B,
  touch — found by derivatives (the Lagrange condition, D21) — and the route is the two straight
  legs A → m → B (τ along a leg, D20). The unknown is a point, so there is no flat direction and
  the route may bend to either side; m is τ-equidistant by the constraint. The parabola and D18
  left the measured route (D18 stays as a verified entry); the author's curve survives as what a
  client may draw, not measured. Round-2 items: (2) local solution from m₀, non-positive-definite
  stops reported and counted; (3) a backtracking floor at 2δ, 2δ for comparisons, the middle's
  argmax margin reported; (4) δ derived for 64 nodes at the current route, with the cancellation
  handled through C²; (5) the Hessian step scaled by ‖B − A‖, the smallest ‖B − A‖ reported;
  (6) degenerate states defined (fewer than 3 FIT notes in view or λ₂ = 0), written as null;
  (7) the tie margin corrected to ≈ 10–20×; (8) Z2: the ready timestamp inside the keyframes call,
  the timed search re-runs and must reproduce m (search_reproduced), the warm-up, Z2's own n and
  n_scored for both, numpy's median and percentile methods, three outcomes; (9) the 95th
  percentile of ready block-bootstrapped with its own draws; (10) frames evenly spaced in t
  without easing, declared; (11) the K6 module's own file hashed after import, the limit declared,
  the thread variables set by the script before numpy; (12) tests that each control can fail, the
  search's known answer, D20's additivity instead of the parabola's flat-direction identity, and
  "a note j" in the wording; (13) contracts.md §0's engine-path paragraph corrected (outside Z);
  (14) the packaging item stays tracked separately. This revision changes the three-point arm, so
  it goes back to a blind phase-1 review (round 3 of 3).
