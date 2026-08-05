# MASTER WORKING NOTE: Conceptual and Architectural Consolidation (Traianus)

Master Working Document. Collects the ontological decisions, the canonical taxonomy, the substrate boundaries and the agreed writing rules.

## 1. Canonical Identity and Core Term
Traianus Definition: Replace "semantic organization engine" with Deterministic Computational Substrate for Autonomous Spatial State Governance.
Canonical Component Term: Officially adopt Spatial Control Plane (or Deterministic Spatial Control Plane).
Terminology Dosage Rule:
Introduce the full term in the title or first paragraph.
In continuous prose, alternate with: the control plane, the computational substrate, the execution layer or the substrate to avoid buzzword saturation.

## 2. Ontological Postulate of the Substrate
Traianus is strictly positioned after a valid mathematical representation exists ($v \in \mathbb{R}^d$).
Ontological Position Postulate:
"Traianus does not represent reality, nor does it construct representations of reality. It preserves state continuity for externally generated representations within a deterministic geometric computational substrate."
Ontological Consequences:
Content Agnosticism: For the substrate, all vectors are equivalent: a text embedding, a LiDAR reading, a computer vision descriptor, a biomedical signal or a robot's state are simply coordinate vectors over which deterministic rules are applied.
Independence from Reality: reality does not belong to Traianus; neither does the representation; neither does the observation.

## 3. 3-Layer Architectural Model and Dual Loop

```text
1. Representation Layer
   Question: "How is a world entity mapped into coordinates v ∈ ℝᵈ?"
   Providers: Neural embeddings, BM25/Sparse, symbolic encoders, vision, audio, LiDAR/IMU, time-series.
        │
        ▼  (Coordinates v ∈ ℝᵈ)
        │
2. Spatial Control Plane (Traianus Substrate)
   Question: "How is a deterministic spatial state Sn maintained and evolved?"
   Mechanisms: Linear algebra, dynamic variance thresholding, transactional state persistence.
        │
        ▲  ▼  (Dual Interaction Loop: Read Projections ◄► External HITL Feedback)
        │
3. Observation & Interaction Layer (RefApps / Observation Clients)
   Question: "How is that spatial state observed, and how does external interaction drive space continuity?"
    Clients: RefApp-01 (Knowledge), RefApp-02 (Cybersecurity), RefApp-03 (Telemetry), Ulpia.
```

### Layer Principles

**Level 1 (Representation):**
"Traianus does not define how reality is represented. It assumes only that an external representation provider can map an entity into a mathematical state suitable for deterministic spatial governance."

**Level 2 (Substrate):** Governs the state $S_n = (B_n, N_n, E_n)$ through three mechanisms: linear algebra, dynamic variance threshold and transactional state persistence.

**Level 3 (Observation and Dual Interaction):**
"Observation layers evaluate perspective projections of state $O_n = P_\theta(S_n)$. External interactions within these layers provide the human-in-the-loop (HITL) feedback necessary to satisfy the Ethical Key, driving state continuity and consolidation ($S_n \to S_{n+1}$) within the control plane."

## 4. Substitution Dictionary (Fossil Purge)
To remove any trace of ambiguity or "notes app / NLP" bias:
| Obsolete Term / "Fossil" | New Canonical Term | Technical Justification |
| :--- | :--- | :--- |
| PKM / Personal Knowledge App | RefApp-01 (Sovereign Personal Knowledge) | It is the first reference application, not the limit of the software. |
| Semantic Organization | State Continuity / Spatial State Governance | Traianus does not "organize semantics"; it maintains continuity of vector states. |
| Semantic Representation | Entity / Mathematical Representation | Traianus operates on the mathematical representation of reality in general. |
| Ulpia (Frontend / UI) | Ulpia (Mathematical Observation Layer) | Independent research program of observation theory. |
| Visualize / Display / UI | Project / Observe / Inspect | Zero UI or rendering code in the Traianus core. |
| Model Agnosticism | Provider Agnosticism | Covers both neural models and physical sensors, audio or symbolic encoders. |
| Organizes representations | Preserves state continuity | Traianus does not "organize"; it executes deterministic state transitions ($S_{n+1} = f(S_n, v_n)$). |

