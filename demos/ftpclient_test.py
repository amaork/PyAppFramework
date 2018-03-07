# -*- coding: utf-8 -*-
import socket
from ..protocol.ftp import FTPClient

if __name__ == '__main__':
    address = socket.gethostbyname("speedtest.tele2.net")
    print "Start connect ftp://speedtest.tele2.net({0:s}), please wait...".format(address)

    ftp = FTPClient(address, timeout=60, verbose=True)
    print(ftp.get_file_list("/"))
