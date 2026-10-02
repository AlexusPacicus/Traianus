# Provenance — data/math/

Frozen research datasets for direction F (`docs/roadmap/NEXT_RESEARCH.md`), mirror of
`data/spinoza/`. Every artifact here is derived from a single declared source by a committed,
offline builder script. The rules below were fixed before the builder existed; the artifacts are
listed at the end.

## Source

- **Text:** *A First Course in Linear Algebra*, Robert A. Beezer.
- **Edition:** source repository `https://github.com/rbeezer/fcla`, commit
  `347f27fe909b54b26970bcc0fcbf69c7e853c766` (2026-08-18), files `src/*.xml`.
- **Licence:** GNU Free Documentation License, Version 1.2 or any later version, with no Invariant
  Sections, no Front-Cover Texts and no Back-Cover Texts (`COPYING.txt` at that commit, read
  2026-10-01). Every artifact derived from it under `data/math/` carries the same licence, and the
  licence text ships with them.
- **Acquisition:** the `src/` tree at the pinned commit, fetched once by the operator and committed
  as a source snapshot, as `data/spinoza/source/` is; the builder runs offline on that snapshot.

## Derivation rules (fixed before the builder exists)

- **ONE STATEMENT = ONE CHUNK:** each `<definition>` and each theorem-like element becomes one
  chunk: its `<title>` followed by its statement. The exact element list is fixed in the builder
  contract after a count over the snapshot.
- **Out of the chunks:** proofs, examples, exercises, `<notation>` blocks and section prose.
- **Formulas apart:** every formula (`$…$`, `<equation>`, `<alignmath>` and the like) is replaced
  in the text by a marker and stored in a separate table keyed by chunk label and position. The
  original statement is reconstructible byte for byte from text plus table, enforced by a test.
- **What the model sees (author, option B):** the stored text with each marker replaced by the
  words of the formula's macros, each macro once per formula, in order of first appearance (amended
  2026-10-01 before any vector exists: a long formula repeats a macro once per entry), taken from
  `macro_words.json` (Beezer's
  96 macros at the pinned commit; `null` = not translated). Only the macros written in the source
  count, never their expansion. Letters, digits, operators and untranslated macros are dropped, so
  a formula with no translated macro leaves nothing. The table is fixed before any vector exists.
- **Title separator (author, 2026-10-02, before any vector exists):** in the text the model sees,
  the text of every `<title>` is followed by `. ` (period, space): the chunk title and each
  `<property>` title inside a definition. No whitespace stands before the period, so a title whose
  formula leaves no words reads `Dimension of. The dimension…`. The separator is unconditional; no
  title of the snapshot ends in `. ? ! : ;`, which a test pins.
- **Labels:** neutral metadata, never embedded: `MATH_BEEZER_<KIND>_<ACRO>`, with `<ACRO>` Beezer's
  own `acro` attribute.
- **Citations:** an edge from a chunk to each `<acroref>` of type definition or theorem inside its
  element, statement and proof included. The other types are dropped, and the list is declared
  (author, 2026-10-02): archetype, chapter, diagram, example, exercise, property, sage, section,
  solution, subsection, technique. These and the two kept are the 13 types of the snapshot. The
  builder holds the list as `DROPPED_CITATION_TYPES`; an acroref of any other type is an error. An
  edge from a chunk to itself is dropped, and each ordered pair appears once.
- **Manifest:** `{label -> chunk}`, insertion order equal to reading order.

## Artifacts

All four are written by `tools/experiments/tooling/build_beezer_corpus.py` from `source/src` and
`macro_words.json`, with keys in reading order; `KIND` is `DEF` or `THM`. Reading order is document
order: `fcla.xml` with every `xi:include` expanded in place. Rebuilding reproduces them byte for
byte (`tests/unit/test_beezer_dataset_consistency.py`).

| File | Content | Size |
|---|---|---|
| `beezer_manifest.json` | `{label -> text the model sees}` | 342 chunks (114 DEF, 228 THM) |
| `beezer_marked.json` | `{label -> statement with tags kept and each formula as a marker ⟦Fn⟧}` | 342 |
| `beezer_formulas.json` | `{label -> [formula source, …]}`, by marker position | 2,078 formulas (1,972 inline, 63 `<equation>`, 43 `<alignmath>`) |
| `beezer_citations.json` | `[[from, to], …]` | 851 ordered pairs |

`source/` is the snapshot of the pinned commit: 53 `src/*.xml`, `COPYING.txt` and
`src2/gfdl-mathbook.xml`; sha256 of the sorted list of per-file sha256 values
`5673bdabd0bce8598f7776495762f6cf9138f57d7aea1f068d1120ac791bf4d6` (commit `00e75d0`).
