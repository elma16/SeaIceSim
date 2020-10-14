from firedrake import *

try:
  import matplotlib.pyplot as plt
except:
  warning("Matplotlib not imported")

def box_test():
    '''
    from Mehlmann and Korn, 2020
    Section 4.3
    Box-Test conditions
    Domain:
        L_x = L_y = 1000000 (meters)
    ocean current:
        o_1 = 0.1*(2*y - L_y)/L_y
        o_2 = -0.1*(L_x - 2*x)/L_x
    wind velocity:
        v_1 = 5 + sin(2*pi*t/T)-3)*(sin(2*pi*x/L_x)*sin(2*pi*y/L_y)
        v_2 = 5 + sin(2*pi*t/T)-3)*(sin(2*pi*y/L_x)*sin(2*pi*x/L_y)
    timestep:
        k = 600 (seconds)
    subcycles:
        N_evp = 500
    total time:
        one month T = 2678400 (seconds)
    Initial Conditions:
        v(0) = 0
        h(0) = 1
        A(0) = x/L_x

    Solved using the mEVP solver

    '''

    n = 30
    L = 1000000
    mesh = SquareMesh(n, n, L)

    V = VectorFunctionSpace(mesh, "CR", 1)
    W = FunctionSpace(mesh, "CR", 1)
    U = MixedFunctionSpace((V, W, W))

    # sea ice velocity
    u_ = Function(V, name="Velocity")
    u = Function(V, name="VelocityNext")

    # mean height of sea ice
    h_ = Function(W, name="Height")
    h = Function(W, name="HeightNext")

    # sea ice concentration
    A_ = Function(W,name="Concentration")
    A = Function(W,name="ConcentrationNext")

    #test functions
    v = TestFunction(V)
    w = TestFunction(W)
    q = TestFunction(W)


    x, y = SpatialCoordinate(mesh)

    # initial conditions

    u_.assign(0)

    h = Constant(1)

    A = x/L

    timestep = 1/n

    T = 100

    # defining the constants to be used in the sea ice momentum equation:

    # the sea ice density
    rho = Constant(900)

    # gravity
    g = Constant(10)

    # Coriolis parameter
    cor = Constant(1.46 * 10 ** (-4))

    # air density
    rho_a = Constant(1.3)

    # air drag coefficient
    C_a = Constant(1.2 * 10 ** (-3))

    # water density
    rho_w = Constant(1026)

    # water drag coefficient
    C_w = Constant(5.5 * 10 ** (-3))

    # ice strength parameter
    P_star = Constant(27.5 * 10 ** 3)

    # ice concentration parameter
    C = Constant(20)

    #  ellipse ratio
    e = Constant(2)

    # geostrophic wind

    geo_wind = as_vector([5 + (sin(2*pi*t/T)-3)*sin(2*pi*x/L)*sin(2*pi*y/L),5 + (sin(2*pi*t/T)-3)*sin(2*pi*y/L)*sin(2*pi*x/L)])

    # ocean current

    ocean_curr = as_vector([0.1*(2*y - L)/L,-0.1*(L - 2*x)/L])

    # mEVP rheology

    alpha = Constant(500)
    beta = Constant(500)

    # strain rate tensor, where grad(u) is the jacobian matrix of u
    ep_dot = 1 / 2 * (grad(u) + transpose(grad(u)))

    # deviatoric part of the strain rate tensor
    ep_dot_prime = ep_dot - 1 / 2 * tr(ep_dot) * Identity(2)

    # ice strength
    P = P_star * h * exp(-C * (1 - A))

    Delta_min = Constant(2 * 10 ** (-9))

    Delta = sqrt(Delta_min ** 2 + 2 * e ** (-2) * inner(ep_dot_prime, ep_dot_prime) + tr(ep_dot) ** 2)

    # viscosities
    zeta = P / (2 * Delta)
    eta = zeta * e ** (-2)

    # internal stress tensor
    sigma = 2 * eta * ep_dot + (zeta - eta) * tr(ep_dot) * Identity(2) - P / 2 * Identity(2)

    # solve the discretised sea ice momentum equation

    # constructing the discretised weak form

    # momentum equation
    Lm = (inner(rho * h * (u - u_) / timestep - rho * h * cor * as_vector([u[1] - ocean_curr[1], ocean_curr[0] - u[0]])
               + rho_a * C_a * dot(geo_wind, geo_wind) * geo_wind + rho_w * C_w * dot(u - ocean_curr, u - ocean_curr) * (
                           ocean_curr - u), v) +
         inner(sigma, grad(v))) * dx

    t = 0.0

    hfile = File('h.pvd')
    hfile.write(h_, time=t)
    all_hs = []
    end = T
    while (t <= end):
        solve(Lm == 0, u)
        u_.assign(u)
        t += timestep
        hfile.write(h_, time=t)
        print(t)

    try:
      fig, axes = plt.subplots()
      plot(all_hs[-1], axes=axes)
    except Exception as e:
      warning("Cannot plot figure. Error msg: '%s'" % e)

    try:
      plt.show()
    except Exception as e:
      warning("Cannot show figure. Error msg: '%s'" % e)

