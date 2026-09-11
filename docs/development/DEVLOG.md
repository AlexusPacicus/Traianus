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
