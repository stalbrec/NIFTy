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

from __future__ import division
from builtins import range
import numpy as np

from ...field import Field
from ..endomorphic_operator import EndomorphicOperator


class DiagonalOperator(EndomorphicOperator):
    """ NIFTY class for diagonal operators.

    The NIFTY DiagonalOperator class is a subclass derived from the
    EndomorphicOperator. It multiplies an input field pixel-wise with its
    diagonal.


    Parameters
    ----------
    domain : tuple of DomainObjects, i.e. Spaces and FieldTypes
        The domain on which the Operator's input Field lives.
    diagonal : {scalar, list, array, Field}
        The diagonal entries of the operator.
    bare : boolean
        Indicates whether the input for the diagonal is bare or not
        (default: False).
    copy : boolean
        Internal copy of the diagonal (default: True)
    default_spaces : tuple of ints *optional*
        Defines on which space(s) of a given field the Operator acts by
        default (default: None)

    Attributes
    ----------
    domain : tuple of DomainObjects, i.e. Spaces and FieldTypes
        The domain on which the Operator's input Field lives.
    target : tuple of DomainObjects, i.e. Spaces and FieldTypes
        The domain in which the outcome of the operator lives. As the Operator
        is endomorphic this is the same as its domain.
    unitary : boolean
        Indicates whether the Operator is unitary or not.
    self_adjoint : boolean
        Indicates whether the operator is self_adjoint or not.

    Raises
    ------

    Notes
    -----
    The ambiguity of bare or non-bare diagonal entries is based on the choice
    of a matrix representation of the operator in question. The naive choice
    of absorbing the volume weights into the matrix leads to a matrix-vector
    calculus with the non-bare entries which seems intuitive, though.
    The choice of keeping matrix entries and volume weights separate
    deals with the bare entries that allow for correct interpretation
    of the matrix entries; e.g., as variance in case of an covariance operator.

    See Also
    --------
    EndomorphicOperator

    """

    # ---Overwritten properties and methods---

    def __init__(self, domain=(), diagonal=None, bare=False, copy=True,
                 default_spaces=None):
        super(DiagonalOperator, self).__init__(default_spaces)

        self._domain = self._parse_domain(domain)

        self._self_adjoint = None
        self._unitary = None
        self.set_diagonal(diagonal=diagonal, bare=bare, copy=copy)

    def _times(self, x, spaces):
        return self._times_helper(x, spaces, operation=lambda z: z.__mul__)

    def _adjoint_times(self, x, spaces):
        return self._times_helper(x, spaces,
                                  operation=lambda z: z.adjoint().__mul__)

    def _inverse_times(self, x, spaces):
        return self._times_helper(x, spaces,
                                  operation=lambda z: z.__rtruediv__)

    def _adjoint_inverse_times(self, x, spaces):
        return self._times_helper(x, spaces,
                                  operation=lambda z: z.adjoint().__rtruediv__)

    def diagonal(self, bare=False, copy=True):
        """ Returns the diagonal of the Operator.

        Parameters
        ----------
        bare : boolean
            Whether the returned Field values should be bare or not.
        copy : boolean
            Whether the returned Field should be copied or not.

        Returns
        -------
        out : Field
            The diagonal of the Operator.

        """
        if bare:
            return self._diagonal.weight(power=-1)
        elif copy:
            return self._diagonal.copy()
        else:
            return self._diagonal

    def inverse_diagonal(self, bare=False):
        """ Returns the inverse-diagonal of the operator.

        Parameters
        ----------
        bare : boolean
            Whether the returned Field values should be bare or not.

        Returns
        -------
        out : Field
            The inverse of the diagonal of the Operator.

        """
        return 1./self.diagonal(bare=bare, copy=False)

    # ---Mandatory properties and methods---

    @property
    def domain(self):
        return self._domain

    @property
    def self_adjoint(self):
        if self._self_adjoint is None:
            self._self_adjoint = (self._diagonal.val.imag == 0).all()
        return self._self_adjoint

    @property
    def unitary(self):
        if self._unitary is None:
            self._unitary = (self._diagonal.val *
                             self._diagonal.val.conjugate() == 1).all()
        return self._unitary

    # ---Added properties and methods---

    def set_diagonal(self, diagonal, bare=False, copy=True):
        """ Sets the diagonal of the Operator.

        Parameters
        ----------
        diagonal : {scalar, list, array, Field}
            The diagonal entries of the operator.
        bare : boolean
            Indicates whether the input for the diagonal is bare or not
            (default: False).
        copy : boolean
            Specifies if a copy of the input shall be made (default: True).

        """

        # use the casting functionality from Field to process `diagonal`
        f = Field(domain=self.domain, val=diagonal, copy=copy)

        # weight if the given values were `bare` is True
        # do inverse weightening if the other way around
        if bare:
            # If `copy` is True, we won't change external data by weightening
            # Otherwise, inplace weightening would change the external field
            f.weight(inplace=copy)

        # Reset the self_adjoint property:
        self._self_adjoint = None

        # Reset the unitarity property
        self._unitary = None

        # store the diagonal-field
        self._diagonal = f

    def _times_helper(self, x, spaces, operation):
        # if the domain matches directly
        # -> multiply the fields directly
        if x.domain == self.domain:
            # here the actual multiplication takes place
            return operation(self.diagonal(copy=False))(x)

        active_axes = []
        if spaces is None:
            active_axes = list(range(len(x.shape)))
        else:
            for space_index in spaces:
                active_axes += x.domain_axes[space_index]

        local_diagonal = self._diagonal.val

        reshaper = [x.val.shape[i] if i in active_axes else 1
                    for i in range(len(x.shape))]
        reshaped_local_diagonal = np.reshape(local_diagonal, reshaper)

        # here the actual multiplication takes place
        local_result = operation(reshaped_local_diagonal)(x.val)

        return Field(x.domain, val=local_result)