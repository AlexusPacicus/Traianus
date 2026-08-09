# Traianus

An offline-first, open-source computational substrate that governs spatial state deterministically over coordinate vectors — independently of how those vectors are produced.

Every system that manages knowledge inherits a hidden coupling: the way it *represents* concepts is fused with the way it *stores and evolves* them. Change the representation (swap an embedding model for a symbolic encoder, or a vision pipeline for a text extractor), and the stored state breaks. Traianus cuts this knot by introducing a **spatial control plane** — a deterministic state machine that operates purely on coordinate vectors $\mathbf{v} \in \mathbb{R}^d$, without caring how those vectors are produced.

This separation makes three promises possible:
- **Deterministic text-embedding engine (384D)** — state is governed over L2-normalized `all-MiniLM-L6-v2` embeddings; other providers are roadmap (WP), not current scope
- **Deterministic auditability** — every state transition $S_{n+1} = f(S_n, v_n)$ is reproducible given identical input vectors
- **Offline sovereignty** — the entire substrate runs on consumer local hardware ($\le 8$ GB RAM) with no runtime cloud dependency

Current status: Proof of Concept (PoC) v1.0 using sovereign personal knowledge as its initial reference application (RefApp-01). See [IMPLEMENTATION_STATUS.md](./IMPLEMENTATION_STATUS.md) for the transparent declaration of what is implemented vs. what is R&D roadmap.

> **"Traianus does not define how reality is represented. It operates upon coordinate vectors $\mathbf{v} \in \mathbb{R}^d$ emitted by external providers to govern spatial state deterministically."**

> **North star (SPEC-REFACTOR-v0.2 §1.3):** "The NSM basis is a provisional prosthesis; the destination is a basis derived from the data the substrate governs (WP1)."

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
   Providers (PoC):
     • Text embedding model — all-MiniLM-L6-v2 (384D float32, offline, pinned)
     • Future representation providers are roadmap scope (see IMPLEMENTATION_STATUS.md)
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

> **Note:** *Higher-order simplicial faces (K_n) and multi-provider dynamic switching form part of the active R&D roadmap, preserved in `docs/exploring/legacy_docs/research/`.* The executable PoC v1.0 of `traianus/` governs the lower-dimensional skeleton $S_n = (V_n, E_n)$; higher-order structures $K_n$ are not executed by the current release.

External observation layers evaluate read-only perspective projections $O_n = P_\theta(S_n)$ without mutating state $S_n$ (ADR-024).

## 4. Scientific Hypotheses

* **RH-0 (Primary Hypothesis):** Traianus investigates whether deterministic computational state can be maintained independently of the mechanisms used to represent external reality.

* **RH-1 (Provider Agnosticism):** The spatial control plane routes and governs spatial state without modifying or relying on internal representation provider weights or semantics.

* **RH-2 (Determinism & Auditability):** Dynamic variance thresholding aims to guarantee reproducible execution paths ($S_{n+1} = f(S_n, v_n)$) given identical inputs.

* **RH-3 (Local Edge Execution):** Operates offline on consumer local hardware ($\le 8$ GB RAM) without requiring runtime cloud API connectivity.

## 5. Quickstart

Minimal quickstart with `venv + pip` — Nix is an optional alternative, not a requirement.

### 1. Minimal setup (venv + pip)

```bash
# Isolated environment (Python 3.10+, see pyproject.toml)
python -m venv .venv
source .venv/bin/activate

# Install the package and the `traianus-bootstrap` script
pip install -e .
# Test extra (pytest, pytest-asyncio, httpx) to run the suite
pip install -e ".[test]"

# Prefetch the offline model (all-MiniLM-L6-v2). The bootstrap and the
# server use local_files_only=True: the model must be cached locally
# before the first server boot.
#
# On a fresh machine, download the model once (one-time):
#   python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"
# Then proceed with the bootstrap and server as usual.
traianus-bootstrap
```

> Nix with flakes (`nix develop`) remains an alternative, but the `venv + pip` path above is the canonical minimal quickstart.

### 2. Start the server (Zero-Trust, localhost only)

```bash
TRAIANUS_TOKEN=your-secret uvicorn traianus.app:app --host 127.0.0.1 --port 8000
```

