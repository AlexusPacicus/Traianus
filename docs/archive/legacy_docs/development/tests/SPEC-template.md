# Normative Test Specification Template (SPEC)

> **Usage:** every SPEC lives in `docs/development/tests/SPEC-*.md` and
> PRECEDES the tests it implements (Spec-First: the specification precedes
> the tests). Grounding: the contracts and architecture rules are translated
> into an explicit matrix of unit/integration tests.

## Normative convention (RFC 2119)

- **MUST** — absolute requirement; failing it breaks the SPEC.
- **MUST NOT** — absolute prohibition.
- **SHOULD** — recommendation; deviation requires documented justification.

## Requirement structure

Each normative requirement is declared as a parseable line:

```
- **<ID>** MUST|MUST NOT|SHOULD: <verifiable behavior>.
```

IDs are unique per SPEC and are referenced from the test header normatives
(`Normative:` + `Coverage:`), guaranteeing 1:1 doc → SPEC → test
traceability.

## Traceability

- Each test file declares in its header docstring:
  - `Normative: docs/development/tests/SPEC-<block>.md`
  - `Coverage: <ID1>, <ID2>, ...`
- Each test function references at least one ID of its Coverage in its
  docstring (or carries it in the name: `test_<BLOCK>_<ID>_<behavior>`).
- The guardians in `tests/meta/` verify: full coverage (no gaps), 1:1 (no
  duplicates), zero orphan tests.
