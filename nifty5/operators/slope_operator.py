import numpy as np

from ..domain_tuple import DomainTuple
from ..field import Field
from .linear_operator import LinearOperator


class SlopeOperator(LinearOperator):
    def __init__(self, domain, target, sigmas):
        self._domain = DomainTuple.make(domain)
        self._target = DomainTuple.make(target)

        if self.domain[0].shape != (len(self.target[0].shape) + 1,):
            raise AssertionError("Shape mismatch!")

        self._sigmas = sigmas
        self.ndim = len(self.target[0].shape)
        self.pos = np.zeros((self.ndim,) + self.target[0].shape)

        if self.ndim == 1:
            self.pos[0] = self.target[0].get_k_length_array().val
        else:
            shape = self.target[0].shape
            for i in range(self.ndim):
                rng = np.arange(target.shape[i])
                tmp = np.minimum(
                    rng, target.shape[i] + 1 - rng) * target.bindistances[i]
                fst_dims = (1,) * i
                lst_dims = (1,) * (self.ndim - i - 1)
                self.pos[i] += tmp.reshape(fst_dims + (shape[i],) + lst_dims)

    @property
    def sigmas(self):
        return self._sigmas

    @property
    def domain(self):
        return self._domain

    @property
    def target(self):
        return self._target

    def apply(self, x, mode):
        self._check_input(x, mode)

        # Times
        if mode == self.TIMES:
            inp = x.val
            res = self.sigmas[-1] * inp[-1]
            for i in range(self.ndim):
                res += self.sigmas[i] * inp[i] * self.pos[i]
            return Field(self.target, val=res)

        # Adjoint times
        res = np.zeros(self.domain[0].shape)
        res[-1] = np.sum(x.val) * self.sigmas[-1]
        for i in range(self.ndim):
            res[i] = np.sum(self.pos[i] * x.val) * self.sigmas[i]
        return Field(self.domain, val=res)

    @property
    def capability(self):
        return self.TIMES | self.ADJOINT_TIMES
