# -*- coding: utf8 -*-

from __future__ import division
from builtins import range
import numpy as np

from ..endomorphic_operator import EndomorphicOperator


class DirectSmoothingOperator(EndomorphicOperator):
    def __init__(self, domain, sigma, log_distances=False,
                 default_spaces=None):
        super(DirectSmoothingOperator, self).__init__(default_spaces)

        self._domain = self._parse_domain(domain)
        if len(self._domain) != 1:
            raise ValueError("DirectSmoothingOperator only accepts exactly one"
                             " space as input domain.")

        self._sigma = float(sigma)
        self._log_distances = log_distances
        self._effective_smoothing_width = 3.01

    def _times(self, x, spaces):
        if self._sigma == 0:
            return x.copy()

        # the domain of the smoothing operator contains exactly one space.
        # Hence, if spaces is None, but we passed LinearOperator's
        # _check_input_compatibility, we know that x is also solely defined
        # on that space
        return self._smooth(x, (0,) if spaces is None else spaces)

    # ---Mandatory properties and methods---
    @property
    def domain(self):
        return self._domain

    @property
    def self_adjoint(self):
        return True

    @property
    def unitary(self):
        return False

    # ---Added properties and methods---

    def _precompute(self, x):
        """ Does precomputations for Gaussian smoothing on a 1D irregular grid.

        Parameters
        ----------
        x: 1D floating point array or list containing the individual grid
            positions. Points must be given in ascending order.


        Returns
        -------
        ibegin: integer array of the same size as x
            ibegin[i] is the minimum grid index to consider when computing the
            smoothed value at grid index i
        nval: integer array of the same size as x
            nval[i] is the number of indices to consider when computing the
            smoothed value at grid index i.
        wgt: list with the same number of entries as x
            wgt[i] is an array with nval[i] entries containing the
            normalized smoothing weights.
        """

        dxmax = self._effective_smoothing_width*self._sigma

        x = np.asarray(x)

        ibegin = np.searchsorted(x, x-dxmax)
        nval = np.searchsorted(x, x+dxmax) - ibegin

        wgt = []
        expfac = 1. / (2. * self._sigma*self._sigma)
        for i in range(x.size):
            if nval[i] > 0:
                t = x[ibegin[i]:ibegin[i]+nval[i]]-x[i]
                t = np.exp(-t*t*expfac)
                t *= 1./np.sum(t)
                wgt.append(t)
            else:
                wgt.append(np.array([]))

        return ibegin, nval, wgt

    def _apply_kernel_along_array(self, power, startindex, endindex,
                                  ibegin, nval, wgt):

        p_smooth = np.zeros(endindex-startindex, dtype=power.dtype)
        for i in range(startindex, endindex):
            imin = max(startindex, ibegin[i])
            imax = min(endindex, ibegin[i]+nval[i])
            p_smooth[imin:imax] += (power[i] *
                                    wgt[i][imin-ibegin[i]:imax-imin+ibegin[i]])

        return p_smooth

    def _apply_along_axis(self, axis, arr, startindex, endindex, distances):

        nd = arr.ndim
        ibegin, nval, wgt = self._precompute(distances)

        ind = np.zeros(nd-1, dtype=np.int)
        i = np.zeros(nd, dtype=object)
        shape = arr.shape
        indlist = np.asarray(list(range(nd)))
        indlist = np.delete(indlist, axis)
        i[axis] = slice(None, None)
        outshape = np.asarray(shape).take(indlist)

        i.put(indlist, ind)

        Ntot = np.product(outshape)
        holdshape = outshape
        slicedArr = arr[tuple(i.tolist())]
        res = self._apply_kernel_along_array(
                    slicedArr, startindex, endindex, ibegin, nval, wgt)

        outshape = np.asarray(arr.shape)
        outshape[axis] = endindex - startindex
        outarr = np.zeros(outshape, dtype=arr.dtype)
        outarr[tuple(i.tolist())] = res
        k = 1
        while k < Ntot:
            # increment the index
            ind[nd-1] += 1
            n = -1
            while (ind[n] >= holdshape[n]) and (n > (1-nd)):
                ind[n-1] += 1
                ind[n] = 0
                n -= 1
            i.put(indlist, ind)
            slicedArr = arr[tuple(i.tolist())]
            res = self._apply_kernel_along_array(
                    slicedArr, startindex, endindex, ibegin, nval, wgt)
            outarr[tuple(i.tolist())] = res
            k += 1

        return outarr

    def _smooth(self, x, spaces):
        # infer affected axes
        # we rely on the knowledge that `spaces` is a tuple with length 1.
        affected_axes = x.domain_axes[spaces[0]]
        if len(affected_axes) != 1:
            raise ValueError("By this implementation only one-dimensional "
                             "spaces can be smoothed directly.")
        affected_axis = affected_axes[0]

        distance_array = x.domain[spaces[0]].get_distance_array()
        if self._log_distances:
            np.log(np.maximum(distance_array, 1e-15), out=distance_array)

        return self._apply_along_axis(
                              affected_axis,
                              x.val,
                              startindex=0,
                              endindex=x.shape[affected_axis],
                              distances=distance_array)
