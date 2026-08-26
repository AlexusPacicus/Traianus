# Implementation Status: Control Plane v1.0.1 (IMPLEMENTED)

> **Purpose:** Transparent declaration of the correspondence between the R&D theoretical framework and the executable Core/Control Plane (substrate frozen at **v1.0.0**; current release **v1.0.1** — stability/security/hygiene, zero scope change). Everything declared as IMPLEMENTED must be verifiable in `traianus/`; everything that remains a hypothesis is declared as RESEARCH / FUTURE ROADMAP in the consolidated status documentation (docs/STATUS.md).

**Date:** 2026-08-14 · *Amended 2026-08-24:* version reconciliation and Ulpia client status correction (LEDGER seq 34) · **Scope:** `traianus/` (executable substrate) vs consolidated status documentation (docs/STATUS.md)

---

## 0. Status Legend (Formal Classification)

Every element of the repository belongs to exactly one of these five categories.

| Icon | Category | Meaning |
| :---: | :--- | :--- |
| 🟢 | **IMPLEMENTED** | Verified in `traianus/` (code + deterministic test). Part of Core/Control Plane v1.0.0. |
| 🟡 | **EXPERIMENTAL** | R&D reproducible — located in `tools/experiments/`. Empirically validated but outside the production control plane. |
| 🔵 | **RESEARCH / FUTURE WORK** | Declared in `docs/STATUS.md` and ADRs (WP1–WP4, Persistent Homology, RH-1, Ulpia). Not part of v1.0.0. |
| ⚪ | **DOCUMENTATION** | Governance, specification, and traceability documents (`docs/`, `README.md`, this file). |
| 🔧 | **INFRASTRUCTURE** | Packaging, tooling, CI, test harness, and agent configuration. |

---

## 1. Core / Control Plane Declaration

**The Core/Control Plane of Traianus is v1.0.0 and is IMPLEMENTED.** It executes the deterministic spatial skeleton $S_n = (V_n, E_n)$ in `traianus/` and is verified by the hermetic test suite (`pytest tests/ -m "not model"`). No component of the Core/Control Plane is claimed as implemented without a deterministic test or empirical harness proof.

---

## 2. Implementation Matrix (Core/Control Plane v1.0.0)

