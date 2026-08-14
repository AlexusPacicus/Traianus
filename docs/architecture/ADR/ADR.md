# Architectural Decision Records (ADR Ledger)

Objective: Document immutable engineering trade-offs to prevent emotional refactoring, architectural drift, or scope creep.

Philosophy: Append-Only. Architectural decisions are stacked sequentially to preserve structural traceability.

Historical Context & Evolutionary Trajectory:
The early entries (ADR-001 through ADR-007) capture rapid prototyping for a deterministic knowledge organizer during a hackathon. To eliminate data randomness and system drift, architectural focus shifted from application features to core state persistence. Subsequent entries (ADR-010 through ADR-025) record this evolution into a foundational, immutable control plane.
Note on Ledger Sequence: Discontinued numbers (006, 008, 009, 011–013) represent internal exploration drafts and interface trade-offs from the initial hackathon phase that were merged or discarded prior to substrate consolidation.

---

## Amendment — Superseding Amendment v0.1 (SPEC-REFACTOR-v0.2 §1.4)

**Status:** Approved (prevails over ADR-017, ADR-022, ADR-023, ADR-007)

> This amendment is append-only: it prevails over the decisions below without erasing their historical traceability.

1. **Substitution of ADR-017 (Geodesic Axes):** the 8 geodesic axes do not represent "quality dimensions of the human mind (Gärdenfors)". They are relabeled `PROSTHETIC_NSM_V1`: a provisional 384D bootstrap basis, disposable at WP1.
2. **Substitution of ADR-022 (Dual-Key Gate C1):** the Topological Key (σ²) is not an "infallible algorithmic judge"; it is defined as a **Provisional Informational Geometric Score**. **The dual gate is preserved in v0.1: consolidation requires the simultaneous satisfaction of the Topological Key (σ² ≥ θ_dyn) AND the Ethical Key (HITL). Neither acts alone.** The score is reported as `PROVISIONAL_INFORMATIONAL_SCORE` but remains a necessary condition alongside human approval.
3. **Substitution of ADR-023 (Local Adjacency E_n):** ε = 0.8 adjacency is declared a purely observational artifact for `/relations` (L2 distance). It does not govern runtime state transitions in v0.1.
4. **Annulment of ADR-007:** the theoretical justification about glyph processing inside transformers (ADR-007, mislabeled "ADR-I5" in the v0.1 draft) is dismissed — it does not correspond to the actual `text/plain` flow of the substrate.

---

## Index of Architectural Decisions

### ADR-001: Separation of Planes (Control Plane vs. External Payloads)
* **Context:** Raw entity payloads processed by external representation providers introduce structural unpredictability if granted routing authority over execution flows.
* **Decision:** Enforce decoupling between the Spatial Control Plane (strongly-typed linear algebra and state execution) and the Data Ingress Layer. Once coordinate vectors $v \in \mathbb{R}^d$ are ingested, external entity payloads lose execution authority within the substrate.
* **Status:** Approved / Active.

### ADR-002: Silent Denial and Internal Telemetry (Refactored for Operator Observability)
* **Context:** Schema validation failures or out-of-boundary parameters can inject error traces back into the caller, exposing system internals or freezing user interfaces.
* **Decision:** Implement dual-channel Silent Denial. External HTTP callers receive a synthetic success response (200 OK) to prevent client lockups. Concurrently, any structural drift or validation failure is atomically persisted to manifold_nodes as an internal telemetry node under lifecycle_state = 'telemetry_error', granting local forensic sovereignty to the operator.
* **Status:** Approved / Active.

### ADR-003: Dual Ingress Layer (Payload-First + Local Web Speech API)
* **Context:** Restricting perimeter ingestion exclusively to typed text minimizes friction, but may limit low-energy input states.
* **Decision:** Implement a text/payload-first interface with an optional toggle for native browser-based Web Speech transcription. Raw audio files are rejected at server ingress (RawDump), keeping all speech-to-text transcription on local client hardware.
* **Status:** Approved / Active.

### ADR-004: Client-Side Persistence Mirroring (IndexedDB)
* **Context:** Direct synchronous disk writes on every client interaction introduce I/O blocking bottlenecks in observation clients.
* **Decision:** Maintain a local IndexedDB instance on the client acting as an optimistic mirror of the backend storage layout.
* **Status:** Approved / Active.

### ADR-005: Vector Variance Routing Over Heuristics
* **Context:** Boolean decision rules with manually injected magic numbers introduce fragile heuristics that violate deterministic validation paradigms.
* **Decision:** State transitions are determined by computing the statistical variance ($\sigma^2$) of scalar projections (dot products) between the $L_2$-normalized input vector $\mathbf{v}$ and active geodetic axes $B_n$. The critical threshold auto-calibrates at boot by measuring intrinsic baseline space dispersion.
* **Status:** Approved / Active.

