# -----------------------------
# CASO 3 - MODELO Y EXPORTACIÓN
# -----------------------------

# Guardar este archivo como `caso3_modelo.py`

from geopy.distance import geodesic
import pandas as pd
from pyomo.environ import *
from pyomo.opt import SolverFactory, TerminationCondition

# CARGA DE DATOS
clientes = pd.read_csv('Proyecto_C_Caso3/clients.csv')
depositos = pd.read_csv('Proyecto_C_Caso3/depots.csv')
estaciones = pd.read_csv('Proyecto_C_Caso3/stations.csv')
vehiculos = pd.read_csv('Proyecto_C_Caso3/vehicles.csv')
peajes = pd.read_csv('Proyecto_C_Caso3/tolls.csv')

# UNIFICAR LOCALIDADES
base = pd.read_csv('Proyecto_Caso_Base/locations.csv')
base = base[base['LocationID'] < 16]
base.to_csv('Proyecto_C_Caso3/locations.csv', index=False)
for i in range(len(estaciones)):
    pd.DataFrame([{
        'LocationID': estaciones.loc[i, 'LocationID'],
        'Longitude': estaciones.loc[i, 'Longitude'],
        'Latitude': estaciones.loc[i, 'Latitude']
    }]).to_csv('Proyecto_C_Caso3/locations.csv', mode='a', header=False, index=False)

locations = pd.read_csv('Proyecto_C_Caso3/locations.csv')
distancias = [
    [geodesic((locations.loc[i, 'Latitude'], locations.loc[i, 'Longitude']),
              (locations.loc[j, 'Latitude'], locations.loc[j, 'Longitude'])).kilometers
     for j in range(len(locations))] for i in range(len(locations))
]

# CONJUNTOS
L = list(range(1, len(locations) + 1))
D = list(range(2, 16))
E = list(estaciones['LocationID'])
V = list(range(1, len(vehiculos) + 1))

# PARÁMETROS
D_demanda = {row['LocationID']: row['Demand'] for _, row in clientes.iterrows()}
clientes['MaxWeight'] = clientes['MaxWeight'].fillna(9999)
peso_max = {row['LocationID']: row['MaxWeight'] for _, row in clientes.iterrows()}
precio_combustible = {int(row['LocationID']): float(row['FuelCost']) for _, row in estaciones.iterrows()}
costo_peaje = {D[i]: 0 if pd.isna(peajes.loc[i, 'RatePerTon']) else peajes.loc[i, 'RatePerTon'] for i in range(len(peajes))}
V_capacidad = {i+1: vehiculos.loc[i, 'Capacity'] for i in range(len(vehiculos))}
V_autonomia = {i+1: vehiculos.loc[i, 'Range'] for i in range(len(vehiculos))}

# MODELO
model = ConcreteModel()
model.L = Set(initialize=L)
model.D = Set(initialize=D)
model.E = Set(initialize=E)
model.V = Set(initialize=V)
model.x = Var(model.L, model.L, model.V, domain=Binary)
model.u = Var(model.L, model.V, domain=NonNegativeIntegers)
model.r = Var(model.L, model.V, domain=NonNegativeReals)
model.w = Var(model.L, model.V, domain=NonNegativeReals)

def dist_rule(m, i, j): return distancias[i-1][j-1]
model.dist = Param(model.L, model.L, initialize=dist_rule, within=NonNegativeReals, mutable=True)
model.demanda = Param(model.D, initialize=D_demanda)
model.capacidad = Param(model.V, initialize=V_capacidad)
model.autonomia = Param(model.V, initialize=V_autonomia)
model.precio_comb = Param(model.L, initialize=precio_combustible, default=0)
model.peso_max = Param(model.D, initialize=peso_max, default=9999)
model.peaje = Param(model.D, initialize=costo_peaje, default=0)

# OBJETIVO
model.obj = Objective(expr=
    sum(model.dist[i,j]*model.x[i,j,k] for i in L for j in L if i!=j for k in V) +
    sum(model.precio_comb[j]*model.r[j,k] for j in E for k in V) +
    sum(model.peaje[i]*model.w[i,k] for i in D for k in V),
    sense=minimize)

# RESTRICCIONES
model.res = ConstraintList()
for i in L:
    for k in V:
        model.res.add(model.x[i, i, k] == 0)
for j in D:
    model.res.add(sum(model.x[i, j, k] for i in L if i != j for k in V) == 1)
for k in V:
    model.res.add(sum(model.x[1, j, k] for j in L if j != 1) == 1)
    model.res.add(sum(model.x[i, 1, k] for i in L if i != 1) == 1)
for h in D:
    for k in V:
        model.res.add(sum(model.x[i, h, k] for i in L if i != h) == sum(model.x[h, j, k] for j in L if j != h))
n = len(L)
for i in D:
    for j in D:
        if i != j:
            for k in V:
                model.res.add(model.u[i, k] - model.u[j, k] + n * model.x[i, j, k] <= n - 1)
for k in V:
    model.res.add(sum(model.demanda[i] * sum(model.x[i, j, k] for j in L if j != i) for i in D) <= model.capacidad[k])
    model.res.add(sum(model.dist[i, j]*model.x[i, j, k] for i in L for j in L if i != j) <= model.autonomia[k] + sum(model.r[j, k] for j in E))
for i in D:
    for k in V:
        model.res.add(model.w[i, k] <= model.peso_max[i])

# SOLUCIONAR Y GUARDAR RESULTADOS EN CSV
results = SolverFactory('glpk').solve(model, tee=False)
print("\n✅ Estado del solver:", results.solver.termination_condition)

# GUARDAR DECISIONES DE x EN CSV
soluciones = []
for k in V:
    for i in L:
        for j in L:
            if i != j and value(model.x[i, j, k]) > 0.5:
                soluciones.append({'VehicleId': k, 'From': i, 'To': j})

pd.DataFrame(soluciones).to_csv('arcos_activados.csv', index=False)
