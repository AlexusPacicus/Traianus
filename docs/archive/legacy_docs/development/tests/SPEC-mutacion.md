# SPEC — MUTATION Block

> Normative (RFC 2119). ADR-015 (dimensional expansion), H4 (append-only).

## Scope

Logographic genesis `/mutate/{new_symbol}`: N→N+1 expansion with canonical
orthogonal vector injection (ADR-015).

## Normative requirements

- **MU-01** MUST: /mutate/{symbol} expands the dimension N→N+1, injects the canonical axis [0,...,1] and refills the nodes with a new revision (ADR-015/H4).
- **MU-02** MUST: The registry of generics applicable to the block matches the SPEC (endpoint_registry).
- **MU-03** MUST: The block endpoints respond without 5xx or 401 with a valid token.
- **MU-04** MUST: The mutation E2E journey with a real model completes offline (Phase 6, @pytest.mark.model).
