from geopy.distance import geodesic
import pandas as pd
from pyomo.environ import *
from pyomo.opt import SolverFactory

#----- procesamiento de datos/ encontrando las distancias entre todas las locations -----
clientes = pd.read_csv('Proyecto_C_Caso2/clients.csv')
depositos = pd.read_csv('Proyecto_C_Caso2/depots.csv')
estaciones = pd.read_csv('Proyecto_C_Caso2/stations.csv')
vehiculos = pd.read_csv('Proyecto_C_Caso2/vehicles.csv')

# Cargar y construir locations.csv
locs_base = pd.read_csv('Proyecto_C_Caso2/locations_initial.csv')
locs_base = locs_base[locs_base['LocationID'] < 16]
locs_base.to_csv('Proyecto_C_Caso2/locations.csv', index=False)

for i in range(len(estaciones)):
    data = {
        'LocationID': estaciones['LocationID'][i],
        'Longitude': estaciones['Longitude'][i],
        'Latitude': estaciones['Latitude'][i],
    }
    pd.DataFrame([data]).to_csv('Proyecto_C_Caso2/locations.csv', mode='a', header=False, index=False)

locations_csv = pd.read_csv('Proyecto_C_Caso2/locations.csv')

# Calcular matriz de distancias
from geopy.distance import geodesic
distancias = []
for i in range(len(locations_csv)):
    coord_i = (locations_csv['Latitude'][i], locations_csv['Longitude'][i])
    fila = []
    for j in range(len(locations_csv)):
        coord_j = (locations_csv['Latitude'][j], locations_csv['Longitude'][j])
        fila.append(geodesic(coord_i, coord_j).kilometers)
    distancias.append(fila)

#--- MODELO ---
Model = ConcreteModel()

numPuertos = len(depositos)
numPuntosDestino = len(clientes)
numLocalidades = len(locations_csv)
numVehiculos = len(vehiculos)
numEstaciones = len(estaciones)

# Conjuntos
P = RangeSet(1, numPuertos)
L = RangeSet(1, numLocalidades)
D = RangeSet(2, numPuntosDestino + 1)
V = RangeSet(1, numVehiculos)
E = RangeSet(numPuntosDestino + 2, numLocalidades)

# Parámetros
D_demanda = {i: clientes['Demand'][i-2] for i in D}
V_capacidad = {k: vehiculos['Capacity'][k-1] for k in V}
V_autonomia = {k: vehiculos['Range'][k-1] for k in V}
E_costo = {i: estaciones['FuelCost'][i - numPuntosDestino - 2] for i in E}

# Variables
Model.x = Var(L, L, V, domain=Binary)
Model.u = Var(D, V, bounds=(1, numLocalidades - 1), domain=Integers)
Model.combustible = Var(L, V, domain=NonNegativeReals)
Model.recarga = Var(E, V, domain=NonNegativeReals)

# Fijar combustible inicial al máximo de autonomía
for k in V:
    Model.combustible[1, k].fix(V_autonomia[k])

# Objetivo: minimizar distancia + costo de recarga
Model.obj = Objective(
    expr=sum(distancias[i-1][j-1]*Model.x[i, j, k] for i in L for j in L if i != j for k in V) +
         sum(E_costo[i]*Model.recarga[i, k] for i in E for k in V)
)

# Restricción 1: cada cliente debe ser visitado exactamente una vez
Model.res1 = ConstraintList()
for j in D:
    Model.res1.add(
        sum(Model.x[i, j, k] for i in L if i != j for k in V) == 1
    )

#Asegurar que si un cliente es visitado debe salir también (flujo entrante = saliente)
Model.res1b = ConstraintList()
for j in D:
    Model.res1b.add(
        sum(Model.x[j, m, k] for m in L if m != j for k in V) == 1
    )

# Restricción 2: un nodo sale desde el depósito por vehículo
Model.res2 = ConstraintList()
for k in V:
    Model.res2.add(sum(Model.x[1, j, k] for j in L if j != 1) == 1)

# Restricción 3: debe regresar al depósito
Model.res3 = ConstraintList()
for k in V:
    Model.res3.add(sum(Model.x[i, 1, k] for i in L if i != 1) == 1)

# Restricción 4: conservación de flujo
Model.res4 = ConstraintList()
for k in V:
    for h in D:
        Model.res4.add(sum(Model.x[i, h, k] for i in L if i != h) ==
                       sum(Model.x[h, j, k] for j in L if j != h))

# Restricción 5: eliminación subciclos (MTZ)
Model.res5 = ConstraintList()
for k in V:
    for i in D:
        for j in D:
            if i != j:
                Model.res5.add(Model.u[i, k] - Model.u[j, k] + numLocalidades * Model.x[i, j, k] <= numLocalidades - 1)

