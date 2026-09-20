# Bitácora de desarrollo

Registro breve, append-only: fecha, qué se intentó, resultado, decisión.
No es un audit trail formal (eso vive en `docs/audit/AUDIT.md` y en la
tabla `audit_log`) — es memoria de proceso para no tener que releer
código ni transcripts un mes después. Entradas cortas a propósito: la
versión pesada de esto (20 registros con matrices de cumplimiento) se
intentó en agosto 2026 y se abandonó por peso conceptual sin aporte al
ejecutable real.

---

## 2026-09-10

**Contexto:** revisión de una exploración de investigación de agosto 2026
(`/Users/test/Documents/exploring/`) en busca de ideas vivas para probar
ahora.

**Se hizo:**
- Informe de ideas vivas/descartadas, cruzando `exploring/` contra el
  estado actual del repo (rama `feat/ulpia-webgl-renderer`).
- Skill `spectral-mathematician` creado (`docs/spectral-mathematician-skill`,
  `e03a9ad`) — cerró un hueco en AGENTS.md §6.5: el MCP `spectral-math-engine`
  estaba conectado sin ningún skill que documentara cuándo usarlo.
- Auditoría crítica del propio trabajo, con verificación empírica, no solo
  relectura. Encontrados y corregidos dos fallos reales:
  1. La mutación del skill nunca pasó por `boundary-validator` pese a que
     AGENTS.md §5.2 lo exige.
  2. El skill afirmaba una equivalencia falsa entre `calibrate_c1_threshold`
     (MCP, normaliza a coseno internamente) y `calibrate_critical_threshold()`
     (`traianus/geometry/observables.py:12`, dot product crudo, asume
     vectores ya L2-normalizados). Solo coinciden si el input ya está
     normalizado — no estaba documentado.
  Corregido en `f846350`, esta vez sí routeado por el gate antes de aplicar.
- Hook `PreToolUse` para forzar el gate en `Edit`/`Write` sobre rutas
  gobernadas (`traianus/`, `tests/`, `AGENTS.md`, `docs/specifications/`),
  reusando la tabla `audit_log` que el validator ya escribía en vez de
  inventar un mecanismo de recibo nuevo. Rama
  `feat/boundary-validator-enforcement-hook` (`12ffd85`), 16 tests nuevos,
  `pytest tests/security/` en verde (70 tests).

**Resultado:** ambas ramas locales, sin push, sin merge, apiladas sobre
`feat/ulpia-webgl-renderer`.

**Sin resolver / decisión pendiente:**
- El hook nunca se probó disparado por el harness real — solo se simuló
  invocando el script a mano con un payload sintético. No confirmado que
  el enforcement funcione en vivo.
- El alcance gobernado del hook excluye `.claude/skills/` — no cubre
  exactamente el tipo de edición que originó esta auditoría. Pendiente
  de decidir a propósito, no dejar como default silencioso.
- `window_seconds=900` sin validar contra fricción real de trabajo.
- Gap conocido: el hook no ata `target_file` al contenido realmente
  editado — un `EXECUTE_SAFE` de una propuesta trivial "cubre" cualquier
  edición al mismo archivo dentro de la ventana.
- Silent Denial (principio del spec de agosto) no está implementada en el
  `boundary-validator` actual — verificado empíricamente, no corregido.
- Doc-drift (AGENTS.md §6.5 vs. skills reales en disco) sigue siendo
  manual.

**Próximo paso (mañana, en orden):**
1. Verificar el hook en vivo, en una sesión nueva.
2. Decidir el alcance de `.claude/skills/` en el gate, a propósito.
3. Confirmar el schema real de stdin/exit-codes de `PreToolUse` contra la
   documentación oficial (no verificable hoy: `WebFetch` denegado en este
   proyecto).
4. Ajustar `window_seconds` según la fricción observada en (1).
5. Cola de siempre: Silent Denial, doc-drift automatizado, spike de WP1
   (base espectral dinámica), releer Direcciones A-D de
   `docs/roadmap/NEXT_RESEARCH.md` antes de tocar de nuevo el proyector
   polar.

---

## 2026-09-11

**Contexto:** retomar tras la sesión del 10. El trabajo de la noche (split
`prepare()`/`evaluate()` del proyector polar + paper + tooling) estaba sin
commitear, y el ledger seq 43 documentaba solo la mitad.

**Se hizo:**
- **Auditoría del working tree.** Encontrado que seq 43 describía únicamente
  el closed-form de `_canonical_u_perp`, cuando el árbol contenía además una
  extensión de API pública (`PolarFrame`, `prepare()`, `evaluate()`) y
  precondiciones nuevas que lanzan `ValueError`. El paper §3.1 ya publicaba
  cifras de una API que el ledger no registraba. Seq 43 reescrito antes de
  commitear.
