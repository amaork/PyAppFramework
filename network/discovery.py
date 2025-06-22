# -*- coding: utf-8 -*-
import json
import time
import typing
import socket
import ipaddress
import threading
import collections
from ..core.timer import Task, Tasklet
from ..core.threading import ThreadLockAndDataWrap, ThreadSafeBool
from ..core.datatype import CustomEvent, DynamicObject, DynamicObjectDecodeError
from .utility import enable_broadcast, enable_multicast, get_default_network, get_host_address
__all__ = ['ServiceDiscovery', 'ServiceResponse', 'DiscoveryEvent', 'DiscoveryMsg']

DEF_GROUP = '224.1.2.3'
DEF_PORT = 45678


class DiscoveryMsg(DynamicObject):
    _properties = {'service', 'port'}


class DiscoveryEvent(CustomEvent):
    MaxSize = 128
    Type = collections.namedtuple(
        'Type', 'Discovery Response Online Offline Error'
    )(*('discovery', 'response', 'online', 'offline', 'error'))

    def bytes(self) -> bytes:
        return self.dumps().encode()

    @staticmethod
    def error():
        return DiscoveryEvent(type=DiscoveryEvent.Type.Error)

    @staticmethod
    def response(msg: DiscoveryMsg, source: str):
        return DiscoveryEvent(type=DiscoveryEvent.Type.Response, data=msg.dumps(), source=source)

    @staticmethod
    def discovery(msg: DiscoveryMsg, source: str):
        return DiscoveryEvent(type=DiscoveryEvent.Type.Discovery, data=msg.dumps(), source=source)


class ServiceDiscovery:
    def __init__(self, service: str, port: int,
                 event_callback: typing.Callable[[DiscoveryEvent], None], network: str = get_default_network(),
                 send_interval: float = 2.0, auto_stop: bool = False, discovery_timeout: float = 0.0):
        self._exit = False
        self._auto_stop = auto_stop
        self._send_interval = send_interval
        self._event_callback = event_callback
        self._stop_sniff = ThreadSafeBool(True)
        self._discovery_timeout = discovery_timeout
        self._send_discovery = ThreadSafeBool(False)
        self._dev_list = ThreadLockAndDataWrap(dict())
        self._msg = DiscoveryMsg(service=service, port=port)
        self._address = get_host_address(ipaddress.IPv4Network(network))[0]
        self._broadcast = ipaddress.IPv4Interface(network).network.broadcast_address.exploded

        self._tasklet = Tasklet(1.0, max_workers=2, name=f'{self.__class__.__name__}')
        self._tasklet.add_task(Task(self.taskOfflineCheck, timeout=3.0, periodic=True))
        self._tasklet.add_task(Task(self.taskReceiveResponse, timeout=0.0), immediate=True)

    def __del__(self):
        self._exit = True

    @property
    def device_list(self) -> typing.List[str]:
        return list(self._dev_list.data.keys())

    def pause(self):
        self._send_discovery.clear()

    def resume(self):
        self._send_discovery.set()
        self._tasklet.add_task(Task(self.taskDiscoveryTimeout, timeout=5.0))

    def setNetwork(self, network: str):
        self._stop_sniff.set()
        self._address = get_host_address(ipaddress.IPv4Network(network))[0]
        self._broadcast = ipaddress.IPv4Interface(network).network.broadcast_address.exploded
        self._tasklet.add_task(Task(self.taskDiscoveryTimeout, timeout=self._discovery_timeout))

    def foundCallback(self, address: str):
        if not address:
            return
        self._dev_list.data[address] = time.time()
        self._event_callback(DiscoveryEvent(type=DiscoveryEvent.Type.Online, data=address))

    def taskDiscoveryTimeout(self):
        if not self._discovery_timeout:
            return

        if not self._send_discovery:
            return

        if not self._dev_list.data:
            self._event_callback(DiscoveryEvent.error())

    def taskOfflineCheck(self):
        if not self._send_discovery:
            return

        # Filter 3 seconds do not send discovery msg device
        offline_device = [k for k, v in self._dev_list.data.items() if time.time() - v > 3.0]
        for address in offline_device:
            self._dev_list.data.pop(address)
            self._event_callback(DiscoveryEvent(type=DiscoveryEvent.Type.Offline, data=address))

    def taskSendDiscovery(self, sock: socket.socket, msg: bytes):
        if self._send_discovery and not self._stop_sniff:
            try:
                sock.sendto(msg, (DEF_GROUP, DEF_PORT))
            except OSError:
                pass

            try:
                sock.sendto(msg, (self._broadcast, DEF_PORT))
            except OSError:
                pass

    def taskReceiveResponse(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, 0)

        while not self._exit:
            enable_broadcast(sock)
            enable_multicast(sock, self._address)
            sock.settimeout(self._send_interval)

            try:
                sock.bind((self._address, DEF_PORT))
            except OSError as e:
                print(f'{self._address}:{DEF_PORT},{e}')
                sock.bind((self._address, 0))

            while not self._exit and not self._stop_sniff:
                try:
                    data, sender = sock.recvfrom(DiscoveryEvent.MaxSize)
                except socket.timeout:
                    continue

                try:
                    event = DiscoveryEvent(**json.loads(data.decode()))
                    if not event.isEvent(DiscoveryEvent.Type.Response):
                        continue

                    if DiscoveryMsg(**json.loads(event.data)) == self._msg:
                        # Just incase event.source is empty
                        source = event.source or sender[0]
                        self.foundCallback(source)
                        if self._auto_stop:
                            self.pause()
                except (TypeError, json.decoder.JSONDecodeError, DynamicObjectDecodeError):
                    pass

            sock.close()
            self._stop_sniff.clear()
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, 0)
            msg = DiscoveryEvent.discovery(self._msg, self._address).bytes()
            self._tasklet.add_task(Task(self.taskSendDiscovery, self._send_interval, args=(sock, msg), periodic=True))
            print(f'Restart sniff: {self._address}')


class ServiceResponse:
    def __init__(self, service: str, port: int, error_callback: typing.Callable, network: str = get_default_network()):
        self._exit = False
        self._error_callback = error_callback
        self._msg = DiscoveryMsg(service=service, port=port)
        self._address = get_host_address(ipaddress.IPv4Network(network))[0]
        threading.Thread(target=self.threadResponse, name='ServiceDiscoveryClient', daemon=True).start()

    def __del__(self):
        self._exit = True

    def threadResponse(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, 0)
        try:
            sock.bind(('', DEF_PORT))
        except OSError as e:
            print(f'{self.__class__.__name__}: {e}')
            self._error_callback()
            return

        while not self._exit:
            data, sender = sock.recvfrom(DiscoveryEvent.MaxSize)

            try:
                event = DiscoveryEvent(**json.loads(data.decode()))
                if not event.isEvent(DiscoveryEvent.Type.Discovery):
                    continue

                if DiscoveryMsg(**json.loads(event.data)) == self._msg:
                    sock.sendto(DiscoveryEvent.response(self._msg, self._address).bytes(), (event.source, DEF_PORT))
            except (TypeError, json.decoder.JSONDecodeError, DynamicObjectDecodeError):
                pass
