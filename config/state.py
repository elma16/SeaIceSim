from os import path, makedirs
import itertools
import sys
import time
from firedrake import *
import numpy as np

__all__ = ["State"]


class SpaceCreator(object):

    def __call__(self, name, mesh=None, family=None, degree=None):
        try:
            return getattr(self, name)
        except AttributeError:
            value = FunctionSpace(mesh, family, degree)
            setattr(self, name, value)
            return value


class FieldCreator(object):

    def __init__(self, fieldlist=None, xn=None, dumplist=None, pickup=True):
        self.fields = []
        if fieldlist is not None:
            for name, func in zip(fieldlist, xn.split()):
                setattr(self, name, func)
                func.dump = name in dumplist
                func.pickup = pickup
                func.rename(name)
                self.fields.append(func)

    def __call__(self, name, space=None, dump=True, pickup=True):
        try:
            return getattr(self, name)
        except AttributeError:
            value = Function(space, name=name)
            setattr(self, name, value)
            value.dump = dump
            value.pickup = pickup
            self.fields.append(value)
            return value

    def __iter__(self):
        return iter(self.fields)


class PointDataOutput(object):
    def __init__(self, filename, ndt, field_points, description,
                 field_creator, comm, create=True):
        """Create a dump file that stores fields evaluated at points.

        :arg filename: The filename.
        :arg field_points: Iterable of pairs (field_name, evaluation_points).
        :arg description: Description of the simulation.
        :arg field_creator: The field creator (only used to determine
            datatype and shape of fields).
        :kwarg create: If False, assume that filename already exists
        """
        # Overwrite on creation.
        self.dump_count = 0
        self.filename = filename
        self.field_points = field_points
        self.comm = comm
        if not create:
            return
        if self.comm.rank == 0:
            with Dataset(filename, "w") as dataset:
                dataset.description = "Point data for simulation {desc}".format(desc=description)
                dataset.history = "Created {t}".format(t=time.ctime())
                # FIXME add versioning information.
                dataset.source = "Output from Gusto model"
                # Appendable dimension, timesteps in the model
                dataset.createDimension("time", None)

                var = dataset.createVariable("time", np.float64, ("time"))
                var.units = "seconds"
                # Now create the variable group for each field
                for field_name, points in field_points:
                    group = dataset.createGroup(field_name)
                    npts, dim = points.shape
                    group.createDimension("points", npts)
                    group.createDimension("geometric_dimension", dim)
                    var = group.createVariable("points", points.dtype,
                                               ("points", "geometric_dimension"))
                    var[:] = points

                    # Get the UFL shape of the field
                    field_shape = field_creator(field_name).ufl_shape
                    # Number of geometric dimension occurences should be the same as the length of the UFL shape
                    field_len = len(field_shape)
                    field_count = field_shape.count(dim)
                    assert field_len == field_count, "Geometric dimension occurrences do not match UFL shape"
                    # Create the variable with the required shape
                    dimensions = ("time", "points") + field_count*("geometric_dimension",)
                    group.createVariable(field_name, field_creator(field_name).dat.dtype, dimensions)

    def dump(self, field_creator, t):
        """Evaluate and dump field data at points.

        :arg field_creator: :class:`FieldCreator` for accessing
            fields.
        :arg t: Simulation time at which dump occurs.
        """

        val_list = []
        for field_name, points in self.field_points:
            val_list.append((field_name, np.asarray(field_creator(field_name).at(points))))

        if self.comm.rank == 0:
            with Dataset(self.filename, "a") as dataset:
                # Add new time index
                dataset.variables["time"][self.dump_count] = t
                for field_name, vals in val_list:
                    group = dataset.groups[field_name]
                    var = group.variables[field_name]
                    var[self.dump_count, :] = vals

        self.dump_count += 1


