import Geometry as G
import matplotlib.pyplot as plt

path = '/Users/jansen/Code/Cycling/Bike_geometry/Geometry_files/Canyon_Endurace_M.txt'

f,ax = plt.subplots(1, figsize=(10,10))

inst = G.Geometry(path)
inst.plot_bike_3D(f,ax)


plt.show()