# Restricción 6: capacidad del vehículo
Model.res6 = ConstraintList()
for k in V:
    Model.res6.add(sum(D_demanda[i] * sum(Model.x[i, j, k] for j in L if i != j) for i in D) <= V_capacidad[k])

# Restricción 7: autonomía total
Model.res7 = ConstraintList()
for k in V:
    Model.res7.add(sum(distancias[i-1][j-1] * Model.x[i, j, k] for i in L for j in L if i != j) <= V_autonomia[k])

# Restricción 8: dinámica de combustible
consumo = 0.25
Model.res8 = ConstraintList()
for k in V:
    for i in L:
        for j in L:
            if i != j:
                Model.res8.add(
                    Model.combustible[j, k] >= Model.combustible[i, k] - consumo * distancias[i-1][j-1] * Model.x[i, j, k] +
                    (Model.recarga[i, k] if i in list(E) else 0)
                )

# Restricción 9: solo puede recargar si pasa por estación
Model.res9 = ConstraintList()
for k in V:
    for i in E:
        Model.res9.add(Model.recarga[i, k] <= V_autonomia[k] * sum(Model.x[i, j, k] for j in L if j != i))

# Restricción 10: no superar autonomía al recargar
Model.res10 = ConstraintList()
for k in V:
    for i in E:
        Model.res10.add(Model.combustible[i, k] + Model.recarga[i, k] <= V_autonomia[k])

# Resolver
solver = SolverFactory('glpk')
solver.options['tmlim'] = 600
results = solver.solve(Model, tee=True)

# Validación de cobertura
municipios_visitados = []
for j in D:
    entrada = sum(Model.x[i, j, k].value for i in L if i != j for k in V)
    if entrada >= 0.9:
        municipios_visitados.append(j)

municipios_no_visitados = [j for j in D if j not in municipios_visitados]
print("⚠️ Municipios NO visitados:", municipios_no_visitados)

# FUNCION EXPORTAR RESULTADOS

def exportar_resultados_vehiculos(Model, distancias, D_demanda, V_capacidad, V_autonomia, E_costo, L, D, E, V, velocidad=50, tarifa_flete=5000, costo_mantenimiento=700):
    columnas = [
        'VehicleId', 'LoadCap', 'FuelCap', 'RouteSequence', 'Municipalities', 'DemandSatisfied',
        'InitLoad', 'InitFuel', 'RefuelStops', 'RefuelAmounts', 'Distance', 'Time', 'FuelCost',
        'TotalCost'
    ]
    resultados = []
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
            f"MUN{str(nodo).zfill(2)}" if nodo in D else f"EST{str(nodo).zfill(2)}" 
            for nodo in ruta[1:-1]
        ] + ["PTO"]
        municipios = [n for n in ruta if n in D_demanda]
        demandas = [D_demanda[n] for n in municipios]
        total_demanda = sum(demandas)
        distancia_total = sum(distancias[ruta[i]-1][ruta[i+1]-1] for i in range(len(ruta)-1))
        tiempo = round(distancia_total / velocidad, 2)
        refuel_stops = [i for i in ruta if i in E and Model.recarga[i, k].value > 0.1]
        refuel_amounts = [round(Model.recarga[i, k].value, 2) for i in refuel_stops]
        fuel_cost = sum(round(Model.recarga[i, k].value * E_costo[i]) for i in E if Model.recarga[i, k].value > 0.1)
        costo_km = tarifa_flete + costo_mantenimiento
        total_cost = round(distancia_total * costo_km + fuel_cost)

        resultados.append([
            f"CAM{str(k).zfill(3)}",
            V_capacidad[k],
            V_autonomia[k],
            ' - '.join(ruta_nombres),
            len(municipios),
            ' - '.join(str(int(d)) if d.is_integer() else str(d) for d in demandas),
            total_demanda,
            V_autonomia[k],
            len(refuel_stops),
            ' - '.join(str(a) for a in refuel_amounts) if refuel_amounts else "0",
            round(distancia_total, 1),
            tiempo,
            fuel_cost,
            total_cost
        ])

    df_resultados = pd.DataFrame(resultados, columns=columnas)
    df_resultados.to_csv("Proyecto_C_Caso2/verificacion_caso2.csv", index=False)
    return df_resultados

exportar_resultados_vehiculos(Model, distancias, D_demanda, V_capacidad, V_autonomia, E_costo, L, D, E, V)
print("Demanda total:", sum(clientes["Demand"]))
print("Demanda cubierta:", sum(Model.x[i, j, k].value * D_demanda[j] 
                                 for i in L for j in D for k in V if i != j))
