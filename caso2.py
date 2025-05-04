from geopy.distance import geodesic
import pandas as pd
from pyomo.environ import *
from pyomo.opt import SolverFactory

#----- procesamiento de datos/ encontrando las distancias entre todas las locations -----
# https://geopy.readthedocs.io/en/stable/#module-geopy.distance 

clientes = pd.read_csv('Proyecto_C_Caso2/clients.csv')
depositos = pd.read_csv('Proyecto_C_Caso2/depots.csv')
estaciones = pd.read_csv('Proyecto_C_Caso2/stations.csv')
vehiculos = pd.read_csv('Proyecto_C_Caso2/vehicles.csv')

df = pd.read_csv('Proyecto_Caso_Base/locations.csv')
# tomamos el mismo origen y las mismas primeras 15 localidades que en el caso base
df = df[df['LocationID'] < 16]

df.to_csv('Proyecto_C_Caso2/locations.csv', index=False)

for i in range(len(estaciones)):
    data= {'LocationID': estaciones['LocationID'][i],
            'Longitude': estaciones['Longitude'][i],
            'Latitude': estaciones['Latitude'][i],}
    data_f = pd.DataFrame([data])
    # modo a es de append pa ir añadiendo y como ya tiene encabezados header se pone en False
    data_f.to_csv('Proyecto_C_Caso2/locations.csv', mode='a', header=False, index=False)

locations_csv = pd.read_csv('Proyecto_C_Caso2/locations.csv')

locations = []
for i in range(len(locations_csv)):
    latitud = locations_csv['Latitude'][i]
    longitud = locations_csv['Longitude'][i]
    coord = (latitud, longitud)
    locs_i=[]
    j=0
    while j<27:
        latitud2 = locations_csv['Latitude'][j]
        longitud2 = locations_csv['Longitude'][j]
        coord2 = (latitud2, longitud2)

        locs_i.append(geodesic(coord, coord2).meters)
        j+=1
    locations.append(locs_i)

print (locations)