- **Bound de SQLite revertido.** `test_sqlite_engine_concurrency.py` tenía el
  p99 relajado de 5 ms a 10 ms, sin justificar en ningún sitio (AGENTS §6.3).
  Medido en vez de asumido: 20/20 en verde a 5 ms, y suite completa también.
  Sin evidencia que lo sostuviera → descartado. Si vuelve a flaquear, que sea
  con un dato delante.
- **Frente polar cerrado:** 3 commits (código+tests, paper+tooling, ledger).
  Gates: 1087 passed / 5 deselected, ruff limpio, `mypy traianus/` limpio,
  coverage 90%.
- **Repo `polar-projector` extraído** en `/Users/test/Documents/NGI/polar-projector`,
  con historia git preservada vía `git-filter-repo` (202 → 6 commits, los 10
  ficheros del operador). Scaffolding propio: `pyproject.toml` (numpy y nada
  más), README, CI (3.11/3.12/3.13), LICENSE AGPL heredada.
  - `PolarFrame` ahora sí exportado — nunca lo estuvo en `traianus.geometry`
    pese a ser el tipo de retorno de `prepare()`.
  - Fixtures deterministas promovidos a `polar_projector.fixtures`: elimina el
    bootstrap de `sys.path` de las tools (el follow-up diferido en seq 41) en
    vez de replicarlo. `random_centroids` cae: sin llamantes en ningún repo.
  - Config de ruff explícita. Traianus depende de una config local implícita,
    así que su CI y la máquina de un colaborador pueden discrepar sobre qué
    reglas aplican — aquí está pinneada en el repo.
  - Verificado: 499 tests en 0.7 s, mypy y ruff limpios, coverage 100% sobre
    el operador, y §3.3 reproduce **18/18 celdas PASS** contra la tabla
    publicada. CI corre esa verificación en cada push.

**Resultado:** el paper es reproducible con `pip install numpy`, sin fastapi
ni torch. Repo local, 8 commits, sin remote.

**Sin resolver / decisión pendiente:**
- **Bloqueante para el siguiente paso:** se decidió que Traianus dependa del
  paquete (fuente única de verdad), pero eso exige que el repo sea resoluble
  — GitHub o PyPI. Hasta que exista remote, el swap no se puede hacer sin
  romper CI. Una path-dependency local funcionaría en la máquina y fallaría
  en Actions.
- Licencia: AGPL-3.0 heredada de Traianus. Para la implementación de
  referencia de un paper es restrictiva y desincentiva la adopción. Es
  reversible (autor único), pero conviene decidirlo a propósito.
- El paper sigue siendo espejo manual de Corca; §4 y §6 siguen en borrador.
- `random_centroids` es código muerto también en Traianus — limpiar allí.
- Higiene de Traianus pendiente: `.coverage` sin gitignorear, `compendio.md`
  suelto en la raíz, `CLAUDE.md` y `.mcp.json` sin trackear.
- **AGENTS §6.5 sigue siendo falso en git:** los cinco skills están
  trackeados en `.opencode/skills/`, pero en `.claude/skills/` solo
  `spectral-mathematician`. Los otros cuatro están en disco sin trackear.
- Cola del 10 intacta: verificar el hook en vivo, alcance de `.claude/skills/`
  en el gate, schema de `PreToolUse`, `window_seconds`.
- Siguiente bloque grande según lo hablado: modularización de la PKM.

---

## 2026-09-18

**Contexto:** tras el paper, pasar de «producir un paper» a un método reutilizable, y decidir entre
PoC de la PKM o papers de lo ya construido. Se eligió **PoC primero**: construir genera las
preguntas (ADR-026 salió de un bug real de render).

**Se hizo:**
- **Metodología incubada** en `docs/methodology/` (bucle 0–4, reglas de papers, instrumentación),
  con condición de salida: se muda a su repo cuando un segundo estudio complete el bucle.
- **Taxonomía fijada:** Traianus = orden implicado (motor), Ulpia = orden explicado (observación,
  O = P_θ(S)), RefApp-01 = el cliente PKM. `frontend/` es RefApp-01, mal etiquetado como Ulpia.
- **Seis documentos de NotebookLM contrastados con el código.** Buena parte ya estaba construida
  (ADR-025, símplex, corrector parabólico, contrato de 64 bytes) pero sin cablear; las cifras de
  titular no tenían respaldo (el Sammon real es 39,4 %, no 86,07 %).
- **PoC RefApp-01** en `frontend/POC.md`: 7 días (18–25), mapa 5D, perspectiva por nota, entrada de
  notas, refutadores R1–R5, registro, decisión del día 7 preregistrada.
