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

from ..domain_tuple import DomainTuple
from ..domains.unstructured_domain import UnstructuredDomain
from ..field import Field
from .linear_operator import LinearOperator


class MaskOperator(LinearOperator):
    def __init__(self, mask):
        if not isinstance(mask, Field):
            raise TypeError

        self._domain = DomainTuple.make(mask.domain)
        self._mask = np.logical_not(mask.to_global_data())
        self._target = DomainTuple.make(UnstructuredDomain(self._mask.sum()))

    def data_indices(self):
        return np.indices(self.domain.shape).transpose((1, 2, 0))[self._mask]

    def apply(self, x, mode):
        self._check_input(x, mode)
        if mode == self.TIMES:
            res = x.to_global_data()[self._mask]
            return Field(self.target, res)
        x = x.to_global_data()
        res = np.empty(self.domain.shape, x.dtype)
        res[self._mask] = x
        res[~self._mask] = 0
        return Field(self.domain, res)

    @property
    def capability(self):
        return self.TIMES | self.ADJOINT_TIMES

    @property
    def domain(self):
        return self._domain

    @property
    def target(self):
        return self._target
