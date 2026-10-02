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

## Reencuadre (autor, 2026-09-30): F es también el corpus del producto v1

El texto de arriba se conserva como pregunta anterior. F sigue siendo banco, y además es el corpus del primer producto.

* **Uso del producto:** herramienta del autor para traducir sus definiciones matemáticas a lenguaje natural: a qué enunciado del corpus se acercan y qué opciones relacionadas hay. Devuelve enunciados reales con su etiqueta y sus citas, de forma determinista; no genera texto. Primer usuario: el autor, empezando por las definiciones de Polar Projector.
* **Corpus:** el criterio pasa a ser cubrir el área de las definiciones del autor. Fuentes y licencia, por decidir fuente a fuente.
* **Fórmulas aparte (autor):** cada vector del corpus es lenguaje natural; las fórmulas viven en una base aparte, en la que el vector o sus combinaciones (p. ej. dos técnicas que dan una nueva, o una derivada) quedan definidos por su fórmula. Es la regla sin pérdida del filtro: un marcador en el texto y la fórmula en su tabla, con el enunciado original reconstruible byte a byte (un test). La base vive en `data/math/` o en el cliente, nunca en `traianus/` (AGENTS §3.2).
* **Consulta sin escritura (autor):** la definición del autor se observa, no se ingiere. El motor calcula su vector y sus relaciones virtuales (ε 0,8 y la vecina más próxima; sin árbol, que cambiaría al meter el punto) y no escribe nada; el cliente calcula el reparto T centrado en ella, como el bloque «Load». Hace falta un endpoint de observación en `traianus/`, genérico (texto → vector y vecinas), sin conceptos de dominio. Refutador de no interferencia: la base queda byte a byte idéntica antes y después (R2). La tensión puede mostrarse solo como descripción (cuánto tira la carga frente a hacia dónde), sin decidir nada.
* **Por decidir:** si la entrada es la fórmula (búsqueda fórmula → fórmula en la base aparte, y de ahí a los vectores) o un borrador verbal; si las definiciones que el autor quiera conservar entran como nodos propios, marcados y separados del corpus.

## Piloto 1: traducción dentro del área, solo Beezer (autor, 2026-10-01)

Pasos 0 y 1 de `docs/methodology/METHODOLOGY.md`, comprometidos antes de construir el corpus. Fuente y reglas de derivación: `data/math/PROVENANCE.md`.

**0. Problema.** Para una definición del autor escrita en prosa, ¿encuentra el motor el enunciado de Beezer que la formaliza? Fuera: otras ramas (piloto 2, Beezer y un trozo de ProofWiki, con su propia regla), la búsqueda por fórmula, el endpoint de observación y la interfaz.

**1. Hipótesis.** Para las definiciones del autor que tienen enunciado correspondiente en Beezer, la etiqueta esperada está entre las k vecinas más cercanas más a menudo que al azar y más a menudo que con una búsqueda léxica.
* **Corpus:** definiciones y teoremas de Beezer en el commit fijado, un enunciado = un fragmento (título y enunciado; cada fórmula, en palabras según la tabla de macros de `data/math/macro_words.json`), vectorizados con el proveedor actual (MiniLM-L6-v2).
* **Entrada:** borrador verbal del autor, sin fórmulas.
* **k = 5 y k = 1 (autor).** Las dos deciden: la hipótesis se sostiene solo si pasa en las dos.
* **Conjunto de prueba (autor, comprometido antes de cualquier vectorización del corpus):** N definiciones propias en borrador verbal; para cada una, las `acro` de Beezer que debería encontrar, o «ninguna». Se escribe leyendo el libro, sin mirar nunca vecinas del motor. P son las que tienen `acro`; las «ninguna», el resto.
  * **Quién etiqueta (autor, opción B):** la prosa es del autor, escrita antes de mirar Beezer; las `acro` las propone Claude con el enunciado y la razón, y el autor lee cada enunciado y la acepta o la rechaza. Se registra como «propuesta por Claude, aceptada por el autor». Es independiente del motor porque se fija antes de que exista ningún vector del corpus.
  * **Tamaño:** el test de McNemar de una cola da p = 0,5^b con b discordantes, todos a favor del motor, así que hacen falta al menos 5 a k = 1 para bajar de 0,05. Las 7 definiciones de Polar Projector dan 3 o 4 positivos, lo que hace imposible que la hipótesis se sostenga; el autor añade conceptos propios de Traianus hasta unos 20 positivos o más.
