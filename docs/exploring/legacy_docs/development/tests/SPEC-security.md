# SPEC — TridenGuard Security (Zero-Trust Gate)

> Normative (RFC 2119). Internal spec: AGENTS.md §2.3 (network blocking) and
> §2.4 (literal grounding) + README_CODE_ENGINE.md (5 Radicals). Formal
> citation: [Dual Boundary Pattern — Deterministic Execution via Binary
> Verification](../../Dual%20Boundary%20Pattern_%20Deterministic%20Execution%20via%20Binary%20Verification.md)
> — byte-level verification: path canonicalization, repo-root containment,
> UTF-8 binary subsequence matching over `read_bytes()`, `\x00`
> sanitization, and silent denial.

## Scope

Deterministic gate `tools/tridenguard_validator.py` (validate_proposal) and
its MCP server over stdio JSON-RPC, plus the operator config perimeter: the
`permission` block of `opencode.jsonc` (bash permission matrix for git
subcommands and remote/deny primitives).

Physical (byte-level) verification follows the Dual Boundary Pattern (formal
citation in the header). SEC-M-08..12 (Phase 3) specify: canonicalization and
repo-root containment, `\x00` sanitization, the expanded network-token
denylist, UTF-8 binary subsequence matching, and silent denial.

## Normative requirements

- **SEC-M-01** MUST: validate_proposal rejects invalid JSON with status QUARANTINED and decision INVALID_JSON.
- **SEC-M-02** MUST: Safety_Abort != NONE blocks with BLOCKED_BY_SAFETY_GATE.
- **SEC-M-03** MUST NOT: Fragments with fetch/axios/urllib.request/import requests pass the gate; they are blocked with ABORTED_VIOLATES_ZERO_TRUST.
- **SEC-M-04** MUST: For REFACTOR/FIX/AUDIT, the grounding must exist literally in the target file; otherwise ABORTED_GROUNDING_FAILED.
- **SEC-M-07** MUST: For REFACTOR/FIX/AUDIT, a proposal without a target_file is rejected with ABORTED_GROUNDING_FAILED (no fail-open); a missing or unreadable target file is also a grounding failure.
- **SEC-M-05** MUST: With valid literal grounding, the proposal returns VALIDATED/EXECUTE_SAFE with and_gate_ok.
- **SEC-M-06** MUST: The MCP server (stdio JSON-RPC) responds initialize/tools-list/tools-call without corrupting the stdout channel.
- **SEC-M-08** MUST NOT: a `target_file` whose canonical path (symlinks and `..` resolved) falls outside the authorized repository root pass the grounding gate; MUST return `ABORTED_GROUNDING_FAILED`.
- **SEC-M-09** MUST: inputs containing a null byte (`\x00` raw or JSON-escaped `\u0000`) are rejected silently (`QUARANTINED` / `ABORTED_VIOLATES_ZERO_TRUST`) before processing.
- **SEC-M-10** MUST NOT: fragments with `httpx`, `socket`, `urllib3`, `subprocess`, `curl`, `wget`, `aiohttp`, `importlib`, `os.system`, `requests.` pass the Zero-Trust Gate; MUST return `ABORTED_VIOLATES_ZERO_TRUST`.
- **SEC-M-11** MUST: grounding is verified via exact UTF-8 binary subsequence over `read_bytes()`; files with non-UTF-8 bytes must not crash the gate (fail-closed).
- **SEC-M-12** MUST: grounding/zero-trust failures are silent (no target path / OS details in the decision) and every decision keeps `status` + `final_decision`.
- **SEC-M-13** MUST: the opencode.jsonc bash permission matrix MUST NOT grant 'git *' wildcard allow; only the explicit read/inspection subcommands (status, diff, log, show, rev-parse, grep, blame, ls-files, add) MAY be allowed, with all mutating/remote git subcommands requiring confirmation.
- **SEC-M-14** MUST: `build_response_format(response_model, *, strict=True, name=None)` returns `{"type": "json_schema", "json_schema": {"name": <name>, "schema": response_model.model_json_schema(), "strict": <strict>}}`.
- **SEC-M-15** MUST: in strict mode, the emitted JSON schema declares `additionalProperties: false` and a `required` list covering every property (no optional leak).
- **SEC-M-16** MUST: `parse_proposal_json` follows the ordered pipeline (1 pure `json.loads` → 2 fenced/embedded extraction → 3 extraction + `json.loads` → 4 extraction + repair) and tracks `used_repair`.
- **SEC-M-17** MUST: when repaired JSON yields a payload missing required fields, `parse_proposal` raises `JSONParsingError` (no semantic false positive).
- **SEC-M-18** MUST: `parse_proposal` validates against `AgentMutationProposal` and logs `ValidationError` at DEBUG with `exc_info=True`; the validator integration maps parse failure to `INVALID_JSON` preserving SEC-M-01..12 outcomes.
