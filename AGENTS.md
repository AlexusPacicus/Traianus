# AGENTS.md — Agent Constitution & Operational Directives (v2.0.0)

**Scope:** Repository-wide (`traianus/`, `tests/`, `tools/`)  
**Standard:** RFC 2119 (`MUST` / `MUST NOT`)

---

## 1. Execution Quality & Conciseness

1.1 The agent **MUST** be concise and **MUST NOT** include dead code, superfluous comments, explanatory over-justifications, or modify files outside the direct scope of the task.

1.2 The agent **MUST NOT** leave temporary test scripts, single-use auxiliary files, or data dumps (`.json`, `.log`) in the repository tree. *(Deliberate exception: frozen research datasets under `data/**`, incl. the `{label -> chunk}` manifests in `data/spinoza/` — see `data/spinoza/PROVENANCE.md`.)*

1.3 The agent **MUST NOT** silence errors with empty `try-except` blocks, unconditional generic catches, or null returns that mask failures. *(Deliberate exceptions, all in the vendored Actuarii kit (6.2) and documented in-line: in `tools/boundary_validator/validator.py`, `_persist_audit` fails open on a record error (`sqlite3.Error`, `OSError`, `UnicodeError`), so an audit-log write failure can never block the gate, and `validate_proposal` and its MCP request handler close with a generic catch to stay total, mapping any unexpected exception to `ABORTED_GROUNDING_FAILED` or to a JSON-RPC internal error; the write and contract hooks close with a generic catch that denies, and the session announcement with one that reports the failure. None weakens enforcement: a missing `EXECUTE_SAFE` receipt blocks the write downstream.)*

1.4 The agent MUST follow a TDD workflow (write and verify failing tests first) and MUST run the test suite (`pytest tests/`) to verify passing status before declaring any task completed.

1.5 The agent **MUST NOT** add external dependencies in `pyproject.toml` without explicit approval (v1.0.0 release freeze: the Nix `flake.nix` devshell is out of scope — reproducibility is anchored in pinned `pyproject.toml` + green CI).

1.6 When modifying `tests/`, `traianus/`, or `pyproject.toml`, the agent **MUST** verify that `.github/workflows/ci.yml` covers the affected test partitions and new dependencies. A missing or stale CI configuration is a **blocking defect** — the task is not complete until CI reflects the current repository structure.

---

## 2. Security & Network Zero-Trust

2.1 Code proposals and mutations **MUST NOT** introduce external network primitives (`fetch`, `axios`, `urllib`, `requests`, `httpx`, `socket`, `subprocess`, `curl`, `wget`, `aiohttp`, `importlib`, `os.system`, `os.popen`).

> Scope note: this ban applies to the `Implementation_Block` of mutation proposals. Local repository tooling (e.g. `tools/audit/check_impact.py`, which shells out to `git grep`) is not subject to it.

2.2 Endpoints **MUST** bind exclusively to `127.0.0.1`. Wildcard CORS policies (`allow_origins=["*"]`) combined with credentials **MUST NOT** be introduced.

2.3 The `/ingesta` endpoint **MUST** receive text as raw `text/plain` in the HTTP body, discard JSON wrappers, and enforce `X-Idempotency-Key`.

2.4 Ingress verification **MUST** execute at the byte level: reject null bytes (`\x00`) and strict UTF-8 decoding failures (`errors="strict"`) with HTTP 400.

2.5 The agent **MUST NOT** execute inline Python (`python3 -c`, `python3 -m`). Python execution is restricted to committed scripts under `tools/` or `traianus/` (`python_script_dirs` in `.actuarii.json`). Any Python script not previously committed requires explicit user approval before execution. This rule is enforced by the permission perimeter of `.claude/settings.json` (deny `python3 -c *`, deny `python3 -m *`) and in code, at the interpreter (6.2): the shim `tools/bin/python3` (and `python`, `python3.11`) runs only `--version` or a script recorded in `HEAD` under those directories of this repository, and denies everything else (`-c`, `-m`, stdin, no script, an uncommitted script) with exit status 126. Test runners and servers are called by their own entry points (`pytest`, `uvicorn`), not through `python3 -m`; the Bash hook names `pytest` when it denies `python3 -m pytest`.

---

## 3. Substrate Domain & Mathematical Invariants (384D)

3.1 The agent **MUST** treat `traianus/` strictly as a deterministic state engine operating over 384D float32 L2-normalized vectors ($\|\mathbf{v}\|_2 = 1.0$), spectral projection signatures, and SQLite transitions, within the ≤ 8 GB RAM hardware envelope.

3.2 The agent **MUST NOT** introduce application domain concepts ("ideas", "thoughts", "hyperfocus") into `traianus/` source or tests. These belong exclusively to the client (RefApp-01).

3.3 The agent **MUST** tag the active seed as `epoch_provenance = 'PROSTHETIC_NSM_V1'`. Cross-epoch comparisons **MUST NOT** be performed without re-projection.

3.4 Spectral projections in $C1$ **MUST** exclude self-projection ($i \neq j$) during variance calculation to prevent variance inflation.

