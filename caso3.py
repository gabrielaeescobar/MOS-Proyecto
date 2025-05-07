from geopy.distance import geodesic
import pandas as pd
from pyomo.environ import *
from pyomo.opt import SolverFactory

import pandas as pd
from geopy.distance import geodesic

# -------------------------------
# 1. CARGA DE ARCHIVOS DE CASO 3
# -------------------------------
clientes = pd.read_csv('Proyecto_C_Caso3/clients.csv')
depositos = pd.read_csv('Proyecto_C_Caso3/depots.csv')
estaciones = pd.read_csv('Proyecto_C_Caso3/stations.csv')
vehiculos = pd.read_csv('Proyecto_C_Caso3/vehicles.csv')
peajes = pd.read_csv('Proyecto_C_Caso3/tolls.csv')

# -------------------------------
# 2. CREACIÓN DEL locations.csv UNIFICADO
# -------------------------------
# Empezar con los 15 nodos originales del caso base
df_base = pd.read_csv('Proyecto_Caso_Base/locations.csv')
df_base = df_base[df_base['LocationID'] < 16]  # Solo del 1 al 15
df_base.to_csv('Proyecto_C_Caso3/locations.csv', index=False)

# Añadir estaciones al archivo de localidades
for i in range(len(estaciones)):
    data = {
        'LocationID': estaciones.loc[i, 'LocationID'],
        'Longitude': estaciones.loc[i, 'Longitude'],
        'Latitude': estaciones.loc[i, 'Latitude']
    }
    pd.DataFrame([data]).to_csv('Proyecto_C_Caso3/locations.csv', mode='a', header=False, index=False)

# Leer el archivo combinado de localidades
locations_csv = pd.read_csv('Proyecto_C_Caso3/locations.csv')

# -------------------------------
# 3. MATRIZ DE DISTANCIAS ENTRE NODOS
# -------------------------------
distancias = []
for i in range(len(locations_csv)):
    coord_i = (locations_csv.loc[i, 'Latitude'], locations_csv.loc[i, 'Longitude'])
    fila = []
    for j in range(len(locations_csv)):
        coord_j = (locations_csv.loc[j, 'Latitude'], locations_csv.loc[j, 'Longitude'])
        distancia = geodesic(coord_i, coord_j).kilometers
        fila.append(distancia)
    distancias.append(fila)

# -------------------------------
# 4. DEFINICIÓN DE CONJUNTOS
# -------------------------------
num_localidades = len(locations_csv)       # Total: 27
num_vehiculos = len(vehiculos)             # Según vehicles.csv

L = list(range(1, num_localidades + 1))    # Todas las localidades
D = list(range(2, 16))                     # Municipios con demanda
E = list(estaciones['LocationID'])         # Estaciones de recarga
V = list(range(1, num_vehiculos + 1))      # Vehículos disponibles

# -------------------------------
# 5. PARÁMETROS: demanda, capacidad, autonomía
# -------------------------------
D_demanda = {
    row['LocationID']: row['Demand']
    for _, row in clientes.iterrows()
}

V_capacidad = {
    i + 1: vehiculos.loc[i, 'Capacity']
    for i in range(num_vehiculos)
}

V_autonomia = {
    i + 1: vehiculos.loc[i, 'Range']
    for i in range(num_vehiculos)
}

# -------------------------------
# 6. PRECIO DE COMBUSTIBLE EN ESTACIONES
# -------------------------------
precio_combustible = {
    int(row['LocationID']): float(row['FuelCost'])
    for _, row in estaciones.iterrows()
}


# -------------------------------
# 7. PESO MÁXIMO PERMITIDO POR MUNICIPIO
# -------------------------------
# Reemplazar NaN por un valor alto por defecto si es necesario
clientes['MaxWeight'] = clientes['MaxWeight'].fillna(9999)

peso_max = {
    row['LocationID']: row['MaxWeight']
    for _, row in clientes.iterrows()
}

