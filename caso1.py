from __future__ import division
from pyomo.environ import *
from pyomo.opt import SolverFactory

Model = ConcreteModel()

# Implementar un modelo básico tipo CVRP con un origen nacional (puerto) y destinos (municipios).
# Incluir restricciones de capacidad y autonomía de los vehículos.
# Validar factibilidad de la solución considerando solamente distancia y demanda.

# Data de entrada
numPuertos = 1
numPuntosDestino = 14
numEstacionesServicio = 3
numLocalidades = numPuertos+numPuntosDestino+numEstacionesServicio

numVehiculos = 8

# Conjuntos
P= RangeSet(1, numPuertos)  
D = RangeSet(1, numPuntosDestino)   
E = RangeSet(1, numEstacionesServicio)    
V = RangeSet(1, numVehiculos)

# Parámetros

# Variables de decisión


