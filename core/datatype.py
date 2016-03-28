# -*- coding: utf-8 -*-

import ctypes


class BasicDataType(object):
    # 1 byte alignment
    _pack_ = 1

    def cdata(self):
        """Get C-style data

        :return:
        """
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
