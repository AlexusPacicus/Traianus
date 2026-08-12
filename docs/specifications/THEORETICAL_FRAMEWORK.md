Marco Teórico de Traianus: Hidrodinámica de Campos, Descomposición de Helmholtz y Alivio Dimensional (d→d+1)
Estado: Borrador / Especificación

Dominio: Física del Sustrato y Álgebra Nucleares

Autores: Equipo Núcleo de Traianus

1. El Campo Unificado y el Marco en Reposo (La "Piscina")
Traianus no modela el espacio de estados como una colección de vectores discretos en un espacio vacío, sino como una variedad geométrica continua y unificada.
Variedad Monista: Los vectores de datos entrantes v y el estado acumulado S_n son proyecciones locales de una única entidad de mayor dimensión.
Marco en Reposo (B_0): El sustrato mantiene una base ortogonal geodésica B_0 ∈ R^{k×d} que representa al sistema en equilibrio no deformado.
Régimen Irrotacional: En equilibrio, el campo se comporta como un flujo potencial irrotacional:
∇×v=0
En este régimen, la información atraviesa el sustrato con cero fricción interna y cero dismorfismo.

2. Presión Espacial, Dismorfismo y Vorticidad (El "Río")
Cuando entran nuevas perturbaciones al sustrato bajo alta densidad de flujo, la compresión espacial fuerza a las trayectorias a desviarse de la ortogonalidad.
Dismorfismo (D): Cizalladura inducida por compresión sobre los ejes ortogonales locales.
Flujo Solenoidal y Vorticidad (ω): La sobrecompresión impide la relajación en línea recta, plegando la energía en vorticidad local:
ω=∇×v
≠0
Resistencia Cinética (K_cin): Es la métrica física del kernel. Mide la fricción/trabajo interno necesario para reasimilar el vórtice dentro del sustrato:
K_cin = 2/1 ||Δv||^2 ⋅(1+Var(v B_0^T))

3. Alivio Dimensional y Re-ortogonalización (d→d+1)
Para evitar el rasgado de la variedad o el colapso de rendimiento bajo alta presión espacial, el sustrato activa una válvula de aumento escalar.
Mapeo de Aumento: El vector de coordenadas v∈R^d se mapea incondicionalmente a v^ ∈ R^{d+1}:
v^ = (v_1, v_2, ..., v_d, K_cin)
Desenrollado del Vórtice: La coordenada (d+1)-ésima absorbe la energía cinética solenoidal. Lo que en d dimensiones se manifiesta como un vórtice turbulento, en d+1 dimensiones se relamina en una trayectoria suave y ortogonal.
Puerta (Gating) mediante θ_dyn: El umbral dinámico θ_dyn evalúa la coordenada (d+1)-ésima para determinar si el estado se consolida, pasa a cuarentena o se deniega:
Puerta de Estado={
Consolidar
Cuarentena / Adaptar
si K_cin ≤ θ_dyn
si K_cin > θ_dyn

4. Taxonomía Doble de lo "Nuevo"
                               ┌── Novedad Dinámica (Vorticidad / Presión Temporal)
                               │   ├─ Agitación cinética local dentro de d dimensiones.
                               │   └─ Absorbida en la coordenada (d+1) mediante K_cin.
Taxonomía de lo "Nuevo" ───────┤
                               └── Novedad Estructural (Descubrimiento de la Variedad)
                                   ├─ Revelación de ejes ocultos de la entidad.
                                   └─ Dispara la actualización de la base B_0.
Novedad Dinámica: Turbulencia transitoria causada por velocidad de flujo o ruido local. Se mide mediante K_cin sin modificar B_0.
Novedad Estructural: Expansión del territorio visible del dominio. Requiere re-alinear B_0 para incorporar los nuevos ejes ortogonales de la entidad hiperdimensional.

5. Hipótesis Experimentales Falsables
H1 (Presión y Vorticidad): El aumento de densidad de puntos dentro de d dimensiones fijas incrementa de forma monótona la vorticidad ω y el dismorfismo cinético K_cin.
H2 (Alivio Dimensional): Proyectar vectores sobrecomprimidos a R^{d+1} mediante aumento escalar cinético restaura la ortogonalidad relativa e incrementa la laminaridad de la trayectoria.
H3 (Discriminación de Novedad): La relación entre la disipación K_cin y la distancia de proyección a la base separa estrictamente el ruido/anomalías transitorias de las actualizaciones estructurales reales de la base.