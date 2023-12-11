# -*- coding: utf-8 -*-
import numpy as np
from ..core.datatype import DynamicObject
__all__ = ['calc_mean_std_cv']


def calc_mean_std_cv(array: np.array, axis: int = 0, is_sample: bool = False) -> DynamicObject:
    count = array.shape[0]

    if is_sample:
        count -= 1

    mean = np.array(array.mean(axis=axis))
    sd = np.sqrt(np.square(np.abs(array - mean)).sum(axis=axis) / array.shape[0])
    cv = sd / mean * 100.0
    return DynamicObject(mean=mean, sd=sd, cv=cv)