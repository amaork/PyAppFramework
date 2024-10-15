# -*- coding: utf-8 -*-
import abc
import time
import typing
from threading import Thread
import google.protobuf.message as message
from google.protobuf.json_format import MessageToDict, MessageToJson

from ..core.timer import Task, Tasklet
from ..misc.settings import UiLogMessage
from .template import CommunicationEvent, CommunicationObject
from .transmit import Transmit, TransmitWarning, TransmitException
__all__ = ['ProtoBufSdkRequestCallback', 'ProtoBufHandle', 'ProtoBufHandleCallback', 'PBMessageWrap',
           'ProtobufRWHelper', 'ProtobufDatabase']

# callback(request message, response raw bytes)
ProtoBufSdkRequestCallback = typing.Callable[[message.Message, bytes], None]

# callback(request raw bytes) ->  response message
ProtoBufHandleCallback = typing.Callable[[bytes, typing.Tuple[str, int]], typing.Optional[message.Message]]


class PBMessageWrap(CommunicationObject):
    def __init__(self, msg: message.Message):
        if not isinstance(msg, message.Message):
            raise TypeError(f"'msg' must be a instance of {message.Message.__name__!r}")

        super().__init__(msg)

    def __repr__(self):
        return f'{self.raw}({self.to_bytes().hex()})'

    def __lt__(self, other):
        return self.get_number(self) < self.get_number(other)

    def to_bytes(self) -> bytes:
        return self.raw.SerializeToString()

    def one_of_name(self) -> str:
        return self.raw.DESCRIPTOR.oneofs[0].name

    def get_number(self, msg) -> int:
        try:
            return ProtobufRWHelper.getMessageFieldsDict(self.raw).get(msg.raw.WhichOneof(self.one_of_name()))
        except (AttributeError, KeyError, TypeError, IndexError):
            return -1

    @property
    def payload(self) -> str:
        return self.raw.WhichOneof(self.one_of_name())

    @classmethod
    @abc.abstractmethod
    def from_bytes(cls, obj, data: bytes):
        pass


class ProtoBufHandle(object):
    def __init__(self,
                 transmit: Transmit,
                 max_msg_length: int,
                 handle_callback: ProtoBufHandleCallback,
                 event_callback: typing.Callable[[CommunicationEvent], None], verbose: bool = False):
        """
        Init a protocol buffers handle for protocol buffer comm simulator
        :param transmit: Data transmit (TCPTransmit or UDPTransmit or self-defined TCPTransmit)
        :param max_msg_length: protocol buffers maximum message length
        :param handle_callback: when received a request will call back this
        :param event_callback: communicate event callback
        :param verbose: show communicate verbose detail
        """
        if not isinstance(transmit, Transmit):
            raise TypeError('{!r} required {!r}'.format('transmit', Transmit.__name__))

        if not callable(handle_callback):
            raise TypeError('{!r} required {!r}'.format('handle_callback', 'callable object'))

        self._verbose = verbose
        self._transmit = transmit
        self._callback = handle_callback
        self._max_msg_length = max_msg_length
        self._event_callback = event_callback
        self._tasklet = Tasklet(schedule_interval=0.1, name=self.__class__.__name__)
        self._tasklet.add_task(Task(func=self.taskDetectConnection, timeout=0.1), immediate=True)
        Thread(target=self.threadCommunicationHandle, name=f'ProtoBufHandle_{transmit.address}', daemon=True).start()

    def __del__(self):
        self._transmit.disconnect()

    def event_callback(self, type_: CommunicationEvent.Type, data: typing.Any = ''):
        self._event_callback(CommunicationEvent(type_=type_, source=self._transmit.address, data=data))

    def _loggingCallback(self, msg: UiLogMessage):
        self.event_callback(CommunicationEvent.Type.Logging, msg)

    def _infoLogging(self, msg: str):
        self._loggingCallback(UiLogMessage.genDefaultInfoMessage(msg))

    def _debugLogging(self, msg: str):
        self._loggingCallback(UiLogMessage.genDefaultDebugMessage(msg))

    def _errorLogging(self, msg: str):
        self._loggingCallback(UiLogMessage.genDefaultErrorMessage(msg))

    @property
    def name(self) -> str:
        return type(self).__name__

    @property
    def connected(self) -> bool:
        return self._transmit.connected

    def disconnect(self):
        self._transmit.disconnect()

    def connect(self, address: typing.Tuple[str, int], timeout: float) -> bool:
        """
        Init transmit
        :param address: for TCPTransmit is (host, port) for UARTTransmit is (port, baud rate)
        :param timeout: transmit communicate timeout is seconds
        :return: success return true, failed return false
        """
        result = self._transmit.connect(address=address, timeout=timeout)
        msg = "{!r} connect {}({})".format(self.name, "success" if result else "failed", address)
        self._infoLogging(msg) if result else self._errorLogging(msg)
        return result

    def taskDetectConnection(self, task: Task):
        if not self._transmit.connected:
            task.reschedule()
        else:
            self.event_callback(CommunicationEvent.Type.Connected)

    def threadCommunicationHandle(self):
        while True:
            if not self.connected:
                self.event_callback(CommunicationEvent.Type.Disconnected)
                time.sleep(0.01)
                continue

            try:
                # Receive request
                request = self._transmit.rx(self._max_msg_length)
                if not request:
                    continue

                if self._verbose:
                    print("<<< {:.2f}: [{}] {}".format(time.perf_counter(), len(request), request.hex()))

                # Call callback get response
                response = self._callback(request, self._transmit.address)
                if not isinstance(response, message.Message):
                    continue

                response = response.SerializeToString()

                if not self._transmit.tx(response):
                    raise TransmitException("send response error")

                if self._verbose:
                    print(">>> {:.2f}: [{}] {}".format(time.perf_counter(), len(response), response.hex()))
            except AttributeError as e:
                self.event_callback(CommunicationEvent.Type.Exception, e)
                break
            except message.DecodeError as e:
                self._errorLogging("Decode msg error: {}".format(e))
                continue
            except TransmitException as e:
                self.event_callback(CommunicationEvent.Type.Disconnected, f'e')
                self._tasklet.add_task(Task(func=self.taskDetectConnection, timeout=0.1))
                self._errorLogging("Comm error: {}".format(e))
                self._transmit.disconnect()
                continue
            except TransmitWarning:
                continue


