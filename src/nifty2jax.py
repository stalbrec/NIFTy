# Copyright(C) 2013-2021 Max-Planck-Society
# SPDX-License-Identifier: GPL-2.0+ OR BSD-2-Clause

from functools import partial, reduce
import operator
from typing import Any, Callable, Tuple
from warnings import warn

from jax.tree_util import tree_map
from . import re as jft

from . import DomainTuple, Field, MultiDomain, MultiField, Operator, makeField


def spaces_to_axes(domain, spaces):
    """Converts spaces in a domain to axes of the underlying NumPy array."""
    if spaces is None:
        return None

    domain = DomainTuple.make(domain)
    axes = tuple(domain.axes[sp_index] for sp_index in spaces)
    axes = reduce(operator.add, axes) if len(axes) > 0 else axes
    return axes


def shapewithdtype_from_domain(domain, dtype):
    if isinstance(dtype, dict):
        dtp_fallback = float  # Fallback to `float` for unspecified keys
        k2dtp = dtype
    else:
        dtp_fallback = dtype
        k2dtp = {}

    if isinstance(domain, MultiDomain):
        parameter_tree = {}
        for k, dom in domain.items():
            parameter_tree[k] = jft.ShapeWithDtype(
                dom.shape, k2dtp.get(k, dtp_fallback)
            )
    elif isinstance(domain, DomainTuple):
        parameter_tree = jft.ShapeWithDtype(domain.shape, dtype)
    else:
        raise TypeError(f"incompatible domain {domain!r}")
    return parameter_tree


def wrap_nifty_call(op, target_dtype=float) -> Callable[[Any], jft.Field]:
    from jax.experimental.host_callback import call

    if callable(op.jax_expr):
        warn("wrapping operator that has a callable `.jax_expr`")

    def pack_unpack_call(x):
        x = makeField(op.domain, x)
        return op(x).val

    # TODO: define custom JVP and VJP rules
    pt = shapewithdtype_from_domain(op.target, target_dtype)
    hcb_call = partial(call, pack_unpack_call, result_shape=pt)

    def wrapped_call(x) -> jft.Field:
        return jft.Field(hcb_call(x))

    return wrapped_call


def convert(op: Operator, dtype=float) -> Tuple[Any, Any]:
    # TODO: return a registered `Model` (?) class that combines both call and
    # values/domain. This would allow for converting everything: domains,
    # operators, fields, ... into single unified object
    if not isinstance(op, Operator):
        raise TypeError(f"invalid input type {type(op)!r}")

    if isinstance(op, (Field, MultiField)):
        parameter_tree = tree_map(jft.ShapeWithDtype.from_leave, op.val)
    else:
        parameter_tree = shapewithdtype_from_domain(op.domain, dtype)
    parameter_tree = jft.Field(parameter_tree)

    if isinstance(op, (Field, MultiField)):
        expr = jft.Field(op.val)
    else:
        expr = op.jax_expr
        if not callable(expr):
            # TODO: implement conversion via host_callback and custom_vjp
            raise NotImplementedError("Sorry, not yet done :(")

    return expr, parameter_tree