### ADR-007: Physical Symmetry and Single-Token Factor Integrity
* **Context:** Multi-character string factors or mean pooling over multi-token extractions introduce length bias and asymmetric attention weights within residual streams.
* **Decision:** Enforcement of 1-token physical symmetry. The toon_factor field in data contracts must consist of exactly 1 Unicode character (len == 1). Multi-character pseudo-tokens are destroyed at the Ingress Customs boundary.
* **Status:** Approved / Active.

### ADR-010: Native On-Premise Execution with Reference Edge Hardware Benchmark
* **Context:** Cloud extraction APIs violate data sovereignty, introduce network latency, and create vendor lock-in.
* **Decision:** All vector inference and control plane operations execute on local hardware. Baseline consumer edge hardware (≤8GB RAM) serves as the reference benchmark testbed environment for PoC validation, not as an architectural software limit.
* **Status:** Approved / Active.

### ADR-014: Spectral Approach Against Linear Compression Errors
* **Context:** Applying rigid max() functions over multi-axis projections hides semantic and geometric overlap across dimensions.
* **Decision:** Replace rigid multi-class categorization with a Spectral Approach. If entry variance falls below the dynamic threshold, the system preserves the complete multichannel analytical signature inside projections_json.
* **Status:** Approved / Active.

### ADR-015: Space Accretion via Orthogonal Canonical Injection
* **Context:** Adding new computational dimensions to static spaces yields noisy projections due to a lack of anchor points for emergent concepts.
* **Decision:** Hyperspace expansion (N→N+1) executes via hot-swapping computational linear algebra. The control plane zero-pads existing vectors and injects a pure canonical unit vector ([0,0,...,1]), preserving mathematical orthogonality by construction.
* **Status:** Approved / Active.

### ADR-016: Non-Generative Vector Inference
* **Context:** Running generative language models gagged by formal grammars to act as coordinate oracles consumes excessive resources and retains probabilistic risks.
* **Decision:** Deprecate generative LLMs in the control plane. Vector coordinates are obtained via non-generative local representation providers, shifting execution entirely to deterministic linear algebra.
* **Status:** Approved / Active.

### ADR-017: Dynamic Geodetic Axes Derived from Corpus Variance
* **Context:** Static geodetic axes anchored on Natural Semantic Metalanguage (NSM) primitives provide a safe initial bootstrap ($S_0$), but induce projection drift over time as domain complexity grows.
* **Decision:** Transition from fixed bootstrap primitives to dynamic geodetic axes extracted directly from corpus variance. Non-blocking background workers execute iterative min-max greedy farthest-point calculations over consolidated embeddings.
* **Status:** Proposed / Funded R&D Scope (WP1). PoC Boundary: Current PoC executes static NSM-anchored axes. Dynamic corpus-derived axis recalculation is deferred to WP1.

### ADR-018: Dynamic Dimension-k Discovery via Persistent Homology
* **Context:** Maintaining a fixed constant dimension k=8 inherited from bootstrap primitives acts as an arbitrary hyperparameter once initial corpus density is surpassed.
* **Decision:** Compute persistent homology over point-cloud coordinates. Topological persistence lifespans in Dimension 1 ($H_1$) determine the dynamic value of $k$.
* **Status:** Proposed / Funded R&D Scope (WP2). PoC Boundary: Current PoC fixes k=8. Dynamic k-discovery via H_{1} persistent homology is deferred to WP2.

### ADR-019: Native Integration of GUDHI C++ Library
* **Context:** Computing simplicial complexes and persistent homology in pure Python scales at O(N^{3}), creating latency bottlenecks on edge hardware.
* **Decision:** Integrate compiled GUDHI C++ bindings into traianus.tda to populate SimplexTree structures for zero-cloud topological data analysis.
* **Status:** Proposed / Funded R&D Scope (WP2). PoC Boundary: Python approximations used in PoC. Native C++ GUDHI integration is deferred to WP2.

### ADR-020: System Clock Eradication and Geodetic Metric Integration
* **Context:** Relational databases organize history via linear timestamps (t), introducing artificial continuity that fractures high-dimensional topological spaces.
* **Decision:** Disconnect the system clock from state retrieval and routing. Temporal movement is replaced by Riemannian geometry: displacement within the manifold is computed as a density metric tensor integral ($D_{\text{somatic}} = \int \sqrt{g_{ij} \, dx^i \, dx^j}$). Internal database timestamps (sys_internal_timestamp) function solely as low-level disk I/O indices and replication delta markers.
* **Status:** Active Core Principle in PoC / Full Metric Engine in Funded R&D Scope (WP3).

