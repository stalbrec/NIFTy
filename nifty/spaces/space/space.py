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
    ..  /__/ /__/ /__/ /__/    \___/  \___   /  core
    ..                               /______/

    .. The NIFTY project homepage is http://www.mpa-garching.mpg.de/ift/nifty/

    NIFTY [#]_, "Numerical Information Field Theory", is a versatile
    library designed to enable the development of signal inference algorithms
    that operate regardless of the underlying spatial grid and its resolution.
    Its object-oriented framework is written in Python, although it accesses
    libraries written in Cython, C++, and C for efficiency.

    NIFTY offers a toolkit that abstracts discretized representations of
    continuous spaces, fields in these spaces, and operators acting on fields
    into classes. Thereby, the correct normalization of operations on fields is
    taken care of automatically without concerning the user. This allows for an
    abstract formulation and programming of inference algorithms, including
    those derived within information field theory. Thus, NIFTY permits its user
    to rapidly prototype algorithms in 1D and then apply the developed code in
    higher-dimensional settings of real world problems. The set of spaces on
    which NIFTY operates comprises point sets, n-dimensional regular grids,
    spherical spaces, their harmonic counterparts, and product spaces
    constructed as combinations of those.

    References
    ----------
    .. [#] Selig et al., "NIFTY -- Numerical Information Field Theory --
        a versatile Python library for signal inference",
        `A&A, vol. 554, id. A26 <http://dx.doi.org/10.1051/0004-6361/201321236>`_,
        2013; `arXiv:1301.4499 <http://www.arxiv.org/abs/1301.4499>`_

    Class & Feature Overview
    ------------------------
    The NIFTY library features three main classes: **spaces** that represent
    certain grids, **fields** that are defined on spaces, and **operators**
    that apply to fields.

    .. Overview of all (core) classes:
    ..
    .. - switch
    .. - notification
    .. - _about
    .. - random
    .. - space
    ..     - point_space
    ..     - rg_space
    ..     - lm_space
    ..     - gl_space
    ..     - hp_space
    ..     - nested_space
    .. - field
    .. - operator
    ..     - diagonal_operator
    ..         - power_operator
    ..     - projection_operator
    ..     - vecvec_operator
    ..     - response_operator
    .. - probing
    ..     - trace_probing
    ..     - diagonal_probing

    Overview of the main classes and functions:

    .. automodule:: nifty

    - :py:class:`space`
        - :py:class:`point_space`
        - :py:class:`rg_space`
        - :py:class:`lm_space`
        - :py:class:`gl_space`
        - :py:class:`hp_space`
        - :py:class:`nested_space`
    - :py:class:`field`
    - :py:class:`operator`
        - :py:class:`diagonal_operator`
            - :py:class:`power_operator`
        - :py:class:`projection_operator`
        - :py:class:`vecvec_operator`
        - :py:class:`response_operator`

        .. currentmodule:: nifty.nifty_tools

        - :py:class:`invertible_operator`
        - :py:class:`propagator_operator`

        .. currentmodule:: nifty.nifty_explicit

        - :py:class:`explicit_operator`

    .. automodule:: nifty

    - :py:class:`probing`
        - :py:class:`trace_probing`
        - :py:class:`diagonal_probing`

        .. currentmodule:: nifty.nifty_explicit

        - :py:class:`explicit_probing`

    .. currentmodule:: nifty.nifty_tools

    - :py:class:`conjugate_gradient`
    - :py:class:`steepest_descent`

    .. currentmodule:: nifty.nifty_explicit

    - :py:func:`explicify`

    .. currentmodule:: nifty.nifty_power

    - :py:func:`weight_power`,
      :py:func:`smooth_power`,
      :py:func:`infer_power`,
      :py:func:`interpolate_power`

"""
from __future__ import division

import abc

from nifty.domain_object import DomainObject


class Space(DomainObject):
    def __init__(self):
        """
            Parameters
            ----------
            None.

            Returns
            -------
            None.
        """

        super(Space, self).__init__()

    @abc.abstractproperty
    def harmonic(self):
        raise NotImplementedError

    @abc.abstractproperty
    def total_volume(self):
        """Returns the total volume of the space
        Returns
        -------
        Floating Point : An real number representing the sum of all pixel volumes.
        Raises
        ------
        NotImplementedError : If it is called for an abstract class, all non-abstract child-classes should
        implement this.
        """
        raise NotImplementedError(
            "There is no generic volume for the Space base class.")

    @abc.abstractmethod
    def copy(self):
        """Returns a copied version of this Space.
        
        Returns
        -------
        Space : A copy of this object.
        """
        return self.__class__()

    def get_distance_array(self, distribution_strategy):
        """The distances of the pixel to zero.
        
        In a harmonic space, this return an array that gives for each pixel its 
        distance to the zero-mode
        Returns
        -------
        array-like : An array representing the distances of each pixel to the zero-mode
        Raises
        ------
        NotImplementedError : If it is called for an abstract class, all non-abstract child-classes 
        that can be regarded as harmonic space should implement this.
        """
        raise NotImplementedError(
            "There is no generic distance structure for Space base class.")

    def get_fft_smoothing_kernel_function(self, sigma):
        """This method returns a function applying a smoothing kernel.
        
        This method, which is only implemented for harmonic spaces,
        helps smoothing functions that live in a position space that has this space as its harmonic space.
        The returned function multiplies field values of a field with a zero centered Gaussian which corresponds to convolution with a
        Gaussian kernel and sigma standard deviation in position space.
        
        Parameters
        ----------
        sigma : Floating Point
        A real number representing a physical scale on which the smoothing takes place. The smoothing is defined with respect to
        the real physical field and points that are closer together than one sigma are blurred together. Mathematically
        sigma is the standard deviation of a convolution with a normalized, zero-centered Gaussian that takes place in position space.
        
        Returns
        -------
        function Field -> Field : A smoothing operation that multiplies values with a Gaussian kernel.
        
        Raises
        ------
        NotImplementedError : If it is called for an abstract class, all non-abstract child-classes 
        that can be regarded as harmonic space should implement this.
        """
        raise NotImplementedError(
            "There is no generic co-smoothing kernel for Space base class.")

    def hermitian_decomposition(self, x, axes=None,
                                preserve_gaussian_variance=False):
        """
        Decomposes the field x into its hermitian and anti-hermitian constituents.
        
        If the space is harmonic, this method decomposes a field x into
        a hermitian and an antihermitian part, which corresponds to a real and imaginary part
        in a corresponding position space. This is an internal function that is mainly used for
        drawing real fields.
        
        Parameters
        ----------
        x : Field
            A field with this space as domain to be decomposed.
        axes : {int, tuple}, *optional*
            Specifies the axes of x which represent this domain.
            (default: None).
            If axes==None:
                weighting is applied with respect to all axes
        preserve_gaussian_variance : bool *optional*
            FIXME: figure out what this does
        Returns
        -------
        (Field, Field) : A tuple of two fields, the first field being the hermitian and the second the anti-hermitian part of x.
        
        Raises
        ------
        NotImplementedError : If it is called for an abstract class, all non-abstract child-classes 
        that can be regarded as harmonic space should implement this.
        """
        raise NotImplementedError

    def __repr__(self):
        string = ""
        string += str(type(self)) + "\n"
        return string
