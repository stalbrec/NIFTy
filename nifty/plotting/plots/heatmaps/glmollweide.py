# -*- coding: utf-8 -*-

from nifty import dependency_injector as gdi
from heatmap import Heatmap
import numpy as np

from .mollweide_helper import mollweide_helper

pyHealpix = gdi.get('pyHealpix')


class GLMollweide(Heatmap):
    def __init__(self, data, xsize=800, color_map=None,
                 webgl=False, smoothing=False):
        # smoothing 'best', 'fast', False
        if 'pyHealpix' not in gdi:
            raise ImportError(
                "The module pyHealpix is needed but not available.")
        self.xsize = xsize

        super(GLMollweide, self).__init__(data, color_map, webgl, smoothing)

    def at(self, data):
        if isinstance(data, list):
            data = [self._mollview(d) for d in data]
        else:
            data = self._mollview(data)
        return GLMollweide(data=data,
                           xsize=self.xsize,
                           color_map=self.color_map,
                           webgl=self.webgl,
                           smoothing=self.smoothing)

    @staticmethod
    def _find_closest(A, target):
        # A must be sorted
        idx = A.searchsorted(target)
        idx = np.clip(idx, 1, len(A)-1)
        left = A[idx-1]
        right = A[idx]
        idx -= target - left < right - target
        return idx

    def _mollview(self, x):
        xsize = self.xsize
        nlat = x.shape[0]
        nlon = x.shape[1]

        res, mask, theta, phi = mollweide_helper(xsize)

        ra = np.linspace(0, 2*np.pi, nlon+1)
        dec = pyHealpix.GL_thetas(nlat)
        ilat = self._find_closest(dec, theta)
        ilon = self._find_closest(ra, phi)
        ilon = np.where(ilon == nlon, 0, ilon)
        res[mask] = x[ilat, ilon]
        return res