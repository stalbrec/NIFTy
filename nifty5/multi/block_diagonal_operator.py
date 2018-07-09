from __future__ import absolute_import, division, print_function
from ..compat import *
import numpy as np
from ..operators.endomorphic_operator import EndomorphicOperator
from .multi_domain import MultiDomain
from .multi_field import MultiField


class BlockDiagonalOperator(EndomorphicOperator):
    def __init__(self, domain, operators):
        """
        Parameters
        ----------
        operators : dict
            dictionary with operators domain names as keys and
            LinearOperators as items
        """
        super(BlockDiagonalOperator, self).__init__()
        self._domain = domain
        self._ops = tuple(operators[key] for key in self.domain.keys())
        self._cap = self._all_ops
        for op in self._ops:
            if op is not None:
                self._cap &= op.capability

    @property
    def domain(self):
        return self._domain

    @property
    def capability(self):
        return self._cap

    def apply(self, x, mode):
        self._check_input(x, mode)
        val = tuple(op.apply(v, mode=mode) if op is not None else None
                    for op, v in zip(self._ops, x.values()))
        return MultiField(self._domain, val)

#    def draw_sample(self, from_inverse=False, dtype=np.float64):
#        dtype = MultiField.build_dtype(dtype, self._domain)
#        val = tuple(op.draw_sample(from_inverse, dtype)
#                    for op in self._op)
#        return MultiField(self._domain, val)

    def _combine_chain(self, op):
        if self._domain is not op._domain:
            raise ValueError("domain mismatch")
        res = {key: v1*v2
               for key, v1, v2 in zip(self._domain.keys(), self._ops, op._ops)}
        return BlockDiagonalOperator(self._domain, res)

    def _combine_sum(self, op, selfneg, opneg):
        from ..operators.sum_operator import SumOperator
        if self._domain is not op._domain:
            raise ValueError("domain mismatch")
        res = {}
        for key, v1, v2 in zip(self._domain.keys(), self._ops, op._ops):
            res[key] = SumOperator.make([v1, v2], [selfneg, opneg])
        return BlockDiagonalOperator(self._domain, res)
