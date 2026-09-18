# Research Methodology

Primary document of `docs/methodology/`: the loop every study on Traianus runs, and where each of its
steps lives. Distilled from the first paper (Polar Projector, 2026-09-11 → 16), whose reference
implementation is the standalone `polar-projector` repository. A working method, not an external
standard: it is expected to change as studies run through it.

## Incubation and exit condition

Incubated here so that a real study tests it before it is generalized. **Exit condition:** once a
second study completes the loop using it, this directory moves to its own repository
(`git filter-repo --path docs/methodology/`), together with whatever tooling both studies turned out
to share. Until then nothing here is extracted into code. Recorded in `docs/LEDGER.md` seq 47.

## The loop

**0. Problem** — one sentence: what is solved, and what is explicitly left out.

**1. Hypothesis + refuters** — one falsifiable sentence, plus the observations that would refute it.
Without a named refuter it is an intuition, not a hypothesis, and it does not advance.

**2. Attack** — in two parts, in this order:
- **(a) Audit the instrument, before running it.** Three fixed questions: does it measure the same
  thing in every arm (scope, units, preamble)? Is any "truth" used to judge also an input of what is
  judged (leakage)? Are baseline and treatment genuinely comparable? The answers are a committed
  record, not a mental check (see [instrumentation](instrumentation/INSTRUMENTATION.md)).
- **(b) Run the attack**, trying to break the hypothesis rather than confirm it.

**3. Reformulate or not — explicit gate.** Only when a refuter held, measured. Declared in writing,
the superseded question kept for traceability, then back to step 1. Never mid-run, on a new hunch or
because something "looks more interesting".

**4. Register** — only what survived step 2 in full enters the registry. Nothing else, however
convenient the number.

**Explore** — a separate branch, always labelled. Free exploration with no gate; it never enters
step 4 without passing steps 1–2 itself.

## Why step 2(a) is the one that matters

Steps 0, 1, 3 and 4 were validated by the first paper: freezing scope, one question with refuters and
writing once pulled it out of a run of reframings. What failed was trusting results without checking
that the experiment measured what it claimed. Seven measurement defects passed several audits with
CI green and were all found in one code review after the manuscript was written (listed in
[papers](papers/PAPERS.md)). No consistency check catches them: a verifier confirms that a figure
matches its artifact, not that the artifact measures what the text says.

## Instances

| Step | Code | Claims |
|---|---|---|
| 0. Problem | the function's contract | the registered question heading `claims.md` |
| 1. Hypothesis + refuters | the test, written first, red | the refuter rows (F1…Fn) |
| 2(a). Audit the instrument | the test fails for the stated reason, not by accident | instrument audit record, committed before the first result |
| 2(b). Attack | red → minimal implementation → green | the benchmark script |
| 4. Register | the test joins the suite as a permanent regression | status `checked`, enforced by the verifier |
| Enforced by | `tdd-cycle` skill | `instrument-audit` skill (step 2(a)); planned: `research-loop` |

A **PoC** runs both instances at once: engine code through the code column, every figure through
the claims column (a claims table in the PoC document, without a CI verifier unless a claim heads
to a publication). Client code without a test suite is validated by the PoC's checkpoint and
labelled exploratory. Scope changes after the first commit are logged in the PoC document.

## Nodes

- **[papers/PAPERS.md](papers/PAPERS.md)** — rules specific to writing a paper: lessons of the first
  one, measurement specification, pre-registration, one source per figure, review order, writing,
  publication.
- **[instrumentation/INSTRUMENTATION.md](instrumentation/INSTRUMENTATION.md)** — the evidence pipeline
  that implements the loop for claims: measurement harness, claims registry, instrument audit record,
  verifier, CI configuration.

## Studies

| Study | Question source | Status |
|---|---|---|
| Render calibration frozen per epoch | `docs/adrs/ADR-026-spatial-render-calibration.md` | Absorbed into the RefApp-01 PoC (day 2: per-epoch frame) |
| RefApp-01 PoC: 5D map, perspectives, note entry | `frontend/POC.md` | Steps 0–1 written; 2(a) records for K6 and R4 drafted, pending review |