- **Revisión ciega del instrumento** como skill (`instrument-audit`) y, tras enmendar AGENTS §6.1,
  como subagente de solo lectura (`instrument-auditor`). K6 y R4 **PASS en fase 1**, cinco rondas
  cada una: encontraron una fuga real (en R4 el eje y *es* el orden verdadero), un nulo no
  comparable, un umbral que se pasaba del 5 % y notas correlacionadas.
- **Contratos a nivel de bit** (`frontend/audits/contracts.md`): huellas SHA-256, dtypes, orden de
  bytes, streams PCG64, determinismo, integridad (nulos fuera; un bit cambiado debe detectarse),
  con traducción al español.
- **Derivaciones D1–D12 verificadas por código:** 30 tests con el `PolarProjector` real, D8 por
  enumeración exhaustiva, D9 con fracciones exactas, un caso negativo por derivación.
- **Prueba de humo** con SQLite aislado en scratch: la ingesta funciona; el mapa es una mancha de
  un color; no hay zoom ni clic; consolidar deja la nota en `incubating` (falla la llave
  topológica).

**Resultado:** ~25 commits en `docs/development-log`, todos de documentación, método y tests; ninguno
de producto. Las fichas y los contratos están listos para construir encima.

**Resuelto de la cola del 11:** `compendio.md` fuera de la raíz (movido a `~/Documents/NGI/`);
`.coverage` gitignoreado.

**Sin resolver / decisión pendiente:**
- **Ruta crítica en el motor:** la vista general usa un marco *por nodo* (no hay mapa común) y dos
  de los tres colores repiten la posición. Hacen falta el marco por época y `/spatial?anchor=`,
  en archivos que la sesión `traianus-2a` tiene sin commitear.
- Hueco de bits entre artefacto (codificado en lote) y motor (una nota a la vez): cerrado por
  decisión — cargar los vectores del artefacto de uno en uno por `/ingesta/vector` — pendiente
  de verificar que ese endpoint no altera los bits.
- Idea del autor, sin anotar en `POC.md`: **logs de pérdida relacional** en la carga nota a nota.
  Formulación propuesta: cuánto del estado final depende del orden de llegada; el grafo ε y los
  kNN finales son invariantes al orden por construcción y sirven de control.
- Ideas en exploración, fuera de la PoC: caras de un politopo de conceptos (proyección del
  7-símplex elegida por el usuario); lote frente a uno-en-uno.
- **Riesgo reconocido:** el día 1 de 7 se fue entero en método.

**Próximo paso (mañana, en orden):**
1. Recap con el autor; decidir la formulación de los logs de pérdida relacional.
2. Coordinar con `traianus-2a` el marco por época y `/spatial?anchor=`.
3. Script de K6 con TDD: tests de integridad → tests de derivaciones → código.
4. Paquete de revisión (ceguera por construcción), fase 2 con el subagente, ejecución.

---

## 2026-09-19

**Contexto:** día 2 de la PoC RefApp-01. Se partía de fichas K6 y R4 aprobadas en fase 1, sin
producto, y con el trabajo de motor de `traianus-2a` terminado pero sin commitear.

**Se hizo:**
- **Trabajo de `traianus-2a` commiteado** en dos commits separados (seguridad del hook,
  calibración del render). Al revisarlo: no resolvía el marco por nodo, solo escalaba x–y.
  `docs/development-log` tenía un test en rojo desde ayer que dependía de ese trabajo; se trajo
  el arreglo con cherry-pick.
- **Pérdida relacional por orden de llegada**, registrada como exploración tras leer el código:
  dentro de una época θ_dyn solo depende de la base y las aristas ε se recalculan al leer, así
  que la pérdida es nula por construcción. Corregida la afirmación contraria de `POC.md`.
- **AGENTS v1.7.0:** un segundo subagente, `instrument-implementer`, acotado (una rama, gate por
  fichero, sin datos reales, se para en un commit). Lección del gate: la ruta va en el argumento
  `target_file`; sin él, el hook deniega.
- **K6, implementado con tests primero por el subagente.** Encontró un error del contrato: el bit
  de signo nunca lo detecta la validación. Primera fase 2: CHANGES. Decisión del autor: B_s con
  columnas estandarizadas, porque la escala de una dimensión no dice nada de ella.
- **Ceguera por construcción.** Un intento de revisión se anuló porque el revisor leyó la
  hipótesis al pasarse de rango; mover el texto no aislaba nada. Se construyó un paquete de
  revisión desde un commit (`tools/audit/build_review_package.py`) y un hook que deniega toda
  lectura fuera de él (`tools/hooks/confine_review_reads.py`). Probado en vivo: deniega
  `POC.md`. Segunda fase 2 dentro del paquete: PASS, 0 bloqueantes.
- **Commit antes de resultados** (pauta del autor): las dos versiones a ejecutar y la regla de
  equivalencia se commitearon antes de correr. A (código revisado) y B (arreglos aplazados)
  salieron idénticas byte a byte.
