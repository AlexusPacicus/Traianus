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

### Cierre (09:48 del día 21)

**Contexto:** escrito la mañana del 21; recoge el trabajo del 20 tras el bloque de las 17:08: R5
congelado, el hito cumplido y un cliente sin entrada de notas visible, sin detalle de nota ni lista.

**Se hizo:**
- **Sonda de la entrada de notas** contra una copia de la base de prueba: el motor procesa la nota de
  forma asíncrona y le da el id `NODE_<n>` en `pending_approval`; sale en `/nodos` y en `/spatial` y
  sirve de ancla, sin cambios de motor. Se retiró la valoración de «día 5 muy cargado»: sus piezas
  son de cliente sobre endpoints que ya existen.
- **Contrato A** (`1f384a2`, subagente): la entrada espera a `NODE_<n>` y refresca el mapa sin
  recargar; el estado de cada nota se marca con un anillo, en un buffer aparte del bloque de 64
  bytes; los errores salen en línea y la clave de idempotencia se reutiliza en los reintentos. El
  chat principal ejecutó las pruebas manuales contra la copia: pasan. El shader no se había
  compilado antes y compiló.
- **Decisión del autor sobre R5:** apuntar a un nodo del mapa muestra su id y su texto sin cambiar la
  perspectiva; un clic sigue abriendo la perspectiva. Enmienda de la regla 2 de `R5.md` (`21e99cf`),
  antes de cualquier ejecución.
- **Contrato B** (`d80c44b`, subagente): seleccionar por id, panel de la nota (id, texto, estado,
  relaciones), tarjeta al pasar el ratón, alternancia Mapa | Lista con las 15 más cercanas por `y`,
  «Entered as NODE_<n>» y una maquetación en columna sin solapes. Pruebas manuales: pasan.
- **Dos hallazgos al probarlo.** (1) El motor guarda la etiqueta como texto de las notas del corpus,
  porque `/ingesta/vector` no recibe texto (`metadata` solo se registra): el cliente enseña
  etiquetas, no frases. (2) Las relaciones del panel son vecinos cercanos con su id, y el id dice a
  qué proposición pertenece: en la vista Mapa de R5 harían de lista de relacionadas. Además, los ids
  de nota pueden saltarse números, porque un reintento duplicado consume uno.
- **Decisiones del autor:** relaciones ocultas por defecto, con un interruptor, y arreglar el motor
  antes de R5. El contrato del motor (`text` opcional en `/ingesta/vector`) quedó preparado y
  validado, sin lanzar.
- **Puerta de Python.** El subagente ejecutó un `python3 -` con heredoc vacío en A y en B, y el chat
  principal intentó por descuido un `python3 -c`, que el perímetro denegó. El autor decidió aplicar
  AGENTS 2.5 en código, en el binario de Python, en vez de enumerar variantes. La llevó otra sesión
  (la sonda de `SessionStart` pasó, según su nota de memoria) y dejó dos commits en
  `feat/python-gate` (`d747e03`, `31ab270`) que esta sesión no ha revisado.
- **Valoración del trabajo,** pedida por el autor: el preregistro tiene efecto real; los riesgos son
  la proporción entre método y producto, los hallazgos que aparecen tarde y que R5 dirá menos de lo
  que parece (tareas que favorecen a la lista; esperadas de T06–T10 propuestas por el chat
  principal). Sin cambio de plan.
- **Idea del autor, para después de la PoC:** las dimensiones iniciales (los ejes) y las aristas las
  elige y nombra el usuario, y el mapa se lee como bloques sólidos de color. Está en memoria; falta
  su sección «Exploration» en `POC.md`.

**Resultado:** tres commits de esta sesión desde el bloque de las 17:08: `1f384a2`, `21e99cf` y
`d80c44b`. Ninguno está subido: el remoto sigue en `c662c7d` y esas ramas solo existen en local. El
contrato del motor no se lanzó y los JSON de los contratos viven fuera del repositorio. Suite completa
sin ejecutar en esta sesión (cambios de cliente y de documentación). La rama abierta es
`feat/python-gate`, de otra sesión, y este bloque se commitea en ella.

**Resuelto de entradas anteriores:**
- 2026-09-20 (17:08): el contrato del día 5 con entrada de notas, lista y detalle con id y texto,
  hecho en A y B; queda la consolidación.
- 2026-09-20 (15:09): el campo de ingesta que desborda en un panel estrecho, resuelto por la
  maquetación de B.

**Sin resolver / decisión pendiente:**
- Autor: color por perspectiva antes del script de R4 (recomendación del chat principal: no
  promoverlo); prórroga el martes 22; modelo de HF; lista de ruff de CI (`ci.yml` ya recoge los
  ficheros de la puerta de Python); integrar las ramas; la fila del día 7 de R5 («list-first»);
  subir lo que está en local.
- Relaciones ocultas por defecto: contrato C sin escribir, más una regla en `R5.md` y su entrada en
  Scope changes.
- Texto del corpus: falta el contrato del cargador, recargar el corpus en una base nueva y declarar
  su estado para R4 y R5. Choca con la rama sin fusionar de R1-INV4, que toca el mismo endpoint.
- Consolidar desde el cliente (botón y llave ética): sin diseño.
- Puerta de Python: revisión, cableado en los ajustes (del autor), AGENTS 2.5 y 6.2 y LEDGER seq 55.
  `.claude/settings.local.json` sigue sin seguimiento y no está ignorado por git.
- Sección «Exploration» de los ejes y aristas elegidos por el usuario, en `POC.md`.
- **Riesgo:** R4 sin script y pocos días de ventana; el resto del día 5 y R5 dependen del texto del
  corpus y de las relaciones ocultas.

**Próximo paso (lunes 21, en orden):**
1. Lanzar el contrato del motor y después el del cargador; recargar el corpus y declarar su estado.
2. Contrato C (relaciones ocultas) y la regla en `R5.md`.
3. Decidir el color por perspectiva y empezar el script de R4 (ficha con fase 1 aprobada).
4. Revisar la puerta de Python y darle su cableado.
5. Martes 22: comprobación del hito y prórroga por la tarde; entrar las cinco notas antes de la
   primera pasada de R5.

---

## 2026-09-21

**Contexto:** día 4 de la PoC RefApp-01, sin trabajo asignado en `POC.md` y con el hito el 22. Se
partía del corpus cargado con la etiqueta como texto, las relaciones siempre visibles en el panel y
R4 sin script. Esta sesión trabajó sobre la cadena que termina en `d80c44b`; el cierre de las 09:48
del día 21 (otra sesión, `8f814f9`) está en `feat/python-gate` y no en esta cadena.

**Se hizo:**
- **Orden de trabajo:** solo ejecuta un agente a la vez y hay un árbol, así que el motor fue antes que
  la retirada del hook de Bash del chat de la puerta (el autor y ese chat decidieron quitarlo; su
  contrato de retirada está validado y sin lanzar). Al abrir se subieron tres ramas locales.
- **Motor: `text` opcional en `/ingesta/vector`** (`67b9205`, subagente): se guarda como texto del
  nodo, con tope de 20.000 caracteres y sin NUL. Declarado por el subagente: el 422 sale de Pydantic,
  con el cuerpo estándar de FastAPI, sin línea de log y repitiendo el texto que lo causa. Suite 2451,
  ejecutada por mí.
