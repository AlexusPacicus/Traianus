---
name: tridenguard-5-radicales
description: Use when generating or validating code proposals under the 5 Radicales contract (Intent_Class, Runtime_Contract, Implementation_Block, Topological_Grounding, Safety_Abort), or when checking a proposal against the tridenguard-validator MCP Zero-Trust gates.
---

# TridenGuard 5 Radicals

Every change proposal must contain exactly:
1. `Intent_Class`: [GENERATE | REFACTOR | FIX | AUDIT | NONE]
2. `Runtime_Contract`: target environment and constraints (local/offline, <= 8 GB RAM).
3. `Implementation_Block`: executable source code snippet.
4. `Topological_Grounding`: exact textual quote, character by character, of the original code.
5. `Safety_Abort`: [NONE | UNSAFE_REQUEST_DETECTED | MISSING_DEPENDENCY_SPEC]

## Deterministic gates (validate_proposal)
1. Safety Gate: Safety_Abort != "NONE" -> BLOCKED_BY_SAFETY_GATE
2. Zero-Trust Gate: forbidden network token (fetch(, axios, urllib.request, import requests) -> ABORTED_VIOLATES_ZERO_TRUST
3. Grounding Gate: non-exact quote in target_file (REFACTOR/FIX/AUDIT) -> ABORTED_GROUNDING_FAILED

Only if the three gates pass: VALIDATED / EXECUTE_SAFE with and_gate_ok: True.
Golden rule: neurons propose, rules dispose.