def strain_rate_tensor():
    '''
    from Mehlmann and Korn, 2020
    Section 4.2
    L = 500000
    pi_x = pi_y = pi/L
    By construction, the analytical solution is
        v_1 = -sin(pi_x*x)*sin(pi_y*y)
        v_2 = -sin(pi_x*x)*sin(pi_y*y)


    '''
    n = 30
    L = 500000
    mesh = SquareMesh(n, n, L)

    V = VectorFunctionSpace(mesh, "CR", 1)

    # sea ice velocity
    u_ = Function(V, name="Velocity")
    u = Function(V, name="VelocityNext")

    # test functions
    v = TestFunction(V)

    x, y = SpatialCoordinate(mesh)

    # initial conditions

    u_.assign(0)

    h = Constant(1)

    A = Constant(1)

    timestep = 10

    T = 100

    # defining the constants to be used in the sea ice momentum equation:

    # the sea ice density
    rho = Constant(900)

    # gravity
    g = Constant(10)

    # Coriolis parameter
    cor = Constant(1.46 * 10 ** (-4))

    # air density
    rho_a = Constant(1.3)

    # air drag coefficient
    C_a = Constant(1.2 * 10 ** (-3))

    # water density
    rho_w = Constant(1026)

    # water drag coefficient
    C_w = Constant(5.5 * 10 ** (-3))

    # ice strength parameter
    P_star = Constant(27.5 * 10 ** 3)

    # ice concentration parameter
    C = Constant(20)

    #  ellipse ratio
    e = Constant(2)

    # strain rate tensor, where grad(u) is the jacobian matrix of u
    ep_dot = 1 / 2 * (grad(u) + transpose(grad(u)))

    # deviatoric part of the strain rate tensor
    ep_dot_prime = ep_dot - 1 / 2 * tr(ep_dot) * Identity(2)

    # ice strength
    P = P_star * h * exp(-C * (1 - A))

    Delta_min = Constant(2 * 10 ** (-9))

    Delta = sqrt(Delta_min ** 2 + 2 * e ** (-2) * inner(ep_dot_prime, ep_dot_prime) + tr(ep_dot) ** 2)

    # viscosities
    zeta = P / (2 * Delta)

    # internal stress tensor
    sigma = zeta/2*(grad(u)+transpose(grad(u)))

    pi_x = pi/L

    R = zeta/2*(3/2*pi_x**2*sin(pi_x*x)*sin(pi_x*y)-1/2*pi_x**2*cos(pi_x*x)*cos(pi_x*y))

    # momentum equation
    Lm = (inner((u - u_)/timestep,v) + inner(sigma,grad(v)))*dx

    t = 0.0

    ufile = File('strain_rate_tensor_u.pvd')
    ufile.write(u_, time=t)
    all_us = []
    end = T
    while (t <= end):
        solve(Lm == 0, u)
        u_.assign(u)
        t += timestep
        ufile.write(u_, time=t)
        print(t)

    try:
        fig, axes = plt.subplots()
        plot(all_us[-1], axes=axes)
    except Exception as e:
        warning("Cannot plot figure. Error msg: '%s'" % e)

    try:
        plt.show()
    except Exception as e:
        warning("Cannot show figure. Error msg: '%s'" % e)

