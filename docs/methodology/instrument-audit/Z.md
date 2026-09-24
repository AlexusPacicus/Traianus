# Z — three-point zoom against a two-point benchmark

The question, hypothesis and refuters live in the RefApp-01 repository (`ZOOM.md`), which a blind
reviewer never opens (definitions.md, Not allowed).

## Instrument audit record (revision 2)

```
Instrument audit — Z1 (neighbourhoods kept along a zoom) and Z2 (zoom latency) (revision 2)

Scope: two arms that zoom from the barycentre to a note by different routes, each judged at the
  start, the middle and the end of its route. Z1 measures how many of each displayed note's 15
  nearest 384-d neighbours stay among its 15 nearest on the displayed plane; Z2 measures compute
  time in this script (numpy, one thread), not the client's end-to-end latency. Not measured:
  colour, legibility, anything shown while the camera moves.
Script: tools/experiments/zoom_three_point.py; unit tests: tests/unit/test_zoom_three_point.py;
  the tests of D17–D19 in tests/unit/test_audit_derivations.py. It imports, and does not copy,
  check_digests, load_inputs and validate_inputs from tools/experiments/k6_colour_predictability.py
  (reviewed code), pinned by sha256 =
  6289c596792154f6bb799606265c68719c6b8c7ae8b69084116dfb23c77876d2 and checked at run time with
  the data digests. Result: data/refapp/Z_result.json, committed.
Data: definitions.md (2,221 vectors, 8-axis basis). The script refuses to run, writing no result,
  unless sha256(embeddings.npy) = eafb0e97172830f2404e96fa08d74bf6cccc0b6cbe84d47b790a476603e7d8d1,
  sha256(labels.json) = 1d60699353d810f089730c6203ee28f9c416e3004b60781bc965cec284097f4f,
  sha256(tests/fixtures/nsm_axes_8.json) =
  b14e5d6700d1a7478a357ca26f0f38f5240f97a42daad45722d21f1c3f964e35 and the K6 script's digest
  above hold, and unless validate_inputs accepts the inputs (contracts.md §0, null elimination).
  Conversions as contracts.md §0: rows cast to float64 and renormalised; â_k = a_k / ‖a_k‖.
  FIT = even indices (1,111), EVAL = odd indices (1,110): everything fitted (barycentre, T, cells)
  uses FIT notes only; every displayed and judged note, and every target, is an EVAL note.
Space: axis coordinates c(v) = (⟨v, â_1⟩, …, ⟨v, â_8⟩) ∈ ℝ⁸. Barycentre p₀ = mean over FIT of c.
  Friction factor f(c) = 1 + Var(c), Var the population variance of the 8 components (ddof = 0).
  Declared: the engine applies the same factor to the stored axis vectors — its caller builds B_0
  from the geodetic matrix (traianus/app.py:619-622) and compute_kinetic_resistance
  (traianus/geometry/observables.py:77-92) uses B_0's rows as given — while this record uses â_k;
  the eight ‖a_k‖ are reported, so the difference has a size.
Friction-time: τ(t₀, t₁) = ∫ from t₀ to t₁ of √f(Pos(t)) · ‖Pos'(t)‖ dt, exact. τ_n(t₀, t₁) is its
  Gauss–Legendre estimate with the n nodes and weights of numpy.polynomial.legendre.leggauss(n)
  mapped to [t₀, t₁]; n = 64 everywhere except the quadrature control (n = 128). Rounding bound
  of τ_n: δ = γ₁₂₈ · τ_n, γ_m = m·(ε/2) / (1 − m·(ε/2)), ε = np.finfo(np.float64).eps: the sum of
  64 positive terms adds at most γ₆₃ (Higham, Accuracy and Stability of Numerical Algorithms, 2nd
  ed., §4.2), and each term — an 8-d affine combination, a variance and a norm over 8 components,
  a square root and a few products — at most γ₆₄ more, a generous count of its operations. An
  upper bound, not a tight one.
Targets: every q in EVAL, in index order (1,110 zooms). Each zoom goes from A = p₀ to B = c(q).
  A target with ‖B − A‖ = 0 is excluded and counted (no route).
Routes (the only difference between the arms):
  two-point (benchmark): Pos₂(t) = (1 − t)A + tB (D = 0).
  three-point: Pos₃(t) = (1 − t)A + tB + 4t(1 − t)D, with D ⊥ (B − A). Why the constraint: τ is a
    length, so at D = 0 the direction D = s(B − A), |s| ≤ ¼, only changes the speed along the
    chord and leaves τ unchanged — a flat direction that leaves the minimiser unidentified. With
    D ⊥ (B − A), Pos₃(½) = (A + B)/2 + D lies on the plain bisector of A and B, i.e. at λ = 0
    relative to the dipole A → B; the judged middle state is the τ-midpoint (States).
  Search: D = U w, w ∈ ℝ⁷, U the last 7 columns of the complete Q of
    numpy.linalg.qr(û, mode="complete"), û = (B − A)/‖B − A‖ as an 8 × 1 matrix: an orthonormal
    basis of (B − A)⊥. Objective τ₆₄(0, 1) of Pos₃. Gradient g = Uᵀ ∂τ₆₄/∂D (D18 on the same
    nodes). Hessian H by central differences of g, step ε^{1/3} · max(1, ‖w‖) per coordinate
    (Nocedal and Wright, Numerical Optimization, 2nd ed., §8.1), symmetrised. Direction: the
    Newton step p = −H⁻¹g when a Cholesky factorisation of H succeeds, else p = −g. Step length:
    Armijo backtracking from 1, halving, sufficient-decrease constant 1e-4 (ibid., Algorithm 3.1;
    the textbook's defaults, declared, not derived). Start: w = 0, the benchmark route.
  Stop: when H is positive definite and the Newton decrement's predicted decrease gᵀH⁻¹g / 2 ≤ δ
    (Boyd and Vandenberghe, Convex Optimization, §9.5.1), or when no Armijo step lowers τ₆₄ by more
    than δ: below δ an improvement is rounding, not geometry. D is therefore determined only up to
    changes worth less than δ in τ₆₄. Cap: 100 iterations, a guard (Newton near a minimum needs
    few); reaching it fails search_converged. Iterations and the final decrement are reported per
    target.
  The easing s(t) = 3t² − 2t³ is a rendering choice with s(½) = ½; it moves no judged state and is
  not modelled.
States, the same definition in both arms:
  start: t = 0, P = A.
  middle: the τ-midpoint. Bisection on t ∈ [0, 1] with the invariant
    τ₆₄(0, lo) < τ₆₄(0, 1)/2 ≤ τ₆₄(0, hi), from lo = 0, hi = 1, until hi − lo ≤ ε;
    t* = (lo + hi)/2; P = Pos(t*). The exact τ(0, t) is strictly increasing (D19); τ₆₄(0, t) may
    depart from monotone by its quadrature error, which the quadrature control covers.
  end: t = 1, P = B.
  The benchmark's middle is its own τ-midpoint, not t = ½.
Notes in view, one Voronoi level per state. The dominant attractor of a note, of q or of a point
  is argmax_k of its axis coordinates, ties to the lower axis index.
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
    mean (ties: lower mean index); in view, q's cell.
Frame at a state: T = ½ Σ (c_i − P)(c_i − P)ᵀ over the FIT notes in view; e₁, e₂ its two leading
  eigenvectors (eigh, eigenvalues descending). Displayed coordinates of an EVAL note j in view:
  (⟨c_j − P, e₁⟩, ⟨c_j − P, e₂⟩). The relative gap (λ₂ − λ₃)/λ₁ is reported per state; below 8ε,
  the scale of eigh's backward error on an 8 × 8 matrix, the plane is not determined by T and
  follows the basis eigh returns: V is still scored there, and such states are counted.
Column "V" (Z1), per target, arm and state: M = the EVAL notes in view. If |M| < 16 the state is
  not scored for that target and arm (counted). Otherwise, for each j in M: its 15 nearest in
  384-d among M \ {j} (largest ⟨v_j, v_i⟩, one Gram array G = V Vᵀ over EVAL; ties by lower
  index) and its 15 nearest on the displayed plane among M \ {j} (Euclidean; ties by lower
  index); recall(j) = the size of their intersection, 0–15. V = mean over j in M of recall(j).
  k = 5 and 50 reported only on states with |M| ≥ k + 1; the others counted.
Statistic (Z1): D_q = V_middle(q, three-point) − V_middle(q, two-point), over the targets scored
  at the middle in both arms. At the start and at the end both arms have the same P and the same
  notes in view by construction, so their displays must be identical (control below) and no
  difference is computed there.
Dependence between targets: EVAL alternates chunks of a sequential text, so nearby targets share
  neighbourhoods and their D_q are correlated. Block bootstrap over the n targets scored in both
  arms, in EVAL index order, cut into ⌈n / L⌉ contiguous blocks of that filtered list (the last
  may be shorter; a block can join chunks that are not adjacent in the text, declared). Grid
  L ∈ {1, 2, 5, 10, 20, 50}: L = 1 is independence; 50 is the largest value of the 1-2-5 grid that
  leaves at least 20 blocks at n = 1,110 (23). Twenty blocks is a declared minimum (with fewer
  resampling units a percentile interval tends to undercover): only the L with ⌈n / L⌉ ≥ 20 are
  used, and n < 20 leaves Z1 undecided (n_scored). B = 10,000 resamples per L; D̄_b = mean of D_q
  over the targets of the drawn blocks, with multiplicity.
Rule (Z1): for each L used, interval = [sorted(D̄_b)[249], sorted(D̄_b)[9749]]. Z1 refuted iff the
  upper bound < 0 at every L; the three-point route keeps more iff the lower bound > 0 at every L;
  otherwise inconclusive. The rank of a 2.5% or 97.5% quantile has Monte Carlo s.d.
  √(10,000 · 0.025 · 0.975) ≈ 15.6 ranks, so sorted[233], [265], [9733] and [9765] are reported to
  show whether a decision hinges on Monte Carlo noise.
Controls (Z1):
  arms_share_start_end: for every target, the start displays of the two arms are equal array for
    array, and so are the end displays (same notes in view, same coordinates, bit for bit).
  identity: at the start state, the recall function applied to the 384-d vectors themselves as
    the "displayed" coordinates (Euclidean on unit vectors orders as the dot product, D5) gives 15
    for every note. A swapped pair counts as a tie iff both notes' similarities lie within 1e-12
    of the 15th-place similarity: float64 rounding of a unit-vector dot product is ≈ 1e-15, a
    margin of ≈ 1,000×; ties are reported. Any other mismatch fails.
  permutation: at the start state (M = all 1,110 EVAL notes), each note's displayed neighbour list
    replaced by the first 15 entries of rng.permutation(1109) indexed into M \ {j} in index order,
    scored by the same recall function: the mean must lie in [0.149, 0.257]. Expected
    225/1109 = 0.2029, per-note s.d. ≈ 0.445 (hypergeometric, D9), s.d. of the mean over 1,110
    notes ≈ 0.0133; ± 4 s.d., widened to those bounds: a correct recall function falls outside
    with probability ≈ 6e-5.
  quadrature: at the D found with n = 64 (no new search), τ, t*, the middle P and the middle state
    recomputed with n = 128 in both arms, then D_q and the Z1 decision at every L, reusing the same
    bootstrap draws. Passes iff the set of targets scored in both arms is unchanged and the Z1
    decision is the same at every L; targets whose k* or V change are counted and reported. A
    decision, not a figure, is compared, so no tolerance is needed.
Code check: descent: τ₆₄(Pos₃) ≤ τ₆₄(Pos₂) for every target. The search starts at the benchmark
  and accepts only decreasing steps, so a failure is a code error, not a measurement.
Z2 (latency), per target, on the three-point route with the D found above. time.perf_counter_ns;
  OMP_NUM_THREADS = OPENBLAS_NUM_THREADS = VECLIB_MAXIMUM_THREADS = 1; the timer overhead (the
  median of 1,000 empty timed calls) subtracted from every timing; the first 10 EVAL targets run
  once untimed as warm-up, then every target is timed. F = 60 displayed frames at
  t_f = f/(F − 1), f = 0, …, F − 1 (a 1-second zoom at 60 frames per second; a design choice).
  search: the search for D, timed once per target and shared: both arms start after it.
  keyframes: t* (bisection), the three states (notes in view, T, display; level 2 includes its
    Lloyd partition), then the F frames: a frame with t_f ≤ t* interpolates between the start and
    middle displays with weight w = t_f / t*, one with t_f > t* between the middle and end
    displays with w = (t_f − t*)/(1 − t*); position (1 − w)·x_prev + w·x_next for the EVAL notes in
    both displays, the others kept at their display position.
  per-step: the same t* and the same level-2 partition, computed and timed in this arm too; then
    at each frame the notes in view, T and the display recomputed from scratch at P = Pos₃(t_f):
    level 0 while t_f < t*; level 1, the axis cell of the current P, while t* ≤ t_f < 1; level 2
    at t_f = 1.
  One timed call per arm per target; the arms interleaved per target, keyframes first at even
    positions of EVAL order and per-step first at odd positions, so drift affects both alike.
  Statistic: Δ_q = time_keyframes(q) − time_per-step(q), paired per target; the median of Δ_q,
    block-bootstrapped over targets as for Z1 (same grid, filter and B, its own draws).
  ready(q) = time_search(q) + the keyframes arm's time up to its third state (the F interpolated
    frames excluded).
  Rule (Z2): refuted iff the lower bound of the median-Δ interval ≥ 0 at every L used (keyframes
    not faster), or the 95th percentile over targets of ready > 100 ms; keyframes faster iff the
    upper bound < 0 at every L; otherwise inconclusive on that part. The 100 ms is the author's
    choice, the response-time limit for an instantaneous feel usually attributed to Miller (1968)
    and Nielsen (Usability Engineering, 1993), citations not verified; the 95th percentile is a
    declared choice. ready is compute only, so meeting 100 ms is necessary, not sufficient, for
    the client. Machine, numpy configuration and thread settings are recorded; the decision holds
    for that machine only.
Validity, checked in this order, every failure listed: search_converged (every target);
  lloyd_converged (every target); n_scored (n ≥ 20); arms_share_start_end; identity; permutation;
  descent; quadrature. Any failure: valid = false, and neither Z1 nor Z2 is decided. Counts
  reported: targets excluded (no route), states not scored (|M| < 16) per arm and state, states
  with a near-zero eigenvalue gap.
Reported, not deciding: V per arm and state (mean over targets); per L used, D̄, the interval and
  the margins of its bounds to 0, n and n_blocks(L); the middle cells k* per arm; τ₂, τ₃ and their
  ratio; t* per arm; ‖D‖ (identified up to δ); the search's iterations and final decrement per
  target; the eigenvalue gaps; Lloyd iterations and cells per end state; the leading direction of
  T at the start state (the corpus's dominant spread seen through the axes); the eight ‖a_k‖;
  k = 5 and 50; for Z2 the median of Δ_q and its interval per L with margins to 0, the 95th
  percentile of ready and its margin to 100 ms, and the timer overhead.
Draws: rng = numpy.random.default_rng(20260924) (PCG64; this record overrides the seed of
  contracts.md §0, as its contract will state), in this order and nowhere else: for each EVAL note
  in index order, rng.permutation(1109) (permutation control); then, for Z1, for each L used in
  ascending order and b = 1…10,000, rng.integers(0, n_blocks(L), n_blocks(L)); then the same loop
  for Z2 with its own n. The quadrature control reuses Z1's draws and draws nothing.
Unit tests (committed with the script, reviewed in phase 2; they can fail). In
  tests/unit/test_audit_derivations.py: D17, D18 and D19, each on random inputs satisfying its
  conditions and with a negative case, tolerances by derivations.md's rule; D18 also against
  central finite differences and against its known answers — at D = 0 the gradient is orthogonal
  to B − A, and τ(s(B − A)) = τ(0) for |s| ≤ ¼. In tests/unit/test_zoom_three_point.py:
  Pos₃(0) = A, Pos₃(½) = (A + B)/2 + D, Pos₃(1) = B; the search keeps D ⊥ (B − A); the bisection's
  invariant and output; the first assignment and the Lloyd iteration on a hand-built cell with a
  known answer, including a tie that must keep its current cell; notes in view never include a
  FIT note and fitting never uses an EVAL note; a target never appears in its own neighbour lists;
  recall ties by lower index; the block counts and the L filter by n; the first three entries of
  the first permutation from seed 20260924 match values recorded in the test; the timer overhead
  is subtracted; the arms' interleaving order; file-layer integrity per contracts.md §0 — a
  single-bit flip at the header, the first and the last data byte and a random position of each
  of the three data files and of the pinned K6 script is refused, writing nothing. The
  memory-layer cases are those of the imported validate_inputs, covered by
  tests/unit/test_k6_colour_predictability.py; one test checks that this script calls it (a NaN
  row is refused before writing).

Same thing in every arm?   Both arms share targets, space, friction factor, quadrature, the state
                           definitions, the level rule, T, the display and the recall function;
                           they differ only in the route (D = 0 against the searched D ⊥ B − A),
                           hence in the middle state's point and possibly its cell. Z2's two arms
                           share the route, the search, t* and the level-2 partition, and differ
                           only in how the F frames are produced.
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
