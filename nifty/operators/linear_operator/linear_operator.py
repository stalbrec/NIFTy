# -*- coding: utf-8 -*-

import abc

from keepers import Loggable
from nifty.field import Field
import nifty.nifty_utilities as utilities


class LinearOperator(Loggable, object):
    __metaclass__ = abc.ABCMeta

    def __init__(self):
        pass

    def _parse_domain(self, domain):
        return utilities.parse_domain(domain)

    @abc.abstractproperty
    def domain(self):
        raise NotImplementedError

    @abc.abstractproperty
    def target(self):
        raise NotImplementedError

    @abc.abstractproperty
    def implemented(self):
        raise NotImplementedError

    @abc.abstractproperty
    def unitary(self):
        raise NotImplementedError

    def __call__(self, *args, **kwargs):
        return self.times(*args, **kwargs)

    def times(self, x, spaces=None, **kwargs):
        spaces = self._check_input_compatibility(x, spaces)

        if not self.implemented:
            x = x.weight(spaces=spaces)

        y = self._times(x, spaces, **kwargs)
        return y

    def inverse_times(self, x, spaces=None, **kwargs):
        spaces = self._check_input_compatibility(x, spaces, inverse=True)

        y = self._inverse_times(x, spaces, **kwargs)
        if not self.implemented:
            y = y.weight(power=-1, spaces=spaces)
        return y

    def adjoint_times(self, x, spaces=None, **kwargs):
        if self.unitary:
            return self.inverse_times(x, spaces)

        spaces = self._check_input_compatibility(x, spaces, inverse=True)

        if not self.implemented:
            x = x.weight(spaces=spaces)
        y = self._adjoint_times(x, spaces, **kwargs)
        return y

    def adjoint_inverse_times(self, x, spaces=None, **kwargs):
        if self.unitary:
            return self.times(x, spaces)

        spaces = self._check_input_compatibility(x, spaces)

        y = self._adjoint_inverse_times(x, spaces, **kwargs)
        if not self.implemented:
            y = y.weight(power=-1, spaces=spaces)
        return y

    def inverse_adjoint_times(self, x, spaces=None, **kwargs):
        if self.unitary:
            return self.times(x, spaces, **kwargs)

        spaces = self._check_input_compatibility(x, spaces)

        y = self._inverse_adjoint_times(x, spaces)
        if not self.implemented:
            y = y.weight(power=-1, spaces=spaces)
        return y

    def _times(self, x, spaces):
        raise NotImplementedError(
            "no generic instance method 'times'.")

    def _adjoint_times(self, x, spaces):
        raise NotImplementedError(
            "no generic instance method 'adjoint_times'.")

    def _inverse_times(self, x, spaces):
        raise NotImplementedError(
            "no generic instance method 'inverse_times'.")

    def _adjoint_inverse_times(self, x, spaces):
        raise NotImplementedError(
            "no generic instance method 'adjoint_inverse_times'.")

    def _inverse_adjoint_times(self, x, spaces):
        raise NotImplementedError(
            "no generic instance method 'inverse_adjoint_times'.")

    def _check_input_compatibility(self, x, spaces, inverse=False):
        if not isinstance(x, Field):
            raise ValueError(
                "supplied object is not a `nifty.Field`.")

        # sanitize the `spaces` and `types` input
        spaces = utilities.cast_axis_to_tuple(spaces, len(x.domain))

        # if the operator's domain is set to something, there are two valid
        # cases:
        # 1. Case:
        #   The user specifies with `spaces` that the operators domain should
        #   be applied to certain spaces in the domain-tuple of x.
        # 2. Case:
        #   The domains of self and x match completely.

        if not inverse:
            self_domain = self.domain
        else:
            self_domain = self.target

        if spaces is None:
            if self_domain != x.domain:
                raise ValueError(
                    "The operator's and and field's domains don't "
                    "match.")
        else:
            for i, space_index in enumerate(spaces):
                if x.domain[space_index] != self_domain[i]:
                    raise ValueError(
                        "The operator's and and field's domains don't "
                        "match.")

        return spaces

    def __repr__(self):
        return str(self.__class__)
