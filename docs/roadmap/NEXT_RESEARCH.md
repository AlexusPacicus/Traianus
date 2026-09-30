# NEXT_RESEARCH.md

> **Research backlog after the initial Traianus Proof of Concept.**
>
> This document intentionally contains exploratory research directions that are **outside the current scope of Traianus**. None of the hypotheses described here are required for the current Proof of Concept or the NLnet proposal. They are preserved as future research questions.

---

# Purpose

Traianus currently investigates whether spatial state governance can be implemented as an independent deterministic computational layer.

During the development of the architecture, additional questions emerged regarding the nature of geometric structures, observation and projection. These questions constitute a separate research programme and are intentionally postponed until the completion of the current roadmap.

---

# Research Direction A — Observation as Projection

Current systems often confuse an internal state with its representation.

An alternative hypothesis is that every observable representation corresponds to a projection of an underlying geometric state rather than to the state itself.

Open questions:

* Which structural properties survive projection?
* Which properties are necessarily lost?
* Can different projections preserve different invariants?
* Is there an optimal projection for a given task?

---

# Research Direction B — The Geometry of Observation

Rather than studying representations, investigate the space of possible observations.

Hypothesis:

> A geometric structure may admit multiple valid observations without altering the underlying state.

Research questions:

* How should an observation be formally defined?
* Which transformations preserve structural invariants?
* Can observations themselves possess a geometry?

---

# Research Direction C — Structural Primitives

Current computational systems primarily manipulate points, vectors or embeddings.

Future work may investigate whether higher-order geometric structures constitute the true computational primitives.

Possible candidates include:

* vertices;
* edges;
* higher-dimensional cells;
* topological relations;
* incidence structures.

Open question:

> What is the minimal structural description required to determine an entire geometric object?

---

# Research Direction D — Projection without Structural Loss

Traianus preserves the complete computational state internally.

Representations shown to users necessarily expose only a subset of that state.

Future work will investigate whether multiple complementary projections can preserve different structural invariants while remaining faithful to the same underlying geometry.

---

# Research Direction E — Ulpia: Spatial Observation Framework

Ulpia is the read-only observation framework over the Traianus substrate. Its purpose is not to construct the geometric state maintained by Traianus, but to investigate how such structures may be observed, projected, analysed and characterized once they already exist.

Traianus and Ulpia therefore address different computational questions:

* **Traianus:** deterministic spatial governance.
* **Ulpia:** mathematical theory of observation over geometric computational states.

## The Observation Operator

Observation is formalized as a **read-only projective projection**:

$$O_n = P_\theta(S_n)$$

where the projection $P_\theta$ over the spatial state $S_n$ guarantees **no-interference** with the underlying geometric state. Ulpia observes and projects; it never mutates.

## Three-Layer Model

```
[ Ingress | Substrate | Observation ]
```

* **Ingress:** sensory input and text ingestion (representation layer).
* **Substrate:** the deterministic Traianus state engine $S_n$ (the only layer that owns state transitions).
* **Observation:** the read-only perspective-projection layer (Ulpia).

## Nuclear Invariants

* **Perspective Non-Interference Oracle:** observing or projecting $S_n$ produces zero side effects on the state engine.
* **Local Impact Isolation:** interactions over localized projections are bounded by $\epsilon$-adjacency and do not propagate beyond their local neighborhood.
* **Dual-Key (Ethical Key via HITL observation layer):** the ethical key is delivered through the observation layer by an explicit Human-In-The-Loop operator intervention (`revision_milestone = 1`), rather than by the probabilistic engine.

## Guiding Principle

The following distinction must remain explicit throughout future development:

> Representation is not the geometric state.
> Observation ($O_n = P_\theta(S_n)$) is not the geometric state.
> Perspective projection does not modify the underlying geometric state.

---

# Research Programme — Risk Matrix

The following risks govern investment in the research directions above. Severity follows the audit legend (🟡 Medium / 🟠 High / 🔴 Critical). The `Roadmap` column maps each risk to the Work Package (see `docs/STATUS.md` §C) or research direction that must absorb it.

