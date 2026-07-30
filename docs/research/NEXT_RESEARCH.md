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

# Research Direction E — Ulpia

Ulpia is currently considered an independent mathematical programme.

Its purpose is not to construct the geometric state maintained by Traianus.

Instead, Ulpia investigates how such structures may be observed, projected, analysed and characterized once they already exist.

Traianus and Ulpia therefore address different computational questions:

* **Traianus:** deterministic spatial governance.
* **Ulpia:** mathematical theory of observation over geometric computational states.

---

## Guiding Principle

The following distinction should remain explicit throughout future development:

> Representation is not the geometric state.
> Observation ($O_n = P_\theta(S_n)$) is not the geometric state.
> Perspective projection does not modify the underlying geometric state.
> Traianus operates exclusively on the geometric state $S_n$ itself.

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