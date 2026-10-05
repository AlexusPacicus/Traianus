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

**Resultado (2026-10-03, `data/math/P1_result.json`, commit `64e3450`; registro `docs/methodology/instrument-audit/P1.md`, revisión 7):** válido; `holds = false`, la hipótesis no se sostiene.

| | aciertos motor | aciertos BM25 | (a) contra el azar | (b) McNemar contra BM25 |
|---|---|---|---|---|
| k = 5 | 4 de 18 | 1 | p ≈ 2,1·10⁻⁴, pasa | b = 3, c = 0, p = 1/8, falla |
| k = 1 | 2 de 18 | 1 | p ≈ 1,7·10⁻³, pasa | b = 1, c = 0, p = 1/2, falla |

(b) falla porque hubo pocas discrepancias. Con la regla fijada, (b) necesitaba al menos 5, todas a favor del motor. Frente a las predicciones: (a) pasa, como esperaban los dos; (b) a k = 5 falla, contra la del autor; (b) a k = 1 falla, como esperaba Claude.

**Lectura ítem por ítem (autor y Claude, 2026-10-03; exploración posterior al resultado, no cambia `holds`).** Para cada ítem se separan tres causas: la prosa del autor (P), la etiqueta esperada (E) y el texto del corpus tras pasar las fórmulas a palabras (C). Las causas son la lectura acordada por el autor y Claude, ítem por ítem. El puesto es el del mejor enunciado esperado entre los 342 (1 = el más cercano).

| ítem | motor | BM25 | causa principal | nota |
|---|---|---|---|---|
| 1 ĉ₁ | 47 | 147 | P + C | prosa de ancla y centroide; NV casi vacío |
| 2 P⊥ | **2** | 232 | acierto a k = 5 | describe la operación; la fórmula de GSP se perdió |
| 6 d_esc | 15 | 155 | P + C | «square» es un falso amigo en los dos brazos; fragmentos vacíos en el top del motor |
| 7 y | 16 | 136 | P | imagen geométrica sin el término «inner product» |
| 11 complemento ortogonal | 26 | 21 | E | «perpendicular» no existe en Beezer; NSM se elige por un rodeo |
| 12 núcleo | **4** | 27 | acierto a k = 5 | «gives zero» entra en la familia del espacio nulo |
| 13 vectores canónicos | 52 | 54 | C | la definición de SUV era la fórmula |
| 14 ortogonalidad | **1** | **1** | acierto doble | la prosa contiene «orthogonal» |
| 15 coeficiente de proyección | 69 | 214 | P | metáfora de la sombra; «size» es un falso amigo |
| 16 rango 1 | 58 | 27 | P | el concepto está en el nombre, no en la prosa |
| 17 forma por lotes | 17 | 143 | P | «the operation» sin especificar |
| 18 linealidad | 215 | 50 | P + C | caso particular de los polos; las dos propiedades de LT se perdieron |
| 21 384d | 6 | 13 | C | los tres fragmentos vacíos «Dimension of» lo empujan fuera del top 5 |
| 23 coordenadas en 8 ejes | 56 | 111 | P | «scattered on each axis» |
| 24 coseno | 21 | 46 | P | «similar» es un falso amigo en los dos brazos |
| 25 traspuesta | 119 | 99 | P | describe un paso del pipeline; «spectral» lleva a autovalores |
| 27 media | 6 | 16 | E | el motor pone LC (el mismo concepto, otro enunciado) en el puesto 4 |
| 28 distancia euclídea | **1** | 47 | acierto a k = 1 | paráfrasis estándar sin ninguna palabra compartida |