| Risk | Severity | Affected Direction | Mitigation | Roadmap |
|---|---|---|---|---|
| State/representation conflation leaks into the substrate | 🟠 High | A, B, E | Enforce the guiding principle structurally: observation lives strictly outside `traianus/`; projections are pure read-only functions | WPs 1–4 |
| Projection introduces non-reproducible drift | 🟡 Medium | A, D | Require deterministic projection operators parameterized by $\theta$ with fixed seed; bypass via exact re-projection on cross-epoch comparison | WP1 |
| Simplicial/homological primitives exceed the ≤8 GB RAM envelope | 🟡 Medium | C, WP2 | Defer $K_n$ faces to WP2; benchmark memory against the fixed hardware envelope before enabling | WP2 |
| Ethical-Key gating degenerates to probabilistic auto-approval | 🟠 High | E, RH-1 | Keep Dual-Key: ethical key delivered exclusively via HITL observation layer (`revision_milestone = 1`) | WP1, RH-1 |
| Observation layer mutates `data_plane` / `manifold_nodes` | 🔴 Critical | E | Physical `mode=ro` connections (zero mutation over substrate tables); append-only invariants per AGENTS §4 | RH-1 |

---

# Research Programme — Benchmarking

Validation of the research programme requires falsifiable experiments with measured baselines. Each direction must reach GREEN only against an explicit benchmark:

* **Observation Cost Benchmark:** projected observation time and memory per projection of $S_n$, measured against the WP4 ≤8 GB envelope and the known SQLite WAL baseline (<1 ms I/O, `docs/STATUS.md` §Known Limitations M2).
* **Non-Interference Probe:** a deterministic suite asserting that any sequence of observations $O_n = P_\theta(S_n)$ produces byte-identical substrate state `manifold_nodes`/`data_plane`.
* **Drift Fidelity Metric:** cross-epoch re-projection fidelity ($\|P_{\theta}(S_n) - \mathrm{proj}(\cdot)\|$) must be recomputed only under a single active `epoch_provenance = 'PROSTHETIC_NSM_V1'`; no cross-epoch comparison without re-projection (AGENTS §3.3).
* **Simplicial Memory Probe / Persistent Homology:** WP2 filtration complexity scaled against the RAM envelope before any native GUDHI integration is accepted.
* **EAS-01 Continuation:** every new observation operator must reproduce the coupling result (governance-rule invariance under representation replacement, `docs/STATUS.md` §B seq 18–20) before entering Experimental status.

Until a direction clears its benchmark, it remains **RESEARCH / FUTURE ROADMAP** and outside Core/Control Plane.

---

# Research Direction F — Second Contrast Manifold (math-only + Faraday intuition)

Apuntado 2026-09-28, fuera de scope v1.0.0. Futuro banco de técnicas/fallos tipo bridges sobre un segundo manifold congelado, espejo de `data/spinoza/` (`PROVENANCE.md` + builder offline + `{label -> chunk}` + `telemetry/` versionada). Vive solo en `data/math/ + tools/experiments/tooling/ + docs/`, nunca en `traianus/` (AGENTS §3.2).

* **F1 math-only, dos vetas:** álgebra (definición/teorema/demostración) y geometría multidimensional (p. ej. Manning, cuatro dimensiones). Filtro por definir tipo `ONE STATEMENT = ONE CHUNK`, fuera prosa histórica y notas editoriales.
* **F2 intuición física:** Faraday (*Experimental Researches*, líneas de fuerza) como veta de intuición, no matemática: no pasa el filtro math-only y no se mezcla con F1. Su formalización (Maxwell/Love/elasticidad) iría en F1 si se necesita.
* **Uso:** re-correr la batería ya medida (E_n, `tools/analyze_bridges.py`, puerta de tensión §22, Sammon, rescue) sobre el manifold matemático para ver qué generaliza y dónde falla vs. Spinoza. Sin entrada en registro sin hipótesis + refutadores (`docs/methodology/METHODOLOGY.md` Explore).
* **Por decidir:** fuentes exactas y dominio público, regla lossless del filtro, etiquetas neutras `MATH_*`.

---

# Research Direction G — Spatial Math Workbench (post-v1.0.0 product)

Apuntado 2026-09-28, fuera de scope v1.0.0. Herramienta cliente de Traianus + Ulpia para hacer matemáticas a nivel espacial: cambiar de plano, bajar a subespacio (gruesa → fina, `RELATIONAL_BRIDGES.md` §9/§15-16), comparar proyecciones sobre el mismo estado congelado. Vive fuera de `traianus/` (cliente, junto a RefApp-01). Usa F como banco: Spinoza + `data/math/` para probar qué vistas generalizan y dónde fallan. Sin hipótesis + refutadores no entra en registro.

---

# Status

This document records research hypotheses only.

No claim contained here is considered validated.

Future work must provide:

* formal mathematical definitions;
* computational models;
* falsifiable hypotheses;
* experimental validation.

Until then, these ideas remain intentionally outside the Traianus core architecture.
