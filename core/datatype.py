# -*- coding: utf-8 -*-
import math
import json
import ctypes
from typing import Tuple, List, Union
import xml.etree.ElementTree as XmlElementTree
__all__ = ['BasicDataType', 'BasicTypeLE', 'BasicTypeBE', 'ComparableXml',
           'DynamicObject', 'DynamicObjectError', 'DynamicObjectDecodeError', 'DynamicObjectEncodeError',
           'str2float', 'str2number', 'resolve_number', 'ip4_check']


def resolve_number(number: float, decimals: int) -> Tuple[int, int]:
    """
    resolve_number to fractional and integer part
    10.3 ==> 10 3
    10.323 ==> 10 232
    :param number: number to resolve
    :param decimals: number decimals
    :return:  integer and fractional
    """
    fractional, integer = math.modf(number)
    return int(integer), int(round(math.pow(10, decimals) * fractional))


def str2float(text: Union[str, int, float]) -> float:
    if isinstance(text, (int, float)):
        return text

    if not isinstance(text, str):
        return 0

    try:
        return float(text)
    except ValueError:
        return 0.0


def str2number(text: Union[str, bool, int, float]) -> int:
    if isinstance(text, (bool, int, float)):
        return text

    if not isinstance(text, str):
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

    except ValueError:
        return 0


def ip4_check(address: str) -> bool:
    try:
        data = address.split(".")
        if len(data) != 4:
            return False

        for num in data:
            if not (0 <= int(num) < 255):
                return False

        return True
    except (ValueError, AttributeError):
        return False


class BasicDataType(ctypes.Structure):
    # 1 byte alignment
    _pack_ = 1

    def __repr__(self):
        return self.cdata().hex()

    def cdata(self) -> bytes:
        """Get C-style data"""
        return ctypes.string_at(ctypes.addressof(self), ctypes.sizeof(self))

    def set_cdata(self, cdata: bytes):
        """Set C-style data

        :param cdata: data
        :return:
        """
        size = len(cdata)
        if size != ctypes.sizeof(self):
            return False

        ctypes.memmove(ctypes.addressof(self), cdata, size)
        return True

    def set_cstr(self, offset: int, maxsize: int, data: Union[str, bytes]):
        if data and offset + len(data) <= ctypes.sizeof(self):
            try:
                ctypes.memmove(ctypes.addressof(self) + offset, data.encode(), min(len(data), maxsize))
            except AttributeError:
                ctypes.memmove(ctypes.addressof(self) + offset, data, min(len(data), maxsize))


class BasicTypeLE(BasicDataType, ctypes.LittleEndianStructure):
    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        return self.cdata() == other.cdata()

    def __ne__(self, other):
        return not self.__eq__(other)


class BasicTypeBE(BasicDataType, ctypes.BigEndianStructure):
    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        return self.cdata() == other.cdata()

    def __ne__(self, other):
        return not self.__eq__(other)


class DynamicObjectError(Exception):
    pass


class DynamicObjectEncodeError(DynamicObjectError):
    pass


class DynamicObjectDecodeError(DynamicObjectError):
    pass


class DynamicObject(object):
    _check = dict()
    _properties = set()

    def __init__(self, **kwargs):
        try:
            for key in self._properties:
                if kwargs.get(key) is None:
                    raise KeyError("do not found key:{!r}".format(key))

            self.__dict__.update(**kwargs)

        except (TypeError, KeyError, ValueError) as e:
            raise DynamicObjectDecodeError("Decode {!r} error:{}".format(self.__class__.__name__, e))

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False

        return self.__dict__ == other.__dict__

    def __len__(self):
        return len(self._properties)

    def __repr__(self):
        return self.dumps()

    def __iter__(self):
        for key in sorted(self.__dict__.keys()):
            yield key

    def __getattr__(self, name):
        try:
            return self.__dict__[name]
        except KeyError:
            msg = "'{0}' object has no attribute '{1}'"
            raise AttributeError(msg.format(type(self).__name__, name))

    @property
    def dict(self) -> dict:
        return self.__dict__.copy()

    @classmethod
    def properties(cls) -> List[str]:
        return list(cls._properties)

    def xml(self, tag: str) -> XmlElementTree.Element:
        element = XmlElementTree.Element(tag)
        for k, v in self.dict.items():
            element.set("{}".format(k), "{}".format(v))
        return element

    def dumps(self) -> str:
        """Encode data to a dict string

        :return:
        """
        return json.dumps(self.__dict__)

    def update(self, data):
        if not isinstance(data, (dict, DynamicObject)):
            raise DynamicObjectEncodeError('DynamicObject update require {!r} or {!r} not {!r}'.format(
                dict.__name__, DynamicObject.__name__, data.__class__.__name__))

        data = data.dict if isinstance(data, DynamicObject) else data
        for k, v in data.items():
            if k not in self._properties:
                raise DynamicObjectEncodeError("Unknown key: {}".format(k))

            if not isinstance(v, type(self.__dict__[k])):
                raise DynamicObjectEncodeError("New value {!r} type is not matched: new({!r}) old({!r})".format(
                    k, v.__class__.__name__, self.__dict__[k].__class__.__name__))

            if k in self._check and hasattr(self._check.get(k), "__call__") and not self._check.get(k)(v):
                raise DynamicObjectEncodeError("Key {!r} new value {!r} check failed".format(k, v))

            self.__dict__[k] = v


class ComparableXml(XmlElementTree.Element):
    def __init__(self, **kwargs):
        super(ComparableXml, self).__init__(**kwargs)

    def __eq__(self, other):
        return self.xml2string(self) == self.xml2string(other)

    def __ne__(self, other):
        return not self.__eq__(other)

    @staticmethod
    def string_strip(data: str) -> Union[str, None]:
        if not isinstance(data, str):
            return None
        
        return "".join([s.strip() for s in data.split("\n")])

    @staticmethod
    def xml2string(xml: XmlElementTree.Element, encode="utf-8") -> Union[str, None]:
        """Xml to string with specified encode

        :param xml: xml Element object
        :param encode: encode type
        :return: string
        """
        if not isinstance(xml, XmlElementTree.Element):
            print("xml2string error is not xml element object")
            return None

        data = XmlElementTree.tostring(xml, encode).strip()
        return ComparableXml.string_strip(data.decode())

    @staticmethod
    def string2xml(data: str) -> Union[XmlElementTree.Element, None]:
        """String to xml Element object

        :param data: string with xml element
        :return: xml Element object
        """
        if not isinstance(data, str):
            print("string2xml error is not a valid string")
            return None

        data = ComparableXml.string_strip(data)
        return XmlElementTree.fromstring(data)
