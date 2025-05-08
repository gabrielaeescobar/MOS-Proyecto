from geopy.distance import geodesic
import pandas as pd
from pyomo.environ import *
from pyomo.opt import SolverFactory

#----- procesamiento de datos/ encontrando las distancias entre todas las locations -----
# https://geopy.readthedocs.io/en/stable/#module-geopy.distance 

clientes = pd.read_csv('Proyecto_C_Caso3/clients.csv')
depositos = pd.read_csv('Proyecto_C_Caso3/depots.csv')
estaciones = pd.read_csv('Proyecto_C_Caso3/stations.csv')
vehiculos = pd.read_csv('Proyecto_C_Caso3/vehicles.csv')
peajes = pd.read_csv('Proyecto_C_Caso3/tolls.csv')


df = pd.read_csv('Proyecto_C_Caso3/locations_initial.csv')
# tomamos el mismo origen y las mismas primeras 15 localidades que en el caso base
df = df[df['LocationID'] < 16]

df.to_csv('Proyecto_C_Caso3/locations.csv', index=False)

for i in range(len(estaciones)):
    data= {'LocationID': estaciones['LocationID'][i],
            'Longitude': estaciones['Longitude'][i],
            'Latitude': estaciones['Latitude'][i],}
    data_f = pd.DataFrame([data])
    # modo a es de append pa ir añadiendo y como ya tiene encabezados header se pone en False
    data_f.to_csv('Proyecto_C_Caso3/locations.csv', mode='a', header=False, index=False)

locations_csv = pd.read_csv('Proyecto_C_Caso3/locations.csv')

locations = []
for i in range(len(locations_csv)):
    latitud = locations_csv['Latitude'][i]
    longitud = locations_csv['Longitude'][i]
    coord = (latitud, longitud)
    locs_i=[]
    j=0
    while j<len(locations_csv):
        latitud2 = locations_csv['Latitude'][j]
        longitud2 = locations_csv['Longitude'][j]
        coord2 = (latitud2, longitud2)

        locs_i.append(geodesic(coord, coord2).meters)
        j+=1
    locations.append(locs_i)

print (locations)

distancias = []
for i in range(len(locations_csv)):
    latitud = locations_csv['Latitude'][i]
    longitud = locations_csv['Longitude'][i]
    coord = (latitud, longitud)
    locs_i=[]
    j=0
    while j< len(locations_csv):
        latitud2 = locations_csv['Latitude'][j]
        longitud2 = locations_csv['Longitude'][j]
        coord2 = (latitud2, longitud2)

        locs_i.append(geodesic(coord, coord2).kilometers)
    
        j+=1
    # df_locs_i = pd.DataFrame([locs_i])
    # df_locs_i.to_csv('Proyecto_C_Caso2/distancias.csv', mode='a', header=False, index=False)
    distancias.append(locs_i)

print (distancias)

#----- modelo para resolver el 2 -----
# Caso 1:
# Implementar un modelo básico tipo CVRP con un origen nacional (puerto) y destinos (municipios).
# Incluir restricciones de capacidad y autonomía de los vehículos.
# Validar factibilidad de la solución considerando solamente distancia y demanda.

# Caso 2:
# Extender el modelo anterior para incluir decisiones de recarga.
# Tomar en cuenta los diferentes precios de combustible en estaciones a lo largo del recorrido.
# Asegurar que ningún vehículo se quede sin combustible en ninguna parte de la ruta.
# Este caso permite probar estrategias como recarga completa vs. recarga mínima necesaria

# Caso 3:
# Incorporar restricciones de peso por municipio, asociadas a normativas locales
# Incluir peajes con tarifas variables según el peso y tramo recorrido.
# Determinar estrategias conjuntas de ruteo y recarga, optimizando el costo total nacional

Model = ConcreteModel()

numPuertos = len(depositos)
numPuntosDestino = len(clientes)
numLocalidades = len(locations_csv)
numVehiculos = len(vehiculos)
numEstaciones = len(estaciones)

# Conjuntos
P = RangeSet(1, numPuertos)
D = RangeSet(2, numPuntosDestino+1) 
V = RangeSet(1, numVehiculos)
E = RangeSet(numPuntosDestino + 2, numLocalidades)
#  locations con todo
L= RangeSet(1, numLocalidades)

