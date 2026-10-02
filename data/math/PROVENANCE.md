# Provenance — data/math/

Frozen research datasets for direction F (`docs/roadmap/NEXT_RESEARCH.md`), mirror of
`data/spinoza/`. Every artifact here is derived from a single declared source by a committed,
offline builder script. No artifact is built yet; this file fixes the source and the rules first.

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
- **Labels:** neutral metadata, never embedded: `MATH_BEEZER_<KIND>_<ACRO>`, with `<ACRO>` Beezer's
  own `acro` attribute.
- **Citations:** an edge from a chunk to each `<acroref>` of type definition or theorem-like inside
  its element, statement and proof included; references to sections are dropped.
- **Manifest:** `{label -> chunk}`, insertion order equal to reading order.
