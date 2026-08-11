# Implementation Status: PoC v1.0 (Truth Pass)

> **Purpose:** Transparent declaration of the correspondence between the R&D theoretical framework and the executable PoC v1.0. Everything declared as implemented must be verifiable in `traianus/`; everything that remains a hypothesis is declared as R&D roadmap in `docs/research/`.

**Date:** 2026-08-01 · **Scope:** `traianus/` (executable substrate) vs `docs/research/` (long-term hypotheses)---

## 0. Status Legend

| Icon | Meaning |
| :---: | :--- |
| 🟢 | Implemented and verified in `traianus/` (code + deterministic test) |
| 🟡 | Partially implemented (explicit boundary or conditional behavior) |
| 🔵 | R&D roadmap — declared in `docs/research/`, not part of PoC v1.0 |

---

## 1. Implementation Matrix

| Component | State | Scope | Verified Evidence |
| :--- | :--- | :--- | :--- |
| **Vertices (V_n)** | 🟢 100% Implemented | `traianus/` | Append-only immutable node log keyed `(id, seq)` in SQLite — DDL `traianus/storage.py:129`; new revisions inserted with increasing `seq` per `id` (`next_node_seq`, `traianus/storage.py:276`); no `UPDATE`/`REPLACE`/`DELETE` on `manifold_nodes` (H4 / ADR-025). |
| **Edges (E_n)** | 🟢 100% Implemented | `traianus/` | Atomic adjacency-ε persistence in `manifold_edges` — server-side `EPSILON_EDGE` (`traianus/app.py:92`), DDL `traianus/storage.py:207`, transactional insert during rebuild (`traianus/storage.py:594`). |
| **Simplicial faces (K_n)** | 🔵 Roadmap I+D | `docs/research/` | Persistent topology & dimension discovery, WP2 — `docs/research/RESEARCH_PROGRAM.md:19-23`. Not executed by PoC v1.0. |
| **Zero-Trust perimeter & C1 gate** | 🟢 100% Implemented | `traianus/` | Fail-closed auth `x-traianus-token` (`traianus/app.py:110-113`); enumerated CORS, no wildcard (`traianus/app.py:65-73`); ingress restricted to `text/plain` (`traianus/app.py:99`, `traianus/app.py:298-299`); dynamic variance threshold calibrated excluding self-projection (`traianus/core.py:39`), observed consolidation rate 30-45% (`tools/audit/audit_harness.py`). |
| **Latency** | 🟢 Measured | `traianus/` | Sub-millisecond projection kernel (0.01 ms kernel / ~13 ms total pipeline including neural embedding, PyTorch on CPU). |
| **Provider agnosticism (RH-1)** | 🟡 Partial | `traianus/` + `docs/research/` | Dimension mismatch handled explicitly: zero-padding when d_db > d_in; HTTP 422 rejection when d_in > d_db (traianus/app.py:353-357, traianus/app.py:466-473). THE POC v1.0 CORE IS OFFICIALLY FROZEN AT 384D (all-MiniLM-L6-v2, pinned, offline). Multi-provider dynamic switching and experimental dimensionalities (e.g., 14D) remain active R&D (RH-1, see LEDGER.md seq 8) but are out of scope for the current validation phase. |
| **Observation layer ($O_n = P_\theta(S_n)$)** | 🟢 Contract + 🔵 Client | `traianus/` + `docs/observation/` | Read-only perspective projections declared in ADR-022/ADR-024; zero-side-effect reads verified (G5/OB, ADR-025 #2). The Ulpia client itself is roadmap (no UI code). See `docs/observation/ULPIA_OVERVIEW.md`. |

---

## 2. Scope Boundary: PoC v1.0 vs R&D Roadmap

* **PoC v1.0 executes** the deterministic spatial skeleton $S_n = (V_n, E_n)$: vertices as an immutable append-only log and deterministic ε-adjacency edges, both governed by transactional persistence and the Zero-Trust perimeter. The observation contract $O_n = P_\theta(S_n)$ (ADR-022/ADR-024) is exposed by read-only endpoints; the Ulpia client rendering layer is roadmap.
* **Higher-order simplicial faces (K_n) and multi-provider dynamic switching form part of the active R&D roadmap** declared in `docs/research/` (WP2, RH-1) and are *not* claimed as implemented.

---

## 3. Claim-to-Source Traceability

| Claim | Primary Source | Guard |
| :--- | :--- | :--- |
| Append-only node log | `traianus/storage.py:129` | `tests/test_substrate.py::test_append_only_revision_log` |
| ε-adjacency persistence | `traianus/storage.py:594` | `tests/test_substrate.py::test_epsilon_edges_adjacency` |
| Zero-Trust perimeter | `traianus/app.py:65-73`, `traianus/app.py:110-113` | `tests/test_security.py`, `tests/security/` |
| C1 variance calibration | `traianus/core.py:39` | `tests/test_substrate.py::test_c1_threshold_excludes_self_projection`, `tools/audit/audit_harness.py` |
| Dimension handling (RH-1) | `traianus/app.py:203-214`, `traianus/app.py:331-340` | `tests/test_cl_i62_dimension_provider.py` |
| Latency envelope | `tools/audit/audit_harness.py` | Empirical benchmark (audit harness) |
