# -*- coding: utf-8 -*-

import sys
import ctypes
import struct

sys.path.append("../../")
import protocol.crc16 as crc


if __name__ == "__main__":
    data = 1234
    string = "amaork0123456789"
    buf = ctypes.create_string_buffer(4)
    struct.pack_into('I', buf, 0, data)

    # 9d78
    crc1 = crc.crc16(buf)

    # B251
    crc2 = crc.crc16(string)

    print "Data: 0x{0:x}, crc16: 0x{1:x}, result: {2:b}".format(data, crc1, crc1 == 0x9d78)
    print "String: {0:s}, crc16: 0x{1:x}, result: {2:b}".format(string, crc2, crc2 == 0xb251)