- **Cargador con texto** (`f253b15`): envía la frase de `data/spinoza/*_manifest.json` con sus sha256
  fijados, rechaza un manifest que discrepe del artefacto y `verify` comprueba el texto. Suite 2505.
  Fallo mío: el contexto del contrato pesaba 40334 bytes contra el tope de 40000 de `context_pack`;
  no sirvió nada y ninguna herramienta lo avisa antes de lanzar. El subagente quitó la cláusula 6.1.
- **Base de R5 en `.data/poc/`,** fuera del scratchpad porque R5 dura días: 2221 de 2221 con bits y
  frase exactos, el ranking de calibración igual al `ranking_full` de K6 y 3195 aristas, las mismas
  que la telemetría v4. Cinco notas entradas por el cliente en orden, T06 a T10 como `NODE_1` a
  `NODE_5`, `pending_approval`: 2226 nodos. El motor añadió cuatro filas `RECAL_2` a `RECAL_5`
  (registro de señales de recalibración, no son nodos). Copia con `sqlite3 .backup`, sha256
  `435a4c6f…`. `preview_start` no arrancó el motor (`getcwd`); corrió en una pestaña de terminal.
- **Las cinco notas no tienen aristas:** `rebuild_epsilon_edges` es una función pura de los vectores
  (L2 ≤ 0,8) sin filtro por estado, y el 36% del corpus (809 de 2221) tampoco tiene ninguna. La causa
  es geométrica y no está medida.
- **Cliente: relaciones tras un interruptor y error de carga visible** (`b91a21c`), con T1–T7 manuales
  contra el corpus real; regla nueva en `R5.md` (ninguna vista usa el interruptor). Nuevo
  `frontend/MANUAL_TESTS.md`: una prueba manual no dejaba registro (LEDGER seq 54).
- **Decisiones del autor:** el color por perspectiva no se promueve, primero acabar la PoC; el registro
  automático de R5 después de R4; las cinco notas esa misma noche; sha256 de los manifests fijados.
- **R4** (`42ab352` a `0a67c9a`), implementado por el subagente con tests primero. Revisión ciega de
  fase 2 nº 1: CHANGES (1 bloqueante, integridad en memoria sin prueba en los tests de R4; 13 no
  bloqueantes). Se pasó el registro a revisión 6 (texto alineado con el código) y se añadieron 33
  casos de test (`154b575`). Revisión nº 2: PASS, 0 bloqueantes y 9 no bloqueantes sin aplicar, para
  que el script fuese el revisado. El revisor vio por casualidad `constant_channels: 1` en el
  resultado de K6; declarado en el registro. El plan de ejecución se commiteó antes (`4b4175c`).
- **Resultado de R4** (`data/refapp/R4_result.json`, dos ejecuciones idénticas byte a byte, sha256
  `a8473f32…`, unos 3 min cada una): válido (control «solo y» 1110 de 1110, permutación 0,2018) y
  **R4 se cumple** en las seis longitudes de bloque; cota superior del intervalo entre −0,0188 y
  −0,0059, la más ajustada en L = 50. Diferencia media −0,069 vecinas de 15 (retención 0,811 frente a
  0,816). El color cuesta unas 1,2 vecinas a los dos brazos (2D 0,891, 4D 0,811). Por la tabla del día
  7, λ pierde el eje horizontal; cuál lo sustituye no se ha decidido. Fila K7 y «R4 outcome» en
  `POC.md`.
- **Predicción** en `R5.md` antes de cualquier ejecución: T06 a T10 se completan menos que T01 a T05
  en las dos vistas (`d1d4372`).
- **Registro automático de R5** (`0384015`): eventos con hora, marcas Start y Stop por tarea y
  descarga en JSON; pasivo, sin reloj ni peticiones. Siete pruebas manuales pasan (`MANUAL_TESTS.md`);
  `R5.md` explica el uso. Al empezar, el navegador ya guardaba 16 eventos `point` de las primeras
  exploraciones del autor; ahora tiene 52 con mis marcas de prueba.
- **Fallos míos:** el contexto del cargador (arriba); un clic fuera de campo tras redimensionar, que
  obligó a comprobar que no había entrado texto en la ingesta (no entró); al probar que las cinco
  notas servían de ancla imprimí sus tres vecinas más cercanas (declarado en `R5.md`); tres veces dejé
  el directorio de trabajo en un subdirectorio y los hooks fallaron por su ruta relativa.

**Resultado:** 15 commits de esta sesión, en la cadena `feat/vector-ingest-text` →
`feat/corpus-text-loader` → `feat/client-relations-toggle` → `feat/r4-perspective-recall` →
`feat/r5-run-log`, todos subidos a `origin`; `main` sin tocar (`cc401eb`). La base de R5 está
congelada y documentada, el registro de ejecuciones existe y R4 está medido. Suite: 2621 verdes, 1
omitida y 5 deseleccionadas, en el último commit de Python (`154b575`); lo posterior es cliente y
documentación. Motor y cliente están parados desde que se cerró la app; la base sigue en `2230|2230`.

**Resuelto de entradas anteriores:**
- 2026-09-20 (cierre 09:48 del día 21, en `feat/python-gate`): el contrato del motor y el del cargador,
  la recarga del corpus con su estado declarado, el contrato C con su regla en `R5.md`, el color por
  perspectiva antes de R4 (no se promueve) y el script de R4 (hecho y ejecutado), entrar las cinco
  notas antes de la primera pasada, el estado que mide R4 (la mitad EVAL del artefacto, ni 2221 ni
  2226) y subir lo que estaba en local.
- 2026-09-20 (17:08): «R4 sin script y pocos días de ventana».

**Sin resolver / decisión pendiente:**
- Autor: característica 4 (consolidar desde el cliente): recortar y declarar, o construirla sobre una
  copia de la base, porque consolidar escribe y rompería la base congelada. Recomendación: recortar.
- Autor: qué eje sustituye a λ. Exige decisión, registro nuevo y otra medición, y la ventana acaba el
  25. El brazo de referencia con pesos de covarianza del corpus conserva 0,150 vecinas más que el
  operador: candidato sin medir.
- Autor: prórroga el martes 22 por la tarde, fila del día 7 de R5 («list-first»), modelo de HF, lista
  de ruff de CI.
- Chat de la puerta: retirada del hook de Bash sin lanzar, AGENTS 2.5 y 6.2, LEDGER seq 55 y el cableado
  de `SessionStart` (del autor). `.claude/settings.local.json` sigue sin seguimiento y con la sonda.
- Integración de la cadena: la entrada de las 09:48 del día 21 no está en ella, y el motor toca las
  mismas zonas de `app.py` y `_storage.py` que la rama R1-INV4 sin fusionar: conflicto esperado.
- R4, no aplicado a propósito: test de canales sin recortar (comprobado leyendo K6: `eval_channels`
  devuelve proyecciones en bruto), redacción de `contracts.md` (y = G[q, j]; §0 no nombra las claves
  de `environment`) y otros seis no bloqueantes, todos en el historial de `R4.md`.
- Hueco declarado: `delegation_contract` no detecta un contexto por encima del tope de `context_pack`.
- Falta un script commiteado que calcule completado y tiempos de R5 desde el JSON del registro.
- Sin tocar de entradas anteriores: K8 (eje z), exploración de documentación con formato fijo, manifest
  del paquete (`data/spinoza/telemetry`), `/ingesta` acepta una clave vacía, prueba intermitente
  `test_concurrent_reads_during_background_write`, limpieza del scratchpad y la sección «Exploration»
  de los ejes elegidos por el usuario.