def strain_rate_tensor_stabilised():
    '''
    from Mehlmann and Korn, 2020
    Section 4.2
    L = 500000
    pi_x = pi_y = pi/L
    By construction, the analytical solution is
        v_1 = -sin(pi_x*x)*sin(pi_y*y)
        v_2 = -sin(pi_x*x)*sin(pi_y*y)


    '''
    n = 30
    L = 500000
    mesh = SquareMesh(n, n, L)

    V = VectorFunctionSpace(mesh, "CR", 1)

    # sea ice velocity
    u_ = Function(V, name="Velocity")
    u = Function(V, name="VelocityNext")

    # test functions
    v = TestFunction(V)

    x, y = SpatialCoordinate(mesh)

    # initial conditions

    u_.assign(0)

    h = Constant(1)

    A = Constant(1)

    timestep = 10

    T = 100

    # defining the constants to be used in the sea ice momentum equation:

    # the sea ice density
    rho = Constant(900)

    # gravity
    g = Constant(10)

    # Coriolis parameter
    cor = Constant(1.46 * 10 ** (-4))

    # air density
    rho_a = Constant(1.3)

    # air drag coefficient
    C_a = Constant(1.2 * 10 ** (-3))

    # water density
    rho_w = Constant(1026)

    # water drag coefficient
    C_w = Constant(5.5 * 10 ** (-3))

    # ice strength parameter
    P_star = Constant(27.5 * 10 ** 3)

    # ice concentration parameter
    C = Constant(20)

    #  ellipse ratio
    e = Constant(2)

    # strain rate tensor, where grad(u) is the jacobian matrix of u
    ep_dot = 1 / 2 * (grad(u) + transpose(grad(u)))

    # deviatoric part of the strain rate tensor
    ep_dot_prime = ep_dot - 1 / 2 * tr(ep_dot) * Identity(2)

    # ice strength
    P = P_star * h * exp(-C * (1 - A))

    Delta_min = Constant(2 * 10 ** (-9))

    Delta = sqrt(Delta_min ** 2 + 2 * e ** (-2) * inner(ep_dot_prime, ep_dot_prime) + tr(ep_dot) ** 2)

    # viscosities
    zeta = P / (2 * Delta)

    # internal stress tensor
    sigma = zeta/2*(grad(u))

    pi_x = pi/L

    R = zeta/2*(3/2*pi_x**2*sin(pi_x*x)*sin(pi_x*y)-1/2*pi_x**2*cos(pi_x*x)*cos(pi_x*y))

    # momentum equation
    Lm = (inner((u - u_)/timestep,v) + inner(sigma,grad(v)))*dx

    t = 0.0

    ufile = File('strain_rate_tensor_u.pvd')
    ufile.write(u_, time=t)
    all_us = []
    end = T
    while (t <= end):
        solve(Lm == 0, u)
        u_.assign(u)
        t += timestep
        ufile.write(u_, time=t)
        print(t)

    try:
        fig, axes = plt.subplots()
        plot(all_us[-1], axes=axes)
    except Exception as e:
        warning("Cannot plot figure. Error msg: '%s'" % e)

    try:
        plt.show()
    except Exception as e:
        warning("Cannot show figure. Error msg: '%s'" % e)

