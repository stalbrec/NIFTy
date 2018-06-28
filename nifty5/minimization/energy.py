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

import numpy as np
from ..field import Field
from ..multi import MultiField
from ..utilities import NiftyMetaBase, memo


class Energy(NiftyMetaBase()):
    """ Provides the functional used by minimization schemes.

   The Energy object is an implementation of a scalar function including its
   gradient and curvature at some position.

    Parameters
    ----------
    position : Field
        The input parameter of the scalar function.

    Notes
    -----
    An instance of the Energy class is defined at a certain location. If one
    is interested in the value, gradient or curvature of the abstract energy
    functional one has to 'jump' to the new position using the `at` method.
    This method returns a new energy instance residing at the new position. By
    this approach, intermediate results from computing e.g. the gradient can
    safely be reused for e.g. the value or the curvature.

    Memorizing the evaluations of some quantities (using the memo decorator)
    minimizes the computational effort for multiple calls.

    See Also
    --------
    memo

    """

    def __init__(self, position):
        super(Energy, self).__init__()
        self._position = position.lock()

    def at(self, position):
        """ Returns a new Energy object, initialized at `position`.

        Parameters
        ----------
        position : Field
            Location in parameter space for the new Energy object.

        Returns
        -------
        Energy
            Energy object at new position.
        """
        return self.__class__(position)

    @property
    def position(self):
        """
        Field : selected location in parameter space.

        The Field location in parameter space where value, gradient and
        curvature are evaluated.
        """
        return self._position

    @property
    def value(self):
        """
        float : value of the functional.

            The value of the energy functional at given `position`.
        """
        raise NotImplementedError

    @property
    def gradient(self):
        """
        Field : The gradient at given `position`.
        """
        raise NotImplementedError

    @property
    @memo
    def gradient_norm(self):
        """
        float : L2-norm of the gradient at given `position`.
        """
        return self.gradient.norm()

    @property
    def curvature(self):
        """
        LinearOperator : implicitly defined curvature.
            A positive semi-definite operator or function describing the
            curvature of the potential at the given `position`.
        """
        raise NotImplementedError

    def longest_step(self, dir):
        """Returns the longest allowed step size along `dir`

        Parameters
        ----------
        dir : Field
            the search direction

        Returns
        -------
        float or None
            the longest allowed step when starting from `self.position` along
            `dir`. If None, the step size is not limited.
        """
        return None

    def __mul__(self, factor):
        from .energy_sum import EnergySum
        if not isinstance(factor, (float, int)):
            raise TypeError("Factor must be a real-valued scalar")
        return EnergySum.make([self], [factor])

    def __rmul__(self, factor):
        return self.__mul__(factor)

    def __add__(self, other):
        from .energy_sum import EnergySum
        if not isinstance(other, Energy):
            raise TypeError("can only add Energies to Energies")
        return EnergySum.make([self, other])

    def __sub__(self, other):
        from .energy_sum import EnergySum
        if not isinstance(other, Energy):
            raise TypeError("can only subtract Energies from Energies")
        return EnergySum.make([self, other], [1., -1.])

    def __neg__(self):
        from .energy_sum import EnergySum
        return EnergySum.make([self], [-1.])