- **Riesgo:** la ventana acaba el 25 y la segunda pasada de R5 debe ir en un día posterior a la primera.

**Próximo paso (martes 22, en orden):**
1. Arrancar el motor en `.data/poc` con log con hora y el cliente; comprobar que la base es
   `2230|2230`; el autor teclea el token.
2. Vaciar el registro del navegador y ensayo del autor (10 minutos, en una nota que no sea de T01 a
   T10).
3. Comprobación del hito con la base real y decisión de la prórroga por la tarde.
4. Primera pasada de R5, con la vista inicial alternando, descargando el JSON a `.data/poc/logs/`.
5. Decidir la característica 4 y el eje que sustituye a λ; dar hueco al chat de la puerta.
6. Un script commiteado que calcule el completado y los tiempos desde el registro.

---

## 2026-09-22

**Contexto:** día 5 de la PoC RefApp-01. La sesión empezó poniéndose al día con la bitácora de los
cuatro días anteriores y la memoria de la noche del 21. El autor trajo dos especificaciones de
calibración cromática escritas en otro chat, y toda la sesión se fue en ese hilo; ninguna tarea del
próximo paso del día 21 se tocó.

**Se hizo:**
- **Dos propuestas externas contrastadas contra el repo y descartadas.** La primera («Especificación
  del Cambio Cromático») y la segunda («Informe Técnico... Calibración Cromática») afirmaban K8 ya
  aplicado (es ficha pendiente, `z = 0.0` hasta que exista), nombraban una base `pkm_substrate.db`
  inexistente (es `traianus.db`), reintroducían `H` como «distancia/ángulo de escape» —el fallo que
  se quitó el día 3 porque `h` es canal de color desde el día 2— y la segunda llamaba «Capa Ulpia» al
  cliente, el error de etiqueta ya corregido el día 1 (Ulpia es la capa de proyección, sin código;
  el cliente es RefApp-01). Inventaba además un acrónimo («ORQ») y usaba «Tomo 0» (real, pero
  investigación futura) como si fuera un estándar de seguridad. El autor confirmó que venían de otro
  chat con contexto distinto y las descartó.
- **Cambio de color de cliente, por contrato a `engine-implementer`** (rama `feat/client-oklch-color`,
  motor sin tocar): el shader pasó de CIE LCh a OKLCH manteniendo L, C y H exactamente como los define
  K6 (`800bb02`). La primera versión escalaba el croma por una constante fija `* 0.37`, decisión mía
  sin medir.
- **El autor rechazó el `0.37` como magic number** («NO QUIERO MAGIC NUMBERS»), tras notar que se
  había dejado llevar por el hilo de las especificaciones externas. Guardado en memoria
  (`no-magic-numbers`).
- **Sustituido por el croma máximo real del gamut sRGB**, calculado por píxel para cada `(L, hue)`:
  porté a GLSL el algoritmo publicado de Ottosson para intersección con el gamut
  (`compute_max_saturation`, `find_cusp`, `find_gamut_intersection`), verificando antes las fórmulas
  exactas contra la fuente (`bottosson.github.io/posts/gamutclipping/`) en vez de reproducirlas de
  memoria (`a49a54f`). Fallo mío en el proceso: lancé el segundo contrato con un placeholder en vez
  del JSON real y lo corregí por mensaje al subagente antes de que actuara sobre él.
- **Verificación propia del port**, no solo la del subagente: revisión línea a línea del diff contra
  la fuente, y contraste numérico — compilé el GLSL tal cual se shippeó en un contexto WebGL aislado
  y lo comparé contra un port en JS escrito de forma independiente, en 98 puntos `(hue, L)`; diferencia
  máxima 3,4×10⁻⁷, sin NaN. Pruebas visuales en el cliente real contra la base congelada de R5: mapa y
  perspectiva correctos, sin errores de consola. El subagente autodenunció un desliz suyo sin efecto
  (un heredoc `python3 -` vacío, contra AGENTS 2.5).
- **Dos peticiones de reabrir el motor, declinadas.** Hacer L un eje independiente vía densidad kNN:
  razoné que un radio basado en `d_esc` heredaría la redundancia con la posición que ya documenta
  ADR-026 (`corr(tanh d_esc, z) = -0.968`) y probablemente fallaría el mismo umbral que descartó `l`
  en K6; kNN con k fijo evita el agujero de densidad del 36% del corpus sin arista a ε=0.8, pero sigue
  siendo un candidato sin probar que necesitaría su propia ficha con revisión ciega, no una decisión
  de diseño directa. Se aparca. Comprobado también si ε=0.8 es un magic number: no de la misma
  categoría que el `0.37` — el LEDGER documenta que la alternativa medida (epsilon de Otsu,
  `epsilon_knee_audit.py`) se probó en la línea de auditoría de puentes y se rechazó explícitamente
  por saturar el grafo en esa geometría; el valor fijo tiene historial de no degenerar en varios
  tamaños de corpus.
- **Decidido no escribir ADR** para el cambio de color: es client-only, reversible, y ya lleva su
  porqué en el comentario de cabecera del shader; la bitácora es el nivel correcto.
- Motor arrancado en `.data/poc` para las pruebas (el autor tecleó el token); sigue vivo al cerrar.

**Resultado:** dos commits en `feat/client-oklch-color` (`800bb02`, `a49a54f`) sobre la punta del día
21 (`a9a4c35`), subidos a `origin`; `main` sin tocar. Ningún commit de motor ni de tooling. Ninguna
tarea de R5 avanzó hoy.

**Sin resolver / decisión pendiente:**
- **Riesgo:** la ventana informal acaba el 25 y hoy no avanzó nada del plan del día 21 — se fue
  entero en un hilo lateral, justificado pero no planeado.
- Sin tocar, de la entrada del 21: vaciar el registro del navegador y hacer un ensayo; primera pasada
  de R5; característica 4 (consolidar desde el cliente); qué eje sustituye a λ; prórroga del 22; fila
  del día 7 «list-first»; modelo de HF; lista de ruff de CI; script commiteado de completado/tiempos
  de R5; K8; documentación con formato fijo; manifest del paquete; `/ingesta` acepta clave vacía;
  prueba intermitente `test_concurrent_reads_during_background_write`; limpieza del scratchpad;
  sección «Exploration» de ejes elegidos por el usuario.
- El chat «de la puerta» (otra sesión) sigue con la retirada del hook de Bash sin lanzar; sin
  actividad suya hoy.
- La cadena de ramas sin integrar creció con dos commits más (`feat/client-oklch-color`); su
  integración sigue sin decidirse.
- Si más adelante se quiere reabrir L como eje independiente: necesitaría una ficha de instrumento
  propia (tipo K8), con revisión ciega, antes de implementarse — no es una decisión de diseño directa.

**Próximo paso:**
1. Vaciar el registro del navegador y hacer un ensayo (10 minutos) fuera de T01–T10.
2. Primera pasada de R5.
3. Decidir la característica 4 y el eje que sustituye a λ.
4. Decidir el destino de la cadena de ramas acumulada, incluida la de hoy.
5. Un script commiteado que calcule el completado y los tiempos de R5 desde el registro.

### Cierre (22:52)

**Contexto:** tras la entrada de esta tarde (color OKLCH cerrado): recapitulación de la bitácora y
decisión de acometer la primera pasada de R5 hoy mismo.

