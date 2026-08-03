# 🏗️ Architecture Specification — OpenCode Configuration of Traianus/TridenGuard

> **Date:** 2026-08-01 · **opencode 1.18.10** · **Status:** ACTIVE (hardened after the 2026-08-01 Plan)
> **Primary sources:** `opencode.jsonc`, `.opencode/agents/*.md`, `tools/tridenguard_validator.py`, `AGENTS.md`
> **Topological Grounding:** every configuration or constitution quote reproduces the real file character by character.

---

## 1. Purpose and Scope

This document specifies the **OpenCode configuration topology** of the Traianus/TridenGuard repository after the 2026-08-01 hardening cycle (Entry #008 of the bitacora). It defines:

1. The root configuration (`opencode.jsonc`): model, governance instructions and MCP server.
2. The topology of the 5 `subagent` agents and their Zero-Trust permission matrix.
3. The interface contract of the MCP validator `tridenguard-validator` v1.2.0.
4. The `AGENTS.md` invariants that condition the operation of the agents.

It is not an OpenCode usage tutorial; it is the architectural contract that **must not be broken** when editing this configuration.

---

## 2. System Context

- **Traianus (Deterministic Spatial Substrate):** maintains state continuity over a simplicial complex $S_n = (V_n, E_n, K_n)$, decoupling the vector representation from state decisions. Strict hardware constraint: local or offline execution on edge ($\le 8\text{ GB}$ RAM).
- **TridenGuard (Neuro-Symbolic Firewall):** Zero-Trust evaluation via deterministic rules (*Policy Gate*, *Zero-Trust Gate*, *Grounding Gate*). Golden rule declared in `AGENTS.md`:

> *"Neurons propose, rules dispose"*

The MCP validator implements this rule as an **executable deterministic gate** over the agent proposals.

---

## 3. Configuration Topology

### 3.1 Model and small model

`opencode.jsonc` (root) declares the main model and the auxiliary model:

```jsonc
{
  "$schema": "https://opencode.ai/config.json",
  "model": "opencode/big-pickle",
  "small_model": "opencode/ling-3.0-flash-free",
```

- `model`: `opencode/big-pickle` — main model for planning and execution (also pinned per-agent in each frontmatter).
- `small_model`: `opencode/ling-3.0-flash-free` — lightweight model for low-cost tasks.

### 3.2 Governance instructions

```jsonc
  "instructions": ["TRAIANUS_AUDIT.md", "docs/LOGOGRAPHY.md"],
```

- `TRAIANUS_AUDIT.md`: technical audit report (Finding C1, H1–H5) and remediation status; **mandatory to consult it before refactoring `traianus/app.py`** (Invariant 1 of `AGENTS.md`).
- `docs/LOGOGRAPHY.md`: master index of the Logography; prevents *Doc-Drift*.

### 3.3 MCP `tridenguard-validator`

```jsonc
  "mcp": {
    "tridenguard-validator": {
      "type": "local",
      "command": [
        "python3",
        "tools/tridenguard_validator.py"
      ]
    }
  }
```

- **Type:** `local` (OpenCode child process; no external network).
- **Protocol:** MCP over stdio, line-delimited JSON-RPC 2.0 (`2024-11-05`).
- **Lifecycle:** OpenCode starts the process when loading the configuration; the server serves `initialize`, `ping`, `tools/list` and `tools/call` until EOF on `stdin`.
- **Exposed tool:** `validate_proposal` (only one). Details in §7.
- **Version:** `SERVER_VERSION = "1.2.0"`.

---

## 4. Agent Topology

The 5 agents reside in `.opencode/agents/` with `mode: subagent` (none declares `name:` in frontmatter; the identifier derives from the filename). Permissions declared via `permission:`.

| Agent | Role | edit | bash | Dependencies |
|--------|-----|------|------|--------------|
| `@plan-architect` | Chief Architect | `deny` | `deny` | `@orchestrator` (executes its plans) |
| `@orchestrator` | Orchestra Director | `deny` | `ask` | `@plan-architect`, `@fixer`, `@antigravity-compiler`, `@logographer` |
| `@fixer` | Syntactic patches + tests | `allow` | `allow` | `@orchestrator` |
| `@antigravity-compiler` | 5 Radicals Compiler | `allow` | `allow` | `@orchestrator` |
| `@logographer` | Documentation (Logography) | `allow` | `deny` | `@orchestrator` |

### Invocation contracts

- **`@plan-architect`** — `edit: deny`, `bash: deny`: analyzes, evaluates audits and designs atomic Action Plans with TDD criteria (🔴/🟢). Delivers to `@orchestrator`; never touches code.
- **`@orchestrator`** — `edit: deny`, `bash: ask`: coordinates executor agents, controls the Red-Green-Refactor TDD cycle and processes **one phase at a time**. Operational rule: does not assign the next phase until the executor reports success in the deterministic test.
- **`@fixer`** — `edit: allow`, `bash: allow`: applies minimal patches, moves files (updating imports atomically) and runs/fixes the Pytest suite.
- **`@antigravity-compiler`** — `edit: allow`, `bash: allow`: implements high-integrity changes under the **5 Radicals** (`Intent_Class`, `Runtime_Contract`, `Implementation_Block`, `Topological_Grounding`, `Safety_Abort`).
- **`@logographer`** — `edit: allow`, `bash: deny`: maintains `docs/LOGOGRAPHY.md`, the bitacora and the specifications; no command execution.

---

## 5. Orchestration Flow

1. **Plan:** `@plan-architect` emits a phased Action Plan with expected Topological Grounding and validation criteria.
2. **Assignment:** `@orchestrator` assigns each phase to an executor according to the task type (5 Radicals → `@antigravity-compiler`; patches/tests → `@fixer`; Logography → `@logographer`).
3. **Execution:** the executor applies the change and reports with `REPORT_TO_ORCHESTRATOR`.
4. **Regression:** validated with `pytest` in `tests/` or the `tools/audit_harness.py` harness before moving to the next phase.
5. **Report:** `@orchestrator` consolidates the final summary for `@plan-architect` and the User.

TDD cycle: 🔴 red (proven/simulated failure) → 🟢 green (implementation) → refactor, **one phase at a time**.

---

## 6. Zero-Trust Security Model

### 6.1 Permission matrix

| Agent | edit | bash | task |
|--------|------|------|------|
| `@plan-architect` | deny | deny | read-only + planning |
| `@orchestrator` | deny | ask | read-only; commands under confirmation |
| `@fixer` | allow | allow | code writing and test execution |
| `@antigravity-compiler` | allow | allow | high-integrity code writing |
| `@logographer` | allow | deny | writing in `docs/` without execution |

No documentation or planning agent holds execution permission; only the code executors (`@fixer`, `@antigravity-compiler`) have `bash: allow`.

### 6.2 MCP validator gates

`validate_proposal` (v1.2.0) implements 3 deterministic gates plus input sanitization:

1. **Safety Gate:** if `Safety_Abort != "NONE"` → `BLOCKED_BY_SAFETY_GATE`.
2. **Zero-Trust Gate:** if the `Implementation_Block` contains any of the 21 forbidden network tokens (`fetch(`, `axios`, `urllib.request`, `import requests`, `httpx`, `socket`, `urllib3`, `subprocess`, `curl`, `wget`, `aiohttp`, `importlib`, `os.system`, `os.popen`, `requests.`, `http.client`, `webbrowser`, `telnet`, `nc `, `ftp`, `xmlrpc`) → `ABORTED_VIOLATES_ZERO_TRUST`. NUL bytes (`\x00` raw or JSON-escaped `\u0000`) are sanitized before processing (SEC-M-09).
3. **Grounding Gate (Dual Boundary Pattern):** for `REFACTOR`/`FIX`/`AUDIT` with `target_file`, verification is physical and byte-level — canonicalize the path (`Path.resolve(strict=True)`), require containment within the repository root (`is_relative_to(REPO_ROOT)`), and match the `Topological_Grounding` quote as an exact UTF-8 binary subsequence over `read_bytes()` of the target file; failures are denied silently (no target path or OS details in the decision) → `ABORTED_GROUNDING_FAILED`.

Only if the three gates pass: `VALIDATED` / `EXECUTE_SAFE` with `and_gate_ok: True`. Invalid JSON input → `QUARANTINED` / `INVALID_JSON`.

### 6.3 `AGENTS.md` invariants applied to the operation

1. **Audit Synchronization:** consult `TRAIANUS_AUDIT.md` before refactoring `traianus/app.py`.
2. **Variance Threshold Correction (C1):** always exclude the self-projection ($i = j$, value $1.0$) when calibrating `auto_calibrate_critical_threshold()`.
3. **Zero-Trust and Network Security:** block external requests (`fetch()`, `axios`, `urllib.request`, `requests`, `httpx`, `socket`, `urllib3`, `subprocess`, `curl`, `wget`, `aiohttp`, `importlib`, `os.system`, `os.popen`); Uvicorn/FastAPI on `127.0.0.1`; no wildcard CORS with credentials; byte-level Dual Boundary verification (path canonicalization, repo-root containment, UTF-8 binary subsequence over `read_bytes()`, `\x00` sanitization, silent denial).
4. **Literal Grounding Guarantee:** the quote in `Topological_Grounding` must exist exactly in the source (equivalent to the validator's Grounding Gate).
5. **Immutable Persistence (*Append-Only*):** `UPDATE`/`DELETE` over the node history is prohibited; new revisions with increasing `seq`.

---

## 7. MCP Validator Interface Contract

### 7.1 JSON-RPC lifecycle

- `initialize` → `protocolVersion: "2024-11-05"`, `capabilities.tools.listChanged: false`, `serverInfo: {name: "tridenguard-validator", version: "1.2.0"}`.
- `ping` → `{}`.
- `tools/list` → `{tools: [validate_proposal]}`.
- `tools/call` (name = `validate_proposal`) → result with `content[0].text` = JSON decision.

### 7.2 `validate_proposal` parameters

- `proposal` (string, **required**): JSON with `Intent_Class`, `Implementation_Block`, `Topological_Grounding`, `Safety_Abort`.
- `target_file` (string, optional): source file path for literal grounding verification (**mandatory for `REFACTOR`/`FIX`/`AUDIT`**).

### 7.3 Decision types

| status | final_decision | Condition |
|--------|----------------|-----------|
| `VALIDATED` | `EXECUTE_SAFE` (+ `and_gate_ok: True`) | 3 gates pass |
| `QUARANTINED` | `INVALID_JSON` (field `decision`; `reason`) | unparseable JSON input |
| `QUARANTINED` | `BLOCKED_BY_SAFETY_GATE` | `Safety_Abort != "NONE"` |
| `QUARANTINED` | `ABORTED_VIOLATES_ZERO_TRUST` | forbidden network token in `Implementation_Block` |
| `QUARANTINED` | `ABORTED_GROUNDING_FAILED` | non-exact grounding (REFACTOR/FIX/AUDIT with `target_file`) |

### 7.4 JSON-RPC error codes

- `-32601` — `Method not found: <method>`.
- `-32602` — `Unknown tool: <name>` or `arguments.proposal must be a string`.
- `-32603` — `Internal error: <e>` (e.g. missing file in the grounding check).

Notifications (`id: null`) **do not receive a response**. The CLI branch (`python3 tools/tridenguard_validator.py <proposal> <target_file>`) is preserved for regression.

---

## 8. Invariants and Maintenance Rules

When editing `opencode.jsonc` or `.opencode/agents/*.md`:

1. **Do not break the MCP contract:** keep `type: "local"` + command `python3 tools/tridenguard_validator.py`; the server must not change transport or lose `validate_proposal`.
2. **Do not raise permissions:** the 2026-08-01 Plan decisions fix `plan-architect` (deny/deny), `orchestrator` (deny/ask), `fixer` and `antigravity-compiler` (allow/allow), `logographer` (allow/deny). Any change requires a new Plan and an update of this specification and of the bitacora.
3. **`mode: subagent` and no `name:`:** the identifier derives from the filename (lesson of the `plan_arquitect.md` → `plan-architect.md` rename).
4. **Literal grounding:** the executor agents must emit exact quotes; the validator rejects them if they do not exist.
5. **Append-Only:** record configuration changes in `docs/development/bitacora.md` as a new revision (never rewrite previous records).
6. **Governance instructions:** keep `TRAIANUS_AUDIT.md` and `docs/LOGOGRAPHY.md` as root instructions; do not add instructions that contradict `AGENTS.md`.

---

## 9. Cross References

- [`AGENTS.md`](../../AGENTS.md) — Agent Constitution (domain, invariants, roles).
- [`LOGOGRAPHY.md`](../LOGOGRAPHY.md) — master index (section 3: Architecture & Engineering).
- [`TRAIANUS_AUDIT.md`](../../TRAIANUS_AUDIT.md) — technical audit (C1, H1–H5) and remediation status.
- [`Project_architecture.md`](./Project_architecture.md) — mathematical formulation of $S_n = (V_n, E_n, K_n)$.
- [`CONTRACTS_AND_PRISMS.md`](./contracts/CONTRACTS_AND_PRISMS.md) — Pydantic contracts and Zero-Trust customs.
- [`ADR.md`](./ADR/ADR.md) — append-only ledger of decisions (ADR-001 to ADR-025).
- [`README_CODE_ENGINE.md`](../../README_CODE_ENGINE.md) — TridenGuard V4 compiler (5 Radicals and 3 Gates).
- [`tools/tridenguard_validator.py`](../../tools/tridenguard_validator.py) — MCP server v1.2.0 (source of the §7 contract).
- [`docs/development/bitacora.md`](../development/bitacora.md) — Entries #008 (hardening), #009 (this specification) and #012 (2026-08-01 logography sync).
- [`docs/STATE_CONSOLIDATION_2026-08-01.md`](../STATE_CONSOLIDATION_2026-08-01.md) — 2026-08-01 cycle consolidation (git state, AGENTS.md invariants, Doc-Drift catalog D1–D10, recommendations R1–R5).
- **Note (R2):** `TRAIANUS_AUDIT.md` is referenced in `opencode.jsonc:6` and in this specification (§3.2, §6.3 and previous reference), and it **exists in the working tree** after the 2026-08-01 rename from `TRAIANUS_AUDITORIA_ES.md` (Doc-Drift D1 resolution).

---

## 10. Validation Criteria

- **Pytest (historical, Entry #008):** cycle #008 closed with `python3 -m pytest tests/ -q` → **34 passed**.
- **Pytest (current state, 2026-08-01):** `python3 -m pytest tests/ -q` → **174 passed / 2 skipped** (cycles #010–#011; refer to `docs/development/tests/TEST_OVERVIEW.md` §7 and to `docs/STATE_CONSOLIDATION_2026-08-01.md`).
- **C1 harness:** `python3 tools/audit_harness.py` → **✅ C1 GUARD PASSED IN GREEN** (consolidation rate 30% within [5%, 95%]); re-verified 2026-08-01.
- **MCP smoke:** handshake `initialize` → `serverInfo` `tridenguard-validator` v1.2.0 OK; `tools/list` exposes `validate_proposal`.
- **This specification:** path `docs/architecture/opencode_architecture.md` registered in `docs/LOGOGRAPHY.md` (section 3) and in `docs/development/bitacora.md` (Entry #009).
