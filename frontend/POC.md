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

**Corpus loading (decision, 2026-09-18).** The engine is loaded by ingesting the frozen
artefact's vectors one at a time, in text order, through `/ingesta/vector` — never by
re-encoding the texts and never in bulk. Two reasons: the vectors are then bit-identical to the
ones K6 and R4 measure (binary32 → binary64 is exact), closing the gap declared in
`audits/contracts.md` §0; and the state is built note by note, S_{n+1} = f(S_n, v_n), which keeps
the arrival order in the revision log. Corrected 2026-09-19 against the code: within one epoch
the threshold, lifecycle state and ε-edges do *not* form against the notes already present (see
"Exploration: relational loss under arrival order"). To verify on day 3, in the contract:
`/ingesta/vector` must not re-normalise in a way that changes the stored bits.

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
- **R4 — neighbourhood.** In a 5D perspective chosen at a note, the horizontal axis and the
  colour channels scatter its real 384-d neighbours more than an arbitrary horizontal axis would.
  Measured offline (`audits/R4.md`).
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
| K6 | Each colour channel is not second-order predictable from (x, y) or from the colour channels chosen before it, in the per-epoch frame | pending | — | `audits/K6.md` | day 2 script |
| K7 | R4: paired recall@15 difference in the 5D perspective, operator vs. radial | pending | — | `audits/R4.md` | day 6 script |

K4 and K5 are not used for any decision until their script is committed and re-run on the
per-epoch frame.

## Scope changes

Each change after this file's first commit is recorded here with its date and reason. A change
that leaves the written scope goes to v2.

- **2026-09-18 — baseline.** Scope set by the author: Spinoza corpus, 5D coloured map, zoom,
  perspective, note entry, interaction reduced to text + relations of a selected note. Earlier
  drafts the same day (a projector-only demo; comparing several notes) were superseded before any
  work ran.
- **2026-09-18 — R4 reformulated, before any result.** The blind review of R4 revision 1 showed
  that in a perspective at q the vertical axis ⟨v, q̂⟩ is the real-distance order itself, so the
  refuter could not test what it claimed. R4 now asks whether the other four dimensions (λ and
  colour) scatter that order more than an arbitrary horizontal axis, measured in 5D with equal
  weights, as the author specified. The overview left R4: it has no chosen note.
- **2026-09-18 — related-notes list added (for R5).** R5 compares the map with a plain list of
  related notes, which the client did not have: selecting a note also lists its 15 nearest notes.
  Built with feature 5 on day 5; it is the control view R5 needs, not a new feature.

## Day-7 decision (pre-registered 2026-09-18, before any result)

| Outcome | Decision |
|---|---|
| R1–R3 tests fail | Fix the engine; mandatory, not a reason to pivot |
| Checkpoint missed on day 4, even after the cuts | One extension of 3 days, decided on day 4 and logged in Scope changes (window to 2026-09-28); no second extension |
| K6 admits no channel (m = 0) | In the geodetic frame colour adds nothing: the map is 2D. Pivot within Ulpia: look for another colour source (e.g. a per-epoch data-derived frame) |
| R4 holds | λ loses the perspective's horizontal axis; the perspective stays, with another axis |
| R5 favours the list | RefApp-01 continues list-first: related notes as the main view, the map as context. Engine and Ulpia unchanged |
| All favourable | Continue: RefApp-01 leaves for its own repository (exit condition) and v2 is scoped |

**R5 protocol.** Ten real navigation tasks ("find the notes related to X"), written and committed
before day 5. On days 5–7, for each task the author records which view was used (map or list)
and whether the task was completed. The majority decides; ties go to the list. Exploratory: one
user, labelled as such.

**Audit freeze.** If the phase-1 review of R4 at `c08fe92` does not return PASS, the record is
frozen as it stands; remaining items are resolved in phase 2 against the code.

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
| 5 | Client: note entry and consolidation (incubating shown as its own state); feature 5 (text + relations) and the related-notes list; R5 tasks committed before starting |
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

## Instrument audits

Records live in [`audits/`](audits/), one file per measurement, so a blind review never opens this
file: [`definitions.md`](audits/definitions.md) (shared), [`K6.md`](audits/K6.md) (colour channel
independence, day 2), [`R4.md`](audits/R4.md) (neighbourhood recall per perspective, day 6).

## Smoke run, day 1 (2026-09-18) — exploration, not results

Engine from the working tree as it stood (including uncommitted engine work), run from a scratch
directory so SQLite created its own `traianus.db` there — `DB_PATH` is relative and has no
environment override; the repository's database was not touched. Bootstrap (8 axes), 30 Spinoza
chunks (six per part) through `/ingesta`, then the client.

| Step | Outcome |
|---|---|
| Text ingest (`/ingesta`, `X-Traianus-Token`, `X-Idempotency-Key`) | Works: 30/30 accepted, 30 nodes in `pending_approval` |
| `/spatial` | Returns all nodes, pending included; the client does not show lifecycle state |
| Consolidate with the ethical key | Node goes to `incubating`, not `consolidated`: topological key failed (variance 0.0016 < threshold 0.0043). Feature 4 may rarely reach `consolidated` on this corpus |
| Map | Renders; every node in one small overlapping blob, one colour — consistent with K2/K3 |
| Note entry from the UI | Reaches the engine (node 31), but the client refetches `/nodos` and `/relations`, not `/spatial`, so the new note is not drawn until reload |
| Zoom, click on a node | Not implemented: the WebGL layer has `pointerEvents: "none"` |
| Console | One warning: `gl.enable(PROGRAM_POINT_SIZE)` is invalid in WebGL2 (point size is always on) |

