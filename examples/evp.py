from seaice import *
from firedrake import *

# TEST 2 : EVP

timestep = 10 ** (-1)
dumpfreq = 10
timescale = 10

dirname = "./output/EVP/u_timescale={}_timestep={}.pvd".format(timescale, timestep)

number_of_triangles = 35
length = 5 * 10 ** 5
mesh = SquareMesh(number_of_triangles, number_of_triangles, length)
rheology = 'VP'

timestepping = TimesteppingParameters(timescale=timescale, timestep=timestep)
output = OutputParameters(dirname=dirname, dumpfreq=dumpfreq)
solver = SolverParameters()
params = SeaIceParameters()

evp = SeaIceModel(mesh=mesh, length=length, rheology=rheology, timestepping=timestepping, output=output, params=params,
                  solver_params=solver)

t = 0
while t < timescale - 0.5 * timestep:
    evp.solve()
    evp.update()
    evp.dump(t)
    t += timestep
    evp.progress(t)
