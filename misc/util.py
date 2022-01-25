# -*- coding: utf-8 -*-
import os
__all__ = ['awk_query']


def awk_query(cmd: str, keyword: str, position: int) -> str:
    ret = os.popen("{0:s} | grep {1:s} | awk '{{print ${2:d}}}'".format(cmd, keyword, position))
    return ret.read().strip()
