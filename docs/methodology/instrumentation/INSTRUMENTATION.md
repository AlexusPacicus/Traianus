# Evidence Instrumentation

How the loop in [METHODOLOGY.md](../METHODOLOGY.md) is instrumented for claims. Generalized from
`polar-projector` @ `0b15002`, where every piece below exists and runs in CI; the one addition not
yet present there is marked.

## Pipeline

```
code → tests → bench/ (+ harness) → claims.md → verifier → manuscript
```

Each stage checks the one before it; the manuscript is an output, not a source. Reference sizes at
`0b15002`: operator 533 lines, tests 1,389, bench 3,135, registry 138, verifier 735, manuscript
1,222. A verifier larger than the code under study is the expected ratio, not an anomaly.

## Measurement harness

Every benchmark reports through one shared module, so two experiments compare measurements rather
than measurement styles. It owns the frozen corpus loader, the timing protocol, host and environment
disclosure, and the on-disk result format.

- **Per-call sampling**, not amortized: a bulk figure hides the tail.
- **`harness_null` arm** measuring the harness's own per-call cost. It cancels in differences
  between arms, not in ratios.
- **Warmup** iterations discarded.
- **Repetitions** aggregated by median of medians; the spread is reported, not hidden.
- **Interleaved arms**, round-robin across repetitions, with at least as many repetitions as arms.
- **Random access order** over the stimuli.
- **Declared non-controls:** what the protocol cannot control is written in the harness (reference:
  CPU affinity does not exist on macOS/arm64; BLAS threading is recorded, not asserted).

Reference: `polar-projector/bench/_harness.py`.

## Claims registry

One `claims.md` per study. **Header:** the registered question, each refuter with where it stands,
the terms of the question, and every superseded question kept for traceability. **Sections:** claims
grouped by subject, registered question, post hoc, must not appear, exploration notebook.

| ID | Claim | Status | Pre-registered | Instrument audit | Source | CI checks |
|---|---|---|---|---|---|---|

The **Instrument audit** column is the addition not present in the reference implementation: the
commit of the record below, which must precede the commit of the result.

**Status**
- `checked` — every figure the claim quotes has a check in the verifier.
- `not-in-ci` — backed by a committed artifact but deliberately not checked (host timings).
- `mismatch` — the manuscript quotes a figure no committed artifact contains; must be fixed.
- `unbacked` — no script or artifact; may not be stated as a measurement.
- `pending` — admissible only if the author decides to include it and a script is written.
- `construction` — a fact read from how a method is built; quotes no figure, names its source
  instead of a check, and is stated as construction, never as a result.
- `remove` — must not appear in the manuscript.

**Pre-registered**
- `yes (<commit>)` — protocol committed before its results.
- `no` — script and results in the same commit; not wrong, but never described as pre-registered.
- `post hoc` — specified after seeing the result it explains; labelled exploratory in the text.
- `n/a (<reason>)` — nothing to pre-register: proofs, deterministic recomputations.

A row may carry one value per arm or scale, separated by `;` (e.g. `unit yes (1c363bb); isometric
post hoc`).

## Instrument audit record

Step 2(a) of the loop, as an artifact. One record per benchmark script, in its docstring, committed
before the script's first result:

```
Instrument audit — <script>

Column "<name>": measures, in every arm, <exact operation; what it includes and excludes>.
  Arm A does <…>; arm B does <…>. Structural zero in <…>, because <…>.

Same thing in every arm?   <same operation, preamble and output in each arm, or why not>
Leakage?                   <does any arm see the labels or data it is judged on>
Comparable arms?           <each arm uses its own frame/model; no step re-processes earlier state>
Text matches code?         <rotation vs. reflection, "new only" vs. "all", …>
Reviewed by:               <person or agent, without reading the manuscript>
```

## Verifier

- **Recompute** deterministic tables instead of trusting them, and compare cell by cell.
- **Compare** each artifact figure to the manuscript at the published precision.
- **Require presence:** every checked figure is printed in the manuscript, signed, and not matched
  inside a section reference ("§3.2") or a larger number ("11" in "11.75"). The single exception is
  an explicit `AWAITING_TEXT` list, empty when writing is done.
- **Validate the registry:** fail on a malformed row, or on a check that does not exist or is too
  broad, instead of skipping it.
- **Mutation-test it:** corrupting one printed figure must fail CI.

**Declared limits.** It checks consistency across code, frozen artifacts and prose. It cannot detect
a benchmark that measures something other than what the text says — that is the instrument audit
record's job. Presence is checked, not location: a string that also occurs elsewhere passes.

Reference: `polar-projector/tools/verify_paper_tables.py`.

## CI configuration

- **The verifier runs on every push; benchmarks do not.** Host timings are not reproducible on CI
  runners, so the verifier reads the frozen artifacts in `bench/results/`.
- **Dependency extras split by purpose:** runtime (minimal), `test`, `repro` (exact pins of the
  environment the figures were measured in), `bench` (comparative baselines, never a runtime
  dependency).
- **Pinned lint and type toolchain**, and a coverage gate over the code under study.

Reference: `polar-projector/.github/workflows/ci.yml`, `polar-projector/pyproject.toml`.
