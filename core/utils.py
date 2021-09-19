# -*- coding: utf-8 -*-
import inspect
import itertools
import collections
from typing import Callable, Tuple, List, Container, Dict, Any, Optional
__all__ = ['util_filter_parameters', 'util_check_arguments', 'util_auto_kwargs']


def util_filter_parameters(func: Callable, filter_args: Container) -> List[str]:
    """Filter func parameters not in filter_args and not has default parameters

    :param func: process function
    :param filter_args: filter args name
    :return: return matched args name
    """
    return [k for k in inspect.signature(func).parameters if k not in filter_args]


def util_default_parameters(func: Callable) -> List[str]:
    return [k for k, v in inspect.signature(func).parameters.items() if v.default != inspect.Parameter.empty]


def util_check_arguments(func: Callable, args: Tuple, filter_args: Optional[collections.Sequence] = None):
    """Check if a function's args is filled

    :param func: function to check
    :param args: function args value
    :param filter_args:  filter args
    :return: passed nothing happened, failed raise TypeError
    """
    def_params = util_default_parameters(func)
    params = util_filter_parameters(func, filter_args or list())
    required_argument_number = [k for k in params if k not in def_params]

    for i, (k, v) in enumerate(itertools.zip_longest(params, args)):
        if k is None:
            raise TypeError(f'{func.__name__} takes {len(params)} positional arguments but {len(args)} were given')

        if v is None and k not in def_params:
            missing = required_argument_number[i:]
            missing_args = ", ".join([f'{x!r}' for x in missing])
            raise TypeError(f'{func.__name__} missing {len(missing)} required positional arguments: {missing_args}')


def util_auto_kwargs(func: Callable, args: Tuple, auto_kwargs: Dict[str, Any]) -> Dict[str, Any]:
    parameters = inspect.signature(func).parameters
    normal_params = util_filter_parameters(func, auto_kwargs.keys())

    kwargs = {k: auto_kwargs.get(k) for k in auto_kwargs if k in parameters}
    kwargs.update(dict(zip(normal_params, args)))
    return kwargs
