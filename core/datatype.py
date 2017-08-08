# -*- coding: utf-8 -*-

import json
import types
import ctypes
import xml.etree.ElementTree as XmlElementTree

__all__ = ['BasicDataType', 'BasicTypeLE', 'BasicTypeBE', 'DynamicObject', 'ComparableXml',
           'str2float', 'str2number',
           'new_class', 'new_instance',
           'ip4_check']


def str2float(text):
    if isinstance(text, (int, long, float)):
        return text

    if not isinstance(text, types.StringTypes):
        print "TypeError:{0:s}".format(type(text))
        return 0

    try:

        return float(text)

    except StandardError, e:
        print "Str2float error:{0:s}, {1:s}".format(text, e)
        return 0.0


def str2number(text):
    if isinstance(text, (bool, int, long, float)):
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

    except StandardError, e:
        print "Str2number error:{0:s}, {1:s}".format(text, e)
        return 0


def new_class(name):
    if not isinstance(name, str):
        raise TypeError("Class name TypeError:{0:s}".format(type(name)))

    parts = name.split('.')
    module = ".".join(parts[:-1])
    cls = __import__(module)
    for component in parts[1:]:
        cls = getattr(cls, component)

    return cls


def new_instance(name, *args, **kwargs):
    cls = new_class(name)
    return cls(*args, **kwargs)


def ip4_check(addr):
    try:

        data = addr.split(".")
        if len(data) != 4:
            return False

        for num in data:
            if not (0 <= int(num) < 255):
                return False

        return True

    except (ValueError, AttributeError):

        return False


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


class DynamicObject(object):
    _properties = ()

    def __init__(self, **kwargs):
        self.__dict__.update(**kwargs)

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False

        return self.__dict__ == other.__dict__

    def __len__(self):
        return len(self._properties)

    def __str__(self):
        return self.encode()

    def __iter__(self):
        for key in sorted(self.__dict__.keys()):
            yield key

    def __getattr__(self, name):
        try:
            return self.__dict__[name]
        except KeyError:
            msg = "'{0}' object has no attribute '{1}'"
            raise AttributeError(msg.format(type(self).__name__, name))

    def decode(self, data):
        """Decode data

        :param data: encoded data, should be a str
        :return: success return data dict else NONE
        """
        if not isinstance(data, str):
            return None

        try:

            dict_ = json.loads(data)
            if not isinstance(dict_, dict):
                return None

            for key in self._properties:
                if dict_.get(key) is None:
                    print "{0:s} Unknown key:{1:s}".format(self.__class__, key)
                    return None

            return dict_

        except ValueError, e:
            print "Decode object '{0}' has error:{1}".format(type(self), e)
            return None

    def encode(self):
        """Encode data to a dict string

        :return:
        """
        return json.dumps(self.__dict__)


class ComparableXml(XmlElementTree.Element):
    def __init__(self, **kwargs):
        super(ComparableXml, self).__init__(**kwargs)

    def __eq__(self, other):
        return self.xml2string(self) == self.xml2string(other)

    def __ne__(self, other):
        return not self.__eq__(other)

    @staticmethod
    def string_strip(data):
        if not isinstance(data, str):
            return None

        return "".join([s.strip() for s in data.split("\n")])

    @staticmethod
    def xml2string(xml, encode="utf-8"):
        """Xml to string with specified encode

        :param xml: xml Element object
        :param encode: encode type
        :return: string
        """
        if not isinstance(xml, XmlElementTree.Element):
            print "xml2string error is not xml element object"
            return None

        data = XmlElementTree.tostring(xml, encode).strip()
        return ComparableXml.string_strip(data)

    @staticmethod
    def string2xml(data):
        """String to xml Element object

        :param data: string with xml element
        :return: xml Element object
        """
        if not isinstance(data, str):
            print "string2xml error is not a valid string"
            return None

        data = ComparableXml.string_strip(data)
        return XmlElementTree.fromstring(data)
