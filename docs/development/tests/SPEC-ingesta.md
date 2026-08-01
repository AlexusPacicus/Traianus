# SPEC — INGESTA Block

> Normative (RFC 2119). Findings: H1 (no-false-200), H2 (MIME firewall),
> M6 (metric without magic), ADR-002 (dual channel/telemetry).

## Scope

Ingress perimeter `/ingesta`, asynchronous spectral pipeline
(async_spectral_processor) and the RawDump contract.

## Normative requirements

- **IN-01** MUST: POST /ingesta with text/plain returns 200 with status "accepted" and an integer ingestion_id.
- **IN-02** MUST NOT: /ingesta accepts a MIME other than text/plain; it responds 415 (allowlist firewall, H2).
- **IN-03** MUST NOT: /ingesta accepts application/json at the perimeter; it responds 415 (H2 regression).
- **IN-04** MUST: A persistence failure in /ingesta responds 503 with "Ingress persistence unavailable" (H1).
- **IN-05** MUST: The spectral pipeline creates a pending_approval node with an L2 vector of 384 dims and 8 projections (ADR-002).
- **IN-06** MUST: A pipeline failure records a telemetry_error node with the trace (ADR-002, dual channel).
- **IN-07** MUST NOT: Axis keys with a double underscore collapse the projection spectrum (parsing regression).
- **IN-08** MUST: action_potential is the variance of the projections, without a magic ×10 constant (M6).
- **IN-09** MUST: The registry of generics applicable to the block matches the SPEC (endpoint_registry).
- **IN-10** MUST: The block endpoints respond without 5xx or 401 when they receive a valid token.
- **IN-11** MUST: The ingestion E2E journey with a real model completes offline (Phase 6, @pytest.mark.model).
