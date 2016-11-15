# -*- coding: utf-8 -*-

import pickle
import numpy as np

from keepers import Versionable

import d2o

from power_index_factory import PowerIndexFactory

from nifty.spaces.space import Space
from nifty.spaces.rg_space import RGSpace
from nifty.nifty_utilities import cast_axis_to_tuple


class PowerSpace(Versionable, Space):

    _serializable = ('log', 'nbin', 'binbounds', 'kindex', 'rho',
                     'pundex', 'dtype')

    # ---Overwritten properties and methods---

    def __init__(self, harmonic_domain=RGSpace((1,)),
                 distribution_strategy='not',
                 log=False, nbin=None, binbounds=None, power_index=None,
                 dtype=np.dtype('float')):

        super(PowerSpace, self).__init__(dtype)
        self._ignore_for_hash += ['_pindex', '_kindex', '_rho', '_pundex',
                                  '_k_array']

        if not isinstance(harmonic_domain, Space):
            raise ValueError(
                "harmonic_domain must be a Space.")
        if not harmonic_domain.harmonic:
            raise ValueError(
                "harmonic_domain must be a harmonic space.")
        self._harmonic_domain = harmonic_domain

        if power_index is None:
            power_index = PowerIndexFactory.get_power_index(
                            domain=self.harmonic_domain,
                            distribution_strategy=distribution_strategy,
                            log=log,
                            nbin=nbin,
                            binbounds=binbounds)

        config = power_index['config']
        self._log = config['log']
        self._nbin = config['nbin']
        self._binbounds = config['binbounds']

        self._pindex = power_index['pindex']
        self._kindex = power_index['kindex']
        self._rho = power_index['rho']
        self._pundex = power_index['pundex']
        self._k_array = power_index['k_array']

    def pre_cast(self, x, axes=None):
        if callable(x):
            return x(self.kindex)
        else:
            return x

    # ---Mandatory properties and methods---

    @property
    def harmonic(self):
        return True

    @property
    def shape(self):
        return self.kindex.shape

    @property
    def dim(self):
        return self.shape[0]

    @property
    def total_volume(self):
        # every power-pixel has a volume of 1
        return reduce(lambda x, y: x*y, self.pindex.shape)

    def copy(self):
        distribution_strategy = self.pindex.distribution_strategy
        return self.__class__(harmonic_domain=self.harmonic_domain,
                              distribution_strategy=distribution_strategy,
                              log=self.log,
                              nbin=self.nbin,
                              binbounds=self.binbounds,
                              dtype=self.dtype)

    def weight(self, x, power=1, axes=None, inplace=False):
        total_shape = x.shape

        axes = cast_axis_to_tuple(axes, len(total_shape))
        if len(axes) != 1:
            raise ValueError(
                "axes must be of length 1.")

        reshaper = [1, ] * len(total_shape)
        reshaper[axes[0]] = self.shape[0]

        weight = self.rho.reshape(reshaper)
        if power != 1:
            weight = weight ** power

        if inplace:
            x *= weight
            result_x = x
        else:
            result_x = x*weight

        return result_x

    def get_distance_array(self, distribution_strategy):
        result = d2o.distributed_data_object(
                                self.kindex,
                                distribution_strategy=distribution_strategy)
        return result

    def get_fft_smoothing_kernel_function(self, sigma):
        raise NotImplementedError(
            "There is no fft smoothing function for PowerSpace.")

    # ---Added properties and methods---

    @property
    def harmonic_domain(self):
        return self._harmonic_domain

    @property
    def log(self):
        return self._log

    @property
    def nbin(self):
        return self._nbin

    @property
    def binbounds(self):
        return self._binbounds

    @property
    def pindex(self):
        return self._pindex

    @property
    def kindex(self):
        return self._kindex

    @property
    def rho(self):
        return self._rho

    @property
    def pundex(self):
        return self._pundex

    @property
    def k_array(self):
        return self._k_array

    # ---Serialization---

    def _to_hdf5(self, hdf5_group):
        hdf5_group['serialized'] = [
            pickle.dumps(getattr(self, item)) for item in self._serializable
        ]

        return {
            'harmonic_domain': self.harmonic_domain,
            'pindex': self.pindex,
            'k_array': self.k_array
        }

    @classmethod
    def _from_hdf5(cls, hdf5_group, loopback_get):
        deserialized =\
            [pickle.loads(item) for item in hdf5_group['serialized']]

        dtype = deserialized[6]
        harmonic_domain = loopback_get('harmonic_domain')
        power_index = {
            'config': {
                'log': deserialized[0], 'nbin': deserialized[1],
                'binbounds': deserialized[2]
            },
            'pindex': loopback_get('pindex'),
            'kindex': deserialized[3],
            'rho': deserialized[4],
            'pundex': deserialized[5],
            'k_array': loopback_get('k_array')
        }

        result = cls(
            harmonic_domain=harmonic_domain,
            power_index=power_index,
            dtype=dtype
        )
        return result
