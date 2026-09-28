# TG — tension gate on cross-label relations

The question, hypothesis and refuters live in `docs/relational-bridges/RELATIONAL_BRIDGES.md` §22,
which a blind reviewer never opens (definitions.md, Not allowed).

## Instrument audit record (revision 1)

```
Instrument audit — TG, relations kept by a tension gate and the spiral they open (revision 1)

Scope: two existing relation graphs on the frozen corpus (union, open borders), each taken
  without the gate, with it, and with a blind draw in its place. The gate judges relations between
  notes with different labels by the tension of their joint neighbourhood along the relation's own
  direction, against blind random directions. Measured: for every EVAL note, how few relations
  separate it from its real neighbours (the spiral's turns), and each graph's relations per note.
  Not measured: display, colour, the rotation, the double way, the fusion order, the descent below
  the zones, the compass (none is part of this gate).
Words: each term below is the frozen glossary word of the question's document, in English:
  note (nota), axis (eje), affinity (afinidad), axis coordinates (coordenadas de eje), label
  (etiqueta), zone (zona), distance and length (distancia, longitud: the same quantity), real
  neighbours (vecinos reales), sphere (esfera), barycentre (baricentro), tension (tensión), bridge
  (puente), bridge sphere (esfera del puente), effort (esfuerzo), minimum spanning tree and its
  edges (árbol mínimo, enlaces mínimos), threshold (umbral), candidate (candidato), keep
  (mantener), cut (corte), blind reference (referencia ciega), tunnel and cone (túnel, cono),
  foreign note (nota ajena), marked bridge (puente marcado), split a neighbourhood (partir un
  vecindario), inconclusive (no concluyente), pending (pendiente), turn (vuelta), budget
  (presupuesto), blind draw (sorteo ciego), grid (parrilla), block length (tramo), interval
  (intervalo), FIT and EVAL notes (notas de ajuste, apartadas).
Symbols, each with one meaning here and none of definitions.md's (v, a_k, â_k, c₁, c_A, c_B, ĉ₁,
  P⊥, v_dipole, δ, u⊥, r, λ, λ_k, d_esc, x, y) or contracts.md's V; contracts.md §0's d = 384 is
  written 384:
  notes — v_i a note's 384-d vector, i, j, n, x note indices (0-based rows); c(v) ∈ ℝ⁸ its axis
    coordinates, c_i = c(v_i), c_{i,k} its k-th component, k only ever indexing axes;
    dist(i, j) = ‖v_i − v_j‖; lab(i) a note's label; Zn(i) the set of zones a note is in;
    N(i) its real neighbours (FIT), R(q) an EVAL note's real neighbours (EVAL);
  gate — Z_k the zone of axis k (its FIT notes), θ_k its threshold; S_ij the bridge sphere of
    i, j, S°_ij = S_ij ∖ {i, j} the same without its two ends, p°_ij the barycentre and T°_ij the
    tension matrix of S°_ij; b_ij the bridge's direction; e_ij(u) the tension of S°_ij along a
    unit u ∈ ℝ⁸; u_1…u_1000 the blind reference; κ_ij the cut; ρ_i an end's cone radius; σ the
    foot parameter of a note on the edge;
  graphs — G⁰ a variant without the gate, G⁺ with it, G^b with the blind draw; M the variant's
    minimum-spanning-tree edges (all notes); J the judged relations, K ⊆ J the kept ones;
    |E| a graph's relation count, β = 2|E|/2221 its budget;
  statistic — q an EVAL note; h_q(n) the fewest relations from q to n in a graph (its turn);
    C_q(t) = |{n ∈ R(q) : h_q(n) ≤ t}|; H the horizon; A_q = Σ_{t=1..H} C_q(t); D_q = A_q(G⁺) −
    A_q(G⁰), D′_q = A_q(G⁺) − A_q(G^b); D̄, D̄′ their means; L a block length, B = 10,000
    resamples, b a resample's index (never a direction).
Script: tools/experiments/tension_gate.py; unit tests: tests/unit/test_tension_gate.py; the tests of
  D27, D28 and D29 in tests/unit/test_audit_derivations.py. The script sets OMP_NUM_THREADS =
  OPENBLAS_NUM_THREADS = VECLIB_MAXIMUM_THREADS = 1 itself, before its first numpy import. It
  imports, and does not copy: check_digests, load_inputs, validate_inputs and IntegrityError from
  tools/experiments/k6_colour_predictability.py, pinned by sha256 =
  6289c596792154f6bb799606265c68719c6b8c7ae8b69084116dfb23c77876d2 as Z pins it; relations,
  pairwise_distances, minimum_spanning_tree, union_edges, axis_cells, median_threshold,
  touching_tree_weights, open_relations and cell_graph from
  tools/experiments/relational_graph_exploration.py, pinned by sha256 =
  627aa8e95a844b0aec290a41c48b9a0bf6890db25b5240b5730c366a56d2e7dc (the file at db12b60). Each pin
  hashes the file the module was loaded from with hashlib and refuses to run on a mismatch, with
  Z's declared limits (the file on disk, not the loaded bytes; top-level code runs on import).
  The engine's epsilon comes from traianus.config.resolve_epsilon_edge(); the script refuses to
  run unless it returns 0.8 (the variable TRAIANUS_EPSILON_EDGE would change it). Result:
  data/refapp/TG_result.json, committed; --out writes the same result elsewhere, not committed.
Data: definitions.md (2,221 vectors, 8-axis basis). The script refuses to run, writing nothing,
  unless the three sha256 digests Z's Data line names hold and validate_inputs accepts the inputs
  (contracts.md §0). Conversions as contracts.md §0: rows cast to float64 and renormalised;
  â_k = a_k / ‖a_k‖. FIT = even rows (1,111), EVAL = odd rows (1,110), as R4 and Z. Everything
  the gate uses to judge — zones, trees, thresholds, real neighbours, spheres, tunnels, efforts —
  comes from FIT notes only; every judged relation joins two FIT notes; the statistic is taken on
  EVAL notes only.
Axis coordinates: c(v) = (⟨v, â_1⟩, …, ⟨v, â_8⟩). Label lab(i) = argmax_k c_{i,k}, ties to the
  lower k (axis_cells). Distances: pairwise_distances, one binary64 value per pair, the engine's
  expression.
Zones (FIT): i ∈ Z_k iff c_{i,k} > (1/8) Σ_k′ c_{i,k′} (strict). The zone of lab(i) holds i unless
  its eight components are equal, which leaves i in no zone (counted, reported; such a note is
  never a judged end). Z_k's tree: minimum_spanning_tree over the FIT notes of Z_k (Prim from the
  zone's lowest row, ties to the lower row). θ_k = median_threshold of that tree's edge lengths
  (numpy.median). A zone with fewer than 2 FIT notes has no tree and no threshold and admits no
  candidate (counted).
Real neighbours: N(i) = the 15 FIT notes nearest to FIT note i by dist, i excluded, ties to the
  lower row. R(q) = the 15 EVAL notes nearest to EVAL note q among the other 1,109 EVAL notes, q
  excluded, ties to the lower row (R4's truth). 15 is R4's number, not chosen here.
Bridge: a pair of FIT notes with lab(i) ≠ lab(j). Its sphere S_ij = {i, j} ∪ N(i) ∪ N(j), a note
  in both counted once (at most 32 notes); S_ij defines the tunnel below. The effort is measured
  on S°_ij = S_ij ∖ {i, j} (between 14 and 30 notes: j may be in N(i) and i in N(j)), so that the
  ends' own separation, which lies wholly along b_ij and along no blind direction, does not
  enter — no note is measured against itself, as the engine's threshold calibration excludes
  self-projection. p°_ij = mean of c over S°_ij; T°_ij = ½ Σ_{x∈S°_ij} (c_x − p°_ij)(c_x − p°_ij)ᵀ
  (8 × 8).
Effort: e_ij(u) = ½ Σ_{x∈S°_ij} ⟨c_x − p°_ij, u⟩² = uᵀ T°_ij u for unit u (D29).
  b_ij = (c_j − c_i)/‖c_j − c_i‖; c_i ≠ c_j because the labels differ, so b_ij exists (its sign
  does not matter: e_ij(u) = e_ij(−u)). The effort is e_ij(b_ij).
Blind reference and cut: u_m = g_m / ‖g_m‖, g_m the m-th row of the draw below (uniform on the
  unit sphere of ℝ⁸, never looking at notes or text). κ_ij = the 12th smallest of
  e_ij(u_1), …, e_ij(u_1000) (index 11 of the ascending sort). Passes the cut iff
  e_ij(b_ij) < κ_ij (strict). If b_ij were exchangeable with the u_m, it would pass with
  probability 12/1001 (D27, the mirror of K6's D8).
Tunnel (384-d, FIT): ρ_i = dist(i, the 15th of N(i)). For a FIT note x ∉ S_ij,
  σ = ⟨v_x − v_i, v_j − v_i⟩ / ‖v_j − v_i‖²; x is inside the cone iff 0 ≤ σ ≤ 1 and
  ‖v_x − v_i − σ(v_j − v_i)‖ ≤ (1 − σ)ρ_i + σρ_j. Foreign notes of the bridge: the FIT notes
  inside the cone and not in S_ij. The bridge is marked iff it has one or more (their number
  reported). It is vetoed iff some foreign note x has neither i nor j in N(x) (x kept its
  neighbours apart from the bridge, and the bridge crosses it).
Candidates and verdicts: shared = Zn(i) ∩ Zn(j). If shared is not empty, the bridge is a candidate
  in zone k ∈ shared iff dist(i, j) ≤ θ_k; if shared is empty, it is a candidate iff
  dist(i, j) ≤ min(θ_lab(i), θ_lab(j)) (its own sphere). A candidate is kept in a zone (or in its
  own sphere) iff it passes the cut and is not vetoed. The effort, the cut and the tunnel depend
  only on the two ends: each is computed once per pair, whatever the number of zones; only
  candidacy differs between zones. One verdict per zone, counted per zone: candidates, kept,
  marked, vetoed.
Variants (all 2,221 notes, built with the imported functions, unchanged from the exploration):
  union — relations(labels, v, 0.8) ∪ M, by union_edges; open borders — open_relations(d, cells,
  t) ∪ M, cells = axis_cells, t_k = median_threshold of touching_tree_weights(M, cells, 8)[k];
  M = minimum_spanning_tree(d) over all notes. Dense per-cell reference (budget only): the
  within-cell relations of cell_graph(d, cells, 8) (threshold = the longest edge) ∪ its cross-cell
  tree edges.
Three graphs per variant (the only difference between them is the set of judged relations):
  J = the variant's relations joining two FIT notes with different labels that are not in M,
    together with every candidate pair not already a relation of the variant (the relations the
    variant already has are judged by the cut and the tunnel alone; added pairs must also be
    candidates in some zone or in their own sphere).
  K = the members of J kept: a relation the variant already has iff it passes the cut and is not
    vetoed; an added pair iff it is kept in at least one zone, or in its own sphere.
  G⁰ = the variant as it is. G⁺ = (variant ∖ J) ∪ K. G^b = (variant ∖ J) ∪ K^b, K^b = |K| members
  of J drawn without replacement (Draws). M ⊆ G⁰, G⁺, G^b, so all three are connected; relations
  touching an EVAL note or joining two notes with the same label are never in J.
Statistic: for each EVAL q and each graph, h_q(n) by breadth-first search over all 2,221 notes;
  C_q(t) and A_q = Σ_{t=1..H} C_q(t), H = the largest turn any EVAL note has in any of the
  variant's three graphs (the eccentricity maximum; reported). By D28, A_q = 15(H + 1) −
  Σ_{n∈R(q)} h_q(n), so D_q = Σ h_q(n)(G⁰) − Σ h_q(n)(G⁺) and D′_q likewise: the differences do
  not depend on H. D̄ = mean of D_q over the EVAL notes in scope, D̄′ likewise.
Scopes: global (all 1,110 EVAL notes) and each zone k (the EVAL notes q with c_{q,k} > the mean of
  their own eight components; a note may be in several zones; zones are not mixed).
Dependence and interval (R4's): for a scope with n notes and each L in the grid {1, 2, 5, 10, 20,
  50}, the scope's EVAL notes in row order are cut into ⌈n/L⌉ contiguous blocks (the last may be
  shorter); L is valid iff ⌈n/L⌉ ≥ 20; an invalid L does not decide. For b = 1…10,000 the blocks
  are resampled with replacement (with multiplicity) and D̄_b computed; interval =
  [sorted(D̄_b)[249], sorted(D̄_b)[9749]]. The same for D̄′.
Rule, per variant and scope:
  (1) more neighbours per turn at no larger budget: if at some valid L the interval of D̄ contains
      0, inconclusive; if at every valid L it lies above 0 and β(G⁺) ≤ β(G⁰), holds; otherwise
      refuted.
  (2) budget below the dense per-cell reference: refuted iff β(G⁺) ≥ β(dense); else holds.
  (3) better than the blind draw: as (1) with D̄′, without the budget clause (G^b has |G⁺|
      relations by construction).
  A scope with no valid L is pending (no decision, not filled by hand). The gate holds for a scope
  iff (1), (2) and (3) hold for both variants; it is refuted iff any of them is refuted in either
  variant; otherwise inconclusive. An inconclusive zone triggers the fixed descent (outside this
  record). Single bridges are kept or discarded by the cut, once; they are never inconclusive.
Controls (each can fail; a failure makes the run invalid and no result is used):
  exchangeable direction — for every pair in J, e_ij(w_ij) with w_ij an independent uniform
    direction (Draws) is compared with κ_ij; the fraction below the cut must lie within
    12/1001 ± 4·√((12/1001)(989/1001)/|J|). A correct cut falls outside with probability ≈ 6e-5
    (normal tail at 4 s.d., as R4's permutation control).
  ceiling — the graph whose relations join each EVAL q to every note of R(q): every h_q(n) = 1,
    so Σ_{n∈R(q)} h_q(n) = 15 for every q; the breadth-first search and the sum must return it
    exactly.
  connectivity — G⁰, G⁺ and G^b are one component each (else an h is undefined).
  equal budget — |G^b| = |G⁺| for each variant.
Draws: rng = numpy.random.default_rng(20260918) (PCG64), used in this order and nowhere else:
  g = rng.standard_normal((1000, 8)) (the blind reference); then, for the pairs of J over both
  variants, each pair once, in ascending (i, j), w = rng.standard_normal((number of pairs, 8)),
  row by pair (the exchangeable-direction control); then, for union and then open borders,
  rng.choice(|J|, |K|, replace=False) indexing that variant's J in ascending (i, j) (the blind
  draw, one fixed draw per variant); then, for union and then open borders, for D̄ and then D̄′,
  for the global scope and then the zones in axis order, for each valid L ascending and b = 1…10,000,
  rng.integers(0, n_blocks, n_blocks).
Reported, not deciding: |J|, |K|, the kept fraction; per zone, candidates, kept, marked and vetoed;
  foreign-note counts; H; β of every graph and of the dense reference; the number of zones per
  FIT note; θ_k per zone; notes in no zone; the interval at every L, valid or not; sorted(D̄_b)
  at 233/265 and 9733/9765 to show a decision does not hinge on Monte Carlo noise.
Unit tests (committed with the script, reviewed in phase 2; they can fail): D27, D28, D29 on
  random inputs; the cone membership on hand-built points (inside, on the surface, beyond each
  end); zone membership and label ties; N(i) and R(q) exclude the note itself and break ties by
  row; the cut is strict; the three graphs differ only in J; the draw order and the first
  components of g from seed 20260918 pinned; the controls fail on injected faults; the inputs are
  validated before use (contracts.md §0, Integrity).

Same thing in every arm?   G⁰, G⁺ and G^b share every relation outside J, the same notes, the
                           same breadth-first search and the same R(q); G⁺ and G^b differ only in
                           which members of J they keep, and keep the same number.
Leakage?                   The gate reads FIT notes only; the statistic reads EVAL notes only, with
                           their truth R(q) among EVAL notes. Declared: the variants' own relations
                           (epsilon, open-border thresholds, the tree M) are built over all notes,
                           EVAL included, but they are the same in every arm.
Comparable arms?           Valid only if the four controls pass. The ends are left out of the
                           effort (Bridge), so the construction adds no tension along b_ij by
                           itself. Declared: b_ij still depends on the ends, and each end's real
                           neighbours lie near it, so b_ij is not exchangeable with the blind
                           directions whenever the neighbours carry information; 12/1001 (D27) is
                           the pass rate of a direction that carries none, which the
                           exchangeable-direction control checks, not a bound for real bridges.
Text matches code?         Checked at review (phase 2).
Reviewed by:               Claude Sonnet 5 (instrument-audit, blind subagent), 2026-09-28, phase 1,
                           record at 4c0fa17 (revision 1): PASS; 0 blocking, 5 non-blocking.
```

## Review history

- **Revision 1** — Claude Sonnet 5 (`instrument-audit`, blind subagent), 2026-09-28, phase 1, round
  1 on this design, record at `4c0fa17`, package built after `fb9b6a2` (the builder's denylist
  gained `docs/relational-bridges/`; a first package built before that fix held the question's
  document and was discarded unread): **PASS**, 0 blocking, 5 non-blocking. (1) The Symbols line
  disclaims symbols this record never uses, and â_k here is definitions.md's: say it is a blanket
  disclaimer. (2) "Z's Data line", "R4's" interval and "R4's permutation control" point at records
  a blind reviewer cannot open: state the digests and the resampling here. (3) No contracts.md
  section for TG yet; needed before any code. (4) The equal-budget control is an identity of the
  construction, a code check rather than an empirical one: say so. (5) Rule (2) does not depend on
  the scope: say so.
