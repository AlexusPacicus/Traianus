# 🏛️ Traianus

Open-source deterministic computational substrate for autonomous spatial state governance.
Preserving state continuity and structural routing through deterministic operations, independently of representation models.

> **"Traianus does not define how reality is represented. It operates upon coordinate vectors $\mathbf{v} \in \mathbb{R}^d$ emitted by external representation providers to govern spatial state deterministically."**

Traianus is an offline-first, open-source Deterministic Computational Substrate for Autonomous Spatial State Governance investigating whether spatial state continuity can be maintained as an independent computational layer, fully decoupled from both external representation providers and observation layers.

The current Proof of Concept (PoC) uses sovereign personal knowledge strictly as its initial reference application (RefApp-01).

---

## The 3-Tier Architectural Model

Traianus strictly enforces a three-tier separation of concerns, where each tier answers a fundamentally distinct question:

```text
1. Representation Layer
   Question: "How is a world entity mapped into coordinates v ∈ ℝᵈ?"
   Providers: 
     • Neural embedding models (Text, Multimodal)
     • Sparse lexical encoders (BM25, TF-IDF, SPLADE)
     • Symbolic & logical encoders (OWL, RDF, Graph Kernels)
     • Computer vision encoders (ViT, CLIP Vision, SAM)
     • Audio & acoustic encoders (Whisper, Wav2Vec, Spectrograms)
     • Physical sensor pipelines (LiDAR, IMU, GPS, Radar, Biomedical)
     • Time-series & signal extractors (Fourier, Wavelets, PCA, IoT)
     • Scientific feature extractors (Molecular structures, DNA sequences)
        │
        ▼  (Coordinates v ∈ ℝᵈ)
        │
2. Spatial Control Plane (Traianus Substrate)
   Question: "How is a deterministic spatial state Sn maintained and evolved?"
   Subsystems: Transactional state persistence, dynamic variance thresholding, L₂ geometry, space accretion.
        │
        ▲  ▼  (Dual Interaction Loop: Read Projections ◄► External HITL Feedback)
        │
3. Observation Layer (Ulpia Mathematical Framework / RefApps)
   Question: "How is that spatial state observed, and how does external interaction drive space continuity?"
   Framework & Clients: Ulpia (Native Mathematical Observation Framework), RefApp-01 (Knowledge), RefApp-02 (Cybersecurity), RefApp-03 (Telemetry).
```
Representation Layer: Operates outside Traianus. External providers map entities into coordinate vectors $v \in \mathbb{R}^d$.
Spatial Control Plane: Executes deterministic state transitions $S_{n+1} = f(S_n, v_n)$ over the discrete simplicial complex $S_n = (V_n, E_n, K_n)$ purely through linear algebra and transactional persistence (ADR-023).
Observation Layer: Evaluates read-only perspective projections $O_n = P_\theta(S_n)$. Powered natively by Ulpia as the mathematical observation framework and consumed by domain reference applications. External interactions provide the human-in-the-loop (HITL) feedback necessary to satisfy the Ethical Key for state consolidation (ADR-022).

## 1. System Boundaries & Non-Goals
To position this infrastructure precisely within the systems landscape, Traianus is explicitly NOT:

Not a Large Language Model (LLM): Performs zero probabilistic text completion or token generation.

Not a Vector Database: Does not merely index static embeddings for top-k similarity retrieval; functions as an active spatial control plane.

Not a Graph Database: Avoids manual triple extraction (subject-predicate-object) or static rigid schemas.

Not an Execution Agent Framework: Executes no autonomous external tools, API calls, or unmonitored background actions.

Not a User Application or UI Framework: Traianus contains zero rendering, layout, or user interface code. External inspection layers (e.g., Ulpia / RefApps) act strictly as optional observation clients.

## 2. Decoupled Architecture & State Function
Given an external entity mapping $v \in \mathbb{R}^d$, the state transition function executes deterministically within the control plane:
$S_{n+1} = f(S_n, v_n)$
Where $S_n = (V_n, E_n, K_n)$ represents the discrete simplicial complex (vertices $V_n$, deterministic edges $E_n$, and simplicial faces $K_n$) at step n (ADR-023). External observation layers evaluate read-only perspective projections $O_n = P_\theta(S_n)$ without mutating state $S_n$  (ADR-024).

## 3. Scientific Hypotheses
Primary Hypothesis (RH-0): Traianus investigates whether deterministic computational state can be maintained independently of the mechanisms used to represent external reality.
RH-1 (Provider Agnosticism): The spatial control plane routes and governs spatial state without modifying or relying on internal representation provider weights or semantics.
RH-2 (Determinism & Auditability): Dynamic variance thresholding aims to guarantee reproducible execution paths ($S_{n+1} = f(S_n, v_n)$) bit for bit.
RH-3 (Local Edge Execution): Operates offline on consumer local hardware (≤8GB RAM) without requiring runtime cloud API connectivity.

## 4. Documentation Ledger

- **Project Identity** (`docs/identity/PROJECT_IDENTITY.md`): System boundaries, canonical definitions, non-goals, and official taxonomy.

- **Research Hypothesis** (`docs/research/RESEARCH_HYPOTHESIS.md`): Theoretical grounding in Conceptual Spaces (Gärdenfors, 2000) and provider agnosticism corollaries.

- **Research Programme** (`docs/research/RESEARCH_PROGRAM.md`): R&D roadmap, WP1–WP4 specifications, deliverables, and risk matrix.

- **Project Architecture** (`docs/arquitecture/Project_arquitecture.md`): Mathematical state machine formulation $S_n = (V_n, E_n, K_n)$ and transactional persistence layer.

- **ADR Ledger** (`docs/arquitecture/ADR/ADR.md`): Immutable append-only log of architectural decision trade-offs (ADR-001 to ADR-025).

- **Data Contracts** (`docs/arquitecture/contracts/CONTRACTS_AND_PRISMS.md`): Pydantic schema specifications (RawDump, RefinedEntity) and Zero Trust ingress firewall.
