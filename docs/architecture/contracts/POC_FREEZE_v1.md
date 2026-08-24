# PoC Freeze Contract (v1.0.0)

## 1. Purpose & Milestone Status

This document formalizes the closure of the Proof of Concept (PoC) and freezes Traianus v1.0.0. It fixes the implemented scope and serves as the reference baseline for subsequent research iterations.

---

## 2. Invariants

* **Fixed Vector Space:** Constrained to 384 dimensions ($\mathbb{R}^{384}$).
* **Deterministic Governance:** State transitions managed via linear algebra and computational topology, with no stochastic dependencies or external calls within the state loop.
* **Immutable Ledger:** State record strictly append-only in local SQLite.
* **Total Decoupling:** The state layer is agnostic to which engine or architecture generated the coordinate vector.

---

## 3. Reproducibility & Verification

* **Hermetic Execution:** Runs 100% offline on commodity hardware ($\le 8\text{ GB RAM}$) with no network or cloud infrastructure dependencies.
* **Determinism:** Under an identical pinned environment (Python ~=3.11 and the dependency set locked in pyproject.toml, model revision 1110a243fdf4706b3f48f1d95db1a4f5529b4d41) and an identical input vector history, the state sequence generated in the ledger is identical at runtime. No bitwise cross-build or cross-platform guarantee is claimed (see docs/STATUS.md, finding M1).

---

## 4. Version Invariance Rule

The v1.0.0 codebase is sealed. Any modification to state geometry, persistence schema, or dimensional expansion belongs to future iterations (v2.0.0+) and shall be treated as a new research milestone.
