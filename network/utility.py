# -*- coding: utf-8 -*-
import os
import sys
import socket
import concurrent.futures
from threading import Thread
__all__ = ['get_host_address', 'connect_device', 'scan_lan_port', 'SocketSingleInstanceLock']


def get_host_address():
    try:
        for addr in socket.gethostbyname_ex(socket.gethostname())[2]:
            if not addr.startswith("127."):
                return addr

        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 53))
        return s.getsockname()[0]
    except socket.error:
        return socket.gethostbyname(socket.gethostname())


def connect_device(address, port, timeout=0.03):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        s.connect((address, port))
        s.close()
        return address
    except (socket.timeout, ConnectionError, ConnectionRefusedError, ConnectionResetError):
        return None


def scan_lan_port(port, timeout, max_workers=None):
    network_seg = ".".join(get_host_address().split(".")[:-1])
    args = [("{}.{}".format(network_seg, i), port, timeout) for i in range(255)]
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as pool:
        result = [pool.submit(connect_device, *arg) for arg in args]

    return [x.result() for x in result if x.result() is not None]


class SocketSingleInstanceLock(object):
    def __init__(self, port):
        """
        Socket single instance lock, using this make sure that is only one instance running in the same time
        If another instance is running will display running instance path and pid
        :param port: tcp socket listen port, using this as lock port
        """
        try:
            self.__lock_port = port
            self.__lock_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
            self.__lock_socket.bind(("0.0.0.0", port))
            self.__lock_socket.listen(5)
            th = Thread(target=self.lockThread)
            th.setDaemon(True)
            th.start()
        except socket.error:
            self.getMessageFromRunningInstance()

    def lockThread(self):
        while True:
            try:
                new_connection, _ = self.__lock_socket.accept()
                new_connection.send("Another instance is running pid: {}\nPath: {}".format(
                    os.getpid(), os.path.join(os.getcwd(), sys.argv[0])
                ).encode())
                new_connection.shutdown(socket.SHUT_WR)
            except socket.error as error:
                print("{}".format(error))

    def getMessageFromRunningInstance(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
            s.settimeout(0.3)
            s.connect(('127.0.0.1', self.__lock_port))
            msg = s.recv(1024)
            s.close()
            raise RuntimeError(msg.decode())
        except socket.error as err:
            print("{}".format(err))
            raise RuntimeError("Another instance is running")