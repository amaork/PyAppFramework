# -*- coding: utf-8 -*-
import json
import time
import random
import typing
import inspect
import collections
import multiprocessing
from ..misc.debug import LoggerWrap, JsonSettingsWithDebugCode
from ..core.datatype import CustomEvent, FrozenJSON, DynamicObject, DynamicObjectDecodeError
from .transmit import TCPSocketTransmit, TCPClientTransmit, TransmitException, TransmitWarning, TCPServerTransmitHandle
__all__ = ['SRPCMessage', 'SRPCAPIWrap', 'SRPCSettings', 'SRPCException', 'SRPCServer',
           'send_msg_to_client', 'send_msg_to_server', 'start_srpc_server']
HandleType = typing.Tuple[typing.Callable, bool]


class SRPCException(Exception):
    pass


class SRPCMessage(CustomEvent):
    """Basic SRPC Message"""
    Type = collections.namedtuple('Type', 'Query Error Echo Result Exit')(
        *'query error echo result exit'.split()
    )

    def __init__(self, **kwargs):
        kwargs.setdefault('data', dict())
        super(SRPCMessage, self).__init__(**kwargs)

    @classmethod
    def exit(cls):
        """Ask server exit"""
        return cls(type=cls.Type.Exit)

    @classmethod
    def query(cls):
        """Query server version"""
        return cls(type=cls.Type.Query)

    @classmethod
    def error(cls, error: str):
        """Send error message to client"""
        return cls(type=cls.Type.Error, data=error)

    @classmethod
    def result(cls, ret: typing.Any):
        """Send result message to client"""
        return cls(type=cls.Type.Result, data=json.dumps(ret))

    @classmethod
    def echo(cls, msg: str, timeout: float = 0.1):
        """Client ask server echo after timeout delay"""
        return cls(type=cls.Type.Echo, data=dict(wait=timeout, message=msg))


class SRPCAPIWrap:
    def __init__(self, client: TCPSocketTransmit, api_info: str, logger: LoggerWrap):
        self.info = api_info
        self.client = client
        self.logger = logger
        self.tag = random.randint(0, 999999999)

    def __enter__(self):
        self.logger.debug(f'[S{self.tag:09d}]: {self.info}')
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.logger.debug(f'[E{self.tag:09d}]: {self.info}')
        if exc_type:
            frame = inspect.stack()[1][0]
            info = inspect.getframeinfo(frame)
            stack_info = f'filename: {info.filename}\rlineno: {info.lineno}\nfunction: {info.function}\n'
            error_info = f'Exception:\n{exc_type} {exc_val} {exc_tb}\n\nStack:\n{stack_info}\nDebug info:\n{self.info}'
            send_msg_to_client(self.client, SRPCMessage.error(error_info))


class SRPCSettings(JsonSettingsWithDebugCode):
    _default_path = 'srpc.json'
    _properties = {'listen_port', 'timeout', 'max_concurrent', 'debug_code', 'app_path', 'launch_cmd'}

    @classmethod
    def default(cls) -> DynamicObject:
        return SRPCSettings(
            timeout=120.0,
            listen_port=8000,
            max_concurrent=8, debug_code='',
            app_path='server.exe', launch_cmd='start /b {}',
        )

    def is_cmd_mode(self) -> bool:
        return self.is_debug_enabled('__cmd_mode__')

    def is_api_debug_enabled(self) -> bool:
        return self.is_debug_enabled('__debug_api__')


def _print_msg(client: TCPSocketTransmit, msg: str, out: bool = False, verbose: bool = False):
    if verbose:
        print(f'{client.address} {"<<<" if out else ">>>"} {msg}')


def send_msg_to_client(client: TCPSocketTransmit, msg: SRPCMessage, error: typing.Callable[[str], None] = print):
    try:
        _print_msg(client, msg.dumps(), True)
        client.tx(msg.dumps().encode())
    except (TransmitException, TransmitWarning) as e:
        error(f'send_msg_to_client: {e}({client.address}, {msg})')


def send_msg_to_server(msg: SRPCMessage, server: TCPClientTransmit.Address, timeout: float) -> typing.Any:
    """Send message to server and get result, otherwise raise RuntimeError"""
    client = TCPClientTransmit(with_length=True)

    try:
        client.connect(server, timeout=timeout)
    except TransmitException:
        raise SRPCException('SRPCServer do not run')

    try:
        client.tx(f'{msg}'.encode())
        result = DynamicObject(**json.loads(client.rx(0).decode()))
    except (TransmitException, TransmitWarning) as e:
        raise SRPCException(e)

    if result.type == SRPCMessage.Type.Result:
        return json.loads(result.data)
    else:
        raise SRPCException(result.data)


