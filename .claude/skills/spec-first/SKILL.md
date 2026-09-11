---
name: spec-first
description: Use when authoring or reviewing normative specifications under the Traianus 5 Radicals contract — SPEC Intent_Class, structured proposal templates, and the frozen spec layout. Emit spec mutations through the boundary-validator Zero-Trust gate.
---

# Spec-First — Authoring Normative Specifications

Spec-first governs authoring and reviewing normative documents emitted as
**SPEC** mutations under the 5 Radicals contract.

## The 5 Radicals contract

Every change proposal (including SPEC mutations) MUST conform to
`AgentMutationProposal` (Pydantic, `strict: true`) in
`traianus/security/schemas/proposals.py`:

1. `Intent_Class`: `[FIX | REFACTOR | TEST | DOC | SPEC | AUDIT]` → `SPEC` for spec work.
2. `Target_File`: relative path strictly within `REPO_ROOT`.
3. `Topological_Grounding`: exact UTF-8 quote present literally in the target file.
4. `Implementation_Block`: exact text / code block to insert or replace at the anchor.
5. `Safety_Abort`: `[NONE | BOUNDARY_VIOLATION | SYNTAX_ERROR | UNAUTHORIZED_SCOPE]`.

Proposals MUST be emitted through `build_response_format(AgentMutationProposal)`
(SEC-M-14..SEC-M-18) and gated by the boundary-validator `validate_proposal`
(Safety, Zero-Trust Capability, and Grounding gates).

## SPEC document template

Spec targets live under `docs/specifications/<NAME>.md`. Each spec MUST contain:

```markdown
# <TITLE> (Normative Specification)

## 1. Scope
Statement of what the specification governs and its explicit non-goals.

## 2. Normative Requirements
RFC 2119 MUST/SHOULD clauses that are deterministic and testable.

## 3. Mathematical Formulation
Formal notation ($\mathbf{v}$, $S_n$, operators) with no application-domain
concepts (AGENTS §3.2).

## 4. Invariants
Concrete, machine-checkable invariants tied to `traianus/` or `tools/`.

## 5. Verification
The deterministic test(s) / audit harness that will mark the spec GREEN.
```

## Rules

- A spec is **not normative** until it has a deterministic verification path and
  is wired into `docs/INDEX.md`.
- Application-domain terms ("ideas", "thoughts", "hyperfocus") belong to the
  client (RefApp-01), NEVER in `traianus/` specs (AGENTS §3.2).
- Do not advance a spec from Draft to Normative without a GREEN verification.
- Golden rule: neurons propose, rules dispose — every SPEC mutation passes the
  boundary-validator gates.
