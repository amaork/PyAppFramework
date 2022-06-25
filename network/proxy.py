# -*- coding: utf-8 -*-
import time
import socket
import selectors
import threading
import collections
from ..core.datatype import DynamicObject, ip4_check, port_check
from .utility import create_socket_and_connect, tcp_socket_send_data
__all__ = ['SocketPair', 'ProxyAttribute', 'TransparentProxy']
SocketPair = collections.namedtuple('SocketPair', 'server client')


class ProxyAttribute(DynamicObject):
    _properties = {'address', 'port', 'timeout', 'recv_buf_size'}
    _check = {
        'address': ip4_check,
        'port': port_check
    }

    def __init__(self, **kwargs):
        kwargs.setdefault('timeout', None)
        kwargs.setdefault('recv_buf_size', 1024)
        super(ProxyAttribute, self).__init__(**kwargs)


class TransparentProxy:
    def __init__(self, attribute: ProxyAttribute):
        self._clients = list()
        self.attribute = attribute
        self._selector = selectors.DefaultSelector()
        threading.Thread(target=self.threadEventHandle, daemon=True).start()
        threading.Thread(target=self.threadAcceptHandle, daemon=True).start()

    def register(self, sock_pair: SocketPair):
        self._clients.append(sock_pair)
        for sock in sock_pair:
            self._selector.register(sock, selectors.EVENT_READ)

    def unregister(self, sock_pair: SocketPair):
        self._clients.remove(sock_pair)
        for sock in sock_pair:
            self._selector.unregister(sock)
            sock.close()

    def relay(self, rx: socket.socket, tx: socket.socket):
        """Real work recv client/server data send to other side if channel"""
        try:
            payload = rx.recv(self.attribute.recv_buf_size)
        except socket.timeout:
            return
        except (BrokenPipeError, ConnectionResetError) as e:
            print(rx.getsockname(), f'{e}')
            payload = b''

        if not payload:
            print('Closed')
            self.unregister(SocketPair(tx, rx))
            return

        tcp_socket_send_data(tx, payload)

    def threadEventHandle(self):
        """Event handle, watch clients socket readable events and handle it"""
        while True:
            if not self._selector.get_map():
                time.sleep(0.01)
                continue

            for key, mask in self._selector.select():
                # Find out which pair of client
                for sock_pair in self._clients:
                    if key.fileobj in sock_pair:
                        rx, tx = sock_pair if key.fileobj == sock_pair[0] else sock_pair[::-1]
                        self.relay(rx, tx)

    def threadAcceptHandle(self):
        """Create transparent proxy server, accept client connect, make a channel between real server and client"""
        listen_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
        listen_socket.bind(('', self.attribute.port))
        listen_socket.listen(5)

        while True:
            print('Before accept')
            client = listen_socket.accept()[0]
            print(f'Client: {client.getpeername()}')

            try:
                # Connect server immediately
                server = create_socket_and_connect(**self.attribute.dict)
                print(f'Server: {server.getpeername()}')
            except RuntimeError:
                # Connect failed close client too
                client.close()
                continue

            # Register to proxy handle list
            self.register(SocketPair(server=server, client=client))
