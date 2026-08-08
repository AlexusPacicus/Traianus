SPEC-ARCH-028: ESPECIFICACIÓN ARQUITECTÓNICA Y REFACTORIZACIÓN COMPLETA TIER 1
1. Diagnóstico Forense y Ruptura Conceptual
El análisis empírico sobre el Manifiesto (Sua Potestas, 151 párrafos) y las auditorías de diseño sobre PoC v1.0 expusieron los límites de la arquitectura comercial previa:  
ZIP
+ 3
Sesgo de Correlación Inter-Ejes: Los 8 ejes geodésicos extraídos con all-MiniLM-L6-v2 presentaban un coseno fuera de diagonal promedio de 0.2267 (máximo 0.3362), reflejando inercia estadística de internet en lugar de geometría de pensamiento.  
ZIP
+ 1
Inestabilidad de Frontera (θ 
dyn
​	
 ): Variaciones insignificantes de fricción (±0.0001) decidían arbitrariamente la ejecución de la Génesis Logográfica (d→d+1) o la retención en incubación.  
ZIP
Fricción Informativa Clásica: El modelo pretendía encajar campos continuos en cronologías de tiempo lineal, relojes maestros y visualizaciones 2D fijas.  
CHANGELOG TÉCNICO: REFACTORIZACIÓN A KERNEL CINÉTICO
+ 1
2. Decisión Fundacional: ADR-028 y Cambio Nomenclatural
Se decreta el descarte de redes neuronales estocásticas y la transición a un Proveedor Analítico No Paramétrico y Weightless (NSM 1972).  
ZIP
+ 1

A. Redefinición de Nomenclatura del Sistema
Sustrato Latente (Tensor Field): Sustituye a la denominación histórica de almacenamiento (Traianus_DB).  
CHANGELOG TÉCNICO: REFACTORIZACIÓN A KERNEL CINÉTICO
+ 2
Kernel Cinético: Sustituye al motor de procesamiento (Traianus_Engine).  
CHANGELOG TÉCNICO: REFACTORIZACIÓN A KERNEL CINÉTICO
+ 2
Matriz de Proyección: Sustituye a la capa de observación (Ulpia_Render).  
CHANGELOG TÉCNICO: REFACTORIZACIÓN A KERNEL CINÉTICO
+ 2
B. Base Atómica Inicial (R 
14
 )
Se adoptan las 14 primitivas universales originales de Anna Wierzbicka (1972) como base I 
14×14
​	
  ortonormal pura (coseno fuera de diagonal 0.0).  
ZIP
Cero dependencias pesadas (PyTorch/Transformers)[cite: 1, 2], consumo de RAM <1 MB y determinismo bit a bit absoluto.  
ZIP
+ 1
3. Capa de Representación (Tier 1): Feature Hashing sobre N-Gramas
Para evitar el uso de diccionarios manuales ("palabras mágicas") y la rigidez de filtros literales, la vectorización a v∈S 
d−1
  ejecuta el siguiente pipeline:

Plaintext
[ Texto Crudo ] ──► [ Extracción 3-5 Gramas ] ──► [ Feature Hashing ] ──► [ Normalización L2 ] ──► v ∈ Sᵈ⁻¹
Subcadenas (n-gramas): Extracción de fragmentos de 3 a 5 caracteres (pen, ens, sient) para capturar variaciones morfológicas y neologismos de forma determinista.  
ZIP
Hashing Trick: Algoritmo determinista (MurmurHash3 / xxHash) que asigna subcadenas a índices k∈[0,d−1] con asignación de signo (+1 / -1) para neutralizar colisiones acumulativas.  
ZIP
Invariante L 
2
​	
  Estricto: Escalamiento ∥v∥ 
2
​	
 =1.0 para satisfacer la norma de conservación de energía del Kernel Cinético.  
ZIP
4. Física del Continuo, Autovalores y Geometría de Gärdenfors
A. Envoltura Geodésica Esférica (SLERP)
En S 
d−1
 , las combinaciones lineales euclídeas rectas cortan el interior del espacio, destruyendo la norma (∥v(λ)∥ 
2
​	
 <1.0). La trayectoria entre estados se restringe a la envoltura geodésica esférica:  
ZIP

v(λ)= 
sinθ
sin((1−λ)θ)
​	
 A+ 
sinθ
sin(λθ)
​	
 Bdonde cosθ=⟨A,B⟩
Esto garantiza ∥v(λ)∥ 
2
​	
 =1.0 en toda la trayectoria, conservando la masa del vector.  
ZIP

