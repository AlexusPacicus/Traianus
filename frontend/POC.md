# RefApp-01 — Proof of Concept

Step 0 of the research loop ([`docs/methodology/METHODOLOGY.md`](../docs/methodology/METHODOLOGY.md))
applied to the PKM client. RefApp-01 owns every application-domain concept (notes, navigation);
it talks to the engine over HTTP only and never imports `traianus/`.

## Layers

- **Traianus** (implicate order) — the state engine: governed, append-only transitions over the
  384-d substrate; the only layer that changes state.
- **Ulpia** (explicate order) — observation, O_n = P_θ(S_n): projects the state onto the map and
  never mutates it (Perspective Non-Interference, ADR-024).
- **RefApp-01** (this directory) — the PKM client.

## Problem

**What it demonstrates:** a person navigates the Spinoza corpus on a coloured spatial map — zooming,
adding notes, interacting between them — and chooses any note as the perspective from which the map
is redrawn. What makes it different is the method underneath: the map is a deterministic Ulpia
observation of a governed Traianus state.

**Features:**
1. Overview map of the corpus in 5D: position (x, y) from the anchor and first dipole, colour
   (l, c, h) from three further dimensions the position does not carry — the second dipole (axes
   4–5) among them. Same idea as `project_to_5d` (`observables.py`), in the per-epoch geodetic
   frame instead of a global SVD.
2. Zoom and pan.
3. Perspective: select a note, and the map is redrawn from it.
4. Note entry: write a note → `pending_approval` → consolidate (dual key) → it appears on the map.
5. Interaction: selecting a note shows its text and draws its relations (`/relations`) on the map.

**v2, not this PoC:** comparing several notes, anchoring one and interacting with others; the
engine's `/mutate` (a new basis axis and epoch).

**Data:** the frozen Spinoza corpus (`data/spinoza/`), plus the notes written during the PoC.

**No parallel store.** The engine already holds text (`manifold_nodes.text`), vectors
(`data_plane`), lifecycle and edges, all append-only. RefApp-01 keeps no database of its own and
reads everything over HTTP. Drift telemetry, if shown, is displayed only: it never freezes,
recalibrates or re-anchors anything (ADR-024, AGENTS 4.3).

**Out of scope:** multi-user security, adaptive codebook K(t), content filters, sync, performance
beyond the size of the Spinoza corpus.

## Hypothesis and refuters

**Hypothesis:** navigating the corpus as Ulpia observations of Traianus state — an overview and
note-chosen perspectives — gives a map that is reproducible, never disturbs the state it shows, and
places each note's real neighbours near it.

**Refuters:**
- **R1 — reproducibility.** The same state, epoch and perspective produce a different map across
  two runs. Checked by a test.
- **R2 — non-interference.** Any navigation (zoom, perspective, overview) writes to the state:
  a new revision, a lifecycle change, a new edge. Checked by a test over the observation endpoints.
- **R3 — governance.** A note reaches the map as consolidated without both keys. Checked by a test.
- **R4 — neighbourhood.** From a chosen perspective, a note's real neighbours in the 384-d
  substrate are not near it on screen. Measured offline (below).
- **R5 (exploratory, one user).** Navigating the map is less useful than a plain list of related
  notes. Judged by the author on day 7, labelled exploration, not result.

## Claims

Every figure this PoC relies on or produces. Vocabulary: `docs/methodology/instrumentation/
INSTRUMENTATION.md`. No CI verifier: this is a PoC, and a verifier is added only if a claim heads
to a publication. A figure without a row here is not used to decide anything.

| ID | Claim | Status | Pre-registered | Instrument audit | Source |
|---|---|---|---|---|---|
| K1 | On the unit sphere with a unit anchor, d_esc² = 1 − y² − λ²‖v_dipole‖² | construction | n/a (algebra) | — | ADR-026 §1; `spatial_observables.py` docstring |
| K2 | `c = (λ+1)/2` is the x coordinate rescaled; `h = tanh(d_esc)` is fixed by (λ, y) and the dipole norm | construction | n/a (read from code) | — | `derive_spatial_observables` |
| K3 | The overview picks anchor and dipole per node, not per epoch | construction | n/a (read from code) | — | `spatial_observables.py:159-160` |
| K4 | corr(tanh d_esc, y) = −0.968 on Spinoza (n = 2,221) | unbacked | no | — | ADR-026; `tools/experiments/measure_polar_render_range.py` is uncommitted and writes no artifact. Also measured on the per-node frame (K3) |
| K5 | Raw ranges: λ 7.16% of [−1, 1], anchor component 19.07%, x–y box 1.36% of the viewport | unbacked | no | — | as K4 |
| K6 | Each colour channel carries variance independent of (x, y) in the per-epoch frame | pending | — | record below (day 2) | day 2 script |
| K7 | R4: recall@15 per perspective, operator / radial / overview | pending | — | record below (R4) | day 6 script |

K4 and K5 are not used for any decision until their script is committed and re-run on the
per-epoch frame.

## Scope changes

Each change after this file's first commit is recorded here with its date and reason. A change
that leaves the written scope goes to v2.

