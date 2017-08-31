from ...energies.energy import Energy
from ...energies.memoization import memo
from . import WienerFilterCurvature


class WienerFilterEnergy(Energy):
    """The Energy for the Wiener filter.

    It covers the case of linear measurement with
    Gaussian noise and Gaussian signal prior with known covariance.

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

    def __init__(self, position, d, R, N, S, old_curvature=None):
        super(WienerFilterEnergy, self).__init__(position=position)
        self.d = d
        self.R = R
        self.N = N
        self.S = S
        self._curvature = old_curvature

    def at(self, position):
        return self.__class__(position=position, d=self.d, R=self.R, N=self.N,
                              S=self.S, old_curvature=self.curvature)

    @property
    @memo
    def value(self):
        return 0.5*self.position.vdot(self._Dx) - self._j.vdot(self.position)

    @property
    @memo
    def gradient(self):
        return self._Dx - self._j

    @property
    def curvature(self):
        if self._curvature is None:
            self._curvature = WienerFilterCurvature(R=self.R,
                                                    N=self.N,
                                                    S=self.S)
        return self._curvature

    @property
    @memo
    def _Dx(self):
        return self.curvature(self.position)

    @property
    @memo
    def _j(self):
        return self.R.adjoint_times(self.N.inverse_times(self.d))