3.5 State consolidation **MUST** require the simultaneous satisfaction of both keys in `traianus/core.py`:
$$\text{Consolidated} \iff (\sigma^2 \ge \theta_{\text{dyn}}) \land (\text{EthicalKey} == \text{True})$$

3.6 Agents **MUST** consult `docs/audit/AUDIT.md` before applying refactorings to `traianus/app.py`.

3.7 Work on vector data, their bit layout, or the K6/R4 measurements **MUST** load the sections of `docs/methodology/instrument-audit/contracts.md` that `tools/hooks/contract_registry.json` registers for the paths concerned, through `tools/audit/context_pack.py`, before the edit. This is enforced in code, not by citation: the `PreToolUse` hook `tools/hooks/require_contract_context.py` denies `Edit`/`Write` on a registered path unless `context_pack` logged a `served` receipt for every required section within the registry window, from the contract file as it is now. A mention or a citation of a contract is not evidence. Conformance to a contract is verified by tests, not by the hook.

---

## 4. Persistence & Immutability

4.1 The agent **MUST NOT** execute SQL `UPDATE` or `DELETE` statements on `geodesic_axes` or node history. All updates are append-only, recorded via increasing sequence numbers (`seq`).

4.2 Lifecycle states **MUST** be restricted to `pending_approval`, `incubating`, `consolidated`, and the append-only error-log state `telemetry_error` (persisted by the spectral processor and read by `/telemetry`). The `archived` state **MUST NOT** be used or defined in schemas or DDLs. The SQLite `CHECK` constraint mirrors this set.

4.3 Local adjacency $E_n$ ($\epsilon = 0.8$, L2) **MUST** remain a purely observational metric in `/relations` and **MUST NOT** alter lifecycle states.

---

## 5. Structured Mutation Proposals (Pydantic / 5 Radicals and the Rationale)

5.1 Mutation proposals **MUST** conform strictly to the Pydantic schema in `tools/boundary_validator/schemas/proposals.py` (`AgentMutationProposal`) with `strict: true`, and **MUST** be emitted through the structured outputs contract `build_response_format(AgentMutationProposal)` of the same module (normative SEC-M-14..SEC-M-18, tested in Actuarii; the validator `tools/boundary_validator/validator.py` parses each proposal):

1. `Intent_Class`: strict classification (`FIX`, `REFACTOR`, `TEST`, `DOC`, `SPEC`, `AUDIT`).
2. `Target_File`: target path relative to repository root.
3. `Topological_Grounding`: exact UTF-8 quote present in target file.
4. `Implementation_Block`: exact text or code block to insert/replace.
5. `Safety_Abort`: high-level safety status (`NONE`, `BOUNDARY_VIOLATION`, `SYNTAX_ERROR`, `UNAUTHORIZED_SCOPE`).
6. `Rationale`: why the change is made, in a sentence a person can read (1 to 1000 characters, not only whitespace). It is recorded with the receipt and copied into the commit as an `Actuarii-Rationale` line; nothing checks that it is true.

5.2 **No Direct OS Authority:** Agents **MUST NOT** assume direct host OS execution authority. Intended actions **MUST** be emitted as structured proposal objects.

5.3 **Literal Grounding Guarantee:** The `Topological_Grounding` quote **MUST** exist exactly (character by character) in the target file.

5.4 **Single-Step Iteration:** Agents **MUST NOT** attempt multi-command chaining or autonomous un-gatekept execution loops.

---

## 6. Governance & Role Taxonomy

6.1 Traianus is governed by a **single executing agent**. Two live subagents are permitted, both from the Actuarii kit (6.2), and at most one agent executes at a time:
- the blind reviewer (`.claude/agents/blind-reviewer.md`): it has only Read, Grep and Glob and starts without the project's `CLAUDE.md` (`omitClaudeMd`); it reviews one record inside a package built by `tools/audit/build_review_package.py`, following the procedure that `.actuarii.json` names (`review.procedure`, here `.claude/skills/instrument-audit/SKILL.md`, step 2(a) of `docs/methodology/METHODOLOGY.md`), reports a PASS/CHANGES verdict and never changes files; the executing agent records the verdict.
- the implementer (`.claude/agents/implementer.md`): delegated by the executing agent to implement one change to code, repository tooling or tests from a strict-JSON `DelegationContract` (Pydantic, no extra fields, every field required; `tools/audit/delegation_contract.py`), validated by the executing agent before launch, test-first, on the one branch the contract names. A measurement whose record passed phase 1 is delegated the same way, and its contract says that the measurement is not run on real data. It answers with a `DelegationReport` validated the same way, touches only the files the contract lists, passes the boundary-validator gate for every governed file, runs no inline Python, never pushes, never reviews its own work, and stops at a commit. While it runs the executing agent makes no edits; `tools/audit/verify_red_green.py` on its report, the review of the diff, the audit and log records, the phase 2 review, the first run of a measurement and the merge stay with the executing agent.