### ADR-021: Total Representation Provider Agnosticism
* **Context:** Tightly coupling a control plane to a specific neural model family risks state corruption and vendor lock-in when models are updated or recalibrated.
* **Decision:** The Spatial Control Plane operates exclusively on $L_2$-normalized coordinate vectors $v \in \mathbb{R}^d$. It ingests vectors from dense neural models, sparse lexical encoders (BM25), symbolic ontologies, or direct physical sensors without modifying or relying on external model weights.
* **Status:** Approved / Active Core Principle.

### ADR-022: Dual Interaction Loop and Dual-Key Consolidation
* **Context:** Unilateral state consolidation—whether driven by autonomous mathematical models or direct external client writes—violates control plane integrity and breaches state determinism.
* **Decision:** Enforce a Dual Interaction Loop governed by Dual-Key Concurrency:
  * **Perspective Projection (Outward):** External inspection layers evaluate read-only perspective projections $O_n = P_\theta(S_n)$ generated by the control plane, generating zero side effects on persistent storage.
  * **Dual-Key Consolidation (Inward):** State transition to the consolidated state ($S_n \to S_{n+1}$) requires the concurrent satisfaction of two orthogonal validation criteria:
    * **Topological Key (Algebraic Constraint):** Evaluated by the control plane. Scalar projection mass variance must satisfy the dynamic circuit-breaker threshold ($\sigma^2 \geq \sigma^2_{\text{dynamic}}$).
    * **Ethical Key (Sovereignty Constraint):** Injected via explicit Human-in-the-Loop (HITL) operator intervention (`revision_milestone = 1`).
  * **If an entity satisfies only one key,** the substrate retains it in quarantine (`lifecycle_state = 'incubating'`), preventing both unvalidated mathematical drift and operator mutation.
* **Invariants:**
  * **Key Symmetry:** Neither key possesses unilateral authority to consolidate state ($S_n \to S_{n+1}$).
  * **Quarantine Enforcement:** Partially validated entities remain structurally preserved in storage without executing topology accretion.
* **Status:** Approved / Active Core Principle.

### ADR-023: Computational Spatial State Substrate
* **Context:** Previous state descriptions introduced continuous density approximations or probabilistic similarity metrics. To preserve determinism, provider agnosticism, and low RAM overhead (≤8GB), the control plane defines state as a discrete spatial substrate.
* **Decision:** The computational state $S_n$ is represented as a finite simplicial complex:
  $$S_n = (V_n, E_n, K_n)$$
  * **Vertices ($V_n$):** $L_2$-normalized coordinate vectors in $\mathbb{R}^d$.
  * **Adjacency Relation ($E_n$):** $E_n \subseteq V_n \times V_n$ where $(v_i, v_j) \in E_n$ iff $d(v_i, v_j) \leq \epsilon$.
  * **Simplicial Faces ($K_n$):** Higher-order simplices formed by sets of mutually adjacent vertices.
  * Probabilistic density metrics and soft similarity weights are excluded from the state substrate.
* **Invariants:**
  * **Substrate Isolation:** The simplicial complex represents the computational state. It is neither the external phenomenon nor its observation.
  * **Boundary Separation:** Representation providers generate coordinates; observation layers inspect state. Traianus governs the intermediate deterministic substrate.
* **Status:** Approved / Active Core Principle.

### ADR-024: Projection Independence and Perspective Isolation
* **Context:** Coupling state evolution to observation mechanisms creates spatial distortion and violates state determinism.
* **Decision:** The computational state $S_n$ is invariant to observation. External inspection layers (e.g., Ulpia, RefApps) operate as read-only projections:
  $$O_n = P_\theta(S_n)$$
  where $\theta$ represents the perspective parameters of the observer. Mutating an observation perspective $P_\theta$ does not alter the underlying spatial state $S_n$. Transitions in $S_n$ occur through valid input vectors $v_n$ and dual-key consolidation (ADR-022).
* **Invariants:**
  * **Perspective Non-Interference:** Reading or projecting $S_n$ generates zero side effects on persistent storage.
  * **Local Impact Isolation:** Interactions performed over localized projections ($O_{\text{n,local}}$) generate vector mutations bounded by distance threshold $\epsilon$. State changes remain topologically confined to the affected neighborhood ($U \subset V_n$).
* **Status:** Approved / Active Core Principle.

