# Puentes relacionales entre celdas — documento en palabras

> Pieza inicial cerrada en chat solo con documentación y análisis, sin código.
> Lenguaje natural matemático, sin fórmulas. Estado a corte del merge del grafo
> relacional en main. Todo lo apuntado como futuro queda marcado y sin desarrollar.
>
> **Versión uno congelada el 2026-09-27 y ampliada por piezas validadas
> después.** Solo se reabre por el veredicto editorial pendiente: si quitar
> las notas puras mueve alguna decisión cerrada, se apunta aquí sin reabrir
> piezas.

## 1. Propósito y límites

Este documento fija una sola pieza: cómo se juzga una relación entre notas de
zonas distintas tratándola como su propia esfera de vecindario. No cambia el
motor, no cambia pruebas, no crea redes. Sirve para decidir después qué grafo
usa la vista general y el zoom relacional. La variante que sumaría mínimos de
puentes ya validados queda apuntada pero sin desarrollar.

## 2. Reparto con todos los ejes

Cada nota se considera con todos los ejes a la vez, con su lista completa de
afinidades. El eje con el que más se alinea sirve solo como etiqueta para contar
y ordenar. Ninguna nota queda encerrada en una sola celda. Las zonas son
vecindarios que se solapan: una nota puede estar a la vista en más de una, con
distinto grado. Este punto corrige el reparto anterior por dominante único.

## 3. Esferas individuales y modulares

Cada zona guarda lo suyo y nada más: qué notas tiene a la vista, quiénes son
sus vecinos reales, y cuál es su umbral propio. Solo cuando cada esfera está
cerrada así se permite componerlas. Primero individuales, después con ellas lo
que queramos: unirlas para la vista general, anidar la fina dentro de la gruesa
al bajar a subespacio, o comparar variantes sin mezclar medidas.

## 4. Esfera del puente

Para cada pareja de notas de zonas distintas que aspire a relacionarse, se
construye su esfera de puente: el conjunto de vecinos reales de ambos extremos
que seguirían cercanos si se mirase a través de ese puente. Esa esfera es
distinta de las dos de origen y es lo que se juzga.

## 5. Tensión como medida que decide

Por tensión entendemos el esfuerzo de encaje entre las dos esferas de origen y
la del puente. Un puente se mantiene cuando acerca sin forzar, como una línea
que se acorta trayendo vecinos reales cerca. Se descarta cuando solo une a
costa de dispersar lo que cada zona conservaba, apretando de lado. Como imagen
de ayuda, sin valor de ley, usamos la de acortar frente a dispersar.

## 6. Listón dinámico de cada zona

El umbral que decide no es un número puesto a mano para todo. Nace de cada zona
a partir de sus enlaces mínimos, los más baratos que ya la conectan por sí
solos. Cada zona tiene el suyo, más exigente donde es compacta y más abierto
donde es dispersa. Con los puentes que quedan a la altura de ese umbral, más los
enlaces mínimos que garantizan conexión, se reconstruye la esfera de la zona.
Lo descartado se cuenta para medir recuperación.

## 7. Referencia ciega al azar

La vara de medir son direcciones elegidas sin haber mirado nunca a los vecinos
ni al texto, fijadas de antemano con semilla escrita. Si un puente pide menos
esfuerzo que casi todas ellas, se mantiene. Las direcciones nacidas del propio
corpus, sesgadas hacia donde el corpus ya varía, quedan de momento como testigo
descriptivo pendiente de revisión, sin poder decidir.

## 8. Direcciones de menor esfuerzo y giro al fusionar

Cada esfera guarda sus direcciones donde menos se estira. Al unir dos zonas con
un puente aparece una dirección nueva para la vista conjunta. Si el puente es
honesto, esa dirección gira poco respecto a las que cada zona traía. Si fuerza,
se desvía para compensar. La revisión acordada para esta pieza usa ese giro como
análisis del estado: se parte de una dirección artificial sin valor, se mira
únicamente cuánto gira hasta la dirección nueva, y ese giro revela la dirección
del estado que el puente propone. Nivel de esfuerzo y giro se prueban en
paralelo sin verse, y sus acuerdos y desacuerdos dirán si el giro entra en la
medida o queda como veto aparte.

## 9. Caso no concluyente y bajada a subespacio

