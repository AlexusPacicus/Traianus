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
