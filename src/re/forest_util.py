# Copyright(C) 2013-2021 Max-Planck-Society
# SPDX-License-Identifier: GPL-2.0+ OR BSD-2-Clause

import operator
from functools import partial, reduce
from typing import Any, Callable, List, Optional, Tuple, TypeVar, Union

from jax import lax
from jax import numpy as jnp
from jax.tree_util import (
    all_leaves,
    tree_leaves,
    tree_map,
    tree_reduce,
    tree_structure,
    tree_transpose,
)

from .field import Field
from .sugar import is1d


def split(mappable, keys):
    """Split a dictionary into one containing only the specified keys and one
    with all of the remaining ones.
    """
    sel, rest = {}, {}
    for k, v in mappable.items():
        if k in keys:
            sel[k] = v
        else:
            rest[k] = v
    return sel, rest


def unite(x, y, op=operator.add):
    """Unites two array-, dict- or Field-like objects.

    If a key is contained in both objects, then the fields at that key
    are combined.
    """
    if isinstance(x, Field) or isinstance(y, Field):
        x = x.val if isinstance(x, Field) else x
        y = y.val if isinstance(y, Field) else y
        return Field(unite(x, y, op=op))
    if not hasattr(x, "keys") and not hasattr(y, "keys"):
        return op(x, y)
    if not hasattr(x, "keys") or not hasattr(y, "keys"):
        te = (
            "one of the inputs does not have a `keys` property;"
            f" got {type(x)} and {type(y)}"
        )
        raise TypeError(te)

    out = {}
    for k in x.keys() | y.keys():
        if k in x and k in y:
            out[k] = op(x[k], y[k])
        elif k in x:
            out[k] = x[k]
        else:
            out[k] = y[k]
    return out


CORE_ARITHMETIC_ATTRIBUTES = (
    "__neg__", "__pos__", "__abs__", "__add__", "__radd__", "__sub__",
    "__rsub__", "__mul__", "__rmul__", "__truediv__", "__rtruediv__",
    "__floordiv__", "__rfloordiv__", "__pow__", "__rpow__", "__mod__",
    "__rmod__", "__matmul__", "__rmatmul__"
)


def has_arithmetics(obj, additional_attributes=()):
    desired_attrs = CORE_ARITHMETIC_ATTRIBUTES + additional_attributes
    return all(hasattr(obj, attr) for attr in desired_attrs)


def assert_arithmetics(obj, *args, **kwargs):
    if not has_arithmetics(obj, *args, **kwargs):
        ae = (
            f"input of type {type(obj)} does not support"
            " core arithmetic operations"
            "\nmaybe you forgot to wrap your object in a"
            " :class:`nifty8.re.field.Field` instance"
        )
        raise AssertionError(ae)


