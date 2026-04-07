import FrameStack as FrS
import matplotlib.pyplot as plt

path = '/Users/jansen/Code/Cycling/Bike_geometry/Geometry_files/Ribble_endurance_L.txt'

f,ax = plt.subplots(1, figsize=(10,10))

inst = FrS.FrameStack(path)
inst.plot_bike_3D(f,ax)


plt.show()