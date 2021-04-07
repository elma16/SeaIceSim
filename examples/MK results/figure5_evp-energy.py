from seaice import *
from firedrake import *
from pathlib import Path
from netCDF4 import Dataset
import numpy as np
import matplotlib.pyplot as plt

path = "./output/figure5"
Path(path).mkdir(parents=True, exist_ok=True)

'''
TEST 2 : EVP

File reproducing figure 5 from Mehlmann and Korn (2021)

Fig 5 a) Energy vs. t (0-24h)
compare evp and vp unstabilised and stabilised
Fig 5 b) Energy vs. t (0-24h)
evp unstabilised and stabilised applied to resolution (10km, 5km, 2.5km)
Fig 5 c) Energy (log) vs. resolution (10km, 5km, 2.5km)
'''

timestep = 0.1
dumpfreq = 10**10
timescale = 1

dirname = path + "/u.pvd"

fig5a_title = "Figure 5 a)"
fig5b_title = "Figure 5 b)"
fig5c_title = "Figure 5 c)"
d_dirname1 = path + "/evp_energy.nc"
d_dirname2 = path + "/evp_stab_energy.nc"
d_dirname3 = path + "/vp_energy.nc"
d_dirname4 = path + "/vp_stab_energy.nc"
fig5a_dirname = path + "/fig5a.png"
fig5b_dirname = path + "/fig5b.png"
fig5c_dirname = path + "/fig5c.png"

#i'm interpreting resolution to mean the number of triangles
number_of_triangles = 35
length = 5 * 10 ** 5
mesh = SquareMesh(number_of_triangles, number_of_triangles, length)
x, y = SpatialCoordinate(mesh)

ocean_curr = as_vector([0.1 * (2 * y - length) / length, -0.1 * (length - 2 * x) / length])


conditions = {'bc': {'u': 0},
              'ic': {'u': 0, 'a' : x / length, 'h' : 1, 's' : as_matrix([[0, 0], [0, 0]])},
              'ocean_curr': ocean_curr,
              'geo_wind' : Constant(as_vector([0, 0])),
              'family':'CR',
              'stabilised': {'state': False , 'alpha': 10},
              'simple' : False,
              'steady_state': False,
              'theta': 1}

conditions_stab = {'bc': {'u': 0},
              'ic': {'u': 0, 'a' : x / length, 'h' : 1, 's' : as_matrix([[0, 0], [0, 0]])},
              'ocean_curr': ocean_curr,
              'geo_wind' : Constant(as_vector([0, 0])),
              'family':'CR',
              'stabilised': {'state': True , 'alpha': 10},
              'simple' : False,
              'steady_state': False,
              'theta': 1}
        
timestepping = TimesteppingParameters(timescale=timescale, timestep=timestep)
output = OutputParameters(dirname=dirname, dumpfreq=dumpfreq)
solver = SolverParameters()
params = SeaIceParameters()

evp = ElasticViscousPlastic(mesh=mesh, conditions=conditions, timestepping=timestepping, output=output, params=params, solver_params=solver)

evp_stab = ElasticViscousPlastic(mesh=mesh, conditions=conditions_stab, timestepping=timestepping, output=output, params=params, solver_params=solver)

vp = ViscousPlastic(mesh=mesh, conditions=conditions, timestepping=timestepping, output=output, params=params, solver_params=solver)

vp_stab = ViscousPlastic(mesh=mesh, conditions=conditions_stab, timestepping=timestepping, output=output, params=params, solver_params=solver)

diag1 = OutputDiagnostics(description="EVP Energy", dirname=d_dirname1)
diag2 = OutputDiagnostics(description="EVP Stabilised Energy", dirname=d_dirname2)
diag3 = OutputDiagnostics(description="VP Energy", dirname=d_dirname3)
diag4 = OutputDiagnostics(description="VP Stabilised Energy", dirname=d_dirname4)
    
t = 0

while t < timescale - 0.5 * timestep:
    evp.solve(evp.usolver)
    evp.update(evp.w0, evp.w1)
    diag1.dump(evp.u1, t)
    evp.dump(evp.u1, evp.s1, t=t)
    evp_stab.solve(evp_stab.usolver)
    evp_stab.update(evp_stab.w0, evp_stab.w1)
    diag2.dump(evp_stab.u1, t)
    evp_stab.dump(evp_stab.u1, evp_stab.s1, t=t)
    vp.solve(vp.usolver)
    vp.update(vp.u0, vp.u1)
    diag3.dump(vp.u1, t)
    vp.dump(vp.u1, t=t)
    vp_stab.solve(vp_stab.usolver)
    vp_stab.update(vp_stab.u0, vp_stab.u1)
    diag4.dump(vp_stab.u1, t)
    vp_stab.dump(vp_stab.u1, t=t)
    t += timestep
    vp.progress(t)

# fig 5a
dataset1 = Dataset(d_dirname1, mode='r')
yaxis1 = dataset1.variables['energy'][:]
dataset1.close()
dataset2 = Dataset(d_dirname2, mode='r')
yaxis2 = dataset2.variables['energy'][:]
dataset2.close()
dataset3 = Dataset(d_dirname3, mode='r')
yaxis3 = dataset3.variables['energy'][:]
dataset3.close()
dataset4 = Dataset(d_dirname4, mode='r')
yaxis4 = dataset4.variables['energy'][:]
dataset4.close()
t = np.arange(0, timescale, timestep)
plt.plot(t,yaxis1,label='EVP')
plt.plot(t,yaxis2,label='EVP Stabilised')
plt.plot(t,yaxis3,label='VP')
plt.plot(t,yaxis4,label='VP Stabilised')
plt.ylabel(r'Energy of solution')
plt.xlabel(r'Time [s]')
plt.title(fig5a_title)
plt.legend(loc='best')
plt.savefig(fig5a_dirname)
