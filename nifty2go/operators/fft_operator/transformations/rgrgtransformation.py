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
import numpy as np
from .transformation import Transformation
from .rg_transforms import SerialFFT


class RGRGTransformation(Transformation):

    # ---Overwritten properties and methods---

    def __init__(self, domain, codomain=None):
        super(RGRGTransformation, self).__init__(domain, codomain)
        self._transform = SerialFFT(self.domain, self.codomain)

    # ---Mandatory properties and methods---

    @property
    def unitary(self):
        return True

    def transform(self, val, axes=None):
        """
        RG -> RG transform method.

        Parameters
        ----------
        val : np.ndarray or distributed_data_object
            The value array which is to be transformed

        axes : None or tuple
            The axes along which the transformation should take place

        """
        if self._transform.codomain.harmonic:
            # correct for forward fft.
            # naively one would set power to 0.5 here in order to
            # apply effectively a factor of 1/sqrt(N) to the field.
            # BUT: the pixel volumes of the domain and codomain are different.
            # Hence, in order to produce the same scalar product, power===1.
            val = self._transform.domain.weight(val, power=1, axes=axes)

        # Perform the transformation
        if issubclass(val.dtype.type, np.complexfloating):
            Tval_real = self._transform.transform(val.real, axes)
            Tval_imag = self._transform.transform(val.imag, axes)
            if self.codomain.harmonic:
                Tval_real.real += Tval_real.imag
                Tval_real.imag = Tval_imag.real + Tval_imag.imag
            else:
                Tval_real.real -= Tval_real.imag
                Tval_real.imag = Tval_imag.real - Tval_imag.imag

            Tval = Tval_real
        else:
            Tval = self._transform.transform(val, axes)
            if self.codomain.harmonic:
                Tval.real += Tval.imag
            else:
                Tval.real -= Tval.imag
            Tval = Tval.real

        if not self._transform.codomain.harmonic:
            # correct for inverse fft.
            # See discussion above.
            Tval = self._transform.codomain.weight(Tval, power=-1, axes=axes)

        return Tval