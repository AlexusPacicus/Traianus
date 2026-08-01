# Implementation Status: PoC v1.0 (Truth Pass)

> **Purpose:** Transparent declaration of the correspondence between the R&D theoretical framework and the executable PoC v1.0. Everything declared as implemented must be verifiable in `traianus/`; everything that remains a hypothesis is declared as R&D roadmap in `docs/research/`.

**Date:** 2026-08-01 · **Scope:** `traianus/` (executable substrate) vs `docs/research/` (long-term hypotheses)

---

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
| **Vertices (V_n)** | 🟢 100% Implemented | `traianus/` | Append-only immutable node log keyed `(id, seq)` in SQLite — DDL `traianus/app.py:126-139`; new revisions inserted with increasing `seq` per `id` (`next_node_seq`, `traianus/app.py:200-209`); no `UPDATE`/`REPLACE`/`DELETE` on `manifold_nodes` (H4 / ADR-025). |
| **Edges (E_n)** | 🟢 100% Implemented | `traianus/` | Atomic adjacency-ε persistence in `manifold_edges` — server-side `EPSILON_EDGE` (`traianus/app.py:48`), DDL `traianus/app.py:172-179`, transactional insert during consolidation (`traianus/app.py:561`). |
| **Simplicial faces (K_n)** | 🔵 Roadmap I+D | `docs/research/` | Persistent topology & dimension discovery, WP2 — `docs/research/RESEARCH_PROGRAM.md:19-23`. Not executed by PoC v1.0. |
| **Zero-Trust perimeter & C1 gate** | 🟢 100% Implemented | `traianus/` | Fail-closed auth `x-traianus-token` (`traianus/app.py:66-69`); enumerated CORS, no wildcard (`traianus/app.py:30-38`); ingress restricted to `text/plain` (`traianus/app.py:55`, `traianus/app.py:370-371`); dynamic variance threshold calibrated excluding self-projection, observed consolidation rate 30-45% (`traianus/app.py:249-265`, `tools/audit_harness.py`). |
| **Latency** | 🟢 Measured | `traianus/` | Sub-millisecond projection kernel (0.01 ms kernel / ~13 ms total pipeline including neural embedding, PyTorch on CPU). |
| **Provider agnosticism (RH-1)** | 🟡 Partial | `traianus/` + `docs/research/` | Dimension mismatch handled explicitly: zero-padding when `d_db > d_in`; HTTP 422 rejection when `d_in > d_db` (`traianus/app.py:284-292`); multi-provider dynamic switching remains active R&D (RH-1, `docs/research/RESEARCH_HYPOTHESIS.md`). |

---

## 2. Scope Boundary: PoC v1.0 vs R&D Roadmap

* **PoC v1.0 executes** the deterministic spatial skeleton $S_n = (V_n, E_n)$: vertices as an immutable append-only log and deterministic ε-adjacency edges, both governed by transactional persistence and the Zero-Trust perimeter.
* **Higher-order simplicial faces (K_n) and multi-provider dynamic switching form part of the active R&D roadmap** declared in `docs/research/` (WP2, RH-1) and are *not* claimed as implemented.

---

## 3. Claim-to-Source Traceability

| Claim | Primary Source | Guard |
| :--- | :--- | :--- |
| Append-only node log | `traianus/app.py:126-139` | `tests/genericos/test_g5_append_only.py` |
| ε-adjacency persistence | `traianus/app.py:561` | `tests/bloques/relaciones/` |
| Zero-Trust perimeter | `traianus/app.py:30-69` | `tests/genericos/test_g9_zero_trust.py`, `tests/security/` |
| C1 variance calibration | `traianus/app.py:249-265` | `tests/genericos/test_g7_determinismo.py`, `tools/audit_harness.py` |
| Dimension handling (RH-1) | `traianus/app.py:284-292` | `tests/afirmaciones/test_cl_i62_dimension_provider.py` |
| Latency envelope | `tools/audit_harness.py` | Empirical benchmark (audit harness) |