Lo que se repite:
* **BM25 casi nunca tuvo palabras con contenido.** projection, distance, perpendicular, angle, direction, axis, operator, average y energy no aparecen en ninguno de los 342 enunciados. Salvo en el ítem 14, BM25 ordenó por palabras funcionales o por falsos amigos («its», «much», «union», «left», el «2» de «Round 2»).
* **Pasar las fórmulas a nombres de macros vació enunciados clave:** NV, GSP, SUV, LT, TM e IP. Los esperados de 11 de los 18 ítems perdieron su contenido definitorio. Los tres fragmentos idénticos «Dimension of» entran en el top 5 del motor en los ítems 6, 21 y 22.
* **Si la única palabra técnica es «vector», el motor cae en las definiciones genéricas de vector** (ítems 1, 7, 15 y 23, y en las «ninguna» 3, 4, 5, 20 y 26).
* **La redacción pesa más que la etiqueta.** Con el mismo esperado, el motor coloca 11 → 26 y 12 → 4; 2 → 2 y 15 → 69; 7 → 16 y 23 → 56; y para NV, 28 → 1, 6 → 15 y 1 → 47.
* **Comparación por puestos, exploratoria:** el motor coloca el esperado mejor que BM25 en 13 ítems, peor en 4 (11, 16, 18 y 25) y empata en 1 (el 14). La mediana del puesto es 19 en el motor y 52 en BM25. Esta comparación no estaba en la regla y no decide nada.
* **Las 10 «ninguna»:** ningún brazo propone una traducción útil. La distancia al más cercano (mediana 1,118) no las separa de P (mediana 1,090). En los ítems 9, 10, 20 y 26 el concepto está en el nombre y no en la prosa, como en el 16.

**Preguntas abiertas para el piloto 2 (autor, 2026-10-03; sin decidir, cada una entra con su regla comprometida antes de cualquier vector):**
1. **Un corpus con más lenguaje natural.** La lectura lo apoya: el vocabulario del autor no está en Beezer. La física encajaría con sus metáforas, pero devolvería enunciados de física en lugar de matemáticos, y eso cambia el producto. Un corpus mayor también añade competidores al esperado.
2. **Recuperar las fórmulas.** El corpus ya es reconstruible byte a byte (texto con marcadores y tabla de fórmulas), pero el modelo necesita frases. Una opción es pasar cada fórmula a lenguaje con reglas deterministas, no con generación. Claude citó de memoria, sin verificar, los motores de lectura de fórmulas para accesibilidad (el Speech Rule Engine de MathJax). Cambiar el texto del corpus rompe la línea base de proveedor de arriba: el corpus nuevo es una línea base nueva.
3. **La prosa propia.** Es el caso de uso, no un defecto que corregir. Reescribirla mirando Beezer filtraría la respuesta en la pregunta. Lo legítimo es fijar antes de ver nada otra forma de escribir, por ejemplo cada definición en dos versiones (imagen y mecanismo) medidas por separado.
4. **Una vista para manipular dimensiones** puede ayudar al autor a escribir, pero cambia la entrada, no el motor. Construirla esperando que arregle la recuperación es un error (autor).
5. **Otro proveedor de embeddings.** Ya estaba previsto como línea base. Se cambia una cosa cada vez. Los 28 ítems ya están vistos: sirven de línea base, pero una confirmación necesita ítems nuevos escritos a ciegas.

### Línea base de proveedor: Qwen3-Embedding-0.6B (autor, 2026-10-03; exploración, comprometida antes de cualquier vector)

Primera aplicación de la línea base de proveedor de arriba. Los 28 ítems ya están vistos, así que es exploración etiquetada (METHODOLOGY, proporcionalidad): no confirma nada y no hay auditoría completa. La pregunta es si el modelo es el cuello de botella; se prueba primero el más fuerte que cabe en la envolvente.

* **Por qué este modelo (búsqueda del 2026-10-03, tarjetas y API de Hugging Face):** Apache 2.0; arquitectura `qwen3` nativa de transformers, sin `trust_remote_code`; 595,8M parámetros; salida de 1024 con entrenamiento MRL, que admite recortar a 32–1024. Descartados: `math-similarity/Bert-MLM_arXiv-MP-class_zbMath` (sin licencia declarada), `uw-math-ai/MathLeap-Qwen-8B` (8B y 4096 dimensiones, fuera de la envolvente; se descarga de un espejo anónimo) y `google/embeddinggemma-300m` (licencia Gemma y acceso restringido). Referencia externa: en MIRB (arXiv 2505.15585), tarea Informalized Mathlib4 Retrieval, BM25 31,5, bge-large-en-v1.5 42,0 y gte-Qwen2-1.5B-instruct 55,2 de nDCG@10; Qwen3 no aparece, el artículo es anterior.
* **Proveedor:** `Qwen/Qwen3-Embedding-0.6B` en la revisión `97b0c614be4d77ee51c0cef4e5f07c00f9eb65b3`, cargado sin red desde la caché local, en la cpu, en float32 forzado (los pesos vienen en bfloat16), con la implementación de atención fijada y registrada, un hilo y un texto por llamada. El pipeline es el del modelo: Transformer, último token, normalización.
* **Instrucción de consulta (autor, opción propia):** cada consulta se codifica como `Instruct: Given a description of a mathematical concept, retrieve the definition or theorem that states it\nQuery:` seguido de la prosa del ítem. Los fragmentos van sin instrucción. Queda fijada aquí y no se retoca mirando resultados.
* **Dos versiones, las dos comprometidas ahora:**
  * **1024:** la salida completa. Es el techo; no puede entrar en el motor, que trabaja en 384 (AGENTS 3.1).
  * **384:** las primeras 384 componentes de la salida float32 de 1024, renormalizadas en float64 por la comprobación de vectores de P1. Es la versión que podría entrar en el motor.