Si la tensión apenas varía en el conjunto completo, el resultado se declara no
concluyente y no se rellena a mano. Eso dispara el trabajo dentro de cada zona
por separado: primero en la celda gruesa de eje, y si hace falta en la celda
fina que el zoom ya define, siempre con partición comprometida de antemano y
nunca recortando a gusto. Cada nivel calcula su propio umbral y sus propias
direcciones. Un tercer nivel más fino queda apuntado pero sin abrir.

## 10. Red única y familia para probar

Se mantiene una candidata única y escasa para la vista general junto a la
familia de variantes sobre el mismo corpus congelado. La de tensión es la única
que decide con la medida nueva; las demás solo informan para comparar. El orden
de fusión del resto y la elección final entre red única y familia quedan como
desarrollo futuro.

## 11. Lo que dicen los avances ya medidos

Con el umbral único heredado, más de un tercio de las notas queda sin ninguna
relación y el resto se reparte en cientos de islas. La unión con el árbol mínimo
da por primera vez un solo componente conexo con pocas relaciones por nota y
cero aisladas. Con umbral por celda salen cientos de miles de relaciones,
demasiado denso para mostrar. Con la mediana por celda se baja a unas tres mil
seiscientas relaciones conectadas, con caminos medianos de una docena de saltos.
Abriendo las fronteras entre celdas quedan unas tres mil trescientas, con algo
más de un millar cruzando entre celdas, y caminos medianos algo más largos.
Esa variante abierta recupera del orden de mil quinientas parejas cruzadas que
la mediana perdía y que tocaban a más de ochocientas notas. Para más de la mitad
de las notas, su vecina más próxima vive fuera de su etiqueta dominante, lo que
confirma el reparto con todos los ejes.

El zoom queda redefinido por el autor como movimiento por continuidad relacional
desde la nota elegida, con profundidad por longitud del camino más corto y
alcance por componente conexa. El cociente entre camino y distancia directa se
lee como relación proyectada, no como coste. La puntuación del zoom no se puede
comparar con la de vecindario por tener distinta base.

El constructor del corpus dejó pasar bloques editoriales de notas al pie dentro
de los manifiestos: más de una decena de bloques, unas veinticinco etiquetas
entre puras y mixtas, y unas cuarenta continuaciones candidatas. Están marcados
desde la fuente sin reconstruir el corpus. Queda pendiente comprobar si quitar
las notas puras cambia alguna decisión de los estudios cerrados.

## 12. Orden de fusión con dirección primero

La fusión es la fusión entre hiperesferas, en el orden escrito antes de
fusionar y nunca tras ver el dibujo. Primero lo interno de cada zona que ya
pasó su umbral, después los puentes ordenados por menor esfuerzo y menor giro,
y al final los enlaces mínimos solo donde falte conexión. Cada esfera fundida
conserva su zona de origen, su esfuerzo y su giro, y si nació en subespacio en
qué nivel.

Ante cada puente candidato se calcula primero la dirección de menor esfuerzo
de su vista conjunta. Con esa dirección ya en la mano se mide el esfuerzo y el
giro frente a las direcciones de origen. Solo entonces se mira la acumulada de
la zona. Sin dirección calculada antes, ni el esfuerzo ni la ortogonalidad
tienen contra qué compararse.

No se rellena el espacio completo: solo se fusiona allí donde la tensión
acumulada de la zona sigue por debajo de su umbral y donde el rumbo nuevo se
mantiene apartado de los rumbos ya fundidos, no alineado con ellos. Así la red
crece por donde menos fuerza y en rumbos independientes. Si una zona no da
puentes concluyentes ni bajando a subespacio, aporta solo sus enlaces mínimos
y queda marcada como pendiente, sin bloquear al resto. Se para cuando la red
queda conexa y escasa; añadir más allá densifica sin orientar y queda prohibido
en esta pieza. La candidata única es escasa y la familia se mantiene al lado
sobre el mismo corpus congelado para comparar, sin poder cambiar a la
candidata una vez congelada.

## 13. Cierre de la doble vía con direcciones y tensión por separado

Direcciones y tensión se separan en dos ejes que no se funden en una sola
nota. El eje de tensión mira el nivel de esfuerzo del puente. El eje de
direcciones mira el giro desde las direcciones de origen hasta la dirección
nueva de la vista conjunta. Cada puente queda con sus dos lecturas guardadas
por separado, para decidir y para rescatar sin mezclarlas.