### ADR-025: Non-Negotiable System State Invariants
* **Context:** System evolution across functional scopes (WP1–WP4) introduces risk of architectural drift. The control plane requires invariant rules preserved across optimizations, language bindings, or hardware targets.
* **Decision:** We establish five non-negotiable State Invariants:
  1. **Monotonic Append-Only Evolution:** State evolution $S_n \to S_{n+1}$ is append-only. Historical vertices, deterministic edges, and simplicial faces in persistent storage are immutable.
  2. **Zero Observation Mutagenicity:** Observation operators act as read-only functions ($O_n = P_\theta(S_n)$). Inspecting or projecting space generates zero side effects on $S_n$.
  3. **External Provider Isolation:** External representation providers function as coordinate generators ($v_n \in \mathbb{R}^d$). They possess zero topology execution rights.
  4. **Mandatory Control Plane Centrality:** Spatial transitions route through the Spatial Control Plane and satisfy Dual-Key Consolidation ($\text{Key}_{\text{Topological}} \land \text{Key}_{\text{Ethical}}$).
  5. **Bitwise State Determinism:** Given an identical initial state $S_0$ and an identical sequence of valid input vectors $V$, the resulting simplicial complex $S_n = (V_n, E_n, K_n)$ is bitwise identical across execution environments.
* **Testing Baseline:** Integration test suites must validate these five invariants on every build pipeline.
* **Scope Protection:** Protects the system against unmonitored external agency or unsafe concurrency patterns.
* **Status:** Approved / Active Core Principle.

### ADR-026: Edge History Append-Only and the Geodesic Basis as Derived Artifact
* **Context:** Invariant #1 (ADR-025) requires monotonic append-only evolution of persistent state. Residual H4 findings showed two historical patterns violating the invariant: `manifold_edges` was upserted in place (`ON CONFLICT(id) DO UPDATE`), and `geodesic_axes` was `UPDATE`d during hyperspace expansion. A full append-only migration of the geodetic basis (option A) was discarded on cost and coherence grounds: the basis is not observed state history.
* **Decision:**
  1. **Edge history becomes append-only (option B, closed).** `manifold_edges` uses the composite primary key `(id, seq)` mirroring `manifold_nodes`. Each forged transition INSERTS a new revision with increasing `seq`; current-state reads (`GET /relations`) expose `MAX(seq)` per logical edge id and exclude `state = 'removed'`. The prior `ON CONFLICT(id) DO UPDATE` upsert is PROHIBITED. Stale `auto-edge-*` rows are never deleted: they receive a tombstone revision `state = 'removed'` (append-only, H4), so the edge history retains every transition. Manual `edge-*` rows are preserved.
  2. **The geodetic basis is a derived artifact, not a versioned log (decision B).** `geodesic_axes` is computed deterministically at boot (`bootstrap.py:115-123`, `INSERT OR IGNORE`, no in-place update of history) and is therefore not versioned. The single `UPDATE geodesic_axes SET vector_blob = ... WHERE id = ?` in `logographic_genesis` (hyperspace expansion) is a cache/derivation refresh of the regenerable basis, NOT a mutation of observed state history; invariant #1 (ADR-025) applies to vertices, deterministic edges, and simplicial faces, not to this derived baseline.
* **Testing Baseline:** G5 (append-only) validates `manifold_nodes` and `manifold_edges` (including tombstone revisions); it does NOT prohibit the documented `geodesic_axes` regeneration.
* **Status:** Approved / Active Core Principle.

### ADR-027: Dual Boundary Pattern & Binary Verification Gate
* **Date:** 2026-08-03
* **Author / Responsible:** AlexusPacicus (I+D Marzo 2026 – Presente)
* **Context:** The Zero-Trust governance layer (AGENTS.md §2, AUDIT.md H3) blocks agents from embedding external network primitives (`fetch`, `axios`, `urllib`, `requests`, `httpx`, `socket`, `subprocess`, `curl`, `wget`, `aiohttp`, `importlib`, `os.system`, `os.popen`). Semantic, plain-text substring checks on proposals are evadable (encoding tricks, obfuscated import paths, symlink escapes) and cannot guarantee that a mutated target file remains inside the repository boundary.
* **Decision:** The validation gate operates on physical bytes, not on semantic lists:
  1. **Spatial Canonicalization (`Target_File`):** every target path is resolved with `Path.resolve(strict=True)` and MUST remain inside the repository root (`is_relative_to`). Symlink escapes and `..` traversal are rejected at the boundary (no follow).
  2. **Binary Subsequence Grounding:** literal grounding is verified as a UTF-8 subsequence over `read_bytes()` of the physical file, not via `in`-checks on a decoded string.
  3. **Null-Byte Sanitization:** raw `\x00` and JSON-escaped `\u0000` fragments are sanitized and rejected (`ABORTED_VIOLATES_ZERO_TRUST`).
  4. **Silent Denial:** rejected proposals return the gate decision without leaking the target path or OS details to the caller.
* **Invariants:**
  * **Physical Containment:** every mutation target is byte-canonicalized inside the repo root.
  * **Fail-Closed:** a non-UTF-8 binary file or an unresolvable path aborts the proposal; there is no fail-open branch.
* **Status:** Approved / Active.
