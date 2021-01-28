import sys
from seaice import *
from firedrake import *

# TEST 3 : BOX TEST

if '--test' in sys.argv:
    timestep = 600
    number_of_triangles = 71
    day = 60 * 60 * 24
    month = 31 * day
    timescale = month
    dumpfreq = 100
else:
    timescale = 100
    number_of_triangles = 30
    timestep = 1
    dumpfreq = 10

dirname = "./output/box_test/u_timescale={}_timestep={}.pvd".format(timescale, timestep)

plot_dirname = "./plots/box_test_energy.png"

length = 10 ** 6
mesh = SquareMesh(number_of_triangles, number_of_triangles, length)
rheology = 'VP'

timestepping = TimesteppingParameters(timescale=timescale, timestep=timestep)
output = OutputParameters(dirname=dirname, dumpfreq=dumpfreq)
solver = SolverParameters()
params = SeaIceParameters()

bt = SeaIceModel(mesh=mesh, length=length, rheology=rheology, timestepping=timestepping, output=output, params=params,
                 solver_params=solver)

t = 0
while t < timescale - 0.5 * timestep:
    bt.solve()
    bt.update()
    bt.dump(t)
    t += timestep
    bt.progress(t)