class ShapeWithDtype():
    """Minimal helper class storing the shape and dtype of an object.

    Notes
    -----
    This class may not be transparent to JAX as it shall not be flattened
    itself. If used in a tree-like structure. It should only be used as leave.
    """
    def __init__(
        self, shape: Union[Tuple[()], Tuple[int], List[int], int], dtype=None
    ):
        """Instantiates a storage unit for shape and dtype.

        Parameters
        ----------
        shape : tuple or list of int
            One-dimensional sequence of integers denoting the length of the
            object along each of the object's axis.
        dtype : dtype
            Data-type of the to-be-described object.
        """
        if isinstance(shape, int):
            shape = (shape, )
        if isinstance(shape, list):
            shape = tuple(shape)
        if not is1d(shape):
            ve = f"invalid shape; got {shape!r}"
            raise TypeError(ve)

        self._shape = shape
        self._dtype = jnp.float64 if dtype is None else dtype
        self._size = None

    @classmethod
    def from_leave(cls, element):
        """Convenience method for creating an instance of `ShapeWithDtype` from
        an object.

        To map a whole tree-like structure to a its shape and dtype use JAX's
        `tree_map` method like so:

            tree_map(ShapeWithDtype.from_leave, tree)

        Parameters
        ----------
        element : tree-like structure
            Object from which to take the shape and data-type.

        Returns
        -------
        swd : instance of ShapeWithDtype
            Instance storing the shape and data-type of `element`.
        """
        if not all_leaves((element, )):
            ve = "tree is not flat and still contains leaves"
            raise ValueError(ve)
        return cls(jnp.shape(element), get_dtype(element))

    @property
    def shape(self) -> Tuple[int]:
        """Retrieves the shape."""
        return self._shape

    @property
    def dtype(self):
        """Retrieves the data-type."""
        return self._dtype

    @property
    def size(self) -> int:
        """Total number of elements."""
        if self._size is None:
            self._size = reduce(operator.mul, self.shape, 1)
        return self._size

    @property
    def ndim(self) -> int:
        return len(self.shape)

    def __len__(self) -> int:
        if self.ndim > 0:
            return self.shape[0]
        else:  # mimic numpy
            raise TypeError("len() of unsized object")

    def __eq__(self, other) -> bool:
        if not isinstance(other, ShapeWithDtype):
            return False
        else:
            return (self.shape, self.dtype) == (other.shape, other.dtype)

    def __repr__(self):
        nm = self.__class__.__name__
        return f"{nm}(shape={self.shape}, dtype={self.dtype})"

    # TODO: overlaod basic arithmetics (see `np.broadcast_shapes((1, 2), (3,
    # 1), (3, 2))`)


def get_dtype(v: Any):
    if hasattr(v, "dtype"):
        return v.dtype
    else:
        return type(v)


def common_type(*trees):
    from numpy import find_common_type

    common_dtp = find_common_type(
        tuple(
            find_common_type(tuple(get_dtype(v) for v in tree_leaves(tr)), ())
            for tr in trees
        ), ()
    )
    return common_dtp


def _size(x):
    return x.size if hasattr(x, "size") else jnp.size(x)


def size(tree, axis: Optional[int] = None) -> int:
    if axis is not None:
        raise TypeError("axis of an arbitrary tree is ill defined")
    sizes = tree_map(_size, tree)
    return tree_reduce(operator.add, sizes)


def _shape(x):
    return x.shape if hasattr(x, "shape") else jnp.shape(x)


T = TypeVar("T")


def shape(tree: T) -> T:
    return tree_map(_shape, tree)


def _zeros_like(x, dtype, shape):
    if hasattr(x, "shape") and hasattr(x, "dtype"):
        shp = x.shape if shape is None else shape
        dtp = x.dtype if dtype is None else dtype
        return jnp.zeros(shape=shp, dtype=dtp)
    return jnp.zeros_like(x, dtype=dtype, shape=shape)


def zeros_like(a, dtype=None, shape=None):
    return tree_map(partial(_zeros_like, dtype=dtype, shape=shape), a)


def _ravel(x):
    return x.ravel() if hasattr(x, "ravel") else jnp.ravel(x)


def norm(tree, ord, *, ravel: bool):
    from jax.numpy.linalg import norm

    def el_norm(x):
        if jnp.ndim(x) == 0:
            return jnp.abs(x)
        elif ravel:
            return norm(_ravel(x), ord=ord)
        else:
            return norm(x, ord=ord)

    return norm(jnp.array(tree_leaves(tree_map(el_norm, tree))), ord=ord)


def dot(a, b, *, precision=None):
    tree_of_dots = tree_map(
        lambda x, y: jnp.dot(_ravel(x), _ravel(y), precision=precision), a, b
    )
    return tree_reduce(operator.add, tree_of_dots, 0.)


def vdot(a, b, *, precision=None):
    tree_of_vdots = tree_map(
        lambda x, y: jnp.vdot(_ravel(x), _ravel(y), precision=precision), a, b
    )
    return tree_reduce(jnp.add, tree_of_vdots, 0.)


def select(pred, on_true, on_false):
    return tree_map(partial(lax.select, pred), on_true, on_false)


