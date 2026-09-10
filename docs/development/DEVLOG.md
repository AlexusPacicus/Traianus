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
