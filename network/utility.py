# -*- coding: utf-8 -*-
import socket
import concurrent.futures
__all__ = ['get_host_address', 'connect_device', 'scan_lan_port']


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

