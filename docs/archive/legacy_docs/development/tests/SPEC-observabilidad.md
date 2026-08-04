# SPEC — OBSERVABILITY Block

> Normative (RFC 2119). Findings: H3 (CORS/token), M5 (real 5xx, protected
> telemetry), ADR-025#2 (observation does not mutate).

## Scope

Manifold reading (`GET /nodos`), telemetry (`GET /telemetry`) and the global
CORS policy.

## Normative requirements

- **OB-01** MUST NOT: The CORS policy uses the "*" wildcard; origins are enumerated (H3).
- **OB-02** MUST: Routes that mutate state or expose telemetry require a token; without it they respond 401 (H3).
- **OB-03** MUST: With a valid token, the protected routes do not respond 401.
- **OB-04** MUST: GET /nodos excludes telemetry_error and returns only MAX(seq) per id (M5/ADR-025#2).
- **OB-05** MUST NOT: /nodos returns an empty SUCCESS on a database error; it responds with a real 5xx (M5).
- **OB-06** MUST: /telemetry requires the operator token and exposes traces only to authorized operators (M5).
- **OB-07** MUST: The registry of generics applicable to the block matches the SPEC (endpoint_registry).
- **OB-08** MUST: The block endpoints respond without 5xx (nodos without token by design; telemetry with token).
- **OB-09** MUST: The observability E2E journey with a real model completes offline (Phase 6, @pytest.mark.model).
