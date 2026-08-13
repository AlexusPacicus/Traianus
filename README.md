# Traianus

An offline-first, open-source computational substrate for deterministic spatial state governance over vector coordinate systems in $\mathbb{R}^d$.

Every system that manages knowledge inherits a hidden coupling: the way it *represents* concepts is fused with how state is maintained. Swap the representation, and historical state collapses. Traianus cuts this knot by introducing a **spatial control plane** — a deterministic state machine that operates purely on coordinate vectors $\mathbf{v} \in \mathbb{R}^d$.

This separation addresses the **Representation-State Coupling Problem** and guarantees three core properties:
- **Deterministic state engine** — spatial state transitions $S_{n+1} = f(S_n, \mathbf{v}_n)$ are governed deterministically over $L_2$-normalized coordinate vectors $\mathbf{v} \in \mathbb{R}^d$.
- **State reproducibility** — Given identical vector sequences, initial state, and execution semantics, the core state transition is deterministic.
- **Offline sovereignty** — hermetic execution offline: `HF_HUB_OFFLINE=1` + `local_files_only=True`, the entire substrate executes locally ($\le 8\text{ GB}$ RAM) with zero cloud runtime dependencies.

Current status: Proof of Concept (PoC) v1.0 using sovereign personal knowledge as its initial reference application (RefApp-01). See [IMPLEMENTATION_STATUS.md](./IMPLEMENTATION_STATUS.md) for current feature status versus the R&D roadmap.

> **"Traianus operates as an independent spatial control plane, governing state transitions deterministically over coordinate vectors $\mathbf{v} \in \mathbb{R}^d$."**

---

## 1. System Boundaries & Non-Goals

To position this infrastructure precisely within the systems landscape, Traianus is explicitly NOT:

* **Not a Large Language Model (LLM):** Performs zero probabilistic text completion, token generation, or prompt processing.
* **Not a Standard Vector Database:** Does not merely index static embeddings for top-k similarity retrieval; functions as an active spatial state controller.
* **Not a Graph Database:** Avoids manual triple extraction (subject-predicate-object) or static rigid schemas.
* **Not an Execution Agent Framework:** Executes zero autonomous external tools, network API calls, or unmonitored background tasks.
* **Not a User Interface Framework:** Contains zero rendering or layout code. External inspection layers operate strictly as optional observation clients.

---

## 2. The 3-Tier Architectural Model

Traianus enforces a strict three-tier separation of concerns:

