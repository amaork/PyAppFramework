# -*- coding: utf-8 -*-
import os
import sys
import time
import typing

import ping3
import ifaddr
import struct
import socket
import platform
import ipaddress
import collections
import concurrent.futures
from threading import Thread
from typing import List, Optional, Dict, Union, Tuple
from ..core.datatype import DynamicObject
__all__ = ['get_system_nic', 'get_address_source_network', 'get_default_network',
           'get_host_address', 'get_broadcast_address', 'get_address_prefix_len',
           'connect_device', 'scan_lan_port', 'scan_lan_alive', 'get_network_ifc',
           'set_keepalive', 'enable_broadcast', 'set_linger_option',
           'enable_multicast', 'join_multicast', 'leave_multicast',
           'create_socket_and_connect', 'wait_device_reboot',
           'tcp_socket_send_data', 'tcp_socket_recv_data', 'tcp_t_section',
           'SocketSingleInstanceLock', 'NicInfo']


class NicInfo(DynamicObject):
    _properties = {'ip', 'name', 'network', 'network_prefix'}
    _check = {
        'ip': lambda x: isinstance(x, str),
        'name': lambda x: isinstance(x, str),
        'network': lambda x: isinstance(x, str),
        'network_prefix': lambda x: isinstance(x, int),
    }


def get_system_nic(ignore_loopback: bool = True) -> Dict[str, NicInfo]:
    interfaces = dict()
    adapters = ifaddr.get_adapters()
    for adapter in adapters:
        for ip in adapter.ips:
            try:
                address = ipaddress.ip_address("{}".format(ip.ip))

                if ignore_loopback and address.is_loopback:
                    continue

                if address.version == 4:
                    network = ipaddress.ip_network("{}/{}".format(address, ip.network_prefix), False)
                    interfaces[adapter.nice_name] = NicInfo(
                        ip=str(address),
                        network=str(network),
                        name=adapter.nice_name,
                        network_prefix=ip.network_prefix
                    )
                    break
            except ValueError:
                continue

    return interfaces


def get_default_network(prefix: int = 24) -> str:
    networks = [x.network for _, x in get_system_nic(ignore_loopback=True).items() if x.network_prefix == prefix]
    return networks[0] if networks else ""


def get_address_prefix_len(ip: str) -> int:
    if '/' in ip:
        try:
            return ipaddress.ip_network(ip, strict=False).prefixlen
        except ValueError:
            return 24

    try:
        address = ipaddress.ip_address(ip)
    except ValueError:
        return 24

    for network, prefix in (
            (ipaddress.IPv4Network('10.0.0.0/8'), 8),
            (ipaddress.IPv4Network('172.16.0.0/12'), 16),
            (ipaddress.IPv4Network('192.168.0.0/16'), 24)
    ):
        if address in network:
            return prefix
    else:
        return 24


def get_address_source_network(ip: str) -> Union[ipaddress.IPv4Network, None]:
    for nic in get_system_nic().values():
        try:
            network = ipaddress.ip_network(nic.network)
            if ipaddress.ip_address(ip) in network.hosts():
                return network
        except ValueError:
            return None

    return None


def get_network_ifc(network: str) -> typing.Optional[NicInfo]:
    interfaces = get_system_nic(ignore_loopback=False)

    for ifc in interfaces.values():
        if ifc.network == network:
            return ifc

    return None


def get_host_address(network: Optional[ipaddress.IPv4Network] = None) -> List[str]:
    try:
        address_set = set()

        try:
            network = ipaddress.ip_network(network, False)
        except ValueError:
            network = list()

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
        return [socket.gethostbyname(socket.gethostname())]


def get_broadcast_address(address: str, network_prefix: int = 24) -> str:
    interface = ipaddress.IPv4Interface("{}/{}".format(address, network_prefix))
    return interface.network.broadcast_address.exploded


