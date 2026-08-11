# Project Identity & Technical Scope

## 1. Header & Scope
Purpose: This document establishes the constitutional boundaries, taxonomy, non-goals, and invariant principles governing Traianus.
Domain: System identity, governance boundaries, and canonical terminology.
Explicit Delegations:
For state machine mathematics and persistence schemas, see docs/architecture/ARCHITECTURE.md.
For scientific foundations and theoretical grounding, see docs/research/RESEARCH_HYPOTHESIS.md.
For engineering decision records, see docs/architecture/ADR/ADR.md.

## 2. Canonical Definition
Traianus is an open-source Deterministic Computational Substrate for Autonomous Spatial State Governance.
In continuous prose, aliases are: the control plane, the computational substrate, the execution layer, or the substrate.
Dosing Rule: Introduce the full canonical term in the title or opening paragraph of every document. In continuous prose, alternate with the shorter aliases above to avoid terminological saturation.
Note on State Autonomy & HITL Safeguards: Autonomous Spatial State Governance specifies the substrate's ability to execute continuous geometric transitions ($S_n \to S_{n+1}$), variance circuit breaking, metric decay, and quarantine persistence independently of runtime cloud infrastructure or continuous manual intervention. The Ethical Key (HITL) acts as a safety gate for entity consolidation, not as a manual driver of substrate state transitions.

## 3. Ontological Position Postulate
Traianus does not represent reality, nor does it construct representations of reality. It preserves state continuity for externally generated representations within a deterministic geometric computational substrate.
Traianus establishes an independent Spatial Control Plane where structural state execution is computationally decoupled from both representation providers and observation layers.

### Ontological Consequences

* **Content Agnosticism:** Input vector coordinates ($v \in \mathbb{R}^d$) are computationally equivalent regardless of their textual origin. The substrate governs state over 384D L2-normalized text embeddings (all-MiniLM-L6-v2); representation providers beyond text are roadmap scope (WP).

* **Domain Independence:** Reality exists outside Traianus. Representation exists outside Traianus. Observation exists outside Traianus. The substrate activates when a valid coordinate representation is presented.

* **Reference Scope:** Sovereign personal knowledge constitutes its initial reference application (RefApp-01), not its structural limit.

## 4. Official Taxonomy

* **Reality:** The external physical or domain phenomenon being measured. Reality exists entirely outside Traianus.

* **Representation Provider:** The external pipeline mapping reality into coordinates $v \in \mathbb{R}^d$ — in the PoC, the text-embedding encoder (all-MiniLM-L6-v2, offline, pinned). The substrate consumes representations; it never generates them natively. Additional provider families are roadmap scope (WP, see IMPLEMENTATION_STATUS.md).

* **Spatial Control Plane (Traianus Substrate):** The deterministic execution layer that governs state transitions ($S_{n+1} = f(S_n, v_n)$) over the discrete simplicial complex $S_n = (V_n, E_n, K_n)$ purely through linear algebra, dynamic variance thresholding, and transactional state persistence (ADR-023).

* **Observation Layer (Ulpia / RefApps):** Perspective projections ($O_n = P_\theta(S_n)$). External interactions within this layer provide the human-in-the-loop (HITL) feedback necessary to satisfy the Ethical Key for state consolidation (ADR-022, ADR-024).

* **Ulpia:** The native mathematical observation framework and research programme in observation theory. It contains zero rendering logic, acting as the native perspective projection engine ($O_n = P_\theta(S_n)$) over which domain RefApps operate.

## 5. Canonical Substitution Table (Fossil Purge)
The following substitutions are mandatory across all Identity, Hypothesis, and Philosophy documents. Fossil terms are permitted exclusively in the PoC Technical Implementation column of README.md §4 and in installation scripts (flake.nix).
| Fossil Term | Canonical Term | Technical Rationale |
| --- | --- | --- |
| PKM / Personal Knowledge App | RefApp-01 (Sovereign Personal Knowledge) | It is the first reference application, not the structural limit of the software. |
| Semantic Organization | State Continuity / Spatial State Governance | Traianus does not "organize semantics"; it maintains the continuity of vector states. |
| Semantic Representation | Entity / Mathematical Representation | Traianus operates on the mathematical representation of reality in general. |
| Ulpia (Frontend / UI) | Ulpia (Native Mathematical Observation Framework) | Native mathematical observation layer ($O_n = P_\theta(S_n)$). |
| Visualize / Display / UI | Project / Observe / Inspect | Zero UI or rendering code in the Traianus core. |
| Model Agnosticism | Provider Agnosticism | Encompasses the current text-embedding provider; additional providers are roadmap (WP), not current scope. |
| Organizes representations | Preserves state continuity | Traianus does not "organize"; it executes deterministic state transitions ($S_{n+1} = f(S_n, v_n)$). |

## 6. Boundaries & Non-Goals
### 6.1 What Traianus Is NOT

* **Not a Large Language Model (LLM):** Performs zero probabilistic text completion or token generation.

* **Not a Vector Database:** Does not merely index static embeddings for top-K similarity retrieval; functions as an active spatial control plane.

* **Not a Graph Database:** Avoids manual triple extraction (subject-predicate-object) or static rigid schemas.

* **Not an Execution Agent Framework:** Executes no autonomous external tools, API calls, or unmonitored background actions.

* **Not a User Application or UI Framework:** Traianus contains zero rendering, layout, or user interface code. External inspection layers (e.g., Ulpia / RefApps) act as optional observation clients.

### 6.2 Operational Invariants

* **Zero External Dependencies at Runtime:** The core executes offline on local architecture without requiring external cloud APIs or runtime network connectivity.

* **Reproducibility Over Performance:** Given identical vector input and initial state, the output state must be identical every time ($S_{n+1} = f(S_n, v_n)$).

* **Provider Agnosticism:** Upgrading or replacing the representation provider must not corrupt or reset the existing geometric state.

## 7. Core System Invariants

* **Provider Agnosticism:**
  * **Execution Mechanism:** Operates strictly on $L_2$-normalized coordinate vectors $v \in \mathbb{R}^d$.
  * **Boundary:** Agnostic to vector origins; zero modification of external provider weights or parameters.

* **Deterministic State Execution:**
  * **Execution Mechanism:** State transitions governed purely by algebraic rules ($S_{n+1} = f(S_n, v_n)$) and dynamic variance thresholding.
  * **Boundary:** Zero probabilistic token completion or LLM execution within the control plane.

* **Local Runtime Sovereignty:**
  * **Execution Mechanism:** Local-first state persistence and spatial execution.
  * **Boundary:** Operates offline; zero runtime cloud API dependency allowed.