- **Resultado de K6:** válido; admite λ₃ y a₈, descarta λ₂ (por 0,0019 sobre τ₁) y l; el tercer
  canal queda constante. Decisiones del autor: L fijo, λ₃ → H, a₈ → C; eje z reformulado (paso 3)
  como el segundo dipolo ortogonalizado en 384-d, a medir con la ficha K8.
- **Marco por época en el motor:** `fit_epoch_frame` + `POST /spatial/calibrate` (revisión
  append-only); `GET /spatial` responde 409 sin marco. Tests de R1 y R2 sobre `/spatial`; un test
  exige que los canales del motor sean los de K6. Retirado el script de K4/K5, atado al marco por
  nodo.
- **Exploraciones anotadas:** partición de Voronoi sobre los ejes como prototipos (Gärdenfors);
  transición continua cerca de un dipolo degenerado (opción del autor).

**Resultado:** todo en ramas locales, sin push. `feat/epoch-frame` (`398dd0f`) contiene el resto:
`feat/k6-colour-predictability` y `feat/render-calibration-hook-hardening`. Suite en verde.

**Resuelto de entradas anteriores:**
- 2026-09-18: formulación de los logs de pérdida relacional (exploración, nula por construcción);
  coordinación con `traianus-2a` (commiteado; el marco por época lo hizo esta sesión); script de
  K6 con TDD; paquete de revisión con ceguera por construcción, fase 2 y ejecución.
- 2026-09-10: el hook del gate se vio actuar en vivo (denegó una edición de `AGENTS.md`).

**Sin resolver / decisión pendiente:**
- R3 (gobernanza): falta comprobar que hay tests que exigen las dos llaves.
- Exploración pedida por el autor y no escrita aún en el repo: la documentación con formato fijo
  que traduzca lenguaje a código, con citas de fichero y línea comprobables contra el código.
- R1-INV4: `/ingesta/vector` no deduplica una clave repetida; bloquea la carga del corpus.
- Manifest del paquete: `data/spinoza/telemetry` sale como no resuelta en vez de denegada (no se
  copia; solo la clasificación).
- Ficha K8 (eje z ortogonalizado), para los días 5–6.
- Integrar las ramas en `docs/development-log` o en una rama de PoC, a decidir.
- **Riesgo:** de dos días, el producto visible sigue sin existir; el hito es el 2026-09-22.

**Próximo paso (mañana, en orden):**
1. R3: comprobar o escribir los tests de las dos llaves.
2. R1-INV4 y verificación de que `/ingesta/vector` guarda los bits intactos.
3. Cargar el corpus nota a nota, calibrar y ver el mapa coloreado (humo real).
4. `GET /spatial?anchor=<id>` con TDD.

### Cierre (23:57)

**Contexto:** tras la entrada de las 16:44: K6 y el marco por época hechos, R3 sin comprobar y el
producto visible sin existir.

**Se hizo:**
- **R3** (`2e5787d`): 12 tests de que una nota solo llega al mapa consolidada con las dos llaves.
  7 confirmaron lo que ya se cumplía; 5 salieron en rojo y destaparon un defecto: `ethical_key` se
  aceptaba como `"true"`, `"yes"`, `"on"`, `"1"` y `1` por la coerción laxa de Pydantic. Se corrigió
  con `StrictBool` en `traianus/app.py`; esa rama queda sin fusionar.
- **Bits de `/ingesta/vector`** (`37efacf`, `762db39`): la primera versión del test exigía guardar
  los bits recibidos y salió roja; era una lectura errónea del contrato. K6 mide
  `v̂ = row / sqrt(row @ row)` en binary64 y eso es lo que guarda el motor. Test y redacción de
  `POC.md` y `contracts.md` corregidos.
- **R1-INV4** (`a355309`, `87d541d`): `/ingesta/vector` deduplica la clave con una columna
  `idempotency_key` anulable y un índice UNIQUE, sin reconstruir la tabla. Cierra AUDIT,
  REMEDIATION-01 INV-4 y LEDGER seq 52.
- **Reparto del trabajo**, por decisión del autor: el chat principal no escribe código; lo escribe
  el subagente `engine-implementer` a partir de un contrato. AGENTS v1.8.0 a v1.9.0 (`bc6b611`,
  `5e6249a`, `36b9011`). Herramientas nuevas: `context_pack` (`3a9997f`, sirve solo las secciones
  pedidas y deja log de rutas), el hook `require_contract_context` (`651bdf4`, los contratos de bits
  se cargan en código, no por mención) y `delegation_contract` (`241f58f`, delegaciones e informes
  como JSON estricto en Pydantic). LEDGER seq 53.