def where(condition, x, y):
    """Selects a pytree based on the condition which can be a pytree itself.

    Notes
    -----
    If `condition` is not a pytree, then a partially evaluated selection is
    simply mapped over `x` and `y` without actually broadcasting `condition`.
    """
    import numpy as np
    from itertools import repeat

    ts_c = tree_structure(condition)
    ts_x = tree_structure(x)
    ts_y = tree_structure(y)
    ts_max = (ts_c, ts_x, ts_y)[np.argmax(
        [ts_c.num_nodes, ts_x.num_nodes, ts_y.num_nodes]
    )]

    if ts_x.num_nodes < ts_max.num_nodes:
        if ts_x.num_nodes > 1:
            raise ValueError("can not broadcast LHS")
        x = ts_max.unflatten(repeat(x, ts_max.num_leaves))
    if ts_y.num_nodes < ts_max.num_nodes:
        if ts_y.num_nodes > 1:
            raise ValueError("can not broadcast RHS")
        y = ts_max.unflatten(repeat(y, ts_max.num_leaves))

    if ts_c.num_nodes < ts_max.num_nodes:
        if ts_c.num_nodes > 1:
            raise ValueError("can not map condition")
        return tree_map(partial(jnp.where, condition), x, y)
    return tree_map(jnp.where, condition, x, y)


def stack(arrays):
    return tree_map(lambda *el: jnp.stack(el), *arrays)


def unstack(stack):
    element_count = tree_leaves(stack)[0].shape[0]
    split = partial(jnp.split, indices_or_sections=element_count)
    unstacked = tree_transpose(
        tree_structure(stack), tree_structure((0., ) * element_count),
        tree_map(split, stack)
    )
    return tree_map(partial(jnp.squeeze, axis=0), unstacked)


def _lax_map(fun, in_axes=0, out_axes=0):
    if in_axes not in (0, (0, )) or out_axes not in (0, (0, )):
        raise ValueError("`lax.map` maps only along first axis")
    return partial(lax.map, fun)


def _safe_assert(condition):
    if not condition:
        raise AssertionError()


def _int_or_none(x):
    return isinstance(x, int) or x is None


def smap(fun, in_axes=0, out_axes=0, *, unroll=1):
    """Stupid/sequential map.

    Many of JAX's control flow logic reduces to a simple `jax.lax.scan`. This
    function is one of these. In contrast to `jax.lax.map` or
    `jax.lax.fori_loop`, it behaves much like `jax.vmap`. In fact, it
    re-implements `in_axes` and `out_axes` and can be used in much the same way
    as `jax.vmap`. However, instead of batching the input, it works through it
    sequentially.

    This implementation makes no claim on being efficient. It explicitly swaps
    around axis in the input and output, potentially allocating more memory
    than strictly necessary and worsening the memory layout.

    For the semantics of `in_axes` and `out_axes` see `jax.vmap`. For the
    semantics of `unroll` see `jax.lax.scan`.
    """
    from jax.tree_util import tree_flatten, tree_map, tree_unflatten

    def blm(*args, **kwargs):
        _safe_assert(not kwargs)
        inax = in_axes
        if isinstance(inax, int):
            inax = tree_map(lambda _: inax, args)
        elif isinstance(inax, tuple):
            if len(inax) != len(args):
                ve = f"`in_axes` {in_axes!r} and input {args!r} must be of same length"
                raise ValueError(ve)
            new_inax = []
            for a, i in zip(args, inax):
                if _int_or_none(i):
                    new_inax += [tree_map(lambda _: i, a)]
                else:
                    new_inax += [i]
            inax = tuple(new_inax)
        else:
            te = (
                "`in_axes` must be an integer or a tuple of arbitrary structures"
                f"; got {in_axes!r}"
            )
            raise TypeError(te)
        args, args_td = tree_flatten(args)
        inax, inax_td = tree_flatten(inax, is_leaf=_int_or_none)
        if inax_td != args_td:
            ve = f"`in_axes` {inax_td!r} incompatible with `args` {args_td!r}"
            raise ValueError(ve)

        args_map = []
        for a, i in zip(args, inax):
            if i is None:
                continue
            elif i != 0:
                args_map += [jnp.swapaxes(a, 0, i)]
            else:
                args_map += [a]
        del a, i

        def fun_reord(_, x):
            args_slice = []
            x = list(x)
            for a, i in zip(args, inax):
                args_slice += [a if i is None else x.pop(0)]
            _safe_assert(not len(x))
            y = fun(*tree_unflatten(args_td, args_slice))
            return None, y

        # TODO: wait for https://github.com/google/jax/issues/14743 to be fixed,
        # then give fun_reord the hash of (fun, in_axes, out_axes) + the
        # constant folded input.
        _, scanned = lax.scan(fun_reord, None, args_map, unroll=unroll)

        oax = out_axes
        if isinstance(oax, int):
            oax = tree_map(lambda _: oax, scanned)
        scanned, scanned_td = tree_flatten(scanned)
        oax, oax_td = tree_flatten(oax, is_leaf=_int_or_none)
        if oax_td != scanned_td:
            ve = f"`out_axes` {oax_td!r} incompatible with output {scanned_td!r}"
            raise ValueError(ve)
        out = []
        for s, i in zip(scanned, oax):
            if i != 0:
                out += [jnp.swapaxes(s, 0, i)]
            else:
                out += [s]
        del s, i

        return tree_unflatten(scanned_td, out)

    return blm


