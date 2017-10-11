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
# Copyright(C) 2013-2017 Max-Planck-Society
#
# NIFTy is being developed at the Max-Planck-Institut fuer Astrophysik
# and financially supported by the Studienstiftung des deutschen Volkes.

from builtins import object
from ..energies import QuadraticEnergy
from ..field import Field


class InvertibleOperatorMixin(object):
    """ Mixin class to invert implicit defined operators.

    To invert the application of a given implicitly defined operator on a
    field, this class gives the necessary functionality. Inheriting
    functionality from this class provides the derived class with the inverse
    to the given implicitly definied application of the operator on a field.
    (e.g. .inverse_times vs. .times and
    .adjoint_times vs. .adjoint_inverse_times)

    Parameters
    ----------
    inverter : Inverter
        An instance of an Inverter class.

    """

    def __init__(self, inverter, preconditioner=None,
                 forward_x0=None, backward_x0=None, *args, **kwargs):
        self.__inverter = inverter
        self._preconditioner = preconditioner
        self.__forward_x0 = forward_x0
        self.__backward_x0 = backward_x0
        super(InvertibleOperatorMixin, self).__init__(*args, **kwargs)

    def _times(self, x):
        if self.__forward_x0 is not None:
            x0 = self.__forward_x0
        else:
            x0 = Field.zeros(self.target, dtype=x.dtype)

        (result, convergence) = self.__inverter(QuadraticEnergy(
                                           A=self.inverse_times,
                                           b=x, position=x0),
                                           preconditioner=self._preconditioner)
        return result.position

    def _adjoint_times(self, x):
        if self.__backward_x0 is not None:
            x0 = self.__backward_x0
        else:
            x0 = Field.zeros(self.domain, dtype=x.dtype)

        (result, convergence) = self.__inverter(QuadraticEnergy(
                                           A=self.adjoint_inverse_times,
                                           b=x, position=x0),
                                           preconditioner=self._preconditioner)
        return result.position

    def _inverse_times(self, x):
        if self.__backward_x0 is not None:
            x0 = self.__backward_x0
        else:
            x0 = Field.zeros(self.domain, dtype=x.dtype)

        (result, convergence) = self.__inverter(QuadraticEnergy(
                                           A=self.times,
                                           b=x, position=x0),
                                           preconditioner=self._preconditioner)
        return result.position

    def _adjoint_inverse_times(self, x):
        if self.__forward_x0 is not None:
            x0 = self.__forward_x0
        else:
            x0 = Field.zeros(self.target, dtype=x.dtype)

        (result, convergence) = self.__inverter(QuadraticEnergy(
                                           A=self.adjoint_times,
                                           b=x, position=x0),
                                           preconditioner=self._preconditioner)
        return result.position