- **Hallazgo de seguridad** (`9fa11ff`): en macOS los dos hooks de ruta se esquivaban cambiando las
  mayúsculas (`TESTS/conftest.py` y `agents.md` salían con exit 0 sin recibo), incluido el gate de
  fronteras. Arreglado por identidad de fichero (`os.path.samefile`), solo desde `tools/hooks/`.
- **Carga del corpus** (`0784464`): `load` y `verify` en
  `tools/experiments/tooling/load_spinoza_corpus.py`. Contra un motor local con base aparte se
  cargaron las 2221 notas sin fallos, `verify` confirmó que las 2221 guardan `v̂` byte a byte y el
  ranking de ejes que calibra el motor coincide con `ranking_full` de `K6_result.json`. El cliente
  muestra el mapa: una nube densa con colores mezclados, no la mancha de un solo color del humo del
  día 1 (a ojo, sin métrica de solapamiento).
- **Reglas del autor:** delegaciones en JSON estricto; `traianus/` inmutable y luego relajado a
  «seguimos hasta acabar la PoC y modularizamos» (ediciones de motor solo si la hoja de ruta las
  pide; `traianus/security/` sale del motor después); lo ajeno a los refutadores espera.
- Diez ramas subidas a GitHub como copia de seguridad, `main` sin tocar (`cc401eb`).

**Resultado:** 13 commits, en ramas locales encadenadas (`feat/context-pack`,
`feat/contract-context-hook`, `feat/delegation-contract`, `feat/hooks-case-fix`,
`feat/corpus-loader`) y tres laterales (`test/r3-two-keys-governance`,
`test/vector-ingest-bit-integrity`, `feat/r1-inv4-vector-idempotency`); `feat/corpus-loader` aún sin
subir. Suite: 2287 en verde, 5 deseleccionadas, comprobada al cierre. Balance: 4 de los 13 commits
van por la ruta de la PoC (R3, bits y su redacción, cargador); el resto es gobernanza y delegación.
En el recap verbal de hoy se dijo «3 de 17»: el conteo era erróneo. Hoja de ruta: día 2 completo;
del día 3, marco por época y mapa a la vista; el ancla, sin empezar.

**Resuelto de entradas anteriores:**
- 2026-09-19 (16:44): R3, tests escritos (con el defecto anterior); R1-INV4, cerrado en su rama y la
  carga no lo necesitó (el cargador no reintenta); verificación de que `/ingesta/vector` guarda los
  bits, hecha con la corrección de lectura; cargar el corpus nota a nota, calibrar y ver el mapa.
- 2026-09-18: el hueco de bits entre artefacto y motor, «pendiente de verificar que ese endpoint no
  altera los bits», queda cerrado.

**Sin resolver / decisión pendiente:**
- Autor: qué hacer con las dos ramas con cambios de motor (`StrictBool`, R1-INV4), sin fusionar; y si
  la congelación de `traianus/` se hace cumplir en código (validador de contratos más hook),
  propuesto sin respuesta.
- El flujo JSON estricto está probado; la definición actualizada de `engine-implementer` no se
  recarga hasta una sesión nueva, así que cada contrato lleva por ahora los dos pasos en `decisions`.
- Huecos declarados: `delegation_contract` no impide que `files_may_touch` liste `traianus/**`; el
  recibo de `context_pack` prueba que se sirvió, no que se leyó; `/ingesta` sigue aceptando una
  clave vacía.
- `POC.md` dice a la vez «checkpoint el día 4» y «checkpoint el 2026-09-22»; con el día 1 = 18, el
  día 4 es el 21. A decidir.
- Las 10 tareas de R5 no están escritas; deben estar commiteadas antes del día 5.
- De la entrada anterior, sin tocar: exploración de documentación con formato fijo, manifest del
  paquete (`data/spinoza/telemetry`) y ficha K8.
- Prueba intermitente `test_concurrent_reads_during_background_write` (cota de 5 ms): falla a veces
  en ejecuciones completas, también en el commit base; sin investigar.
- Idea aparte, diferida: dimensiones de color elegidas por el usuario y pares configuración-log.
- Limpieza del scratchpad de la sesión, con una imagen de disco dentro: `rm` está denegado, es del
  autor.
- **Riesgo:** el mapa se ve, pero faltan zoom, pan y la perspectiva por nota; el hito sigue siendo el
  2026-09-22.

**Próximo paso (mañana, en orden):**
1. Zoom y pan en la capa WebGL (hoy ignora el ratón).
2. `GET /spatial?anchor=<id>` con TDD por el gate, vía `engine-implementer` con contrato JSON: es
   cambio de motor, pero está en la ruta de la hoja de ruta.
3. Escribir y commitear las 10 tareas de R5.
4. Decidir la fecha del checkpoint y la congelación de `traianus/`.
5. Subir `feat/corpus-loader` y decidir la integración de las ramas.

