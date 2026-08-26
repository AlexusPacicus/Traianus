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
| `part4_bondage.md` + `part4_bondage_manifest.json` | `tools/experiments/tooling/build_spinoza_corpus.py --part 4` | Part IV ("Of Human Bondage, or the Strength of the Emotions"), 507 sentence-chunks, labels `PART4_BONDAGE_*` incl. the full Appendix. Header-punctuation variants of PG#3800 (`PROPOSITIONS.`, `APPENDIX.`) handled; a spurious header chunk in Part I was eliminated by the same fix. |
| `part5_power.md` + `part5_power_manifest.json` | `tools/experiments/tooling/build_spinoza_corpus.py --part 5` | Part V ("Of the Power of the Understanding, or of Human Freedom" — title faithful to the declared PG#3800/Elwes edition), 220 sentence-chunks, labels `PART5_POWER_*`, 42/42 propositions; ends at the "End of the Ethics" boundary. |
| `telemetry/v1.json` | `tools/experiments/tooling/freeze_telemetry.py` | Versioned aggregate summaries of the manifold experiments (isolated parts 2/3 and accumulated 1+2+3): nodes, edges, gate rates, sigma^2, Sammon stress, collision rescue, inter-part edge distribution, top cross-part bridges. Distilled from ephemeral `.data/` artifacts; findings conditional on the MiniLM-L6-v2 representation provider. |
| `telemetry/v2.json` | `tools/experiments/tooling/freeze_telemetry.py` | Supersedes v1: adds Part IV isolated run and the accumulated 1+2+3+4 manifold (2087 nodes). Inter-part analysis now includes AFFECTS<->BONDAGE (223 edges — densest continuum) and GOD<->BONDAGE. |
| `telemetry/v3.json` | `tools/experiments/tooling/freeze_telemetry.py` | Supersedes v2: corpus regenerated under the abbreviation-aware tokenizer (409/458/627/507 chunks); all scratch DBs re-ingested. Accumulated (n=2001): Sammon gain 39.4%, rescue 97.4% over 1909 collisions; AFFECTS<->BONDAGE 215 remains densest. |
| `telemetry/v4.json` | `tools/experiments/tooling/freeze_telemetry.py` | Supersedes v3: adds Part V isolated run and the complete accumulated 1+2+3+4+5 Ethics manifold (2221 nodes / 3195 edges). Inter-part matrix completed: MIND<->POWER = 126 (second-strongest continuum), GOD<->POWER = 14 (weakest link). |
| `telemetry/v5.json` | `tools/experiments/tooling/freeze_telemetry.py --extra-report` | Supersedes v4: same run summaries plus a `dynamic_epsilon_audit` section embedding (a) the Otsu adaptive-threshold sweep (accumulated epsilon*=1.2032, bootstrap std 0.0015), (b) Q-axis anisotropy vs empirical permutation null per part and accumulated, (c) the 5x5 inter-part matrix as size-normalized enrichment ratios at epsilon*, and (d) the 8x5 axis-part independence battery over four units of analysis (all vertices / active loads / variance-weighted / edge-level references; seeded Monte-Carlo conditional p-values, bias-corrected Cramer's V, Holm post-hoc, deterministic jackknife). Removes all fixed analytic thresholds from the bridge audit (LEDGER seq 40). |

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
