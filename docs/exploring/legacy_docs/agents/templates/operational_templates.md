# Operational Templates — OpenCode Standard

**Version:** 2.0.0 (Structured Outputs Contract)
**Logographic Location:** `docs/agents/templates/operational_templates.md`
**Status:** Normative / Mandatory
**Compliance:** RFC 2119 (MUST, MUST NOT, SHALL)

---

## 1. Template 1: Mutation Proposal (5 Radicals, Structured Outputs)

**Sender (MUST):** Execution Agent (`@test-engineer`, `@antigravity-compiler`, `@fixer`, `@doc-writer`, `@doc-fixer`).
**Receiver (MUST):** MCP Server `tridenguard-validator` (`validate_proposal` tool).
**Purpose:** Emit any code or documentation mutation proposal with physical byte-level grounding and a strict structured output contract.

### 1.1 Response Format Contract (SEC-M-14)

Every proposal MUST be sampled against the strict JSON Schema emitted by:

```python
from tools.schemas.proposals import AgentMutationProposal, build_response_format

build_response_format(AgentMutationProposal, strict=True, name="AgentMutationProposal")
# => {
#      "type": "json_schema",
#      "json_schema": {
#        "name": "AgentMutationProposal",
#        "schema": AgentMutationProposal.model_json_schema(),  # additionalProperties: false
#        "strict": true,
#      },
#    }
```

### 1.2 Mandatory Payload (derived from `AgentMutationProposal.model_json_schema()`)

Strict mode (SEC-M-15) MUST declare `additionalProperties: false` and a `required`
list covering every property — no optional leak. Example payload:

```json
{
  "Intent_Class": "FIX",
  "Target_File": "traianus/app.py",
  "Topological_Grounding": "auto_calibrate_critical_threshold()",
  "Implementation_Block": "def auto_calibrate_critical_threshold() -> float:\n    ...",
  "Safety_Abort": "NONE"
}
```

### 1.3 Evaluation Rules by MCP

- `Topological_Grounding` MUST match the target file content exactly (character by character, UTF-8 byte match).
- `Target_File` MUST be a valid canonical path contained within the repository root (`is_relative_to(REPO_ROOT)`).
- `Implementation_Block` MUST NOT include calls to forbidden network or system primitives (`fetch`, `requests`, `socket`, `subprocess`, etc.).
- `Safety_Abort` MUST be `NONE` for a proposal to reach the grounding gate.

### 1.4 DoD — Acceptance Criteria (Structured Outputs)

| # | Criterion | Gate |
|---|---|---|
| 1 | `build_response_format` emits `json_schema` + `strict: true` | SEC-M-14 |
| 2 | Strict schema forbids extra properties and requires all properties | SEC-M-15 |
| 3 | Parser pipeline is ordered and reports `used_repair` | SEC-M-16 |
| 4 | Repaired-but-incomplete JSON raises `JSONParsingError` | SEC-M-17 |
| 5 | `ValidationError` logged at DEBUG; validator still returns `INVALID_JSON` | SEC-M-18 |
| 6 | Hermetic suite green: `pytest tests -m "not model" -q` | — |

### 1.5 Legacy Mode (Template 1 v1.0.0 — deprecated, NOT recommended)

Free-form JSON payloads without the strict schema contract are deprecated.
They MUST be migrated to the structured outputs contract above; the `tridenguard-validator`
still parses them for backward compatibility but the strict contract is the canonical form.

---

## 2. Template 2: Task Dispatch Order

**Sender (MUST):** `@dispatcher`
**Receiver (MUST):** Assigned Execution Agent
**Purpose:** Hand off the operational turn to a specialized agent defining an atomic scope of 1 single TDD step.

```markdown
### Task Assignment: [TASK_ID]

* **Assigned Agent:** `@test-engineer`
* **TDD Phase / Cycle:** RED
* **Target File (`Target_File`):** `tests/bloques/ingesta/test_especificos.py`
* **Normative Requirement:** `docs/specifications/security_normative.md` (SEC-M-03)

#### Context / Anchor (`Topological_Grounding`):
> `"def test_ingestion_IN04_503_on_persistence_failure():"`

#### Atomic Instruction:
> Write the test verifying that a SQLite database I/O failure during ingestion
> returns an explicit HTTP 503 status code instead of a synthetic 200 OK.

> **Explicit Constraint:** Emit the response strictly using Template 1 (Structured Outputs contract).
```

---

## 3. Template 3: Logbook Milestone Entry

**Sender (MUST):** `@logographer`
**Receiver (MUST):** `docs/LOGOGRAPHY.md`
**Purpose:** Immutably record phase completions, release milestones, and security gate decisions.

```markdown
## [2026-08-03T22:15:00Z] — Milestone Completion: PHASE 2 (Security Normative)

* **Session ID:** `3a8f9c12-7b1e-42f0-9a3d-82e14b01934e`
* **Signing Agent:** `@logographer`
* **Referenced Specification:** `docs/specifications/security_normative.md`
* **Summary of Changes:**
  * Defined and incorporated normative rules SEC-M-01 through SEC-M-18 following the RFC 2119 standard.
* **Control Plane Verdict:** `APPROVED`
* **Repository State:** Clean (`git status`)
```