---

## 2026-09-20

**Contexto:** día 3 de la PoC RefApp-01. Se partía del corpus cargado en un motor de prueba, sin
zoom, sin pan y sin perspectiva por nota, con el hito el 22.

**Se hizo:**
- **Decisiones del autor al abrir:** `traianus/` no se congela (el motor se edita solo si la hoja de
  ruta lo pide); `StrictBool` y R1-INV4 siguen sin fusionar hasta modularizar; hito el 22
  (`5f6d778`); recortes en el orden de `POC.md`.
- **La definición nueva de `engine-implementer` sí se recarga.** Con contratos sin los dos pasos en
  `decisions`, el subagente ejecutó `context_pack` por su cuenta (una llamada, las secciones exactas
  del contrato) y contestó un informe JSON que `report` aceptó. Una primera sonda mía tocaba un test
  ajeno a la hoja de ruta y el autor la rechazó (AGENTS 1.1): se sustituyó por un corte real del
  endpoint. LEDGER seq 54.
- **Zoom y pan** (`d3acdbc`): la rueda hace zoom sobre el cursor, arrastrar desplaza, doble clic
  vuelve. Verificado en el navegador leyendo la matriz de vista que dibujó la GPU; ninguna petición
  al motor mientras se navega (R2). Al mirarlo: el buffer de dibujo se quedaba en 300×150 (un zoom
  solo agrandaba píxeles) y el bucle de «respiración» movía los nodos y leía `h` como distancia de
  escape, cuando desde el día 2 es un canal de color; se quitó. Un fallo mío que la verificación
  destapó: dejé habilitados los atributos de transición sobre un buffer vacío y WebGL no dibujaba.
- **Perspectiva, decisiones del autor:** cualquier nodo actual puede ser ancla; la posición se
  recomputa en el marco del ancla a partir de sus pesos sobre los ejes; el color queda el de la
  época. El autor dudó si recomputar también el color y se aparcó como exploración en `POC.md`
  (`ce56847`). Medido al decidirlo: los 2221 nodos cargados están `incubating` y `/spatial` no filtra
  por estado.
- **Motor, tres cortes por contrato JSON al subagente:** `select_poles` (`b17bc96`),
  `perspective_frame` y `observe` (`3fd5ec0`) y `GET /spatial?anchor=<id>` (`1762227`; 404 id
  desconocido, 409 sin marco, 422 ante un `ValueError`, solo lectura). Error mío en el contrato del
  corte 2: describía la colinealidad del proyector como «q y los dos ejes en un plano», y
  `_is_collinear` comprueba que las proyecciones de los polos casi coincidan. El subagente siguió la
  decisión correcta y lo declaró.
- **Corrección de método.** El chat principal empezó a escribir a mano la selección de nodo del
  cliente y el autor lo frenó. El hueco era real: `engine-implementer` cubría `traianus/**` y
  `tools/**`, el contrato solo admitía `engine` o `tools` y el frontend no tiene runner de tests.
  Decisión del autor: ampliar el canal. AGENTS v1.10.0; esquema con `scope: client`, gate `tsc` y
  tests `manual`, con sus acoplamientos aplicados en código (`4d4a2f6`); LEDGER seq 54. El borrador
  quedó en `stash@{0}`, sin usar. El zoom y pan (`d3acdbc`) es la excepción declarada: también lo
  escribió el chat principal.
- **Selección en el cliente** (`1d88a2a`, por el subagente): un clic sobre un nodo pide su
  perspectiva y la dibuja, con el ancla resaltada, Escape o un botón para volver, la proporción real
  del plano y el plano completo a zoom 1. Decisión mía, distinta de lo que había recomendado: la
  perspectiva se escala con un único factor y sin recorte, porque el ancla tiene la mayor similitud
  posible y recortar a unos pocos σ apilaría a sus vecinos en el borde. Las comprobaciones manuales
  las ejecutó el chat principal en el navegador; la de errores mostró la superposición tapada por la
  barra de ingesta en un panel estrecho y se corrigió (`ca490cb`).
- **Observación exploratoria**, un solo ancla: en la perspectiva el color sigue a x (R² del canal h
  sobre un cuadrático de x, y = 0,524; `POC.md`). Hipótesis sin verificar: los dos dipolos contienen
  AXIS_6. Es un indicio a favor de recomputar el color por perspectiva.
- **Consultas del autor:** cargó un documento del «Kernel cinético» y anunció que más adelante habrá
  una búsqueda de otros documentos dispersos; se leyó y se aparcó (no está en el repo). Sobre
  «descargar el modelo para no depender de la API de HF»: ya está en la caché local y el motor lo
  carga con `local_files_only=True`; solo la precarga de CI en un runner en frío toca la red. Se
  preguntó qué se busca exactamente y no hay respuesta.

