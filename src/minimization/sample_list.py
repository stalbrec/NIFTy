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
# Copyright(C) 2021 Max-Planck-Society
# Author: Philipp Arras, Philipp Frank

import pickle

from .. import utilities
from ..multi_domain import MultiDomain
from ..multi_field import MultiField


class SampleList:
    def __init__(self, comm, domain):
        from ..sugar import makeDomain
        self._comm = comm
        self._domain = makeDomain(domain)
        utilities.check_MPI_equality(self._domain, comm)

    @staticmethod
    def indices_from_comm(n_samples, comm):
        ntask, rank, _ = utilities.get_MPI_params_from_comm(comm)
        return range(*utilities.shareRange(n_samples, ntask, rank))

    @property
    def comm(self):
        return self._comm

    @property
    def domain(self):
        return self._domain

    def global_iterator(self, op=None):
        op = _none_to_id(op)
        if self.comm is not None:
            for itask in range(self.comm.Get_size()):
                for i in range(_bcast(len(self), self._comm, itask)):
                    ss = self[i] if itask == self._comm.Get_rank() else None
                    yield op(_bcast(ss, self._comm, itask))
        else:
            for ss in self:
                yield op(ss)

    def global_average(self, op=None):
        """if op returns tuple, then individual averages are computed and returned individually."""
        op = _none_to_id(op)
        res = [op(ss) for ss in self]
        n = self.global_n_samples()
        if not isinstance(res[0], tuple):
            return utilities.allreduce_sum(res, self.comm) / n
        res = [[elem[ii] for elem in res] for ii in range(len(res[0]))]
        return tuple(utilities.allreduce_sum(rr, self.comm) / n for rr in res)

    def global_n_samples(self):
        return utilities.allreduce_sum([len(self)], self.comm)

    def __len__(self):
        """Local length"""
        raise NotImplementedError

    def global_sample_stat(self, op):
        from ..probing import StatCalculator
        sc = StatCalculator()
        for ss in self.global_iterator(op):
            sc.add(ss)
        return sc.mean, sc.var

    def global_mean(self, op=None):
        return self.global_sample_stat(op)[0]

    def global_sd(self, op=None):
        return self.global_sample_stat(op)[1].sqrt()

    def save(self, file_name_base):
        if self._comm is not None:
            raise NotImplementedError
        with open(file_name_base + ".pickle", "wb") as f:
            pickle.dump(self, f, pickle.HIGHEST_PROTOCOL)

    @staticmethod
    def load(file_name_base, comm=None):
        if comm is not None:
            raise NotImplementedError
        with open(file_name_base + ".pickle", "rb") as f:
            obj = pickle.load(f)
        utilities.myassert(isinstance(obj, SampleList))
        return obj


class ResidualSampleList(SampleList):
    def __init__(self, mean, residuals, neg, comm):
        """
        Entries in dict of residual can be missing -> no residual is added
        """
        super(ResidualSampleList, self).__init__(comm, mean.domain)
        self._m = mean
        self._r = tuple(residuals)
        self._n = tuple(neg)

        if len(self._r) != len(self._n):
            raise ValueError("Residuals and neg need to have the same length.")

        r_dom = self._r[0].domain
        if not all(rr.domain is r_dom for rr in self._r):
            raise ValueError("All residuals must have the same domain.")
        if isinstance(r_dom, MultiDomain):
            try:
                self._m.extract(r_dom)
            except:
                raise ValueError("`residual.domain` must be a subdomain of `mean.domain`.")

        if not all(isinstance(nn, bool) for nn in neg):
            raise TypeError("All entries in neg need to be bool.")

    def at(self, mean):
        """Creates a new instance of `ResidualSampleList` where only the mean
        has changed. The residuals remain the same for the new list.
        """
        return ResidualSampleList(mean, self._r, self._n, self.comm)

    def update(self, field):
        """Updates (parts of) the mean with the new field values. A new instance
        of `ResidualSampleList` is created and the residuals remain the same for
        the new list.
        """
        if isinstance(self._m, MultiField) and self.domain != field.domain:
            return self.at(self._m.union([self._m, field]))
        return self.at(field)

    def __getitem__(self, i):
        return self._m.flexible_addsub(self._r[i], self._n[i])

    def __len__(self):
        return len(self._r)


class MinimalSampleList(SampleList):
    def __init__(self, samples, comm=None):
        super(MinimalSampleList, self).__init__(comm, samples[0].domain)
        self._s = samples

    def __getitem__(self, x):
        return self._s[x]

    def __len__(self):
        return len(self._s)


def _none_to_id(obj):
    if obj is None:
        return lambda x: x
    return obj


def _bcast(obj, comm, root):
    data = obj if comm.Get_rank() == root else None
    return comm.bcast(data, root=root)
