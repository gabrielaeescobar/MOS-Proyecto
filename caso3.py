from geopy.distance import geodesic
import pandas as pd
from pyomo.environ import *
from pyomo.opt import SolverFactory

# ----------------------------
# Lectura de datos
# ----------------------------

clientes = pd.read_csv('Proyecto_C_Caso3/clients.csv')
depositos = pd.read_csv('Proyecto_C_Caso3/depots.csv')
estaciones = pd.read_csv('Proyecto_C_Caso3/stations.csv')
vehiculos = pd.read_csv('Proyecto_C_Caso3/vehicles.csv')
tolls = pd.read_csv('Proyecto_C_Caso3/tolls.csv')

# Normalizar nombres de columnas para evitar errores
cols = [col.strip().lower() for col in tolls.columns]
tolls.columns = cols

# Preparación de localidades
locations_df = pd.read_csv('Proyecto_C_Caso3/locations_initial.csv')
locations_df = locations_df[locations_df['LocationID'] < 16]

# Sobrescribimos primero con las localidades iniciales
locations_df.to_csv('Proyecto_C_Caso3/locations.csv', index=False)

# Luego agregamos estaciones (sin encabezado)
for i in range(len(estaciones)):
    data = {
        'LocationID': estaciones['LocationID'][i],
        'Longitude': estaciones['Longitude'][i],
        'Latitude': estaciones['Latitude'][i],
    }
    pd.DataFrame([data]).to_csv('Proyecto_C_Caso3/locations.csv', mode='a', header=False, index=False)

locations_csv = pd.read_csv('Proyecto_C_Caso3/locations.csv')

# Convertir a numérico por seguridad
locations_csv['Latitude'] = pd.to_numeric(locations_csv['Latitude'], errors='coerce')
locations_csv['Longitude'] = pd.to_numeric(locations_csv['Longitude'], errors='coerce')

# Calcular distancias entre localidades
distancias = []
for i in range(len(locations_csv)):
    coord1 = (locations_csv['Latitude'][i], locations_csv['Longitude'][i])
    fila = []
    for j in range(len(locations_csv)):
        coord2 = (locations_csv['Latitude'][j], locations_csv['Longitude'][j])
        fila.append(geodesic(coord1, coord2).kilometers)
    distancias.append(fila)

# Procesar costos de peajes
costo_peaje = {}
for _, row in tolls.iterrows():
    origen = int(row['clientid'])
    destino = int(row['clientid'])
    base = 0 if pd.isna(row['baserate']) else float(str(row['baserate']).replace(",", ""))
    por_tonelada = 0 if pd.isna(row['rateperton']) else float(str(row['rateperton']).replace(",", ""))
    costo_peaje[(origen, destino)] = (base, por_tonelada)

# Parámetros y conjuntos
num_puertos = len(depositos)
num_clientes = len(clientes)
num_localidades = len(locations_csv)
num_vehiculos = len(vehiculos)
num_estaciones = len(estaciones)

Model = ConcreteModel()

P = RangeSet(1, num_puertos)
D = RangeSet(2, num_clientes + 1)
V = RangeSet(1, num_vehiculos)
E = RangeSet(num_clientes + 2, num_localidades)
L = RangeSet(1, num_localidades)
N = RangeSet(2, num_localidades)

D_demanda = {i + 2: clientes['Demand'][i] for i in range(num_clientes)}
D_peso_max = {i + 2: clientes['MaxWeight'][i] if not pd.isna(clientes['MaxWeight'][i]) else float('inf') for i in range(num_clientes)}
V_capacidad = {i + 1: vehiculos['Capacity'][i] for i in range(num_vehiculos)}
V_autonomia = {i + 1: vehiculos['Range'][i] for i in range(num_vehiculos)}
E_costo = {i + num_clientes + 2: estaciones['FuelCost'][i] for i in range(num_estaciones)}

# Variables
Model.x = Var(L, L, V, domain=Binary)
Model.u = Var(N, V, bounds=(1, num_localidades - 1), domain=Integers)
Model.c = Var(L, V, domain=NonNegativeReals)
Model.r = Var(E, V, domain=NonNegativeReals)
Model.peaje = Var(L, L, V, domain=NonNegativeReals)

# Costos
flete = 5000
mant = 700
costo_km = flete + mant

# Objetivo
Model.obj = Objective(
    expr=sum(costo_km * distancias[i-1][j-1] * Model.x[i, j, k] for i in L for j in L for k in V if i != j) +
         sum(E_costo[e] * Model.r[e, k] for e in E for k in V) +
         sum(Model.peaje[i, j, k] for i in L for j in L for k in V if i != j),
    sense=minimize
)

# Restricciones

# Restricción para calcular costos de peaje con activación lineal
Model.peso_total = Var(L, V, domain=NonNegativeReals)
Model.res_peajes = ConstraintList()
M = 1e6  # constante grande
for i in L:
    for j in L:
        if i != j:
            for k in V:
                base, por_ton = costo_peaje.get((i, j), (0, 0))
                Model.res_peajes.add(
                    Model.peaje[i, j, k] <= base * Model.x[i, j, k] + por_ton * Model.peso_total[j, k]
                )
                Model.res_peajes.add(Model.peaje[i, j, k] >= 0)
Model.res1 = ConstraintList()
for j in D:
    Model.res1.add(sum(Model.x[i, j, k] for i in L if i != j for k in V) == 1)

Model.res2 = ConstraintList()
for k in V:
    Model.res2.add(sum(Model.x[1, j, k] for j in D) == 1)

Model.res3 = ConstraintList()
for k in V:
    Model.res3.add(sum(Model.x[i, 1, k] for i in L if i != 1) == 1)