**Se hizo:**
- **Latencia real del cliente, verificada como regresión propia de hoy.** El cálculo del gamut OKLCH
  (`compute_max_saturation`/`find_cusp`/`find_gamut_intersection`) corría en el fragment shader,
  recalculado por cada píxel cubierto en vez de una vez por nota. Movido al vertex shader por contrato
  a `engine-implementer` (`cd2047b`), salida visual idéntica (mismas funciones, solo cambia qué etapa
  las ejecuta), `tsc` verde. Revisado el diff y el color en el cliente real: sin negros ni NaN.
- **La latencia siguió notándose tras el arreglo.** Diagnóstico: máquina de 8 GB con ~62 MB libres y
  ~2,87 GB comprimidos por el sistema — no es el motor (`uvicorn`, 5,6 MB) ni el cliente, es la propia
  app de Claude (varios procesos renderer, uno solo hasta 519 MB) más el resto de apps abiertas.
  Cerrado mi panel de navegador y archivada una sesión antigua sin relación ("Polar Projector research
  paper", inactiva desde el 10-09); ganancia modesta, sin más margen sin cerrar apps que el autor usa.
- **La ventana del 25 vuelve a ser vinculante**, tras una sesión que derivó dos veces en ideas de
  features (Partes por color/dimensión, vistas por dimensión, autocompletado del campo de id) — las
  tres aparcadas en la pila de fichas futuras. Ya era la fecha formal de `POC.md` («Deadline»); solo se
  revierte el «indicativo» de la noche del 21 (memoria del agente actualizada).
- **El tiempo de R5 pasa a calcularse del registro**, no a mano (`ccc5763`, antes de cualquier
  corrida): `run_stop.ms − run_start.ms`, más preciso y sin coste añadido; la regla 1 y el margen de
  10 s de la regla 8 no cambian.
- **Ensayo y primera corrida real de T01** (mapa y lista), con tropiezos de protocolo: dos intentos
  anulados por cambiar de vista a mitad de corrida (regla 4); un malentendido de la regla 3 (dos notas
  de la misma proposición no son dos proposiciones distintas), corregido al repetir; aclarado que la
  lista no exige clic para contar como alcanzada (muestra las 15 con texto a la vez, es el propio
  diseño de esa vista). El registro descargado (copiado a `.data/poc/logs/`, fuera del árbol) reveló
  más de lo que el relato verbal había contado: un tercer intento de mapa también completó pero corrió
  367 s con un hueco de 129 s sin eventos antes de Stop (solapado con esta conversación) — se usó en su
  lugar el intento más limpio (149 s). T01 mapa queda registrado: completado, 149 s (`7c03638`). T01
  lista: se leyeron las 15 (1:5 y 1:6 presentes) pero nunca dentro de un ciclo Start/Stop — sin tiempo
  válido, pendiente de repetir.

**Resultado:** tres commits sobre la punta de la tarde (`ccc5763`, `cd2047b`, `7c03638`), más esta
entrada, en `feat/client-oklch-color`; nada subido a `origin` todavía, `main` sin tocar. Un dato real
de R5 registrado (T01 mapa); T01 lista y las nueve tareas restantes, pendientes.

**Resuelto de entradas anteriores:**
- 2026-09-21 (noche): «la ventana del PoC es indicativa» — revertido hoy, vuelve a ser vinculante el
  25.

**Sin resolver / decisión pendiente:**
- T01 lista: repetir con un Start/Stop limpio.
- T02 a T10: sin empezar.
- La cadena de ramas sin integrar sigue sin decidirse, con dos commits más de hoy.
- Ideas aparcadas hoy: Partes por color/dimensión, vistas por dimensión, autocompletado del campo de
  id, auto-ajuste del bounding box del mapa — todas después del 25.
- El chat «de la puerta» no dio señales hoy.
- **Riesgo:** solo queda mañana como día real antes del 25 (despedida de soltero el 24); la segunda
  pasada de R5 no cabe ya antes de esa fecha salvo que se decida otra cosa.

**Próximo paso (mañana, único día real antes del 25):**
1. T01 lista, con Start/Stop limpio.
2. T02 a T10, alternando vista, un Start/Stop por tarea y vista.
3. Descargar el registro al final de la pasada, a `.data/poc/logs/`.
4. Tabla del día 7 con lo que haya, aunque falte la segunda pasada.

---

## 2026-09-23

**Contexto:** día 6 de la PoC RefApp-01, único día real antes del 25 (despedida de soltero el 24). Se
partía de T01 mapa registrado, T01 lista sin ciclo Start/Stop válido, y T02–T10 sin empezar.

**Se hizo:**
- Motor arrancado en `.data/poc`: `preview_start` volvió a fallar por `getcwd` (mismo fallo del día
  3); levantado en pestaña de terminal.
- **T01 lista repetida limpia** (63 s): 1:5 y 1:6 en el top-15, completada. T02 lista: ninguna
  esperada en el top-15 (verificado replicando `nearestIds` de `frontend/src/notes.ts` contra
  `/spatial`, no de memoria) — no completada.
- **T03 mapa:** un primer Start/Stop fue un clic accidental, descartado; repetido (124 s), alcanzó
  las 3 esperadas.
- **Corrección de protocolo, del autor:** el control de sesgo real de R5 es la alternancia de qué
  vista va primero entre tareas (T01 mapa, T02 lista...), no un día de separación dentro de una
  misma tarea — la regla 4 tal como está escrita solo pedía el día. Permitió correr las dos vistas de
  cada tarea el mismo día y terminar R5 en una sesión.
- **T04 a T10, y los huecos de T02 (mapa) y T03 (lista),** corridas en ambas vistas, cada resultado
  verificado contra el motor (top-15 real por `/spatial` para lista, eventos `point`/`select` del log
  de R5 para mapa) en vez de fiarse del relato del autor.
- **Malentendido detectado y corregido en T07 mapa:** el autor creyó haber alcanzado 2:14 y 5:39
  además de 2:39; el log no tenía ningún evento de alcance para esas dos ids — probable cita dentro
  del texto de otra nota, confundida con la nota misma (regla 2: la proposición se lee del id, no del
  texto). Repetido (137 s, 103 eventos): confirmado que solo 2:39 es alcanzable en esa vista.
- **R5 completo: 20 corridas** (10 tareas × 2 vistas). Por regla 8: mapa gana 3 tareas (T03, T05,
  T10), lista gana 2 (T01, T06), 5 empates (T02, T04, T07, T08, T09) — **gana el mapa**, lo contrario
  de lo que anticipaba la tabla del día 7 de `POC.md` (solo tenía fila para «R5 favours the list»).
  Añadida una sección «R5 outcome» a `POC.md` con el resultado y la predicción del 21-09 (T06–T10
  completa menos proporción que T01–T05), que se cumplió en las dos vistas.
- Varias veces, a petición del autor, se contrastó si una nota alcanzada tenía relación conceptual
  real con el ancla más allá del conjunto esperado — sí la tenía en varios casos (T02, T07), lo que
  sugiere que el conjunto esperado de T06–T10 (propuesto por el chat, no por cita explícita como
  T01–T05) puede ser estrecho; no se tocó, está congelado.

**Resultado:** 16 commits de esta sesión en `feat/client-oklch-color`, todos de `R5.md`/`POC.md`;
ninguno de motor ni cliente. 17 commits sin subir a `origin` en total (incluidos los 5 de la tarde del
22). Suite no ejecutada: solo documentación.

**Resuelto de entradas anteriores:**
- 2026-09-22 (cierre): T01 lista con Start/Stop limpio; T02 a T10; tabla del día 7 — las tres,
  hechas.

**Sin resolver / decisión pendiente:**
- Autor: qué hacer con el resultado «R5 favours the map» — no tiene fila en la tabla de decisión del
  día 7; RefApp-01 sigue sin decidir si es list-first, map-first o sin cambio.
- Integración de la larga cadena de ramas sin fusionar sigue sin decidirse, ahora con los commits de
  hoy encima.
- Ideas aparcadas el 22 (Partes por color/dimensión, vistas por dimensión, autocompletado, auto-ajuste
  del bounding box) siguen esperando.
- El chat «de la puerta» no dio señales hoy.
- Sin tocar de entradas anteriores: K8 (eje z), documentación con formato fijo, manifest del paquete,
  `/ingesta` acepta clave vacía, prueba intermitente `test_concurrent_reads_during_background_write`,
  limpieza del scratchpad.

**Próximo paso:**
1. Autor: decidir qué hacer con el resultado de R5 (mapa gana), dado que no está en la tabla de
   decisión.
2. Cerrar el día 7 formalmente (ledger, resultados) según la hoja de ruta de `POC.md`.
3. Decidir la integración de la cadena de ramas y si se sube algo a `origin`.

### Cierre (13:59)

**Contexto:** tras la entrada de esta mañana (R5 completo, mapa gana): recap de la PoC entera contra
el estado real del repo, y decisión de empezar la integración de la larga cadena de ramas sin
fusionar.

**Se hizo:**
- **Recap de la PoC** contra el repo, no memoria: hito cumplido el día 20; R1/R2 con tests presentes
  sin recorrer hoy; R3 con su fix de gobernanza confirmado ausente de la rama de trabajo
  (`ethical_key` era `bool` normal, no `StrictBool`); R4/K7 se cumple, auditado; R5 completo (entrada
  de esta mañana).
- **Mapeadas las ~37 ramas locales** contra `HEAD` y `main`: casi toda la cadena larga de sesiones
  anteriores resulta ser una sola línea (antepasada de `HEAD`, un solo merge a `main` la trae entera).
  Solo 8 ramas divergen de verdad, y de esas solo tres son de la PoC: el fix de R3 (`StrictBool`),
  R1-INV4 (deduplicación de `/ingesta/vector`, hallazgo 🟠 Open en `AUDIT.md`) y un test de
  integridad de bits — las tres del día 2 (19-09), nunca fusionadas hasta hoy.
- **Las tres, fusionadas:** R3 (`90a1879`, conflicto trivial de una línea de import), R1-INV4
  (`c8e1ba3`, conflicto en `ci.yml` y `LEDGER.md` — reordenado el `LEDGER.md` para que el seq 52
  quede antes del 53, contenido de motor limpio), test de bits (`4b228a4`, sin conflicto). `AUDIT.md`
  ya marca R1-INV4 ✅ Resolved.
- **Verificado tras cada merge:** `pytest tests/` en verde (2633 → 2662 tras R3 → 2667 tras R1-INV4 y
  el test de bits), `ruff` limpio en el alcance exacto de `ci.yml`, `mypy traianus/` limpio (33
  ficheros).
- Dejadas fuera, a propósito: `feat/python-gate` (rama de otra sesión, ajena a la PoC) y cuatro ramas
  de exploración previas a la PoC (`defer/pivot-14d`, `feat/parser-14d`,
  `docs/threat-model-and-academic-grounding`, `research/ulpia-3d-membrane`) — candidatas a limpieza
  aparte, no a integración.

**Resultado:** tres commits de merge sobre `feat/client-oklch-color`, nada subido a `origin`. Suite,
ruff y mypy verdes tras la integración.

**Resuelto de entradas anteriores:**
- 2026-09-23 (mañana): de «integración de la cadena de ramas», las tres piezas reales (R3, R1-INV4,
  test de bits) quedan integradas; el resto de la cadena ya era una sola línea, sin trabajo que hacer
  ahí.

**Sin resolver / decisión pendiente:**
- Autor: subir `feat/client-oklch-color` a `origin` y plantear el camino a `main`.
- Autor: el resultado «R5 favours the map» sigue sin fila en la tabla del día 7.
- `feat/python-gate` sin integrar, ajeno a esta sesión.
- Limpieza de las cuatro ramas viejas de exploración, aparte.

**Próximo paso:**
1. Decidir si se sube `feat/client-oklch-color` a `origin` y se abre el camino a `main`.
2. Autor: decidir el resultado de R5 y cerrar el día 7 (ledger, resultados) según `POC.md`.

### Cierre (14:08)

**Contexto:** tras la entrada de las 13:59 (ramas de la PoC integradas, recap hecho): decidir el
resultado de R5 y subir la rama.

**Se hizo:**
- **Decisión de R5, del autor:** no gana el mapa en exclusiva — ninguna vista sustituye a la otra; el
  mapa queda como vista por defecto (contexto general), la lista a una interacción. El Day-7 table no
  tenía fila para el resultado real; registrado como párrafo propio en `POC.md` (`316633e`). Sin
  cambio de motor ni de Ulpia.
- **`feat/client-oklch-color` subida a `origin`** en dos pushes: los 27 commits acumulados desde el
  22 (color OKLCH, R5 completo, integración de R3/R1-INV4/bits) y después el commit de la decisión de
  R5.
- **Limpieza de ramas.** Clasificadas las 34 ramas locales por ascendencia real contra
  `feat/client-oklch-color` (`git merge-base --is-ancestor`, no de memoria); confirmado con el autor
  el alcance exacto antes de borrar nada. 30 eran checkpoints de sesión ya contenidos en la rama
  actual — borradas, local y remoto (25 tenían copia en `origin`). Las 5 que sí divergen de verdad
  (`feat/python-gate` y las cuatro de exploración pre-PoC: `defer/pivot-14d`, `feat/parser-14d`,
  `docs/threat-model-and-academic-grounding`, `research/ulpia-3d-membrane`) quedaron intactas, tal
  como la propia bitácora las había marcado para limpieza aparte, no de hoy.

**Resultado:** un commit nuevo (`316633e`) sobre `feat/client-oklch-color`, subido a `origin`. Árbol
de ramas locales reducido de 34 a 9 (`main`, `ngi`, `ulpia`, `feat/client-oklch-color` y las cinco
divergentes). `main` sin tocar, sin merge. Suite no ejecutada esta sesión (ningún cambio de motor ni
de cliente).

**Resuelto de entradas anteriores:**
- 2026-09-23 (13:59): subir `feat/client-oklch-color` a `origin` — hecho.
- 2026-09-23 (13:59): «R5 favours the map» sin fila en la tabla del día 7 — resuelto por decisión del
  autor (ninguna vista gana en exclusiva).
- 2026-09-23 (13:59): limpieza de ramas — las 30 de checkpoint quedaron borradas; las cuatro de
  exploración pre-PoC y `feat/python-gate` siguen aparte, sin tocar, como estaba previsto.

**Sin resolver / decisión pendiente:**
- Autor: camino a `main` — sin decidir todavía («no sé aún lo que hacer ahora... nada de merge a
  main aún»).
- `feat/python-gate` sin integrar, ajeno a esta sesión.
- Limpieza de las cuatro ramas de exploración pre-PoC, aparte.
- `.claude/settings.local.json` sigue sin seguimiento (de la sesión del python-gate, no de esta).
- Sin tocar de entradas anteriores: K8 (eje z), documentación con formato fijo, manifest del paquete,
  `/ingesta` acepta clave vacía, prueba intermitente `test_concurrent_reads_during_background_write`,
  limpieza del scratchpad.

**Próximo paso:**
1. Autor: decidir el camino a `main` (cuándo y cómo integrar `feat/client-oklch-color`).
2. Cerrar formalmente el día 7 en el ledger, si procede, con la decisión de R5 ya registrada.

### Cierre (17:56)

**Contexto:** tras el cierre de las 14:08, el autor pidió modularizar — la condición de salida del
Day-7 table de `POC.md` para un resultado favorable: RefApp-01 sale a su propio repositorio.

**Se hizo:**
- **Plan explícito, aprobado por el autor** (modo plan): extraer primero, acotar v2 después ya en el
  repo nuevo; licencia AGPL-3.0-or-later; sin `AGENTS.md`/hooks/subagentes en el repo nuevo por
  ahora; repo `refapp-01`, privado, cuenta `AlexusPacicus`.
- **Hallazgo que cambió el corte ingenuo:** `frontend/audits/` (`contracts.md`, `K6.md`, `R4.md`,
  `definitions.md`, `derivations.md`) es contenido del motor, no del cliente —
  `tools/hooks/contract_registry.json` (AGENTS §3.7) exige secciones suyas antes de editar
  `traianus/geometry/**` y el tooling K6/R4/corpus-loader; moverlo entero con `frontend/` habría
  dejado el hook apuntando a un contrato inexistente y bloqueado esas ediciones para siempre
  (falla cerrado por diseño).
- **Etapa 1 — reubicación,** delegada a `engine-implementer` por contrato JSON: los cinco ficheros a
  `docs/methodology/instrument-audit/`, ~34 referencias actualizadas (motor, tooling, diez tests,
  agentes, skills). Dos huecos declarados por el informe, cerrados por mí: `AGENTS.md` §3.7 (vía
  `validate_proposal`, caso `d5192688`, `EXECUTE_SAFE`) y dos citas internas cruzadas entre los
  ficheros movidos (ruta no gobernada, sin gate). `pytest tests/` verde (2669) antes y después de
  fusionar. LEDGER seq 55 (`d20f932`, `e3e09f9`, `569d9b7`, fusionados en `220819d`).
- **Etapa 2 — extracción del cliente:** clon `--no-local` de Traianus (el primer intento, con
  hardlinks, lo rechazó `git-filter-repo`) en `/Users/test/Documents/NGI/refapp-01`;
  `git-filter-repo` con `--path-rename frontend/:` preserva 57 de los ~75 commits que tocaban
  `frontend/` (el resto solo tocaba `audits/` u otras rutas, vacíos tras el filtro). Scaffolding:
  `LICENSE` (AGPL-3.0-or-later), `README.md`, `.gitignore`, CI (`typecheck` + `build`);
  `package.json`/`-lock.json` renombrados de `"ulpia"` a `"refapp-01"`; las nueve citas de `POC.md`
  a `audits/...` reescritas como enlaces absolutos a Traianus, fijados al commit de la reubicación.
  `npm ci && npm run typecheck && npm run build` verdes.
- **Etapa 3 — publicación:** repo `refapp-01` creado en GitHub (privado), subido como `main`,
  verificado contra un clon limpio independiente.
- **Etapa 4 — retirada de Traianus:** `frontend/` borrado con `git rm -r` (el `rm` de shell sigue
  denegado por política; para el clon local fallido de la etapa 2, un `mv` fuera del camino sí se
  permitió), el job `test-frontend` fuera de `ci.yml`, `README.md` con puntero al repo nuevo.
  `pytest tests/` verde (2669), sin cambio. LEDGER seq 56 (`3a28af3`, `38f72c4`).

**Resultado:** seis commits nuevos en `feat/client-oklch-color`, todos subidos a `origin`; `main` sin
tocar. `refapp-01` publicado y verificado
([github.com/AlexusPacicus/refapp-01](https://github.com/AlexusPacicus/refapp-01)).

**Resuelto de entradas anteriores:**
- Condición de salida del Day-7 table (RefApp-01 sale a su propio repositorio) — cumplida.
- 2026-09-19: el hueco de que `frontend/audits/contracts.md` gobierna ediciones del motor sin estar
  declarado como tal — cerrado al reubicarlo a `docs/methodology/`.

**Sin resolver / decisión pendiente:**
- Autor: camino de `feat/client-oklch-color` a `main` — sigue sin decidir.
- `AGENTS.md` §6.1 (`scope: client`): cláusula ya inalcanzable (no queda `frontend/src/**`), dejada
  declarada, no resuelta — fichero gobernado, decisión aparte.
- v2 (comparar notas, anclar e interactuar, `/mutate`): se acota en `refapp-01`, cuando el autor
  quiera.
- Restos sin trackear en disco: `frontend/node_modules/`, `frontend/dist/`, `frontend/.DS_Store`
  (ignorados por git, inofensivos) y un clon fallido en
  `/Users/test/Documents/NGI/refapp-01-stale-hardlinked-clone`; `rm` denegado por política, el autor
  los borra si quiere.
- `feat/python-gate` y las cuatro ramas de exploración pre-PoC: sin tocar, aparte, como estaba
  decidido.
- Sin tocar de entradas anteriores: K8 (eje z), documentación con formato fijo, manifest del
  paquete, `/ingesta` acepta clave vacía, prueba intermitente
  `test_concurrent_reads_during_background_write`, limpieza del scratchpad.

**Próximo paso:**
1. Autor: decidir el camino a `main`.
2. v2 en `refapp-01`, cuando el autor quiera.
3. Limpieza manual de los restos en disco que `rm` no me deja tocar.

### Cierre (23:38)

**Contexto:** el autor fusionó el PR de modularización a `main` por su cuenta (`7ed20c2`) y pidió
un plan para atacar el backlog general del DEVLOG más los tres módulos sin cablear. Aparte, pidió
quitar toda atribución/publicidad de Claude en commits y PRs — aplicado desde este cierre en
adelante.

**Se hizo:**
- **Plan explícito** (modo plan), aprobado por el autor: cinco deltas — dos bugs declarados desde
  el día 2, retirar `scope: client`, retirar `simplex.py`, e investigar la prueba intermitente sin
  delegar. K8 quedó fuera (no seleccionado); "documentación con formato fijo" y `svd_filter.py`
  quedaron declarados, sin entregable definido, para que el autor decida.
- **Δ1 — `/ingesta` rechaza clave vacía** (`a38cc77`): mismo check que ya tenía `/ingesta/vector`
  (REMEDIATION-01 §3.1, mitad que faltaba). LEDGER seq 57.
- **Δ2 — manifest del paquete** (`a76d802`): `_is_denied` comparaba con `startswith` crudo; una
  cita de `data/spinoza/telemetry` sin barra final caía en `unresolved` en vez de `denied`. El
  subagente encontró que mi contrato afirmaba mal que solo una entrada de `DENIED` terminaba en
  barra (son tres) y generalizó el arreglo en vez de parchear solo telemetry. LEDGER seq 58.
- **Atribución opcional en los contratos de delegación** (`2155a71`), hecho antes de Δ3 porque su
  propio esquema exigía una línea `Co-Authored-By` obligatoria — bloqueaba lanzar cualquier
  contrato sin publicidad de Claude. `attribution` pasa a `str | None`; sin ella, el commit del
  subagente no lleva línea de coautoría.
- **Δ3 — retirar `scope: client`** (`877bf20` + `11d7ab0`): `frontend/src/**` ya no existe, así que
  ni el `scope: client` del contrato ni el gate `tsc` ni la expectativa `manual` eran alcanzables.
  Quitados de los tres `Literal` de `delegation_contract.py`, de sus tres validadores dedicados, de
  `AGENTS.md` §6.1 y de `engine-implementer.md`. El propio informe del subagente señaló una
  inconsistencia en mi contrato (`AGENTS.md` seguía diciendo «or client change» pese a que ya no
  quedaba `frontend/src/**`); la cerré yo en un commit aparte. LEDGER seq 59.
- **Δ4 — retirar `traianus/geometry/simplex.py`** (`18b8ca7`): verificado contra el código, no
  contra el docstring, que `SemanticSimplex` no es una pieza a la espera de una llamada — el
  mecanismo real de señal de recalibración es `VarianceTracker` (EWMA + Schmitt trigger,
  `traianus/telemetry/variance_tracker.py`), consumido por `app.py`. `SemanticSimplex` es un
  diseño alternativo que nunca se conectó, con su propia constante `RECALIBRATION_SIGNAL`
  desconectada de la real. `ParabolicCorrector` y `SVDAnisotropyFilter` quedaron fuera del plan
  (el primero es un corte de alcance a propósito; el segundo tiene un desajuste real spec/código
  que el autor debe decidir cómo resolver, no yo). LEDGER seq 60.
- Cada delta: contrato JSON validado antes de lanzar, revisado por mí tras el commit, `pytest
  tests/` + `ruff` + `mypy` en verde, fusionado a `main` y subido antes del siguiente.

**Resultado:** ocho commits nuevos en `main` (cuatro de código/gobernanza, cuatro de LEDGER),
todos subidos a `origin`. Suite: 2632 verdes / 1 omitido / 5 deseleccionados al cierre (bajó de
2672 por las eliminaciones netas de test surface en Δ3 y Δ4). Nada de esto tocó `refapp-01`.

**Resuelto de entradas anteriores:**
- `/ingesta` acepta clave vacía — cerrado (Δ1).
- Manifest del paquete (`data/spinoza/telemetry`) — cerrado (Δ2).
- `AGENTS.md` §6.1 `scope: client` inalcanzable — cerrado (Δ3), en vez de dejado declarado.
- Uno de los tres módulos sin cablear (`simplex.py`) — cerrado (Δ4).

**Sin resolver / decisión pendiente:**
- Autor: camino a `main` — ya no aplica como tal (el autor fusionó `feat/client-oklch-color`
  directamente); queda decidir qué sigue.
- Autor: `svd_filter.py` — ¿arreglar el código para restar un sesgo compartido real, o corregir el
  docstring/spec para que describa la resta de PCA que ya hace? Sin decidir.
- Autor: «documentación con formato fijo» — sin entregable concreto definido.
- K8 (eje z), fuera de este plan por decisión del autor.
- Prueba intermitente: investigación (Δ5) empezada, sin cerrar a esta hora — sigue en la entrada
  de mañana.
- Restos en disco y limpieza de ramas de otras sesiones: sin cambios, igual que antes.

**Próximo paso:**
1. Terminar Δ5 (prueba intermitente) y decidir con el autor si toca la cota o no.
2. Autor: decidir `svd_filter.py` y «documentación con formato fijo».
3. Autor: decidir qué sigue tras la fusión directa a `main`.

---

## 2026-09-24

**Contexto:** continuación de la sesión de ayer; queda Δ5 del plan de backlog — investigar
`test_concurrent_reads_during_background_write` antes de tocar su cota, sin delegar (memoria: no
magic numbers).

**Se hizo:**
- **30 corridas medidas**, ninguna con código tocado antes: 20 aisladas (solo ese test, nada más
  corriendo) y 10 con la suite completa (`pytest tests/`, ~2632 tests, condición real de CI y de
  cada sesión de trabajo).
- **Aisladas: 20/20 en verde.** Sin excepción.
- **Bajo la suite completa: 9/10 en verde, 1 fallo real.** El único fallo: p99 de 9,56 ms contra
  la cota de 5 ms (case 9,56 > 5, no un margen minúsculo). Memoria libre de la máquina en el
  momento de medir: ~51 MB (`vm_stat`, páginas libres × 16 KB) — mismo cuadro que el cierre del
  22-09 (≈62 MB libres, varios procesos de la app de Claude compitiendo por CPU/memoria).
- **Lectura:** el patrón coincide con lo ya registrado en LEDGER seq 52/53 (2 de 10 falló
  entonces; el mismo tipo de fallo, nunca en aislamiento). No es un bug de contención en el código
  — la prueba aislada nunca falla — es una cota de reloj de pared que la máquina real, bajo carga
  real, a veces no cumple.

**Resultado:** ningún cambio de código. Medida tomada y documentada; no toco la cota sin que el
autor decida qué hacer con ella.

**Resuelto de entradas anteriores:**
- Prueba intermitente: investigada (Δ5); la medida está sobre la mesa, la decisión no.

**Sin resolver / decisión pendiente:**
- Autor: con 29/30 en verde y el único fallo bajo carga real de la propia máquina de trabajo —
  ¿relajar la cota (con esta medida como base, no un número inventado), aceptarla como flake
  conocido y documentado, o investigar más (qué corre justo antes de este test en la suite
  completa)? Sin decidir.
- Todo lo demás de la entrada de ayer sigue igual: `svd_filter.py`, «documentación con formato
  fijo», K8, camino tras la fusión a `main`, restos en disco, ramas de otras sesiones.

**Próximo paso:**
1. Autor: decidir qué hacer con la cota de `test_concurrent_reads_during_background_write`.

### Cierre (11:59)

**Contexto:** tras la entrada de esta mañana (180 corridas medidas, decisión pendiente): el autor
preguntó por el umbral de percepción humana antes de decidir el número, luego confirmó.

**Se hizo:**
- **Referencia dada:** los tres límites de Nielsen/Miller (~100ms instantáneo, ~1s sin romper el
  hilo de pensamiento, ~10s el límite de atención) — ni la cota vieja (5ms) ni el fallo medido
  (9,56ms) se acercan a lo perceptible.
- **Cota recalibrada a 10ms** (`9728c1e`): el entero de milisegundo más pequeño que cubre las 180
  corridas de hoy, elegido contra esa referencia, no una aproximación a ojo. Comentario en el
  código con la medida y su fecha, para que una futura reapertura tenga un número real, no una
  suposición. Cota bajo trazador escalada proporcionalmente (50ms → 100ms). Hecho directamente,
  sin delegar (cambio de una constante, ya justificado por la medición). LEDGER seq 61.

**Resultado:** un commit de código (`9728c1e`) y uno de ledger (`f77d69b`), ambos en `main`,
subidos. Suite: 2632 verdes, sin cambio.

**Resuelto de entradas anteriores:**
- Prueba intermitente — cerrada del todo (medida, decidida, implementada).

**Sin resolver / decisión pendiente:**
- Autor: `svd_filter.py`, «documentación con formato fijo» (siguiente en la cola, por orden del
  autor), K8, camino tras la fusión a `main`, restos en disco, ramas de otras sesiones.

**Próximo paso:**
1. `svd_filter.py`: recordar qué hace y decidir arreglar el código o el docstring.
2. Documentación de formato fijo, después.

### Cierre (svd_filter)

**Contexto:** tras recordarle al autor qué hacía `svd_filter.py`, decidió ambas cosas a la vez: el
docstring pasa a describir con precisión lo que el código hace (reducción de anisotropía por
proyección ortogonal), y además pidió una comprobación real — que `transform` devuelva vectores
renormalizados a norma unitaria, invariante básico del sustrato (AGENTS §3.1) que el filtro violaba.

**Se hizo:**
- **`SVDAnisotropyFilter` corregido** (`3d03bfa`): docstring del módulo y de la clase reescritos
  con la formulación exacta del autor; terminología arreglada (era "left singular vector", el
  código usa el derecho, `fit()` ya lo decía bien — inconsistencia interna cerrada). `transform` y
  `fit_transform` renormalizan a norma L2 unitaria, con guarda por `eps` para el caso borde de un
  solo vector (donde filtrar deja un vector casi nulo que no se puede renormalizar sin dividir por
  ~0). Tres tests existentes reescritos, no debilitados, para el nuevo contrato; dos nuevos.
  Ningún llamador añadido — sigue sin cablear, esto cierra la consistencia, no la decisión de
  cablearlo. LEDGER seq 62.

**Resultado:** un commit de código (`3d03bfa`) y uno de ledger, fusionados a `main`. Suite: 2632
verdes, sin cambio.

**Resuelto de entradas anteriores:**
- `svd_filter.py` — cerrado, las dos mitades del backlog de módulos sin cablear (Δ4 ayer, este
  hoy) resueltas.

**Sin resolver / decisión pendiente:**
- «Documentación con formato fijo» — siguiente en la cola, por orden del autor.
- Lo de siempre: K8, camino tras la fusión a `main`, restos en disco, ramas de otras sesiones.

**Próximo paso:**
1. Documentación de formato fijo — retomar con el autor qué entregable concreto quiere.

### Cierre (svd_filter, segunda vuelta)

**Contexto:** al preguntarle al autor su opinión sobre el cambio de `svd_filter.py` recién
fusionado, señaló un problema real que la primera vuelta no resolvía: renormalizar cada vector por
separado distorsiona la geometría relativa del corpus (dos vectores con distinta "dosis" de
contaminación por `u1` pueden acabar siendo el mismo vector), y propuso una fórmula concreta para
resolverlo junto con el hueco de bias removal que `POC.md` ya había señalado.

**Se hizo:**
- **`SVDAnisotropyFilter`, segunda revisión** (`7f6668e`): `fit()` guarda la media del corpus
  (`self.mean_`); `transform` centra el vector por esa media *antes* de proyectar `u1` (antes se
  proyectaba sobre el vector crudo), y devuelve `(vector_unitario, norma_residual)` en vez de
  descartar el escalar — señal reutilizable para `d_esc`, `L` o un tensor de control. Cambio de
  firma deliberado (tupla en vez de array), seguro porque nada lo llama todavía.
  Sigue sin cablear. LEDGER seq 63.
- **Error en mi propio contrato, detectado por el subagente:** afirmé que un test seguiría dando
  `ortho` como dirección superviviente bajo la nueva fórmula; a mano, no es cierto — un offset
  ortogonal *constante* por fila lo absorbe por completo el centrado, colapsando el residuo a casi
  cero. El subagente lo verificó por cálculo directo y rehizo el fixture con una señal ortogonal
  que varía por fila, preservando el propósito real del test en vez de forzarlo a pasar.

**Resultado:** un commit de código (`7f6668e`) y uno de ledger, en `main`. Suite: 2634 verdes
(9/9 en el fichero del módulo, dos nuevos).

**Resuelto de entradas anteriores:** ninguna — `svd_filter.py` ya estaba cerrado; esto es un
refinamiento posterior a la conversación con el autor, no una reapertura de un pendiente.

**Sin resolver / decisión pendiente:**
- «Documentación con formato fijo» — sigue siendo lo siguiente en la cola.
- Lo de siempre: K8, camino tras la fusión a `main`, restos en disco, ramas de otras sesiones.

**Próximo paso:**
1. Documentación de formato fijo — retomar con el autor qué entregable concreto quiere.

### Cierre (14:14)

**Contexto:** recap de la bitácora a petición del autor; lo siguiente en la cola era la
«documentación con formato fijo» (pendiente desde el 19-09), sin entregable definido.

**Se hizo:**
- **Borrador y decisiones del autor:** las citas `fichero:línea` que ya había en `docs/` nunca se
  comprobaban y se habían desviado (`app.py:379` de REMEDIATION-01 apunta hoy a un `)`,
  `validator.py:59` a `try:`). De ahí el formato: cita anclada en texto literal, como exige AGENTS
  5.3, con la línea derivada del ancla. El autor aceptó las cuatro recomendaciones: alcance en los
  invariantes clave, `--fix` para líneas desfasadas, `docs/traceability/`, y REMEDIATION-01 sin
  tocar como registro fechado.
- **`TRACEABILITY.md`** (`a57146c`), escrito y comprobado a mano antes de que existiera el checker:
  14 fichas, 20 citas de código, 29 de tests. Cuatro afirmaciones sin test que las fije, declaradas
  como huecos en vez de fichas (bind a `127.0.0.1`, sin `UPDATE`/`DELETE` como test, ε sin cambiar
  estados, potencial de acción en la ingesta de texto).
- **Checker** (`b1da739`), delegado a `engine-implementer` con contrato JSON validado: ancla única
  en la línea citada, tests existentes vía `ast`, estructura fija, `--fix`. Revisado en vivo sobre
  una copia con una línea desfasada y un ancla rota: ambos detectados, `--fix` solo tocó el número.
  Límite menor anotado: un encabezado mal escrito se reporta como campo duplicado, no como tal.
- **Dos ideas del autor, aparcadas** tras contrastarlas con el repo: un protocolo de entrada binario
  de 64 bytes (como entrada invierte el flujo de datos; el bloque de 64 bytes ya existe como
  salida, `ZeroCopyExporter`, sin cablear) y lenguajes de especificación formal (Hypothesis para
  afirmaciones «∀» de las fichas, TLA+ más adelante).

**Resultado:** fusionado a `main` (`90b01b3`), LEDGER seq 64 (`e81b0aa`), subido a `origin`; rama
borrada. Suite: 2652 verdes (18 nuevos). Solo queda sin seguimiento `.claude/settings.local.json`,
de la sesión del python-gate.

**Resuelto de entradas anteriores:**
- 2026-09-24 (svd_filter, segunda vuelta): «documentación con formato fijo» — entregada.
- 2026-09-19: la exploración de documentación que traduzca lenguaje a código con citas
  comprobables — hecha.

**Sin resolver / decisión pendiente:**
- Autor: si los cuatro huecos declarados de `TRACEABILITY.md` merecen tests (serían el punto de
  entrada natural de la idea de Hypothesis, que necesita aprobar la dependencia).
- `refapp-01/POC.md` («Built but not wired») y `docs/specifications/simplex_control_spec.md` siguen
  citando `simplex.py`, retirado en la seq 60 — documentación desfasada, fuera de este alcance.
- Lo de siempre: K8, v2 en `refapp-01`, restos en disco, `feat/python-gate` y las cuatro ramas de
  exploración pre-PoC.

**Próximo paso:**
1. Autor: elegir entre K8 y la v2 en `refapp-01`.
2. Retirar o actualizar las dos referencias desfasadas a `simplex.py`.
