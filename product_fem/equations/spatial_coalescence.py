from .base import Equation
from product_fem import ProductDirichletBC, ProductForm, Function, Control, to_Function
from fenics import as_matrix, TrialFunction, TestFunction, dx, Dx, inner, grad, div, exp
import numpy as np

            
# sig^2/2 Laplacian(u) + mu•grad(u) = f
# parameters: sig (float), mu (array)
class HittingTimes1D(Equation):
    def __init__(self, W, u_bdy=1., epsilon=1e-2):
        mu, sig = self._init_control(W)
        u, v = TrialFunction(W.V), TestFunction(W.V)
        
        # left hand side forms 
        Ax_forms = [-0.5 * u.dx(0) * Dx(sig**2 * v, 0) * dx,
                    u * v * dx,
                    mu * u.dx(0) * v * dx,
                    u * v * dx]
        Ay_forms = [u * v * dx,
                    -0.5 * u.dx(0) * Dx(sig**2 * v,0) * dx,
                    u * v * dx,
                    mu * u.dx(0) * v * dx]
        
        # right hand side forms 
        bx_forms = [-1. * v * dx]
        by_forms = [1. * v * dx]
        
        # product forms and control
        lhs = ProductForm(Ax_forms, Ay_forms)
        rhs = ProductForm(bx_forms, by_forms)
        control = Control([mu, sig])
        
        # boundary is epsilon nbhd around diagonal x=y
        on_product_boundary = lambda x, y: np.linalg.norm(x - y) <= epsilon
        bc = ProductDirichletBC(W, u_bdy, on_product_boundary)
        
        super().__init__(lhs, rhs, control, bc)
        
    def _init_control(self, W):
        # default control here is mu(x)=0 and sig(x)=0.25
        mu = Function(W.V, name='mu')
        sig = Function(W.V, name='sigma')
        sig.vector()[:] = 0.25
        return mu, sig
        
        
# sig^2/2 Laplacian(u) + mu•grad(u) = -1
# parameters: mu (mean vector), sig (covariance matrix)
class HittingTimes2D(Equation):
    
    def __init__(self, W, u_bdy=1., epsilon=1e-2):
        mu, sig = self._init_control(W)
        # to enforce SPD on sigma we use a log-Cholesky factorization
        L = as_matrix([[exp(sig[0]), sig[2]],[0, exp(sig[1])]])
        sigma = L.T * L
        
        u, v = TrialFunction(W.V), TestFunction(W.V)
        
        # left hand side forms
        Ax_forms = [-0.5 * inner(grad(u), div(sigma * v)) * dx,
                    u * v * dx,
                    inner(mu, grad(u)) * v * dx,
                    u * v * dx]
        Ay_forms = [u * v * dx,
                    -0.5 * inner(grad(u), div(sigma * v)) * dx,
                    u * v * dx,
                    inner(mu, grad(u)) * v * dx]
        
        # right hand side forms
        bx_forms = [1. * v * dx]
        by_forms = [-1. * v * dx]
        
        # product forms and control
        lhs = ProductForm(Ax_forms, Ay_forms)
        rhs = ProductForm(bx_forms, by_forms)
        control = Control([mu, sig])
        
        # boundary is epsilon nbhd around diagonal x=y
        on_product_boundary = lambda x, y: np.linalg.norm(x - y) <= epsilon
        bc = ProductDirichletBC(W, u_bdy, on_product_boundary)
        
        super().__init__(lhs, rhs, control, bc)
    
    def _init_control(self, W):
        mu = Function(W.V, dim=2, name='mu')
        sig = Function(W.V, dim=3, name='sig')
        return mu, sig
        

def HittingTimes(W, u_bdy, epsilon):
    """
    TODO: change this CoalescenceTimes
    
    The equation class for the system of equations (TODO: define $L$ and use this instead)
    .. math::
    
        \frac{\sigma(x)^2}{2} \Delta_x u(x, y) + \mu(x) \cdot \nabla_x u(x, y) &= -1 \\
        \frac{\sigma(y)^2}{2} \Delta_y u(x, y) + \mu(y) \cdot \nabla_y u(x, y) &= -1
    
    if both $x$ and $y$ are in $\Omega$,
    a domain in $\mathbb{R}$ or $\mathbb{R}^2$
    specified by ``W``, and boundary conditions
    .. math::
        \text{ and } u(x, y) = u_b(x, y) \text{ if } |x - y| \le \epsilon
        
    where $u$ is a function on $\Omega \times \Omega$,
    $\mu$ is a function on $\Omega$,
    and $u_b$ is a function on $\Omega \times \Omega$.
    Furthermore, there are reflecting (i.e., Dirichlet)
    boundary conditions on $\delta \Omega \times \Omega \cup \Omega \times \delta \Omega$.
    
    The parameters are {math}`\sigma \in \mathbb{R}_+$ and $\mu : [0,1] \to \mathbb{R}`,
    and so the ``control`` of this equation is of the form ``mu, sigma``.
    The default {math}`\mu` is {math}`\mu(x) = 0`.
    In one dimension, sigma is a single number and defaults to {math}`\sigma = 1/4`.
    In two dimensions, the operator (TODO FIXUP) is
    
    .. math::
    
        \sum_{ij} \Sigma_{ij} \partial_{x_i} \partial_{x_j} u(x, y)
    
    :param ProductFunctionSpace W: The product function space in which $u$ lives.
    :param u_bdy: The values for $u$ along the "diagonal"; either a float or a callable.
    :param float epsilon: The width of the "diagonal" boundary affected by ``u_bdy``.
    """
    gdim = W.V.ufl_domain().geometric_dimension()
    if gdim==1:
        return HittingTimes1D(W, u_bdy, epsilon)
    elif gdim==2:
        return HittingTimes2D(W, u_bdy, epsilon)   