- **2026-09-18 — baseline.** Scope set by the author: Spinoza corpus, 5D coloured map, zoom,
  perspective, note entry, interaction reduced to text + relations of a selected note. Earlier
  drafts the same day (a projector-only demo; comparing several notes) were superseded before any
  work ran.

## Deadline

- **Window:** 2026-09-18 → 2026-09-25. Past it, anything that is not a factual error goes to a v2.
- **Checkpoint 2026-09-22:** the Spinoza corpus on the coloured overview, zoom working, and
  selecting a note redraws the map from it. If not reached, cut in this order:
  1. dimensional increase;
  2. interaction between notes (feature 5);
  3. WebGL, replaced by Canvas 2D.

| Day | Work |
|---|---|
| 1 | This document; smoke run of the current client and engine; review of the R4 audit record; commit docs |
| 2 | Engine: per-epoch 5D frame — choose the three colour dimensions and measure their independence from (x, y) on Spinoza; R1–R3 tests |
| 3 | Engine: `/spatial` on the epoch frame; `GET /spatial?anchor=<id>` — TDD, through the boundary-validator |
| 4 | Checkpoint |
| 5 | Client: note entry and consolidation; feature 5 (text + relations) |
| 6 | R4 offline measurement; dimensional increase if nothing was cut |
| 7 | Close: ledger entry, results, R5 judgement |

**Dimensional increase (interaction).** When a note is anchored, the second dipole (axes 4–5)
moves from colour to a z axis — a genuine third axis, not a rescaling of the first (ADR-026 §2.1).
It enters only if the checkpoint is met. Every colour channel, and z, must carry variance
independent of (x, y) — the test d_esc failed (corr −0.968 with y). The compendium's "dimensional
pulsation" (cluster count set as dimension) is not this and is not used; the engine's `/mutate` is
a different mechanism (substrate, v2).

## Incubation and exit condition

Incubated here under the monorepo policy of `docs/LEDGER.md` seq 25; this file is the one
documented exception to that entry's sources-only rule. **At close (2026-09-25):** if the PoC
continues, this directory moves to its own repository with its history. Either way the identifiers
that mislabel this client as Ulpia (`package.json` `name`, `Ulpia*.tsx`, `ulpia_renderer.ts`) are
renamed then, not during the PoC.

## Open finding: the overview has no shared frame

`traianus/geometry/spatial_observables.py` (`derive_spatial_observables`) picks anchor and dipole
**per node**: each node's dominant geodetic axis becomes its own anchor, the next two its dipole.
Every node is drawn on the same (x, y) plane but measured in its own coordinate system, so two
nodes with different dominant axes can land together on screen by coincidence. A node never moves
as the corpus grows, but the overview is not a map. ADR-026's range figures were measured on this
placement.

Proposed fix, consistent with ADR-026: one frame per epoch (anchor and dipole chosen once, frozen
with the calibration). Perspectives are unaffected: every node shares the chosen note's frame.
Owner: the engine session that holds this file's uncommitted changes. Blocking for the checkpoint.

## Open finding: two of three colour channels repeat the position

In `derive_spatial_observables`, `c = (λ+1)/2` is the x coordinate rescaled, and `h = tanh(d_esc)`
is determined by (λ, y) and the dipole norm — constant once the frame is per epoch. Only
`l = 1/(1+var)` (variance of the note's projections on the geodetic basis, not the neighbourhood
density the render spec names) carries information the position does not. Decision (feature 1):
colour carries the next three dimensions of the epoch frame, as in the 5D design, so it cannot
repeat the position by construction.

## Built but not wired

`SemanticSimplex` (`simplex.py`), `ParabolicCorrector` (`parabolic.py`) and `SVDAnisotropyFilter`
(`svd_filter.py`) have no caller in the engine. The renderer already applies the parabolic
corrector in its vertex shader, so animated transitions between views (overview → perspective)
only need the engine to return the exact midpoint view — polish, cut before feature 5. The SVD
filter centres its data, so it removes the neighbourhood's direction of largest variance, not the
shared bias its spec describes; it must not be wired as is.

## Audit definitions (shared by the K6 and R4 records)

A reviewer reads this block and one record block, nothing else of this file.

