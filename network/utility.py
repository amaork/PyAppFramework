# -*- coding: utf-8 -*-
import os
import sys
import time
import struct
import socket
import platform
import ipaddress
import concurrent.futures
from threading import Thread
__all__ = ['get_host_address', 'get_broadcast_address', 'connect_device', 'scan_lan_port', 'set_keepalive',
           'enable_broadcast', 'enable_multicast', 'set_linger_option', 'create_socket_and_connect',
           'SocketSingleInstanceLock']


def get_host_address(network=None):
    try:
        address_set = set()
        network = network or list()
        for address in socket.gethostbyname_ex(socket.gethostname())[2]:
            if not ipaddress.IPv4Address(address).is_loopback:
                address_set.add(address)

        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 53))
        address_set.add(s.getsockname()[0])

        for address in address_set:
            if ipaddress.IPv4Address(address) in network:
                return [address]
        return list(address_set)
    except socket.error:
        return socket.gethostbyname(socket.gethostname())


def get_broadcast_address(address, nbits=24):
    interface = ipaddress.IPv4Interface("{}/{}".format(address, nbits))
    return interface.network.broadcast_address.exploded


def set_keepalive(sock, after_idle_sec=1, interval_sec=1, max_fails=3):
    """Set TCP keepalive on an open socket.
    It activates after 1 second (after_idle_sec) of idleness,
    then sends a keepalive ping once every 3 seconds (interval_sec),
    and closes the connection after 3 failed ping (max_fails), or 3 seconds
    :param sock: opened tcp socket
    :param after_idle_sec: after #after_idle_sec idleness then send keepalive ping
    :param interval_sec: send keepalive ping every #interval_sec
    :param max_fails: after #max_fails times indicate the connection is lose
    :return:
    """
    _system = platform.system().lower()
    if _system == "linux":
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        sock.setsockopt(socket.SOL_TCP, socket.TCP_KEEPIDLE, after_idle_sec)
        sock.setsockopt(socket.SOL_TCP, socket.TCP_KEEPINTVL, interval_sec)
        sock.setsockopt(socket.SOL_TCP, socket.TCP_KEEPCNT, max_fails)
    elif _system == "darwin":
        TCP_KEEPALIVE = 0x10
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        sock.setsockopt(socket.IPPROTO_TCP, TCP_KEEPALIVE, interval_sec)
    elif _system == "windows":
        sock.ioctl(socket.SIO_KEEPALIVE_VALS, (1, after_idle_sec * 1000, interval_sec * 1000))


def enable_broadcast(sock):
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)


def enable_multicast(sock, mcast_group):
    option = struct.pack("4sL", socket.inet_aton(mcast_group), socket.INADDR_ANY)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, option)


def set_linger_option(sock, onoff=1, linger=0):
    option = struct.pack("ii", onoff, linger)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, option)


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


def create_socket_and_connect(address, port, timeout, recv_buf_size=32 * 1024, retry=3, no_delay=True):
    times = 0
    while times < retry:
        try:
            # Create a tcp socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)

            # Set timeout
            sock.settimeout(timeout)

            # Connect to specified address and port
            sock.connect((address, port))

            # Set linger option
            set_linger_option(sock)

            # Disable Nagle algorithm
            sock.setsockopt(socket.SOL_TCP, socket.TCP_NODELAY, no_delay)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, recv_buf_size)
            return sock
        except socket.error as error:
            print("Create socket and connect to {}:{} error:{}".format(address, port, error))
            times += 1
            if times < retry:
                time.sleep(times)
            continue

    raise RuntimeError("Connect to {}:{} failed".format(address, port))


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