* **Todo lo demás, como en P1:** corpus, conjunto de prueba, tabla de macros, BM25 y su semilla, ε, las comprobaciones de rechazo y de validez, y la definición del puesto (el del mejor enunciado esperado entre los 342).
* **Brazo MiniLM:** se lee de `data/math/P1_result.json` (commit `64e3450`), verificado por su sha256; no se vuelve a ejecutar. Así comparten ítems, empates y puestos.
* **Lo que decide, por versión (autor):** Qwen3 coloca mejor que MiniLM si un test de Wilcoxon de rangos con signo, exacto y de una cola, da p < 0,05. Pares: los 18 ítems de P; diferencia d = puesto MiniLM − puesto Qwen3 (positiva si Qwen3 coloca mejor); las d = 0 se descartan; rangos de |d| con rangos medios en los empates; p exacto enumerando los 2ⁿ signos sobre esos rangos. Se decide por separado para 1024 y para 384, sin corrección por multiplicidad, declarado. Es la respuesta a la pregunta de arriba; no confirma nada sobre el producto.
* **Solo informe (no deciden):**
  * La regla de P1 por versión: (a) contra el azar y (b) McNemar contra BM25, a k = 5 y k = 1, y su `holds`, por continuidad.
  * McNemar exacto de una cola Qwen3 frente a MiniLM, a k = 5 y k = 1.
  * MRR, recall@10, recall@20 y mediana del puesto, en los tres brazos (MiniLM, Qwen3, BM25).
  * Consulta sin instrucción, en las dos versiones: los mismos vectores de fragmentos y las 28 consultas sin el prefijo. Dice si la instrucción aporta; no sirve para elegir instrucción.
  * Separación entre P y «ninguna», dentro de cada modelo: AUC = probabilidad de que la distancia al fragmento más cercano de un ítem de P sea menor que la de un ítem «ninguna», los empates cuentan 1/2. Para MiniLM, con las distancias guardadas en `P1_result.json`. Se compara el AUC, no las distancias, porque la escala del coseno cambia de un modelo a otro.
  * Latencia por texto (p50 y p95) y memoria máxima del proceso, medidas, en un fichero aparte, porque los tiempos no son reproducibles byte a byte.
  * Desglose por esperado vaciado: los 11 ítems cuyo esperado es NV, GSP, SUV, LT, TM o IP (1, 2, 6, 7, 13, 15, 18, 23, 24, 25 y 28) frente a los 7 restantes (11, 12, 14, 16, 17, 21 y 27). La etiqueta viene de la lectura de P1, posterior a su resultado, y por eso solo informa.
  * Aciertos y puestos ítem por ítem frente a MiniLM, y los bloques de solo informe de P1.
* **Ficheros:** los resultados van a ficheros aparte; `P1_result.json` y el script de P1 no cambian de comportamiento.
* **Coste esperado:** unos 1,2 GB en disco y unos 3 GB de RAM; la latencia por texto, estimada sin medir, entre 30 y 50 veces la de MiniLM.

