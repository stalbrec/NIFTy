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

import numpy as np
from .slicing_transformation import SlicingTransformation
from . import lm_transformation_helper
import pyHealpix


class LMHPTransformation(SlicingTransformation):

    def __init__(self, domain, codomain=None):
        super(LMHPTransformation, self).__init__(domain, codomain)

    @property
    def unitary(self):
        return False

    def _transformation_of_slice(self, inp):
        nside = self.codomain.nside
        lmax = self.domain.lmax
        mmax = lmax

        if issubclass(inp.dtype.type, np.complexfloating):
            rr = lm_transformation_helper.buildLm(inp.real, lmax=lmax)
            ri = lm_transformation_helper.buildLm(inp.imag, lmax=lmax)
            rr = pyHealpix.alm2map(rr, lmax, mmax, nside)
            ri = pyHealpix.alm2map(ri, lmax, mmax, nside)
            return rr + 1j*ri

        else:
            rr = lm_transformation_helper.buildLm(inp, lmax=lmax)
            return pyHealpix.alm2map(rr, lmax, mmax, nside)