* **Medida:** aciertos en P a cada k, es decir, definiciones de P con alguna `acro` esperada entre sus k vecinas.
* **Azar:** orden uniforme de los N_c fragmentos; para una definición con m `acro` esperadas, p_i = 1 − C(N_c − m, k) / C(N_c, k). Los aciertos bajo el azar siguen una Poisson-binomial de las p_i.
* **Línea base léxica (decide, autor):** BM25 con sus valores habituales (k1 = 1,2, b = 0,75) sobre el mismo texto sin fórmulas; los empates se rompen con un sorteo de semilla comprometida antes del run.
* **Regla de decisión:** a cada k, (a) P(aciertos ≥ observados | azar) < 0,05, test exacto de una cola, y (b) el motor gana a BM25 en las definiciones de P donde discrepan, test exacto de McNemar de una cola, < 0,05. La hipótesis se sostiene solo si (a) y (b) se cumplen a k = 5 y a k = 1.
* **Refutadores:** a algún k, aciertos no superiores al azar, o no superiores a BM25. Incluye el caso de texto vacío: sin fórmulas, la prosa de un enunciado se reduce casi al título, y si eso deja el vector sin contenido, el piloto falla aquí.

**Solo informe (no deciden, salvo que el autor lo decida):**
* **«Ninguna»:** distancia a la vecina más próxima, frente a la de P.
* **Prosa sin fórmulas:** distribución de palabras por fragmento.
* **Grafo de citas:** fracción de las citas de Beezer cuyos extremos están a distancia ≤ 0,8 (ε de `/relations`), y la misma fracción en la Ética. No es comparable uno a uno: la Ética está en frases y Beezer en enunciados; se declara al informar.

**Línea base de proveedor (autor):** el conjunto de prueba, el corpus, la tabla de macros y esta regla quedan congelados como la comparación para cualquier otro proveedor que se evalúe más adelante. Solo cambia el proveedor; se compara por aciertos de etiqueta a k = 5 y k = 1, no por vectores, así que no hace falta reproyectar entre épocas (AGENTS 3.3). Cambiar cualquier otra pieza rompe la comparación, y cada nuevo proveedor entra con su propia regla comprometida antes.

**Predicciones antes de cualquier vector (2026-10-02, no deciden nada; sirven para calibrar la intuición contra el resultado):**
* **Autor:** (a) pasa; (b) a k = 5 pasa, sin certeza; (b) a k = 1, más dudas.
* **Claude:** (a) pasa a k = 5 y probablemente a k = 1; (b) a k = 5, dudosa; (b) a k = 1, probablemente falla: los ítems con palabras técnicas los acierta también BM25, los de metáfora probablemente ninguno, y solo cuentan las paráfrasis puras. Las cuatro a la vez, entre un 25 y un 35 %, estimado a ojo, sin cálculo.

**Orden:** (1) este texto y `PROVENANCE.md`; (2) el conjunto de prueba del autor; (3) contrato del builder y su test sin pérdida (engine-implementer); (4) registro de auditoría del instrumento y revisión ciega; (5) script, primera ejecución y resultado.

## Línea física aparcada: operaciones como dirección

Aparcada hasta pasar los tres filtros de `docs/methodology/METHODOLOGY.md` (puerta de líneas físicas). Filtros 1 y 2 redactados; el 3, pendiente de verificar las citas.

**1. Hipótesis.** Una operación matemática (derivar, combinar dos técnicas) corresponde a una dirección en el espacio: los desplazamientos X → op(X) están más alineados de lo que dan dos referencias.
* **Criterio no circular:** qué deriva de qué lo fija la base de fórmulas, no los embeddings ni el corpus.
* **Nulo del autor:** dirección nula y carga igual a la medida. Cada desplazamiento conserva su longitud medida y su dirección se sortea uniforme en la esfera de 384D.
* **Control de pares al azar:** desplazamientos entre pares al azar del mismo corpus, con la misma carga.
* **Regla de decisión (autor, opción b):** una dirección se afirma solo si se superan los dos. La misma regla rige la etiqueta de dirección en la consulta sin escritura.
* **Refutadores:** alineación no superior al nulo del autor; alineación no superior a la de pares al azar.
* **Antes del run:** estadístico (candidato: longitud media resultante de los desplazamientos unitarios), número de sorteos y semilla, comprometidos.

