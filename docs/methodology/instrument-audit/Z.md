# Z — three-point zoom against a two-point benchmark

The question, hypothesis and refuters live in the RefApp-01 repository (`ZOOM.md`), which a blind
reviewer never opens (definitions.md, Not allowed).

## Instrument audit record (revision 1)

```
Instrument audit — Z1 (neighbourhoods kept along a zoom) and Z2 (zoom latency) (revision 1)

Scope: two arms that zoom from the barycentre to a note by different routes, each judged at the
  start, the middle and the end of its route. Z1 measures how many of each displayed note's 15
  nearest 384-d neighbours stay among its 15 nearest on the displayed plane; Z2 measures compute
  time in this script (numpy, one thread), not the client's end-to-end latency. Not measured:
  colour, legibility, anything shown while the camera moves.
Script: tools/experiments/zoom_three_point.py; unit tests: tests/unit/test_zoom_three_point.py.
  Result: data/refapp/Z_result.json, committed.
Data: definitions.md (2,221 vectors, 8-axis basis). The script refuses to run, writing no result,
  unless sha256(embeddings.npy) = eafb0e97172830f2404e96fa08d74bf6cccc0b6cbe84d47b790a476603e7d8d1,
  sha256(labels.json) = 1d60699353d810f089730c6203ee28f9c416e3004b60781bc965cec284097f4f and
  sha256(tests/fixtures/nsm_axes_8.json) =
  b14e5d6700d1a7478a357ca26f0f38f5240f97a42daad45722d21f1c3f964e35, or when the inputs fail the
  integrity checks of contracts.md §0 (null elimination). Conversions as contracts.md §0: rows
  cast to float64 and renormalised; â_k = a_k / ‖a_k‖. FIT = even indices (1,111), EVAL = odd
  indices (1,110): everything fitted (barycentre, T, cells) uses FIT notes only; every displayed
  and judged note, and every target, is an EVAL note.
Space: axis coordinates c(v) = (⟨v, â_1⟩, …, ⟨v, â_8⟩) ∈ ℝ⁸. Barycentre p₀ = mean over FIT of c.
  Friction factor f(c) = 1 + Var(c), Var the population variance of the 8 components (ddof = 0).
  Declared: the engine's K_cin (traianus/geometry/observables.py:77-92) applies the same factor to
  the stored axis vectors a_k, not to â_k; the two differ by the axes' norms.
Friction-time: for a route Pos: [0, 1] → ℝ⁸, τ(t₀, t₁) = ∫ from t₀ to t₁ of √f(Pos(t)) · ‖Pos'(t)‖ dt,
  computed by Gauss–Legendre quadrature with n = 64 nodes mapped to [t₀, t₁]. The integrand is
  positive wherever Pos'(t) ≠ 0 (f ≥ 1), so τ(0, t) is strictly increasing (D19).
Targets: every q in EVAL, in index order (1,110 zooms). Each zoom goes from A = p₀ to B = c(q).
  A target with ‖B − A‖ = 0 is excluded and counted (no route).
Routes (the only difference between the arms):
  two-point (benchmark): Pos₂(t) = (1 − t)A + tB.
  three-point: Pos₃(t) = (1 − t)A + tB + 4t(1 − t)D, D ∈ ℝ⁸ chosen to minimise τ(0, 1): gradient
    descent from D = 0 (the benchmark route), gradient by D18 on the same quadrature nodes, step by
    Armijo backtracking (sufficient-decrease constant 1e-4, step halved from 1 at each iteration;
    Nocedal and Wright, Numerical Optimization, 2nd ed., Algorithm 3.1; constants the textbook's
    defaults, declared, not derived). Stops when no step of length ≥ ε · max(1, ‖D‖) satisfies the
    Armijo condition, ε = np.finfo(np.float64).eps (convergence to float precision), or after
    10,000 iterations (the cap is a safety bound; hitting it fails search_converged).
  The easing s(t) = 3t² − 2t³ is a rendering choice with s(½) = ½; it moves no judged state and is
  not modelled.
States, the same definition in both arms:
  start: t = 0, P = A. middle: the τ-midpoint, t* with τ(0, t*) = τ(0, 1)/2, found by bisection on
  [0, 1] until the interval is no wider than ε (unique by D19); P = Pos(t*). end: t = 1, P = B.
  The benchmark's middle is its own τ-midpoint, not t = ½.
Notes in view, one Voronoi level per state:
  start (level 0): all notes.
  middle (level 1): the axis cell of P, k* = argmax_k P_k (ties: lower axis index); in view, the
    notes whose dominant attractor argmax_k c_k equals k* (FIT for fitting, EVAL for display).
  end (level 2): inside q's axis cell (argmax_k c(q)_k), a centroidal Voronoi partition of that
    cell's FIT notes around P = c(q): T_cell = ½ Σ (c_i − P)(c_i − P)ᵀ over them; its 8
    eigenvectors e_j (numpy.linalg.eigh) with both signs give 16 starting sites; first
    assignment of each FIT note to argmax_s ⟨c_i − P, s⟩ (ties: lower site index); then each site
    moves to the mean of its notes and every FIT note is reassigned to the nearest mean
    (Euclidean; ties: lower site index), until no note changes cell, or 1,000 iterations (the cap
    fails lloyd_converged); empty cells are dropped. EVAL notes are assigned to the nearest final
    mean; in view, q's cell.
Frame at a state: T = ½ Σ (c_i − P)(c_i − P)ᵀ over the FIT notes in view; e₁, e₂ its two leading
  eigenvectors (eigh, eigenvalues descending). Displayed coordinates of an EVAL note j in view:
  (⟨c_j − P, e₁⟩, ⟨c_j − P, e₂⟩). The gap between T's 2nd and 3rd eigenvalues is reported (a zero
  gap leaves the plane undetermined).
Column "V" (Z1), per target, arm and state: M = the EVAL notes in view. If |M| < 16 the state is
  not scored for that target and arm (counted). Otherwise, for each j in M: its 15 nearest in
  384-d among M \ {j} (largest ⟨v_j, v_i⟩, one Gram array G = V Vᵀ over EVAL; ties by lower
  index) and its 15 nearest on the displayed plane among M \ {j} (Euclidean; ties by lower
  index); recall(j) = the size of their intersection, 0–15. V = mean over j in M of recall(j).
Statistic (Z1): D_q = V_middle(q, three-point) − V_middle(q, two-point), over the targets scored
  at the middle in both arms. At the start and at the end both arms have the same P and the same
  notes in view by construction, so their displays must be identical (control below) and no
  difference is computed there.
Dependence between targets: as R4 — EVAL alternates chunks of a sequential text; block
  bootstrap over targets in index order, L ∈ {1, 2, 5, 10, 20, 50}, ⌈n / L⌉ contiguous blocks (the
  last may be shorter), n the number of targets scored in both arms; B = 10,000 resamples per L;
  D̄_b = mean of D_q over the targets of the drawn blocks, with multiplicity.
Rule (Z1): for each L, interval = [sorted(D̄_b)[249], sorted(D̄_b)[9749]]. Z1 refuted iff the upper
  bound < 0 at every L; the three-point route keeps more iff the lower bound > 0 at every L;
  otherwise inconclusive. The Monte Carlo neighbours sorted[233], [265], [9733], [9765] are
  reported, as in R4.
Controls (Z1):
  arms_share_start_end: for every target, the start displays of the two arms are equal array for
    array, and so are the end displays (same notes in view, same coordinates, bit for bit).
  identity: at the start state, the recall function applied to the 384-d vectors themselves as
    the "displayed" coordinates (Euclidean on unit vectors orders as the dot product, D5) gives 15
    for every note; a swapped pair within 1e-12 of the 15th-place similarity counts as a tie, as in
    R4, and ties are reported. Any other mismatch fails.
  permutation: at the start state (M = all 1,110 EVAL notes), each note's displayed neighbour list
    replaced by the first 15 entries of rng.permutation(1109) indexed into M \ {j} in index order,
    scored by the same recall function: mean must lie in [0.149, 0.257] — R4's interval, derived
    for this same M (expected 225/1109 = 0.2029, s.d. of the mean ≈ 0.0133, ± 4 s.d.; D9).
  descent: for every target, τ(Pos₃) ≤ τ(Pos₂) (the search starts at the benchmark and only
    accepts decreasing steps).
  quadrature: the whole run is repeated with n = 128 nodes; every V, every middle cell k* and the
    Z1 decision must be identical to the n = 64 run.
Z2 (latency), timed with time.perf_counter_ns, OMP/OPENBLAS/VECLIB threads = 1, after 10 warm-up
  zooms (not recorded), harness overhead (the median of 1,000 empty timed calls) subtracted from
  every timing. F = 60 displayed frames per zoom (a 1-second zoom at 60 frames per second; a design
  choice). On the three-point route, per target:
  keyframes: the search for D, the three states (notes in view, T, display) and F frames whose
    note positions are linearly interpolated between the displays of consecutive states, for the
    notes present in both (the others kept at their state position).
  per-step: the same search, then at each of the F frames the frame recomputed from scratch at
    Pos₃(t_f), t_f = f/(F − 1), f = 0, …, F − 1, with the notes in view of the level of the last state passed (level 0
    before the middle, level 1 from the middle on, level 2 at the end).
  ready: the time from the start of the search until the three states exist (keyframes arm).
  Rule (Z2): refuted iff the median over targets of the keyframes total ≥ the median of the
    per-step total, or the 95th percentile over targets of ready > 100 ms. The 100 ms is the
    response-time limit for an instantaneous feel (Miller 1968; Nielsen, Usability Engineering,
    1993; citations not verified); the 95th percentile is a declared choice. Machine, numpy
    configuration and thread settings are recorded; the decision holds for that machine only.
Validity, checked in this order, every failure listed: search_converged (every target);
  lloyd_converged (every target); arms_share_start_end; identity; permutation; descent;
  quadrature. Any failure: valid = false and neither Z1 nor Z2 is decided. Counts reported:
  targets excluded (no route), states not scored (|M| < 16) per arm and state.
Reported, not deciding: V per arm and state (mean over targets); the middle cells k* per arm;
  τ(Pos₂), τ(Pos₃) and their ratio; t* per arm; ‖D‖; the eigenvalue gaps; Lloyd iterations and
  cells per end state; the leading direction of T at the start state (the corpus's dominant
  spread seen through the axes); k = 5 and 50; the Z2 medians, 95th percentiles and harness
  overhead.
Draws: rng = numpy.random.default_rng(20260924) (PCG64), in this order and nowhere else: for each
  EVAL note in index order, rng.permutation(1109) (permutation control); then, for each L in
  ascending order and b = 1…10,000, rng.integers(0, n_blocks(L), n_blocks(L)).
Unit tests (committed with the script, reviewed in phase 2; they can fail): D17, D18 and D19 on
  random inputs (D18 against central finite differences); Pos₃ passes through A, the τ-midpoint and
  B; the τ-midpoint bisection returns τ(0, t*) = τ(0, 1)/2 within the quadrature's own difference
  between n = 64 and n = 128; the first assignment and the Lloyd iteration on a hand-built cell
  with a known answer; notes in view never include a FIT note and fitting never uses an EVAL note;
  a target never appears in its own neighbour lists; recall ties by lower index; the block counts
  (⌈n / L⌉); the first three entries of the first permutation from seed 20260924 match values
  recorded in the test; a digest mismatch and each null-elimination case of contracts.md §0 are
  refused before writing; the harness overhead is subtracted.

Same thing in every arm?   Both arms share targets, space, friction factor, quadrature, the state
                           definitions, the level rule, T, the display and the recall function;
                           they differ only in the route (D = 0 against the searched D), hence in
                           the middle state's point and possibly its cell. Z2's two arms share the
                           route and the search and differ in how the F frames are produced.
Leakage?                   Barycentre, T and cells are fitted on FIT; displays and neighbours are
                           EVAL only; no label is read. FIT and EVAL are disjoint but not
                           independent (adjacent chunks of one text in both halves). The route
                           depends on the target q through B = c(q), in both arms alike.
Comparable arms?           Valid only if every condition in Validity holds. Z1 can only differ at
                           the middle: start and end are shared by construction, and the control
                           checks it. Z2's keyframes arm computes 3 states against the per-step
                           arm's F by design; the comparison asks whether the search and the
                           interpolation eat that saving, and the 100 ms bound asks whether the
                           search itself is fast enough.
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
