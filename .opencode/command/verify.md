---
description: Runs the full regression (pytest, C1 harness and MCP smoke) and reports the validation status.
agent: fixer
---

Run the empirical validation of the TDD cycle over Traianus/TridenGuard:

1. `python3 -m pytest tests/ -q`
2. `python3 tools/audit_harness.py`
3. MCP smoke (handshake + tools/list):
   printf '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"clientInfo":{"name":"auditor","version":"0.0.1"}}}\n{"jsonrpc":"2.0","id":2,"method":"tools/list"}\n' \
     | python3 tools/tridenguard_validator.py

Close with `REPORT_TO_ORCHESTRATOR`: test count, C1 GUARD status and MCP serverInfo (expected v1.1.0).