# Parámetros
# Demanda de los clientes
D_demanda = {}
for i in range(2, numPuntosDestino+2):
    D_demanda[i] = clientes['Demand'][i-2]

D_peso_maximo = {}
for i in range(2, numPuntosDestino+2):
    if clientes['MaxWeight'][i-2] == 'N/A':
        D_peso_maximo[i] = 0
    else:
        D_peso_maximo[i] = clientes['MaxWeight'][i-2]

# Capacidad de los vehículos
V_capacidad = {}
for i in range(1, numVehiculos+1):
    V_capacidad[i] = vehiculos['Capacity'][i-1]

# Autonomía de los vehículos
V_autonomia = {}
for i in range(1, numVehiculos+1):
    V_autonomia[i] = vehiculos['Range'][i-1]

# Costo de recarga en cada estación
E_costo = {}
for i in range(numPuntosDestino + 2, numLocalidades+1):
    E_costo[i] = estaciones['FuelCost'][i-numPuntosDestino-2]

# tarifa base de cada cliente
T_base = {}
for i in range(2, numPuntosDestino+2):
    if peajes['BaseRate'][i-2] == 'N/A':
        T_base[i] = 0
    else:
        T_base[i] = peajes['BaseRate'][i-2]

# tarifa de peaje por cliente
T_peaje = {}
for i in range(2, numPuntosDestino+2):
    if peajes['RatePerTon'][i-2] == 'N/A':
        T_peaje[i] = 0
    else:
        T_peaje[i] = peajes['RatePerTon'][i-2]


tarifa_flete_km = 5000   # Ft
costo_mantenimiento_km = 700  # Cm
costo = tarifa_flete_km + costo_mantenimiento_km
N_intermedios = RangeSet(2, numLocalidades)  # todo excepto el depósito


# Variables de decisión
Model.x = Var(L,L,V, domain=Binary) # x[i,j,k] = 1 si el vehiculo k viaja de i a j
Model.u = Var(N_intermedios, V, bounds=(1, numLocalidades - 1), domain=Integers)
Model.c = Var(L, V, domain=NonNegativeReals) # combustible
Model.r = Var(E, V, domain=NonNegativeReals) # recarga
Model.w = Var(D, V, domain=NonNegativeReals) # peso

### FALTA COMPLETAR CON LOS PEAJES Y DEMÁS DEL CASO 3
# Función objetivo: minimizar la distancia total recorrida, el costo de recarga y el costo de peaje
Model.obj = Objective(
    expr=sum(costo*distancias[i-1][j-1]*Model.x[i,j,k] 
             for i in L for j in L for k in V if i != j ) +
         sum(E_costo[e]*Model.r[e,k] for e in E for k in V) 
         
         , sense=minimize
)

