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
# Copyright(C) 2019 Max-Planck-Society
#
# NIFTy is being developed at the Max-Planck-Institut fuer Astrophysik.

import numpy as np

from ..domain_tuple import DomainTuple
from ..domains.rg_space import RGSpace
from ..domains.unstructured_domain import UnstructuredDomain
from ..operators.linear_operator import LinearOperator
from ..sugar import makeDomain, makeField


class Gridder(LinearOperator):
    def __init__(self, target, uv, eps=2e-10, nthreads=1):
        self._capability = self.TIMES | self.ADJOINT_TIMES
        self._target = makeDomain(target)
        if (len(self._target) != 1 or not isinstance(self._target[0], RGSpace)
                or not len(self._target.shape) == 2):
            raise ValueError("need target with exactly one 2D RGSpace")
        if uv.ndim != 2:
            raise ValueError("uv must be a 2D array")
        if uv.shape[1] != 2:
            raise ValueError("second dimension of uv must have length 2")
        self._domain = DomainTuple.make(
            UnstructuredDomain((uv.shape[0])))
        # wasteful hack to adjust to shape required by ducc0.wgridder
        self._uvw = np.empty((uv.shape[0], 3), dtype=np.float64)
        self._uvw[:, 0:2] = uv
        self._uvw[:, 2] = 0.
        self._eps = float(eps)
        self._nthreads = int(nthreads)


    def apply(self, x, mode):
        self._check_input(x, mode)
        speedOfLight = 299792458.
        freq = np.array([speedOfLight])
        x = x.val
        nxdirty, nydirty = self._target[0].shape
        dstx, dsty = self._target[0].distances
        from ducc0.wgridder import ms2dirty, dirty2ms
        if mode == self.TIMES:
            res = ms2dirty(self._uvw, freq, x.reshape((-1,1)), None, nxdirty,
                           nydirty, dstx, dsty, 0, 0,
                           self._eps, False, self._nthreads, 0)
        else:
            res = dirty2ms(self._uvw, freq, x, None, dstx, dsty, 0, 0,
                           self._eps, False, self._nthreads, 0)
            res = res.reshape((-1,))
        return makeField(self._tgt(mode), res)