def get_map(map) -> Callable:
    from jax import pmap, vmap

    if isinstance(map, str):
        if map in ('vmap', 'v'):
            m = vmap
        elif map in ('pmap', 'p'):
            m = pmap
        elif map in ('lax.map', 'lax', 'l'):
            m = _lax_map
        elif map in ('smap', 's'):
            m = smap
        else:
            raise ValueError(f"unknown `map` {map!r}")
    elif callable(map):
        m = map
    else:
        raise TypeError(f"invalid `map` {map!r}; expected string or callable")
    return m


def map_forest(
    f: Callable,
    in_axes: Union[int, Tuple] = 0,
    out_axes: Union[int, Tuple] = 0,
    tree_transpose_output: bool = True,
    map: Union[str, Callable] = "vmap",
    **kwargs
) -> Callable:
    if out_axes != 0:
        raise TypeError("`out_axis` not yet supported")
    in_axes = in_axes if isinstance(in_axes, tuple) else (in_axes, )
    i = None
    for idx, el in enumerate(in_axes):
        if el is not None and i is None:
            i = idx
        elif el is not None and i is not None:
            ve = "mapping over more than one axis is not yet supported"
            raise ValueError(ve)
    if i is None:
        raise ValueError("must map over at least one axis")
    if not isinstance(i, int):
        te = "mapping over a non integer axis is not yet supported"
        raise TypeError(te)

    map = get_map(map)
    map_f = map(f, in_axes=in_axes, out_axes=out_axes, **kwargs)

    def apply(*xs):
        if not isinstance(xs[i], (list, tuple)):
            te = f"expected mapped axes to be a tuple; got {type(xs[i])}"
            raise TypeError(te)
        x_T = stack(xs[i])

        out_T = map_f(*xs[:i], x_T, *xs[i + 1:])
        # Since `out_axes` is forced to be `0`, we don't need to worry about
        # transposing only part of the output
        if not tree_transpose_output:
            return out_T
        return unstack(out_T)

    return apply


def map_forest_mean(method, map="vmap", *args, **kwargs) -> Callable:
    method_map = map_forest(
        method, *args, tree_transpose_output=False, map=map, **kwargs
    )

    def meaned_apply(*xs, **xs_kw):
        return tree_map(partial(jnp.mean, axis=0), method_map(*xs, **xs_kw))

    return meaned_apply