* The FastAPI server binds exclusively to the loopback `127.0.0.1` — no external network exposure.
* `TRAIANUS_TOKEN` is **mandatory** for the protected routes: `/ingesta`, `/consolidar`, `/mutate`, `/relations`, `/telemetry`. Fail-closed: if it is not defined in the environment, every protected route responds `401`.

### 3. Environment variables

| Variable | Required | Type | Default | Description |
| --- | --- | --- | --- | --- |
| `TRAIANUS_TOKEN` | Yes | string | — | Operator token for mutating endpoints (`/ingesta`, `/consolidar`, `/mutate`, `/relations`, `/telemetry`). Read per-request, so it can be rotated without a restart. |
| `TRAIANUS_EPSILON_EDGE` | No | float | `0.8` | ε threshold for deterministic E_n adjacency (‖v_i − v_j‖₂ ≤ ε) during consolidation (ADR-023/H5). Server-side constant, configurable at boot only. |

### 4. Hermetic tests (no model, offline)

```bash
pytest tests/ -m "not model"
```

### 5. E2E tests with the real model

```bash
pytest tests/ -m "model"
```

Requires the model cached locally (prefetch with `traianus-bootstrap`). The `model` marker is registered in `pyproject.toml`.

## 6. Documentation Ledger

* **Project Identity** (`docs/PROJECT_IDENTITY.md`): System boundaries, canonical definitions, non-goals, and official taxonomy.

* **Project Architecture** (`docs/architecture/ARCHITECTURE.md`): Mathematical state machine formulation $S_n = (V_n, E_n, K_n)$ and transactional persistence layer.

* **Data Contracts** (`docs/architecture/contracts/CONTRACTS_AND_PRISMS.md`): Pydantic schema specifications (RawDump, RefinedEntity) and Zero Trust ingress firewall.

* **ADR Ledger** (`docs/architecture/ADR/ADR.md`): Immutable append-only log of architectural decision trade-offs (ADR-001 to ADR-027).

* **Governance & Audit** (`AGENTS.md`, `TRAIANUS_AUDIT.md`): Agent constitution with the mandatory proposal schema, and the technical audit report with remediation status.

* **Research (archived)** (`docs/exploring/legacy_docs/research/`): RESEARCH_HYPOTHESIS.md (grounding in Conceptual Spaces, Gärdenfors) and RESEARCH_PROGRAM.md (WP1-WP4 roadmap), preserved for historical reference.

## 7. Development Environment (OpenCode)

This project uses [OpenCode](https://opencode.ai) as the primary AI-assisted development interface with a zero-trust MCP architecture.

### OpenCode Plugin Setup

```bash
# Install the OpenCode plugin and skills runtime
cd .opencode && npm install && cd ..
```

This installs `@opencode-ai/plugin` and the two skills:
- `tdd-cycle` — Red-Green-Refactor workflow with empirical validation
- `tridenguard-5-radicales` — Structured mutation proposals (5 Radicals)

### Configuration Summary

| Component | Value |
|---|---|
| Primary model | `opencode/longcat-2.0-free` (1M context, free tier) |
| Small model | `opencode/deepseek-v4-flash-free` (flash, free tier) |
| MCP servers | `tridenguard-validator` (Zero-Trust gate), `spectral-math-engine` (deterministic algebra) |
| Network | Fully denied (`webfetch: deny`, `websearch: deny`) |
| Git mutations | Require confirmation (`ask`) |

### MCP Servers

Both servers run locally over stdio — no network egress:

- **`traianus/security/validator.py`** (v1.2.0) — validates mutation proposals through 3 deterministic gates: Safety, Zero-Trust, Grounding
- **`tools/spectral_math_mcp.py`** (v1.0.0) — deterministic math: C1 threshold calibration, simplex volume (Cayley-Menger), barycentric coordinates, float drift analysis

### Permissions

OpenCode operates under a strict permission matrix (`opencode.jsonc`):
- **Read-only git** — `git status`, `git diff`, `git log`, `git show` allowed without prompt
- **Mutating git** — `git commit`, `git push`, `git checkout` require confirmation
- **Destructive** — `rm *` denied
- **Network** — all web access denied

See `opencode.jsonc` for the full permission matrix and `AGENTS.md` for the agent constitution.

## License

GPL-3.0-or-later. See `pyproject.toml` and `LICENSE` for the full license declaration.
