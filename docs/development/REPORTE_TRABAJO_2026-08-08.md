# Informe de Trabajo — 2026-08-08

**Ámbito:** repositorio `Traianus` (rama `main`, sin commits emitidos)
**Ciclo:** TDD (RED → GREEN → REFACTOR) sobre SPEC-TDD-028 + colocación documental
**Estado final:** suite `71 passed` · harness C1 verde (45%) · TridenGuard EXECUTE_SAFE

---

## 1. Verificación y colocación de documentos (Kernel Cinético)

Los tres documentos del Kernel Cinético estaban en `~/Downloads/` y **no** se encontraban
versionados en el repo (solo citados como "CHANGELOG TÉCNICO…" en
`docs/architecture/ADR/ADR.md:268` y en `docs/development/SPEC-ARCH-028.MD`).

| Documento | Destino en repo | Origen |
|---|---|---|
| Changelog v1.0.0-alpha | `docs/development/CHANGELOG_KERNEL_CINETICO.md` | copia literal |
| V2 física del continuo | `docs/development/KERNEL_CINETICO_FISICA_CONTINUO.md` | copia literal |
| Registro de transición logográfica | `docs/development/REGISTRO_TRANSICION_LOGOGRAFICA.md` | extraído del export HTML |

**Nota sobre el Registro:** el export de Google Docs contenía 2814 líneas de chrome
HTML. El contenido limpio se extrajo del JSON inline (`DOCS_modelChunk`, chunks `ty:"is"`,
campo `s`, ordenados por `ibi`) y se escribió como Markdown, incluyendo la tabla
comparativa Tomo 0 → Tomo 1. No se commitearon los artefactos intermedios (`.html`,
`.json`).

---

## 2. SPEC-TDD-028 — Parser Analítico Weightless 14D (NSM 1972)

### 2.1 Especificación cumplida

| Criterio del SPEC | Estado |
|---|---|
| `encode_weightless_14d(text) → ndarray (14,) float64` | ✅ TEST-01 |
| Norma L2 = 1.0 ±1e-12 | ✅ TEST-02 |
| Fallback uniforme `1/√14` para entrada vacía | ✅ TEST-03 |
| Determinismo bit a bit (mismos bytes entrada → mismos bytes salida) | ✅ TEST-04 |
| Sensibilidad morfológica (raíz compartida `pens-` → dot alto) | ✅ TEST-05 (calibrado) |
| `θ_dyn = P95(σ²_control)` sobre corpus de 100 frases neutras | ✅ TEST-06 |
| Registro de `θ_dyn` en `tools/audit_harness.py` (DoD) | ✅ |
| Sin dependencias externas ni red (FNV-1a 64-bit, stdlib + numpy) | ✅ |

### 2.2 Artefactos producidos

| Archivo | Líneas | Rol |
|---|---|---|
| `tools/weightless_parser_1972.py` | 85 | parser: n-gramas 3-5 → feature hashing FNV-1a → L2 |
| `tools/fixtures/control_corpus_100.txt` | 100 | corpus de control neutro (TEST-06) |
| `tests/unit/test_weightless_parser.py` | 65 | 6 tests TEST-01..06 |
| `tools/audit_harness.py` | 147 (+21) | registra `θ_dyn` y verifica contract 14D |

### 2.3 Resultados medidos

```
theta_dyn (P95 σ²_control, 100 frases) = 0.012917
norma del vector de prueba            = 1.0 (shape (14,))
pensamiento · pensar                  = 0.75   (conteo, sin signo)
pensamiento · pensar                  = 0.0    (sign trick — cancelación)
coseno máx teórico 6/√(23·9)          ≈ 0.417  (cota del SPEC "> 0.8")
```

---

## 3. Desviaciones del SPEC (calibradas, patrón audit C1)

Dos requisitos del SPEC-TDD-028 eran **internamente contradictorios** con los números
que el propio spec citaba. Siguiendo el precedente del audit (C1: calibrar con datos
medidos, no con cifras aspiracionales), se aplicó la corrección documentada en el código:

