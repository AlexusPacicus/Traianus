# Data Contracts & Zero-Trust Ingress Customs

## 1. Purpose & Zero-Trust Ingress Principle
This document specifies the validation boundaries, byte-level security filters, and Pydantic v2 data contracts governing Traianus' ingress perimeter (`traianus/security/`).

**Live Document Delegations:**
* For system identity, operational boundaries, and Non-Goals, see [../../PROJECT_IDENTITY.md](../../PROJECT_IDENTITY.md).
* For discrete state machine formulation and SQLite WAL persistence, see [../ARCHITECTURE.md](../ARCHITECTURE.md).
* For empirical validation and ledger records, see [../../specifications/EAS-01_LOGOGRAPHIC_PHYSICS.md](../../specifications/EAS-01_LOGOGRAPHIC_PHYSICS.md) and [../../LEDGER.md](../../LEDGER.md).

---

## 2. Zero-Trust Perimeter Rules (Byte-Level Validation)

Before any payload is processed by representation providers (`traianus/representation/`) or passed to the geometry/governance kernels (`traianus/geometry/`, `traianus/governance/gate.py`), it must clear the synchronous Zero-Trust validation gate in `traianus/security/validator.py`:

1. **Null-Byte Rejection (`\x00`):** Any raw payload containing null bytes is immediately rejected at the byte layer to prevent memory corruption and string truncation attacks.
2. **UTF-8 Decoding Validation:** Strictly verifies valid UTF-8 character encoding; malformed byte sequences trigger an immediate perimeter fault.
3. **Buffer Length Cap:** Enforces hard limits on input string byte size to protect local execution from memory exhaustion and DoS vector injection.

---

## 3. Pydantic v2 Contract Specifications

Data validation is structured into a two-tier contract architecture:

### 3.1 External Ingress Contract (`RawDump`)
Exposed at the `/ingesta` perimeter endpoint. Validates incoming raw HTTP payloads before invoking external coordinate encoders.

```python
from pydantic import BaseModel, Field

class RawDump(BaseModel):
    text: str = Field(
        ..., 
        description="Raw external entity payload content in plain text."
    )
    type: str = Field(
        default="text/plain", 
        description="MIME payload type. Non-plain text payloads are rejected at perimeter."
    )
```

### 3.2 Internal Control Plane Refinement Contract (`RefinedEntity`)
Constructed internally within `traianus/security/schemas/` after coordinate projection and variance evaluation. Enforces structural completeness prior to persistent storage.

```python
from pydantic import BaseModel, Field
from typing import List

class RefinedEntity(BaseModel):
    text: str = Field(
        ..., 
        description="Structured entity payload content in plain text."
    )
    lifecycle_state: str = Field(
        ..., 
        description="State attribute: 'pending_approval', 'consolidated', 'incubating', or 'telemetry_error'."
    )
    revision_milestone: bool = Field(
        default=False, 
        description="TRUE only when validated by explicit external/human interaction (Ethical Key)."
    )
    projections: List[float] = Field(
        ..., 
        description="Full multi-axis projection spectrum array p = [p_1, ..., p_k]."
    )
```

---

## 4. Silent Denial & Internal Telemetry (ADR-002)

**External Behavior:** Upon validation failure or payload corruption, technical stack traces are suppressed toward external callers to prevent interface lockups and information leakage.

**Telemetry Persistence:** Validation faults are logged atomically in SQLite as an internal telemetry node under `lifecycle_state = 'telemetry_error'`, granting local observability over pipeline faults without compromising perimeter security.

---

## 5. Execution Guarantees

| Rule | Claim | Mechanism | Boundary |
| :--- | :--- | :--- | :--- |
| **Byte Isolation** | Rejects malformed bytes at perimeter. | Null-byte and UTF-8 verification in `traianus/security/validator.py`. | Byte-level firewall prior to vector projection. |
| **MIME Filtering** | Filters non-text payloads. | `RawDump` validates `type == 'text/plain'` at ingress. | Rejects non-text media at HTTP entry point. |
| **Silent Denial** | Suppresses stack traces to callers. | Catches ingress exceptions and logs `telemetry_error` node (ADR-002). | Prevents internal information leakage. |
