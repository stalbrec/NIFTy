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
# Copyright(C) 2013-2018 Max-Planck-Society
#
# NIFTy is being developed at the Max-Planck-Institut fuer Astrophysik
# and financially supported by the Studienstiftung des deutschen Volkes.

from __future__ import absolute_import, division, print_function

from ..compat import *
from ..minimization.energy_adapter import EnergyAdapter
from ..multi_domain import MultiDomain
from ..multi_field import MultiField
from ..operators.distributors import PowerDistributor
from ..operators.energy_operators import Hamiltonian, InverseGammaLikelihood
from ..operators.scaling_operator import ScalingOperator
from ..operators.simple_linear_operators import FieldAdapter


def make_adjust_variances(a,
                          xi,
                          position,
                          samples=[],
                          scaling=None,
                          ic_samp=None):
    """ Creates a Hamiltonian for constant likelihood optimizations.

    Constructs a Hamiltonian to solve constant likelihood optimizations of the
    form phi = a * xi under the constraint that phi remains constant.

    Parameters
    ----------
    a : Operator
        Operator which gives the amplitude when evaluated at a position
    xi : Operator
        Operator which gives the excitation when evaluated at a position
    postion : Field, MultiField
        Position of the whole problem
    samples : Field, MultiField
        Residual samples of the whole problem
    scaling : Float
        Optional rescaling of the Likelihood
    ic_samp : Controller
        Iteration Controller for Hamiltonian

    Returns
    -------
    Hamiltonian
        A Hamiltonian that can be used for further minimization
    """

    d = a*xi
    d = (d.conjugate()*d).real
    n = len(samples)
    if n > 0:
        d_eval = 0.
        for i in range(n):
            d_eval = d_eval + d(position + samples[i])
        d_eval = d_eval/n
    else:
        d_eval = d(position)

    x = (a.conjugate()*a).real
    if scaling is not None:
        x = ScalingOperator(scaling, x.target)(x)

    return Hamiltonian(InverseGammaLikelihood(d_eval)(x), ic_samp=ic_samp)


def do_adjust_variances(position,
                        amplitude_model,
                        minimizer,
                        xi_key='xi',
                        samples=[]):
    h_space = position[xi_key].domain[0]
    pd = PowerDistributor(h_space, amplitude_model.target[0])
    a = pd(amplitude_model)
    xi = FieldAdapter(MultiDomain.make({xi_key: h_space}), xi_key)

    axi_domain = MultiDomain.union([a.domain, xi.domain])
    ham = make_adjust_variances(
        a, xi, position.extract(axi_domain), samples=samples)
    a_pos = position.extract(a.domain)

    # Minimize
    # FIXME Try also KL here
    e = EnergyAdapter(a_pos, ham, constants=[], want_metric=True)
    e, _ = minimizer(e)

    # Update position
    s_h_old = (a*xi)(position.extract(axi_domain))

    position = position.to_dict()
    position['xi'] = s_h_old/a(e.position)
    position = MultiField.from_dict(position)
    position = MultiField.union([position, e.position])

    s_h_new = (a*xi)(position.extract(axi_domain))

    import numpy as np
    # TODO Move this into the tests
    np.testing.assert_allclose(s_h_new.to_global_data(),
                               s_h_old.to_global_data())
    return position
