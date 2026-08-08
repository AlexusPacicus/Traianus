---
description: Audit the repository for Spanish-language prose (OSS l10n) and report findings.
agent: build
---

Run the lexical Spanish audit: `python tools/audit_spanish_terms.py`

Scope: $ARGUMENTS (default: whole repository).

Report findings and the exit code (1 = findings present). Classify each hit as genuine Spanish prose vs. false positive — the auditor's marker set includes English-valid domain tokens (`vector`, `token`, `host`, `base`, `note`) and DB column names inside SQL strings (`simbolo`). Do NOT translate code identifiers, function names, or DB schema column names. Propose renames only for prose/comments/docstrings, and only as a proposal (5 Radicals) when touching source.
