# **CHANGELOG TÉCNICO: REFACTORIZACIÓN A KERNEL CINÉTICO (v1.0.0-alpha)**

Este documento detalla los cambios técnicos, estructurales y de nomenclatura que deben aplicarse a la base de código y a la arquitectura de datos para alinear la implementación de software con la nueva física vectorial continua establecida en el Tomo 1 y el Registro de Transición Logográfica.

## **\[REMOVED / DEPRECATED\] \- Eliminación de Arquitectura Clásica**

> * ---

>   **DEPRECATED \- Nomenclatura Histórica:** Se eliminan todas las referencias a clases, módulos o archivos nombrados Traianus o Ulpia.  
> * **REMOVED \- Timestamps y Módulos de Tiempo (WP3):** Se elimina cualquier estructura de datos basada en cronología lineal (ej. created\_at, updated\_at). El tiempo como variable independiente deja de existir en el esquema de base de datos.  
> * **REMOVED \- Curvatura Topológica:** Se desechan las funciones diseñadas para "doblar" o curvar el espacio de proyección.  
> * **DEPRECATED \- Interfaces 2D Estáticas:** Se suspende el desarrollo de cualquier *frontend* basado en lienzos estáticos o grafos de nodos fijos.

## **\[CHANGED\] \- Refactorización Estructural**

> * ---

>   **CHANGED \- Nomenclatura del Core:**  
  * Traianus\_DB o módulo de almacenamiento pasa a ser **Sustrato Latente** (Tensor Field).  
  * Traianus\_Engine pasa a ser **Kernel Cinético**.  
  * Ulpia\_Render pasa a ser **Matriz de Proyección**.  
> * **CHANGED \- Gestión de Memoria y Coordenadas:** En lugar de guardar vectores de posición estática (coordenadas cartesianas fijas) para cada entidad, el sistema ahora debe calcular y persistir el **Espectro de Autovalores (λ)** de la matriz de deformación generada durante la colisión.  
> * **CHANGED \- Condición de Expansión (d → d+1):** La lógica de añadir dimensiones pasa de ser una regla heurística a un límite termodinámico. El eje *d+1* solo se inyecta cuando el cálculo de la fricción (basado en la varianza espectral de las proyecciones) supera el umbral dinámico de densidad de la región actual.

## **\[ADDED\] \- Nuevas Implementaciones (Mecánica Física)**

> * ---

>   **ADDED \- Cálculo de Fricción Geométrica:** Implementación de la métrica de fricción basada en el gradiente de densidad vectorial local. Este valor sustituye al "tiempo" y define la resistencia de una trayectoria.  
> * **ADDED \- Válvula Dimensional Ortogonal:** Protocolo estricto para inyectar vectores \[0, 0, ..., 1.0\] (Zero-Padding) asegurando ortogonalidad absoluta (⟨eviejo, enuevo⟩ \= 0\) y preservando invariablemente la norma L2 \= 1.0.  
> * **ADDED \- Arquitectura Orientada a Eventos Asíncronos (SPAIC-ready):** La capa de entrada de datos (*Ingestion Layer*) debe ser refactorizada para operar *clockless* (sin reloj de muestreo maestro), preparándose para recibir *spikes* (pulsos cinéticos asíncronos) directamente basados en la superación de umbrales tensionales (compatible con Hardware Neuromórfico y Teorema de Takens m=5).

## **Hoja de Ruta Inmediata (Next Steps)**

> 1. ---

>    **Prueba Unitaria de la Válvula Dimensional:** Ejecutar la simulación en Python (traianus-simulation.py adaptada a los nuevos nombres) para validar el paso matemático estricto de *384D → 385D*.  
> 2. **Definir Estructura del Tensor:** Crear el esqueleto en Rust/C++ (o lenguaje definitivo) del Kernel Cinético, centrándose exclusivamente en la ingesta, normalización y cálculo de varianza de un solo vector frente a la base.  
> 3. **Pausar Capa de Proyección:** No escribir código para la Matriz de Proyección hasta que el sustrato matemático N-dimensional devuelva los autovalores correctamente en la terminal cruda.