The three subagents of v1 (`instrument-auditor`, `instrument-implementer`, `engine-implementer`) were retired in v2.0.0. The RefApp-01 client in the sibling repository `../refapp-01` is changed from a session opened there: this repository's Bash sandbox does not write outside it.

The former role taxonomy (planning, orchestration, code RED/GREEN, docs, github, traceability) is retained **conceptually** for documentation and process traceability, and the detailed role definitions are archived in git history.

6.2 Enforcement is centralized, not per-role: it is the Actuarii kit (Apache-2.0, canonical at `https://github.com/AlexusPacicus/actuarii`), vendored by its installer at Actuarii `73eaf2b` into `tools/` and `.claude/`, and configured by `.actuarii.json` (governed paths, Python script directories, contract registry, blind review, receipt window). Changes to the kit go into Actuarii first and are ported here; its tests live there, and `tests/` keeps the engine's. Claude Code is the only harness: the OpenCode mirror was dropped in v2.0.0.
- Permission perimeter, `.claude/settings.json`: git read-only commands, `pytest` and read-only shell commands allowed; `rm *`, `python3 -c *`, `python3 -m *`, WebFetch and WebSearch denied; git mutations and `gh` ask, as does every other `Bash` call.
- Bash sandbox: on, failing closed when unavailable, with a `denyWrite` entry per governed path, so `Bash` cannot write them; git commands that rewrite governed paths (`switch`, `merge`, `restore`) and `push` are run by the person.
- The boundary-validator MCP (`.mcp.json`, `tools/boundary_validator/validator.py`) gates each proposal (5) and issues a receipt for the exact change.
- `PreToolUse` hooks, each failing closed: `require_boundary_validation.py` (every tool) denies a write to a governed path without a receipt for that exact change within the receipt window (900 s), denies a governed `.py` result that does not parse or that adds a network or process primitive, and records each allowed write in the audit trail; `require_contract_context.py` enforces 3.7; `confine_review_reads.py` confines `Read`, `Grep` and `Glob` to the review package while `.data/review_lock.json` exists; `deny_python_escapes.py` denies the `Bash` commands that reach an interpreter around the shim of 2.5. A path hook decides the target by filesystem identity, not by its spelling.
- `SessionStart` hooks: `session_python_gate.sh` puts `tools/bin` first on the `PATH` of every `Bash` call; `announce_governance.py` announces where the rules come from, the governed paths, the receipt window, the sandbox and the commit hook. The `ConfigChange` hook `block_config_changes.py` keeps a change to the project or local settings, or to a skill, from applying to the running session.
- Git hooks: `pre-commit` (`tools/git/commit_integrity.py`) refuses a commit whose staged governed path is not the file on disk; `commit-msg` (`tools/git/commit_record.py`) appends one `Actuarii-Record` line per governed file (`matches` when the writes the gate allowed lead to the committed content, `changed outside the channel` otherwise) and the `Actuarii-Rationale` of each receipt.
- Instruction loading: `CLAUDE.md` loads `AGENTS.md` and `docs/audit/AUDIT.md`.

Declared limits are the kit's (Actuarii `AGENTS.md` §9): it keeps a record of the work and is not a security boundary against an adversarial agent. Two matter most here: with the sandbox off, writes made through `Bash` pass none of these gates; and `.data/context_pack.log` and `.data/review_lock.json` are outside `denyWrite`, so `Bash` can forge a contract-context receipt (3.7) or end a blind review by removing its lock.

6.3 Domain boundaries from the taxonomy remain normative for the single agent: edits to `tests/` vs `traianus/` vs `docs/` follow the same separation the roles once enforced (tests are not altered to mask failures; source is not edited to chase the test).

6.4 **Logographic Rules:** every directory under `docs/` **MUST** contain exactly one primary markdown document defining that domain node; component sub-documentation **MUST** be placed in isolated sub-folders matching the taxonomy.

6.5 **Skills Registry:** agent skills live under `.claude/skills/<name>/SKILL.md`, versioned in git.
- From the Actuarii kit: `blind-review` (the kit's default review procedure; `.actuarii.json` names `instrument-audit` instead), `boundary-validator` (gating of mutation proposals, 5) and `tdd-cycle` (Red-Green-Refactor, one phase at a time, with a gate per phase).
- `instrument-audit` — blind review of instrument audit records (step 2(a) of `docs/methodology/METHODOLOGY.md`): specification before the script exists, code before the first run, `file:line` evidence, PASS/CHANGES verdict; the procedure the blind reviewer follows (6.1), whose verdict the executing agent writes into the record's `Reviewed by:` line.
- `lab-analyst` — chromatic transmission analyst over corpus manifolds (collision rescue, Sammon stress, falsifiable ontological alignment); operates read-only on `.data/` artifacts via committed tooling in `tools/experiments/tooling/`.
- `spec-first` — authoring normative specifications under the 5 Radicals SPEC contract and the frozen spec template in `docs/specifications/`.
- `spectral-mathematician` — deterministic verification of C1 threshold calibration, simplex volumes, barycentric coordinates, and float32/64 drift via the `spectral-math-engine` MCP.
