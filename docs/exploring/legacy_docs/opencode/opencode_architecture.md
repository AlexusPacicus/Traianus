# OpenCode Governance and Integration Architecture

**Status:** Canonical (v1.2.0)

**Date:** 2026-08-03

**Scope:** Agent Governance, MCP Server (`tools/tridenguard_validator.py`) and CLI Matrix (`opencode.jsonc`)

---

## 1. The Dual Boundary Pattern in OpenCode

The OpenCode architecture separates the execution environment into two physically isolated planes:

```
┌────────────────────────────────────────────────────────────────────────┐
│ DATA PLANE (Probabilistic / No Authority)                             │
│ LLM Agents (@plan-architect, @orchestrator, @fixer, etc.)              │
│ Emits proposals in the structured TOON/JSON format.                    │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ In-Flight Interception
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│ CONTROL PLANE (Deterministic / Binary - C-Speed)                      │
│ MCP TridenGuard + opencode.jsonc CLI Matrix                            │
│ Physical byte verification, path canonicality and Silent Denial.       │
└────────────────────────────────────────────────────────────────────────┘

```

* **Data Plane (LLM):** Generates typed intents (`GENERATE`, `REFACTOR`, `FIX`, `AUDIT`). It holds **zero direct execution authority** over the host system.
* **Control Plane (Deterministic):** Intercepts every proposal *in-flight* and applies physical binary verifications before authorizing access to the file system, network or terminal.

---

## 2. Physical Implications in the MCP Server (`tools/tridenguard_validator.py`)

The security gates abandon semantic evaluation and plain-text (`str`) denylists:

1. **Spatial Canonicalization (`Target_File`):**
* Every target path is resolved to its absolute physical location via `Path(target).resolve(strict=True)`.
* Strict containment within the repository is verified with `is_relative_to()`. This prevents *path traversal* (`../`) attacks and symlink escapes.

2. **Binary Subsequence Grounding (`Topological_Grounding`):**
* The target file is read as a pure byte stream (`read_bytes()`).
* The grounding quote is encoded to UTF-8 (`quote_bytes`) and checked via exact subsequence matching: `quote_bytes in file_bytes`.

3. **Memory Sanitization:**
* Immediate detection and blocking of null bytes (`\x00`) or memory-termination patterns before evaluating the proposal.

---

## 3. Governance of the CLI Matrix (`opencode.jsonc`)

The configuration file enforces unbreakable limits at the OS process level:

* **Wildcard Prohibition:** The rule `"git *": "allow"` is prohibited.
* **Explicit Enumeration:** Only read/inspection commands without side effects are authorized (`git status`, `git diff`, `git log`, `pytest`).
* **Mutation Interception:** Every mutating or remote-sync command (`git commit`, `git push`, `git checkout`) requires human authorization (`"bash": { "git ...": "ask" }`).

---

## 4. Physical-Binary Containment of the `@orchestrator`

The orchestrator has no autonomous execution capability nor command chaining:

* **Permission Invariant:** Immutably configured with `edit: deny` and `bash: ask`.
* **Single-Step Execution:** The Control Plane rejects any attempt to send multiple coupled commands. Each step of the TDD cycle requires an individual validation cycle.

---

## 5. Telemetry and Silent Denial by Dogfooding

* **Silent Denial:** For invalid proposals (`QUARANTINED`), the Control Plane returns a synthetic verdict to the agent to break the adversarial optimization loop.
* **Local Append-Only Persistence:** The real forensic trace is recorded in the Traianus database in the `opencode_telemetry` table:

```sql
CREATE TABLE IF NOT EXISTS opencode_telemetry (
    session_id TEXT NOT NULL,
    seq INTEGER NOT NULL,
    agent_role TEXT NOT NULL,
    intent_class TEXT NOT NULL,
    target_file TEXT NOT NULL,
    grounding_hash TEXT NOT NULL,
    verdict TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    sys_internal_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (session_id, seq)
);

```

---

## 6. Mirror Architecture (1:1 Dual Plane)

There is a bijective symmetry between code production and its documentary backing:

```
Code Plane (traianus/, tests/) ◄───────── 1:1 ─────────► Documentation Plane (docs/, SPEC-*.md)
----------------------------------                             ----------------------------------------
@antigravity-compiler / @fixer                                 @doc-architect (Specs / RFC 2119 Norms)
Code / TDD Patches                                             @logographer (LOGOGRAPHY.md Ledger)

```

* No code mutation is valid without its corresponding specification in `docs/` or `SPEC-*.md`.
* Every TDD phase closure must be recorded in `docs/LOGOGRAPHY.md`.

---

## 7. Secondary Impacts

1. **Cross-Platform Determinism:** Byte-level verification unifies behavior across environments (line endings `\n` vs `\r\n` and path separators).
2. **Token Efficiency:** The prompt context is reduced to the rigid TOON/JSON schema.
3. **Sub-millisecond Latency:** Binary checks in Python operate at the C level ($<1\text{ ms}$).
