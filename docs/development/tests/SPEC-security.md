# SPEC — TridenGuard Security (Zero-Trust Gate)

> Normative (RFC 2119). Internal spec: AGENTS.md §2.3 (network blocking) and
> §2.4 (literal grounding) + README_CODE_ENGINE.md (5 Radicals).

## Scope

Deterministic gate `tools/tridenguard_validator.py` (validate_proposal) and
its MCP server over stdio JSON-RPC.

## Normative requirements

- **SEC-M-01** MUST: validate_proposal rejects invalid JSON with status QUARANTINED and decision INVALID_JSON.
- **SEC-M-02** MUST: Safety_Abort != NONE blocks with BLOCKED_BY_SAFETY_GATE.
- **SEC-M-03** MUST NOT: Fragments with fetch/axios/urllib.request/import requests pass the gate; they are blocked with ABORTED_VIOLATES_ZERO_TRUST.
- **SEC-M-04** MUST: For REFACTOR/FIX/AUDIT, the grounding must exist literally in the target file; otherwise ABORTED_GROUNDING_FAILED.
- **SEC-M-05** MUST: With valid literal grounding, the proposal returns VALIDATED/EXECUTE_SAFE with and_gate_ok.
- **SEC-M-06** MUST: The MCP server (stdio JSON-RPC) responds initialize/tools-list/tools-call without corrupting the stdout channel.