# -------------------------------
# 8. COSTO DE PEAJE POR MUNICIPIO
# -------------------------------
# Dado que TollName no tiene (i, j), se asocia el costo por nodo usando el índice
# (asumimos que cada peaje se asocia secuencialmente a D: municipios 2–15)

# Limpieza al construir el diccionario
costo_peaje = {}
for idx, row in peajes.iterrows():
    try:
        loc_id = D[idx]
        costo = row['RatePerTon']
        costo_peaje[loc_id] = 0 if pd.isna(costo) else float(costo)
    except IndexError:
        continue


# -------------------------------
# 9. VERIFICACIÓN
# -------------------------------
print(f"Total de localidades cargadas: {len(locations_csv)}")
print("Distancia entre nodo 1 y nodo 2:", distancias[0][1])
print("Ejemplo demanda:", D_demanda)
print("Precio combustible estaciones:", precio_combustible)
print("Peso máximo por municipio:", peso_max)
print("Costo de peaje por municipio:", costo_peaje)


from pyomo.environ import *

# -------------------------
# CREACIÓN DEL MODELO
# -------------------------
model = ConcreteModel()

# -------------------------
# CONJUNTOS
# -------------------------
model.L = Set(initialize=L)       # Localidades
model.D = Set(initialize=D)       # Municipios con demanda
model.E = Set(initialize=E)       # Estaciones de recarga
model.V = Set(initialize=V)       # Vehículos

# -------------------------
# VARIABLES DE DECISIÓN
# -------------------------
model.x = Var(model.L, model.L, model.V, domain=Binary)              # Ruta del vehículo
model.u = Var(model.L, model.V, domain=NonNegativeIntegers)          # Orden de visita (MTZ)
model.r = Var(model.L, model.V, domain=NonNegativeReals)            # Litros recargados
model.f = Var(model.L, model.V, domain=NonNegativeReals)            # Combustible restante
model.w = Var(model.L, model.V, domain=NonNegativeReals)            # Peso transportado

# -------------------------
# PARÁMETROS
# -------------------------
def dist_rule(model, i, j):
    return distancias[i-1][j-1]


model.dist = Param(model.L, model.L, initialize=dist_rule, within=NonNegativeReals, mutable=True)
model.demanda = Param(model.D, initialize=D_demanda, within=NonNegativeReals)
model.capacidad = Param(model.V, initialize=V_capacidad, within=NonNegativeReals)
model.autonomia = Param(model.V, initialize=V_autonomia, within=NonNegativeReals)
model.precio_comb = Param(model.L, initialize=precio_combustible, within=NonNegativeReals, default=0)
model.peso_max = Param(model.D, initialize=peso_max, within=NonNegativeReals, default=9999)
model.peaje = Param(model.D, initialize=costo_peaje, within=NonNegativeReals, default=0)

# -------------------------
# FUNCIÓN OBJETIVO
# -------------------------
def obj_rule(model):
    return (
        sum(model.dist[i, j] * model.x[i, j, k] for i in model.L for j in model.L if i != j for k in model.V) +
        sum(model.precio_comb[j] * model.r[j, k] for j in model.E for k in model.V) +
        sum(model.peaje[i] * model.w[i, k] for i in model.D for k in model.V)
    )

model.obj = Objective(rule=obj_rule, sense=minimize)

# -------------------------
# RESTRICCIONES
# -------------------------
model.res = ConstraintList()

# (0) Prohibir viajes del mismo nodo a sí mismo
for i in L:
    for k in V:
        model.res.add(model.x[i, i, k] == 0)

# (1) Cada cliente debe ser visitado una sola vez
for j in D:
    model.res.add(sum(model.x[i, j, k] for i in L if i != j for k in V) == 1)

# (2) Cada vehículo debe salir del puerto una vez
for k in V:
    model.res.add(sum(model.x[1, j, k] for j in L if j != 1) == 1)

