# Simulación del Kernel sobre Base Geodésica Real — Datos de la Prueba

**Script:** `traianus-simulation.py` (raíz)
**Fecha:** 2026-08-06
**DB:** `traianus.db` — tabla `geodesic_axes` (solo lectura, sin mutación)
**Kernel:** `traianus/core.py` (`calibrate_critical_threshold`, `evaluate_gate_v01`)

---

## 1. Objeto de la prueba

Sustituir los ejes sintéticos (`np.random` + Gram-Schmidt, ortonormales) por los
8 BLOBs reales de `geodesic_axes` y medir: densidad del tejido (θ_dyn),
comportamiento de la compuerta dual y validez de la Válvula Dimensional
384D → 385D.

## 2. Base geodésica real cargada

8 ejes, dimensión 384, L2-normalizados (norma = 1.0):

| Eje | Símbolo | Tag | Dim | \|\|v\|\|₂ |
|---|---|---|---|---|
| AXIS_1 | ▲ | _SOMETHING | 384 | 1.000000 |
| AXIS_2 | △ | _BE_BELOW | 384 | 1.000000 |
| AXIS_3 | ▴ | _TRUE | 384 | 1.000000 |
| AXIS_4 | ▵ | _BE_BIG | 384 | 1.000000 |
| AXIS_5 | ▶ | _HERE | 384 | 1.000000 |
| AXIS_6 | ▷ | _LONG_TIME | 384 | 1.000000 |
| AXIS_7 | ▸ | _BECAUSE | 384 | 1.000000 |
| AXIS_8 | ▹ | _KIND_OF | 384 | 1.000000 |

**No-ortonormalidad medida:** coseno fuera de diagonal media **0.2267**, máxima **0.3362**.
(Base anterior de la simulación: ortonormal → coseno 0.0. Ficción.)

## 3. Densidad del tejido (umbral dinámico)

`calibrate_critical_threshold()` — varianza de proyecciones **cruzadas** de la base,
excluyendo auto-proyección (i ≠ j, audit C1):

```
theta_dyn = 0.004292
```

- Con la base ortonormal sintética: `theta_dyn = 0.000000` (gate degenerado).
- Con la fórmula vieja de la simulación (`mean(cross²)`): `0.056346` (escala errónea).

## 4. Vector de prueba y espectro de proyección

Vector de prueba = mezcla convexa de dos primitivas reales (AXIS_1 + AXIS_2),
normalizada L2 (simula una ingesta focalizada).

| Proyección | Valor |
|---|---|
| p₁ (<v_d, e₁>) | +0.772054 |
| p₂ (<v_d, e₂>) | +0.772054 |
| p₃ (<v_d, e₃>) | +0.248010 |
| p₄ (<v_d, e₄>) | +0.325321 |
| p₅ (<v_d, e₅>) | +0.377084 |
| p₆ (<v_d, e₆>) | +0.225004 |
| p₇ (<v_d, e₇>) | +0.295496 |
| p₈ (<v_d, e₈>) | +0.299192 |

```
Media Espectral (p_bar)   = +0.414277
Varianza (sigma^2)        = 0.044516   (fricción)
```

## 5. Compuerta Dual

| Clave | Valor |
|---|---|
| Condición (σ² ≥ θ_dyn) | `True` (0.044516 ≥ 0.004292) |
| Ethical Key (HITL) | `True` |
| Estado | **CONSOLIDATED** |

**Contraste (gate ahora discriminante):** vector "ruidoso" uniforme (seed 42) →
varianza ≈ 0.003 < 0.004292 → **INCUBATING**. El umbral real separa nota focalizada
de nota genérica; ya no es un gate que siempre pasa.

## 6. Válvula Dimensional (384D → 385D)

1. Zero-padding de la entidad: `v_d+1 = [v_d; 0.0]` → shape `(385,)`.
2. Re-padding de los 8 ejes reales (cada uno `[e_i; 0.0]`).
3. Inyección del eje canónico `e_9 = [0, ..., 0, 1.0]`.
4. Recálculo del espectro en R³⁸⁵ (9 ejes): p₁..p₈ idénticos, **p₉ = +0.000000**.

```
Nueva varianza espectral (sigma^2) = 0.056520
```

## 7. Invariantes físicas (todas VERDE)

| Invariante | Resultado | Valor |
|---|---|---|
| 1. \|\|v₃₈₅\|\|₂ == 1.0 | ✅ | 1.000000 |
| 2. dim(e₉) == 385 | ✅ | — |
| 3. \|B_n+1\| == 9 | ✅ | — |
| 4. max\|⟨e_viejo, e_nuevo⟩\| == 0 | ✅ | 0.00e+00 |
| 5. ⟨v_d+1, e_nuevo⟩ == 0 | ✅ | 0.00e+00 |

**RESULTADO DE LA PRUEBA: PASÓ (VERDE)**

## 8. Conclusiones

1. La base real no es ortonormal; el modelo Gram-Schmidt era irreal y fabricaba
   un gate degenerado (θ = 0.0).
2. θ_dyn = 0.0043 es propiedad exclusiva de la base (8 BLOBs reales): estable y auditable.
3. El gate ahora discrimina: varianza espectral = "fricción"; consolidación requiere
   fricción ≥ densidad del tejido.
4. La Válvula Dimensional es un protocolo matemáticamente consistente: L2 = 1.0
   exacto, ortogonalidad absoluta del eje nuevo, espectro determinista.
5. Validación pendiente: el vector de prueba es sintético. Falta correr el criterio
   sobre embeddings reales de notas (`tools/audit_harness.py`) para confirmar que la
   varianza predice algo útil (WP1 del audit).
