# Threat Model: Semantic Capability Vulnerability

**Date:** 2026-08-03 (canonicalized from legacy spec)
**Scope:** Traianus boundary-validator and OpenCode governance

---

## 1. The Semantic Capability Vulnerability

Modern LLM agent frameworks construct execution flows by processing system instructions, constraints, and untrusted external data within a shared probabilistic context window. Because the natural language engine evaluates both authorization rules and potential exploit payloads semantically, threat actors can bypass boundaries via Indirect Prompt Injections (IDPI) or contextual manipulation.

**Failure Mode:** Allowing semantic evaluation logic (the LLM) to govern physical execution boundaries results in non-deterministic security, capability laundering, and vulnerability to string-based evasion (e.g., Unicode homoglyphs, null bytes).

## 2. The Dual Boundary Pattern & Capability Matrix

The Dual Boundary Pattern resolves this by enforcing strict separation of concerns, mirroring the Harvard Architecture at the execution layer:

> * **Data Plane (Untrusted / Probabilistic):** LLMs, prompt environments, and parsed external text. This layer proposes actions (tool calls or code refactoring) but holds **zero execution authority**.
> * **Control Plane (Trusted / Deterministic):** A pre-compiled, immutable Capability Matrix governing execution limits. It intercepts proposals in-flight and verifies them physically at the byte/system level before authorizing access to host resources.

This separation is enforced by three deterministic gates in the boundary-validator:
1. **Safety Gate** — rejects proposals where `Safety_Abort != NONE`.
2. **Zero-Trust Capability Gate** — evaluates proposed actions against an immutable 4-tuple Capability Matrix: `(capability_name, target_parameter, subsystem, boundary_rule)`. Rejects any capability or parameter not explicitly mapped in the matrix, bypassing lexical token denylists entirely.
3. **Grounding Gate** — validates that the `Topological_Grounding` quote exists literally (byte-level UTF-8 subsequence) within the target file.

## 3. Physical Verification Mechanisms

To eliminate evasions based on character encoding, formatting, or path abstraction, validation logic is reduced to binary and canonical operations:

* **Filesystem Containment (Path Canonicalization):** Target paths are resolved to their absolute physical location via `Path.resolve(strict=True)`. Strict containment within the repository root is verified with `is_relative_to()`. Neutralizes path traversal (`../`), symlink escapes, and prefix clipping (SEC-M-08).
* **Literal Grounding (Subsequence Matching):** Target files are read as raw byte streams (`read_bytes()`). The grounding quote is encoded to UTF-8 and verified via exact binary subsequence matching (`quote_bytes in file_bytes`). Neutralizes Unicode homoglyphs and formatting-based evasions (SEC-M-05).
* **Memory Sanitization:** Null bytes (`\x00`) and strict UTF-8 decoding failures (`errors="strict"`) are rejected at the ingress perimeter (SEC-M-09, SEC-M-11).

## 4. Silent Denial

When an agent proposal violates a constraint, providing explicit diagnostic errors (e.g., "Access Denied: Path outside root") creates an adversarial feedback loop, allowing the attacker or a compromised LLM to iterate and optimize the exploit payload.

The pattern mandates **Silent Denial** (SEC-M-12):
1. The physical host execution is skipped (resources are shielded).
2. A detailed forensic log is appended to the isolated audit ledger (`audit_log` table in SQLite).
3. The control plane returns a synthetic, neutral state to the agent context (`QUARANTINED` with no path or reason leakage).

This ruptures the feedback loop: the attacker cannot determine if the exploit was structurally intercepted or simply failed logically.

## 5. Governing Invariants

| Invariant | RFC 2119 | Code Reference |
|---|---|---|
| Total Function | The validator MUST NOT raise uncaught exceptions | `validator.py:135-137` |
| Fail-Closed | Any internal error MUST produce `QUARANTINED` | `validator.py:135-137` |
| Byte-Level Grounding | The `Topological_Grounding` quote MUST exist as raw UTF-8 bytes | `validator.py:127-130` |
| Path Containment | `Target_File` MUST resolve within `REPO_ROOT` | `validator.py:123-125` |
| Silent Denial | Error responses MUST NOT leak paths, reasons, or OS details | `validator.py:39-42` |