1. **TEST-05 (`dot > 0.8`) era matemáticamente inalcanzable.** `pensamiento` genera 23
   n-gramas y `pensar` 9; comparten 6. El coseno ideal sin colisiones es
   `6/√(23·9) ≈ 0.417 < 0.8`. Umbral recalibrado a `> 0.5` (línea base de palabras no
   relacionadas medida ≈ 0.23).

2. **El sign trick (+1/−1) del spec destruía la señal morfológica en 14D.** Medido:
   `pensamiento·pensar = 0.0` (colisiones de signo opuesto en el mismo índice de 14
   buckets). Se reemplazó por **acumulación por conteo** en el mismo bucket:
   `v[h % DIM] += 1.0`, resultado `0.75`. Esto preserva el Feature Hashing del pipeline
   (Extraction → Hashing → L2) manteniendo la determinación exacta.

3. **Corpus corregido de 101 → 100 líneas** (TEST-06 exige exactamente 100).

Cada desviación queda anotada en el docstring del test y en el módulo, para que el
refactor futuro no "silencie" el invariante real (sensibilidad morfológica sobre ruido).

---

## 4. Integración y verificación

### 4.1 Suite completa

```
python3 -m pytest tests/ -q
71 passed in ~2-3s
```

Incluye las regresiones históricas (C1 self-projection, append-only, ε-edges, seguridad
SEC-M-*, dimensiones, WAL, etc.) — intactas.

### 4.2 Harness empírico (`tools/audit_harness.py`)

```
Basis orthogonality (off-diagonal cosine) - Mean/Max
Notes accepted at ingestion (H1/H2/H3): 20/20
Measured consolidation rate: 45% (9/20)
✅ C1 GUARD PASSED IN GREEN: non-degenerate (9/20)
-> Weightless theta_dyn (P95 sigma^2_control, 100 phrases): 0.012917
-> Weightless 14D contract OK (shape=(14,), norm=1.0)
```

### 4.3 TridenGuard Zero-Trust Gate (REFACTOR del harness)

```
status: VALIDATED · final_decision: EXECUTE_SAFE
case_id: 52829234-2eb3-4c06-92e6-d3a8d68e516c
and_gate_ok: true
```

---

## 5. Higiene del repositorio

- Sin dependencias nuevas (no se tocó `pyproject.toml` ni `flake.nix`).
- Sin artefactos temporales, dumps `.json`/`.log` ni scripts de un solo uso en el árbol.
- `tools/audit_harness.py` importa el parser después de `sys.path.insert` (sin romper la
  ejecución directa); se eliminó un import muerto (`spectral_variance`).
- Nada commiteado.

### Estado git (sin commit)

```
 M docs/architecture/ADR/ADR.md          (modificación previa, no de este ciclo)
 M tools/audit_harness.py
?? docs/development/CHANGELOG_KERNEL_CINETICO.md
?? docs/development/KERNEL_CINETICO_FISICA_CONTINUO.md
?? docs/development/REGISTRO_TRANSICION_LOGOGRAFICA.md
?? docs/development/SPEC-ARCH-028.MD
?? tests/unit/
?? tools/fixtures/
?? tools/weightless_parser_1972.py
```

---

## 6. Pendiente / decisiones para el usuario

1. **Commits:** ¿se versiona el trabajo (3 documentos + SPEC-TDD-028) en uno o varios
   commits? La modificación de `docs/architecture/ADR/ADR.md` es previa y debería
   separarse.
2. **`SPEC-TDD-028` no existe como archivo.** Los tests son la spec ejecutable; si se
   quiere trazabilidad al DoD (como `SPEC-ARCH-028.MD`), conviene materializarla en
   `docs/development/`.
3. **Siguiente fase del Kernel Cinético:** el parser 14D está listo como Tier 1; queda
   la integración con el sustrato 384D (re-proyección/provance) si el refactor
   (SPEC-ARCH-028/SPEC-REFACTOR-v0.1) avanza.
