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

from .linear_operator import LinearOperator


class ChainOperator(LinearOperator):
    def __init__(self, ops, _callingfrommake=False):
        if not _callingfrommake:
            raise NotImplementedError
        super(ChainOperator, self).__init__()
        self._ops = ops
        self._capability = self._all_ops
        for op in ops:
            self._capability &= op.capability

    @staticmethod
    def simplify(ops):
        from .scaling_operator import ScalingOperator
        from .diagonal_operator import DiagonalOperator
        # Step 1: verify domains
        for i in range(len(ops)-1):
            if ops[i+1].target != ops[i].domain:
                raise ValueError("domain mismatch")
        # Step 2: unpack ChainOperators
        opsnew = []
        for op in ops:
            if isinstance(op, ChainOperator):
                opsnew += op._ops
            else:
                opsnew.append(op)
        ops = opsnew
        # Step 3: collect ScalingOperators
        fct = 1.
        opsnew = []
        lastdom = ops[-1].domain
        for op in ops:
            if isinstance(op, ScalingOperator):
                fct *= op._factor
            else:
                opsnew.append(op)
        if fct != 1.:
            # try to absorb the factor into a DiagonalOperator
            for i in range(len(opsnew)):
                if isinstance(opsnew[i], DiagonalOperator):
                    opsnew[i] = DiagonalOperator(opsnew[i].diagonal()*fct,
                                                 domain=opsnew[i].domain,
                                                 spaces=opsnew[i]._spaces)
                    fct = 1.
                    break
        if fct != 1:
            # have to add the scaling operator at the end
            opsnew.append(ScalingOperator(fct, lastdom))
        ops = opsnew
        # Step 4: combine DiagonalOperators where possible
        opsnew = []
        for op in ops:
            if (len(opsnew) > 0 and
                    isinstance(opsnew[-1], DiagonalOperator) and
                    isinstance(op, DiagonalOperator) and
                    op._spaces == opsnew[-1]._spaces):
                opsnew[-1] = DiagonalOperator(opsnew[-1].diagonal() *
                                              op.diagonal(),
                                              domain=opsnew[-1].domain,
                                              spaces=opsnew[-1]._spaces)
            else:
                opsnew.append(op)
        ops = opsnew
        return ops

    @staticmethod
    def make(ops):
        ops = tuple(ops)
        ops = ChainOperator.simplify(ops)
        if len(ops) == 1:
            return ops[0]
        return ChainOperator(ops, _callingfrommake=True)

    @property
    def domain(self):
        return self._ops[-1].domain

    @property
    def target(self):
        return self._ops[0].target

    @property
    def capability(self):
        return self._capability

    def apply(self, x, mode):
        self._check_mode(mode)
        t_ops = self._ops if mode & self._backwards else reversed(self._ops)
        for op in t_ops:
            x = op.apply(x, mode)
        return x