**2. Crítica adversarial.**
* **La combinación como suma no prueba composición.** Con A, B y C unitarios y A ≠ −B, $\cos(C, (A+B)/\|A+B\|) = (C\cdot A + C\cdot B)/\sqrt{2 + 2\,A\cdot B}$: queda fijada por las similitudes por pares, así que «la combinación cae cerca de la derivada» equivale a «la derivada se parece a sus dos padres». Solo la versión como dirección tiene contenido. La igualdad irá a un archivo de derivaciones con su test.
* **Anisotropía:** en MiniLM dos frases sin relación suelen tener coseno positivo, y cualquier conjunto de desplazamientos puede superar el nulo isótropo. Por eso el control de pares al azar decide.
* **Rango con pocas relaciones:** con k relaciones, T tiene rango ≤ k y nunca sale isótropo. El nulo son k vectores sorteados con sus longitudes, no $(\mathrm{tr}\,T/d)\,I$.
* **Plantilla léxica (propuesto, sin decidir):** si op(X) repite X y añade siempre las mismas palabras («la derivada de…»), el desplazamiento puede ser la dirección de esas palabras y no de la operación. Un control candidato: la misma plantilla sobre X ajenos a la operación. Según la regla del autor, no decide salvo que el autor lo decida.

**3. Búsqueda externa.** Citado de memoria, sin verificar: webfetch y websearch están denegados por el perímetro.
* Desplazamientos como relaciones: Mikolov, Yih y Zweig (2013). Levy y Goldberg (2014) muestran que 3CosAdd se descompone en similitudes, lo mismo que la igualdad del filtro 2. Críticas a la evaluación por analogías: Linzen (2016); Rogers, Drozd y Li (2017).
* Anisotropía de los embeddings: Mu y Viswanath (2018); Ethayarajh (2019).
* Uniformidad en la esfera: test de Rayleigh (Mardia y Jupp, *Directional Statistics*).
* Recuperación matemática, para el producto: Approach0, la búsqueda por fórmula de zbMATH, y buscadores de mathlib en lenguaje natural (Moogle, LeanSearch).

---

## Línea de física: de fuerzas a campos de tensión (aparcada hasta acabar el piloto)

Apuntado 2026-10-02, fuera del piloto y fuera de `traianus/`. Vive en Tomo 0 / §5 del paper de Polar Projector, nunca en el conjunto de prueba (Beezer no trae fricción; ese lenguaje cae a «ninguna» por diseño).

* **Tesis.** Pasar de fuerzas a campos de tensión no elimina la fricción; la convierte de fuerza externa en disipación intrínseca (residuo, no rozamiento).
* **Diccionario.** Fricción 1D = pérdida de proyección; colisión = evento local de curvatura/disipación; fuerzas entre centroides = gradientes del campo.
* **Ancla técnica.** `E_esc` como fricción del marco (la definición 6 del conjunto de prueba lo dice sin la palabra).
* **Puerta.** Entra por la puerta de líneas físicas de `docs/methodology/METHODOLOGY.md` como el resto: hipótesis + refutadores + búsqueda externa antes de definiciones.
* **Media en el hueco (autor, 2026-10-02).** La media minimiza la distancia cuadrática total, pero en un grupo bimodal cae en tierra de nadie: llegar desde ahí a cualquier miembro real cuesta energía en todas direcciones. Óptima en total, pésima en local (aviso de §5 del paper; la Proposición 2 existe para ese caso).
* **Estado.** Idea registrada, sin redactar.

---

# Research Direction G — Spatial Math Workbench (post-v1.0.0 product)

Apuntado 2026-09-28, fuera de scope v1.0.0. Herramienta cliente de Traianus + Ulpia para hacer matemáticas a nivel espacial: cambiar de plano, bajar a subespacio (gruesa → fina, `RELATIONAL_BRIDGES.md` §9/§15-16), comparar proyecciones sobre el mismo estado congelado. Vive fuera de `traianus/` (cliente, junto a RefApp-01). Usa F como banco: Spinoza + `data/math/` para probar qué vistas generalizan y dónde fallan. Sin hipótesis + refutadores no entra en registro.

**Reencuadre (autor, 2026-09-30):** G es la v2 del producto de F. Pendiente: la bajada a subespacio se disparaba cuando la tensión salía no concluyente (§9), y la tensión como selector quedó archivada el 2026-09-29 (§23). La v2 necesita otro criterio para decidir cuándo bajar.

**Vista aparcada (autor, 2026-10-02):** cuotas espectrales normalizadas — tomar el total dispersado como 1 y repartirlo por eje, de modo que las 8 cuotas sumen el total. El motor guarda proyecciones crudas (`observables.py:90`); las cuotas serían cálculo de cliente como el bloque Load, no dato del sustrato. Fuera del piloto (usa dispersión cruda, def. 23a).

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
