# -*- coding: utf-8 -*-
import ctypes
import struct
import unittest
from ..protocol.crc16 import *


class CRC16Test(unittest.TestCase):
    def testCStringBuffer(self):
        data = 1234
        buf = ctypes.create_string_buffer(4)
        struct.pack_into('I', buf, 0, data)
        self.assertEqual(crc16(buf.raw), 0x9d78)

    def testString(self):
        string = "amaork0123456789"
        self.assertEqual(crc16(string.encode()), 0xb251)

    def testType(self):
        with self.assertRaises(TypeError):
            crc16("1212")

        with self.assertRaises(TypeError):
            crc16(123)


if __name__ == "__main__":
    unittest.main()
