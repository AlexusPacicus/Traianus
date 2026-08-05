---
description: Coordinates the execution of the Action Plan emitted by @plan-architect, one phase at a time, controlling the TDD cycle.
agent: orchestrator
---

Take the latest Action Plan of @plan-architect and coordinate its execution with @fixer, @antigravity-compiler and @logographer.

Operational rule: process ONE phase at a time; do not assign the next one until the executor reports success in the deterministic test (pytest or C1 harness).

Conclude with a consolidated summary for @plan-architect and the User.
