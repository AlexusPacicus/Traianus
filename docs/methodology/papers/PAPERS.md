# Writing Papers

How to write a paper on Traianus, from the retrospective of the first one (Polar Projector,
2026-09-11 → 16). The loop it instantiates is in [METHODOLOGY.md](../METHODOLOGY.md); the evidence
pipeline behind it is in [INSTRUMENTATION.md](../instrumentation/INSTRUMENTATION.md).

## Lessons from the first paper

| What happened | Cost | Rule that prevents it |
|---|---|---|
| The framing changed several times (A → C → revised question) and every rewrite introduced new errors | Days of rewriting; contradictions between sections | §1: genre and deadline on day one; a change of framing goes to a v2 |
| Several audits (Claude and other AIs) reviewed the text and missed 7 measurement errors | Wrong published figures, corrected after the push | §3 and §6: specify each measurement and review the benchmark code first |
| CI checked that text and artifacts agreed, not that the benchmark measured what the text said | False sense of safety | §6: CI does not replace reviewing the measurement |
| The same figures in the abstract, §1, §3, §5, the README and the registry | Cascading corrections; stale README and upload zip | §5: one source per figure |
| Protocols changed after seeing results; experiments without pre-registration | Weaker claims | §4: protocol committed before running |
| One corpus, 3–5 repetitions, no intervals, ratios with near-zero denominators | Fragile claims | §3: default controls and statistics |

The seven measurement errors, to recognize them next time:
1. A "cost" column that measured a different operation for each method.
2. A method that re-transformed already placed points at every step.
3. An alignment that allowed reflections where the text said "rotation".
4. A method that skipped work the others did.
5. Sequential data access when measuring flatness against working-set size.
6. Harness overhead not subtracted before reporting ratios.
7. A rule that used the same labels it was evaluated against.

## 1. Before starting

- **Genre and venue:** measured report, method, negative results; preprint or conference.
- **Deadline.** Past it, anything that is not a factual error goes to a v2.
- **One question in one sentence**, plus what would refute it. No prose until it exists.
- **What this paper is not.** Written down explicitly.

## 2. Claims registry (`claims.md`)

One row per claim, before any text is written. Columns and vocabulary are defined once, in
[INSTRUMENTATION.md](../instrumentation/INSTRUMENTATION.md#claims-registry).

- **A figure without a row** does not enter the manuscript.
- **Exploration is not a result:** it lives in the exploration notebook until it has a script, an
  artifact and a check.

## 3. Specifying each measurement (the missing step)

Before running any benchmark, for every column of every table, write the instrument audit record
(template in [INSTRUMENTATION.md](../instrumentation/INSTRUMENTATION.md#instrument-audit-record)).
Another person or agent checks it against the code without reading the paper, asking:

- Do all methods perform the same operation, with the same preamble and the same output?
- Does each method use its own frame or model, and not another's?
- Does any method see the labels or data it is evaluated against?
- Does any step modify or re-process state from earlier steps?
- Does the text say exactly what the code does (rotation vs. reflection, "new only" vs. "all")?

**Default controls** for every timing benchmark:
- an empty arm that measures the harness itself;
- random data access;
- at least as many repetitions as methods, rotating the order;
- median across repetitions, spread kept;
- more samples per repetition for microsecond operations.

**Default statistics:**
- bootstrap intervals on every comparison that is interpreted;
- differences rather than ratios when the denominator is small;
- never "within noise" without having measured the noise;
- a single corpus, encoder or machine is stated under limitations.

## 4. Pre-registration

- **Protocol:** script and configuration committed before the first result; the hash is cited.
- **Later changes** to protocol or analysis: labelled post hoc in the text and in the registry.
- **Bug fixes** after seeing results: declared in the row, with date and reason.

## 5. One source per figure

- **Every figure lives in an artifact** (`bench/results/*.json`). The manuscript quotes it and CI
  checks that they agree.
- **README and documentation carry no figures:** they link to the paper's section.
- **Abstract and conclusion are written last**, from already checked figures.

## 6. Review order

1. **Measurement code** against its instrument audit record (§3). Parallel agents, one per
   benchmark, each asking "does this measure what the column says?".
2. **Figures** against artifacts (CI does this).
3. **Prose:** consistency across sections, cross-references, claims without a row.

Do not review prose before code: it polishes text that will change.

What the CI verifier must check is specified in
[INSTRUMENTATION.md](../instrumentation/INSTRUMENTATION.md#verifier).

## 7. Writing

- **Claims frozen before writing.** Written once, in order: tables, results, method, discussion,
  conclusion, abstract.
- **Baselines that win are presented as a result**, not hidden.
- **Construction vs. measurement:** facts read from code are stated as construction, never as a
  result.
- **Use of AI:** declared in detail from the start (translation, drafts, references, audits, code).

## 8. Publication

- **Automatic build from the manuscript:** LaTeX, upload zip and PDF, no manual steps.
- **Release from a tag** with CI green; the attached PDF is built from that tag.
- **Licenses decided before publishing:** code (Apache-2.0), text and data (CC BY 4.0).
- **Metadata:** `CITATION.cff`, and the author name identical everywhere: Alexis Zapico-Fernández.
- **Zenodo:** enable the GitHub integration before creating the release to be archived.

## Quick checklist

- [ ] Genre, venue and deadline decided
- [ ] Question and refuters written
- [ ] Claims registry started
- [ ] Instrument audit record written for each column and checked against the code
- [ ] Default controls and statistics included
- [ ] Protocol committed before running
- [ ] Measurement code reviewed by agents
- [ ] CI verifier tested with mutants
- [ ] Text written once; README without figures
- [ ] Automatic build and release; licenses and `CITATION.cff`
