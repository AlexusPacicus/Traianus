# TRAIANUS
### Deterministic Spatial Control Plane & Local-First Research Substrate
Decoupling vector representation systems from state management over $v \in \mathbb{R}^d$.


```text
[ Vector (Texto) ]
        │
        ▼  (Aduana Zero-Trust / Inferencia Local)
┌──────────────────────────────────────────────────────────┐
│  TRAIANUS : Control Plane / Sustrato Latente             │
│  Gestión determinista del estado y topología (v ∈ ℝᵈ)    │
└──────────────────────────────────────────────────────────┘
        │
        ▼  (Colapso Transversal)
[ ULPIA : Capa de Proyección Geométrica 2D ] ──> Observación humana
Traianus operates strictly as a blind, N-dimensional mathematical substrate (Control Plane) computing physical friction and topological tension. Its counterpart, Ulpia, is a deterministic 2D geometric projection layer where these latent vector forces are projected for human observation, completely bypassing linear chat interfaces.


⚡ Quickstart & Hermetic Verification
Traianus is frozen in v1.0.0 with a hermetic, offline-isolated test suite. You can run the deterministic core and verify system invariants locally:


Bash
# 1. Clone the repository
git clone [https://github.com/AlexusPacicus/Traianus.git](https://github.com/AlexusPacicus/Traianus.git)
cd Traianus


# 2. Install in editable mode (Python 3.11, pinned in pyproject.toml)
python -m venv .venv
source .venv/bin/activate
pip install -e .
pip install -e ".[test]"


# 3. Bootstrap the local substrate scaffold (8D geodetic basis)
traianus-bootstrap


# 4. Run the complete hermetic test suite (Unit, Integration, Security & Representation)
pytest
🛡️ System Boundaries & Non-Goals
Not a User Interface Framework: contains zero rendering or layout code; visual surfaces like Ulpia act strictly as deterministic geometric projection layers.
Zero External Dependencies at Runtime: executes strictly offline on local architecture without requiring external cloud APIs or runtime network connectivity.
Reproducibility Over Performance: given identical vector input and initial state, the output state must be identical every time (S 
n+1
​	
 =f(S 
n
​	
 ,e 
n
​	
 )).
🔬 Modality Specialization (EAS-01)
Continuous signals & physical telemetry: governed natively by continuous spectral projection variance (σ 
2
 ) in traianus/geometry/observables.py (C1 threshold calibration, self-projections excluded).
Natural language text (RefApp-01): governed via Normalized Compression Distance (NCD) coupling or Human-In-The-Loop (HITL) validation — demonstrating graded resistance to keyword injection (zlib AUC 0.953, bz2/lzma AUC 0.922–0.933).
📌 Status
Core/Control Plane v1.0.0 (IMPLEMENTED). Work Packages WP1–WP4 (including Persistent Homology) and the Ulpia geometric projection layer remain RESEARCH / FUTURE ROADMAP. See IMPLEMENTATION_STATUS.md and docs/STATUS.md.


📖 Deep-Dive Documentation
For thorough theoretical, topological, and architectural specifications, consult the docs/ directory:
🏛 System Architecture: docs/architecture/ARCHITECTURE.md — complete component contracts and dataflow design.
🔒 PoC Freeze Contract: docs/architecture/contracts/POC_FREEZE_v1.md — v1.0.0 invariants, reproducibility guarantees, and version sealing rules.
🛡 Security & Boundary Audit: docs/audit/AUDIT.md — invariant verification and hermetic boundary guarantees.
📜 Foundation Manuscripts (SUA POTESTAS, Tomo 0): declared RESEARCH / FUTURE ROADMAP — experimental reproduction in tools/experiments/exp_manifesto_tomo0.py.
Master Index: docs/INDEX.md — unified traceability matrix (Concept → Code → Test).
Operational Ledger: docs/LEDGER.md — append-only log of operational deltas and empirical falsations.
Implementation Status: IMPLEMENTATION_STATUS.md + docs/STATUS.md — formal 5-category repository classification.