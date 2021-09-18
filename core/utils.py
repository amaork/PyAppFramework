# -*- coding: utf-8 -*-
import inspect
from typing import Callable, Tuple, List, Container, Dict, Any
__all__ = ['util_filter_parameters', 'util_check_arguments', 'util_auto_kwargs']


def util_filter_parameters(func: Callable, filter_args: Container) -> List[str]:
    return [x for x in inspect.signature(func).parameters if x not in filter_args]


def util_check_arguments(func: Callable, args: Tuple, filter_args: Container):
    params = util_filter_parameters(func, filter_args)
    if len(args) < len(params):
        missing = tuple(params[len(args):])
        message = ",".join([f'{x!r}' for x in missing])
        raise TypeError(f'{func.__name__} missing {len(missing)} required positional arguments: {message}')
    elif len(args) > len(params):
        raise TypeError(f'{func.__name__} takes {len(params)} positional arguments but {len(args)} were given')


def util_auto_kwargs(func: Callable, args: Tuple, auto_kwargs: Dict[str, Any]) -> Dict[str, Any]:
    parameters = inspect.signature(func).parameters
    normal_params = util_filter_parameters(func, auto_kwargs.keys())

    kwargs = {k: auto_kwargs.get(k) for k in auto_kwargs if k in parameters}
    kwargs.update(dict(zip(normal_params, args)))
    return kwargs
