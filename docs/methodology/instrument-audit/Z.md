# Z — three-point zoom against a two-point benchmark

The question, hypothesis and refuters live in the RefApp-01 repository (`ZOOM.md`), which a blind
reviewer never opens (definitions.md, Not allowed).

## Instrument audit record (revision 14)

```
Instrument audit — Z1 (neighbourhood kept along a zoom) and Z2 (zoom latency) (revision 14)

Scope: two arms that zoom from the barycentre to a note by different routes, each judged at the
  start, the middle and the end of its route. Z1 measures, for each displayed note, how much of its
  real neighbourhood — its nearest notes in 384-d among all EVAL notes, at every scale — the zoom
  keeps nearest to it on the displayed plane, against a zoom with no information (D25); Z2
  measures compute time in this script (numpy, one thread), not the client's end-to-end latency.
  Not measured: colour, legibility, anything shown while the camera moves, and the smooth curve a
  client may draw through the three points (see Routes).
Symbols, each with one meaning here and none of definitions.md's (v, a_k, â_k, c₁, c_A, c_B, ĉ₁,
  P⊥, v_dipole, δ, u⊥, r, λ, λ_k, d_esc, x, y) or contracts.md's V; where contracts.md §0 uses a
  letter here too, its meaning there is not used here (its d = 384 is written 384, and its v_i,
  a component, is never meant: v_i, v_j are notes' vectors):
  notes and space — v_i, v_j notes' 384-d vectors; c(v) ∈ ℝ⁸ a note's axis coordinates, written
    c_i, c_j for notes i, j; c_k its k-th component (k only ever indexes axes, and components are
    never written with a numeral, so no c₁ appears), c̄ the mean of its 8 components, ‖c‖ its
    norm; p₀ the FIT barycentre; f the friction factor; τ a friction-time and τ_seg that of a
    straight leg (D20), s ∈ [0, 1] a leg's parameter;
  points and the search — A = p₀, B, d = ‖B − A‖, q the target; u the unit chord (as in D21–D26)
    and ξ ∈ [0, d] the position along it; z ∈ ℝ⁷ the offset coordinates, κ their index, Z_N their
    basis, h = ‖z‖; ℓ_z the line, mid(z) its middle, lo and hi the bisection's ends; m, m₀ the
    middles, m* a known touching point (tests only); S, E objective and constraint; μ, μ̂
    multipliers; g the search's objective; H its Hessian and ω_min(H) its smallest eigenvalue;
    p the step's direction, Dg its slope, α its length; Θ the stop's threshold; ζ, ζ₊, ζ₋ the
    finite-difference steps; c_Arm Armijo's constant; Pos(t) and ease(t) a client's curve and
    easing (not measured);
  rounding — ε = np.finfo(np.float64).eps (the unit roundoff is written ε/2), γ_N, C, err_A and
    err_B the legs' errors; ν the rounding bound of a route's τ, ν_g that of the search's
    objective, ρ_pt that of a computed point; ρ₂, ρ₃ the radii of the middles' uncertainty
    spheres;
  states and score — P a state's point, k* its cell, T and T_cell tension tensors, e₁, e₂ and
    ω₁ ≥ ω₂ ≥ … their eigenvectors and eigenvalues, σ a Voronoi site; U the EVAL notes,
    N_U = |U| (1,110 in the real data, 168 in the known world), N_c = N_U − 1; M the notes in
    view, N_M of them; j a note, K a scale, K′ = min(K, N_M − 1); hyp_j(K) and shown_j(K) its
    neighbourhood hypersphere and its displayed neighbours, O_j(K) their overlap, R_j(K) its
    score, R_NX(K) and AUC as in D25; Γ the Gram array, X_E the EVAL matrix;
  statistics — D_q, D̄; n the number of targets a bootstrap resamples (those scored in both arms
    for Z1, those with a route for Z2); L a block length, N_boot the resamples, b a resample's
    index; Z2's t the zoom's time (only), t_f, N_f, w, pos_prev, pos_next, Δ_q, ready;
  known world — o_k a coordinate vector of ℝ³⁸⁴, k₁ < k₂ a pair of axes, ι its offset's number,
    β_ι the offset, i a note's 0-based index.
  Three kinds of sphere, always named in full: D21's friction-time hyperspheres (the level sets
  the middle's definition uses), D25's neighbourhood hyperspheres (hyp_j(K)), and a middle's
  uncertainty sphere (radius ρ₂ or ρ₃).
Script: tools/experiments/zoom_three_point.py; unit tests: tests/unit/test_zoom_three_point.py;
  the tests of D5, D17, D19, D20, D21, D23, D24, D25 and D26 in
  tests/unit/test_audit_derivations.py. The script's and its tests' docstrings cite the last
  revision of this record that changed code; a revision that changes only wording leaves them.
  The script sets OMP_NUM_THREADS = OPENBLAS_NUM_THREADS = VECLIB_MAXIMUM_THREADS = 1 itself,
  before its first numpy import. It imports, and does not copy, check_digests, load_inputs,
  validate_inputs and IntegrityError (their exception, raised by the pin check too) from
  tools/experiments/k6_colour_predictability.py (reviewed code); after the import it hashes the
  file the module was loaded from (module.__file__) with hashlib, not through the module's own
  check_digests (which an edit could disable), and refuses to run unless its sha256 =
  6289c596792154f6bb799606265c68719c6b8c7ae8b69084116dfb23c77876d2. Declared limits:
  this checks the file on disk, not the bytes the interpreter loaded (a stale bytecode cache is not
  seen); the "read once, hash and parse the same bytes" rule of contracts.md §0 cannot apply to an
  imported module; and importing it runs its top-level code, which sets the thread variables again
  (to the same values) and imports traianus.geometry.polar_projector, which the pin does not cover
  and the three imported functions do not use. Result: data/refapp/Z_result.json, committed; the
  option --out writes the same result to another path, and only the default one is committed.
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
  Declared: the engine applies the same factor to the stored axis vectors — its caller builds its
  basis matrix from the geodetic matrix (traianus/app.py:619-622) and compute_kinetic_resistance
  (traianus/geometry/observables.py:77-92) uses that matrix's rows as given — while this record
  uses â_k;
  the eight ‖a_k‖ are reported, so the difference has a size. Declared likewise: the engine's
  dominant attractor (traianus/app.py:282-285, :551-554, :693-696) is the argmax of ⟨v, a_k⟩ over
  the stored, unnormalised axis vectors, a tie going to the first key in the matrix's iteration
  order; this record uses â_k and the lower axis index (States).
Friction-time along a straight leg (D20):
  τ_seg(start, end) = ‖end − start‖ ∫₀¹ √f(start + s(end − start)) ds, computed with the 64
  Gauss–Legendre nodes and weights of numpy.polynomial.legendre.leggauss(64) mapped to [0, 1] (128
  in the quadrature control only), by D20's node-sum form, whose gradients are exact for the rule. Rounding bound, for 64 nodes and evaluated at the
  current route: ν = γ₂₅₆ · max(1, C²) · τ, γ_N = N(ε/2) / (1 − N(ε/2)) for N operations,
  ε = np.finfo(np.float64).eps, C the largest absolute axis coordinate among the route's
  quadrature points, τ the route's total. Count, to first order, per node: Var, with the rounding
  of the node's coordinates and of their mean, has an absolute error of about 19ε·C²; the
  subtraction c_k − c̄ can cancel, so the bound is written against C² and not against Var, and
  f ≥ 1 turns it into a relative error of f; the square root, the leg length (one norm of 8
  components per leg) and the products bring the relative error of a node's term to about
  (19·max(1, C²) + 72)·ε/2. The sum of 64 positive terms adds γ₆₃ (Higham, Accuracy and Stability
  of Numerical Algorithms, 2nd ed., §4.2): about (19·max(1, C²) + 135)·ε/2 in all, below
  128·max(1, C²)·ε for every C. An upper bound, not a tight one. The errors of the two legs, err_A
  and err_B, satisfy |err_A + err_B| ≤ ν and |err_A − err_B| ≤ ν, so S and E below each carry at
  most ν.
Targets: every q in EVAL, in index order (1,110 zooms). Each zoom goes from A = p₀ to B = c(q),
  d = ‖B − A‖. A target with d = 0 is excluded and counted (no route); the smallest positive d
  is reported. d < 4√2 is D23's condition; |c_k| ≤ 1 gives d ≤ 4√2, and a target with d ≥ 4√2
  fails tube_defined (a code or data error).
Routes (the only difference between the arms): both use the same line and the same bisection.
  u = (B − A)/d; Z_N = the last 7 columns of the complete orthogonal factor of numpy.linalg.qr(u
  as an 8 × 1 matrix, mode="complete"), an orthonormal basis of the hyperplane orthogonal to u,
  fixed per target. For z ∈ ℝ⁷ the line ℓ_z(ξ) = A + ξ·u + Z_N z. mid(z): bisection on ξ ∈ [0, d] keeping the invariant
  E(ℓ_z(lo)) < 0 ≤ E(ℓ_z(hi)), from lo = 0, hi = d, until hi − lo ≤ ε·d; ξ = (lo + hi)/2,
  mid(z) = ℓ_z(ξ). E(m) = τ_seg(A, m) − τ_seg(m, B) (D21).
  two-point (benchmark): the segment A → B, with middle m₀ = mid(0). With exact integrals, on the
    segment E < 0 exactly where τ_seg(A, ·) < τ_seg(A, B)/2 (D20 additivity), so m₀ is the
    segment's τ-midpoint, unique (D19). With the 64-node rule E is still strictly increasing on
    the segment (D23's quadrature form at h = 0), so its zero is unique; what the rule departs
    from is additivity, so that zero is not exactly the exact integral's τ-midpoint — which the
    quadrature control covers. Rounding can make the computed E non-monotone between nearby
    evaluations, but the bisection uses only its sign, and the sign can be wrong only where
    |E| ≤ ν + ‖∇E‖·ρ_pt, which the middle's uncertainty sphere accounts for (ρ₂, States).
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
  Search for m: every point it visits satisfies E = 0 by construction, so it is a search without
    constraint over z.
    Domain, the tube (D23): ‖z‖ ≤ h_max(d) = (4√2 − d)·√(d/(8√2 − d)), and E(ℓ_z(0)) < 0 ≤
    E(ℓ_z(d)). Inside it the zero of E on each line in [0, d] is unique (D23, which holds for the
    64- and the 128-node τ, both Gauss–Legendre); the second condition is its existence, which D23
    does not give. z = 0 is inside (E(A) = −τ_seg(A, B) < 0 < E(B)); if the computed signs say
    otherwise there, the search fails search_code (no_sign_change, a code or data error), and no
    later z can meet it, since each passed the domain test as a trial. The tube is where the search
    can guarantee its answer, not part of m's definition: a search that ends against its edge fails
    search_converged (below), and h/h_max = ‖z‖/h_max(d) at the found m is reported per target.
    Objective g(z) = S(mid(z)), both legs on the 64 nodes. Gradient (D24): ∇g = Z_Nᵀ(∇S − μ̂∇E),
    μ̂ = ⟨∇S, u⟩/⟨∇E, u⟩, at mid(z), with ∇S and ∇E by D20 on the same nodes (the exact gradients
    of the 64-node τ). ⟨∇E, u⟩ > 0 in the domain (D23): a computed value ≤ 0 fails search_code.
    The critical points of g are D21's Lagrange points, with μ = μ̂ (D24); μ̂ is reported and
    |μ̂| ≥ 1 counted.
    Rounding of a point: the computed ℓ_z(ξ), A + ξ·u + Z_N z in float64, differs from the exact
    point by at most ρ_pt = γ₁₀·‖(|A_k| + ξ·|u_k| + Σ_κ |(Z_N)_kκ|·|z_κ|)_{k=1…8}‖ (to first order:
    one product, a 7-term dot product and two additions per component).
    Rounding of g at the current z: ν_g = (1 + |μ̂|)·ν + |⟨∇S, u⟩|·d·ε + (‖∇S‖ + |μ̂|·‖∇E‖)·ρ_pt.
    Count, to first order: S at the computed point carries ν, and the point sits within ρ_pt of its
    exact place on the line, which moves S by at most ‖∇S‖·ρ_pt; the bisection's signs are right
    wherever |E| > ν + ‖∇E‖·ρ_pt, and the rounded midpoint fl((lo + hi)/2) lies in the last
    interval, of width at most d·ε, so that place lies within d·ε of one where |E| is at most
    ν + ‖∇E‖·ρ_pt; moving along u to the exact zero changes S by −μ̂·E (D24, first order). A
    comparison between two evaluations of g uses 2ν_g.
    Hessian H of g: central differences of ∇g with step ζ = ε^{1/3}·d per coordinate (the
    problem's length scale; Nocedal and Wright, Numerical Optimization, 2nd ed., §8.1), taken as
    the representable ζ₊ = (z_κ + ζ) − z_κ and ζ₋ = z_κ − (z_κ − ζ): column κ =
    (∇g(z⁺_κ) − ∇g(z⁻_κ))/(ζ₊ + ζ₋), z⁺_κ and z⁻_κ being z with its κ-th coordinate moved by +ζ₊ or
    −ζ₋; then symmetrised. A difference point outside the domain means the search is at the edge:
    it fails search_converged.
    Iteration, from z = 0 (so the search starts on the benchmark's middle), each step in this
    order: (1) at z: mid(z), g, ∇g and H. (2) Stop: H positive definite (a Cholesky factorisation
    succeeds) and the Newton decrement ½∇gᵀH⁻¹∇g ≤ Θ := 2ν_g/(1 − 2c_Arm), c_Arm = 10⁻⁴: converged
    (Boyd and Vandenberghe, Convex Optimization, §9.5.1). (3) Direction: p = −H⁻¹∇g if H is
    positive definite, otherwise p = −∇g; Dg = ∇gᵀp is negative for either unless ∇g = 0. ∇g = 0
    with H not positive definite is a critical point not certified as a minimum: it fails
    search_converged. Dg ≥ 0 otherwise is a code error: it fails search_code. (4) Step length:
    from α = 1, halving; a trial z + αp is rejected when it leaves the domain or fails Armijo,
    g(z + αp) ≤ g(z) + c_Arm·α·Dg (Nocedal and Wright, Algorithm 3.1; c_Arm is the textbook's
    default, declared); the first trial that passes is the step. The halving ends at
    α·|Dg| ≤ 2ν_g, below which a change of g is rounding: that floor stop fails search_converged.
    A search that works stops at (2) first: at a Newton step the computed change of g is
    −½∇gᵀH⁻¹∇g, plus the quadratic model's remainder, plus at most 2ν_g of rounding, so above Θ the
    full step passes Armijo unless the remainder exceeds the margin — and near a minimum the
    remainder is of third order in the step. (5) A cap of 100 iterations, a guard: reaching it
    fails search_converged.
    m = mid(z) at the stop. The exact E at the computed m satisfies
    |E(m)| ≤ ν + ⟨∇E, u⟩·d·ε + 2‖∇E‖·ρ_pt by construction (the bisection), not by a stop rule; the
    value computed and reported can exceed that bound by a further ν, so no test asserts the bound
    on it. m is the local solution the search reaches from m₀; S need not
    be convex (each leg's integrand is a product of positive convex functions of m), so it is not
    claimed to be the global one. Reported per target: iterations, the decrement at the stop, μ̂,
    h/h_max, ⟨∇E, u⟩ and |E(m)| at m, ξ, ρ_pt, the steps that fell back to −∇g, and, for a failed
    search, why. A failed search leaves m = mid(z) at the last iterate whose mid(z), g and ∇g
    step (1) computed, whatever failed after them — a difference point for H, a trial, or the
    next iterate's own evaluation; at the cap the last accepted step is never evaluated, so m is
    the iterate before it. The three-point arm is built on that m, scored, and enters D_q, the
    quadrature control, the reported figures and Z2, but valid is then false (Validity), so
    nothing is decided on it and those figures are diagnostics only; when that iterate is z = 0,
    m = m₀ and D_q = 0. Only a failure inside that first evaluation, at z = 0, leaves no m and so
    no three-point arm: the target drops out of D_q and Z2; after a non-positive slope there its
    two-point arm is still built and scored, with ρ₂ null, and after no sign change neither arm
    has a middle.
States, the same definition in both arms:
  start: P = A. middle: P = m₀ (benchmark) or m (three-point). end: P = B.
  If the search ends at z = 0, m = m₀ bit for bit and D_q = 0 for that target.
Notes in view, one Voronoi level per state. The dominant attractor of a note, of q or of a point
  is argmax_k of its axis coordinates, ties to the lower axis index. Each computed middle has its
  own uncertainty sphere, of radius ρ₂ (benchmark) or ρ₃ (three-point): the points it could stand
  for, given what fixed it. ρ₂ = (ν + ‖∇E‖·ρ_pt)/⟨∇E, u⟩ + d·ε + ρ_pt: where
  |E| ≤ ν + ‖∇E‖·ρ_pt the bisection's sign can be wrong, which spreads the zero over that much of
  its line; the last interval adds d·ε, and the point's rounding ρ_pt.
  ρ₃ = ρ₂ + √(2Θ/ω_min(H))·(1 + ‖Z_Nᵀ∇E‖/⟨∇E, u⟩): the move the stop still allows in z (the
  untaken Newton step, bounded through the decrement), carried to m through D24's ∇ξ, which also
  moves m along u; first order, and only at a stop at (2). A move of at most ρ₂ (or ρ₃) in every
  coordinate changes the argmax margin (first minus second largest coordinate) by at most 2ρ₂ (or
  2ρ₃), so the middle's margin is reported per target and arm next to 2ρ₂ or 2ρ₃, and targets
  whose margin is below it are counted: their cell could depend on where in its uncertainty
  sphere the middle stands.
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
  K = 1, …, N_U − 2 (1,108 in the real data): hyp_j(K) = its K nearest in 384-d among U \ {j}
  (largest ⟨v_j, v_i⟩ from one Gram array Γ = X_E X_Eᵀ over the EVAL rows; ties by lower index) —
  j's neighbourhood hypersphere, the
  same in both arms and at every state; K′ = min(K, N_M − 1); shown_j(K) = its K′ nearest on the
  displayed plane among M \ {j}, ordered by squared Euclidean distance (the distance's order in
  exact arithmetic, without the square root's rounding, which could merge two distinct squared
  distances into a tie; ties by lower index);
  O_j(K) = |hyp_j(K) ∩ shown_j(K)|;
  R_j(K) = (O_j(K)/K − K′/(N_U − 1)) / (1 − K′/(N_U − 1)); R_NX(K) = the mean over j in M of
  R_j(K); the state's score AUC = [Σ_K R_NX(K)/K] / [Σ_K 1/K]. It is 1 when the zoom keeps every
  note's neighbourhood hypersphere in order, 0 on average for a zoom with no information (a random view shown
  in a random order, D25), and below 0 when the zoom does worse than that. It judges the whole
  zoom: a view that cuts a note's real neighbours off scores lower even with a perfect display,
  and a view of fewer than K + 1 notes cannot reach 1 at scale K. The weights 1/K count every
  scale factor about alike (1–10 weighs about as much as 10–100); a uniform weight would give
  nearly all the weight to the largest neighbourhoods. A score is computed once per identical view
  and display and reused, which is exact, since the neighbourhood ranks are fixed per run.
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
    ℝ³⁸⁴, and the axes are â_k = o_k (k = 1…8). Offsets: the pairs k₁ < k₂ of axis indices in
    lexicographic order (k₁ = 1…7, k₂ = k₁ + 1…8; 28 pairs), each taken three times in a row,
    numbered ι = 1…84 in that order; β_ι = 0.1 + 0.2·frac(ι²·(√5 − 1)/2): 84 distinct values in
    (0.1, 0.3), each belonging to one pair. Notes: for each ι in order, four notes at the 0-based
    indices 4(ι − 1) … 4(ι − 1) + 3 — FIT (k₁, k₂, β_ι), EVAL (k₁, k₂, β_ι), FIT (k₂, k₁, β_ι),
    EVAL (k₂, k₁, β_ι) — where note (k₁, k₂, β) has axis coordinates c_k = 0.1 + β for k = k₁,
    0.1 − β for k = k₂ and 0.1 otherwise, and vector v = Σ_k c_k o_k + √(1 − ‖c‖²)·o_{9+i}, i the
    note's 0-based index (0…335), so ‖v‖ = 1 and the parts beyond the axes are orthogonal between
    notes. FIT = even indices (168) and EVAL = odd (168), as in the real data. Each mirror pair
    (k₁, k₂, β_ι), (k₂, k₁, β_ι) lies in the same half, so the FIT barycentre is 0.1 in every
    coordinate, on the diagonal, and every target has B − A orthogonal to it:
    by D26 m₀ is the only answer, for every target, and by its quadrature form, for the 64-node
    τ the search computes, ∇g(0) = 0 and the projection gap makes g rise off z = 0 (up to the
    rule's error along the chord). Two kinds of tie would leave a display order to rounding, and
    the offsets rule out both. They are distinct (the ι² differ and (√5 − 1)/2 is irrational), so
    no permutation of the axes maps the corpus onto itself (it would have to fix every pair): with
    one offset shared by several pairs, notes symmetric under such a permutation land on one
    display point. And no pair's three offsets are equally spaced: the three notes of a pair in
    one axis cell lie on one line of ℝ⁸, at parameter β_ι along it, and so do their displayed
    points (the display is affine in c), so one of them is equally far from the other two, on the
    display as in ℝ⁸, iff its offset is the mean of theirs (or the line is orthogonal to the
    displayed plane, where all three coincide). If one of a pair's β_ι, β_{ι+1}, β_{ι+2}
    (ι = 1, 4, …, 82) were the mean of the other two, then, since β_ι = 0.1 + 0.2·(ι²·(√5 − 1)/2
    − an integer), (√5 − 1)/2 times twice its number squared minus the other two numbers squared
    would be an integer; that combination is −(6ι + 5), −2 or 6ι + 7 as the mean is β_ι, β_{ι+1}
    or β_{ι+2}, never 0, and (√5 − 1)/2 is irrational. Twice one offset of a pair minus the other
    two is at least 5.0·10⁻³ in absolute value over the 28 pairs; revisions 6–8's offsets,
    frac(ι·(√5 − 1)/2), gave 0 for 6 of them. Rounding orders such ties, and the quadrature
    control's 128-node m₀, which differs from the 64-node m only in its last bits, could reorder
    them. The smallest relative gap between two displayed distances from a note, over the middle
    states, is reported, so a failure there can be told apart. Expected: every search stops at (2)
    at z = 0 with no step, so every D_q is exactly 0; every middle state is scored (its cell holds
    the 21 EVAL notes that share the target's leading axis); Z1 is inconclusive at every L used;
    tube_defined, search_converged, search_code, lloyd_converged, Z1's n_scored,
    arms_share_start_end, identity, permutation and quadrature hold. Z2 and search_reproduced are
    not run there: a clock is never deterministic. Its draws come from its own generator (Draws),
    so the real run's draws are untouched. Any other outcome: valid = false, and the real data are
    not read.
  arms_share_start_end: for every target, the start states of the two arms are equal and so are
    the end states — same notes in view and the same coordinates bit for bit, or both degenerate.
  identity: at the start state (M = U), the score applied to the 384-d vectors themselves as the
    "displayed" coordinates (Euclidean on unit vectors orders as the dot product, D5) gives
    R_j(K) = 1 for every note and scale (D25 (a)). A note out of order counts as a tie iff its
    similarity to j and that of the note it swapped with lie within 1e-12 of each other. The
    worst-case float64 error of a 384-term dot product of unit vectors is γ₃₈₄ ≈ 4.3e-14, and the
    Euclidean side adds rounding of the same order, so 1e-12 leaves a margin of ≈ 10–20× (not
    more); ties are reported. Any other mismatch fails.
  permutation: at the start state (M = U), each note's display ranking replaced by
    rng.permutation(N_c) indexed into U \ {j} in index order, and scored by the same function (the
    score takes two rankings per note, in 384-d and on the display): the AUC must lie in
    ±4/√(N_U(N_U − 2)), computed at the run's N_U (±0.003607 in the real data, ±0.0240 in the
    known world). By D25 (b) its mean is 0 and its variance at most 1/(N_U(N_U − 2)), the notes'
    permutations being independent; with the normal approximation over N_U independent notes, a
    correct score falls outside with probability ≈ 6.3e-5 at the bound, and less, since the
    variance is an upper bound. Declared limits: the band cannot see an error in the chance term
    smaller than itself (in the real data, N_c = N_U instead of N_U − 1 shifts the AUC by about
    8e-4 and passes; identity passes too, since R_j(K) = 1 at O_j(K) = K for any N_c) — D25's
    unit tests, which enumerate every arrangement, cover those; and at the start state K′ = K, so the
    branch K′ < K (views of fewer than K + 1 notes) has no run-time control: it is exercised by the
    middle and end states and checked by D25's unit tests.
  quadrature: the found m is kept (no new search); m₀ = mid(0), the benchmark's middle state, the
    two legs' τ, |E(m)| and ∇g at m are recomputed with 128 nodes; then D_q and the Z1 decision at
    every L, reusing the same bootstrap draws. Passes iff the set of targets scored in both arms is
    unchanged and the Z1 decision is the same at every L; targets whose k* or score change are
    counted, and |E(m)| and ‖∇g‖ at 128 nodes are reported. A decision, not a figure, is compared,
    so no tolerance is needed.
Z2 (latency), per target with a route, on the three-point route with the m found above.
  time.perf_counter_ns; the timer overhead (the median of 1,000 empty timed calls) subtracted from
  every timing and timestamp difference, and once more from the keyframes arm's total, since that
  timed call reads the clock once inside, for its timestamp. Warm-up: the first 10 EVAL targets
  with a route run once, search and both arms, untimed and discarded; then every target is timed.
  N_f = 60 displayed frames at the times t_f = (frame number)/(N_f − 1), frame number 0 … N_f − 1
  (the subscript f names a frame, not the friction), evenly spaced in t without easing (a 1-second
  zoom at 60 frames per second; both choices declared: easing would change which frames fall
  before the middle). On the three-point route t ∈ [0, ½] runs linearly along A → m and t ∈ [½, 1]
  along m → B, so the middle is at t = ½.
  search: the line (u, Z_N and d) built again and the search for m, whose first step computes
    m₀ = mid(0), re-run in the timed pass; it must reproduce the m of the Z1 pass bit for bit
    (search_reproduced). Timed once per target and shared: both arms start after it.
  keyframes: the three states (notes in view, T, display; level 2 includes its Lloyd partition),
    a timestamp once the third state exists, then the N_f frames: a frame with t_f ≤ ½ interpolates
    between the start and middle displays with weight w = 2t_f, one with t_f > ½ between the middle
    and end displays with w = 2t_f − 1; position (1 − w)·pos_prev + w·pos_next for the EVAL notes in
    both displays, and, for a note in only one of the two, the position it has in that one.
  per-step: the same level-2 partition — T_cell, the Lloyd iteration and the EVAL assignment, not
    the level-2 state — computed and timed in this arm too; then at each frame the notes in view,
    T and the display recomputed from scratch at the route's point P(t_f): level 0 while t_f < ½;
    level 1, the axis cell of the current P, while ½ ≤ t_f < 1; level 2, q's cell of that
    partition, at t_f = 1, at P = B exactly. Each arm builds each state it shows once: the
    keyframes arm 3, the per-step arm N_f.
  Untimed and shared by both arms: the 64 Gauss–Legendre nodes and weights, and the notes' axis
    coordinates and dominant attractors, computed once per run before any timing; each state's
    cell is filtered from them inside the timed calls, and everything that depends on the route's
    point is computed there too.
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
  to −∇g, |μ̂| ≥ 1, middles whose argmax margin is below 2ρ₂ or 2ρ₃. The state counts see only
  the arms that exist: a target whose search fails inside its first evaluation has no
  three-point arm (and, after no sign change, no two-point arm either), so it adds no
  three-point state to them and shows as missing only among the failed searches, with valid
  false (search_code).
Reported, not deciding: the score per arm and state (mean over targets); per L used, D̄, the
  interval and the margins of its bounds to 0, n and n_blocks(L); the middle cells k* per arm,
  N_M per arm, the targets whose middle cells differ and D̄ over those whose cells agree; per
  target scored in both arms, the scales K where R_NX(K) of the three-point middle minus that of
  the benchmark's changes sign (where one route starts keeping more than the other), summarised
  over targets; the middle cells' argmax margins; τ₂ = τ_seg(A, B), τ₃ = S(m) and their ratio; ξ;
  ‖m − m₀‖; h/h_max; the search diagnostics above; the eigenvalue gaps; Lloyd iterations and
  cells per end state; the leading direction of T at the start state (the corpus's dominant
  spread seen through the axes); the eight ‖a_k‖; the smallest positive d; for Z2, the median of
  Δ_q and the 95th percentile of ready with their intervals per L and their margins (to 0 and to
  100 ms), and the timer overhead.
Draws: rng = numpy.random.default_rng(20260924) (PCG64; this record overrides the seed of
  contracts.md §0, as its §4 states), in this order and nowhere else: for each EVAL note
  in index order, rng.permutation(N_c) (permutation control); then, for Z1, for each L used in
  ascending order and b = 1…N_boot, rng.integers(0, n_blocks(L), n_blocks(L)); then the same loop
  twice for Z2 with its n, first for the median of Δ, then for the 95th percentile of ready. The
  quadrature control reuses Z1's draws and draws nothing. The known world has its own generator,
  numpy.random.default_rng(20260925), for its permutation control (rng.permutation(167) for each
  of its 168 EVAL notes) and then its Z1 bootstrap, in the same order.
Unit tests (committed with the script, reviewed in phase 2; they can fail). In
  tests/unit/test_audit_derivations.py: D5 (existing), D17, D19, D20, D21, D23, D24, D25 and
  D26, each on inputs satisfying its conditions and with a negative case, tolerances by
  derivations.md's rule; D20's node-sum gradients against central finite differences of the
  64-node τ, its reversal for the symmetric rule, and its additivity and radial rate for the
  integral; D21 on random synthetic frictions whose touching point is known; D23's slope on random
  parallels inside the tube for the integral and for the 64-node quadrature, and h_max against
  its closed form; D24's gradient against finite differences of g computed through the
  bisection; D25 (b) exactly, by enumerating every arrangement for small N_U and N_M (no draws),
  and D25 (a) with a view smaller than K + 1; D26 on random chords orthogonal to the diagonal,
  and its quadrature form: g(−z) = g(z) and the node-by-node gap, with the 64-node τ. In tests/unit/test_zoom_three_point.py, for the search: (i) a search
  that does not work must fail — with A and B off the diagonal, where m₀ is not a solution
  (∇g(0) ≠ 0), the search must end at (2) with g(z) < g(0) − 2ν_g; a search that returns its
  input fails this test; (ii) through D21's synthetic friction, injected in the test: √f affine
  on the region the legs sweep (so the 64-node τ is exact along every leg), with √f ≥ 1 and
  ‖∇√f‖ < 1/(2√2) there (so D23's tube holds for it), and A and B placed so that the touching
  point m* follows in closed form by symmetry; from its own m₀, the search must end at (2) — ρ₃
  bounds the remaining move only at a converged stop — with m* in the found m's uncertainty
  sphere, ‖m − m*‖ ≤ ρ₃ (States; first order), compared in ℝ⁸; ν, ν_g, Θ and ρ₃ keep the formulas
  derived for f = 1 + Var, whose operation count bounds that of an affine √f; (iii) the known
  answers where m₀ is the solution, which the search must return with no step — A and B on the diagonal (f = 1 on the segment, ≥ 1
  elsewhere, and the sum of the two legs grows off it) and B − A orthogonal to the diagonal from
  A on it (D26); (iv) search_code fires when the direction p, once computed, is replaced by −p
  (Dg > 0; a gradient flipped everywhere would not do it, since the Hessian built from it is then
  not positive definite and the fallback −∇g descends for it), and on a forced ⟨∇E, u⟩ ≤ 0;
  (v) mid(0) is the τ-midpoint of the segment, the bisection keeps its invariant, and
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
  test; the timer overhead is subtracted, and once more from the keyframes arm's total; the timed
  search rebuilds its line inside its interval; each Z2 arm builds each state once (the keyframes
  arm 3, the per-step arm N_f, its last at P = B); the arms' interleaving order; search_reproduced;
  which point a failed search leaves (with a cap of 1, m = m₀ although a step was accepted; after
  a difference point of H fails at a later iterate, that iterate; after a non-positive slope at a
  later iterate, the one before it; at z = 0, a non-positive slope leaves the two-point arm only,
  with ρ₂ null, and no sign change neither arm, and such a target is out of D_q and of Z2);
  the smallest positive d skips a target with d = 0; the known world's corpus meets D26's
  conditions, its 84 offsets are distinct, no pair's three are equally spaced (twice one minus
  the other two at least 5.0·10⁻³ in absolute value), and its null_world passes, with a smallest
  relative display gap > 0, and fails with an arm-dependent search; that each control can fail —
  identity with a score that counts j among its own neighbours, permutation with a score whose
  chance term is dropped (R_j(K) = O_j(K)/K, whose null AUC is about 1/Σ_K(1/K) ≈ 0.13),
  arms_share_start_end with an arm-dependent start, quadrature with a changed decision;
  tube_defined with d ≥ 4√2; n_scored with fewer than 20 targets scored in both arms (Z1), and
  with fewer than 20 with a route (Z2); file-layer integrity per contracts.md §0 — a single-bit
  flip at the header, the first and the last data byte and a random position of each of the three
  data files and of the K6 module's file is refused, writing nothing, the K6 module's file also
  with the module's check_digests disabled. The memory-layer cases are those of the imported
  validate_inputs, covered by tests/unit/test_k6_colour_predictability.py; one test checks that
  this script calls it (a NaN row is refused before writing).

Same thing in every arm?   Both arms share targets, space, friction factor, quadrature, the line
                           and its bisection, the state definitions, the level rule, T, the display
                           and the score, with each note's neighbourhood hypersphere the same in both; they
                           differ only in the route (the segment against the two legs through the
                           searched m), hence in the middle state's point and possibly its cell.
                           Z2's two arms share the route, the search and the level-2 partition, and
                           differ only in how the N_f frames are produced.
Leakage?                   Barycentre, T and cells are fitted on FIT; displays, neighbourhoods and
                           neighbourhood hyperspheres are EVAL only; no label is read. FIT and EVAL are disjoint
                           but not independent (adjacent chunks of one text in both halves). The
                           route depends on the target q through B = c(q), in both arms alike.
Comparable arms?           Valid only if every condition in Validity holds. Z1 can only differ at
                           the middle: start and end are shared by construction, and the control
                           checks it. When the middle cells differ, both arms are still judged
                           against the same neighbourhood hyperspheres over all EVAL notes and at the same
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
                           instrument-auditor (blind subagent, review package built at d175b56),
                           2026-09-25; phase 1 (specification), round 1 of 3 on revision 5's
                           design; commit d175b56 (revision 5); PASS, 0 blocking, 11
                           non-blocking; D20 (amended) and D23–D26 verified.
                           Revision 6 applies those items and changes no arm: its review is
                           round 2 of 3 on revision 5's design.
                           instrument-auditor (blind subagent, review package built at cdafd6c),
                           2026-09-25; phase 1 (specification), round 2 of 3 on revision 5's
                           design; commit cdafd6c (revision 6); PASS, 0 blocking, 6
                           non-blocking; round-1 items addressed (3 and 8 in part); D23–D26
                           verified; no arm changed.
                           Revision 7 applies those items and changes no arm: its review is
                           round 3 of 3 on revision 5's design.
                           instrument-auditor (blind subagent, review package built at ff61178),
                           2026-09-25; phase 1 (specification), round 3 of 3 on revision 5's
                           design; commit ff61178 (revision 7); PASS, 0 blocking, 7
                           non-blocking; round-2 items addressed (5 in part); D20, D23–D26
                           verified; no arm changed. Phase 1 closed; the 7 items carry to
                           phase 2, items 3 and 5 before any code.
                           Revisions 8 and 9 change no arm and had no phase-1 round: phase 2
                           checks them against the code.
                           instrument-auditor (blind subagent, review package built at 33a12e3),
                           2026-09-25; phase 2 (code, before the first run), round 1; commit
                           33a12e3 (revision 9; script and tests); PASS, 0 blocking, 12
                           non-blocking; every record line mapped; D5, D17, D19–D21, D23–D26
                           tested; contracts.md §0 and §4 conform; revision 8's seven items and
                           revision 9's offsets verified against the code; no result exists.
                           instrument-auditor (blind subagent, review package built at 05adb96),
                           2026-09-26; phase 2 (code, before the first run), round 2; commit
                           05adb96 (revision 11; script and tests at a4e9274); CHANGES, 1
                           blocking, 6 non-blocking; round-1 items 1–12 resolved in record and
                           code, revision 11's failed-search sentence matches the code; D5, D17,
                           D19–D21, D23–D26 tested; contracts.md §0 and §4 conform; blocking: the
                           per-step arm builds the level-2 state twice (N_f + 1 states against
                           the record's N_f); no result exists.
                           instrument-auditor (blind subagent, review package built at ec26df4),
                           2026-09-26; phase 2 (code, before the first run), round 3; commit
                           ec26df4 (revision 13; script and tests at 83870fa); PASS, 0
                           blocking, 4 non-blocking; round-2 blocking item B1 (each Z2 arm
                           builds each state it shows once: 3 and N_f, the last per-step frame
                           at P = B) and items N1–N6 resolved in record and code; revision 13's
                           failed-search sentences match the code; every record line mapped; D5,
                           D17, D19–D21, D23–D26 tested; contracts.md §0 and §4 conform; no
                           result exists.
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
- **Revision 5** — `instrument-auditor` subagent, blind by construction (package built from
  `d175b56`, lock set), 2026-09-25, phase 1, round 1 of 3 on revision 5's design: **PASS**, 0
  blocking, 11 non-blocking; D20 (amended) and D23–D26 verified; both round-4 blocking items
  resolved by the design. The reviewer did not open the packaged results of other records
  (data/refapp/K6_result.json, R4_result.json) and disclosed that its session context held the
  user's memory index (outcomes of other records, Z's process status; nothing on Z's hypothesis
  or results). Non-blocking, items 1, 2 and 6 before any code: (1) the known world's quadrature
  expectation is not fixed by D26 — the six notes (p, q′, β) with q′ ∉ {p, q} are symmetric
  under permutations of the other axes and land on one display point, so their order is decided
  by rounding, which differs between the 64-node m and the 128-node m₀; D_q at 128 nodes is then
  not 0 and the decision can flip on a correct pipeline — use generic offsets (distinct β per
  pair, mirror pairs kept in each half, Σ_k c_k constant) or state the caveat; (2) ν_g and the
  |E(m)| claim leave out the rounding of the point itself (ε·‖m‖∞, of order C, not d), which
  matters for d below about C/20; (3) the middle cell's margin understates the residual — the
  decrement allows √(2b/ω_min(H)), P's float grid ε·‖P‖∞ exceeds d·ε when d < ‖P‖∞, and
  ‖Z_N αp‖∞ omits the move along u; (4) D23 is proved for the integral but applied to the 64-
  and 128-node E: it holds for any quadrature with positive weights, Σw = 1 and Σw·s = ½, which
  D23's conditions should state; (5) test (ii)'s synthetic friction must satisfy
  ‖∇√f‖ < 1/(2√2); (6) test (iv) cannot fire as worded — a consistently flipped gradient makes
  the finite-difference Hessian not positive definite, the fallback is then a descent direction
  for the flipped gradient and the search ends at the floor; inject the flip into p only;
  (7) the known world's positions: 1-based positions with FIT on even ones contradict the order
  FIT, EVAL, …, and the loop order over {p, q} and β is not fixed; (8) symbols still colliding:
  ν (bound and ν_j(K)), h (difference step and offset), c₁ (definitions.md's anchor), t (in
  [0, 1] here, in [0, d] in D23–D24), o_j in ℝ⁷ and o_k in ℝ³⁸⁴; (9) the permutation band cannot
  see an error in the chance correction below 0.0036 (P = N_U instead of N_U − 1 passes both
  controls), so the off-by-one test must use a defect the band detects, the K′ < K branch has no
  run-time control (declare it), the score takes rankings, and the two-sided 4σ tail is ≈ 6.3e-5;
  (10) contracts.md has no section for Z yet, needed before phase 2; (11) derivations.md's
  "Used by" lists D9 for Z, no longer used, and the record's test lists omit D5, which the
  identity control uses.
- **Changes in revision 6** — the eleven round-1 items, no change to either arm's design.
  (1) The known world's offsets are distinct: β_n = 0.1 + 0.2·frac(n·g), g = (√5 − 1)/2, one per
  pair and level (84), so no permutation of the axes maps the corpus onto itself; the smallest
  relative gap between displayed distances is reported. (2) The rounding of a point,
  ρ_ℓ = γ₁₀·‖M_ℓ‖, enters ν_g as (‖∇S‖ + |μ̂|·‖∇E‖)·ρ_ℓ and the bound on |E(m)| as 2‖∇E‖·ρ_ℓ.
  (3) The middle cell's margin is compared with 2r: r₂ = ½·d·ε + ρ_ℓ for the benchmark, and r₃
  adds the move the stop still allows, √(2b/ω_min(H)), carried to m through D24's ∇ξ.
  (4) D23 states that it holds for any quadrature with positive weights, Σw = 1 and Σw·s = ½,
  and its proof covers h = 0 through the same bound; its conditions now ask only f ≥ 1 and
  ‖∇√f‖ < 1/(2√2). (5) Test (ii)'s synthetic friction must meet those conditions. (6) Test (iv)
  replaces p by −p once computed. (7) The known world's notes have 0-based indices, FIT on even
  ones as in the real data, and a fixed loop order. (8) Symbols: the position along the chord is
  ξ ∈ [0, d] in the record and in D23–D26 (the line is ℓ_z(ξ) = A + ξ·u + Z_N z and the bisection
  runs to ε·d; t is the zoom's time only); the hypersphere is V_j(K); the difference step is δ;
  Armijo's constant is c_Arm; the coordinate vectors o_k are only those of ℝ³⁸⁴; in the
  derivations D25's candidates are N_c and D26's projector Π, D24's step along u is Δξ. (9) The
  permutation control names what the score takes, the tail ≈ 6.3e-5, and declares its limits
  (an error in the chance term below about 0.0036, and no run-time control of K′ < K, both
  covered by D25's unit tests); its can-fail test drops the chance term (null AUC ≈ 0.13).
  (10) contracts.md's section for Z is written once phase 1 closes, before any code, as K8's was.
  (11) derivations.md's "Used by" drops D9 for Z; the record's test list includes D5. This
  revision changes no arm, so it is round 2 of 3 on revision 5's design.
- **Revision 6** — `instrument-auditor` subagent, blind by construction (package built from
  `cdafd6c`, lock set), 2026-09-25, phase 1, round 2 of 3 on revision 5's design: **PASS**, 0
  blocking, 6 non-blocking; round-1 items addressed, 3 and 8 in part; D23–D26 verified again;
  the claim that no arm changed holds. The reviewer did not open the packaged results of other
  records and disclosed the memory index in its context, as in round 1. Non-blocking, before
  phase 2: (1) r₂ omits the bisection's sign-error term — the computed middle can sit
  (ν + ‖∇E‖·ρ_ℓ)/⟨∇E, u⟩ from the exact zero on its line, about 64–128 times ½·d·ε, which ν_g
  already carries; and the rounded midpoint fl((lo + hi)/2) guarantees d·ε, not ½·d·ε;
  (2) test (ii)'s tolerance √(2b/ω_min(H)) is a distance in z while the touching point is in ℝ⁸ —
  compare in z with z* = Z_Nᵀ(m* − A), or in m with r₃, and say that the bound is first order;
  (3) the caveat that the quadrature estimate may depart from monotone is stale — by D23's
  quadrature form the 64-node E is strictly increasing on the segment; what the quadrature
  departs from is additivity, and only rounding can break monotonicity, within
  |E| ≤ ν + ‖∇E‖·ρ_ℓ; (4) D23's conditions omit s_i ∈ [0, 1], used by the quadrature bound, and,
  now that f need not be 1 + Var, f continuously differentiable (D20's differentiation under the
  integral and D24's implicit function theorem need it); (5) new symbol collisions — g (objective
  and (√5 − 1)/2), n (targets and offset index), ℓ (the line and the level index), P (the point
  and "P = N_U", which should be N_c), r (residual and r_j(K)), M_ℓ next to M, δ and u⊥ against
  definitions.md's "2δ·u⊥", c = 0.1·1 + β(o_p − o_q) adding vectors of ℝ³⁸⁴ to one of ℝ⁸, b (the
  bound and the bootstrap index), p and q (the direction and the target against the known
  world's axes), and contracts.md's V against V_j(K) once Z's section exists; (6) the bound on
  |E(m)| is on the exact E at the computed m, while the reported value is computed and can
  exceed it by a further ν — say so, so that no phase-2 test asserts it on the computed value.
- **Changes in revision 7** — the six round-2 items, no change to either arm's design (the
  author, 2026-09-25). (1) Each computed middle has its own sphere: ρ₂ = (ν + ‖∇E‖·ρ_pt)/⟨∇E, u⟩
  + d·ε + ρ_pt (the zone where the bisection's sign can be wrong, the last interval, now d·ε since
  the rounded midpoint only stays inside it, and the point's rounding), ρ₃ = ρ₂ plus the move the
  stop allows carried to m; the argmax margin is compared with 2ρ₂ or 2ρ₃. ν_g and the |E(m)|
  bound use d·ε. (2) Test (ii) compares in ℝ⁸ and passes iff the known touching point lies in the
  found m's own sphere, ‖m − m*‖ ≤ ρ₃, first order; its friction has √f affine on the region the
  legs sweep, so the 64-node τ is exact there and m* follows in closed form. (3) The benchmark's
  caveat now says what the quadrature departs from — additivity, not monotonicity, which D23's
  quadrature form gives — and where rounding can break monotonicity. (4) D23's conditions state
  s_i ∈ [0, 1] and f continuously differentiable, with f ≥ 1 and ‖∇√f‖ < 1/(2√2) needed on the
  legs only; D20's conditions ask f continuously differentiable and its ∇f = ∇Var holds for
  f = 1 + Var. (5) One table of symbols, each with one meaning and none of definitions.md's or
  contracts.md's V: the stop's threshold is Θ, the finite-difference steps ζ, the radii ρ₂, ρ₃
  and the point's rounding ρ_pt, γ_N for a count of N operations, err_A, err_B for the legs'
  errors, κ for z's coordinates; the hypersphere, the displayed neighbours, the per-note score
  and the per-note AUC are hyp_j(K), shown_j(K), R_j(K) and AUC_j (in D25 too, whose part (c)
  no longer uses κ or c); the known world's pairs are k₁ < k₂, its offsets β_ι with ι their
  number, its coordinates written per component; "u⊥" is written as the hyperplane orthogonal to
  u; the engine's basis matrix is no longer called B_0; Z2's frames are numbered in words, not
  by f; D23 and D26 write the offset vector Y, D23's proof W, and û_A, û_B for the legs'
  directions. (6) The |E(m)| bound is stated for the exact E at the computed m, and the reported
  value may exceed it by a further ν. This revision changes no arm: round 3 of 3 on revision 5's
  design.
- **Revision 7** — `instrument-auditor` subagent, blind by construction (package built from
  `ff61178`, lock set), 2026-09-25, phase 1, round 3 of 3 on revision 5's design: **PASS**, 0
  blocking, 7 non-blocking; round-2 items addressed, 5 in part; D20, D23–D26 verified again; no
  arm changed. Phase 1 closes on this design; the items carry to phase 2, 3 and 5 before any
  code. The reviewer did not open the packaged results of other records and disclosed the memory
  index and recent commit messages in its context (other records' outcomes, Z's process status;
  nothing on Z's hypothesis or results). Non-blocking: (1) two lines still use r, a bare O and P
  for the score and the candidate count ("r = 1 at O = K for any P", "r = O/K"); they should read
  R_j(K) = 1 at O_j(K) = K for any N_c, and R_j(K) = O_j(K)/K; (2) the symbol table is
  incomplete — c(v) is missing (c_k a component, c_i, c_j notes' vectors, c̄, ‖c‖; c_k at k = 1
  reads as definitions.md's c₁), and so are p₀, f, τ and τ_seg with P, Q and s (P is also a
  state's point, Q also the QR factor), lo, hi, m*, the generic ρ, ω_min(H) (ω is T's
  eigenvalues), Pos and ease; "ν a route's τ" should say τ's rounding bound; n is not only the
  targets scored (Z2's n counts targets with a route); "hypersphere" names both D21's level sets
  and D25's neighbour sets, next to the middle's "sphere"; contracts.md §0's d = 384 and v_i (a
  component) collide with d = ‖B − A‖ and v_i (a note's vector); (3) N_U is written as 1,110,
  which is only the real data's value, and so are K up to 1,108, rng.permutation(1109) and the
  band ±0.003607 — the known world has N_U = 168, K up to 166 and a band of ±4/√(168·166) ≈
  ±0.0240; hard-coded, the band is about ±0.6 of the known world's null s.d. bound and null_world
  would often fail on a correct pipeline: state N_U = |U| and the band as its formula; (4) the
  count "middle cells decided inside the last move" should read "argmax margin below 2ρ₂ or
  2ρ₃"; (5) test (ii) must require the search to end at (2) — ρ₃ bounds the remaining move only
  at a converged stop — and should say that ν, ν_g, Θ and ρ₃ keep their formula with the injected
  friction; (6) D20 is stated for the integral while the record uses its node-sum form for the
  64-node τ (state it, and test that form against finite differences of the 64-node τ), and D26's
  proof uses additivity, which the 64- and 128-node τ lack — in the known world g is still even in
  z, so ∇g(0) = 0, and a node-by-node projection keeps z = 0 a strict local minimiser up to the
  rule's error: add a quadrature form to D26; (7) rounding can make the computed E non-monotone
  anywhere between two nearby evaluations; what can go wrong only where |E| ≤ ν + ‖∇E‖·ρ_pt is
  the sign, which is all the bisection uses — say "sign", not "monotonicity".
- **Changes in revision 8** — the seven round-3 items, after phase 1 closed; no change to either
  arm's design, and no further phase-1 round: phase 2 checks them against the code (the author,
  2026-09-25). (1) The two lines read R_j(K) = 1 at O_j(K) = K for any N_c, and R_j(K) = O_j(K)/K.
  (2) The symbol table adds c(v), c_i, c_j, c_k (k only indexes axes, never a numeral), c̄, ‖c‖,
  p₀, f, τ, τ_seg with its start and end written in words, s, lo, hi, m*, ω_min(H), Pos, ease and
  κ; ν is τ's rounding bound; n is described per bootstrap; contracts.md §0's d = 384 and v_i are
  set apart; the QR factor is no longer called Q; three kinds of sphere are always named in full
  (D21's friction-time hyperspheres, D25's neighbourhood hyperspheres, a middle's uncertainty
  sphere). (3) N_U = |U| (1,110 in the real data, 168 in the known world); K runs to N_U − 2, the
  permutations are rng.permutation(N_c), and the band is ±4/√(N_U(N_U − 2)) at the run's N_U
  (±0.003607 real, ±0.0240 known world). (4) The count reads "middles whose argmax margin is below
  2ρ₂ or 2ρ₃". (5) Test (ii) requires the search to end at (2), and ν, ν_g, Θ and ρ₃ keep their
  formulas with the injected friction. (6) D20 states its node-sum form, whose gradients are exact
  for the rule (tested against finite differences of the 64-node τ); D26 gains a quadrature form:
  g is even in z, so ∇g(0) = 0, and a node-by-node projection gap makes g rise off z = 0, up to
  the rule's error along the chord; the known world cites it. (7) The benchmark's caveat says
  "sign": rounding can make the computed E non-monotone, but the bisection uses only its sign,
  which can be wrong only where |E| ≤ ν + ‖∇E‖·ρ_pt.
- **Contract and registry** (2026-09-25) — contracts.md §4 is Z's contract (`0f9ad7c`; §3 stays
  reserved for the frozen K8 record), and the registry rule `z` (`53022bd`, LEDGER seq 68) makes
  the contract hook deny Edit/Write on tools/experiments/zoom_*.py and tests/unit/test_zoom_*.py
  unless context_pack served §0 and §4. Next: the implementation by `instrument-implementer`,
  test-first, then the blind phase-2 review.
- **Implementation** (2026-09-25) — `instrument-implementer`, test-first, `cb421ff` on
  `feat/zoom-impl`: the script, its tests and the tests of D17, D19–D21 and D23–D26; not yet
  reviewed. Its known-world run found exact ties: the smallest relative display gap was 0.
- **Changes in revision 9** — the known world's offsets, after that finding (the author,
  2026-09-25). frac(ι·(√5 − 1)/2) moves by one of two steps, (√5 − 1)/2 or (√5 − 3)/2, so a
  pair's three offsets were equally spaced whenever both its steps were the second: 6 of the 28
  pairs. In each of such a pair's two axis cells its middle note was exactly as far from the
  other two, rounding ordered the tie, and the quadrature control's 128-node m₀ could order it otherwise
  and fail null_world on a correct pipeline; revision 6 had ruled out the ties of axis
  permutations only. null_world passed at that run; the implementer relaxed its own test of the
  gap from > 0 to ≥ 0 and reported the ties. The offsets become frac(ι²·(√5 − 1)/2), equally
  spaced for no pair whichever offset is the middle one (Controls, null_world), and the unit
  tests require that and a positive smallest gap. No arm's design changes, so there is no
  phase-1 round (METHODOLOGY.md): phase 2 checks it against the code.
- **Revision 9 implemented** (2026-09-25) — `instrument-implementer`, `33a12e3`: the offset line
  and the two tests, red on the earlier offsets for the stated reasons (6 pairs equally spaced, a
  smallest display gap of 0), then green; the full suite passed.
- **Phase 2, round 1** — `instrument-auditor` subagent, blind by construction (package built from
  `33a12e3`, lock set), 2026-09-25, phase 2 (code, before the first run), round 1: **PASS**, 0
  blocking, 12 non-blocking; every line of the record mapped to code; D5, D17, D19–D21 and
  D23–D26 tested; contracts.md §0 and §4 conform down to the data layer; revision 8's seven items
  and revision 9's offsets verified against the code, with D20's node-sum and D26's quadrature
  forms, never reviewed in a phase-1 round, checked by the reviewer; no result exists. The
  reviewer did not open the packaged results of other records and disclosed the memory index,
  the project instructions and recent commit messages in its context (other records' outcomes,
  Z's process status; nothing on Z's hypothesis or results). Non-blocking, to fix before the
  first run: (1) code the record does not describe — the score cache, exact since the ranks are
  fixed per run, and the --out option; (2) a failed search still gives the three-point arm its
  last point as a middle, which is scored and enters D_q, the quadrature control, the reported
  figures and Z2; valid is then false, but the record does not say so; (3) a line without a sign
  change at z = 0 fails search_code (no_sign_change), unnamed in the record; (4) Z2's timed
  search reuses the line built in the Z1 pass, so the QR for Z_N is not timed, and the per-step
  frames filter each note's cell, computed once per corpus, against "recomputed from scratch";
  (5) the keyframes arm reads the clock once more inside its timed call and only one overhead is
  subtracted, so each Δ_q carries about one timer read against keyframes; (6) the warm-up takes
  the first 10 targets with a route, not the first 10 EVAL targets; (7) the engine also computes
  the dominant attractor at traianus/app.py:693-696; (8) the K6 pin is checked by the pinned
  module's own check_digests, so an edit that disabled it would disable the pin at run time (the
  unit test hashes the file independently); (9) no test makes n_scored fail; (10) D21's test
  uses one fixed case, not random inputs; (11) "as its contract will state" is stale; (12) the
  smallest d is taken over every target, excluded ones included.
- **Changes in revision 10** — the twelve phase-2 round-1 items, no change to either arm's design
  (the author, 2026-09-25, who chose to declare item 2, to fix items 5 and 8 in code rather than
  declare them, and a second phase-2 round). Record only: (1) a score is computed once per
  identical view and display and reused, which is exact, and --out is declared; (2) a search
  that fails after its first point still gives the three-point arm its last point, which is
  scored, but valid is then false and its figures are diagnostics only; (3) no_sign_change at
  z = 0 fails search_code, and no later z can meet it; (6) the warm-up takes the first 10
  targets with a route; (7) traianus/app.py:693-696 joins the dominant-attractor citation;
  (11) the draws cite §4. Record and code: (4) the timed search builds its line again (u, Z_N,
  d) inside its interval, and what is computed once per run, untimed and shared by both arms, is
  declared (the quadrature nodes and weights, the notes' axis coordinates and dominant
  attractors); (5) the overhead is subtracted once more from the keyframes arm's total, for its
  timestamp read; (8) the script hashes the K6 module's file with hashlib, not through the
  module's check_digests; (12) the smallest positive d is reported. Tests: (9) n_scored fails
  with fewer than 20 targets scored in both arms, and with fewer than 20 with a route; (10) D21
  on random synthetic frictions; and a test for each code change. The code goes to phase 2,
  round 2.
- **Revision 10 implemented** (2026-09-26) — `instrument-implementer`, `a4e9274`: items 4, 5, 8
  and 12 in code, each with a test that was red before its change; the n_scored tests (item 9),
  which pass on the existing code and were shown to fail by breaking each clause in turn; D21's
  tests on 200 random synthetic frictions (item 10), with the half-chord, centre and directions
  drawn too; the full suite passed. Its report found item 2's wording loose.
- **Changes in revision 11** — one sentence, no change to either arm's design (2026-09-26): a
  failed search's m is mid(z) at the last iterate whose mid(z), g and ∇g step (1) computed, not
  "the last point it evaluated" — at the cap the last accepted step is never evaluated, and a
  failure while evaluating a later point leaves the iterate before it.
- **Phase 2, round 2** — `instrument-auditor` subagent, blind by construction (package built from
  `05adb96`, lock set), 2026-09-26, phase 2 (code, before the first run), round 2: **CHANGES**, 1
  blocking, 6 non-blocking; round-1 items 1–12 resolved in record and code; revision 11's
  sentence matches the code; D5, D17, D19–D21 and D23–D26 tested; contracts.md §0 and §4 conform;
  no result exists. The reviewer did not open the packaged results of other records and
  disclosed the memory index, the project instructions and recent commit subjects in its context
  (nothing on Z's hypothesis or results). Blocking: (B1) the per-step arm calls level 2 in full at
  P = B, eigh and display included, keeps only its partition and builds the level-2 state again
  at t = 1, so it computes N_f + 1 states against the record's N_f — unequal work per arm
  (failure pattern 1), which moves every Δ_q toward keyframes being faster by an amount unknown
  before the run; the Z2 tests replace both arms or check only their order, so none sees it.
  Non-blocking: (N1) a search that fails at its first point leaves no m and no three-point arm,
  so the target drops out of D_q and Z2 while its two-point arm is still scored — unstated;
  (N2) no test pins which point a failed search leaves (e.g. at a cap of 1, m = m₀ although a
  step was accepted); (N3) the reported-figures line still says "the smallest d"; (N4) the K6
  module is said to be imported for three functions only, but check_pin also raises its
  IntegrityError; (N5) both docstrings cite revision 10; (N6) the lists in quadrature_control
  lack annotations (mypy, outside CI).
- **Changes in revision 12** — B1 and the six non-blocking items, no change to either arm's
  design (the author, 2026-09-26, who chose the level-2 frame at P = B exactly and to name the
  exception rather than define one). (B1) The per-step arm computes the level-2 partition alone
  — T_cell, the Lloyd iteration and the EVAL assignment — and builds the level-2 state once, at
  t_f = 1 and P = B exactly, so each arm builds each state it shows once (3 against N_f); a test
  counts the states per arm. (N1) A search that fails at z = 0 is stated: no m, no three-point
  arm, the target out of D_q and Z2, the two-point arm still scored after a non-positive slope.
  (N2) A test pins which point a failed search leaves. (N3) "the smallest positive d" in the
  reported figures. (N4) IntegrityError is named among the imports, here and in contracts.md §4.
  (N5) The docstrings cite this revision. (N6) The lists are annotated. The code goes to phase
  2, round 3.
- **Revision 12 implemented** (2026-09-26) — `instrument-implementer`, `83870fa`: the level-2
  partition split from its state (level2_partition), so the per-step arm builds its level-2
  state once, at P = B exactly; tests that count the states each Z2 arm builds (3 and N_f, the
  degenerate end state included) and that its last frame is the keyframes arm's end state bit
  for bit, both red before the change; a test that a search stopped by a cap of 1 leaves m₀,
  shown able to fail; the reported key is smallest_positive_d; Z1's states unchanged bit for bit
  on four synthetic corpora; mypy clean on the script; the full suite passed. Its report found
  the failed-search sentences ambiguous at z = 0 and for a difference point of H.
- **Changes in revision 13** — wording only, no change to either arm's design (2026-09-26): a
  failed search leaves m at the last iterate whose mid(z), g and ∇g step (1) computed, whatever
  failed after them (a difference point for H, a trial, the next iterate's evaluation); at z = 0
  that is m₀, with D_q = 0; only a failure inside the first evaluation leaves no m.
- **Phase 2, round 3** — `instrument-auditor` subagent, blind by construction (package built from
  `ec26df4`, lock set), 2026-09-26, phase 2 (code, before the first run), round 3: **PASS**, 0
  blocking, 4 non-blocking; round 2's B1 and N1–N6 resolved in record and code; revision 13's
  sentences match the code on every path; every record line mapped; D5, D17, D19–D21 and
  D23–D26 tested; contracts.md §0 and §4 conform; no result exists. The reviewer did not open the
  packaged results of other records and disclosed the memory index, the project instructions and
  recent commit subjects in its context (nothing on Z's hypothesis or results). Non-blocking, to
  fix before the first run: (1) only the cap case of the failed-search sentences is tested — a
  difference point of H failing after the first iterate, a non-positive slope at a later
  iterate, and at z = 0 a non-positive slope (two-point arm only, ρ₂ null) or no sign change
  (neither arm) are correct by reading but untested; (2) the record says "Euclidean; ties by
  lower index", while the display order uses the squared distance, the same order in exact
  arithmetic, but in float64 the square root can merge two distinct squared distances into a
  tie; (3) the counts look only at arms that exist, so a target whose search fails inside its
  first evaluation adds no degenerate or not-scored state and Z1's n can fall short without a
  count explaining it; (4) the docstrings cite revision 12, the last revision that changed code
  — state that convention once.
- **Changes in revision 14** — the four phase-2 round-3 items, after phase 2 closed; no change to
  either arm's design, and no further round, as for K6 (the author, 2026-09-26). (1) The test
  list adds the other paths of a failed search: a difference point of H failing at a later
  iterate, a non-positive slope at a later iterate, and at z = 0 a non-positive slope (two-point
  arm only, ρ₂ null) or no sign change (neither arm), such a target out of D_q and Z2. (2) The
  display order is by squared Euclidean distance, stated with the reason. (3) The state counts
  see only existing arms; a search failing inside its first evaluation shows only among the
  failed searches. (4) The docstrings cite the last revision that changed code.
