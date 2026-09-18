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
  substrate are not near it on screen. Measured offline (`audits/R4.md`).
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
| K6 | Each colour channel carries variance independent of (x, y) in the per-epoch frame | pending | — | `audits/K6.md` | day 2 script |
| K7 | R4: recall@15 per perspective, operator / radial / overview | pending | — | `audits/R4.md` | day 6 script |

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

## Instrument audits

Records live in [`audits/`](audits/), one file per measurement, so a blind review never opens this
file: [`definitions.md`](audits/definitions.md) (shared), [`K6.md`](audits/K6.md) (colour channel
independence, day 2), [`R4.md`](audits/R4.md) (neighbourhood recall per perspective, day 6).
