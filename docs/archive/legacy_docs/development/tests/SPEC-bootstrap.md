# SPEC — BOOTSTRAP Block

> Normative (RFC 2119). Findings: M3 (offline), L4 (NSM inventory), Pydantic
> contracts (L5).

## Scope

Vector utilities, data contracts (RawDump, RefinedEntity) and the encoder
offline guard (app + bootstrap).

## Normative requirements

- **BO-01** MUST: Vector serialization is an exact roundtrip (serialize_vector → frombuffer).
- **BO-02** MUST: RawDump validates the ingress contract (text, type).
- **BO-03** MUST: RefinedEntity rejects an invalid lifecycle_state with ValidationError.
- **BO-04** MUST: The app encoder is built with local_files_only=True and HF_HUB_OFFLINE=1 (M3).
- **BO-05** MUST: The bootstrap encoder is built with local_files_only=True and HF_HUB_OFFLINE=1 (M3).
- **BO-06** MUST: The registry of generics applicable to the block matches the SPEC (endpoint_registry).
- **BO-07** MUST: The bootstrap block exposes no HTTP endpoints.
- **BO-08** MUST: The bootstrap E2E journey with a real model completes offline (Phase 6, @pytest.mark.model).