def set_keepalive(sock: socket.socket, after_idle_sec: int = 1, interval_sec: int = 1, max_fails: int = 3) -> None:
    """Set TCP keepalive on an open socket.
    It activates after 1 second (after_idle_sec) of idleness,
    then sends a keepalive ping once every 3 seconds (interval_sec),
    and closes the connection after 3 failed ping (max_fails), or 3 seconds
    :param sock: opened tcp socket
    :param after_idle_sec: after #after_idle_sec idleness then send keepalive ping
    :param interval_sec: send keepalive ping every #interval_sec
    :param max_fails: after #max_fails times indicate the connection is lost
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


def enable_broadcast(sock: socket.socket) -> None:
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)


def join_multicast(sock: socket.socket, mcast_group: str, ifc_addr: str):
    option = struct.pack("4s4s", socket.inet_aton(mcast_group), socket.inet_aton(ifc_addr))
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, option)


def leave_multicast(sock: socket.socket,  mcast_group: str, ifc_addr: str):
    option = struct.pack("4s4s", socket.inet_aton(mcast_group), socket.inet_aton(ifc_addr))
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_DROP_MEMBERSHIP, option)


def enable_multicast(sock: socket.socket, ifc_addr: str, loop: bool = False, ttl: int = 2) -> None:
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_IF, socket.inet_aton(ifc_addr))
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_LOOP, int(loop))
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, ttl)


def set_linger_option(sock: socket.socket, onoff: int = 1, linger: int = 0) -> None:
    option = struct.pack("ii", onoff, linger)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, option)


def connect_device(address: str, port: int, timeout: float = 0.03) -> Union[str, None]:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        s.connect((address, port))
        s.close()
        return address
    except (socket.timeout, ConnectionError, TimeoutError):
        return None


def wait_device_reboot(address: str, shutdown_wait: int = 30, reboot_wait: int = 180) -> Tuple[bool, bool]:
    # First wait shutdown
    reboot = False
    shutdown = False
    reboot_result = collections.namedtuple('reboot_result', ['shutdown', 'reboot'])

    # Wait shutdown
    t0 = time.perf_counter()
    while time.perf_counter() - t0 < shutdown_wait:
        if ping3.ping(dest_addr=address, timeout=1) is None:
            shutdown = True
            break

    if not shutdown:
        return reboot_result(shutdown, reboot)

    # Wait reboot
    t0 = time.perf_counter()
    while time.perf_counter() - t0 < reboot_wait:
        if ping3.ping(dest_addr=address, timeout=1) is not None:
            reboot = True
            break

    return reboot_result(shutdown, reboot)


def scan_lan_port(port: int, network: Union[ipaddress.IPv4Network, str] = "",
                  timeout: float = 0.005, max_workers: Optional[int] = None) -> List[str]:
    try:
        network = ipaddress.ip_network(network)
    except ValueError:
        network = get_default_network(prefix=24)
        if not network:
            print("scan_lan_port: invalid network")
            return list()
        else:
            print("scan_lan_port: found multiple nic use {}".format(network))
            network = ipaddress.ip_network(network)

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as pool:
        result = [pool.submit(connect_device, *(str(x), port, timeout)) for x in network.hosts()]

    return [x.result() for x in result if x.result() is not None]


def scan_lan_alive(network: Union[ipaddress.IPv4Network, str] = "",
                   timeout: int = 1, max_workers: int = 256) -> List[str]:
    try:
        network = ipaddress.ip_network(network)
    except ValueError:
        network = get_default_network(prefix=24)
        if not network:
            print("scan_lan_alive: invalid network")
            return list()
        else:
            print("scan_lan_alive: found multiple nic use {}".format(network))
            network = ipaddress.ip_network(network)

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as pool:
        result = [pool.submit(ping3.ping, **DynamicObject(dest_addr=str(x), timeout=timeout).dict)
                  for x in network.hosts()]

    return [str(x) for x, r in zip(network.hosts(), result) if r.result() is not None]


def tcp_socket_send_data(tcp_socket: socket.socket, data: bytes, header: str = '') -> List[int]:
    """Send data to peer

    :param tcp_socket: tcp socket to send data
    :param data: data to send
    :param header: send data with length header
    :return: send data length list
    """
    total_send = 0
    send_length = list()
    data = struct.pack(header, len(data)) + data if header else data

    while total_send < len(data):
        send = tcp_socket.send(data[total_send:])
        if send == 0:
            raise ConnectionError('peer closed')

        total_send += send
        send_length.append(send)

    return send_length


def tcp_socket_recv_data(tcp_socket: socket.socket, length: int, header: str = '') -> bytes:
    """Receive #length specified bytes data until to timeout or peer closed (raise BrokenPipeError)

    :param tcp_socket: tcp socket to receive data
    :param length: expect receive data length
    :param header: receive data with length header
    :return: receive data
    """
    recv_data = bytes()

    # Specified header fmt or length is zero means read length from header
    if header or not length:
        try:
            length = struct.unpack(header, tcp_socket.recv(struct.calcsize(header)))[0]
        except (struct.error, IndexError) as e:
            print(f'tcp_socket_recv_data: {e}(header: {header}, len: {length})')
            return bytes()

    while len(recv_data) < length:
        try:
            data = tcp_socket.recv(length - len(recv_data))
        except socket.timeout:
            return recv_data

        if not data:
            raise BrokenPipeError('peer closed')

        recv_data += data

    return recv_data


def create_socket_and_connect(address: str, port: int, timeout: Union[float, None] = None,
                              recv_buf_size: int = 32 * 1024, retry: int = 3, no_delay: bool = True) -> socket.socket:
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


def tcp_t_section(server: str, data: bytes, expect_len: int, header: str = '>L') -> bytes:
    """connect server send data and recv data then disconnect

    :param server: server <address>:<port>:[timeout in ms] such as "192.168.1.1:1234:3000"
    :param data: data to send
    :param expect_len: expect recv length
    :param header: tx/rx data header format
    :return: receive data
    """
    timeout = 3000

    try:
        address, port, timeout = server.strip().split(':')
    except ValueError:
        address, port = server.strip().split(':')

    try:
        sock = create_socket_and_connect(address, int(port), float(timeout / 1e3))
    except RuntimeError as e:
        print(f'tcp_t_section, connect error: {e}')
        return bytes()

    if sum(tcp_socket_send_data(sock, data, header)) != len(data) + struct.calcsize(header):
        print(f'tcp_t_section, tx error: {server} error')
        sock.close()
        return bytes()

    try:
        return tcp_socket_recv_data(sock, expect_len, header)
    except OSError as e:
        print(f'tcp_t_section, rx error: {e}')
        return bytes()
    finally:
        sock.close()


class SocketSingleInstanceLock(object):
    def __init__(self, port: int):
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
