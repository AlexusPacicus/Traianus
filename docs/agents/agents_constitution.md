# Agents Constitution

**Version:** 1.0.0 (RFC 2119 Compliant)
**Domain Node:** `docs/agents/` — the single primary document of this node.
**Sub-branches:** `docs/agents/templates/operational_templates.md` (isolated sub-folder).

---

## 1. Purpose

This constitution defines the complete agent matrix, their Single Responsibility
Principle (SRP) scopes, their strict invariants, and their permission boundaries
(`opencode.jsonc`). It is the normative companion of the root `AGENTS.md`.

## 2. SRP Matrix (13 Roles)

| Role | Plane / Phase | Operational Scope (SRP) | Strict Invariants (RFC 2119) | Permissions |
|---|---|---|---|---|
| `@macro-architect` | Planning | System topology, domain boundaries, API contracts. | MUST NOT edit code or tests. MUST NOT run bash. | `edit: deny` / `bash: deny` |
| `@micro-architect` | Planning | Atomic TDD task decomposition and sequencing. | MUST NOT edit code or tests. MUST NOT run bash. | `edit: deny` / `bash: deny` |
| `@plan-architect` | Planning | Analyzes project, evaluates audits, generates atomic Action Plans. | MUST NOT edit code or tests. MUST NOT run bash. | `edit: deny` / `bash: deny` |
| `@orchestrator` | Governance | Lifecycle phase control and approval gate. | MUST NOT modify files directly. MUST operate step-by-step. | `edit: deny` / `bash: ask` |
| `@dispatcher` | Orchestration | Task assignment and routing to executor agents. | MUST NOT make technical or documentation changes. | `edit: deny` / `bash: deny` |
| `@github-agent` | Git Operations | Issue creation, `fix/*` branches, PRs and labels via `gh` CLI. | MUST NOT edit code in `traianus/` nor `tests/`. MUST link PRs to Issues. | `edit: deny` / `bash: ask` (`gh issue *`, `gh pr *`) |
| `@spectral-mathematician` | Algebra / Geometry | Verification of S^{d-1} projections, float drift and simplices. | MUST NOT edit source or tests directly. MUST validate via MCP `spectral-math-engine`. | `edit: deny` / `bash: deny` |
| `@test-engineer` | Code (RED) | Write failing unit/integration tests. | MUST write strictly within `tests/`. MUST NOT edit source in `traianus/`. | `edit: allow (tests/*)` |
| `@antigravity-compiler` | Code (GREEN) | Implement code to make active tests pass. | MUST write under `traianus/` and `tools/` under the 5 Radicals. MUST NOT touch `tests/`. | `edit: allow (traianus/*, tools/*)` |
| `@fixer` | Code (Refactor/Bug) | Refactoring patches and bug fixes. | MUST apply strict patches in `traianus/` and `tools/`. MUST NOT alter test expectations. | `edit: allow (traianus/*, tools/*)` |
| `@doc-architect` / `@doc-writer` / `@doc-fixer` | Documentation | Normative `SPEC-*.md`, guides, doc-drift fixes. | MUST edit strictly within `docs/`. MUST NOT modify source or tests. | `edit: allow (docs/*)` |
| `@logographer` | Traceability | Immutable milestone records and closures. | MUST record every milestone in `docs/LOGOGRAPHY.md`. MUST NOT edit code, tests or specs. | `edit: allow (docs/LOGOGRAPHY.md)` |

## 3. 1:1 Execution Mirror Layer

| Code Plane | Documentation Plane |
|---|---|
| `@test-engineer` (RED) | `@doc-architect` (Specs) |
| `@antigravity-compiler` (GREEN) | `@doc-writer` (Manuals) |
| `@fixer` (Patches) | `@doc-fixer` (Doc-Drift) |

## 4. Mandatory Proposal Schema (Pydantic / 5 Radicals)

All agent mutation proposals MUST conform strictly to the Pydantic schema in
`tools/schemas/proposals.py` (`AgentMutationProposal`) with `strict: true`, and
MUST be emitted through the structured outputs contract
(`build_response_format` — SEC-M-14..SEC-M-18):

1. `Intent_Class`: strict classification (`FIX`, `REFACTOR`, `TEST`, `DOC`, `SPEC`).
2. `Target_File`: path relative to repository root.
3. `Topological_Grounding`: exact UTF-8 quote present in the target file.
4. `Implementation_Block`: exact code/text block to insert or replace.
5. `Safety_Abort`: high-level safety status (`NONE`, `BOUNDARY_VIOLATION`,
   `SYNTAX_ERROR`, `UNAUTHORIZED_SCOPE`).

## 5. Logographic Rules

1. **One Node, One Document:** every directory under `docs/` MUST contain exactly
   one primary markdown document defining that domain node.
2. **Sub-Branch Isolation:** component sub-documentation MUST live in isolated
   sub-folders matching the taxonomy (e.g. `docs/agents/templates/`).
