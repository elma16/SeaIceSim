from seaice import *
from firedrake import *
from pathlib import Path

Path("./output/evp").mkdir(parents=True, exist_ok=True)

# TEST 2 : EVP

timestep = 10
dumpfreq = 10
timescale = 10**3

dirname = "./output/evp/u_timescale={}_timestep={}.pvd".format(timescale, timestep)
title = "EVP Plot"
diagnostic_dirname = "./output/evp/evp.nc"
plot_dirname = "./output/evp/evp_energy1000.png"

number_of_triangles = 35
length = 5 * 10 ** 5
mesh = SquareMesh(number_of_triangles, number_of_triangles, length)
x, y = SpatialCoordinate(mesh)

bcs_values = [0, 1, 1]
ics_values = [0, x / length, as_matrix([[1, 2], [3, 4]])]
ocean_curr = as_vector([0.1 * (2 * y - length) / length, -0.1 * (length - 2 * x) / length])
forcing = [ocean_curr]

timestepping = TimesteppingParameters(timescale=timescale, timestep=timestep)
output = OutputParameters(dirname=dirname, dumpfreq=dumpfreq)
solver = SolverParameters()
params = SeaIceParameters()

evp = ElasticViscousPlastic(mesh=mesh, length=length, bcs_values=bcs_values, ics_values=ics_values,
                            timestepping=timestepping, output=output, params=params, solver_params=solver,
                            forcing=forcing)

diag = OutputDiagnostics(description="EVP Test", dirname=diagnostic_dirname)

t = 0

while t < timescale - 0.5 * timestep:
    evp.solve(evp.usolver)
    evp.update(evp.w0, evp.w1)
    diag.dump(evp.u1, t)
    evp.dump(evp.u1, t)
    t += timestep
    evp.progress(t)

plotter = Plotter(dataset_dirname=diagnostic_dirname, diagnostic='energy', plot_dirname=plot_dirname,
                  timestepping=timestepping, title=title)

plotter.plot()