**Predicciones antes de cualquier vector (2026-10-04, no deciden nada):**
* **Autor:** el Wilcoxon pasa en las dos versiones, pero con poca diferencia. Aciertos a k = 5: 1 o 2 más que MiniLM (de 4 a 5 o 6); entran en el top 5 los que MiniLM dejó justo fuera, en el puesto 6 (ítems 21 y 27), y quizá alguno que quedó más abajo.
* **Claude (a ojo, sin cálculo):** Wilcoxon a 1024 pasa (65–70 %), a 384 pasa (55–60 %): los puestos mejoran en general aunque haya pocos aciertos nuevos. Aciertos a k = 5 entre 6 y 8 de 18; la regla de P1 contra BM25 entera, 10–15 %. La mejora se concentra en los 7 no vaciados; en los 11 vaciados, poca. AUC P frente a «ninguna» entre 0,5 y 0,65 en los dos modelos. La instrucción mueve la mediana del puesto uno o dos puestos.

**Resultado (2026-10-05; script `6bc35ea`, resultado `78cb722`).** Válido en las dos versiones: vectores, alineación y BM25 igual al guardado en los 28 ítems; ningún texto truncado. Una segunda ejecución dio un fichero idéntico byte a byte. **El Wilcoxon falla en las dos versiones:**

| versión | n | ceros | W+ | W− | p | pasa |
|---|---|---|---|---|---|---|
| 1024 | 16 | 2 | 74 | 62 | 12653/32768 ≈ 0,386 | no |
| 384 | 16 | 2 | 72 | 64 | 6965/16384 ≈ 0,425 | no |

Los dos ceros son los ítems 14 y 28 (puesto 1 en los dos modelos). Frente a las predicciones: el Wilcoxon falla, contra las dos.

**Solo informe:**
* Aciertos a k = 5: 7 en las dos versiones (MiniLM 4, BM25 1); a k = 1: 3 (MiniLM 2). McNemar contra MiniLM a k = 5: b = 5 (ítems 1, 6, 7, 24, 27), c = 2 (2, 12), p = 29/128.
* La regla de P1 con Qwen3: pasa a k = 5 contra el azar y contra BM25 (6 a 0) y falla a k = 1 (2 a 0); `holds` = falso en las dos versiones.
* MRR 0,192 (MiniLM), 0,274 (1024), 0,285 (384); mediana del puesto 19, 17 y 12,5; recall@10 0,33, 0,39 y 0,50; recall@20 0,50, 0,61 y 0,56.
* AUC P frente a «ninguna»: 0,567 (MiniLM), 0,700 (1024), 0,689 (384).
* Sin instrucción: 6 aciertos a k = 5 y mediana 22 (1024) y 23,5 (384).
* Desglose: en los 11 vaciados, aciertos a k = 5 de 2 a 5 y mediana de 47 a 14 (1024); en los 7 no vaciados, aciertos 2 y 2, mediana de 6 a 19 (1024) y 7 (384).
* Coste medido: p50 de 187 ms por fragmento y 189 ms por consulta; memoria máxima 2,06 GB.

**Lectura (autor y Claude, 2026-10-05; exploración posterior al resultado, no cambia la decisión):**
1. **Qwen3 no es claramente mejor; es distinto.** Sube 9 ítems y baja 7, con d entre −163 y +82; las caídas suman 403 puestos y las subidas 324. Con 18 ítems solo se detectaría una mejora grande y constante: el resultado es compatible con ninguna mejora y con una real.
2. **Recortar a 384 no cuesta nada medible aquí.** Las dos versiones dan los mismos aciertos y las métricas se reparten; nada compara 384 con 1024, así que no se afirma que 384 sea mejor.
3. **No hay evidencia de que el modelo sea el cuello de botella**, que no es lo mismo que «el modelo no es el problema»: es un solo modelo, una instrucción y 18 ítems, y los aciertos a k = 5 y el AUC suben.
4. **Los vaciados no son la barrera para Qwen3.** 8 de las 9 subidas son ítems vaciados y 5 de las 7 caídas son no vaciados. Hipótesis sin probar: la entrada poco convencional es la consulta (el vocabulario propio del autor), no el corpus. Las mayores caídas lo ilustran: el ítem 13 («a one in one position and zeros in the rest») va a enunciados sobre ceros (ZPZT, RREF); el 16 usa «anchor» y «operator» en un sentido que Beezer no tiene.

**Decisión del autor (2026-10-05):** la reescritura de la consulta con un LLM, si llega, es lo último que se prueba: mete generación en la entrada y no dejaría ver si funciona el motor. **Candidato para el piloto 2, sin decidir:** un glosario del autor, fijado y congelado antes de ejecutar, que traduzca sus términos a los habituales y se aplique por regla a la consulta. En estos 28 ítems sería exploración (ya se sabe qué ítems fallan); confirmaría solo en ítems nuevos. Siguen haciendo falta más ítems y la división desarrollo/prueba.