class DiagnosticsOutput(object):
    def __init__(self, filename, diagnostics, description, comm, create=True):
        """Create a dump file that stores diagnostics.

        :arg filename: The filename.
        :arg diagnostics: The :class:`Diagnostics` object.
        :arg description: A description.
        :kwarg create: If False, assume that filename already exists
        """
        self.filename = filename
        self.diagnostics = diagnostics
        self.comm = comm
        if not create:
            return
        if self.comm.rank == 0:
            with Dataset(filename, "w") as dataset:
                dataset.description = "Diagnostics data for simulation {desc}".format(desc=description)
                dataset.history = "Created {t}".format(t=time.ctime())
                dataset.source = "Output from Gusto model"
                dataset.createDimension("time", None)
                var = dataset.createVariable("time", np.float64, ("time", ))
                var.units = "seconds"
                for name in diagnostics.fields:
                    group = dataset.createGroup(name)
                    for diagnostic in diagnostics.available_diagnostics:
                        group.createVariable(diagnostic, np.float64, ("time", ))

    def dump(self, state, t):
        """Dump diagnostics.

        :arg state: The :class:`State` at which to compute the diagnostic.
        :arg t: The current time.
        """

        diagnostics = []
        for fname in self.diagnostics.fields:
            field = state.fields(fname)
            for dname in self.diagnostics.available_diagnostics:
                diagnostic = getattr(self.diagnostics, dname)
                diagnostics.append((fname, dname, diagnostic(field)))

        if self.comm.rank == 0:
            with Dataset(self.filename, "a") as dataset:
                idx = dataset.dimensions["time"].size
                dataset.variables["time"][idx:idx + 1] = t
                for fname, dname, value in diagnostics:
                    group = dataset.groups[fname]
                    var = group.variables[dname]
                    var[idx:idx + 1] = value


