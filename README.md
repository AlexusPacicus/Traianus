# Traianus

An offline-first, open-source computational substrate that governs spatial state deterministically over coordinate vectors — independently of how those vectors are produced.

Every system that manages knowledge inherits a hidden coupling: the way it *represents* concepts is fused with the way it *stores and evolves* them. Change the representation (swap an embedding model for a symbolic encoder, or a vision pipeline for a text extractor), and the stored state breaks. Traianus cuts this knot by introducing a **spatial control plane** — a deterministic state machine that operates purely on coordinate vectors $\mathbf{v} \in \mathbb{R}^d$, without caring how those vectors are produced.

This separation makes three promises possible:
- **Provider agnosticism** — swap representation providers without disrupting state
- **Deterministic auditability** — every state transition $S_{n+1} = f(S_n, v_n)$ is reproducible given identical input vectors
- **Offline sovereignty** — the entire substrate runs on consumer local hardware ($\le 8$ GB RAM) with no runtime cloud dependency

Current status: Proof of Concept (PoC) v1.0 using sovereign personal knowledge as its initial reference application (RefApp-01). See [IMPLEMENTATION_STATUS.md](./IMPLEMENTATION_STATUS.md) for the transparent declaration of what is implemented vs. what is R&D roadmap.

> **"Traianus does not define how reality is represented. It operates upon coordinate vectors $\mathbf{v} \in \mathbb{R}^d$ emitted by external providers to govern spatial state deterministically."**

## 1. System Boundaries & Non-Goals

To position this infrastructure precisely within the systems landscape, Traianus is explicitly NOT:

* **Not a Large Language Model (LLM):** Performs zero probabilistic text completion or token generation.

* **Not a Vector Database:** Does not merely index static embeddings for top-k similarity retrieval; functions as an active spatial control plane.

* **Not a Graph Database:** Avoids manual triple extraction (subject-predicate-object) or static rigid schemas.

* **Not an Execution Agent Framework:** Executes no autonomous external tools, API calls, or unmonitored background actions.

* **Not a User Application or UI Framework:** Contains zero rendering, layout, or user interface code. External inspection layers (Ulpia / RefApps) act strictly as optional observation clients.

## 2. The 3-Tier Architectural Model

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
* **Representation Layer:** Operates outside Traianus. External providers map entities into coordinate vectors $v \in \mathbb{R}^d$.
* **Spatial Control Plane:** Executes deterministic state transitions $S_{n+1} = f(S_n, v_n)$ over the discrete simplicial complex $S_n = (V_n, E_n, K_n)$ purely through linear algebra and transactional persistence (ADR-023). The executable PoC v1.0 in `traianus/` currently operates over the skeleton $S_n = (V_n, E_n)$, with a sub-millisecond projection kernel (0.01ms kernel / ~13ms total pipeline including neural embedding).
* **Observation Layer:** Evaluates read-only perspective projections $O_n = P_\theta(S_n)$. Powered natively by Ulpia as the mathematical observation framework and consumed by domain reference applications. External interactions provide the human-in-the-loop (HITL) feedback necessary to satisfy the Ethical Key for state consolidation (ADR-022).

## 3. Decoupled Architecture & State Function

Given an external entity mapping $v \in \mathbb{R}^d$, the state transition function executes deterministically within the control plane:

$$S_{n+1} = f(S_n, v_n)$$

Where $S_n = (V_n, E_n, K_n)$ represents the discrete simplicial complex at step $n$:

* $V_n$ — Vertices (coordinate vectors)
* $E_n$ — Deterministic edges (adjacency relations)
* $K_n$ — Simplicial faces (higher-order structures)

> **Note:** *Higher-order simplicial faces (K_n) and multi-provider dynamic switching form part of the active R&D roadmap in `docs/research/`.* The executable PoC v1.0 of `traianus/` governs the lower-dimensional skeleton $S_n = (V_n, E_n)$; higher-order structures $K_n$ are not executed by the current release.

External observation layers evaluate read-only perspective projections $O_n = P_\theta(S_n)$ without mutating state $S_n$ (ADR-024).

## 4. Scientific Hypotheses

* **RH-0 (Primary Hypothesis):** Traianus investigates whether deterministic computational state can be maintained independently of the mechanisms used to represent external reality.

* **RH-1 (Provider Agnosticism):** The spatial control plane routes and governs spatial state without modifying or relying on internal representation provider weights or semantics.

* **RH-2 (Determinism & Auditability):** Dynamic variance thresholding aims to guarantee reproducible execution paths ($S_{n+1} = f(S_n, v_n)$) given identical inputs.

* **RH-3 (Local Edge Execution):** Operates offline on consumer local hardware ($\le 8$ GB RAM) without requiring runtime cloud API connectivity.

## 5. Quickstart

### Prerequisites

* **Nix** with flakes enabled (see [nixos.wiki/wiki/Flakes](https://nixos.wiki/wiki/Flakes))
* **SQLite** (bundled automatically in the Nix shell)

### Running

```bash
# Enter the development shell (installs all dependencies)
nix develop

# 1. Bootstrap the geodetic baseline (offline, all-MiniLM-L6-v2 cached)
traianus-bootstrap

# 2. Run the test suite (hermetic partition, no model required)
pytest tests/ -m "not model"
```

### Without Nix

Ensure Python 3.11+ and the dependencies listed in `pyproject.toml` are installed, then run:

```bash
pip install -e .
traianus-bootstrap
pytest tests/ -m "not model"
```

### Start the control plane locally

The FastAPI server binds only to the local loopback (Zero-Trust, no external network):

```bash
uvicorn traianus.app:app --host 127.0.0.1 --port 8000
```

## 6. Documentation Ledger

* **Project Identity** (`docs/identity/PROJECT_IDENTITY.md`): System boundaries, canonical definitions, non-goals, and official taxonomy.

* **Research Hypothesis** (`docs/research/RESEARCH_HYPOTHESIS.md`): Theoretical grounding in Conceptual Spaces (Gärdenfors, 2000) and provider agnosticism corollaries.

* **Research Programme** (`docs/research/RESEARCH_PROGRAM.md`): R&D roadmap, WP1-WP4 specifications, deliverables, and risk matrix.

* **Project Architecture** (`docs/architecture/Project_architecture.md`): Mathematical state machine formulation $S_n = (V_n, E_n, K_n)$ and transactional persistence layer.

* **ADR Ledger** (`docs/architecture/ADR/ADR.md`): Immutable append-only log of architectural decision trade-offs (ADR-001 to ADR-025).

* **Data Contracts** (`docs/architecture/contracts/CONTRACTS_AND_PRISMS.md`): Pydantic schema specifications (RawDump, RefinedEntity) and Zero Trust ingress firewall.

## License

GPL-3.0-or-later. See `pyproject.toml` and `LICENSE` for the full license declaration.