### La puerta del motor sobre P1 (autor, 2026-10-05; exploración, comprometida antes de calcular ningún σ²)

P1 y la línea base de Qwen3 no pasaron por el estado de Traianus: solo usaron el encoder y ε, y ordenaron en el script. Esta es la primera medida del producto a través del motor. Se cambia una sola cosa respecto a P1: los candidatos son los que deja pasar la puerta C1. Los 28 ítems ya están vistos, así que es exploración: no confirma nada.

* **Pregunta.** ¿Restringir los candidatos a los fragmentos que la puerta consolida mejora el puesto del enunciado esperado, más que restringirlos al azar al mismo tamaño?
* **Lo que mide la puerta (código, no hipótesis).** σ² de un fragmento es la varianza de sus 8 proyecciones sobre B_0 (`traianus/governance/gate.py`). θ_dyn es la media de las varianzas de las proyecciones cruzadas entre los ejes de B_0 (`traianus/geometry/observables.py`), un número fijo de la base que no depende del corpus.
* **Vía.**
  * Base nueva con `traianus-bootstrap` (B_0 `PROSTHETIC_NSM_V1`).
  * Los 342 fragmentos entran por `/ingesta/vector`, en el proceso y sin servidor, con el vector MiniLM de P1 y su `acro` como etiqueta. Esta vía siempre deja `incubating`, porque evalúa la puerta con la clave ética en falso.
  * Después, cada fragmento pasa por `/nodos/{id}/consolidar` con su texto y la clave ética en verdadero.
* **Clave ética (autor): aprobación por fuente.** El autor aprueba Beezer entero como fuente, no fragmento a fragmento, porque conoce los enunciados esperados y aprobar uno a uno filtraría la respuesta. Por tanto, consolidado ⟺ σ² ≥ θ_dyn. Se declara que esta aprobación no es un HITL por fragmento.
* **Consulta.** Se codifica como en P1 y no se escribe en la base. El ranking es el de P1 (producto escalar, mismas claves de desempate), solo sobre los nodos cuya última revisión es `consolidated`, leídos en solo lectura. El endpoint de observación queda fuera: sería una segunda variable.
* **Puesto (autor).** Es el del mejor enunciado esperado que sobrevive, entre los candidatos. Si no sobrevive ninguno, el puesto es 343: fallo, y el peor puesto posible sobre el corpus entero.
* **BM25 (autor):** sobre el corpus entero, como en P1.
* **Validez.** Si falla cualquiera de estas comprobaciones, `valid = false` y no hay decisión:
  * Los vectores de las dos revisiones de cada nodo son idénticos byte a byte al vector enviado.
  * El ranking sobre los 342 nodos del motor, sin filtro, reproduce el puesto guardado en `P1_result.json` en los 28 ítems.
  * BM25 recalculado es igual al guardado, como en la línea base de Qwen3.
  * Las filas de `manifold_nodes` son idénticas antes y después de las consultas (R2).