def _handle_client(client: TCPSocketTransmit, version: str,
                   stop_flag: multiprocessing.Event, msg_cls: typing.Type[SRPCMessage],
                   register_handle: typing.Dict[str, HandleType], extra_arg: typing.Tuple[str, typing.Any]):
    while True:
        try:
            req = client.rx(0)
            _print_msg(client, req.decode())

            if not req:
                break

            try:
                msg = msg_cls(**json.loads(req.decode()))
            except (json.decoder.JSONDecodeError, DynamicObjectDecodeError) as decode_err:
                send_msg_to_client(client, msg_cls.error(f'{decode_err}'))
                continue

            # SRPC special handle(exit/echo/query)
            if msg.type == msg_cls.Type.Exit:
                send_msg_to_client(client, msg_cls.result(True))
                client.disconnect()
                stop_flag.set()
                break
            elif msg.type == msg_cls.Type.Echo:
                echo = FrozenJSON(msg.data)
                time.sleep(echo.wait)
                send_msg_to_client(client, msg_cls.result(echo.message))
            elif msg.type == msg_cls.Type.Query:
                send_msg_to_client(client, msg_cls.result(version))
            else:
                # User defined handle
                handle, required_extra_arg = register_handle.get(msg.type)

                if not callable(handle):
                    send_msg_to_client(client, msg_cls.error(f'invalid msg: {msg}'))
                    client.disconnect()
                else:
                    if required_extra_arg and extra_arg and len(extra_arg) == 2:
                        extra_arg_name, extra_arg_value = extra_arg
                        msg.data.update({extra_arg_name: extra_arg_value})

                    handle(msg.data, client)
        except TransmitWarning as warning:
            _print_msg(client, f'warning:{warning}')
        except TransmitException as exception:
            _print_msg(client, f'disconnect:{exception}')
            break


def _handle_new_connection(client: TCPSocketTransmit, version: str,
                           stop_flag: multiprocessing.Event, msg_cls: typing.Type[SRPCMessage],
                           handles: typing.Dict[str, HandleType], extra_arg: typing.Tuple[str, typing.Any]):
    multiprocessing.Process(
        target=_handle_client,
        kwargs=dict(
            client=client, version=version, stop_flag=stop_flag,
            msg_cls=msg_cls, register_handle=handles, extra_arg=extra_arg
        ), daemon=True
    ).start()


class SRPCServer(TCPServerTransmitHandle):
    def __init__(self, verbose: bool = False):
        super(SRPCServer, self).__init__(_handle_new_connection, with_length=True, processing=True, verbose=verbose)


def start_srpc_server(address: TCPSocketTransmit.Address,
                      max_concurrent: int, version: str, msg_cls: typing.Type[SRPCMessage],
                      handles: typing.Dict[str, HandleType], extra_arg: typing.Tuple[str, typing.Any] = None,
                      wait_forever: bool = True, verbose: bool = False
                      ) -> typing.Tuple[SRPCServer, multiprocessing.Event]:
    """Start a simple RPC server

    :param address: server listen host and port
    :param max_concurrent: server max concurrent number
    :param version: server version string
    :param msg_cls: rpc message class
    :param handles: rpc message handles
    :param extra_arg: handle extra arg, (arg name, arg value)
    :param wait_forever: wait forever set this as true
    :param verbose: server enable verbose print
    :return: SRPCServer instance and stop server flag
    """
    stop_flag = multiprocessing.Event()
    server = SRPCServer(verbose=verbose)

    try:
        server.start(
            address, max_concurrent,
            kwargs=dict(stop_flag=stop_flag, msg_cls=msg_cls, version=version, handles=handles, extra_arg=extra_arg)
        )
    except Exception as e:
        stop_flag.set()
        print(f'Start SRPC server failed: {e}')
    else:
        print(f'SRPC server started: {address}, max_concurrent: {max_concurrent}')

        if wait_forever:
            while server.is_running() and not stop_flag.is_set():
                time.sleep(1)

            print('SRPC server exit!!!!')

    return server, stop_flag
