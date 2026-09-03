# ADR-025: Unified Spatial Control & Schema Partitioning
**Estatus:** Aprobado
**Fecha:** Septiembre 2026
**Área:** Arquitectura de Sustrato, Telemetría Cinemática e Ingesta
---
## 1. Contexto y Problema
Durante el ciclo de desarrollo del módulo `PolarProjector` y la posterior auditoría técnica, emergieron tres deficiencias estructurales críticas que impiden unificar la arquitectura e integrar la PoC:
1. **Inconsistencia y Colisión de Esquemas (`storage`):** Coexistían dos visiones de persistencia en `traianus.db` sin una jerarquía clara:* **Plano de Datos (`data_plane`):** Registro *append-only* inmutable de coordenadas continuas completas ($d=384$ o superior) para reconstrucción histórica.* **Plano de Control (`manifold_nodes` / `manifold_edges`):** Grafo de ejecución rápido que indexa la topología de estados activos.

La falta de formalización y la reestructuración del archivo `traianus/storage.py` al paquete `traianus/storage/` provocaron la duplicación de responsabilidades y la rotura de referencias globales (`DB_PATH`) en módulos de utilidades y pruebas.2. **Vulnerabilidad de Evasión en la Telemetría EWMA (Trigger Invertido):** El diseño previo establecía un disparador de recalibración unidireccional cuando el ratio de varianzas superaba un umbral superior $\theta$. En condiciones de prueba con datos reales, una ráfaga (*burst*) de estímulos desalineados o una inyección semántica incrementa la dispersión del denominador ($d_{esc}$), provocando que el ratio colapse drásticamente (de ~200 a ~3). Esto permite a un atacante evadir la alerta manteniendo la anomalía por debajo del umbral superior.3. **Huérfano de Integración (`PolarProjector` como Código Muerto):** A pesar de contar con un 100% de cobertura de pruebas unitarias y de propiedades, el `PolarProjector` no estaba enlazado al flujo transaccional de `/ingesta` en `app.py`, manteniendo el sistema dependiente de evaluaciones geométricas continuas estáticas.
---
## 2. Decisiones de Diseño
### 2.1. Partición Jerárquica de Almacenamiento y Compatibilidad de Interfaz
* **Plano de Datos como Fuente Única de Verdad Inmutable (`data_plane`):** Almacena de forma persistente y estrictamente en modo *append-only* las coordenadas semánticas en bruto (`float64`). Esta tabla nunca se edita ni se trunca.* **Plano de Control como Caché Materializada Volátil (`manifold_nodes` / `manifold_edges`):** Es una proyección de ejecución optimizada para SQLite WAL. Si el *codebook* se actualiza o se re-ortogonalizan los ejes, las tablas del Plano de Control se pueden limpiar (`DELETE` / `TRUNCATE`) y reconstruir asíncronamente leyendo las coordenadas secuenciales de `data_plane`.* **Compatibilidad de Paquete (`storage`):** La estructura interna `traianus/storage/` debe re-exportar explícitamente la constante `DB_PATH` desde `traianus/storage/__init__.py`. Esto garantiza compatibilidad inversa total para los scripts de `tools/` y pruebas sin parches directos de inyección de rutas.
### 2.2. Banda de Tolerancia Bidireccional (Schmitt Trigger EWMA e Histéresis Ortogonal)
El diagnóstico de varianza evoluciona a un **Schmitt Trigger bidireccional con zona de histéresis**:
$$\text{Disparar Alerta} = \left( \text{Ratio}_{EWMA} > \theta_{upper} \right) \lor \left( \text{Ratio}_{EWMA} < \theta_{lower} \right)$$
$$\text{Reset Alerta} = \theta_{lower} + \Delta < \text{Ratio}_{EWMA} < \theta_{upper} - \Delta$$
Donde:
* **Ratio:** Proporción de varianzas $\frac{\sigma^2_\lambda}{\sigma^2_{esc}}$.* **Umbral Inferior ($\theta_{lower} \approx 10.0$):** Captura el colapso de señal por ráfagas de desalineación o inyecciones semánticas.* **Umbral Superior ($\theta_{upper} \approx 500.0$):** Captura la concentración anómala o sobreajuste en el eje semántico actual.* **Banda de Histéresis ($\Delta$):** Margen de amortiguación para evitar oscilaciones continuas del disparador en los límites de la banda.
**Garantía de Ortogonalidad en el Reset:** Al activarse la recalibración por salida de banda, la reconstrucción de la base del vórtice ($c_1, u, u^\perp$) desde el Plano de Datos exige forzar la re-proyección ortogonal de Gram-Schmidt para asegurar de forma estricta que:
$$u^\perp \cdot u = 0$$
### 2.3. Cierre del Circuito: Integración Obligatoria en `/ingesta`
El flujo de entrada en `app.py` ejecutará la siguiente secuencia determinista:
1. **Escritura Incondicional:** Persistir el vector entrante $v_n$ en `data_plane` en `float64`.2. **Proyección Cinemática 8D:** Invocar `PolarProjector` con guarda de vector nulo sobre la base $u^\perp$ activa para calcular el voltaje escalar $\lambda \in [-1, 1]$ y la distancia de escape $d_{esc}$.3. **Evaluación de Telemetría:** Pasar las métricas por el `VarianceTracker` con el Schmitt Trigger bidireccional.4. **Actualización de Caché:*** **Dentro de Banda:** Insertar/Actualizar el estado en `manifold_nodes` ($O(1)$ en SQLite WAL).* **Fuera de Banda:** Congelar temporalmente la actualización del Plano de Control y disparar el proceso asíncrono de re-ortogonalización y recalibración de la base desde `data_plane`.


---
## Enmienda A1 (implementación, misma rama)
* **Escritura validada, no incondicional (§2.3 paso 1 enmendado):** la validación (encode, base no vacía, dimensiones, proyecciones, polar, EWMA) precede a CUALQUIER `INSERT`; `data_plane` + revisión `manifold_nodes` + `mark_queue_processed` commitean en UNA transacción. Un fallo deja cero filas (sin huérfanos).
* **DDL único:** `traianus/storage/_storage.py` (`*_DDL`) es la única fuente; `SQLiteEngine`, `db_factory.py` y el validador (`audit_log`) la consumen.
* **Desambiguación:** `manifold_nodes.event_type CHECK (ERROR | RECALIBRATION_SIGNAL) DEFAULT 'ERROR'`; `/telemetry` lo expone. Sin nuevo lifecycle state (compatible con AGENTS.md §4.2).
* **`control_plane`:** DDL presente, sin cablear al pipeline (decisión pendiente).

## 3. Consecuencias y Beneficios
* **Consistencia de Código:** Desaparecen las colisiones en la inyección de rutas de base de datos al estabilizar `traianus/storage/__init__.py`.* **Seguridad Defensiva:** Inmunidad contra ataques de evasión semántica por inyección de ruido o vectores desalineados gracias a la detección en la banda inferior $\theta_{lower}$.* **Evolución Ontológica sin Pérdida:** Posibilidad de re-indexar o alterar el grafo de control en cualquier momento sin riesgo de corrupción o pérdida de histórico, manteniendo `data_plane` intacto.* **Eliminación de Código Muerto:** Activación del `PolarProjector` directamente en la tubería de producción de FastAPI.
