# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# Copyright(C) 2013-2019 Max-Planck-Society
#
# NIFTy is being developed at the Max-Planck-Institut fuer Astrophysik.

from unittest import SkipTest

import numpy as np
import pytest
from numpy.testing import assert_allclose, assert_equal

import nifty6 as ift

pmp = pytest.mark.parametrize
IC = ift.GradientNormController(tol_abs_gradnorm=1e-5, iteration_limit=1000)

spaces = [ift.RGSpace([1024], distances=0.123), ift.HPSpace(32)]

minimizers = [
    'ift.VL_BFGS(IC)',
    'ift.NonlinearCG(IC, "Polak-Ribiere")',
    # 'ift.NonlinearCG(IC, "Hestenes-Stiefel"),
    'ift.NonlinearCG(IC, "Fletcher-Reeves")',
    'ift.NonlinearCG(IC, "5.49")',
    'ift.L_BFGS_B(ftol=1e-10, gtol=1e-5, maxiter=1000)',
    'ift.L_BFGS(IC)',
    'ift.NewtonCG(IC)'
]

newton_minimizers = ['ift.RelaxedNewton(IC)']
quadratic_only_minimizers = [
    'ift.ConjugateGradient(IC)',
    'ift.minimization.scipy_minimizer._ScipyCG(tol=1e-5, maxiter=300)'
]
slow_minimizers = ['ift.SteepestDescent(IC)']


@pmp('minimizer', minimizers + newton_minimizers + quadratic_only_minimizers +
     slow_minimizers)
@pmp('space', spaces)
def test_quadratic_minimization(minimizer, space):
    np.random.seed(42)
    starting_point = ift.Field.from_random('normal', domain=space)*10
    covariance_diagonal = ift.Field.from_random('uniform', domain=space) + 0.5
    covariance = ift.DiagonalOperator(covariance_diagonal)
    required_result = ift.full(space, 1.)

    try:
        minimizer = eval(minimizer)
        energy = ift.QuadraticEnergy(
            A=covariance, b=required_result, position=starting_point)

        (energy, convergence) = minimizer(energy)
    except NotImplementedError:
        raise SkipTest

    assert_equal(convergence, IC.CONVERGED)
    assert_allclose(
        energy.position.local_data,
        1./covariance_diagonal.local_data,
        rtol=1e-3,
        atol=1e-3)


@pmp('space', spaces)
def test_WF_curvature(space):
    np.random.seed(42)
    required_result = ift.full(space, 1.)

    s = ift.Field.from_random('uniform', domain=space) + 0.5
    S = ift.DiagonalOperator(s)
    r = ift.Field.from_random('uniform', domain=space)
    R = ift.DiagonalOperator(r)
    n = ift.Field.from_random('uniform', domain=space) + 0.5
    N = ift.DiagonalOperator(n)
    all_diag = 1./s + r**2/n
    curv = ift.WienerFilterCurvature(R, N, S, iteration_controller=IC,
                                     iteration_controller_sampling=IC)
    m = curv.inverse(required_result)
    assert_allclose(
        m.local_data,
        1./all_diag.local_data,
        rtol=1e-3,
        atol=1e-3)
    curv.draw_sample()
    curv.draw_sample(from_inverse=True)

    if len(space.shape) == 1:
        R = ift.ValueInserter(space, [0])
        n = ift.from_random('uniform', R.domain) + 0.5
        N = ift.DiagonalOperator(n)
        all_diag = 1./s + R(1/n)
        curv = ift.WienerFilterCurvature(R.adjoint, N, S,
                                         iteration_controller=IC,
                                         iteration_controller_sampling=IC)
        m = curv.inverse(required_result)
        assert_allclose(
            m.local_data,
            1./all_diag.local_data,
            rtol=1e-3,
            atol=1e-3)
        curv.draw_sample()
        curv.draw_sample(from_inverse=True)