B. Espectro de Autovalores (λ) y Fricción
Registro por Autovalores (λ): La memoria no almacena posiciones cartesianas estáticas, sino el Espectro de Autovalores (λ) de la matriz de deformación generada tras la colisión.  
CHANGELOG TÉCNICO: REFACTORIZACIÓN A KERNEL CINÉTICO
+ 2
Resonancia: La recuperación de conocimiento opera por sintonía armónica con la firma λ en lugar de búsquedas relacionales clásicas.  
REGISTRO DE TRANSICIÓN LOGOGRÁFICA
+ 1
Fricción Geométrica (σ 
2
 ): Reemplaza al tiempo lineal. Mide el trabajo de deformación topológica necesario para absorber el vector.  
CHANGELOG TÉCNICO: REFACTORIZACIÓN A KERNEL CINÉTICO
+ 4
C. Naturaleza de las Aristas (E 
n
​	
 )
Las aristas ϵ-edges (ϵ=0.8) no son punteros o relaciones fijas; representan trazos o huellas cinéticas de tensión activa que sostienen el equilibrio elástico de la hiperesfera.  
ZIP
+ 3

5. Transducción Biofísica y Somática
El Kernel Cinético acopla su física vectorial con la fisiología del observador mediante tres mecanismos:
Reconstrucción Topológica de Takens (m=5): Encastre en dimensiones ortogonales para preservar los atractores caóticos somáticos sin necesidad de muestreo fragmentado.  
REGISTRO DE TRANSICIÓN LOGOGRÁFICA
Física de Solitones (KdV): Las colisiones de trapecios/politopos se comportan como solitones hemodinámicos (ondas no dispersivas que no pierden su energía al propagarse).  
REGISTRO DE TRANSICIÓN LOGOGRÁFICA
Ingesta Clockless (SPAIC / MHD): La capa de entrada opera sin reloj de muestreo maestro, procesando spikes (pulsos cinéticos asíncronos) gatillados al superar el umbral tensional.  
CHANGELOG TÉCNICO: REFACTORIZACIÓN A KERNEL CINÉTICO
+ 1
6. Indexación Voronoi Esférica (O(K)) y Expansión Dimensional
Partición por Células Voronoi: El espacio se divide en regiones convexas sobre S 
d−1
  delimitadas por los K ejes prototipo activos (K≪N):
  
ZIP
C 
i
​	
 ={v∈S 
d−1
 ∣⟨v,p 
i
​	
 ⟩>⟨v,p 
j
​	
 ⟩∀j

=i}
Enrutamiento Asíncrono: La API responde en O(K) asignando la célula C 
i
​	
  al nodo. Un worker asíncrono calcula las adyacencias ϵ-edge de forma acotada a C 
i
​	
  y sus células colindantes.  
ZIP
+ 1
Válvula Dimensional (d→d+1): Cuando la varianza local de una célula supera el límite elástico (σ 
2
 (C 
i
​	
 )≥θ 
dyn
​	
 ), se inyecta el eje ortogonal e 
d+1
​	
 =[0,…,1.0] con zero-padding, bisecando la célula saturada sin deformar la ortogonalidad previa.  
CHANGELOG TÉCNICO: REFACTORIZACIÓN A KERNEL CINÉTICO
+ 4
7. Depreciación Formal de Atributos Clásicos y Parámetros
A. Elementos Removidos / Deprecados
Timestamps Lineales: Eliminación de created_at y updated_at en la base de datos. El tiempo se mide como Fricción Geométrica.  
CHANGELOG TÉCNICO: REFACTORIZACIÓN A KERNEL CINÉTICO
+ 3
Curvatura Espacial: Se elimina el doblado del espacio; se mantiene ortogonalidad estricta (⟨e 
i
​	
 ,e 
j
​	
 ⟩=0) y la tensión se expresa como gradiente de densidad.  
CHANGELOG TÉCNICO: REFACTORIZACIÓN A KERNEL CINÉTICO
+ 2
B. Matriz de Parámetros Invariantes
Parámetro / Invariante	Valor / Regla	Estado / Ubicación
Dimensión Base Inicial	d=14 (I 
14×14
​	
 , ortogonalidad 0.0)	
traianus/bootstrap.py

  
ZIP
Invariante Vectorial	∥v∥ 
2
​	
 =1.0 (Norma L 
2
​	
  estricta)	
traianus/core.py

  
ZIP
Firma de Memoria	Espectro de Autovalores (λ)	
Sustrato Latente  
CHANGELOG TÉCNICO: REFACTORIZACIÓN A KERNEL CINÉTICO
+ 2

Distancia Adyacente	ϵ=0.8 (E 
n
​	
  observacional / trazo cinético)	TRAIANUS_EPSILON_EDGE[cite: 1, 4]
Calibración Umbral (θ 
dyn
​	
 )	Percentil 95 (P 
95
​	
 ) sobre corpus neutro (100 frases)	
tools/audit_harness.py

  
ZIP
Persistencia	Append-only inmutable keyed por (id, seq) en WAL	
manifold_nodes / manifold_edges

  
ZIP