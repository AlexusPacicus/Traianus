# Provenance — data/spinoza/

Frozen research datasets. Every artifact here is derived from a single,
declared public-domain source by a committed, offline builder script.

## Source

- **Text:** *Ethics, Demonstrated in Geometrical Order* (Ethica Ordine
  Geometrico Demonstrata), Benedictus de Spinoza.
- **Edition:** Project Gutenberg eBook **#3800**, translated from the Latin
  by **R. H. M. Elwes**. Public domain (no copyright notice in source;
  Gutenberg #3800 is a pre-1929 publication).
- **Acquisition:** `https://www.gutenberg.org/cache/epub/3800/pg3800.txt`
  downloaded once by the operator; the builder runs fully offline on that
  local file.

## Artifacts

| File | Derived by | Notes |
|---|---|---|
| `part1_god.md` + `part1_god_manifest.json` | `tools/experiments/tooling/build_spinoza_corpus.py --part 1` | Part I ("Concerning God"), 409 sentence-chunks, labels `PART1_GOD_*`. |
| `source/pg3800.txt` | operator download (single acquisition) | Committed source snapshot (SHA-256 647f0227...) enabling byte-exact builder reproduction; see tests/unit/test_builder_reproducibility.py. |
| `part2_mind.md` + `part2_mind_manifest.json` | `tools/experiments/tooling/build_spinoza_corpus.py --part 2` | Part II ("On the Nature and Origin of the Mind"), labels `PART2_MIND_*`. |
| `part3_affects.md` + `part3_affects_manifest.json` | `tools/experiments/tooling/build_spinoza_corpus.py --part 3` | Part III ("On the Origin and Nature of the Emotions"), 627 sentence-chunks, labels `PART3_AFFECTS_*` (incl. the 48 Definitions of the Emotions as `DEFEMO_NN` and the closing General Definition as `GENDEF`). |
| `part4_bondage.md` + `part4_bondage_manifest.json` | `tools/experiments/tooling/build_spinoza_corpus.py --part 4` | Part IV ("Of Human Bondage, or the Strength of the Emotions"), 507 sentence-chunks, labels `PART4_BONDAGE_*` incl. the full Appendix (72 chunks). Header-punctuation variants of PG#3800 (`PROPOSITIONS.`, `APPENDIX.`) handled; a spurious header chunk in Part I was eliminated by the same fix. |
| `telemetry/v1.json` | `tools/experiments/tooling/freeze_telemetry.py` | Versioned aggregate summaries of the manifold experiments (isolated parts 2/3 and accumulated 1+2+3): nodes, edges, gate rates, sigma^2, Sammon stress, collision rescue, inter-part edge distribution, top cross-part bridges. Distilled from ephemeral `.data/` artifacts; findings conditional on the MiniLM-L6-v2 representation provider. |
| `telemetry/v2.json` | `tools/experiments/tooling/freeze_telemetry.py` | Supersedes v1: adds Part IV isolated run and the accumulated 1+2+3+4 manifold (2087 nodes). Inter-part analysis now includes AFFECTS<->BONDAGE (223 edges — densest continuum) and GOD<->BONDAGE. |

Derivation rules (all parts): ONE SENTENCE = ONE CHUNK; `{label -> chunk}`
manifest with insertion order == reading order; labels are neutral metadata
never embedded; Gutenberg footnote reference markers (`[N]`) and footnote
text blocks removed; Elwes editorial "N.B." cross-reference notes excluded (only under
AXIOMS/POSTULATES — elsewhere "N.B." is Spinoza's own text); abbreviation-
aware sentence segmentation (N.B., initials, roman numerals up to 6 chars,
citation names) with a lossless guarantee enforced by
tests/unit/test_build_spinoza_corpus.py.

## History / superseded sources

- `part1_god.md` was originally an operator-local file (`/Ethics_1.md`,
  sourced from globalgreyebooks.com) whose text contained third-party
  hyperlink footnotes. It was **re-derived from PG#3800** and replaced
  (LEDGER seq 30 -> seq 32); do not reintroduce non-Gutenberg text.

## Governance notes

- The `*.json` manifests under this directory are a **deliberate exception**
  to AGENTS.md §1.2 (no data dumps): they are frozen dataset contracts whose
  agreement with the `.md` corpus is enforced by
  `tests/unit/test_spinoza_dataset_consistency.py`.
- Ephemeral work artifacts (scratch SQLite DBs, telemetry JSON) live under
  `.data/` and are gitignored.
