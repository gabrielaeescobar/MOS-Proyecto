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
Model.u = Var(D, V, bounds=(1, numLocalidades - 1), domain=Integers) # u[i,k] = número de localidades visitadas por el vehículo k al visitar la localidad i 


# Función objetivo: minimizar la distancia total recorrida
Model.obj = Objective(
    expr=sum(distancias[i-1][j-1]*Model.x[i,j,k] 
             for i in L for j in L for k in V if i != j),
    sense=minimize
)

# Restricción 1: cada cliente debe ser visitado exactamente una vez
Model.res1 = ConstraintList()
for j in D:
    Model.res1.add(
        sum(Model.x[i,j,k] for i in L if i != j for k in V) == 1
    )

# Restricción 2: desde el depósito/puerto sale un nodo por vehículo
Model.res2 = ConstraintList()
for k in V:
    Model.res2.add(
        sum(Model.x[1,j,k] for j in L if j != 1) == 1
    )

# Restricción 3: al depósito/puerto llega un nodo por vehículo
Model.res3 = ConstraintList()
for k in V:
    Model.res3.add(
        sum(Model.x[i,1,k] for i in L if i != 1) == 1
    )

# Restricción 4: si un vehículo entra a un nodo, también debe salir de él. Conservación de flujo
Model.res4 = ConstraintList()
for k in V:
    for h in D:
        Model.res4.add(
            sum(Model.x[i,h,k] for i in L if i != h) == sum(Model.x[h,j,k] for j in L if j != h)
        )

# Restricción 5: eliminación de subciclos (MTZ)
Model.res5 = ConstraintList()
for k in V:
    for i in D:
        for j in D:
            if i != j:
                Model.res5.add(
                    Model.u[i,k] - Model.u[j,k] + numLocalidades * Model.x[i,j,k] <= numLocalidades - 1
                )

# Restricción 6 : Capacidad de cada vehículo
Model.res6 = ConstraintList()
for k in V:
    Model.res6.add(
        sum(D_demanda[i] * sum(Model.x[i,j,k] for j in L if i != j) for i in D) <= V_capacidad[k]
    )

# Restricción 7: Autonomía de cada vehículo
Model.res7 = ConstraintList()
for k in V:
    Model.res7.add(
        sum(distancias[i-1][j-1] * Model.x[i,j,k] for i in L for j in L if i != j) <= V_autonomia[k]
    )

solver = SolverFactory('glpk')
solver.options['tmlim'] = 300 # tiempo límite de 5 minutos
results = solver.solve(Model, tee=True)


velocidad = 50  # km/h - estimación de velocidad promedio
tarifa_flete = 5000
costo_mantenimiento = 700
costo_km = tarifa_flete + costo_mantenimiento  # 5700
for k in V:
    ruta = [1]  # siempre inicia en PTO
    actual = 1
    while True:
        next_nodo = None
        for j in L:
            if j != actual and Model.x[actual, j, k].value == 1:
                next_nodo = j
                ruta.append(j)
                actual = j
                break
        if next_nodo == 1 or next_nodo is None:
            break

    ruta_nombres = ["PTO"] + [f"MUN{str(nodo).zfill(2)}" for nodo in ruta[1:-1]] + ["PTO"]

    demandas = [D_demanda[n] for n in ruta if n in D_demanda]
    total_demanda = sum(demandas)
    total_distancia = sum(distancias[ruta[i]-1][ruta[i+1]-1] for i in range(len(ruta)-1))
    tiempo = round(total_distancia / velocidad, 2)
    costo = round(total_distancia * costo_km)

    print(f"{k} CAM{str(k).zfill(3)} ,{V_capacidad[k]} ,{V_autonomia[k]} , {' - '.join(ruta_nombres)}")
    print(f",→ ,{len(demandas)} ,{' - '.join(str(d) for d in demandas)} ,{total_demanda} ,{V_autonomia[k]} ,{round(total_distancia,1)} ,{tiempo} ,{costo}")

# Calcular la distancia total recorrida por todos los vehículos
distancia_total = 0
for k in V:
    ruta = [1]
    actual = 1
    while True:
        next_nodo = None
        for j in L:
            if j != actual and Model.x[actual, j, k].value == 1:
                next_nodo = j
                ruta.append(j)
                actual = j
                break
        if next_nodo == 1 or next_nodo is None:
            break
    distancia_total += sum(distancias[ruta[i]-1][ruta[i+1]-1] for i in range(len(ruta)-1))

print(f"Distancia total recorrida por todos los vehículos: {round(distancia_total, 2)} km")
