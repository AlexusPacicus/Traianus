# 🛡️ Normative Security Specification (`SPEC-security.md`)

**Version:** 1.0.0 (RFC 2119 Compliant)  
**Canonical File:** `docs/specifications/security_normative.md`  
**Target Gate:** `tools/tridenguard_validator.py` (TridenGuard MCP Server)

---

## 1. Purpose and Perimeter

This specification establishes the legally binding physical invariants for in-flight proposal interception. The TridenGuard validator **MUST** evaluate all agent mutation proposals against these rules prior to execution.

The validator operates as a total function: it **MUST NOT** raise uncaught exceptions to the caller and **MUST** fail closed (`QUARANTINED`) upon any internal error.

---

## 2. Invariant Interception Rules (SEC-M-01 to SEC-M-13)

### SEC-M-01: Schema & JSON Validity
- The proposal payload **MUST** be a syntactically valid JSON object conforming to `AgentMutationProposal`.
- If JSON parsing fails, the validator **MUST** return `status: "QUARANTINED"` with `final_decision: "INVALID_JSON"`.

### SEC-M-02: Safety Abort Gate
- If the proposal's `Safety_Abort` field is not `"NONE"`, the proposal **MUST** be rejected immediately.
- The validator **MUST** return `final_decision: "BLOCKED_BY_SAFETY_GATE"`.

### SEC-M-03: Zero-Trust Network Token Denylist
- The `Implementation_Block` **MUST NOT** contain external network primitives (`fetch(`, `axios`, `urllib.request`, `import requests`, `httpx`, `socket`, `urllib3`, `aiohttp`, `http.client`).
- Any detected network token **MUST** trigger `final_decision: "ABORTED_VIOLATES_ZERO_TRUST"`.

### SEC-M-04: Grounding Citation Requirement
- Mutating intent classes (`REFACTOR`, `FIX`, `AUDIT`) **MUST** contain a non-empty `Topological_Grounding` string.
- If grounding is missing or empty for mutating intents, the proposal **MUST** be rejected with `final_decision: "ABORTED_GROUNDING_FAILED"`.

### SEC-M-05: Literal Grounding Match
- The string declared in `Topological_Grounding` **MUST** exist literally (character for character) within the target file.
- If the quote is missing from the target file, the validator **MUST** return `final_decision: "ABORTED_GROUNDING_FAILED"`.

### SEC-M-06: Stdio MCP Protocol Integrity
- The validator **MUST** communicate over stdio via line-delimited JSON-RPC 2.0 protocol.
- All internal diagnostic logs **MUST** be routed to `stderr` to avoid corrupting the stdout JSON-RPC response stream.

### SEC-M-07: Mandatory Target File for Mutating Intents
- Proposals specifying `FIX`, `REFACTOR`, or `AUDIT` **MUST** provide a non-empty `Target_File` path.
- Omitting `Target_File` on mutating intents **MUST** fail closed as `ABORTED_GROUNDING_FAILED` (no fail-open allowed).

### SEC-M-08: Spatial Canonical Isolation & Path Containment
- The validator **MUST** resolve the target file path using `Path.resolve(strict=True)` to expand symlinks and eliminate `..` traversals.
- The canonical path **MUST** satisfy `is_relative_to(REPO_ROOT)`.
- Any path attempting to escape `REPO_ROOT` **MUST** return `final_decision: "ABORTED_GROUNDING_FAILED"`.

### SEC-M-09: Memory Sanitization (`\x00` Rejection)
- The raw payload string and target path **MUST NOT** contain null bytes (`\x00` or JSON-escaped `\u0000`).
- Detection of null bytes **MUST** immediately quarantine the request with `final_decision: "ABORTED_VIOLATES_ZERO_TRUST"`.

### SEC-M-10: Extended Execution & Process Token Denylist
- In addition to network tokens, `Implementation_Block` **MUST NOT** contain process execution primitives (`subprocess`, `curl`, `wget`, `importlib`, `os.system`, `os.popen`, `telnet`, `nc `, `ftp`).
- Any match **MUST** yield `final_decision: "ABORTED_VIOLATES_ZERO_TRUST"`.

### SEC-M-11: Non-UTF-8 Fail-Closed Inspection
- Grounding verification **MUST** execute via binary UTF-8 subsequence matching over `read_bytes()`.
- If the target file is non-UTF-8 or unreadable, the validator **MUST NOT** crash with `UnicodeDecodeError`; it **MUST** return `ABORTED_GROUNDING_FAILED`.

### SEC-M-12: Silent Denial Protocol
- Grounding and security rejections **MUST NOT** leak absolute host paths, OS user details, or stack tracebacks in the response JSON.
- Rejections **MUST** return generic synthetic failure responses to break adversarial LLM optimization loops.

### SEC-M-13: Broad-First CLI Permission Ordering
- In `opencode.jsonc`, bash permission matching **MUST** evaluate broad catch-alls first (`"*": "ask"`, `"rm *": "deny"`), followed by narrow read-only git allow rules.
- Wildcard git allows (`"git *": "allow"`) **MUST NOT** be configured; only explicit inspection subcommands (`status`, `diff`, `log`, `show`, `rev-parse`, `grep`, `blame`, `ls-files`, `add`) are permitted.

---

## 3. Telemetry Schema DDL (`opencode_telemetry`)

All rejected or quarantined attempts **MUST** be recorded asynchronously in the local forensic table:

```sql
CREATE TABLE IF NOT EXISTS opencode_telemetry (
    id TEXT PRIMARY KEY,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    intent_class TEXT NOT NULL,
    target_file TEXT,
    final_decision TEXT NOT NULL,
    safety_abort TEXT NOT NULL,
    payload_hash TEXT NOT NULL
);