```text
1. Representation Layer
   Question: "How is an entity mapped into coordinates v ∈ ℝᵈ?"
   Vectors:
     • Text embedding model — all-MiniLM-L6-v2 (384D float32, offline, pinned)
     • Physical telemetry & sensor modalities (roadmap scope)
        │
        ▼  (Coordinates v ∈ ℝᵈ)
        │
2. Spatial Control Plane (Traianus Substrate)
   Question: "How is a deterministic spatial state S_n maintained and evolved?"
   Subsystems: Transactional state persistence (SQLite WAL), dynamic variance thresholding, L₂ geometry.
        │
        ▲  ▼  (Dual Interaction Loop: Read Projections ◄► External HITL Feedback)
        │
3. Observation Layer (Ulpia Mathematical Framework / RefApps)
   Question: "How is that spatial state observed, and how does external interaction drive space continuity?"
   Framework & Clients: Ulpia (Native Mathematical Observation Framework), RefApp-01 (Knowledge).
Representation Layer: Maps entities or signals into coordinate vectors v∈R 
d
 .
Spatial Control Plane: Executes deterministic state transitions S 
n+1
​	
 =f(S 
n
​	
 ,v 
n
​	
 ) over the discrete state S 
n
​	
 =(V 
n
​	
 ,E 
n
​	
 ) purely through linear algebra, dynamic variance thresholding, and SQLite WAL append-only persistence (PRIMARY KEY (id, seq)).
Observation Layer: Evaluates read-only perspective projections O 
n
​	
 =P 
θ
​	
 (S 
n
​	
 ) without mutating state S 
n
​	
 . External interactions provide human-in-the-loop (HITL) feedback to satisfy the Ethical Key for state consolidation (ADR-022).
3. Decoupled Architecture & State Function
Given an entity coordinate v∈R 
d
 , the state transition function executes deterministically within the control plane:

S 
n+1
​	
 =f(S 
n
​	
 ,v 
n
​	
 )
Where S 
n
​	
 =(V 
n
​	
 ,E 
n
​	
 ) represents the discrete spatial state at sequence step n:
V 
n
​	
  — Vertices (L 
2
​	
 -normalized coordinate vectors in R 
d
 )
E 
n
​	
  — Deterministic adjacency edges (d(v 
i
​	
 ,v 
j
​	
 )≤ϵ)
(Higher-order simplicial faces K 
n
​	
  are reserved for the WP2 R&D roadmap).
4. Modality Specialization & Empirical Findings (EAS-01)
Traianus enforces a strict distinction based on signal modality:
Continuous Signals & Physical Telemetry: Governed natively by continuous spectral projection variance (σ 
2
 ) in traianus/core.py.
Natural Language Text (RefApp-01): Governed via Normalized Compression Distance (NCD) coupling or Human-In-The-Loop (HITL) validation. This addresses the Representation-State Coupling Problem, defeating keyword injection and noise dilution (AUC>0.93).
5. Quickstart
Minimal setup with venv + pip.

1. Minimal setup
Bash
# Isolated environment (Python 3.10+, see pyproject.toml)
python -m venv .venv
source .venv/bin/activate

# Install the package and the `traianus-bootstrap` script
pip install -e .

# Install test dependencies (pytest, pytest-asyncio, httpx)
pip install -e ".[test]"

# Run the bootstrap scaffold
traianus-bootstrap
2. Start the server (Localhost binding)
Bash
TRAIANUS_TOKEN=your-secret uvicorn traianus.app:app --host 127.0.0.1 --port 8000
The FastAPI server binds exclusively to loopback 127.0.0.1 — no external network exposure.
TRAIANUS_TOKEN is mandatory for protected endpoints (/ingesta, /consolidar, /mutate, /relations, /telemetry). Unauthenticated requests respond with 401.
3. Environment Variables
Variable	Required	Type	Default	Description
TRAIANUS_TOKEN	Yes	string	—	Operator token for protected endpoints (/ingesta, /consolidar, /mutate, /relations, /telemetry).
TRAIANUS_EPSILON_EDGE	No	float	0.8	Distance threshold ϵ for deterministic E 
n
​	
 adjacency (∥v 
i
​	
 −v 
j
​	
 ∥ 
2
​	
 ≤\epsil).
4. Running the Test Suite
Bash
# Hermetic unit & integration tests (offline, no neural model execution)
pytest tests/ -m "not model"

# E2E test suite (requires cached local model)
pytest tests/ -m "model"
6. Documentation Ledger (docs/)
The documentation suite follows a strict Fractal Architecture:
Master Index: Unified traceability matrix (Concept → Code → Test) and navigation map.
Project Identity: System boundaries, Non-Goals, operational invariants, and canonical definitions.
Operational Ledger: Append-only log of operational deltas (Δ 
n
​	
 ) and empirical falsations.
Architecture Specification: Mathematical state machine formulation S 
n
​	
 =(V 
n
​	
 ,E 
n
​	
 ) and SQLite WAL schema.
Data Contracts: Byte-level security filters, Silent Denial (ADR-002), and Pydantic v2 schemas (RawDump, RefinedEntity).
ADR Ledger: Immutable append-only record of architectural decisions (ADR-001 to ADR-027).
Normative Specification EAS-01: Empirical report on the Representation-State Coupling Problem and NCD validation.
Kernel Simulation Guide: Simulation protocol over the 8D real geodetic basis.
7. Development Environment (OpenCode)
This project uses OpenCode as the primary development interface backed by a local Zero-Trust MCP validator architecture.

Governance & Security Constraints
AGENTS.md: Root constitution defining agent roles, single-step execution, and the 5 Code Radicals.
opencode.jsonc: Process-level permission matrix (edit, bash allowlists/denylists).
In-Flight Interception: Agent mutation proposals are intercepted in-flight by the local stdio MCP validator (traianus/security/validator.py) executing 3 physical gates: Safety, process execution denylist, and exact UTF-8 byte Grounding.
License
GPL-3.0-or-later. See pyproject.toml and LICENSE for the full license declaration.