Model.res4 = ConstraintList()
for k in V:
    for h in L:
        if h != 1:
            Model.res4.add(sum(Model.x[i, h, k] for i in L if i != h) == sum(Model.x[h, j, k] for j in L if j != h))

Model.res5 = ConstraintList()
for k in V:
    for i in N:
        for j in N:
            if i != j:
                Model.res5.add(Model.u[i, k] - Model.u[j, k] + num_localidades * Model.x[i, j, k] <= num_localidades - 1)

Model.res6 = ConstraintList()
for k in V:
    Model.res6.add(sum(D_demanda[i] * sum(Model.x[j, i, k] for j in L if j != i) for i in D) <= V_capacidad[k])

Model.res7 = ConstraintList()
for k in V:
    for i in L:
        for j in L:
            if i != j:
                recarga = Model.r[i, k] if i in E else 0
                Model.res7.add(Model.c[j, k] >= Model.c[i, k] + recarga - distancias[i-1][j-1] * Model.x[i, j, k])

Model.res8 = ConstraintList()
for k in V:
    for i in L:
        Model.res8.add(Model.c[i, k] <= V_autonomia[k])
    for i in E:
        Model.res8.add(Model.r[i, k] <= V_autonomia[k])

Model.res9 = ConstraintList()
for j in D:
    peso_max = D_peso_max[j]
    for k in V:
        Model.res9.add(sum(D_demanda[i] * Model.x[i, j, k] for i in D if i != j) <= peso_max)

# Restricción: calcular el peso total al llegar a cada cliente
Model.res_peso_total = ConstraintList()
for j in D:
    for k in V:
        Model.res_peso_total.add(
            Model.peso_total[j, k] == sum(D_demanda[i] * Model.x[i, j, k] for i in D if i != j)
        )

# Resolución
solver = SolverFactory('glpk')
solver.options['tmlim'] = 300
results = solver.solve(Model, tee=True)

# Verificaciones clave
print("Claves de D_demanda:", list(D_demanda.keys()))
print("Claves de D_peso_max:", list(D_peso_max.keys()))

for k in V:
    print(f"Rutas vehículo {k}:")
    for i in L:
        for j in L:
            if i != j and Model.x[i, j, k].value and Model.x[i, j, k].value > 0.5:
                print(f"  Va de {i} a {j}")

print("Modelo listo para resolver el Caso 3.")

def exportar_resultados_vehiculos_case3(Model, distancias, D_demanda, V_capacidad, V_autonomia, E_costo, L, D, E, V, costo_peaje, velocidad=50):
    columnas = [
        'VehicleId', 'LoadCap', 'FuelCap', 'RouteSeq', 'Municipalities', 'Demand',
        'InitLoad', 'InitFuel', 'RefuelStops', 'RefuelAmounts', 'TollsVisited', 'TollCosts',
        'VehicleWeights', 'Distance', 'Time', 'FuelCost', 'TollCost', 'TotalCost'
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

        ruta_nombres = ['PTO'] + [
            f"MUN{str(nodo).zfill(2)}" if nodo in D else
            f"EST{str(nodo).zfill(2)}" if nodo in E else
            f"PEA{str(nodo).zfill(2)}" for nodo in ruta[1:-1]
        ] + ['PTO']

        municipios = [n for n in ruta if n in D_demanda]
        demandas = [D_demanda[n] for n in municipios]
        total_demanda = sum(demandas)
        distancia_total = sum(distancias[ruta[i]-1][ruta[i+1]-1] for i in range(len(ruta)-1))
        tiempo = round(distancia_total / velocidad, 2)

        refuel_stops = [i for i in ruta if i in E and Model.r[i, k].value > 0.1]
        refuel_amounts = [round(Model.r[i, k].value, 2) for i in refuel_stops]
        fuel_cost = round(sum(Model.r[i, k].value * E_costo[i] for i in E if Model.r[i, k].value > 0.1), 2)

        tolls_visited = [(ruta[i], ruta[i+1]) for i in range(len(ruta)-1) if (ruta[i], ruta[i+1]) in costo_peaje]
        toll_costs = []
        for (i, j) in tolls_visited:
            base, por_ton = costo_peaje.get((i, j), (0, 0))
            if (j in D) and ((j, k) in Model.peso_total):
                peso_real = Model.peso_total[j, k].value
            else:
                peso_real = 0
            costo = base + por_ton * peso_real
            toll_costs.append(round(costo, 2))
        toll_total = round(sum(toll_costs), 2)

        pesos_por_municipio = [int(D_demanda[m]) for m in municipios]

        total_cost = round(distancia_total * (flete + mant) + fuel_cost + toll_total)

        resultados.append([
            f"CAM{str(k).zfill(3)}",
            V_capacidad[k],
            V_autonomia[k],
            ' - '.join(ruta_nombres),
            len(municipios),
            '-'.join(str(int(d)) for d in demandas),
            total_demanda,
            V_autonomia[k],
            len(refuel_stops),
            '-'.join(str(a) for a in refuel_amounts) if refuel_amounts else '0',
            len(tolls_visited),
            '-'.join(str(tc) for tc in toll_costs) if toll_costs else '0',
            '-'.join(str(p) for p in pesos_por_municipio),
            round(distancia_total, 1),
            tiempo,
            fuel_cost,
            toll_total,
            total_cost
        ])

    df_resultados = pd.DataFrame(resultados, columns=columnas)
    df_resultados.to_csv("Proyecto_C_Caso3/verificacion_caso3.csv", index=False)
    print("Archivo verificacion_caso3.csv exportado correctamente.")
    return df_resultados

# Ejecutar después de resolver el modelo:
df = exportar_resultados_vehiculos_case3(Model, distancias, D_demanda, V_capacidad, V_autonomia, E_costo, L, D, E, V, costo_peaje)
