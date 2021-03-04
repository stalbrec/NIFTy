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
# Copyright(C) 2013-2021 Max-Planck-Society
#
# NIFTy is being developed at the Max-Planck-Institut fuer Astrophysik.

import numpy as np

from ..domain_tuple import DomainTuple
from ..domains.unstructured_domain import UnstructuredDomain
from ..sugar import makeField
from .linear_operator import LinearOperator


class Multifield2Vector(LinearOperator):
    """Flatten a MultiField and return a Field with unstructred domain and the
    same number of degrees of freedom.

    FIXME
    """

    def __init__(self, domain):
        self._dof = domain.size
        self._domain = domain
        self._target = DomainTuple.make(UnstructuredDomain(self._dof))
        self._capability = self.TIMES | self.ADJOINT_TIMES

    def apply(self, x, mode):
        self._check_input(x, mode)
        x = x.val
        ii = 0
        if mode == self.TIMES:
            res = np.empty(self.target.shape)
            for key in self.domain.keys():
                arr = x[key].flatten()
                res[ii:ii + arr.size] = arr
                ii += arr.size
        else:
            res = {}
            for key in self.domain.keys():
                n = self.domain[key].size
                shp = self.domain[key].shape
                res[key] = x[ii:ii + n].reshape(shp)
                ii += n
        return makeField(self._tgt(mode), res)
