# -*- coding: utf-8 -*-

import sys
import argparse
from ..protocol.serialport import SerialTransferProtocol, SerialPort, SerialTransferError

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-p", "--port", help="Serial port name", default="COM17")
    parser.add_argument("-t", "--timeout", help="Serial port timeout", default=1)
    parser.add_argument("-b", "--baudrate", help="Serial port baudrate", default=38400)
    args = vars(parser.parse_args())

    port = SerialPort(args.get("port"), args.get("baudrate"), args.get("timeout"))
    serial_transaction = SerialTransferProtocol(port.write, port.read)

    # Read test
    try:

        global_data, package_data = serial_transaction.recv(lambda x: print("Read:{0:.02f}%".format(x)))
        print("Read success: global data size: {0:d}, package data size: {1:d}".format(
            len(global_data), len(package_data)))

        # Write test
        if serial_transaction.send(global_data, package_data, lambda x: print("Write:{0:.02f}%".format(x))):
            print("Write success!")

    except SerialTransferError as error:
        print("Serial Transfer data error:{0:s}".format(error))
        sys.exit(-1)
