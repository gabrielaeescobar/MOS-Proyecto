# MOS-Proyecto-1
### Integrantes
Mariana Ortega - 202211233
María Alejandra Pinzón - 202213956
Gabriela Escobar - 201130766


## Archivos py
En los archivos `.py` de cada caso, está el código de la implementación, sin ningún tipo de visualización ni análisis. En todos está, el procesamiento de datos, y el modelo implementado. Decidimos dejar estos archivos para que se pueda ver en un solo lugar el código de la implementaciones. Sin embargo, si se desea ver la implementacion completa en pyomo se debe acceder a los notebooks.
## Notebooks con análisis y código
Cada caso tiene un jupyter notebook de tipo `.ipynb`. En estos, dejamos el mismo código que está en los archivos tipo `.py.`, pero ahora tiene:
- Formulación matemática final, después de hacerle ajustes por la implementación.
- Graficas para visualización.  
- Tablas y gráficas para análisis
- Análisis y conclusiones de resultados
## Carpetas con archivos
Hay tres carpetas, una para cada caso, donde están los archivos de la base de datos, y algunos adicionales que fueron creados en el proceso para poder realizar el procesamiento de datos, e imprimir la respuesta final. A continuación se explicará cada archivo.
### Caso Base
#### Base de datos
Los archivos `clients.csv`, `depots.csv` y `vehicles.csv` fueron dados por el equipo de la clase, y fue la base de datos que utilizamos para este caso. Adicionalmente el archivo `Readme.md` explica el contenido, columna por columna, de los archivos de la base de datos.
#### Archivos propios
- `locations.csv` tiene todos los elementos que tienen locations, en este caso, los puertos y clientes. Anteriormente eran dados en archivos separados, y para el procesamiento de datos era pertinente tenerlos todos en uno solo. 
- `distancias.csv` es el archivo que muestra la matriz de ubicaciones. en este caso, la matriz es 25 x 25, pues muestra la distancia entre todos los nodos/locations del caso. Por los datos dados, había 1 puerto y 24 clientes.
- `i_comoVerMapa.png` y `i_mapaInteractivoCasoBasico.png` son fotos utlizadas en el análsisi del caso. `ruta_vehiculos_interactiva.html` fue el mapa creado en la visualización del caso usando folium.
- `verificacion_caso1_csv` muestra la solución del caso base.
### Caso 2
#### Base de datos
Los archivos `clients.csv`, `depots.csv`, `vehicles.csv` y `stations.csv` fueron dados por el equipo de la clase, y fue la base de datos que utilizamos para este caso. Adicionalmente el archivo `Readme.md` explica el contenido, columna por columna, de los archivos de la base de datos.
#### Archivos propios
- `locations.csv` tiene todos los elementos que tienen locations, en este caso, los puertos y clientes. Anteriormente eran dados en archivos separados, y para el procesamiento de datos era pertinente tenerlos todos en uno solo. `locations_initial.csv` fue creada con el fin de corregir el error de la base de datos, que los clientes no tenian sus coordenadas.
- `distancias.csv` es el archivo que muestra la matriz de ubicaciones. en este caso, la matriz es 27 x 27, pues muestra la distancia entre todos los nodos/locations del caso. Por los datos dados, había 1 puerto, 14 clientes y 12 estaciones de servicio.
- `mapa_rutas_caso2.html` fue el mapa creado en la visualización del caso usando folium.
- `verificacion_caso2_csv` muestra la solución del caso base.

### Caso 3
#### Base de datos
Los archivos `clients.csv`, `depots.csv`, `vehicles.csv`, `stations.csv` y `tolls.csv` fueron dados por el equipo de la clase, y fue la base de datos que utilizamos para este caso. Adicionalmente el archivo `Readme.md` explica el contenido, columna por columna, de los archivos de la base de datos.
#### Archivos propios
- `locations.csv` tiene todos los elementos que tienen locations, en este caso, los puertos y clientes. Anteriormente eran dados en archivos separados, y para el procesamiento de datos era pertinente tenerlos todos en uno solo. `locations_initial.csv` fue creada con el fin de corregir el error de la base de datos, que los clientes no tenian sus coordenadas.
- `distancias.csv` es el archivo que muestra la matriz de ubicaciones.
- `verificacion_caso2.csv` muestra la solución del caso base.

#### Implementación y Resultados
- Toda la solución correspondiente al Caso 3 se encuentra integrada en el notebook Caso3_Logistico.ipynb. En dicho notebook se desarrolla y ejecuta todo el flujo del modelo de optimización, incluyendo:

- Modelo matemático completo implementado en Pyomo con estructura modular.

- Visualización interactiva de rutas nacionales planificadas mediante mapas generados con folium, los cuales se despliegan directamente en el entorno del notebook.

- Cálculo y visualización de resultados por vehículo, incluyendo rutas, costos desagregados, tiempos, distancias, recargas, pesos y cumplimiento de restricciones.

- Evaluación de escenarios de sensibilidad, donde se modifican parámetros como el precio del combustible, la autonomía de los vehículos y la disponibilidad de estaciones de recarga.

- Análisis detallado y respuestas a las preguntas clave del caso, elaboradas y documentadas dentro del mismo notebook.

- No se exportan archivos ni mapas; toda la visualización y verificación se realiza de forma interactiva en el notebook.

- Este diseño garantiza trazabilidad, claridad y reproducibilidad de los resultados dentro de un único entorno de trabajo.