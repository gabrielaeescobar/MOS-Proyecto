from geopy.distance import geodesic
import pandas as pd

# --- 1. Carga de archivos del Caso 3 ---
clientes = pd.read_csv('Proyecto_C_Caso3/clients.csv')
depositos = pd.read_csv('Proyecto_C_Caso3/depots.csv')
estaciones = pd.read_csv('Proyecto_C_Caso3/stations.csv')
vehiculos = pd.read_csv('Proyecto_C_Caso3/vehicles.csv')
peajes = pd.read_csv('Proyecto_C_Caso3/tolls.csv')  # <-- peajes para caso 3

# --- 2. Crear archivo locations.csv ---
# Empezamos con los mismos 15 nodos del caso base
df_base = pd.read_csv('Proyecto_Caso_Base/locations.csv')
df_base = df_base[df_base['LocationID'] < 16]  # PTO (1) + 14 municipios (2-15)
df_base.to_csv('Proyecto_C_Caso3/locations.csv', index=False)

# Agregar las estaciones al archivo de locations
for i in range(len(estaciones)):
    data = {
        'LocationID': estaciones.loc[i, 'LocationID'],
        'Longitude': estaciones.loc[i, 'Longitude'],
        'Latitude': estaciones.loc[i, 'Latitude']
    }
    df_station = pd.DataFrame([data])
    df_station.to_csv('Proyecto_C_Caso3/locations.csv', mode='a', header=False, index=False)

# Leer locations.csv actualizado
locations_csv = pd.read_csv('Proyecto_C_Caso3/locations.csv')

# --- 3. Calcular matriz de distancias (en kilómetros) ---
distancias = []
for i in range(len(locations_csv)):
    coord_i = (locations_csv.loc[i, 'Latitude'], locations_csv.loc[i, 'Longitude'])
    fila = []
    for j in range(len(locations_csv)):
        coord_j = (locations_csv.loc[j, 'Latitude'], locations_csv.loc[j, 'Longitude'])
        distancia = geodesic(coord_i, coord_j).kilometers
        fila.append(distancia)
    distancias.append(fila)

# --- 4. Verificación ---
print(f"Total de localidades cargadas: {len(locations_csv)}")
print("Distancia entre nodo 1 y nodo 2:", distancias[0][1])
