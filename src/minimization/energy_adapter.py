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
# Copyright(C) 2013-2020 Max-Planck-Society
#
# NIFTy is being developed at the Max-Planck-Institut fuer Astrophysik.

import numpy as np

from .. import random
from ..linearization import Linearization
from ..minimization.energy import Energy
from ..utilities import myassert, allreduce_sum
from ..multi_domain import MultiDomain
from ..sugar import from_random

class EnergyAdapter(Energy):
    """Helper class which provides the traditional Nifty Energy interface to
    Nifty operators with a scalar target domain.

    Parameters
    -----------
    position: Field or MultiField
        The position where the minimization process is started.
    op: EnergyOperator
        The expression computing the energy from the input data.
    constants: list of strings
        The component names of the operator's input domain which are assumed
        to be constant during the minimization process.
        If the operator's input domain is not a MultiField, this must be empty.
        Default: [].
    want_metric: bool
        If True, the class will provide a `metric` property. This should only
        be enabled if it is required, because it will most likely consume
        additional resources. Default: False.
    nanisinf : bool
        If true, nan energies which can happen due to overflows in the forward
        model are interpreted as inf. Thereby, the code does not crash on
        these occaisions but rather the minimizer is told that the position it
        has tried is not sensible.
    """

    def __init__(self, position, op, constants=[], want_metric=False,
                 nanisinf=False):
        if len(constants) > 0:
            cstpos = position.extract_by_keys(constants)
            _, op = op.simplify_for_constant_input(cstpos)
            varkeys = set(op.domain.keys()) - set(constants)
            position = position.extract_by_keys(varkeys)
        super(EnergyAdapter, self).__init__(position)
        self._op = op
        self._want_metric = want_metric
        lin = Linearization.make_var(position, want_metric)
        tmp = self._op(lin)
        self._val = tmp.val.val[()]
        self._grad = tmp.gradient
        self._metric = tmp._metric
        self._nanisinf = bool(nanisinf)
        if self._nanisinf and np.isnan(self._val):
            self._val = np.inf

    def at(self, position):
        return EnergyAdapter(position, self._op, want_metric=self._want_metric,
                             nanisinf=self._nanisinf)

    @property
    def value(self):
        return self._val

    @property
    def gradient(self):
        return self._grad

    @property
    def metric(self):
        return self._metric

    def apply_metric(self, x):
        return self._metric(x)


class StochasticEnergyAdapter(Energy):
    """A variant of `EnergyAdapter` that provides the energy interface for an
    operator with a scalar target where parts of the imput are averaged
    instead of optmized. Specifically, for the input corresponding to `keys`
    a set of standart normal distributed samples are drawn and each gets
    partially inserted into `bigop`. The results are averaged and represent a
    stochastic average of an energy with the remaining subdomain being the DOFs
    that are considered to be optimization parameters.
    """
    def __init__(self, position, bigop, keys, local_ops, n_samples, comm, nanisinf,
                 _callingfrommake=False):
        if not _callingfrommake:
            raise NotImplementedError
        super(StochasticEnergyAdapter, self).__init__(position)
        for op in local_ops:
            myassert(position.domain == op.domain)
        self._comm = comm
        self._local_ops = local_ops
        self._n_samples = n_samples
        lin = Linearization.make_var(position)
        v, g = [], []
        for op in self._local_ops:
            tmp = op(lin)
            v.append(tmp.val.val)
            g.append(tmp.gradient)
        self._val = allreduce_sum(v, self._comm)[()]/self._n_samples
        if np.isnan(self._val) and self._nanisinf:
            self._val = np.inf
        self._grad = allreduce_sum(g, self._comm)/self._n_samples

        self._op = bigop
        self._keys = keys

    @property
    def value(self):
        return self._val

    @property
    def gradient(self):
        return self._grad

    def at(self, position):
        return StochasticEnergyAdapter(position, self._local_ops,
                        self._n_samples, self._comm, self._nanisinf)

    def apply_metric(self, x):
        lin = Linearization.make_var(self.position, want_metric=True)
        res = []
        for op in self._local_ops:
            res.append(op(lin).metric(x))
        return allreduce_sum(res, self._comm)/self._n_samples

    @property
    def metric(self):
        from .kl_energies import _SelfAdjointOperatorWrapper
        return _SelfAdjointOperatorWrapper(self.position.domain,
                                           self.apply_metric)

    def resample_at(self, position):
        return StochasticEnergyAdapter.make(position, self._op, self._keys,
                                             self._n_samples, self._comm)

    @staticmethod
    def make(position, op, keys, n_samples, mirror_samples, nanisinf = False, comm=None):
        """Energy adapter where parts of the model are sampled.
        """
        samdom = {}
        for k in keys:
            if k in position.domain.keys():
                raise ValueError
            if k not in op.domain.keys():
                raise ValueError
            else:
                samdom[k] = op.domain[k]
        samdom = MultiDomain.make(samdom)
        local_ops = []
        sseq = random.spawn_sseq(n_samples)
        from .kl_energies import _get_lo_hi
        for i in range(*_get_lo_hi(comm, n_samples)):
            with random.Context(sseq[i]):
                rnd = from_random(samdom)
                _, tmp = op.simplify_for_constant_input(rnd)
                myassert(tmp.domain == position.domain)
                local_ops.append(tmp)
                if mirror_samples:
                    local_ops.append(op.simplify_for_constant_input(-rnd)[1])
        n_samples = 2*n_samples if mirror_samples else n_samples
        return StochasticEnergyAdapter(position, op, keys, local_ops, n_samples,
                                        comm, nanisinf, _callingfrommake=True)
