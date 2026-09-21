# RefApp-01 — manual test log

A `manual` test of a client contract has no runner and is not red-first (`docs/LEDGER.md` seq 54), so
the executing agent's run in the browser is the only one and it left no record. This file keeps it:
what was run, against what, and the numbers read. Raw logs live outside the tree, in `.data/poc/logs/`
(git-ignored, AGENTS 1.2).

## 2026-09-21 — contract C, `b91a21c` (relations behind a toggle, initial-load error)

Browser pane against the R5 base `.data/poc` (2,221 corpus notes with sentences, before the five notes
were entered), engine at `f253b15`, client on the Vite dev server. Read-only: the only writes to the
base that day were the load, the calibration and the five entries below. A `fetch` wrapper in the page
logged method and URL, never headers. Widths: the pane's own (280 px), and emulated 431 and 1100 px.

| Test | Result | Evidence |
|---|---|---|
| T1 hidden by default | pass | Panels of `VEC_PART2_MIND_P13_DEMO_01_C02` (41 edges), `VEC_PART1_GOD_DEF_01` (1) and `VEC_PART1_GOD_APPENDIX_C01` (0): id, state, sentence and a "Show relations" button with `aria-pressed=false`; no count, no rows, no "No relations". |
| T2 shown = `/relations` | pass | 41-edge note: "Relations: 41 (first 15)" and 15 rows identical, in content and order, to the first 15 edges of that note in `GET /relations` (3,195 edges, `jq`). Second press hides them. 0-edge note: "No relations". |
| T3 off when the note changes | pass | Toggle on, then list rows 1 and 2 opened (`…P13_PROP`, `…P12_PROP_C02`): off each time; back to Map (anchor panel again): off; new selection by id: off. |
| T4 no requests | pass | Four toggle presses: 0 requests. Whole pass: only `GET /spatial?anchor=…`, one per selection. |
| T5 failed initial load | pass, simulated | `GET /spatial` (no anchor) made to fail in the page; the red line showed "Failed to fetch (simulated by test)" and the console logged `[UlpiaWebGL]`. With the engine up no line appeared. Limit: a simulated network failure, not an engine error or a 401. |
| T6 layout | pass | Bounding boxes of ingest bar, id field, overlay, panel, toggle and legend at 431 and 1100 px, relations hidden and shown: no overlaps, no horizontal overflow. At 431 px the panel is capped at 360 px (40vh) and scrolls (scrollHeight 519 shown). |
| T7 no regression | pass | Wheel zoom 1.5683; drag moved the centre to (0.1918, −0.1555); hover card with id, state and sentence of `…P06_DEMO_01_C01`; click opened its perspective and panel; Escape returned to the overview (zoom 1, centre 0, 0); no console errors. Note entry was not in this pass (next). |

Not observed: screenshots lag the pane, so nothing here rests on them; the layout rests on the
rectangles and the view matrix.

## 2026-09-21 — entry of the five R5 notes, through the client

Each note: the exact text of `R5.md` set in the ingest bar, Enter, the client's "Entered as NODE_n",
then `GET /nodos` to compare the stored text with the source.

| Task | Node | Stored text | State |
|---|---|---|---|
| T06 | `NODE_1` | exact (first entry, 13.8 s: model load) | `pending_approval` |
| T07 | `NODE_2` | exact | `pending_approval` |
| T08 | `NODE_3` | exact | `pending_approval` |
| T09 | `NODE_4` | exact | `pending_approval` |
| T10 | `NODE_5` | exact | `pending_approval` |

2,226 nodes afterwards; no id skipped. The engine log shows five `POST /ingesta` and no error; the
engine added four `RECAL_2` to `RECAL_5` rows (recalibration-signal log, not nodes). Every entered
note answers `GET /spatial?anchor=` with 200 and no fallback.

## 2026-09-21 — R5 run log, `0384015`