# Restricción 1: cada cliente debe ser visitado exactamente una vez
Model.res1 = ConstraintList()
for j in D:
    Model.res1.add(
        sum(Model.x[i,j,k] for i in L if i != j for k in V) == 1
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
    for h in L:
        if h != 1:
            Model.res4.add(
                sum(Model.x[i,h,k] for i in L if i != h) == sum(Model.x[h,j,k] for j in L if j != h)
            )

# Restricción 5: eliminación de subciclos (MTZ)
Model.res5 = ConstraintList()
for k in V:
    for i in N_intermedios:
        for j in N_intermedios:
            if i != j:
                Model.res5.add(
                    Model.u[i,k] - Model.u[j,k] + numLocalidades * Model.x[i,j,k] <= numLocalidades - 1
                )

# Restricción 6 : Capacidad de cada vehículo
Model.res6 = ConstraintList()
for k in V:
    Model.res6.add(
        sum(D_demanda[i] * sum(Model.x[j,i,k] for j in L if j != i) for i in D) <= V_capacidad[k]
    )
    
# Restricción 7: Continuidad del nivel de combustible
Model.res7 = ConstraintList()
for k in V:
    for i in L:
        for j in L:
            if i != j:
                recarga = Model.r[i, k] if i in E else 0  # solo recarga si está en estación
                Model.res7.add(
                    Model.c[j, k] >= Model.c[i, k] + recarga - distancias[i-1][j-1] * Model.x[i, j, k]
                )

# Restricción 8: el nivel de combustible y la recarga no pueden exceder la capacidad del tanque
Model.res8 = ConstraintList()
for k in V:
    for i in L:
        Model.res8.add(
            Model.c[i, k] <= V_autonomia[k]
        )
    for i in E:
        Model.res8.add(
            Model.r[i, k] <= V_autonomia[k]
        )

### FALTA COMPLETAR CON LOS PEAJES Y DEMÁS DEL CASO 3

solver = SolverFactory('glpk')
solver.options['tmlim'] = 300 # tiempo límite de 5 minutos
results = solver.solve(Model, tee=True)


def exportar_resultados_vehiculos(Model, distancias, D_demanda, V_capacidad, V_autonomia, E_costo, L, D, E, V, velocidad=50, tarifa_flete=5000, costo_mantenimiento=700):
    ## FALTA COMPLETAR COLUMNAS CON LOS PEAJES Y DEMÁS DEL CASO 3
    columnas = [
        'VehicleId', 'LoadCap', 'FuelCap', 'RouteSequence', 'Municipalities', 'DemandSatisfied',
        'InitLoad', 'InitFuel', 'RefuelStops', 'RefuelAmounts', 'Distance', 'Time', 'FuelCost',
        'TotalCost'
    ]
    resultados = []
    # recrear el modelo para obtener los resultados
    for k in V:
        ruta = [1]
        actual = 1

        while True:
            siguiente = None
            for j in L:
                if j != actual and Model.x[actual, j, k].value and Model.x[actual, j, k].value > 0.5:
                    siguiente = j
                    ruta.append(j)
                    actual = j
                    break
            if siguiente is None or actual == 1:
                break
            

        ruta_nombres = ["PTO"] + [
            f"MUN{str(nodo).zfill(2)}" if nodo not in E else f"EST{str(nodo).zfill(2)}" 
            for nodo in ruta[1:-1]
        ] + ["PTO"]
        municipios = [n for n in ruta if n in D_demanda]
        demandas = [D_demanda[n] for n in municipios]
        total_demanda = sum(demandas)
        distancia_total = sum(distancias[ruta[i]-1][ruta[i+1]-1] for i in range(len(ruta)-1))
        tiempo = round(distancia_total / velocidad, 2)
        refuel_stops = [i for i in ruta if i in E and Model.r[i, k].value > 0.1] # es para decir que el vehiculo recarga en la estacion i, como si fuera recarga[i,k] > 0 
        refuel_amounts = [round(Model.r[i, k].value, 2) for i in refuel_stops]
        fuel_cost = sum(Model.r[i, k].value * E_costo[i] for i in E if Model.r[i, k].value > 0.1)
        fuel_cost = round(fuel_cost, 2)
        refuel_amounts = [round(Model.r[i, k].value, 2) for i in refuel_stops]
        costo_km = tarifa_flete + costo_mantenimiento
        total_cost = round(distancia_total * costo_km + fuel_cost)

        resultados.append([
            f"CAM{str(k).zfill(3)}",                                                # VehicleId
            V_capacidad[k],                                                         # LoadCap
            V_autonomia[k],                                                         # FuelCap
            ' - '.join(ruta_nombres),                                               # RouteSequence
            len(municipios),                                                        # Municipalities
            ' - '.join(str(int(d)) if d.is_integer() else str(d) for d in demandas),# DemandSatisfied 
            total_demanda,                                                          # InitialLoad
            V_autonomia[k],                                                         # InitFuel
            len(refuel_stops),                                                      # RefuelStops
            ' - '.join(str(a) for a in refuel_amounts) if refuel_amounts else "0",  # RefuelAmounts
            round(distancia_total, 1),                                              # Distance
            tiempo,                                                                 # Time
            fuel_cost,                                                              # FuelCost
            total_cost                                                              # TotalCost
        ])


    df_resultados = pd.DataFrame(resultados, columns=columnas)
    df_resultados.to_csv("Proyecto_C_Caso3/verificacion_caso3.csv", index=False)
    return df_resultados

df = exportar_resultados_vehiculos(Model, distancias, D_demanda, V_capacidad, V_autonomia, E_costo, L, D, E, V)
distancia_total = df['Distance'].sum()
print(f'Distancia total recorrida por todos los vehículos: {round(distancia_total, 2)} km')