Ambas vías usan las mismas zonas y niveles y la misma referencia ciega al azar,
y ninguna ve a la otra al decidir durante la prueba. Los acuerdos mandan poco:
donde ambas mantienen o ambas descartan, la red obedece sin más. Los
desacuerdos mandan mucho y no se olvidan. El puente que el nivel mantiene pero
el giro veta por desviarse demasiado, y el que el nivel descarta pero el giro
rescata por apuntar al estado aunque pida algo más de esfuerzo, se guardan en
el resto con su zona, su nivel, su esfuerzo, su giro, sus direcciones de origen
y la carga acumulada de su zona en ese momento. Cada caso se cuenta por zona y
nivel, sin mezclar.

El rescate solo llega en combinación con otras direcciones y cargas. Dos o más
puentes vetados por separado pueden formar juntos un camino honesto si sus
direcciones combinadas cubren rumbos apartados y el esfuerzo repartido entre
ellos queda por debajo de lo que cada uno pedía solo. Un puente vetado por giro
puede entrar si otro ya fundido en la zona sostiene el rumbo que a él le
faltaba, siempre que la acumulada de la zona siga por debajo de su umbral. Cada
rescate apunta a los puentes que combina, para comprobar sin ejecutar.

Si los desacuerdos son raros y siempre del mismo lado, la vía que sobra queda
como control. Si son frecuentes y repartidos, ambas quedan dentro de la medida.
Si el giro solo veta sin rescatar nunca, queda como veto aparte. Con giro
dentro, cada puente entra con esfuerzo y giro combinados pero guardados por
separado; con giro como veto, entra por esfuerzo y cae si el giro excede lo
declarado.

## 14. La espiral con la que abre el zoom

No es una red, es una espiral. Se elige una nota y se abre por vueltas:
primero sus relacionadas directas, luego las relacionadas de esas, hacia fuera
por profundidad de relaciones. Lo que se fija aquí es con qué relaciones se
abre cada vuelta y cuándo se para, de modo que ninguna nota quede fuera de
alcance y cada vuelta aporte rumbos nuevos en vez de repetir los mismos.

De las siete variantes medidas vale la que deje abrir esa espiral entera y
legible: conectada de punta a punta, escasa por vuelta, con cada tramo venido
de una esfera validada que guarda su esfuerzo y su giro. El umbral heredado con
sus cientos de islas no abre entera. Las densas que unen a pocos saltos no se
dejan leer. El árbol solo alarga los caminos. El denso por celda no sirve para
mostrar. Entre la unión y las fronteras abiertas se elige la que abra mejor;
la no elegida queda para comparar, sin poder cambiar a la fijada una vez
congelada.

Se entra por la zona de la nota elegida, contando con todos los ejes y usando
la etiqueta solo para contar, y se baja a la zona fina cuando la gruesa no
concluye. Cada vuelta usa su propio umbral nacido de sus enlaces mínimos, con
la dirección calculada antes de decidir, y solo se abre donde la acumulada
sigue baja y el rumbo nuevo se aparta de los ya abiertos. El cociente entre
camino y distancia directa se lee como relación proyectada, no como coste.

Lo medido lleva dentro las notas editoriales marcadas desde la fuente, casi
todas resueltas como texto propio salvo una ajena dejada sin marcar por
decisión del autor. Queda pendiente comprobar si quitar las puras mueve alguna
decisión cerrada. Veredicto ya medido en rama propia e integrado en main: al
quitar las once notas puras, las decisiones de los tres estudios cerrados no
cambian. Y una cosa es esta espiral para mostrar y otra el gobierno
del motor, cuyo valor heredado no se toca.

## 15. Entrada neutra y apertura por la celda

La ruta entra por el baricentro, en neutro, con todo a la vista y sin haber
elegido bando entre celdas. La espiral se centra en la nota elegida con su
celda como primera vuelta. O sea, cámara en neutro y apertura en la nota: el
viaje va del centro medio a la nota, y una vez allí se abre por vueltas de
profundidad con su propio umbral.

La celda de eje sirve como puerta de entrada por defecto, no como cárcel. Si
la gruesa concluye, la espiral sigue desde ahí hacia fuera. Si no concluye, se
baja a la zona fina sin forzar, con umbral y direcciones propios. Más de la
mitad de las notas tienen su vecina más próxima fuera de su etiqueta, así que
la puerta orienta pero no encierra: un puente puede abrirse hacia otra celda
desde la primera vuelta. La vista inicial con todo es la más densa y vive de
los fotogramas clave ya medidos dentro de presupuesto.

## 16. Tercer nivel con su propio umbral