* **No aplica.** Si la puerta deja pasar 0 o los 342 fragmentos, no hay nada que comparar: el resultado es «no aplica» y no se decide nada.
* **Lo que decide (autor, regla (b)).** La puerta mejora la recuperación solo si se cumplen las dos condiciones:
  1. **Wilcoxon contra P1.** Test de rangos con signo, exacto y de una cola, como en la línea base de Qwen3. Pares: los 18 ítems de P. Diferencia: d = puesto P1 − puesto con puerta. Los ceros se descartan y los empates llevan rangos medios. Pasa si p < 0,05. El brazo P1 se lee de `P1_result.json`, verificado por su sha256.
  2. **Control de subconjuntos al azar.** Se sortean 10 000 subconjuntos uniformes de los 342 fragmentos, del mismo tamaño que el que deja pasar la puerta, con semilla 20261005. Cada sorteo se puntúa con las mismas reglas (puesto, 343, Wilcoxon contra P1). El estadístico es el p exacto del Wilcoxon, porque W+ no es comparable cuando cambia el número de ceros. p_azar = (1 + #{p_sorteo ≤ p_puerta}) / 10 001, y la condición pasa si p_azar < 0,05.
  * No hay corrección por multiplicidad, y se declara.
* **Por qué hace falta el control.** Quitar candidatos solo puede mejorar el puesto de un esperado que sobrevive. Sin el control, un Wilcoxon que pasa no distingue «la puerta elige» de «hay menos competidores».
* **Solo informe (no deciden):**
  * Cuántos fragmentos pasan y θ_dyn.
  * Qué enunciados esperados sobreviven.
  * Si pasan los tres «Dimension of».
  * La regla de P1 con la puerta, a k = 5 y k = 1, y su `holds`: el azar con los candidatos que quedan y las p_i de los esperados que sobreviven; McNemar contra BM25.
  * McNemar de la puerta contra P1.
  * MRR, recall@10, recall@20 y mediana del puesto.
  * AUC de P frente a «ninguna», con la distancia al candidato más cercano.
  * El desglose entre los 11 vaciados y los 7 no vaciados.
  * Los ítems uno por uno.
* **Ficheros.** El resultado va en `data/math/P1_gate_result.json`, aparte. `P1_result.json` y el script de P1 no cambian de comportamiento.

**Predicciones antes de calcular ningún σ² (2026-10-05, no deciden nada):**
* **Autor:** pasa la mitad de los fragmentos; el Wilcoxon falla; la puerta no gana al azar.
* **Claude (a ojo, sin cálculo):** no veo un mecanismo por el que σ² separe los enunciados con contenido de los vaciados: mide cuánto de desigual carga un vector sobre los ejes NSM. Fracción que pasa entre el 30 y el 60 %. El Wilcoxon falla (65–70 %), porque los esperados que caen en el 343 pesan más que lo que suben los que quedan. Las dos condiciones a la vez, entre un 5 y un 10 %. Los tres «Dimension of» corren la misma suerte (son el mismo vector).

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

## Línea física aparcada: ley de continua dirección

Apuntado 2026-10-04 (autor). Idea, sin redactar como hipótesis; entra por la puerta de líneas físicas de `docs/methodology/METHODOLOGY.md` como el resto.

* **Ley.** La continuidad de una entidad es continuidad de dirección de su trayectoria.
* **Trayectoria.** Los caminos más cortos sobre la base de la espiral (`docs/relational-bridges/RELATIONAL_BRIDGES.md` §24), desde todas las notas a la vez; continuidad = coseno entre pasos consecutivos.
* **Consecuencia para el postulado tiempo–fricción.** El tiempo de una ruta sería su giro acumulado, no su longitud.
* **Subdirecciones (autor).** Todas las descomposiciones de la dirección superior en subespacios a la vez, que se deforman en conjunto.
* **Ortogonalidad (autor, ley).** Toda descomposición en subespacios es ortogonal, respecto al producto euclídeo en 384D. Con ella las subdirecciones de Δ forman exactamente la esfera de diámetro [0, Δ] (Tales); cada partición en V y V⊥ es un diámetro, y la familia es continua si lo es Δ. Es un teorema, no una medida: va al archivo de derivaciones con su test. Familias admisibles: solo ortogonales (las celdas no lo son sin ortogonalizar; B_0 lo es solo si B_0 B_0ᵀ = I, comprobación aparcada que pasa a ser condición previa).
* **Representaciones (autor).** Las formas de representar la dirección superior son todas a la vez; cada una es y no es: P_V Δ es la parte de Δ en V y su complemento P_{V⊥} Δ es su antípoda en la esfera de Tales, de modo que las dos juntas dan Δ. Misma forma que la capa de proyección de Ulpia sobre Traianus (un estado, todas sus observaciones, ninguna lo altera), pero solo para las observaciones que son proyecciones ortogonales lineales; la perspectiva y las polares quedan como vistas para mostrar. Pendiente: comprobar qué proyecciones de Ulpia lo son.
* **Contenido empírico posible.** Solo si B_0 sale privilegiada frente a subespacios al azar de la misma dimensión.
* **Pendiente.** Control de circularidad (los caminos más cortos en un grafo de proximidad tienden a ser rectos; decide un control en el mismo grafo); dependencia del proveedor; puerta de líneas físicas.
* **Relacionada.** «Operaciones como dirección», las cuotas espectrales normalizadas y Ética II, Lemas 4–7 (cita sin verificar).

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