def VP_EVP_test1():
    '''
    from Mehlmann and Korn, 2020
    Section 4.2
    VP+EVP Test 1
    Solve a modified momentum equation
    L_x = L_y = L = 500000
    vw_1 = 0.1*(2y-L_y)/L_y
    vw_2 = -0.1*(L_x-2x)/L_x
    v(0) = 0
    h = 1
    A = x/L_x
    '''

    n = 30
    L = 1000000
    mesh = SquareMesh(n, n, L)

    V = VectorFunctionSpace(mesh, "CR", 1)
    W = FunctionSpace(mesh, "CR", 1)
    U = MixedFunctionSpace((V, W, W))

    # sea ice velocity
    u_ = Function(V, name="Velocity")
    u = Function(V, name="VelocityNext")

    # mean height of sea ice
    h_ = Function(W, name="Height")
    h = Function(W, name="HeightNext")

    # sea ice concentration
    A_ = Function(W,name="Concentration")
    A = Function(W,name="ConcentrationNext")

    #test functions
    v = TestFunction(V)
    w = TestFunction(W)
    q = TestFunction(W)


    x, y = SpatialCoordinate(mesh)

    # initial conditions

    u_.assign(0)

    h = Constant(1)

    A = x/L

    timestep = 1/n

    T = 100

    # defining the constants to be used in the sea ice momentum equation:

    # the sea ice density
    rho = Constant(900)

    # gravity
    g = Constant(10)

    # Coriolis parameter
    cor = Constant(1.46 * 10 ** (-4))

    # air density
    rho_a = Constant(1.3)

    # air drag coefficient
    C_a = Constant(1.2 * 10 ** (-3))

    # water density
    rho_w = Constant(1026)

    # water drag coefficient
    C_w = Constant(5.5 * 10 ** (-3))

    # ice strength parameter
    P_star = Constant(27.5 * 10 ** 3)

    # ice concentration parameter
    C = Constant(20)

    #  ellipse ratio
    e = Constant(2)

    # geostrophic wind

    geo_wind = as_vector([5 + (sin(2*pi*t/T)-3)*sin(2*pi*x/L)*sin(2*pi*y/L),5 + (sin(2*pi*t/T)-3)*sin(2*pi*y/L)*sin(2*pi*x/L)])

    # ocean current

    ocean_curr = as_vector([0.1*(2*y - L)/L,-0.1*(L - 2*x)/L])

    # mEVP rheology

    alpha = Constant(500)
    beta = Constant(500)

    # strain rate tensor, where grad(u) is the jacobian matrix of u
    ep_dot = 1 / 2 * (grad(u) + transpose(grad(u)))

    # deviatoric part of the strain rate tensor
    ep_dot_prime = ep_dot - 1 / 2 * tr(ep_dot) * Identity(2)

    # ice strength
    P = P_star * h * exp(-C * (1 - A))

    Delta_min = Constant(2 * 10 ** (-9))

    Delta = sqrt(Delta_min ** 2 + 2 * e ** (-2) * inner(ep_dot_prime, ep_dot_prime) + tr(ep_dot) ** 2)

    # viscosities
    zeta = P / (2 * Delta)
    eta = zeta * e ** (-2)

    # internal stress tensor
    sigma = 2 * eta * ep_dot + (zeta - eta) * tr(ep_dot) * Identity(2) - P / 2 * Identity(2)

    # solve the discretised sea ice momentum equation

    # constructing the discretised weak form

    # momentum equation
    Lm = (inner(rho * h * (u - u_) / timestep - rho * h * cor * as_vector([u[1] - ocean_curr[1], ocean_curr[0] - u[0]])
               + rho_a * C_a * dot(geo_wind, geo_wind) * geo_wind + rho_w * C_w * dot(u - ocean_curr, u - ocean_curr) * (
                           ocean_curr - u), v) +
         inner(sigma, grad(v))) * dx

    t = 0.0

    hfile = File('h.pvd')
    hfile.write(h_, time=t)
    all_hs = []
    end = T
    while (t <= end):
        solve(Lm == 0, u)
        u_.assign(u)
        t += timestep
        hfile.write(h_, time=t)
        print(t)

    try:
      fig, axes = plt.subplots()
      plot(all_hs[-1], axes=axes)
    except Exception as e:
      warning("Cannot plot figure. Error msg: '%s'" % e)

    try:
      plt.show()
    except Exception as e:
      warning("Cannot show figure. Error msg: '%s'" % e)

