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

from .. import exp
from ..utilities import memo
from ..operators.smoothness_operator import SmoothnessOperator
from .nonlinear_power_curvature import NonlinearPowerCurvature
from .response_operators import LinearizedPowerResponse
from ..minimization.energy import Energy


class NonlinearPowerEnergy(Energy):
    """The Energy of the power spectrum according to the critical filter.

    It describes the energy of the logarithmic amplitudes of the power spectrum
    of a Gaussian random field under reconstruction uncertainty with smoothness
    and inverse gamma prior. It is used to infer the correlation structure of a
    correlated signal.

    Parameters
    ----------
    position : Field,
        The current position of this energy.
    m : Field,
        The map whichs power spectrum has to be inferred
    D : EndomorphicOperator,
        The curvature of the Gaussian encoding the posterior covariance.
        If not specified, the map is assumed to be no reconstruction.
        default : None
    sigma : float
        The parameter of the smoothness prior.
        default : ??? None? ???????
    samples : integer
        Number of samples used for the estimation of the uncertainty
        corrections.
        default : 3
    """

    def __init__(self, position, d, N, m, D, FFT, Instrument, nonlinearity,
                 Projection, sigma=0., samples=3, sample_list=None,
                 inverter=None):
        super(NonlinearPowerEnergy, self).__init__(position)
        self.m = m
        self.D = D
        self.d = d
        self.N = N
        self.T = SmoothnessOperator(domain=self.position.domain[0],
                                    strength=sigma, logarithmic=True)
        self.FFT = FFT
        self.Instrument = Instrument
        self.nonlinearity = nonlinearity
        self.Projection = Projection
        self._sigma = sigma

        self.power = self.Projection.adjoint_times(exp(0.5*self.position))
        if sample_list is None:
            if samples is None or samples == 0:
                sample_list = [m]
            else:
                sample_list = [D.generate_posterior_sample() + m
                               for _ in range(samples)]
        self.sample_list = sample_list
        self.inverter = inverter
        self._value, self._gradient = self._value_and_grad()

    def at(self, position):
        return self.__class__(position, self.d, self.N, self.m, self.D,
                              self.FFT, self.Instrument, self.nonlinearity,
                              self.Projection, sigma=self._sigma,
                              samples=len(self.sample_list),
                              sample_list=self.sample_list,
                              inverter=self.inverter)

    def _value_and_grad(self):
        likelihood_gradient = None
        for sample in self.sample_list:
            residual = self.d - \
                self.Instrument(self.nonlinearity(
                    self.FFT.adjoint_times(self.power*sample)))
            lh = 0.5 * residual.vdot(self.N.inverse_times(residual))
            LinR = LinearizedPowerResponse(
                self.Instrument, self.nonlinearity, self.FFT, self.Projection,
                self.position, sample)
            grad = LinR.adjoint_times(self.N.inverse_times(residual))
            if likelihood_gradient is None:
                likelihood = lh
                likelihood_gradient = grad.copy()
            else:
                likelihood += lh
                likelihood_gradient += grad
        Tpos = self.T(self.position)
        likelihood *= 1./len(self.sample_list)
        likelihood += 0.5*self.position.vdot(Tpos)
        likelihood_gradient *= -1./len(self.sample_list)
        likelihood_gradient += Tpos
        return likelihood, likelihood_gradient

    @property
    def value(self):
        return self._value

    @property
    def gradient(self):
        return self._gradient

    @property
    @memo
    def curvature(self):
        return NonlinearPowerCurvature(
            self.position, self.FFT, self.Instrument, self.nonlinearity,
            self.Projection, self.N, self.T, self.sample_list,
            inverter=self.inverter)