| Component | State | Scope | Verified Evidence |
| :--- | :--- | :--- | :--- |
| **Vertices (V_n)** | 🟢 100% Implemented | `traianus/` | Append-only immutable node log keyed `(id, seq)` in SQLite — DDL `traianus/storage.py:129`; new revisions inserted with increasing `seq` per `id` (`next_node_seq`, `traianus/storage.py:276`); no `UPDATE`/`REPLACE`/`DELETE` on `manifold_nodes` (H4 / ADR-025). |
| **Edges (E_n)** | 🟢 100% Implemented | `traianus/` | Atomic adjacency-ε persistence in `manifold_edges` — server-side `EPSILON_EDGE` (`traianus/app.py:100`), DDL `traianus/storage.py:207`, transactional append during rebuild (`traianus/storage.py:525-531`). |
| **Simplicial faces (K_n)** | 🔵 RESEARCH / FUTURE ROADMAP | `docs/STATUS.md` | Persistent topology & dimension discovery — WP2 (ADR-018/ADR-019/ADR-023). Declared as R&D roadmap, not part of Core/Control Plane v1.0.0. |
| **Zero-Trust perimeter & C1 gate** | 🟢 100% Implemented | `traianus/` | Fail-closed auth `x-traianus-token` (`traianus/app.py:118`); enumerated CORS, no wildcard (`traianus/app.py:72-79`); ingress restricted to `text/plain` (`traianus/app.py:107`, `traianus/app.py:314`); dynamic variance threshold calibrated excluding self-projection (`traianus/geometry/observables.py`), observed consolidation rate 30-45% (`tools/audit/audit_harness.py`). |
| **Latency** | 🟢 Measured | `traianus/` | ~12ms p50 total pipeline (encode ~11.5ms + SQLite WAL persist ~0.5ms; LEDGER seq 22 measurement). Verified offline with `HF_HUB_OFFLINE=1` + `local_files_only=True`. |
| **Provider agnosticism (RH-1)** | 🟡 Partial | `traianus/` | Dimension mismatch handled explicitly: zero-padding when d_db > d_in; HTTP 422 rejection when d_in > d_db (traianus/app.py:221-229, traianus/app.py:367, traianus/app.py:518-529). THE v1.0.0 CORE IS FROZEN AT 384D (all-MiniLM-L6-v2, pinned, offline). Multi-provider dynamic switching and experimental dimensionalities (e.g., 14D) remain active R&D (RH-1, see LEDGER.md seq 8) and are out of scope for the current validation phase. |
| **Observation layer ($O_n = P_\theta(S_n)$)** | 🟢 Contract + 🟡 Client (code exists, integration pending) | `traianus/` + `frontend/` | Read-only perspective projections declared in ADR-022/ADR-024; zero-side-effect reads verified (G5/OB, ADR-025 #2). The read-only contract is implemented in `traianus/`; a Ulpia client prototype lives under `frontend/` (React/Vite, arrived via the ulpia-line merge) but its integration with the observation contract remains RESEARCH / FUTURE ROADMAP — it is not part of the v1.0.x substrate scope and carries no substrate code. |

---

## 3. Repository Classification Matrix

Formal classification of the project tree. Each element belongs to exactly one category (see §0 legend).

| Category | Folders / Files |
| :--- | :--- |
| 🟢 **IMPLEMENTED** | `traianus/app.py` · `traianus/storage.py` · `traianus/core.py` · `traianus/bootstrap.py` · `traianus/observability.py` · `traianus/geometry/` · `traianus/governance/` · `traianus/representation/` · `traianus/security/` · `traianus/__init__.py` |
| 🟡 **EXPERIMENTAL** | `tools/experiments/` — `shared/` (corpus, kinematics engine), `hypothesis/` (H1/H2/H3), `logographic/` (EAS-01), `representation/` (independence), `validation/` (C1, WP1), `tooling/` (fixture export, ingest, simulation; dynamic bridge-audit suite: `epsilon_knee_audit.py`, `audit_axis_anisotropy.py`, `inter_part_enrichment.py`, `fisher_axis_part_test.py` — Otsu-adaptive epsilon, permutation-null anisotropy, enrichment-ratio 5x5 matrix, 8x5 axis-part independence battery, see LEDGER seq 40 / telemetry v5), `exp_manifesto_tomo0.py` |
| 🔵 **RESEARCH / FUTURE WORK** | Work Packages WP1–WP4, Persistent Homology, RH-1 (multi-provider), Ulpia observation client *integration* — see §4. No code for these exists in `traianus/`; the Ulpia client prototype under `frontend/` is out of substrate scope. |
| ⚪ **DOCUMENTATION** | `docs/` (INDEX, LEDGER, PROJECT_IDENTITY, STATUS, architecture/, audit/, specifications/) · `README.md` · `IMPLEMENTATION_STATUS.md` · `LICENSE` |
| 🔧 **INFRASTRUCTURE** | `pyproject.toml` · `opencode.jsonc` · `AGENTS.md` · `.gitignore` · `.github/` (CI) · `.opencode/` (skills) · `tests/` (verification harness) · `tools/audit/` (audit harness, invariant verifier) · `tools/mcp/` (spectral math MCP) |

---

## 4. Work Packages — RESEARCH / FUTURE ROADMAP

The following work packages are explicitly declared **RESEARCH / FUTURE ROADMAP**. They are funded R&D scope, documented in `docs/STATUS.md` and the ADR ledger, and are **not** part of Core/Control Plane v1.0.0.

| Work Package | Scope | Normative Reference |
| :--- | :--- | :--- |
| **WP1 — Dynamic Geodetic Axes** | Transition from the fixed `PROSTHETIC_NSM_V1` bootstrap basis to corpus-derived axes; decoupling governance from representation (EAS-01). | ADR-017 + ADR ledger Amendment §1 |
| **WP2 — Persistent Homology & Simplicial Faces (K_n)** | Persistent Homology filtration over simplicial complexes; dynamic k-discovery via $H_1$; native GUDHI C++ integration. | ADR-018, ADR-019, ADR-023, docs/STATUS.md |
| **WP3 — Riemannian Metric Engine** | System clock eradication; geodesic metric tensor integration ($D_{\text{somatic}} = \int \sqrt{g_{ij} \, dx^i \, dx^j}$). | ADR-020 |
| **WP4 — Cross-Scope Invariant Preservation** | Architectural drift control for invariants across optimizations, language bindings, and hardware targets. | ADR-025 |
| **RH-1 — Multi-Provider Dynamic Switching** | Dynamic provider switching and experimental dimensionalities beyond the frozen 384D core. | LEDGER.md seq 8 |
| **Ulpia Observation Client** | External rendering/inspection layer over the read-only observation contract. | ADR-022/ADR-024 |

---

## 5. Scope Boundary: v1.0.0 vs R&D Roadmap

* **Core/Control Plane v1.0.0 executes** the deterministic spatial skeleton $S_n = (V_n, E_n)$: vertices as an immutable append-only log and deterministic ε-adjacency edges, both governed by transactional persistence and the Zero-Trust perimeter. The observation contract $O_n = P_\theta(S_n)$ (ADR-022/ADR-024) is exposed by read-only endpoints; the Ulpia client rendering layer is roadmap.
* **WP1–WP4 (including Persistent Homology / K_n) and multi-provider dynamic switching (RH-1) form the active RESEARCH / FUTURE ROADMAP** declared in consolidated status documentation (docs/STATUS.md) and are *not* claimed as implemented in v1.0.0.

---

## 6. Claim-to-Source Traceability

| Claim | Primary Source | Guard |
| :--- | :--- | :--- |
| Append-only node log | `traianus/storage.py:129` | `tests/unit/test_substrate.py::test_append_only_revision_log` |
| ε-adjacency persistence | `traianus/storage.py:594` | `tests/unit/test_substrate.py::test_epsilon_edges_adjacency` |
| Zero-Trust perimeter | `traianus/app.py:72-79`, `traianus/app.py:118` | `tests/security/test_security.py`, `tests/security/` |
| C1 variance calibration | `traianus/geometry/observables.py` | `tests/unit/test_substrate.py::test_c1_threshold_excludes_self_projection`, `tools/audit/audit_harness.py` |
| Dimension handling (RH-1) | `traianus/app.py:221-229`, `traianus/app.py:518-529` | `tests/representation/test_representation_providers.py` |
| Latency envelope | `tools/audit/audit_harness.py` | Empirically validated low-latency CPU-bound processing (~12ms p50 pipeline) |
