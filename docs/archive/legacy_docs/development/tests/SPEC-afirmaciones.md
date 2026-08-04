# SPEC — Documentary Claims

> Normative (RFC 2119). Grounding: TRAIANUS_AUDIT.md:35 — "making the
> claims match the code". Every documentary claim in the repo must be backed
> by a test (registry in tests/afirmaciones/claims_registry.py) or marked as
> RED/WP.

## Scope

Claims from Traianus sources (ADR.md, CONTRACTS_AND_PRISMS.md,
PROJECT_IDENTITY.md, Project_architecture.md, README.md, audit) with state
ACTIVE | RED | SUP | WP. RED probes with disposition (CODE_FIX | DOC_FIX).

## Normative requirements

- **CL-C41** MUST NOT: Stack traces are filtered from anonymous callers; /telemetry requires a token (C-4.1).
- **CL-I5** MUST NOT: The control plane embeds a user interface (zero-UI, I-5).
- **CL-I61** MUST NOT: The control plane invokes generative LLMs (zero-LLM, I-6.1/ADR-016).
- **CL-I62** MUST: A provider with a dimension greater than the basis is rejected or handled explicitly without breaking projections (I-6.2/L6).
- **CL-R1** MUST: The README quickstart boots via traianus-bootstrap (packaged script) (R-1/M4).
- **CL-R2** MUST: The README quickstart documents uvicorn traianus.app:app --host 127.0.0.1 (R-2/M4).
- **CL-WP1** MUST NOT: The packages traianus.{core.basis,tda,metrics,replication} exist (WP exclusion in the PoC).
- **CL-TR1** MUST: The doc → SPEC → test chain has no gaps: every ACTIVE claim has a test and every test references its SPEC (full traceability).
- **CL-LIT1** MUST: Topological_Grounding quotes exist character for character in the cited source file (AGENTS.md §2.4).
