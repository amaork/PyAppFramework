# -*- coding: utf-8 -*-

import types
import ctypes


__all__ = ['BasicDataType', 'BasicTypeLE', 'BasicTypeBE', 'str2float', 'str2number']


def str2float(text):
    if isinstance(text, float):
        return text

    if not isinstance(text, types.StringTypes):
        print "TypeError:{0:s}".format(type(text))
        return 0

    try:

        return float(text)

    except ValueError, e:
        print "Str2float error:{0:s}, {1:s}".format(text, e)
        return 0.0


def str2number(text):
    if isinstance(text, int):
        return text

    if not isinstance(text, types.StringTypes):
        print "TypeError:{0:s}".format(type(text))
        return 0

    try:

        text = text.lower()

        if text.startswith("0b"):
            return int(text, 2)
        elif text.startswith("0x"):
            return int(text, 16)
        elif text.startswith("0"):
            return int(text, 8)
        elif text == "true":
            return 1
        elif text == "false":
            return 0
        elif text.endswith("k") or text.endswith("kb"):
            return int(text.split("k")[0]) * 1024
        elif text.endswith("m") or text.endswith("mb"):
            return int(text.split("m")[0]) * 1024 * 1024
        else:
            return int(text)

    except ValueError, e:
        print "Str2number error:{0:s}, {1:s}".format(text, e)
        return 0


class BasicDataType(object):
    # 1 byte alignment
    _pack_ = 1

    def cdata(self):
        """Get C-style data"""
        return buffer(self)[:]

    def set_cdata(self, cdata, size):
        """Set C-style data

        :param cdata: data
        :param size: data size
        :return:
        """
        fit = min(size, ctypes.sizeof(self))
        ctypes.memmove(ctypes.addressof(self), cdata, fit)


class BasicTypeLE(BasicDataType, ctypes.LittleEndianStructure):
    pass


class BasicTypeBE(BasicDataType, ctypes.BigEndianStructure):
    pass
