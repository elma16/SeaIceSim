from seaice import *
from firedrake import *
from pathlib import Path

Path("./output/evp").mkdir(parents=True, exist_ok=True)

'''
TEST 2 : EVP
'''

timestep = 0.1
dumpfreq = 10 ** 4
timescale = timestep * dumpfreq

stabilise = False
family = 'CG'

dirname = "./output/evp/u_timescale={}_timestep={}_stabilised={}_family={}.pvd".format(timescale, timestep, stabilise,
                                                                                       family)
title = "EVP Plot"
diagnostic_dirname = "./output/evp/evp.nc"
plot_dirname = "./output/evp/evp_energy.png"

number_of_triangles = 35
length = 5 * 10 ** 5
mesh = SquareMesh(number_of_triangles, number_of_triangles, length)
x, y = SpatialCoordinate(mesh)

ocean_curr = as_vector([0.1 * (2 * y - length) / length, -0.1 * (length - 2 * x) / length])
conditions = {'bc': {'u': 0},
              'ic': {'u': 0, 'a' : x / length, 's' : as_matrix([[0, 0], [0, 0]])},
              'ocean_curr': ocean_curr}

timestepping = TimesteppingParameters(timescale=timescale, timestep=timestep)
output = OutputParameters(dirname=dirname, dumpfreq=dumpfreq)
solver = SolverParameters()
params = SeaIceParameters()

evp = ElasticViscousPlastic(mesh=mesh, length=length, conditions=conditions, timestepping=timestepping, output=output,
                            params=params, solver_params=solver, stabilised=stabilise, family=family,theta=1,steady_state=False)

diag = OutputDiagnostics(description="EVP Test", dirname=diagnostic_dirname)

t = 0

while t < timescale - 0.5 * timestep:
    u0, s0 = evp.w0.split()
    evp.solve(evp.usolver)
    evp.update(evp.w0, evp.w1)
    # diag.dump(evp.u1, t)
    evp.dump(evp.u1, evp.s1, t=t)
    t += timestep
    evp.progress(t)

# plotter = Plotter(dataset_dirname=diagnostic_dirname, diagnostic='energy', plot_dirname=plot_dirname,
#                  timestepping=timestepping, title=title)

# plotter.plot()
