# NIFTy
# Copyright (C) 2017  Theo Steininger
#
# Author: Theo Steininger
#
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

"""
    ..                  __   ____   __
    ..                /__/ /   _/ /  /_
    ..      __ ___    __  /  /_  /   _/  __   __
    ..    /   _   | /  / /   _/ /  /   /  / /  /
    ..   /  / /  / /  / /  /   /  /_  /  /_/  /
    ..  /__/ /__/ /__/ /__/    \___/  \___   /  rg
    ..                               /______/

    NIFTY submodule for regular Cartesian grids.

"""
from __future__ import division

import numpy as np

from d2o import distributed_data_object,\
                STRATEGIES as DISTRIBUTION_STRATEGIES

from nifty.spaces.space import Space


class RGSpace(Space):
    """
        ..      _____   _______
        ..    /   __/ /   _   /
        ..   /  /    /  /_/  /
        ..  /__/     \____  /  space class
        ..          /______/

        NIFTY subclass for spaces of regular Cartesian grids.

        Attributes
        ----------
        harmonic : bool
            Whether or not the grid represents a Fourier basis.
        zerocenter : {bool, numpy.ndarray}
            Whether the Fourier zero-mode is located in the center of the grid
            (or the center of each axis speparately) or not.
            MR FIXME: this also does something if the space is not harmonic!
        distances : {float, numpy.ndarray}
            Distance between two grid points along each axis (default: None).
    """

    # ---Overwritten properties and methods---

    def __init__(self, shape, zerocenter=False, distances=None,
                 harmonic=False):
        """
            Sets the attributes for an RGSpace class instance.

            Parameters
            ----------
            shape : {int, numpy.ndarray}
                Number of grid points or numbers of gridpoints along each axis.
            zerocenter : {bool, numpy.ndarray}, *optional*
                Whether the Fourier zero-mode is located in the center of the
                grid (or the center of each axis speparately) or not
                MR FIXME: this also does something if the space is not harmonic!
                (default: False).
            distances : {float, numpy.ndarray}, *optional*
                Distance between two grid points along each axis
                (default: None).
                If distances==None:
                    if harmonic==True, all distances will be set to 1
                    if harmonic==False, the distance along each axis will be
                      set to the inverse of the number of points along that axis
            harmonic : bool, *optional*
                Whether the space represents a Fourier or a position grid
                (default: False).

            Returns
            -------
            None
        """
        self._harmonic = bool(harmonic)

        super(RGSpace, self).__init__()

        self._shape = self._parse_shape(shape)
        self._distances = self._parse_distances(distances)
        self._zerocenter = self._parse_zerocenter(zerocenter)

    def hermitian_decomposition(self, x, axes=None,
                                preserve_gaussian_variance=False):
        """Separates the hermitian and antihermitian part of a field.
        
        This is a function which is called by the field in order to separate itself for 
        each of its domains. 
        
        Parameters
        ----------
        x: Field
            Field to be decomposed.
        axes: {int, tuple}, *optional*
            Specifies which indices of the field belongs to this RGSpace. If None, it 
            takes the first dimensions of the field.
            (default: None)
        preserve_gaussian_variance: bool, *optional*
            
            (default: False)
        
        """
        # compute the hermitian part
        flipped_x = self._hermitianize_inverter(x, axes=axes)
        flipped_x = flipped_x.conjugate()
        # average x and flipped_x.
        hermitian_part = x + flipped_x
        hermitian_part /= 2.

        # use subtraction since it is faster than flipping another time
        anti_hermitian_part = (x-hermitian_part)/1j

        if preserve_gaussian_variance:
            hermitian_part, anti_hermitian_part = \
                self._hermitianize_correct_variance(hermitian_part,
                                                    anti_hermitian_part,
                                                    axes=axes)

        return (hermitian_part, anti_hermitian_part)

    def _hermitianize_correct_variance(self, hermitian_part,
                                       anti_hermitian_part, axes):
        # Correct the variance by multiplying sqrt(2)
        hermitian_part = hermitian_part * np.sqrt(2)
        anti_hermitian_part = anti_hermitian_part * np.sqrt(2)

        # The fixed points of the point inversion must not be averaged.
        # Hence one must divide out the sqrt(2) again
        # -> Get the middle index of the array
        mid_index = np.array(hermitian_part.shape, dtype=np.int) // 2
        dimensions = mid_index.size
        # Use ndindex to iterate over all combinations of zeros and the
        # mid_index in order to correct all fixed points.
        if axes is None:
            axes = xrange(dimensions)

        ndlist = [2 if i in axes else 1 for i in xrange(dimensions)]
        ndlist = tuple(ndlist)
        for i in np.ndindex(ndlist):
            temp_index = tuple(i * mid_index)
            hermitian_part[temp_index] /= np.sqrt(2)
            anti_hermitian_part[temp_index] /= np.sqrt(2)
        return hermitian_part, anti_hermitian_part

    def _hermitianize_inverter(self, x, axes):
        # calculate the number of dimensions the input array has
        dimensions = len(x.shape)
        # prepare the slicing object which will be used for mirroring
        slice_primitive = [slice(None), ] * dimensions
        # copy the input data
        y = x.copy()

        if axes is None:
            axes = xrange(dimensions)

        # flip in the desired directions
        for i in axes:
            slice_picker = slice_primitive[:]
            slice_picker[i] = slice(1, None, None)
            slice_picker = tuple(slice_picker)

            slice_inverter = slice_primitive[:]
            slice_inverter[i] = slice(None, 0, -1)
            slice_inverter = tuple(slice_inverter)

            try:
                y.set_data(to_key=slice_picker, data=y,
                           from_key=slice_inverter)
            except(AttributeError):
                y[slice_picker] = y[slice_inverter]
        return y

    # ---Mandatory properties and methods---

    @property
    def harmonic(self):
        return self._harmonic

    @property
    def shape(self):
        return self._shape

    @property
    def dim(self):
        return reduce(lambda x, y: x*y, self.shape)

    @property
    def total_volume(self):
        return self.dim * reduce(lambda x, y: x*y, self.distances)

    def copy(self):
        """Returns a copied version of this RGSpace.
			
        Returns
        -------
		RGSpace : A copy of this object.
        """
        return self.__class__(shape=self.shape,
                              zerocenter=self.zerocenter,
                              distances=self.distances,
                              harmonic=self.harmonic)

    def weight(self, x, power=1, axes=None, inplace=False):
        """ Weights a field living on this space with a specified amount of volume-weights.

		Weights hereby refer to integration weights, as they appear in discretized integrals.
		Per default, this function mutliplies each bin of the field x by its volume, which lets
		it behave like a density (top form). However, different powers of the volume can be applied
		with the power parameter. If only certain axes are specified via the axes parameter,
		the weights are only applied with respect to these dimensions, yielding an object that
		behaves like a lower degree form.
        Parameters
        ----------
        x : Field
            A field with this space as domain to be weighted.
        power : int, *optional*
            The power to which the volume-weight is raised.
            (default: 1).
        axes : {int, tuple}, *optional*
            Specifies for which axes the weights should be applied.
            (default: None).
            If axes==None:
                weighting is applied with respect to all axes
        inplace : bool, *optional*
            If this is True, the weighting is done on the values of x,
			if it is False, x is not modified and this method returns a 
			weighted copy of x
            (default: False).

        Returns
        -------
		Field
			A weighted version of x, with volume-weights raised to power.
            
        """
        weight = reduce(lambda x, y: x*y, self.distances)**power
        if inplace:
            x *= weight
            result_x = x
        else:
            result_x = x*weight
        return result_x

    def get_distance_array(self, distribution_strategy):
        """Returns the distance of the bins to zero.
        
        Calculates an n-dimensional array with its entries being the
        lengths of the k-vectors from the zero point of the grid.
        MR FIXME: Since this is about k-vectors, it might make sense to
        throw NotImplementedError if harmonic==False.

        Parameters
        ----------
        None : All information is taken from the parent object.

        Returns
        -------
        nkdict : distributed_data_object
        
        Raises
        ------
        ValueError
            The distribution_strategy is neither slicing nor not.
        """
        shape = self.shape
        # prepare the distributed_data_object
        nkdict = distributed_data_object(
                        global_shape=shape, dtype=np.float64,
                        distribution_strategy=distribution_strategy)

        if distribution_strategy in DISTRIBUTION_STRATEGIES['slicing']:
            # get the node's individual slice of the first dimension
            slice_of_first_dimension = slice(
                                    *nkdict.distributor.local_slice[0:2])
        elif distribution_strategy in DISTRIBUTION_STRATEGIES['not']:
            slice_of_first_dimension = slice(0, shape[0])
        else:
            raise ValueError(
                "Unsupported distribution strategy")
        dists = self._distance_array_helper(slice_of_first_dimension)
        nkdict.set_local_data(dists)

        return nkdict

    def _distance_array_helper(self, slice_of_first_dimension):
        dk = self.distances
        shape = self.shape

        inds = []
        for a in shape:
            inds += [slice(0, a)]

        cords = np.ogrid[inds]

        dists = ((cords[0] - shape[0]//2)*dk[0])**2
        # apply zerocenterQ shift
        if not self.zerocenter[0]:
            dists = np.fft.ifftshift(dists)
        # only save the individual slice
        dists = dists[slice_of_first_dimension]
        for ii in range(1, len(shape)):
            temp = ((cords[ii] - shape[ii] // 2) * dk[ii])**2
            if not self.zerocenter[ii]:
                temp = np.fft.ifftshift(temp)
            dists = dists + temp
        dists = np.sqrt(dists)
        return dists

    def get_fft_smoothing_kernel_function(self, sigma): 
    
        if sigma is None:
            sigma = np.sqrt(2) * np.max(self.distances)

        return lambda x: np.exp(-0.5 * np.pi**2 * x**2 * sigma**2)

    # ---Added properties and methods---

    @property
    def distances(self):
        return self._distances

    @property
    def zerocenter(self):
        return self._zerocenter

    def _parse_shape(self, shape):
        if np.isscalar(shape):
            shape = (shape,)
        temp = np.empty(len(shape), dtype=np.int)
        temp[:] = shape
        return tuple(temp)

    def _parse_distances(self, distances):
        if distances is None:
            if self.harmonic:
                temp = np.ones_like(self.shape, dtype=np.float64)
            else:
                temp = 1 / np.array(self.shape, dtype=np.float64)
        else:
            temp = np.empty(len(self.shape), dtype=np.float64)
            temp[:] = distances
        return tuple(temp)

    def _parse_zerocenter(self, zerocenter):
        temp = np.empty(len(self.shape), dtype=bool)
        temp[:] = zerocenter
        return tuple(temp)

    # ---Serialization---

    def _to_hdf5(self, hdf5_group):
        hdf5_group['shape'] = self.shape
        hdf5_group['zerocenter'] = self.zerocenter
        hdf5_group['distances'] = self.distances
        hdf5_group['harmonic'] = self.harmonic

        return None

    @classmethod
    def _from_hdf5(cls, hdf5_group, repository):
        result = cls(
            shape=hdf5_group['shape'][:],
            zerocenter=hdf5_group['zerocenter'][:],
            distances=hdf5_group['distances'][:],
            harmonic=hdf5_group['harmonic'][()],
            )
        return result
