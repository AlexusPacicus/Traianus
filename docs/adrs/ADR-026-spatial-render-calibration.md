# ADR-026: Calibración de Render Espacial Congelada por Época

**Estatus:** Aprobado
**Fecha:** Septiembre 2026
**Área:** Geometría Observacional, Contrato Espacial Ulpia

---

## 1. Contexto y Problema

`derive_spatial_observables` derivaba `x, y, z` de un SVD sobre la matriz de proyecciones de **un solo nodo**, reformada a `(1, k)`. Restarle su media por columnas anula la matriz, de modo que la SVD devolvía `S = 0` y **todos los nodos se renderizaban en el origen**. La suite pasaba en verde porque los tests solo comprobaban finitud, nunca valor.

El defecto no admite parche menor: una matriz `(1, k)` tiene rango 1, así que ni siquiera sin centrar podría producir tres coordenadas independientes. Una SVD necesita población; una función pura por nodo no la tiene.

Al sustituirla por la lectura directa del `PolarProjector` emergieron dos problemas distintos, medidos sobre el corpus Spinoza congelado (n = 2.221, `tools/experiments/measure_polar_render_range.py`):

1. **Redundancia analítica de `d_esc`.** Sobre `S^{d-1}` con ancla unitaria y `z = ⟨v, ĉ₁⟩`:

   ‖r‖² = ‖v − c₁‖² − ⟨v − c₁, ĉ₁⟩² = (2 − 2z) − (z − 1)² = 1 − z²

   d_esc² = ‖r‖² − λ²‖v_dipole‖² = **1 − z² − λ²‖v_dipole‖²**

   La distancia de escape queda determinada por `(λ, z)`. Empíricamente: `corr(tanh d_esc, z) = −0.968`, y la tercera componente principal de la posición vale el **1.03%** de la varianza estandarizada.

2. **Rango dinámico degenerado.** Las coordenadas crudas ocupan bandas estrechas: `λ` cubre el 7.16% de `[-1,1]`, la componente sobre el ancla el 19.07%. La caja envolvente `x-y` cubría el **1.36%** del viewport.

## 2. Decisiones de Diseño

### 2.1. La posición es 2D: `(λ, ⟨v, ĉ₁⟩)`

`x` es el voltaje sobre el dipolo, `y` la componente sobre el ancla. Ambos son independientes entre sí (`corr = +0.137`).

`d_esc` **NO** es canal de posición: promoverlo a eje amplificaría ruido de coma flotante (sd = 0.0036) hasta convertirlo en estructura aparente. Permanece en el canal cromático `h`, donde su dispersión estrecha no necesita amplificación.

`z` queda reservado y constante a `0.0`. Recuperar un tercer eje genuino exige un **segundo dipolo** (ejes geodésicos cuarto y quinto por ranking), no un reescalado del primero. Queda fuera de alcance.

### 2.2. Calibración afín congelada por época

`SpatialCalibration` aplica `clip((v − μ) / (k·σ), −1, 1)` con `k = 3` por defecto. Las constantes se ajustan **una vez por época** y se persisten bajo esa etiqueta.

La alternativa —calcular `(μ, σ)` sobre la población en cada petición— fue descartada: cada ingesta cambiaría las constantes y por tanto movería todos los nodos ya colocados. Ése es exactamente el drift incremental que el §1 del manuscrito usa como argumento contra t-SNE y UMAP; adoptarlo aquí sería contradecir la tesis del operador.

Congelada por época, la posición de un nodo es estable durante toda la vida de la época y solo se mueve en un evento de recalibración explícito y registrado.

Verificación empírica sobre el mismo corpus: la caja envolvente pasa del **1.36% al 91.82%** del viewport, con 30/2221 nodos (1.4%) recortados en el borde, consistente con `k = 3σ`.

### 2.3. Persistencia append-only

Tabla `spatial_calibration` con `PRIMARY KEY (epoch_provenance, seq)`. Un reajuste INSERTA `seq+1`; las constantes superadas permanecen legibles (AGENTS 4.1: nunca `UPDATE` ni `DELETE`). Cada fila registra además `sample_size`, de modo que es auditable contra qué población se ajustó y cuándo se movieron las posiciones renderizadas.

`get_active_spatial_calibration` devuelve `None` cuando la época nunca se ha calibrado. `None` es un "aún sin calibrar" honesto, no un fallo enmascarado (AGENTS 1.3): el endpoint renderiza coordenadas polares crudas —nube estrecha pero fiel— hasta que exista un ajuste.

## 3. Consecuencias

* **Contrato de 6 canales con un canal muerto.** `z` es constante. El bloque binario de 64 B (`zero_copy.py`, `binary.ts`, el shader) no cambia: se conserva la ranura con valor documentado en vez de romper el contrato zero-copy.
* **Impacto en el manuscrito.** Las §2-§3 tratan `(λ, d_esc)` como el par de salida del operador. La identidad de §1.1 de este ADR obliga a reformular: el par informativo sobre la esfera unidad es `(λ, ⟨v,ĉ₁⟩)`. No invalida ninguna Proposición —`d_esc` sigue siendo la norma que el paper afirma— pero sí cambia qué se afirma que se está midiendo.
* **Redundancia cromática resuelta.** Con `y` en la componente sobre el ancla, `h` deja de duplicar `y` y `c` deja de duplicar `x`.

## 4. Punto Abierto: Disparador del Reajuste

La tabla se lee pero **nada la escribe todavía**. El disparador natural parecía el evento de recalibración del Schmitt Trigger (ADR-025 §2.2), pero la medición lo desaconseja: el arnés de auditoría emite `recalibration_triggered` en prácticamente **cada ingesta** (banda `ALERT_LOW` sostenida). Enganchar el reajuste ahí movería las posiciones continuamente — precisamente el drift que §2.2 de este ADR existe para evitar.

El disparador necesita política propia (cambio de época, acción explícita del operador, o crecimiento de la población por encima de un factor). Queda sin decidir; hasta entonces `/spatial` sirve coordenadas crudas.
