---
description: Append a new operational delta (Δ_n) to the append-only docs/LEDGER.md.
agent: build
---

Append a new entry to docs/LEDGER.md. Topic: $ARGUMENTS

Rules (append-only invariant):
- Next seq = max existing seq + 1; never modify or delete an existing row.
- Format mirrors seq 1-7: date, short title, bullets (context/scope/verification), Gate line.
- Update docs/LOGOGRAPHY.md only if the file-tree topology changed; it does not carry history.
- Keep it in English (project OSS language).

Do not commit unless explicitly asked.
