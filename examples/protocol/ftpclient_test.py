# -*- coding: utf-8 -*-

import sys
import socket
sys.path.append("../../../")

from PyAppFramework.protocol.ftp import FTPClient

if __name__ == '__main__':
    address = socket.gethostbyname("kernel.org")
    print "Start connect ftp://kernel.org({0:s}), please wait...".format(address)

    ftp = FTPClient(address, timeout=60, verbose=True)
    print ftp.get_file_list("/pub/linux/kernel/")