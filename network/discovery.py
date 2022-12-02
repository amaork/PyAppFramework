# -*- coding: utf-8 -*-
import json
import typing
import socket
import ipaddress
import threading
import collections

from ..core.timer import SwTimer
from ..core.threading import ThreadLockAndDataWrap
from ..core.datatype import CustomEvent, DynamicObject, DynamicObjectDecodeError
from .utility import enable_broadcast, enable_multicast, get_default_network, get_host_address
__all__ = ['ServiceDiscovery', 'ServiceResponse', 'DiscoveryEvent', 'DiscoveryMsg']

DEF_GROUP = '224.1.2.3'
DEF_PORT = 45678


class DiscoveryMsg(DynamicObject):
    _properties = {'service', 'port'}


class DiscoveryEvent(CustomEvent):
    MaxSize = 128
    Type = collections.namedtuple('Type', 'Discovery Response')(*('discovery', 'response'))

    def bytes(self) -> bytes:
        return self.dumps().encode()

    @staticmethod
    def response(msg: DiscoveryMsg, source: str):
        return DiscoveryEvent(type=DiscoveryEvent.Type.Response, data=msg.dumps(), source=source)

    @staticmethod
    def discovery(msg: DiscoveryMsg, source: str):
        return DiscoveryEvent(type=DiscoveryEvent.Type.Discovery, data=msg.dumps(), source=source)


class ServiceDiscovery:
    def __init__(self, service: str, port: int, network: str = get_default_network(),
                 send_interval: int = 1, found_callback: typing.Callable[[str], None] = None, auto_stop: bool = False):
        self._exit = False
        self._auto_stop = auto_stop
        self._callback = found_callback
        self._dev_list = ThreadLockAndDataWrap(set())
        self._msg = DiscoveryMsg(service=service, port=port)
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, 0)
        self._address = get_host_address(ipaddress.IPv4Network(network))[0]
        self._broadcast = ipaddress.IPv4Interface(network).network.broadcast_address.exploded
        self._timer = SwTimer(send_interval, callback=self.timerSendDiscoveryMsg, auto_start=True)
        threading.Thread(target=self.threadReceiveResponse, name='ServiceDiscovery', daemon=True).start()

    def __del__(self):
        self._exit = True

    @property
    def device_list(self) -> typing.List[str]:
        return list(self._dev_list.data)

    def pause(self):
        self._timer.pause()

    def resume(self):
        self._timer.resume()

    def foundCallback(self, address: str):
        if callable(self._callback):
            self._callback(address)

        self._dev_list.data.add(address)

    def timerSendDiscoveryMsg(self):
        msg = DiscoveryEvent.discovery(self._msg, self._address).bytes()
        self._sock.sendto(msg, (DEF_GROUP, DEF_PORT))
        self._sock.sendto(msg, (self._broadcast, DEF_PORT))

    def threadReceiveResponse(self):
        enable_broadcast(self._sock)
        enable_multicast(self._sock, DEF_GROUP)
        self._sock.bind(('', DEF_PORT))
        while not self._exit:
            data, sender = self._sock.recvfrom(DiscoveryEvent.MaxSize)

            try:
                event = DiscoveryEvent(**json.loads(data.decode()))
                if not event.isEvent(DiscoveryEvent.Type.Response):
                    continue

                if DiscoveryMsg(**json.loads(event.data)) == self._msg:
                    self.foundCallback(event.source)
                    if self._auto_stop:
                        self._timer.pause()
            except (TypeError, json.decoder.JSONDecodeError, DynamicObjectDecodeError):
                pass


class ServiceResponse:
    def __init__(self, service: str, port: int, network: str = get_default_network()):
        self._exit = False
        self._msg = DiscoveryMsg(service=service, port=port)
        self._address = get_host_address(ipaddress.IPv4Network(network))[0]
        threading.Thread(target=self.threadResponse, name='ServiceDiscoveryClient', daemon=True).start()

    def __del__(self):
        self._exit = True

    def threadResponse(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, 0)
        sock.bind(('', DEF_PORT))

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