Consequences for the plan: feature 4 must show `incubating` as a state of its own; the client
must refetch `/spatial` after ingest; zoom, click and perspective are all new client work (days
3–5), none of it exists yet. A `DB_PATH` environment override would make isolated runs routine.

## Exploration / v2: faces of a concept polytope (author's idea, 2026-09-18)

Not in this PoC's scope: it arrived mid-run, and adopting it now would be a reformulation without
the loop's gate. Recorded so it enters v2 through steps 1–2.

**Idea.** The 8 geodetic axes, in general position, span a 7-simplex: all 56 triangles of three
axes are faces. Instead of notes floating in a space, the user sees a 3D polyhedron of named
concepts from outside, with each note placed on a face by its barycentric coordinates relative to
that face's three axes. The 3D polyhedron is not the 7-simplex; it is a projection of it,
parametrised by the user's choice (Ulpia's O = P_θ(S), θ chosen by the observer; the state never
changes, ADR-024). Choosing a note brings to the front the face of its three leading concepts;
neighbouring faces share two. The current perspective's frame (c₁, c_A, c_B) — `SemanticSimplex`
in `traianus/geometry/simplex.py` — is already one such face seen head-on.

**Conditions it must meet.**
1. Deterministic given θ (R1): vertices placed in 3D by classical MDS of the 8 axes' Gram
   matrix, so the layout comes from the basis, not from chance; the user chooses the face.
2. The projection shows itself as a projection: vertices always labelled with their concepts and
   the active face named, so an artefact of the 3D rendering is not read as corpus structure.
3. Its loss is measured: the MDS stress of the 7-to-3 placement is reported.

Open difficulties: barycentric coordinates need non-negative weights, and projections can be
negative (any transform distorts); a note that mixes many concepts evenly belongs to no face well;
and R5's question — does it help navigation more than a list? — applies to it too.

**Cheap version, candidate for day 5 if there is margin:** in the perspective view, draw the
triangle (c₁, c_A, c_B) with its three concepts' names at the vertices.

## Exploration: one-at-a-time vs. batched encoding (2026-09-18)

**Question (author's).** Encoding notes one at a time keeps their relations whole; encoding them
in a batch may lose or gain relations.

**Refuter.** On the 2,221 Spinoza texts, the 15-nearest-neighbour set of some note differs
between one-at-a-time and batched encoding for reasons other than near-ties (two similarities to
the note within 1e-6 of each other). Also reported: max |G_single − G_batch| over all pairs, and
the structure of Δ_i = v_single,i − v_batch,i (norms, a shared direction, correlation with text
length or part).

**Expected, stated before measuring:** the encoder isolates each text in a batch (attention mask,
mask-aware pooling), so Δ is float32 rounding and the neighbour sets agree except at near-ties.
Where the author's point does hold is the engine, not the encoder: Traianus is stateful, and
ingesting one note at a time builds the state's trajectory (see Corpus loading).

Exploration branch: not in the PoC's scope, no gate; it enters a registry only after its own
instrument audit.

## Exploration: relational loss under arrival order (author's idea, 2026-09-18; registered 2026-09-19)

**Question (author's).** When the corpus is loaded one note at a time, how much of the final
state depends on the order the notes arrived in?

**What the code says, before measuring (2026-09-19).** Within one epoch, almost nothing:
- θ_dyn (`auto_calibrate_critical_threshold`, `app.py:220`) is calibrated on the geodetic basis
  only, never on the nodes; a node's lifecycle state and `action_potential` at ingest depend on
  its own vector and the basis alone.
- ε-edges are not persisted at ingest: `rebuild_epsilon_edges` (`_storage.py:649`) recomputes
  E_n on read from the current node set. The final graph and the final kNN sets are functions of
  the set, not of the sequence.
- The only order-dependent quantity is the EWMA drift tracker (`VarianceTracker`, Schmitt band),
  updated only on the text path (`app.py:290`), never by `/ingesta/vector`, and held in process
  memory; what survives is the `telemetry_error` rows of its alerts.
- Order enters the state through the revision log itself: node ids, `seq`, timestamps.

So under the PoC's loading path the relational loss is zero by construction; the ε-graph and
kNN are the controls, not the object. The question becomes live only where state is formed
against a population: a render calibration fitted at a point in the trajectory
(`spatial_calibration`), an epoch change (`/mutate`), or a θ calibrated on the nodes.

**Refuter.** Two loadings of the same 2,221 vectors in two orders (text order and one PCG64
permutation) through `/ingesta/vector` into fresh databases produce a different current state
modulo ids and `seq`: a different lifecycle state or `action_potential` for some vector, or a
different ε-edge set. Reported alongside: the drift tracker's alert sequence under both orders
on the text path, descriptive only.

Exploration branch: not in the PoC's scope, no gate; it enters a registry only after its own
instrument audit.
