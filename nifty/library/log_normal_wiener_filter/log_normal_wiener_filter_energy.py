from nifty.energies.energy import Energy
from nifty.energies.memoization import memo
from nifty.library.wiener_filter import WienerFilterCurvature
from nifty.basic_arithmetics import exp

class LogNormalWienerFilterEnergy(Energy):
    """The Energy for the log-normal Wiener filter.

    It covers the case of linear measurement with
    Gaussian noise and Gaussain signal prior with known covariance.

    Parameters
    ----------
    position: Field,
        The current position.
    d : Field,
        the data.
    R : Operator,
        The response operator, describtion of the measurement process.
    N : EndomorphicOperator,
        The noise covariance in data space.
    S : EndomorphicOperator,
        The prior signal covariance in harmonic space.
    """

    def __init__(self, position, d, R, N, S):
        super(WienerFilterEnergy, self).__init__(position=position)
        self.d = d
        self.R = R
        self.N = N
        self.S = S

    def at(self, position):
        return self.__class__(position=position, d=self.d, R=self.R, N=self.N,
                              S=self.S)

    @property
    @memo
    def value(self):
        return (0.5*self.position.vdot(self._Sx) -
                self._Rexpxd.vdot(self._NRexpxd))

    @property
    @memo
    def gradient(self):
        return self._Sx + self._expx * self.R.adjoint_times(self._NRexpxd)

    @property
    @memo
    def curvature(self):
        return WienerFilterCurvature(R=self.R, N=self.N, S=self.S)

    @property
    @memo
    def _expx(self):
        return exp(self.position)

    @property
    @memo
    def _Rexpxd(self):
        return self.R(self._expx) - self.d

    @property
    @memo
    def _NRexpxd(self):
        return self.N.inverse_times(self._Rexpxd)

    @property
    @memo
    def _Sx(self):
        return self.S.inverse_times(self.position)