# (3) Cada vehículo debe regresar al puerto una vez
for k in V:
    model.res.add(sum(model.x[i, 1, k] for i in L if i != 1) == 1)

# (4) Conservación de flujo
for h in D:
    for k in V:
        model.res.add(
            sum(model.x[i, h, k] for i in L if i != h) ==
            sum(model.x[h, j, k] for j in L if j != h)
        )

# (5) Subtour elimination (MTZ)
n = len(L)
for i in D:
    for j in D:
        if i != j:
            for k in V:
                model.res.add(model.u[i, k] - model.u[j, k] + n * model.x[i, j, k] <= n - 1)

# (6) Capacidad máxima por vehículo
for k in V:
    model.res.add(
        sum(model.demanda[i] * sum(model.x[i, j, k] for j in L if j != i) for i in D)
        <= model.capacidad[k]
    )

# (7) Autonomía más recarga
for k in V:
    model.res.add(
        sum(model.dist[i, j] * model.x[i, j, k] for i in L for j in L if i != j)
        <= model.autonomia[k] + sum(model.r[j, k] for j in E)
    )

# (8) Peso máximo permitido en cada municipio
for i in D:
    for k in V:
        model.res.add(model.w[i, k] <= model.peso_max[i])




SolverFactory('glpk').solve(model, tee=True)


import pandas as pd
from pyomo.environ import value

# Verificación de resultados
rutas = []

for k in V:
    tramos = [(i, j) for i in L for j in L if i != j and value(model.x[i, j, k]) > 0.5]

    if not tramos:
        continue

    # Ordenar la secuencia de nodos
    secuencia = [1]
    while True:
        ult = secuencia[-1]
        siguiente = [j for i, j in tramos if i == ult and j not in secuencia]
        if not siguiente:
            break
        secuencia.append(siguiente[0])

    # Extraer demanda, peso, peaje y recarga
    demandas = [D_demanda[n] for n in secuencia if n in D]
    pesos = [round(value(model.w[n, k]), 2) for n in secuencia if n in D]
    recargas = [round(value(model.r[n, k]), 2) for n in secuencia if n in E]
    costos_peaje = [round(peso_max[n] * costo_peaje.get(n, 0), 2) if n in D else 0 for n in secuencia]

    etiquetas = []
    for nodo in secuencia:
        if nodo == 1:
            etiquetas.append("PTO")
        elif nodo in D:
            etiquetas.append(f"MUN{str(nodo).zfill(2)}")
        elif nodo in E:
            etiquetas.append(f"EST{str(nodo).zfill(2)}")

    rutas.append({
        "VehicleId": f"CAM{str(k).zfill(3)}",
        "LoadCap": V_capacidad[k],
        "FuelCap": V_autonomia[k],
        "RouteSeq": "-".join(etiquetas),
        "Municipalities": len(demandas),
        "Demand": "-".join(str(int(d)) for d in demandas),
        "InitLoad": sum(demandas),
        "InitFuel": V_autonomia[k],
        "RefuelStops": len(recargas),
        "RefuelAmounts": "-".join(str(r) for r in recargas),
        "TollsVisited": sum(1 for p in costos_peaje if p > 0),
        "TollCosts": "-".join(str(int(p)) for p in costos_peaje if p > 0),
        "VehicleWeights": "-".join(str(p) for p in pesos),
        "Distance": round(sum(distancias[i-1][j-1] for i, j in tramos), 2),
        "Time": round(sum(distancias[i-1][j-1] for i, j in tramos) * 0.85, 2),
        "FuelCost": round(sum(value(model.r[n, k]) * precio_combustible.get(n, 0) for n in E), 2),
        "TollCost": round(sum(costos_peaje), 2),
        "TotalCost": round(
            sum(value(model.r[n, k]) * precio_combustible.get(n, 0) for n in E) +
            sum(costos_peaje), 2)
    })

df_verificacion = pd.DataFrame(rutas)

# Exportar resultados
df_verificacion.to_csv("verificacion_caso3.csv", index=False)
