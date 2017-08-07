# -*- coding: utf-8 -*-
from __future__ import print_function
import sys
import argparse
from ..protocol.serialport import SerialTransactionProtocol, SerialPort

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-p", "--port", help="Serial port name", default="COM17")
    parser.add_argument("-t", "--timeout", help="Serial port timeout", default=1)
    parser.add_argument("-b", "--baudrate", help="Serial port baudrate", default=38400)
    args = vars(parser.parse_args())

    port = SerialPort(args.get("port"), args.get("baudrate"), args.get("timeout"))
    serial_transaction = SerialTransactionProtocol(port.send, port.recv)

    # Read test
    result, data = serial_transaction.read(lambda x: print("Read:{}%".format(x)))
    if not result:
        print("Read error:{0:s}".format(data))
        sys.exit(-1)

    global_data, package_data = data[0], data[1]
    print("Read success: global data size: {0:d}, package data size: {1:d}".format(len(global_data), len(package_data)))

    # Write test
    result, error = serial_transaction.write(global_data, package_data, lambda x: print("Write:{}%".format(x)))
    if not result:
        print("Write error:{0:s}".format(error))
        sys.exit(-1)

    print("Write success!")
