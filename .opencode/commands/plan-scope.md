---
description: Produce a plan + scope for Traianus work, tracked as GitHub issues, without executing code changes.
agent: build
---

Create a plan and scope for: $ARGUMENTS

Deliverables:
1. Diagnosis of the current state (git branches, working tree, doc drift, open issues).
2. Workstreams with concrete acceptance criteria ("Definición de hecho").
3. One GitHub issue per workstream via `gh issue create` — ask before creating each.

Grounding rules:
- Follow AGENTS.md and the remediation priorities in TRAIANUS_AUDIT.md.
- Every issue gets: Contexto, Alcance, Definición de hecho.
- Do not modify source code, open PRs, or push during this command — planning only.