**Resultado:** 10 commits en la cadena local `feat/perspective-function` → `feat/perspective-observe`
→ `feat/spatial-anchor` → `feat/delegation-client-scope` → `feat/client-selection`: seis los escribió
el subagente por contrato, uno el chat principal (`d3acdbc`, excepción declarada) y tres son de
documentación. Sin commits de otras sesiones. Los tres criterios del hito están cumplidos a día 20:
corpus sobre el mapa coloreado, zoom, y elegir un nodo redibuja el mapa desde él. Suite en 2437
verdes con 5 deseleccionadas, comprobada en `4d4a2f6`; los commits posteriores solo tocan el cliente y
la documentación. Seis ramas nuevas subidas a GitHub con el visto bueno del autor; `main` sin tocar.

**Resuelto de entradas anteriores:**
- 2026-09-19 (cierre): la definición de `engine-implementer` se recarga en la sesión nueva y el
  flujo JSON funciona sin los dos pasos en `decisions`.
- 2026-09-19 (cierre): `POC.md` decía a la vez «día 4» y «22»: el hito es el 22.
- 2026-09-19 (cierre): `StrictBool` y R1-INV4 sin fusionar hasta modularizar; `traianus/` no se
  congela y no se hace cumplir en código.
- 2026-09-19 (cierre): zoom y pan, y `GET /spatial?anchor=<id>` (próximos pasos 1 y 2), hechos. El
  riesgo «faltan zoom, pan y la perspectiva por nota» queda cerrado.
- 2026-09-19 (cierre): `feat/corpus-loader` ya está en el remoto.

**Sin resolver / decisión pendiente:**
- Autor: las tareas de R5, que deben estar commiteadas antes de empezar el día 5 (el 22; fichero
  propuesto `frontend/R5.md`). Dijo «9 ahora» y no está claro si lleva 9 escritas o baja el
  protocolo a 9; sería un cambio de alcance a registrar y con 9 no hay empates.
- Autor: la prórroga de 3 días se decide el martes 22 por la tarde.
- Autor: qué se busca al «descargar el modelo» (un fallo concreto, otra máquina o que CI no dependa
  del hub).
- Autor: promover o no el color por perspectiva antes de la primera ejecución de R4 (día 6);
  exigiría cambiar el registro R4 y otra revisión de fase 1.
- Autor: ampliar la lista de ruff de `ci.yml`, que no incluye `traianus/app.py` ni los tests nuevos.
- Integración de las ramas encadenadas, incluidas las de `StrictBool` y R1-INV4: sin decidir.
- Excepción declarada: `d3acdbc` es código del chat principal, verificado en el navegador y no por un
  test. Los tests del cliente son `manual` y sin rojo previo (límite en LEDGER seq 54).
- La cláusula de cliente de la definición de `engine-implementer` llega a un subagente desde la
  sesión siguiente; hasta entonces cada contrato de cliente repite sus reglas en `decisions`.
- Diseño del cliente: en la perspectiva el ancla fija la escala y el grueso de la nube queda pequeño
  a zoom 1. Menores, declarados por el subagente: un doble clic sobre un nodo lanza dos peticiones;
  el fallo de la carga inicial de la vista general solo sale por consola; el campo de ingesta
  desborda la ventana en un panel muy estrecho.
- De la entrada anterior, sin tocar: exploración de documentación con formato fijo, manifest del
  paquete (`data/spinoza/telemetry`), ficha K8, prueba intermitente
  `test_concurrent_reads_during_background_write`, `/ingesta` acepta una clave vacía y limpieza del
  scratchpad.
- **Riesgo:** el hito ya se cumple; quedan la entrada de notas y consolidación (día 5), la
  interacción y la lista de relacionadas, y R4 (día 6). La función compartida que pide el registro
  R4 existe (`observe`); falta el script.

**Próximo paso (mañana, en orden):**
1. R5: escribir y commitear las tareas antes de empezar el día 5; aclarar si son 9 o 10.
2. Día 5, por contratos de cliente y de motor: entrada de nota y consolidación (`incubating` como
   estado propio, volver a pedir `/spatial` tras ingestar), interacción (texto y relaciones) y la
   lista de notas relacionadas.
3. Comprobación del hito el martes 22 y decisión de la prórroga por la tarde.
4. Decidir el color por perspectiva antes del script de R4.
5. Aclarar lo del modelo de HF y la lista de ruff de CI.

### Cierre (17:08)

**Contexto:** tras la entrada de las 15:09: hito cumplido, las tareas de R5 sin escribir y dudas sobre
si eran 9 o 10. El traspaso de la sesión daba la fecha por el 21; era la tarde del domingo 20, día 3.

**Se hizo:**
- **Calendario corregido al abrir.** El lunes 21 queda sin trabajo asignado: el hito pasó al 22 y el
  día 5 sigue en el 22.