Browser pane against the R5 base (2,226 nodes), the client on the Vite dev server. The ingest of T1
was forced to fail in the page (an interceptor rejected `POST /ingesta`), so no note was written: the
engine log has 0 `POST /ingesta` and the base stays `2230|2230`. The pane's own width (431 px) and
emulated 431×900 and 1100×800. The browser's log already held 16 `point` events when the tests
began, the author's first exploration (16:53–16:54, no run mark); the tests appended to it, so
that browser's log also holds test marks for T03, T08, T09 and T10.

| Test | Result | Evidence |
|---|---|---|
| T1 events | pass | One run from the overview gave, in order: `run_start`, 3 `point`, `select` (map_click), 2 `relations_toggle` (on, off), `view` (list), `open`, `select` (panel_button), `view` (map), `select` (id_field), `overview` (escape), `select` (id_field), `overview` (button), `run_stop`, `ingest_submit` (length 8): every action, with its fields. Nothing is recorded for pressing the active view again, opening the row already open, an unknown id, a click on empty space or Escape in the overview. |
| T2 `point` | pass | 2 px of movement on one node: one event; leaving to empty space: none; each other node: one. With the cursor at rest, a re-layout under it re-sends the pointer position and the card, and the log, register a `point` without the hand moving. |
| T3 marks | pass | Start disabled without a task and while a run is open, Stop disabled with none open, the task select disabled during a run. `run_start` carries view and anchor: `overview` and null from the overview, `map` and the anchor from Map, `list` and the anchor from List; each `run_stop` names the started task. |
| T4 store | pass, partly | Read by a fresh copy of the module, the stored 36 events restore as 36. Prefilled to 19,995, seven more records stop at 20,000 with `full` true and the fifth new event last. With `setItem` throwing: "not saved: storage unavailable" shows, the log keeps recording (37), the download holds all 37, and the message goes when a write works (38 stored). Not observed in the UI: the "log full" text and the load-failure path (`getItem` throwing, an unparsable value); they need a reload and a new login, so the first was tested at store level and the second by reading. |
| T5 no leaks | pass | The downloaded file (`r5-run-log-<UTC stamp>.json`, schema `r5-run-log/1`, 36 events, as the button said, the viewport and `exportedAt`) has only the fields `anchor id length ms on source t task to type via view`. None of the 2,226 note texts is in it, nor `token`, `X-Traianus`, `poc-token`, `Authorization`, `Bearer` or the text typed in the ingest bar. |
| T6 no requests, no change | pass | Only the `GET /spatial?anchor=…` of each selection (one per `select`) and the blocked ingest; the engine log holds only `GET`. Wheel zoom 1.5683, drag moved the centre, no console errors, no event from zoom or pan. |
| T7 layout | pass | The run strip is a 39 px row at the bottom, in the same place in the overview, Map, List and List with relations, at 431 and 1100 px; no overlap with the ingest bar, id field, overlay, panel, list or legend; no horizontal overflow. The map is as tall in Map as in List (472 px at 431×900, 606 at 1100×800); every state gives up the same 39 px. |

## Earlier contracts

Contracts A (`1f384a2`) and B (`d80c44b`): their manual tests passed on 2026-09-20 (`DEVLOG.md`); the
evidence was not kept.

## Raw logs (`.data/poc/logs/`, not versioned)

- `engine-2026-09-21.log`: the last 999 lines of the engine's terminal, no timestamps. It starts in
  the middle of the corpus load (301 of the 2,221 `POST /ingesta/vector` are visible) and covers the
  calibration, the client tests and the five entries. No error or traceback.
- `engine.log`: from the restart at 12:58:57 on 2026-09-21, one timestamp per line, appended to. The
  R5 runs go here. It sees every request the client makes, but not pointing at a node on the map
  (no request) and not the clock.
- The page's request log lived in the browser's memory and was not saved.
- `r5-run-log-*.json`: the run log the client downloads (`R5.md`, Run log); the author saves it here.
