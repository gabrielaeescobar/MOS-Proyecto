from geopy.distance import geodesic
import pandas as pd
from pyomo.environ import *
from pyomo.opt import SolverFactory

#----- procesamiento de datos/ encontrando las distancias entre todas las locations -----
# https://geopy.readthedocs.io/en/stable/#module-geopy.distance 

clientes = pd.read_csv('Proyecto_Caso_Base/clients.csv')
depositos = pd.read_csv('Proyecto_Caso_Base/depots.csv')
vehiculos = pd.read_csv('Proyecto_Caso_Base/vehicles.csv')
for i in range(len(depositos)):
    data= {'LocationID': depositos['LocationID'][i],
            'Longitude': depositos['Longitude'][i],
            'Latitude': depositos['Latitude'][i],}
    data_f = pd.DataFrame([data])
    data_f.to_csv('Proyecto_Caso_Base/locations.csv', index=False)

for i in range(len(clientes)):
    data= {'LocationID': clientes['LocationID'][i],
            'Longitude': clientes['Longitude'][i],
            'Latitude': clientes['Latitude'][i],}
    data_f = pd.DataFrame([data])
    # modo a es de append pa ir añadiendo y como ya tiene encabezados header se pone en False
    data_f.to_csv('Proyecto_Caso_Base/locations.csv', mode='a', header=False, index=False)

locations_csv = pd.read_csv('Proyecto_Caso_Base/locations.csv')

locations = []
for i in range(len(locations_csv)):
    latitud = locations_csv['Latitude'][i]
    longitud = locations_csv['Longitude'][i]
    coord = (latitud, longitud)
    locs_i=[]
    j=0
    #cuando hagamos los otros casos hay que cambiar ese 25
    while j<25:
        latitud2 = locations_csv['Latitude'][j]
        longitud2 = locations_csv['Longitude'][j]
        coord2 = (latitud2, longitud2)

        locs_i.append(geodesic(coord, coord2).meters)
        j+=1
    locations.append(locs_i)

print (locations)

#----- modelo para resolver el caso base -----
# Implementar un modelo básico tipo CVRP con un origen nacional (puerto) y destinos (municipios).
# Incluir restricciones de capacidad y autonomía de los vehículos.
# Validar factibilidad de la solución considerando solamente distancia y demanda.

Model = ConcreteModel()

numPuertos = 1
numPuntosDestino = 24
numLocalidades = len(locations)
numVehiculos = 8

print(numLocalidades)

# Conjuntos
P= RangeSet(1, numPuertos) 
D = RangeSet(1, numPuntosDestino)   
V = RangeSet(1, numVehiculos)

# Parámetros
D_demanda = {}
for i in range(1, numPuntosDestino+1):
    D_demanda[i] = clientes['Demand'][i-1]

V_capacidad = {}
for i in range(1, numVehiculos+1):
    V_capacidad[i] = vehiculos['Capacity'][i-1]
    
V_autonomia = {}
for i in range(1, numVehiculos+1):
    V_autonomia[i] = vehiculos['Range'][i-1]

print(V_capacidad)

# Variables de decisión
Model.x = Var(D,V, domain=Binary) # x[i,j,k] = 1 si el vehiculo k viaja de i a j
Model.y = Var(V, domain=Binary) # y[k] = 1 si el vehiculo k es utilizado
Model.u = Var(D,V, domain=NonNegativeReals) # 

# Función objetivo
Model.obj = Objective(expr=sum(Model.x[i, j, k]*locations[i][j] for i in D for j in D for k in V))

# Restricciones

# Restriccion 1 Cada municipio debe ser visitado por un vehiculo una vez
Model.res1 = ConstraintList()
for j in D:
    Model.res1.add(sum(Model.x[i,j,k] for i in D for k in V) == 1)

# Restriccion 2 Se sale del puerto solo una vez
Model.res2 = ConstraintList()
for k in V:
    Model.res2.add(sum(Model.x[0,j,k] for j in D) == 1)

# Restriccion 3 Cada vehiculo que llega a un municipio debe salir de ese municipio. Restriccion de flujo
Model.res3 = ConstraintList()
for j in D:
    for k in V:
        Model.res3.add(sum(Model.x[i,j,k] for i in D) == sum(Model.x[j,i,k] for i in D))

# Restriccion 4: eliminacion de subrutas dentro de un vehiculo
Model.res4 = ConstraintList()


# Restriccion 5: no superar la capacidad de los vehiculos

# Restriccion 6: no superar la autonomia de los vehiculos