class State(object):
    """
    Build a model state to keep the variables in, and specify parameters.

    :arg mesh: The :class:`Mesh` to use.
    :arg timestepping: class containing timestepping parameters
    :arg output: class containing output parameters
    :arg parameters: class containing physical parameters
    """

    def __init__(self, mesh,timestepping=None,output=None,parameters=None):

        self.timestepping = timestepping
        if output is None:
            raise RuntimeError("You must provide a directory name for dumping results")
        else:
            self.output = output
        self.parameters = parameters


        # The mesh
        self.mesh = mesh

        # Build the spaces
        V = VectorFunctionSpace(mesh, "CR", 1)
        S = TensorFunctionSpace(mesh, "DG", 0)
        U = FunctionSpace(mesh, "CR", 1)
        W = MixedFunctionSpace([V, U, U, S])

        # Allocate state
        self._allocate_state()
        if self.output.dumplist is None:
            self.output.dumplist = fieldlist
        self.fields = FieldCreator(fieldlist, self.xn, self.output.dumplist)

        # set up bcs
        V = self.fields('u').function_space()
        self.bcs = []
        if V.extruded:
            self.bcs.append(DirichletBC(V, 0.0, "bottom"))
            self.bcs.append(DirichletBC(V, 0.0, "top"))
        for id in self.u_bc_ids:
            self.bcs.append(DirichletBC(V, 0.0, id))

        self.dumpfile = None

        #  Constant to hold current time
        self.t = Constant(0.0)

    def setup_dump(self, t, tmax, pickup=False):
        """
        Setup dump files
        Check for existence of directory so as not to overwrite
        output files
        Setup checkpoint file

        :arg tmax: model stop time
        :arg pickup: recover state from the checkpointing file if true,
        otherwise dump and checkpoint to disk. (default is False).
        """

        if any([self.output.dump_vtus, self.output.dumplist_latlon,
                self.output.dump_diagnostics, self.output.point_data,
                self.output.checkpoint and not pickup]):
            # setup output directory and check that it does not already exist
            self.dumpdir = path.join("results", self.output.dirname)
            running_tests = '--running-tests' in sys.argv or "pytest" in self.output.dirname
            if self.mesh.comm.rank == 0:
                if not running_tests and path.exists(self.dumpdir) and not pickup:
                    raise IOError("results directory '%s' already exists"
                                  % self.dumpdir)
                else:
                    if not running_tests:
                        makedirs(self.dumpdir)

        if self.output.dump_vtus:

            # setup pvd output file
            outfile = path.join(self.dumpdir, "field_output.pvd")
            self.dumpfile = File(
                outfile, project_output=self.output.project_fields,
                comm=self.mesh.comm)

            # make list of fields to dump
            self.to_dump = [field for field in self.fields if field.dump]

            # make dump counter
            self.dumpcount = itertools.count()

        # if there are fields to be dumped in latlon coordinates,
        # setup the latlon coordinate mesh and make output file
        if len(self.output.dumplist_latlon) > 0:
            mesh_ll = get_latlon_mesh(self.mesh)
            outfile_ll = path.join(self.dumpdir, "field_output_latlon.pvd")
            self.dumpfile_ll = File(outfile_ll,
                                    project_output=self.output.project_fields,
                                    comm=self.mesh.comm)

            # make functions on latlon mesh, as specified by dumplist_latlon
            self.to_dump_latlon = []
            for name in self.output.dumplist_latlon:
                f = self.fields(name)
                field = Function(
                    functionspaceimpl.WithGeometry(
                        f.function_space(), mesh_ll),
                    val=f.topological, name=name+'_ll')
                self.to_dump_latlon.append(field)

        # we create new netcdf files to write to, unless pickup=True, in
        # which case we just need the filenames
        if self.output.dump_diagnostics:
            diagnostics_filename = self.dumpdir+"/diagnostics.nc"
            self.diagnostic_output = DiagnosticsOutput(diagnostics_filename,
                                                       self.diagnostics,
                                                       self.output.dirname,
                                                       self.mesh.comm,
                                                       create=not pickup)

        if len(self.output.point_data) > 0:
            pointdata_filename = self.dumpdir+"/point_data.nc"
            ndt = int(tmax/self.timestepping.dt)
            self.pointdata_output = PointDataOutput(pointdata_filename, ndt,
                                                    self.output.point_data,
                                                    self.output.dirname,
                                                    self.fields,
                                                    self.mesh.comm,
                                                    create=not pickup)

        # if we want to checkpoint and are not picking up from a previous
        # checkpoint file, setup the dumb checkpointing
        if self.output.checkpoint and not pickup:
            self.chkpt = DumbCheckpoint(path.join(self.dumpdir, "chkpt"),
                                        mode=FILE_CREATE)
            # make list of fields to pickup (this doesn't include
            # diagnostic fields)
            self.to_pickup = [field for field in self.fields if field.pickup]

        # if we want to checkpoint then make a checkpoint counter
        if self.output.checkpoint:
            self.chkptcount = itertools.count()

        # dump initial fields
        self.dump(t)

    def pickup_from_checkpoint(self):
        """
        :arg t: the current model time (default is zero).
        """
        if self.output.checkpoint:
            # Open the checkpointing file for writing
            chkfile = path.join(self.dumpdir, "chkpt")
            with DumbCheckpoint(chkfile, mode=FILE_READ) as chk:
                # Recover all the fields from the checkpoint
                for field in self.to_pickup:
                    chk.load(field)
                t = chk.read_attribute("/", "time")
                next(self.dumpcount)
            # Setup new checkpoint
            self.chkpt = DumbCheckpoint(path.join(self.dumpdir, "chkpt"), mode=FILE_CREATE)
        else:
            raise ValueError("Must set checkpoint True if pickup")

        return t

    def dump(self, t):
        """
        Dump output
        """
        output = self.output

        # Diagnostics:
        # Compute diagnostic fields
        for field in self.diagnostic_fields:
            field(self)

        if output.dump_diagnostics:
            # Output diagnostic data
            self.diagnostic_output.dump(self, t)

        if len(output.point_data) > 0:
            # Output pointwise data
            self.pointdata_output.dump(self.fields, t)

        # Dump all the fields to the checkpointing file (backup version)
        if output.checkpoint and (next(self.chkptcount) % output.chkptfreq) == 0:
            for field in self.to_pickup:
                self.chkpt.store(field)
            self.chkpt.write_attribute("/", "time", t)

        if output.dump_vtus and (next(self.dumpcount) % output.dumpfreq) == 0:
            # dump fields
            self.dumpfile.write(*self.to_dump)

            # dump fields on latlon mesh
            if len(output.dumplist_latlon) > 0:
                self.dumpfile_ll.write(*self.to_dump_latlon)

    def initialise(self, initial_conditions):
        """
        Initialise state variables

        :arg initial_conditions: An iterable of pairs (field_name, pointwise_value)
        """
        for name, ic in initial_conditions:
            f_init = getattr(self.fields, name)
            f_init.assign(ic)
            f_init.rename(name)

    def set_reference_profiles(self, reference_profiles):
        """
        Initialise reference profiles

        :arg reference_profiles: An iterable of pairs (field_name, interpolatory_value)
        """
        for name, profile in reference_profiles:
            field = getattr(self.fields, name)
            ref = self.fields(name+'bar', field.function_space(), False)
            ref.interpolate(profile)

    def _allocate_state(self):
        """
        Construct Functions to store the state variables.
        """

        W = self.W
        self.xn = Function(W)
        self.xstar = Function(W)
        self.xp = Function(W)
        self.xnp1 = Function(W)
        self.xrhs = Function(W)
        self.xb = Function(W)  # store the old state for diagnostics
        self.dy = Function(W)

