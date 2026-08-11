# Ulpia — Native Mathematical Observation Framework (Layer 3)

**Date:** 2026-08-03
**Scope:** Observation layer $O_n = P_\theta(S_n)$ over the Traianus spatial substrate.

---

## 1. Position in the 3-Layer Model

| Layer | Role |
| :--- | :--- |
| 1. Ingress | External representation providers emit $L_2$-normalized coordinate vectors $\mathbf{v} \in \mathbb{R}^d$. |
| 2. Substrate | Traianus governs the deterministic spatial state $S_n = (V_n, E_n, K_n)$ (ADR-023). |
| 3. Observation | **Ulpia** evaluates read-only perspective projections $O_n = P_\theta(S_n)$; domain RefApps consume those projections. |

Ulpia is the **native mathematical observation framework** of the Traianus 3-layer model. It contains **zero rendering, layout, or user interface logic**; it is the perspective-projection engine over which domain reference applications (RefApp-01 Knowledge, RefApp-02 Cybersecurity, RefApp-03 Telemetry) operate.

## 2. Theoretical Boundary (ADR-024, NEXT_RESEARCH Direction E)

Ulpia is an **independent mathematical research programme**. It does not construct the geometric state maintained by Traianus; it investigates how such structures are observed, projected, analyzed, and characterized once they exist.

> Representation is not the geometric state.
> Observation ($O_n = P_\theta(S_n)$) is not the geometric state.
> Perspective projection does not modify the underlying geometric state.

This triple distinction is normative (ADR-024, "Projection Independence and Perspective Isolation"):

- **Perspective Non-Interference:** reading or projecting $S_n$ generates **zero side effects** on persistent storage.
- **Local Impact Isolation:** interactions over localized projections ($O_{\text{n,local}}$) generate vector mutations bounded by the distance threshold $\epsilon$; state changes remain topologically confined to the affected neighborhood ($U \subset V_n$).

## 3. Dual-Key Interaction (ADR-022)

External inspection layers provide the **human-in-the-loop (HITL)** feedback required to satisfy the **Ethical Key** for state consolidation:

- **Topological Key (Algebraic):** $\sigma^2 \geq \sigma^2_{\text{dynamic}}$ — evaluated by the Traianus control plane (C1 gate, self-projection excluded).
- **Ethical Key (Sovereignty):** explicit HITL operator intervention (`revision_milestone = 1`) injected through the observation layer.

Neither key holds unilateral authority to consolidate state; observations merely expose state and carry the operator's ethical decision.

## 4. Implementation Status

| Capability | State |
| :--- | :--- |
| Perspective projection model $O_n = P_\theta(S_n)$ | 🟢 Declared substrate contract (ADR-022, ADR-024). |
| Read-only observation semantics (no state mutation on read) | 🟢 Verified — G5/OB: `GET /nodos`, `GET /telemetry` are zero-side-effect (ZOM, ADR-025 #2). |
| Ulpia client application | 🔵 Roadmap — no UI code in this repository (zero rendering logic, PROJECT_IDENTITY non-goal). |