def VP_EVP_test2():
    '''
    from Mehlmann and Korn, 2020
    Section 4.2
    VP+EVP test 2

    '''

    n = 30
    L = 1000000
    mesh = SquareMesh(n, n, L)

    V = VectorFunctionSpace(mesh, "CR", 1)
    W = FunctionSpace(mesh, "CR", 1)
    U = MixedFunctionSpace((V, W, W))

    # sea ice velocity
    u_ = Function(V, name="Velocity")
    u = Function(V, name="VelocityNext")

    # mean height of sea ice
    h_ = Function(W, name="Height")
    h = Function(W, name="HeightNext")

    # sea ice concentration
    A_ = Function(W,name="Concentration")
    A = Function(W,name="ConcentrationNext")

    #test functions
    v = TestFunction(V)
    w = TestFunction(W)
    q = TestFunction(W)


    x, y = SpatialCoordinate(mesh)

    # initial conditions

    u_.assign(0)

    h = Constant(1)

    A = x/L

    timestep = 1/n

    T = 100

    # defining the constants to be used in the sea ice momentum equation:

    # the sea ice density
    rho = Constant(900)

    # gravity
    g = Constant(10)

    # Coriolis parameter
    cor = Constant(1.46 * 10 ** (-4))

    # air density
    rho_a = Constant(1.3)

    # air drag coefficient
    C_a = Constant(1.2 * 10 ** (-3))

    # water density
    rho_w = Constant(1026)

    # water drag coefficient
    C_w = Constant(5.5 * 10 ** (-3))

    # ice strength parameter
    P_star = Constant(27.5 * 10 ** 3)

    # ice concentration parameter
    C = Constant(20)

    #  ellipse ratio
    e = Constant(2)

    # geostrophic wind

    geo_wind = as_vector([5 + (sin(2*pi*t/T)-3)*sin(2*pi*x/L)*sin(2*pi*y/L),5 + (sin(2*pi*t/T)-3)*sin(2*pi*y/L)*sin(2*pi*x/L)])

    # ocean current

    ocean_curr = as_vector([0.1*(2*y - L)/L,-0.1*(L - 2*x)/L])

    # mEVP rheology

    alpha = Constant(500)
    beta = Constant(500)

    # strain rate tensor, where grad(u) is the jacobian matrix of u
    ep_dot = 1 / 2 * (grad(u) + transpose(grad(u)))

    # deviatoric part of the strain rate tensor
    ep_dot_prime = ep_dot - 1 / 2 * tr(ep_dot) * Identity(2)

    # ice strength
    P = P_star * h * exp(-C * (1 - A))

    Delta_min = Constant(2 * 10 ** (-9))

    Delta = sqrt(Delta_min ** 2 + 2 * e ** (-2) * inner(ep_dot_prime, ep_dot_prime) + tr(ep_dot) ** 2)

    # viscosities
    zeta = P / (2 * Delta)
    eta = zeta * e ** (-2)

    # internal stress tensor
    sigma = 2 * eta * ep_dot + (zeta - eta) * tr(ep_dot) * Identity(2) - P / 2 * Identity(2)

    # solve the discretised sea ice momentum equation

    # constructing the discretised weak form

    # momentum equation
    Lm = (inner(rho * h * (u - u_) / timestep - rho * h * cor * as_vector([u[1] - ocean_curr[1], ocean_curr[0] - u[0]])
               + rho_a * C_a * dot(geo_wind, geo_wind) * geo_wind + rho_w * C_w * dot(u - ocean_curr, u - ocean_curr) * (
                           ocean_curr - u), v) +
         inner(sigma, grad(v))) * dx

    t = 0.0

    hfile = File('h.pvd')
    hfile.write(h_, time=t)
    all_hs = []
    end = T
    while (t <= end):
        solve(Lm == 0, u)
        u_.assign(u)
        t += timestep
        hfile.write(h_, time=t)
        print(t)

    try:
      fig, axes = plt.subplots()
      plot(all_hs[-1], axes=axes)
    except Exception as e:
      warning("Cannot plot figure. Error msg: '%s'" % e)

    try:
      plt.show()
    except Exception as e:
      warning("Cannot show figure. Error msg: '%s'" % e)



strain_rate_tensor()