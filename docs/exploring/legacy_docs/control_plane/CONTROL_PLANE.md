# Spatial Control Plane

## 1. Spectral Variance Circuit Breaker

The Circuit Breaker computes $L_2$-normalized orthogonal scalar projections of input vectors onto active geodetic axes $B_n$, then evaluates the mass variance $\sigma^2$ against the critical dynamic threshold $\sigma^2_{\text{dynamic}}$.

### Threshold Calibration (C1 Fix)

`auto_calibrate_critical_threshold()` computes the baseline variance from **cross-projections only** (excluding self-projection). For an $L_2$-normalized axis, the projection onto itself is exactly `1.0`, which inflates the baseline variance by ~16× and makes the Topological Key unreachable for real inputs. The fix excludes self-projection (`j != i`), producing a threshold the input scale can actually cross.

### Routing Logic

| Condition | Result |
| :--- | :--- |
| $\sigma^2 \geq \sigma^2_{\text{dynamic}}$ AND `revision_milestone = 1` | Transition to `'consolidated'` |
| $\sigma^2 < \sigma^2_{\text{dynamic}}$ | Transition to `'incubating'` (full multichannel spectrum preserved in `projections_json`) |

### Action Potential

`action_potential = float(variance)` — the raw variance without the magic `*10.0` constant (ADR-005).

## 2. Dual-Key Consolidation (ADR-022)

State transition to `'consolidated'` requires two concurrent validations:

### Topological Key (Algebraic)

Spatial variance. Projection mass variance must satisfy the dynamic threshold: $\sigma^2 \geq \sigma^2_{\text{dynamic}}$.

### Ethical Key (HITL)

Explicit operator intervention: `revision_milestone = 1`.

### Quarantine Enforcement

If an entity satisfies only one key, the substrate retains it in quarantine (`lifecycle_state = 'incubating'`), preventing both unvalidated mathematical drift and operator mutation. Neither key holds unilateral authority to consolidate state.

## 3. Orthogonalization & Basis Accretion (N → N+1)

The Basis Engine performs dynamic axis calculation and space accretion via greedy farthest-point projection (ADR-017). New axes are injected as pure canonical unit vectors ([0,0,...,1]), guaranteeing mathematical orthogonality with existing axes.

### Geodesic Axes Mutation (ADR-026 Decision B)

`geodesic_axes` is a derived artifact, not a versioned log. It is computed deterministically at boot (`INSERT OR IGNORE`, no in-place update of history). The single `UPDATE geodesic_axes SET vector_blob = ...` in `logographic_genesis` (hyperspace expansion) is a cache/derivation refresh of the regenerable basis, NOT a mutation of observed state history. Invariant #1 (ADR-025) applies to vertices, deterministic edges, and simplicial faces, not to this derived baseline.

## 4. Ingress Customs Gate (DUA)

The Ingress Customs Gate is a synchronous Zero-Trust firewall that validates payload integrity prior to coordinate processing.

- **Type Allowlist:** Only `text/plain` is accepted. All other MIME types receive HTTP 415.
- **Audio Rejection:** `audio/ogg` and `audio/m4a` are rejected at the perimeter.
- **Silent Denial (ADR-002):** Validation failures suppress stack traces from external callers. Failures are logged as internal telemetry nodes under `lifecycle_state = 'telemetry_error'`.

## 5. References

- ADR-022: Dual Interaction Loop and Dual-Key Consolidation
- ADR-017: Dynamic Geodetic Axes Derived from Corpus Variance
- ADR-015: Space Accretion via Orthogonal Canonical Injection
- ADR-001: Separation of Planes
- ADR-002: Silent Denial and Internal Telemetry
- ADR-026: Edge History Append-Only and the Geodesic Basis as Derived Artifact
- TRAIANUS_AUDIT.md: Finding C1 (threshold scale mismatch)