```
Audit definitions

Vectors      v ∈ S^383, L2-normalized. Corpus: the 2,221 Spinoza chunks frozen by
             tools/experiments/tooling/freeze_spinoza_embeddings.py (commit f26186d; output
             .data/spinoza_frozen, gitignored), float32 on disk, used as float64.
Basis        8 NSM geodetic axes, tests/fixtures/nsm_axes_8.json (epoch PROSTHETIC_NSM_V1).
             Stored in table geodesic_axes (traianus/storage/_storage.py:114); epochs:
             docs/architecture/ARCHITECTURE.md §7.
Operator     traianus/geometry/polar_projector.py, for anchor c₁ and poles c_A, c_B:
               ĉ₁ = c₁ / ‖c₁‖;  P⊥x = x − ⟨x, ĉ₁⟩ĉ₁                          (:235-237)
               v_dipole = P⊥c_A − P⊥c_B  (collinear fallback 2δ·u⊥)          (:173-174)
               r = P⊥(v − c₁)                                                (:279)
               λ = clip(⟨r, v_dipole⟩ / ‖v_dipole‖², −1, 1)                  (:283-284)
               d_esc = ‖r − λ·v_dipole‖                                      (:290)
λ_k          λ with c₁ = the rank-1 axis and (c_A, c_B) = the k-th dipole's two axes.
Position     x = λ₁, y = ⟨v, ĉ₁⟩.

Allowed reading   these two blocks; the files and lines cited in them.
Not allowed       the rest of frontend/POC.md; docs/adrs/ADR-026-*; traianus/geometry/
                  spatial_observables.py (its docstring states prior results); data/spinoza/
                  telemetry/; docs/LEDGER.md; any manuscript.
```

## K6 measurement: colour channels independent of position (day 2)

**Question.** In a per-epoch geodetic frame, can three dimensions beyond position be shown as
colour without repeating it?

**Refuter.** No candidate is admissible under the rule below: in this frame colour cannot carry
information the position lacks. That is a decision point for the author, not a cue to change the
candidates (step 3).

### Instrument audit record (must be reviewed and committed before the first result)

```
Instrument audit — K6, colour channel independence

Data: the 2,221 L2-normalized Spinoza vectors from the frozen artifact (f26186d), as float64;
  the active basis of 8 NSM geodetic axes.
Frame (one per epoch): rank the 8 axes by mean signed projection over the 2,221 vectors.
  Anchor = rank 1; dipole 1 = ranks 2–3 → position x = λ₁, y = ⟨v, â₁⟩;
  dipole 2 = ranks 4–5; dipole 3 = ranks 6–7; rank 8 left over.
Candidates, in preference order: λ₂ (dipole 2), λ₃ (dipole 3), ⟨v, â₈⟩, l = 1/(1+var) of the
  8 projections.
Null: ⟨v, e⟩ for 1,000 fixed-seed random unit vectors e — how much an unrelated direction
  resembles the position in this (anisotropic) corpus.
Positive control: h = tanh(d_esc) of dipole 1 (K2: must come out redundant).
Column "R²": least-squares fit of the channel on (x, y, x², y², xy) over the 2,221 vectors.
Rule: admissible iff R² ≤ the 95th percentile of the null's R²; colour = the first three
  admissible candidates in order; fewer than three → the missing channels are constant.
  (Replaces a fixed R² ≤ 0.5 drafted the same day, which had no derivation.)

Same thing in every arm?   Every candidate, control and null direction on the same vectors, frame
                           and regression.
Leakage?                   The frame is fitted on the corpus it describes — by design, it is the
                           epoch's frame; no label or ground truth is read.
Comparable arms?           The positive control must exceed the null's 95th percentile; if it
                           does not, the instrument cannot detect redundancy and no candidate
                           result is used. Geodetic axes are not random: if they come out more
                           redundant than the null, that is a result for the author (step 3), not
                           a reason to relax the rule.
Text matches code?         Checked at review.
Reviewed by:               pending — `instrument-audit` skill, run by the author in a separate session.
```

## R4 measurement: operator and radial perspectives

The perspective shown uses the polar operator; a radial coordinate is computed alongside and never
rendered, and the overview is the third arm.

**Instrument: offline, not live.** A committed script under `tools/experiments/` over the frozen
Spinoza corpus, every node as the chosen perspective, all arms computed by the engine code the
endpoints serve. Live logs would sample only the notes the user happens to click.

### Instrument audit record (must be reviewed and committed before the first result)

```
Instrument audit — R4, perspectives: operator, radial, overview

Column "recall@15": for chosen note q, of q's 15 nearest neighbours in the 384-d substrate (q
  itself excluded), how many are among q's 15 nearest on the arm's 2D map, all N notes placed.
  Operator arm: c₁ = q; poles = the two geodetic axes of the active basis with the largest signed
  projection onto q; position (λ, ⟨v, q̂⟩), each axis z-scored over the N placed notes.
  Radial arm: (⟨v − q, e⟩, ‖v − q‖), e a fixed seeded random unit vector, same z-scoring.
  Overview arm: the per-epoch frame, identical for every q, same z-scoring. Added once that frame
  exists.

Same thing in every arm?   Same perspectives, neighbour sets, k and N; every map from the engine's
                           code path, not a re-implementation.
Leakage?                   Ground truth is the 384-d neighbourhood; no arm reads it.
Comparable arms?           Recall only; cost is not compared. Axis scaling is fixed before running,
                           because 2D neighbours depend on it; any other scaling is a post hoc
                           ablation.
Text matches code?         Checked at review.
Reviewed by:               pending — `instrument-audit` skill, run by the author in a separate session.
```

With c₁ = q on unit vectors, ⟨v, q̂⟩ = cos θ orders notes by distance exactly as ‖v − q‖ does, so
operator and radial share their vertical ordering and differ in the horizontal axis: λ, the
contrast between two geodetic poles, against a random direction.
