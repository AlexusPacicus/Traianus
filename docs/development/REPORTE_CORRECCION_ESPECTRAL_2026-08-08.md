# Informe — Corrección Espectral del Parser 14D y Commits (2026-08-08)

**Rama:** `feat/simulation-real-data`
**Ciclo:** Corrección conceptual SPEC-TDD-028 + verificación de hipótesis + 2 commits atómicos
**Estado:** suite 71 passed · harness C1 verde (45%) · TridenGuard EXECUTE_SAFE

---

## 1. Corrección arquitectónica del parser (SPEC-TDD-028)

Se separaron estrictamente las tres fases en `tools/weightless_parser_1972.py`,
eliminando la ambigüedad entre extracción de características y evaluación de fricción:

| Fase | Operación | Salida |
|---|---|---|
| **A** — Extracción vectorial (Tier 1) | texto → n-gramas 3-5 → FNV-1a 64-bit → conteos `v_raw` → L2 estricto | `v ∈ S¹³`, `‖v‖₂ = 1.0` |
| **B** — Proyección espectral (Tier 1→2) | `s_k = ⟨v, P_k⟩`, `k ∈ [1,14]` | espectro `s` |
| **C** — Fricción geométrica (Tier 2) | `σ² = var(s)` **solo** sobre el espectro, nunca sobre conteos crudos | `σ² ∈ [0,1)` |

### Base de prototipos reales (Fase B)

Reemplazada la base identidad `I₁₄ₓ₁₄` (semánticamente vacía) por **14 prototipos
NSM reales** en el mismo espacio 14D del parser (`encode_weightless_14d(primitiva)`):

```
something, someone, happen, move, be in a place, be good, think, know,
want, feel, see, say, true, time
```

- Archivo: `tools/fixtures/nsm_prototypes_14.json`
- Geometría medida: **rango 14** (completo), condición ~35, coseno off-diagonal
  mean 0.24 / max 0.83 → no ortogonal, no degenerada.
- Aislamiento de cambio: sustituir la base toca solo `load_prototype_basis()` y el
  JSON, nunca las fases A ni C.

---

## 2. Recalibración dinámica de `θ_dyn`

Re-ejecutada sobre `tools/fixtures/control_corpus_100.txt` con el espectro de la
Fase B:

```
θ_dyn = P95(σ²(s_control)) = 0.044743
```

Registrada en `tools/audit_harness.py` (DoD), junto con el guard del contract 14D
(shape `(14,)`, norma `1.0`).

---

## 3. Verificación de hipótesis — FALSADA (resultado medido)

La hipótesis de diseño — "palabras cortas/repetitivas proyectan plano (σ² baja),
frases con tensión ontológica proyectan con asimetría clara (σ² alta)" — fue
**falsada empíricamente** bajo ambas bases candidatas. El hallazgo se documenta en
SPEC-TDD-028 §4, no se silencia.

| Entrada | σ² (base NSM real) | `max|s|` | prototipo dominante |
|---|---|---|---|
| `sol` (3 ch) | 0.0381 | 0.577 | `want` (0.577) — ruido de hashing |
| `y y y…` ×50 | 0.0481 | 0.618 | — |
| `casa` | 0.0524 | 0.667 | — |
| `pensar` / `pensamiento` | 0.0347 / 0.0505 | 0.769 / 0.839 | `happen` (0.839) |
| frase neutral 52 ch | 0.0351 | 0.811 | — |
| onto1 "Algo existe…" | 0.0408 | 0.814 | `something` (0.814) |
| onto2 "El ser es…" | 0.0286 | 0.750 | — |
| onto3 "Todo lo que existe…" | 0.0342 | **0.856** | `someone` (0.856) |

### Conclusiones empíricas

1. **σ² no discrimina contenido:** `casa` pasa (0.052), `onto1` rechazada (0.041).
   Mide concentración de energía, no densidad semántica.
2. **`max|s|` direcciona mejor** (cortas 0.58–0.67 vs onto3 0.86) pero da falsos
   positivos (`pensamiento` 0.839) y falsos negativos (`onto1` 0.814 < P95 0.853).
3. **El espacio 14D es irreductiblemente pérdida:** 3 caracteres → 1 n-grama → 1
   bucket. "sol" proyecta máximamente sobre `want`: ruido puro, no significado.
4. La base identidad es vacía; la base NSM real corrige la geometría pero no puede
   salvar la pérdida del hashing a 14D.

### Consecuencia de diseño

`σ²` en 14D es una métrica de **concentración espectral**, no una llave semántica de
consolidación. El parser queda como **Tier 1 determinista de representación**
(fases A/B/C y `θ_dyn` conservadas como calibración registrada); el gate semántico
pertenece al sustrato 384D con base geodésica real.

---

## 4. Matriz de pruebas (verificada)

| ID | Invariante | Estado |
|---|---|---|
| TEST-01 | dimensión `(14,)` float64 | ✅ |
| TEST-02 | `‖v‖₂ = 1.0` ± 1e-12 | ✅ |
| TEST-03 | fallback uniforme para vacío | ✅ |
| TEST-04 | determinismo bit a bit | ✅ |
| TEST-05 | sensibilidad morfológica `dot > 0.5` (calibrado) | ✅ |
| TEST-06 | `θ_dyn = P95(σ²_control)`, `0 < θ < 1` | ✅ |

---

## 5. Commits atómicos ejecutados

| Commit | Mensaje | Archivos | Δ |
|---|---|---|---|
| `ced6099` | `docs(kernel): add continuum-physics specifications and TDD-028 records` | 4 (3 documentos Kernel + SPEC-TDD-028.md) | +250 |
| `1e496a6` | `feat(parser): implement weightless 14D parser with spectral projection and TDD suite` | 5 (parser, 2 fixtures, tests, harness) | +599 |

Ambos mensajes en inglés, alineados con el estilo del repo.

---

## 6. Verificación final

```
python3 -m pytest tests/ -q        → 71 passed
python3 tools/audit_harness.py     → C1 GUARD PASSED (45%), θ_dyn=0.044743, contract 14D OK
TridenGuard (2 ciclos)             → VALIDATED / EXECUTE_SAFE
```

Sin dependencias nuevas; sin artefactos temporales; sin `try-except` que silencie.

### Estado git (sin commitear, intencional)

```
 M docs/architecture/ADR/ADR.md          ← modificación previa, ajena a este ciclo
?? docs/development/REPORTE_TRABAJO_2026-08-08.md
?? docs/development/SPEC-ARCH-028.MD
```

---

## 7. Siguiente paso recomendado

Si el objetivo es un **gate semántico funcional**, la vía es la opción (b) del audit:
percentil empírico sobre varianzas **observadas en ingesta 384D** (rolling quantile)
y re-proyección sobre la base geodésica real — no el parser 14D. El parser queda como
representación determinista Tier 1 y como componente de verificación de integridad.