El tercer nivel solo se abre cuando la zona fina sale no concluyente contra su
propio umbral dinámico en todos los tamaños de bloque, nacido de sus enlaces
mínimos. Cómo se deriva ese umbral queda escrito antes del run, se recalcula
zona por zona y nunca se mueve a mano tras ver el resultado. Sin ese veredicto
medido no se parte nada. Al partir por el rumbo donde más se estira, cada mitad
calcula su propio umbral nacido de sus enlaces mínimos y sus propias
direcciones, sin heredar decisiones salvo el reparto ya comprometido. Los
puentes entre mitades se juzgan contra el menor de los dos umbrales de las
mitades que tocan, como los puentes entre zonas. Si una mitad sigue sin
concluir contra su umbral, aporta solo sus mínimos y queda marcada como
pendiente, sin bloquear a la otra. Con esto la bajada queda completa en tres
peldaños y ninguno se abre sin que el anterior haya salido no concluyente
contra su umbral.

## 17. Variante del umbral con puentes por relaciones

El umbral de cada zona nace primero solo de sus enlaces mínimos, como ya
fijamos. En la variante, una vez hay rondas anteriores congeladas con puentes
validados, el umbral de la zona suma además los esfuerzos mínimos de esos
puentes validados que tocan la zona. Solo valen puentes de resultados ya
comprometidos y congelados, nunca del run en curso. Con ese umbral enriquecido
se vuelven a juzgar las parejas que quedaron fuera por poco, y lo que entra
nuevo apunta a la ronda que aportó el mínimo que lo dejó pasar.

Si lo validado previo viene contaminado, contamina; por eso la variante nunca
sustituye a la primera, corre al lado y se informa cuánta recuperación extra
aporta frente a ella. Si la extra es casi toda de una sola ronda vieja, se
declara y se revisa esa ronda antes de usarla para decidir.

## 18. Brújula de dos direcciones opuestas

Hacen falta dos notas con direcciones iniciales opuestas, a media vuelta una
de otra. Esas dos direcciones fijas son la brújula: no valen por sí mismas,
valen como norte y sur contra los que se lee todo lo demás.

Al fusionarse con otras cargas, cada una de esas dos direcciones se tuerce a
su manera. Leyendo cuánto y hacia dónde gira cada aguja frente a su punto de
partida es como se estipula la dirección del estado que propone la fusión. Si
ambas agujas giran coherentes hacia el mismo rumbo, ese rumbo es el del
estado. Si se abren o se contradicen, la fusión no concluye y queda pendiente
sin forzar.

Las mitades que proponen arrancan siempre de esa brújula opuesta, nunca de un
norte único, y lo único que se analiza es el giro de cada aguja al cargar la
fusión. Las direcciones nacidas del corpus quedan como testigo de a dónde
apuntaba ya cada zona, y la ciega al azar como vara para decir si el giro
observado es mayor de lo que daría el azar.

La brújula solo estipula en igualdad de carga. Si una nota carga más que la
otra, la vista conjunta se inclina hacia la pesada aunque el puente sea
honesto, y el giro dice más de quién pesa que del estado.

Por cada medida se crea una nota neutra sin rumbo propio, cuya carga se fija
en función de las cargas que se van a medir para igualar la balanza. Al
fundirla con las dos agujas, su tensión cancela la diferencia de cargas sin
aportar dirección, y lo que queda en la vista conjunta es solo rumbo. La
neutra debe demostrarse sin rumbo con sus controles antes de usarse, su carga
se calcula igual en todas las zonas con la regla escrita de antemano y nunca
se reutiliza la misma neutra entre zonas distintas. Si muestra rumbo propio,
la medida no vale y queda pendiente sin forzar.

## 19. Estructura decidida para la auditoría

La puerta de tensión y la brújula van a registros hermanos de los ya
existentes, cada uno con su historial de revisiones. La espiral consume sin
decidir y no pide registro. La brújula lleva registro propio como herramienta
agnóstica a la carga con salida a otros ámbitos, no solo como pieza de aquí.
Cada registro pide su propia sección de contrato, una por pieza, registrada
antes de escribir herramienta. En metodología quedan para después de este
chat el lenguaje más natural con sus mejoras y los contratos nuevos.

## 20. Apuntado pero no desarrollado

- Nada pendiente: el veredicto editorial ya quedó apuntado arriba.

## 21. Trazabilidad sin tocar nada

Cada apartado apunta a particiones, resultados y registros ya congelados en este
repositorio y en el cliente, para comprobar sin ejecutar que lo escrito coincide
con lo medido. Un cambio de umbral en el camino de observación necesitaría
revisar la regla de adyacencia fijada en la constitución.
