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