@pmp('minimizer', minimizers + newton_minimizers)
def test_rosenbrock(minimizer):
    try:
        from scipy.optimize import rosen, rosen_der, rosen_hess_prod
    except ImportError:
        raise SkipTest
    np.random.seed(42)
    space = ift.DomainTuple.make(ift.UnstructuredDomain((2,)))
    starting_point = ift.Field.from_random('normal', domain=space)*10

    class RBEnergy(ift.Energy):
        def __init__(self, position):
            super(RBEnergy, self).__init__(position)

        @property
        def value(self):
            return rosen(self._position.to_global_data_rw())

        @property
        def gradient(self):
            inp = self._position.to_global_data_rw()
            out = ift.Field.from_global_data(space, rosen_der(inp))
            return out

        @property
        def metric(self):
            class RBCurv(ift.EndomorphicOperator):
                def __init__(self, loc):
                    self._loc = loc.to_global_data_rw()
                    self._capability = self.TIMES
                    self._domain = space

                def apply(self, x, mode):
                    self._check_input(x, mode)
                    inp = x.to_global_data_rw()
                    out = ift.Field.from_global_data(
                        space, rosen_hess_prod(self._loc.copy(), inp))
                    return out

            t1 = ift.GradientNormController(
                tol_abs_gradnorm=1e-5, iteration_limit=1000)
            return ift.InversionEnabler(RBCurv(self._position), t1)

        def apply_metric(self, x):
            inp = x.to_global_data_rw()
            pos = self._position.to_global_data_rw()
            return ift.Field.from_global_data(space, rosen_hess_prod(pos, inp))

    try:
        minimizer = eval(minimizer)
        energy = RBEnergy(position=starting_point)

        (energy, convergence) = minimizer(energy)
    except NotImplementedError:
        raise SkipTest

    assert_equal(convergence, IC.CONVERGED)
    assert_allclose(energy.position.local_data, 1., rtol=1e-3, atol=1e-3)


@pmp('minimizer', minimizers + slow_minimizers)
def test_gauss(minimizer):
    space = ift.UnstructuredDomain((1,))
    starting_point = ift.Field.full(space, 3.)

    class ExpEnergy(ift.Energy):
        def __init__(self, position):
            super(ExpEnergy, self).__init__(position)

        @property
        def value(self):
            x = self.position.to_global_data()[0]
            return -np.exp(-(x**2))

        @property
        def gradient(self):
            x = self.position.to_global_data()[0]
            return ift.Field.full(self.position.domain, 2*x*np.exp(-(x**2)))

        def apply_metric(self, x):
            p = self.position.to_global_data()[0]
            v = (2 - 4*p*p)*np.exp(-p**2)
            return ift.DiagonalOperator(
                ift.Field.full(self.position.domain, v))(x)

    try:
        minimizer = eval(minimizer)
        energy = ExpEnergy(position=starting_point)

        (energy, convergence) = minimizer(energy)
    except NotImplementedError:
        raise SkipTest

    assert_equal(convergence, IC.CONVERGED)
    assert_allclose(energy.position.local_data, 0., atol=1e-3)


@pmp('minimizer', minimizers + newton_minimizers + slow_minimizers)
def test_cosh(minimizer):
    space = ift.UnstructuredDomain((1,))
    starting_point = ift.Field.full(space, 3.)

    class CoshEnergy(ift.Energy):
        def __init__(self, position):
            super(CoshEnergy, self).__init__(position)

        @property
        def value(self):
            x = self.position.to_global_data()[0]
            return np.cosh(x)

        @property
        def gradient(self):
            x = self.position.to_global_data()[0]
            return ift.Field.full(self.position.domain, np.sinh(x))

        @property
        def metric(self):
            x = self.position.to_global_data()[0]
            v = np.cosh(x)
            return ift.DiagonalOperator(
                ift.Field.full(self.position.domain, v))

        def apply_metric(self, x):
            p = self.position.to_global_data()[0]
            v = np.cosh(p)
            return ift.DiagonalOperator(
                ift.Field.full(self.position.domain, v))(x)

    try:
        minimizer = eval(minimizer)
        energy = CoshEnergy(position=starting_point)

        (energy, convergence) = minimizer(energy)
    except NotImplementedError:
        raise SkipTest

    assert_equal(convergence, IC.CONVERGED)
    assert_allclose(energy.position.local_data, 0., atol=1e-3)
