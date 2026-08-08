---
description: Run the Red-Green-Refactor TDD cycle for the Traianus substrate, one phase at a time, with regression via pytest and the C1 audit harness.
agent: build
---

Load the tdd-cycle skill (use the skill tool). Apply it to: $ARGUMENTS

Work one phase at a time. RED: write the failing test first and verify it fails. GREEN: implement the minimal change. REFACTOR: clean up while keeping tests green.

Regression gate (do not skip): run `python -m pytest tests/ -m "not model"` and, for consolidation-rate changes, `python tools/audit_harness.py`.

Hard rules from AGENTS.md: never alter tests to mask a failure; never edit source to chase the test; no external network primitives in the Implementation_Block; lifecycle states restricted to the CHECK-constrained set.
