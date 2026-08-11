# ⚙️ Neuro-Symbolic Engineering Methodology and TDD

> **Standard Operating Guide:** This document defines the mandatory flow of analysis, architecture specification, test design, and test-driven development (TDD) cycle for **Traianus** and **TridenGuard**.

---

## 🧠 Core Philosophy
```text
"Neurons propose, rules dispose."
Probabilistic Models (LLMs): Generate code proposals, refactoring, or syntactic structuring.
Deterministic Gates (Validator Gates): Mechanically validate proposals via rigid rules (Zero-Trust, Literal Grounding, algebraic variance) before allowing execution or consolidation.
🔄 4-Phase Workflow
Plaintext
┌─────────────────────────┐     ┌─────────────────────────┐
│ 1. Analysis & Domain    │ ──► │ 2. Specification (ASD)  │
│ (Boundaries & Hardware) │     │ (Contracts & ADRs)      │
└─────────────────────────┘     └─────────────────────────┘
                                             │
                                             ▼
┌─────────────────────────┐     ┌─────────────────────────┐
│ 4. Atomic TDD Cycle     │ ◄── │ 3. TDD Specification    │
│ (🔴 Red ➔ 💻 🟢 Green)  │     │ (Invariant Matrix)      │
└─────────────────────────┘     └─────────────────────────┘
📌 PHASE 1: Analysis & Domain Delimitation
Before modifying the system, analyze requirements and operational boundaries:
Boundaries & Non-Goals: Define what problem is solved and what is explicitly out of scope to avoid scope creep.
Physical Hardware Budget: Ensure solutions execute within 8 GB RAM / Unified Memory (Mac M1) constraints without depending on cloud APIs at runtime.
Deliverable: docs/identity/PROJECT_IDENTITY.md or analysis summary.
🏗️ PHASE 2: Architectural Specification (ASD)
Strict definition of data structures, state equations, and ingress customs:
State Model: Formulation of transitions S 
n+1
​	
 =f(S 
n
​	
 ,v 
n
​	
 ) over the simplicial complex S 
n
​	
 =(V 
n
​	
 ,E 
n
​	
 ,K 
n
​	
 ).
Pydantic Data Contracts: Definition of types and rigid validators (RawDump, RefinedEntity).
Zero-Trust Security Gates: Deterministic rules blocking network access (fetch, axios, requests) or unauthorized execution.
ADRs (Architectural Decision Records): Append-only log of any relevant design decision.
Deliverable: Files in docs/architecture/ (Project_architecture.md, CONTRACTS_AND_PRISMS.md, ADR.md).
📝 PHASE 3: TDD Specification (Invariant Matrix)
Translation of contracts and architectural rules into an explicit matrix of unit/integration tests:

ID Case	Invariant / Rule to Test	Test Input	Expected Result
TC-01	Self-projection exclusion in variance (C1).	L 
2
 geodetic matrix	Consolidation rate ∈[5%,95%]
TC-02	Pseudo-token shield (len != 1).	"toon_factor": "[FRICTION]"	ValidationError (422)
TC-03	Grounding Gate in Refactorizations.	Non-existent citation in source	QUARANTINED state by TridenGuard
TC-04	Zero-Trust Network Prohibition.	Code with fetch() or requests	QUARANTINED state by TridenGuard
⚙️ PHASE 4: Atomic TDD Operational Cycle
🔴 1. RED (Red Phase)
Write the test that exposes the failure or new functionality in the Pytest suite (tests/):

Bash
pytest tests/test_control_plane.py -k "test_nombre_del_caso"
# MUST FAIL 🔴
💻 2. CODE (Implementation Phase with Agents)
Invoke the corresponding OpenCode sub-agent (@fixer or @antigravity-compiler):
The agent must generate the minimal solution using the 5 Code Radicals structure:
Intent_Class: [GENERATE | REFACTOR | FIX | AUDIT]
Runtime_Contract: Target environment and allowed dependencies.
Implementation_Block: Executable code fragment.
Topological_Grounding: Exact textual citation of code to modify.
Safety_Abort: Safety state (NONE if safe).
🟢 3. GREEN (Green Phase)
Apply the patch to source code (traianus/app.py) and re-run the test:

Bash
pytest tests/test_control_plane.py -k "test_nombre_del_caso"
# MUST PASS 🟢
⚙️ 4. REFACTOR / HARNESS (Verification & Documentation)
Deterministic Validation: Execute tools/tridenguard_validator.py and tools/audit_harness.py.
Documentation Sync: Invoke @logographer to update docs/LOGOGRAPHY.md and prevent code-spec drift (Doc-Drift).
🤖 OpenCode Role Integration
Sub-Agent	Primary Role	Phase of Action
@fixer	Audit bug resolution and rapid refactoring.	PHASE 4 (Code/Green)
@antigravity-compiler	Code proposal generation with 5 Radicals validation and Grounding.	PHASE 4 (Code/Green)
@logographer	Specification maintenance and docs/LOGOGRAPHY.md updates.	PHASE 1, 2 and 4 (Refactor/Docs)