## 5. Redefinition of the Research Hypotheses
We substitute the linguistic formulation with a purely infrastructure thesis:
Primary Research Hypothesis (RH):
"Traianus investigates whether deterministic computational state can be maintained independently of the mechanisms used to represent external reality."
RH-1 (Provider Agnosticism): The control plane routes and governs states without modifying or depending on the weights or semantics of the representation provider.
RH-2 (Determinism & Auditability): Dynamic variance threshold filtering guarantees 100% reproducible execution paths ($S_{n+1} = f(S_n, v_n)$).
RH-3 (Local-First Sovereignty): Operates fully offline in a local architecture without requiring cloud API calls at runtime.

## 6. Implementation Vocabulary Aisle and Invariants
Technological Isolation Rule:
Forbidden: Naming libraries, databases or frameworks (SQLite WAL, FastAPI, Pydantic, worker queues, all-MiniLM-L6-v2) in the Identity, Hypothesis or Philosophy documents.
Allowed: Only and exclusively in the PoC Status Table (README Section 4) under the "PoC Technical Implementation" column and in installation scripts (flake.nix).
Fundamental System Invariants (PROJECT_IDENTITY.md §5):
Provider Agnosticism: Consumes normalized vectors $v \in \mathbb{R}^d$ without modifying or altering the weights of the external provider.
Deterministic State Execution: State transitions governed strictly by linear algebra and dynamic variance threshold, without probabilistic token generation or LLM execution in the substrate.
Local Runtime Sovereignty: 100% local and offline execution and persistence.

## 7. Multi-Provider Benchmarking Matrix
To test RH-1 (Provider Agnosticism) and demonstrate how Traianus filters the probabilistic residual of neural networks, the R&D program (RESEARCH_PROGRAM.md) will include comparative benchmarks over 4 input families:
| Input Family | Provider Examples | Vector Type ($v \in \mathbb{R}^d$) | Benchmark Property and Purpose |
| :--- | :--- | :--- | :--- |
| **1. Neural (Latent)** | Sentence-Transformers, E5, CLIP | Dense, continuous ($d \approx 384-1536$) | Evaluates isolation of anisotropy and training noise. |
| **2. Lexical / Statistical** | BM25, TF-IDF, SPLADE | Sparse, discrete ($d = \|V\| \approx 50,000$) | 100% deterministic frequency baseline; validates sparse geometry without latent noise. |
| **3. Symbolic / Logical** | Graph Kernels (Weisfeiler-Lehman), OWL Ontologies | Discrete, structured | Validates pure topological states without statistical approximation. |
| **4. Direct Physical Signal** | Fourier/Wavelet Transforms, LiDAR, IMU, ECG | Dense/Sparse (per sensor) | Validates direct applicability in robotics, IoT and industrial telemetry. |

## 8. Document Ledger Reorganization
Dissolve CORE_THESIS.md and integrate the Dual Consolidation Key (Ethical/HITL Key + Topological Key) into Project_architecture.md. The canonical ledger is maintained in 7 essential documents:
README.md: Entry point, 3-layer architecture, Why Traianus?, PoC table.
PROJECT_IDENTITY.md: 4-level taxonomy, ontological postulate, non-goals and invariants.
RESEARCH_HYPOTHESIS.md: Scientific pre-print, Conceptual Spaces theory (Gärdenfors) and corollaries RH-1 to RH-3.
Project_architecture.md: Formulation of the state machine $S_n = (B_n, N_n, E_n)$, transactional persistence and the Dual Key.
CONTRACTS_AND_PRISMS.md: Pydantic schemas (RawDump, RefinedIdeaTOON) and Zero-Trust Customs.
ADR.md: Immutable decision record (ADR-001 to ADR-020).
RESEARCH_PROGRAM.md: R&D roadmap (WP1–WP4) and risk matrix for the funding proposal.
