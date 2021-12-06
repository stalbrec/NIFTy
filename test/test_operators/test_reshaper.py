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

import nifty8 as ift
import pytest
from nifty8 import DomainChangerAndReshaper

from ..common import list2fixture, setup_function, teardown_function


def test_reshaper():
    dom = ift.makeDomain((ift.RGSpace([2, 4]), ift.UnstructuredDomain([10])))
    for tgt in [ift.UnstructuredDomain(dom.size), ift.RGSpace([8, 10]), (ift.UnstructuredDomain(4), ift.RGSpace(20))]:
        op = DomainChangerAndReshaper(dom, tgt)
        ift.extra.check_linear_operator(op)

        op1 = ift.ScalingOperator(dom, 1.2)

        with pytest.raises(ValueError):
            op1 @ op

        op1.force(op)