- **R5 estructurada como benchmark** (`c662c7d`, `frontend/R5.md`). Las diez tareas se ejecutan en las
  dos vistas, en días distintos, con la primera vista alternando (impares mapa, pares lista). Cambio
  de protocolo antes de cualquier resultado, anotado en «Scope changes». La primera propuesta del
  chat principal (una vista fija por tarea) se sustituyó por decisión del autor: las mismas tareas
  en ambas. Lo de 9 o 10 queda cerrado: son diez.
- **Fuente de verdad fuera de la herramienta.** El autor no ha leído la Ética, así que ninguna
  esperada puede salir de su memoria ni de lo que muestre una vista (sería medir el motor contra sí
  mismo). T01–T05: frases del corpus elegidas por regla (la de posición central de cada Parte entre
  las que citan al menos 3 proposiciones ajenas; 45 candidatas), y las esperadas son las
  proposiciones que citan. T06–T10: notas propias del autor, en inglés porque el encoder es
  `all-MiniLM-L6-v2` y el corpus es la traducción de Elwes. Las esperadas las propuso el chat
  principal por búsqueda de texto, con el enunciado al lado, y el autor las conservó. Se descartó
  una de cinco ideas (solapaba con otra y su mitad sobre tecnología no tiene equivalente en la
  Ética).
- **Regla de estado nueva.** Las cinco notas propias no están en el corpus, así que las cinco
  dependen de la entrada de notas del día 5: se entran antes del primer intento y después no se
  entra nada. Si no se pueden entrar al acabar el día 6, T06–T10 quedan anuladas.
- **Reglas numéricas**, propuestas por el chat principal y confirmadas por el autor: tope de 3
  minutos, margen de 10 segundos, los empates no puntúan, se exigen 2 proposiciones distintas para
  dar una ejecución por completada; en igualdad gana la lista.
- **Sesgo declarado en los límites.** En una perspectiva el eje vertical ya es el orden de distancia
  real, así que en tareas de «relacionadas» el mapa como mucho iguala a la lista y los empates van a
  la lista. «R5 favorece a la lista» significa «para recuperar relacionadas la lista basta», no «el
  mapa no tiene valor». La fila del día 7 de `POC.md` no se tocó.
- **Subida** de `ec1ead3` y `c662c7d` a `origin/feat/client-selection`; `main` sin tocar (`cc401eb`).

**Resultado:** un commit de esta sesión (`c662c7d`), de documentación; los demás de hoy están en la
entrada de las 15:09. Árbol limpio y todo subido. Suite sin ejecutar: solo documentación.

**Resuelto de entradas anteriores:**
- 2026-09-20: las tareas de R5, «9 o 10» y su commit antes del día 5 (`c662c7d`).
- 2026-09-19 (cierre): «las 10 tareas de R5 no están escritas».

**Sin resolver / decisión pendiente:**
- Autor: la fila del día 7 («R5 favorece a la lista → RefApp-01 sigue list-first») dice más de lo que
  sostiene el resultado. Se ofreció matizarla y no hay respuesta.
- Autor: color por perspectiva antes de R4 (día 6). Además R4 debe declarar sobre qué estado mide:
  2221 nodos, o 2226 con las cinco notas dentro.
- Requisito para el contrato del día 5, sin escribir: el detalle del mapa y las filas de la lista
  deben mostrar el id y el texto de cada nota; hoy el cliente solo muestra «Perspective at {ancla}».
- R5 depende del día 5: sin entrada de notas quedan T01–T05.
- La selección de las anclas se hizo con un filtro `awk` desechable fuera del repositorio. Las cinco
  anclas están congeladas en `R5.md`; hacerla reproducible sería un contrato de `tools/**`.
- Hueco menor aparcado hasta acabar los refutadores: la lista `DENIED` de
  `tools/audit/build_review_package.py` no incluye `frontend/R5.md`. Riesgo bajo.
- Siguen abiertos los demás de la entrada de las 15:09: prórroga el martes 22, modelo de HF, lista de
  ruff de CI, integración de las ramas y los menores del cliente.

**Próximo paso:**
1. Contrato del día 5 (entrada de notas y consolidación con `incubating` como estado propio y nueva
   petición de `/spatial` tras ingestar; lista de las 15 más cercanas; detalle con id y texto). Se
   puede preparar el lunes 21; antes de lanzarlo, anotar las líneas del log de `context_pack`.
2. Entrar las cinco notas antes del primer intento de R5; primera pasada y, al menos un día después,
   segunda.
3. Comprobación del hito el martes 22 y decisión de la prórroga por la tarde.
4. Decidir el color por perspectiva y el estado de R4 antes de su script.
5. Aclarar lo del modelo de HF y la lista de ruff.
