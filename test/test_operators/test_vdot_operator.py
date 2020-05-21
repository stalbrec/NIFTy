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
# Copyright(C) 2020 Max-Planck-Society
#
# NIFTy is being developed at the Max-Planck-Institut fuer Astrophysik.

import numpy as np
from numpy.testing import assert_allclose

import nifty6 as ift

from ..common import setup_function, teardown_function

def test_vdot_operator():
    dom = ift.makeDomain(ift.RGSpace(8))
    fa_1 = ift.FieldAdapter(dom, 'f1')
    fa_2 = ift.FieldAdapter(dom, 'f2')
    op1 = fa_1.vdot(fa_2)
    f = ift.from_random(op1.domain, dtype=np.float64)
    res1 = f['f1'].vdot(f['f2'])
    res2 = op1(f)
    assert_allclose(res1.val, res2.val)
    ift.extra.check_jacobian_consistency(op1, f)
    #another Test for linearization?
