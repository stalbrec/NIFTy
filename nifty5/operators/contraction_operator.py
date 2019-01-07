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

import numpy as np

from .. import utilities
from ..compat import *
from ..domain_tuple import DomainTuple
from ..field import Field
from .linear_operator import LinearOperator


class ContractionOperator(LinearOperator):
    """A linear operator which sums up fields into the direction of subspaces.

    This ContractionOperator sums up a field with is defined on a DomainTuple
    to a DomainTuple which contains the former as a subset.

    Parameters
    ----------
    domain : Domain, tuple of Domain or DomainTuple
    spaces : int or tuple of int
        The elements of "domain" which are contracted.
    weight : int, default=0
        if nonzero, the fields living on self.domain are weighted with the
        specified power.
    """

    def __init__(self, domain, spaces, weight=0):
        self._domain = DomainTuple.make(domain)
        self._spaces = utilities.parse_spaces(spaces, len(self._domain))
        self._target = [
            dom for i, dom in enumerate(self._domain) if i not in self._spaces
        ]
        self._target = DomainTuple.make(self._target)
        self._weight = weight
        self._capability = self.TIMES | self.ADJOINT_TIMES

    def apply(self, x, mode):
        self._check_input(x, mode)
        if mode == self.ADJOINT_TIMES:
            ldat = x.to_global_data() if 0 in self._spaces else x.local_data
            shp = []
            for i, dom in enumerate(self._domain):
                tmp = dom.shape if i > 0 else dom.local_shape
                shp += tmp if i not in self._spaces else (1,)*len(dom.shape)
            ldat = np.broadcast_to(ldat.reshape(shp), self._domain.local_shape)
            res = Field.from_local_data(self._domain, ldat)
            if self._weight != 0:
                res = res.weight(self._weight, spaces=self._spaces)
            return res
        else:
            if self._weight != 0:
                x = x.weight(self._weight, spaces=self._spaces)
            res = x.sum(self._spaces)
            return res if isinstance(res, Field) else Field.scalar(res)
