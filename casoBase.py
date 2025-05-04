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

distancias = []
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

        locs_i.append(geodesic(coord, coord2).kilometers)
    
        j+=1
    df_locs_i = pd.DataFrame([locs_i])
    df_locs_i.to_csv('Proyecto_Caso_Base/distancias.csv', mode='a', header=False, index=False)
    distancias.append(locs_i)

print (distancias)

#----- modelo para resolver el caso base -----
# Implementar un modelo básico tipo CVRP con un origen nacional (puerto) y destinos (municipios).
# Incluir restricciones de capacidad y autonomía de los vehículos.
# Validar factibilidad de la solución considerando solamente distancia y demanda.

Model = ConcreteModel()

numPuertos = 1
numPuntosDestino = 24
numLocalidades = len(distancias)
numVehiculos = 8

print(numLocalidades)

# Conjuntos
P= RangeSet(1, numPuertos) 
D = RangeSet(2, numLocalidades)   
V = RangeSet(1, numVehiculos)
L= RangeSet(1, numLocalidades)
nodos = [_ for _ in range(numLocalidades)]


# Parámetros
D_demanda = {}
for i in range(2, numPuntosDestino+2):
    D_demanda[i] = clientes['Demand'][i-2]

V_capacidad = {}
for i in range(1, numVehiculos+1):
    V_capacidad[i] = vehiculos['Capacity'][i-1]
    
V_autonomia = {}
for i in range(1, numVehiculos+1):
    V_autonomia[i] = vehiculos['Range'][i-1]

print(V_capacidad)


# Variables de decisión
Model.x = Var(L,L,V, domain=Binary) # x[i,j,k] = 1 si el vehiculo k viaja de i a j
#Model.y = Var(V, domain=Binary) # y[k] = 1 si el vehiculo k es utilizado
Model.u = Var(L,V, domain=NonNegativeReals) # 

# Función objetivo
Model.obj = Objective(expr=sum(Model.x[i, j, k]*distancias[i-1][j-1] for i in L for j in L for k in V), sense=minimize)
# Restricciones

# Restriccion 1 Cada municipio debe ser visitado por un vehiculo una vez
# Restricción 1: cada cliente debe ser visitado exactamente una vez
Model.res1 = ConstraintList()
for j in D:
    Model.res1.add(sum(Model.x[i, j, k] for i in L if i != j for k in V) == 1)

# Restriccion 2 Se sale del puerto solo una vez
Model.res2 = ConstraintList()
for k in V:
    Model.res2.add(
        sum(Model.x[1,j,k] for j in L if j!=1) == 1
        )

# Restriccion 3 Cada vehiculo que llega a un municipio debe salir de ese municipio. Restriccion de flujo
Model.res3 = ConstraintList()
for j in D:  # solo aplica a clientes
    for k in V:
        Model.res3.add(
            sum(Model.x[i, j, k] for i in L if i != j) ==
            sum(Model.x[j, i, k] for i in L if i != j)
        )
            
# Restriccion 4: eliminacion de subrutas dentro de un vehiculo
Model.res4 = ConstraintList()
for k in V:
    for i in D:
        for j in D:
            if i != j:
                Model.res4.add(
                    Model.u[i, k] - Model.u[j, k] + numPuntosDestino * Model.x[i, j, k] <= numPuntosDestino - 1
                )

# Restriccion 5: no superar la capacidad de los vehiculos
# Cv <= demanda de clientes Xikj * Demandai
Model.res5 = ConstraintList()
Model.res5.add(
    sum(D_demanda[i] * sum(Model.x[i, j, k] for j in L if j != i) for i in D) <= V_capacidad[k]
)

# # Restriccion 6: no superar la autonomia de los vehiculos
Model.res6 = ConstraintList()
for k in V:
    Model.res6.add(
        sum(Model.x[i, j, k] * distancias[i - 1][j - 1] for i in L for j in L if i != j) <= V_autonomia[k]
    )
    
# Model.res_uso_minimo = Constraint(expr=sum(Model.x[i, j, k] for i in L for j in L for k in V if i != j) >= 1)


# Especificacion del solver
SolverFactory("ipopt").solve(Model)
#Model.display()
print("\n📦 Arcos activos (x[i,j,k] == 1):")
for i in L:
    for j in L:
        if i != j:
            for k in V:
                val = Model.x[i, j, k].value
                if val is not None and val > 0.5:
                    print(f"x[{i},{j},{k}] = {val}")

# Imprimir rutas
def imprimir_rutas(Model, L, V, origen=1):
    print("\n📍 Rutas por vehículo:")
    for k in V:
        ruta = [origen]
        actual = origen
        visitados = set()
        while True:
            encontrado = False
            for j in L:
                if j != actual:
                    val = Model.x[actual, j, k].value
                    if val is not None and val > 0.5 and j not in visitados:
                        ruta.append(j)
                        visitados.add(j)
                        actual = j
                        encontrado = True
                        break
            if not encontrado:
                break  # no hay más destinos desde esta ciudad
        if len(ruta) > 1:
            print(f"🛻 Vehículo {k}: {' -> '.join(map(str, ruta))}")
        else:
            print(f"🛻 Vehículo {k}: no se utilizó.")

# Llamar la función (ajusta si cambias los conjuntos)
imprimir_rutas(Model, L, V)
print ("D_demanda: " + str(D_demanda))
print ("V_capacidad: " + str(V_capacidad))
print ("V_autonomia: " + str(V_autonomia))
print("Distancia minima: " + str(value(Model.obj)))