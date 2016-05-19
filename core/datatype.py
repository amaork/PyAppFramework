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

    def set_cdata(self, cdata):
        """Set C-style data

        :param cdata: data
        :return:
        """
        size = len(cdata)
        if size != ctypes.sizeof(self):
            return False

        ctypes.memmove(ctypes.addressof(self), cdata, size)
        return True


class BasicTypeLE(BasicDataType, ctypes.LittleEndianStructure):
    def __eq__(self, other):
        if not isinstance(other, BasicTypeLE):
            return False
        return self.cdata() == other.cdata()

    def __ne__(self, other):
        return not self.__eq__(other)


class BasicTypeBE(BasicDataType, ctypes.BigEndianStructure):
    def __eq__(self, other):
        if not isinstance(other, BasicTypeBE):
            return False
        return self.cdata() == other.cdata()

    def __ne__(self, other):
        return not self.__eq__(other)