class ProtobufRWHelper:
    @classmethod
    def updateRepeatedItem(cls, msg: message.Message, field_name: str, items: typing.Sequence[message.Message]):
        # Delete old items
        for _ in range(len(msg.__getattribute__(field_name))):
            msg.__getattribute__(field_name).__delitem__(0)

        # Set new items
        msg.__getattribute__(field_name).extend(items)

    @classmethod
    def setRepeatedItem(cls, msg: message.Message, field_name: str, idx: int, item: typing.Any) -> bool:
        items = [x for x in msg.__getattribute__(field_name)]

        # Modify item then update
        try:
            items[idx] = item
        except IndexError:
            return False

        cls.updateRepeatedItem(msg, field_name, items)
        return True

    @classmethod
    def getRepeatedItem(cls, msg: message.Message, field_name: str, idx: int) -> typing.Optional[message.Message]:
        try:
            return msg.__getattribute__(field_name)[idx]
        except IndexError:
            return None

    @classmethod
    def updateNormalItem(cls, msg: message.Message, field_name: str, item: message.Message):
        msg.__getattribute__(field_name).CopyFrom(item)

    @classmethod
    def setNormalItem(cls, msg: message.Message, filed_name: str, name: str, value: typing.Any) -> bool:
        try:
            msg.__getattribute__(filed_name).__setattr__(name, value)
        except TypeError as e:
            print(f'save {filed_name}.{name} = {value} error: {e}')
            return False
        else:
            return True

    @classmethod
    def getNormalItem(cls, msg: message.Message, field_name: str, name: str) -> typing.Any:
        return msg.__getattribute__(field_name).__getattribute__(name)

    @classmethod
    def messageToDict(cls, msg: message.Message, e2i: bool = True, **kwargs) -> dict:
        return MessageToDict(
            msg, preserving_proto_field_name=True,
            including_default_value_fields=True, use_integers_for_enums=e2i, **kwargs
        )

    @classmethod
    def messageToJson(cls, msg: message.Message, e2i: bool = True, **kwargs) -> str:
        return MessageToJson(
            msg, preserving_proto_field_name=True,
            including_default_value_fields=True, use_integers_for_enums=e2i, **kwargs
        )

    @classmethod
    def getMessageFieldsDict(cls, msg: message.Message, reverse: bool = False) -> dict:
        names = msg.DESCRIPTOR.fields_by_name
        numbers = msg.DESCRIPTOR.fields_by_number
        return dict(zip(numbers, names)) if reverse else dict(zip(names, numbers))


class ProtobufDatabase:
    def __init__(self,
                 db_path: str, db_msg: message.Message.__class__,
                 encrypt_func: typing.Callable[[bytes], bytes] = None,
                 decrypt_func: typing.Callable[[bytes], bytes] = None):
        self.db_path = db_path
        self.__encrypt_func = encrypt_func
        self.__decrypt_func = decrypt_func

        try:
            with open(self.db_path, 'rb') as fp:
                data = fp.read()
                if callable(self.__decrypt_func):
                    data = self.__decrypt_func(data)
                self.db = db_msg.FromString(data)
        except FileNotFoundError:
            self.db = self.getDefaultDatabase()
            self.save()

    def save(self) -> bool:
        try:
            with open(self.db_path, 'wb') as fp:
                data = self.db.SerializeToString()
                if callable(self.__encrypt_func):
                    data = self.__encrypt_func(data)
                fp.write(data)
        except OSError as e:
            print(f'save db to {self.db_path} error: {e}')
            return False
        else:
            return True

    @abc.abstractmethod
    def getDefaultDatabase(self) -> message.Message:
        pass

    def updateRepeatedItem(self, field_name: str, items: typing.Sequence[typing.Any]) -> bool:
        ProtobufRWHelper.updateRepeatedItem(self.db, field_name, items)
        return self.save()

    def setRepeatedItem(self, field_name: str, idx: int, item: message.Message) -> bool:
        if not ProtobufRWHelper.setRepeatedItem(self.db, field_name, idx, item):
            return False

        return self.save()

    def getRepeatedItem(self, field_name: str, idx: int) -> typing.Optional[message.Message]:
        return ProtobufRWHelper.getRepeatedItem(self.db, field_name, idx)

    def updateNormalItem(self, field_name: str, item: message.Message) -> bool:
        ProtobufRWHelper.updateNormalItem(self.db, field_name, item)
        return self.save()

    def setNormalItem(self, filed_name: str, name: str, value: typing.Any) -> bool:
        if not ProtobufRWHelper.setNormalItem(self.db, filed_name, name, value):
            return False

        return self.save()

    def getNormalItem(self, field_name: str, name: str) -> typing.Any:
        return ProtobufRWHelper.getNormalItem(self.db, field_name, name)
