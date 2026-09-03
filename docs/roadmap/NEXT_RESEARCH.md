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

# Status

This document records research hypotheses only.

No claim contained here is considered validated.

Future work must provide:

* formal mathematical definitions;
* computational models;
* falsifiable hypotheses;
* experimental validation.

Until then, these ideas remain intentionally outside the Traianus core architecture.
