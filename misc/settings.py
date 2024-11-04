# -*- coding: utf-8 -*-
import os
import re
import abc
import json
import codecs
import typing
import logging
import collections
from string import Template, hexdigits
from typing import Tuple, Optional, Any, Sequence, Union, List, TypeVar, NamedTuple, Callable

from ..core.datatype import DynamicObject, DynamicObjectDecodeError, BasicFileHeader, str2number
__all__ = ['JsonSettings', 'JsonSettingsDecodeError', 'SystemTrayIconSettings', 'WindowsPositionSettings',
           'CustomAction', 'BinarySettings',
           'UiLogMessage', 'LoggingMsgCallback',
           'UiInputSetting', 'UiLayout',
           'UiFontInput', 'UiColorInput',
           'UiFileInput', 'UiFolderInput', 'UiPushButtonInput',
           'UiTextInput', 'UiTimeInput', 'UiAddressInput', 'UiHexByteInput',
           'UiSerialInput', 'UiAddressSelectInput', 'UiNetworkSelectInput', 'UiInterfaceSelectInput',
           'UiSelectInput', 'UiCheckBoxInput', 'UiIntegerInput', 'UiDoubleInput',
           'Font', 'Time', 'Color', 'Unit', 'IndexColor', 'color_property',
           'Layout', 'LayoutSpace', 'LayoutMargins']

Font = NamedTuple('Font', [('name', str), ('point', int), ('weight', int)])
Time = NamedTuple('Time', [('hour', int), ('minute', int), ('second', int)])
Unit = collections.namedtuple('Unit', 'time_s time_ms temp_c vol_v vol_mv')(*(
    ' (S)', ' (ms)', ' (°C)', ' (V)', ' (mV)'
))

Color = Tuple[int, int, int]
IndexColor = Tuple[int, int]

Layout = Sequence[str]
LayoutSpace = Tuple[int, int, int]
LayoutMargins = Tuple[int, int, int, int]


class SystemTrayIconSettings(DynamicObject):
    _properties = {'icon', 'tips', 'msg_title', 'minimize_msg', 'exit_callback'}

    def __init__(self, **kwargs):
        kwargs.setdefault('minimize_msg', None)
        kwargs.setdefault('exit_callback', None)
        super(SystemTrayIconSettings, self).__init__(**kwargs)


class JsonSettingsDecodeError(Exception):
    pass


class JsonSettings(DynamicObject):
    _default_path = "settings.json"

    def __init__(self, **kwargs):
        super(JsonSettings, self).__init__(**kwargs)

    def save(self, path: Optional[str] = None):
        return self.store(self, path)

    @classmethod
    def get(cls, path: str = None):
        try:
            return cls.load(path)
        except (json.JSONDecodeError, JsonSettingsDecodeError, FileNotFoundError):
            settings = cls.default()
            settings.save(path)
            return settings

    @classmethod
    def file_path(cls):
        return cls._default_path[:]

    @classmethod
    def load(cls, path: Optional[str] = None):
        try:
            path = path or cls._default_path
            if not os.path.isfile(path):
                cls.store(cls.default(), path)
                return cls.default()

            with codecs.open(path, "r", "utf-8") as fp:
                # noinspection PyTypeChecker
                dict_ = json.load(fp, object_pairs_hook=collections.OrderedDict)

            return cls(**dict_) if dict_ else cls.default()
        except (json.JSONDecodeError, JsonSettingsDecodeError, DynamicObjectDecodeError) as err:
            raise JsonSettingsDecodeError(err)

    @classmethod
    def store(cls, settings: DynamicObject, path: Optional[str] = None):
        if not isinstance(settings, cls):
            print("TypeError: require:{!r}".format(cls.__name__))
            return False

        path = path if path else cls._default_path

        try:
            if not os.path.isdir(os.path.dirname(path)) and len(os.path.dirname(path)):
                os.makedirs(os.path.dirname(path))
            with codecs.open(path, "w", "utf-8") as fp:
                json.dump(settings.dict, fp, indent=4, ensure_ascii=False, cls=cls._json_encoder)
        except OSError as e:
            print("store settings to {}, failed: {}".format(path, e))
            return False

        return True

    @classmethod
    def default(cls) -> DynamicObject:
        pass

    @classmethod
    def ui(cls) -> DynamicObject:
        pass


class BinarySettings:
    @classmethod
    @abc.abstractmethod
    def model(cls) -> str:
        pass

    @classmethod
    def extension(cls) -> str:
        return f'*.{cls.model()}'

    @classmethod
    def _encrypt(cls, data: bytes) -> bytes:
        return data

    @classmethod
    def _decrypt(cls, data: bytes) -> bytes:
        return data

    @classmethod
    def load(cls, path: str) -> bytes:
        try:
            with open(path, 'rb') as fp:
                data = fp.read()

            header = BasicFileHeader('')
            header.set_cdata(data[:BasicFileHeader.Size])
            header.check(data[BasicFileHeader.Size:], cls.model())
            return cls._decrypt(data[BasicFileHeader.Size:])
        except (OSError, ValueError) as e:
            print(f'load {path} fail: {e}')
            raise OSError(e)

    @classmethod
    def save(cls, data: bytes, path: Optional[str] = None):
        try:
            data = cls._encrypt(data)
            header = BasicFileHeader(cls.model())
            header.update(data)

            with open(path, 'wb') as fp:
                fp.write(header.cdata())
                fp.write(data)
        except (TypeError, OSError) as e:
            print(f'save data to {path}, fail: {e}')
            raise OSError(e)


class WindowsPositionSettings(JsonSettings):
    _properties = {'x', 'y', 'width', 'height', 'pin'}

    @classmethod
    def default(cls) -> DynamicObject:
        return WindowsPositionSettings(x=0, y=0, width=0, height=0, pin=False)

    def isValid(self):
        return self.width and self.height

    def setPosition(self, x: int, y: int, w: int, h: int):
        self.update(dict(x=x, y=y, width=w, height=h))

    def getPosition(self) -> typing.Tuple[int, int, int, int]:
        return self.x, self.y, self.width, self.height


class CustomAction(DynamicObject):
    _properties = {'text', 'slot', 'shortcut', 'ks'}

    def __init__(self, text: str, slot: Callable[[None], None], shortcut: str = ''):
        if not isinstance(text, str):
            raise TypeError("text must be 'str' type")

        if not callable(slot):
            raise TypeError("slot must be 'callable' type")

        super(CustomAction, self).__init__(text=text, slot=slot, shortcut=shortcut, ks='')


class UiInputSetting(DynamicObject):
    _attributes = {
        "INT": (int, (list, tuple)),
        "BOOL": (bool, (list, tuple)),
        "FLOAT": ((float, int), (list, tuple)),
        "TEXT": (str, (list, tuple)),
        "FILE": (str, (list, tuple)),
        "FOLDER": (str, str),
        "FONT": (str, str),
        "COLOR": (str, str),
        "SERIAL": (str, float),
        "NETWORK": (str, str),
        "ADDRESS": (str, str),
        "INTERFACE": (str, str),
        "BUTTON": (object, object),
        "SELECT": ((str, int), (list, tuple)),
        "SBS_SELECT": ((str, int), (list, tuple)),
    }
    INPUT_TYPES = [k for k, _ in _attributes.items()]
    _properties = {'name', 'data', 'type', 'check', 'default', 'readonly', 'label_left'}

    # Min, max, step
    INT_TYPE_CHECK_DEMO = (1, 100, 1)
    FLOAT_TYPE_CHECK_DEMO = (3.3, 12.0, 0.1)

    BOOL_TYPE_CHECK_DEMO = (True, False)
    SELECT_TYPE_CHECK_DEMO = ("A", "B", "C")

    # Regular expression, max length
    TEXT_TYPE_CHECK_DEMO = (r"^(\d+)\.(\d+)\.(\d+)\.(\d+)$", 16, False)
    PASSWORD_TYPE_CHECK_DEMO = (r"[\s\S]*", 16, True)

    def __init__(self, **kwargs):
        kwargs.setdefault('readonly', False)
        kwargs.setdefault('label_left', True)
        super(UiInputSetting, self).__init__(**kwargs)

        # Check name
        if not isinstance(self.name, str):
            raise TypeError("name require a 'str' type")

        # Check type
        try:
            data_type, check_type = self._attributes.get(self.type)
        except TypeError:
            raise ValueError("type ValueError is must be one of theme:{!r}".format(self.INPUT_TYPES))

        # Check type
        if not isinstance(self.check, check_type):
            raise TypeError("check type error, it require {!r}".format(data_type))

        if isinstance(self.check, (list, tuple)) and not self.is_text_type():
            for item in self.check:
                if not isinstance(item, data_type):
                    raise TypeError("check type error, it require a tuple or list of {!r}".format(data_type))

        # Check default value
        if not isinstance(self.data, data_type) or not isinstance(self.default, data_type):
            raise TypeError("default must match type, it require {!r}".format(data_type))

    def get_data(self) -> Any:
        return self.data

    def get_name(self) -> str:
        return self.name

    def get_check(self) -> Any:
        return self.check

    def get_default(self) -> Any:
        return self.default

    def is_readonly(self) -> bool:
        return True if self.readonly else False

    def is_int_type(self) -> bool:
        return self.type == "INT"

    def is_bool_type(self) -> bool:
        return self.type == "BOOL"

    def is_text_type(self) -> bool:
        return self.type == "TEXT"

    def is_file_type(self):
        return self.type == "FILE"

    def is_font_type(self) -> bool:
        return self.type == "FONT"

    def is_float_type(self) -> bool:
        return self.type == "FLOAT"

    def is_color_type(self) -> bool:
        return self.type == "COLOR"

    def is_folder_type(self) -> bool:
        return self.type == "FOLDER"

    def is_select_type(self) -> bool:
        return self.type == "SELECT"

    def is_button_type(self) -> bool:
        return self.type == "BUTTON"

    def is_serial_type(self) -> bool:
        return self.type == "SERIAL"

    def is_network_type(self) -> bool:
        return self.type == "NETWORK"

    def is_address_type(self) -> bool:
        return self.type == "ADDRESS"

    def is_interface_type(self) -> bool:
        return self.type == "INTERFACE"

    def is_sbs_select_type(self) -> bool:
        return self.type == "SBS_SELECT"

    @staticmethod
    def getDemoSettings(d2: bool = False) -> DynamicObject:
        font_input = UiFontInput(name="字体")
        color_input = UiColorInput(name="颜色", r=255, g=255, b=255)
        int_input = UiInputSetting(name="数字", type="INT", data=10,
                                   check=UiInputSetting.INT_TYPE_CHECK_DEMO, default=50)
        ts_int_input = UiInputSetting(name="数字(TS)", type="INT", data=20,
                                      check=UiInputSetting.INT_TYPE_CHECK_DEMO, default=50, readonly=True)
        text_input = UiInputSetting(name="文本", type="TEXT", data="192.168.1.1",
                                    check=UiInputSetting.TEXT_TYPE_CHECK_DEMO, default="192.168.1.11")
        password_input = UiInputSetting(name="密码", type="TEXT", data="HIDDEN PASSWORD",
                                        check=UiInputSetting.PASSWORD_TYPE_CHECK_DEMO, default="")
        bool_input = UiInputSetting(name="布尔", type="BOOL", data=False,
                                    check=UiInputSetting.BOOL_TYPE_CHECK_DEMO, default=True)
        float_input = UiInputSetting(name="浮点", type="FLOAT", data=5.0,
                                     check=UiInputSetting.FLOAT_TYPE_CHECK_DEMO, default=3.3)
        ts_float_input = UiInputSetting(name="浮点(TS)", type="FLOAT", data=4.567,
                                        check=(3.3, 12.0, 3), default=3.3, readonly=True)
        select_input = UiInputSetting(name="选择", type="SELECT", data="C",
                                      check=UiInputSetting.SELECT_TYPE_CHECK_DEMO, default="B")
        sbs_select_input = UiInputSetting(name="选择", type="SBS_SELECT", data=1,
                                          check=UiInputSetting.SELECT_TYPE_CHECK_DEMO, default=1)
        file_input = UiInputSetting(name="文件", type="FILE", data="", default="", check=("*.jpg", "*.bmp"))
        folder_input = UiInputSetting(name="文件夹", type="FOLDER", data="", default="", check="")
        network_input = UiInputSetting(name="网络选择", type="NETWORK", data="192.168.1.0/24", default="", check="")
        address_input = UiInputSetting(name="地址选择", type="ADDRESS", data="192.168.1.241", default="", check="")

        serial_input = UiSerialInput(name="串口", port="COM1")

        if d2:
            layout = UiLayout(name="Json Demo 设置（Gird）",
                              layout=[
                                  ["int", "float"],
                                  ["ts_int", "ts_float"],
                                  ["bool", 'text'],
                                  ["select", "sbs_select"],
                                  ["file", "serial"],
                                  ["network", "address"],
                                  ["font", "color"],
                                  ['folder'],
                              ])
        else:
            layout = UiLayout(name="Json Demo 设置 （VBox）",
                              layout=["int", "float",
                                      "ts_int", "ts_float",
                                      "bool", "text", "password", "select", 'sbs_select',
                                      "file", "folder", "serial", "font", "color", "network", "address"])
        return DynamicObject(int=int_input.dict, ts_int=ts_int_input.dict,
                             float=float_input.dict, ts_float=ts_float_input.dict,
                             bool=bool_input.dict,
                             font=font_input.dict, color=color_input.dict,
                             folder=folder_input.dict,
                             network=network_input.dict, address=address_input.dict,
                             text=text_input.dict, password=password_input.dict,
                             file=file_input.dict, serial=serial_input.dict,
                             select=select_input.dict, sbs_select=sbs_select_input.dict,
                             layout=layout.dict)


class UiFileInput(UiInputSetting):
    CHECK_EDITABLE = -1
    CHECK_SELECTABLE = -2

    def __init__(self, name: str, fmt: Tuple[str, ...], default: str = "",
                 selectable: bool = False, editable: bool = False):
        fmt = list(fmt)
        fmt.append(str(selectable))
        fmt.append(str(editable))
        super(UiFileInput, self).__init__(name=name, data="", default=default,
                                          check=fmt, readonly=False, type="FILE")

    @staticmethod
    def getFilePath(data) -> str:
        try:
            _, file_path = data
            return file_path
        except ValueError:
            return data

    @staticmethod
    def isEditable(check: Sequence) -> bool:
        try:
            return check[UiFileInput.CHECK_EDITABLE] == str(True)
        except IndexError:
            return False

    @staticmethod
    def isSelectable(check: Sequence) -> bool:
        try:
            return check[UiFileInput.CHECK_SELECTABLE] == str(True)
        except IndexError:
            return False


class UiFolderInput(UiInputSetting):
    def __init__(self, name: str, default: str = ""):
        super(UiFolderInput, self).__init__(name=name, data="", default=default,
                                            check="", readonly=False, type="FOLDER")


class UiFontInput(UiInputSetting):
    def __init__(self, name: str, font_name: str = "宋体", point_size: int = 9, weight: int = 50):
        font = font_name, point_size, weight
        super(UiFontInput, self).__init__(name=name, data="{}".format(font), default="{}".format(font),
                                          check="", readonly=False, type="FONT")

    @staticmethod
    def get_font(font_setting: Union[str, Font]) -> Font:
        default_font = Font("宋体", 9, 50)
        try:
            font_setting = font_setting[1:-1].split(", ")
            return Font(font_setting[0][1:-1], str2number(font_setting[1]), str2number(font_setting[2]))
        except AttributeError:
            if isinstance(font_setting, (list, tuple)) and len(font_setting) == 3 and \
                    isinstance(font_setting[0], str) and all(isinstance(x, int) for x in font_setting[1:]):
                return Font(*tuple(font_setting))
            else:
                return default_font
        except (TypeError, IndexError, ValueError):
            return default_font

    @staticmethod
    def get_stylesheet(font_setting: Union[str, Font]) -> str:
        try:
            font_name, point_size, _ = UiFontInput.get_font(font_setting)
            return 'font: {}pt "{}";'.format(point_size, font_name)
        except (IndexError, TypeError, ValueError):
            return ""


class UiTextInput(UiInputSetting):
    CHECK = collections.namedtuple('UiTextInputCheck', ['REGEXP', 'LENGTH'])(*range(2))

    def __init__(self, name: str, length: int, default: str = "",
                 password: bool = False, re_: str = r"[\s\S]*", readonly: bool = False):
        super(UiTextInput, self).__init__(name=name, data=default, default=default,
                                          check=(re_, length, password), readonly=readonly, type="TEXT")


class UiTimeInput(UiTextInput):
    WallTimeRegExp = "^(2[0-3]|[01]?[0-9]):([0-5]{1})([0-9]{1}):([0-5]{1})([0-9]{1})$"

    def __init__(self, name: str, default: str = "00:00:00",
                 hour_number: int = 4, readonly: bool = False, wall_time: bool = False):
        if wall_time:
            super(UiTimeInput, self).__init__(name, 8, default=default, re_=self.WallTimeRegExp, readonly=readonly)
        else:
            h = str(hour_number)
            length = 6 + hour_number
            re_ = Template(r"^(\d{0,$h}):([0-5]{1})([0-9]{1}):([0-5]{1})([0-9]{1})$$")
            super(UiTimeInput, self).__init__(name, length, default=default, re_=re_.substitute(h=h), readonly=readonly)

    @staticmethod
    def isValidTime(time_string: str) -> bool:
        if not isinstance(time_string, str) or len(time_string) != 8:
            return False
        return re.match(UiTimeInput.WallTimeRegExp, time_string) is not None

    @staticmethod
    def str2time(time_string: str) -> Time:
        return UiTimeInput.seconds2time(UiTimeInput.str2seconds(time_string))

    @staticmethod
    def str2seconds(time_string: str) -> int:
        try:
            times = time_string.split(":")
            if len(times) != 3:
                return 0
            return int(times[0]) * 3600 + int(times[1]) * 60 + int(times[2])
        except (AttributeError, ValueError):
            return 0

    @staticmethod
    def second2str(seconds: int) -> str:
        h, m, s = UiTimeInput.seconds2time(seconds)
        return "{0:02d}:{1:02d}:{2:02d}".format(h, m, s)

    @staticmethod
    def seconds2time(seconds: int) -> Time:
        try:
            h = seconds // 3600
            m = (seconds % 3600) // 60
            s = (seconds % 60)
            return Time(h, m, s)
        except TypeError:
            return Time(0, 0, 0)


class UiAddressInput(UiTextInput):
    RegExp = "((?:(?:25[0-5]|2[0-4]\\d|[01]?\\d?\\d)\\.){3}(?:25[0-5]|2[0-4]\\d|[01]?\\d?\\d))"

    def __init__(self, name: str, default: str = "000.000.000.000", readonly: bool = False):
        super(UiAddressInput, self).__init__(name, 16, default=default, re_=self.RegExp, readonly=readonly)


class UiHexByteInput(UiTextInput):
    RegExp = Template(r"^([0-9a-fA-F]{2}\ ?){0,$len}")

    def __init__(self, name: str, length: int, default: str = "00 01 02 03 04 05 06", readonly: bool = False):
        re_ = self.RegExp.substitute(len=length)
        super(UiHexByteInput, self).__init__(name, length * 3 - 1, default=default, re_=re_, readonly=readonly)


class UiColorInput(UiInputSetting):
    def __init__(self, name: str, r: int, g: int, b: int):
        color = r, g, b
        super(UiColorInput, self).__init__(name=name, data="{}".format(color), default="{}".format(color),
                                           check="", readonly=False, type="COLOR")

    @staticmethod
    def html2rgb(html_color: str) -> Color:
        if len(html_color) != 7 or html_color[0] != '#' or any([x.upper() not in hexdigits for x in html_color[1:]]):
            return 0, 0, 0

        # noinspection PyTypeChecker
        return tuple([int(a + b, 16) for a, b in zip(html_color[1::2], html_color[2::2])])

    @staticmethod
    def rgb2html(rgb_color: Color) -> str:
        return "#{:02X}{:02X}{:02X}".format(*rgb_color)

    @staticmethod
    def get_color(color_setting: Union[str, Color]) -> Color:
        default_color = 255, 255, 255
        try:
            color_setting = color_setting[1:-1].split(", ")
            return str2number(color_setting[0]), str2number(color_setting[1]), str2number(color_setting[2])
        except AttributeError:
            if isinstance(color_setting, (list, tuple)) and len(color_setting) == 3 and \
                    all(isinstance(x, int) for x in color_setting):
                return color_setting
            else:
                return default_color
        except (TypeError, IndexError, ValueError):
            return default_color

    @staticmethod
    def get_color_stylesheet(color_setting: Union[str, Color], border: bool = False) -> str:
        try:
            color_setting = UiColorInput.get_color(color_setting)

            r = color_setting[0]
            g = color_setting[1]
            b = color_setting[2]
            style = "color: rgb({}, {}, {});".format(r, g, b)
            return style + 'border: none;' if border else style
        except (IndexError, TypeError):
            return ""

    @staticmethod
    def get_bg_color_stylesheet(color_setting: Union[str, Color], border: bool = False) -> str:
        try:
            color_setting = UiColorInput.get_color(color_setting)
            r = color_setting[0]
            g = color_setting[1]
            b = color_setting[2]
            style = "background-color: rgb({}, {}, {});".format(r, g, b)
            return style + 'border: none;' if border else style
        except (TypeError, IndexError):
            return ""


class UiDoubleInput(UiInputSetting):
    CHECK = collections.namedtuple('UiDoubleInputCheck', ['MIN', 'MAX', 'STEP', 'DECIMALS'])(*range(4))

    def __init__(self, name: str, minimum: float, maximum: float,
                 default: float = 0.0, step: float = 1.0, decimals: int = 1, readonly: bool = False):
        super(UiDoubleInput, self).__init__(name=name, data=default, default=default,
                                            check=(minimum, maximum, step, decimals), readonly=readonly, type="FLOAT")


class UiIntegerInput(UiInputSetting):
    CHECK = collections.namedtuple('UiIntegerInputCheck', ['MIN', 'MAX', 'STEP'])(*range(3))

    def __init__(self, name: str, minimum: int, maximum: int, default: int = 0, step: int = 1, readonly: bool = False):
        super(UiIntegerInput, self).__init__(name=name, data=default, default=default,
                                             check=(minimum, maximum, step), readonly=readonly, type="INT")


class UiSelectInput(UiInputSetting):
    def __init__(self, name: str, options: Sequence[str],
                 default: Union[int, str], readonly: bool = False, sbs: bool = False):
        super(UiSelectInput, self).__init__(name=name, data=default, default=default,
                                            check=options, readonly=readonly, type="SBS_SELECT" if sbs else "SELECT")


class UiSerialInput(UiInputSetting):
    def __init__(self, name: str, port: str = "", scan_timeout: float = 0.0):
        super(UiSerialInput, self).__init__(name=name, data=port, default=port,
                                            check=scan_timeout, readonly=False, type="SERIAL")


class UiNetworkSelectInput(UiInputSetting):
    def __init__(self, name: str, network: str = "", default: str = ""):
        super(UiNetworkSelectInput, self).__init__(name=name, data=network, default=default,
                                                   check=network, readonly=False, type="NETWORK")


class UiAddressSelectInput(UiInputSetting):
    def __init__(self, name: str, address: str = "", default: str = ""):
        super(UiAddressSelectInput, self).__init__(name=name, data=address, default=default,
                                                   check=address, readonly=False, type="ADDRESS")


class UiInterfaceSelectInput(UiInputSetting):
    def __init__(self, name: str, iface: str = '', default: str = ''):
        super(UiInterfaceSelectInput, self).__init__(name=name, data=iface, default=default,
                                                     check=iface, readonly=False, type="INTERFACE")


class UiCheckBoxInput(UiInputSetting):
    def __init__(self, name: str, default: bool = False, readonly: bool = False, label_left: bool = False):
        super(UiCheckBoxInput, self).__init__(name=name, data=default, default=default, label_left=label_left,
                                              check=(True, False), readonly=readonly, type="BOOL")


class UiPushButtonInput(UiInputSetting):
    def __init__(self, name: str, slot: Callable, data: Any = ''):
        super(UiPushButtonInput, self).__init__(name=name, data=data,
                                                default=slot, check=slot, readonly=False, type="BUTTON")


class UiLayout(DynamicObject):
    _properties = {'name', 'layout', 'margins', 'spaces', 'stretch', 'min_size', 'title', 'font'}

    def __init__(self, **kwargs):
        kwargs.setdefault('name', "")
        kwargs.setdefault('title', False)
        kwargs.setdefault('font', ('', 0))
        kwargs.setdefault('stretch', (0, 0))
        kwargs.setdefault('min_size', (0, 0))
        kwargs.setdefault("spaces", (6, 6, 6))
        kwargs.setdefault("margins", (9, 9, 9, 9))
        super(UiLayout, self).__init__(**kwargs)

        if not isinstance(self.name, str):
            raise TypeError("name must be a 'str'")

        if not isinstance(self.layout, (list, tuple)):
            raise TypeError("layout must be a tuple or list")

    def get_name(self) -> str:
        return self.name

    def get_font(self):
        font = self.font

        try:
            if isinstance(font[0], str) and isinstance(font[1], int) and font[0] and font[1]:
                return tuple(font[:2])
        except IndexError:
            pass

        return None, None

    def get_layout(self) -> Layout:
        return self.layout

    def get_spaces(self) -> LayoutSpace:
        return self.spaces

    def get_margins(self) -> LayoutMargins:
        return tuple(self.margins)

    def get_min_size(self) -> Tuple[int, int]:
        return tuple(self.min_size)

    def get_stretch(self) -> Tuple[int, int]:
        return tuple(self.stretch)

    def force_display_title(self):
        return self.title

    def check_layout(self, settings: dict) -> bool:
        return self.is_vertical_layout(self.get_layout(), settings) or self.is_grid_layout(self.get_layout(), settings)

    def get_grid_layout(self, settings: dict) -> Union[Layout, List[Layout]]:
        if self.is_grid_layout(self.get_layout(), settings):
            return self.get_layout()
        else:
            return [[x] for x in self.get_layout()]

    def get_vertical_layout(self, settings: dict) -> Layout:
        if self.is_vertical_layout(self.get_layout(), settings):
            return self.get_layout()
        else:
            layout = list()
            [layout.extend(a) for a in self.get_layout()]
            return layout

    @staticmethod
    def is_grid_layout(layout: Layout, settings: dict) -> bool:
        return all(isinstance(x, (list, tuple)) and UiLayout.is_vertical_layout(x, settings) for x in layout)

    @staticmethod
    def is_vertical_layout(layout: Layout, settings: dict) -> bool:
        return all(isinstance(x, str) and settings.get(x) is not None for x in layout)


T = TypeVar('T', bound='UiLogMessage')


class UiLogMessage(DynamicObject):
    _properties = {'level', 'color', 'font_size', 'content'}
    DefaultColor = collections.namedtuple(
        'DefaultColor', 'Info Debug Warn Error'
    )(*'#000000 #0000FF #74572f #FF0000'.split())

    def __init__(self, **kwargs):
        # Default is info level color is black size is 3
        kwargs.setdefault('font_size', 3)
        kwargs.setdefault('color', "#000000")
        kwargs.setdefault('level', logging.INFO)
        super(UiLogMessage, self).__init__(**kwargs)

    @classmethod
    def genDefaultMessage(cls, content: str, level: int) -> T:
        return {
            logging.INFO: cls.genDefaultInfoMessage,
            logging.WARN: cls.genDefaultWarnMessage,
            logging.DEBUG: cls.genDefaultDebugMessage,
            logging.ERROR: cls.genDefaultErrorMessage,
        }.get(level, UiLogMessage.genDefaultInfoMessage)(content)

    @classmethod
    def genDefaultInfoMessage(cls, content: str, color: str = DefaultColor.Info) -> T:
        return UiLogMessage(content=content, level=logging.INFO, color=color or UiLogMessage.DefaultColor.Info)

    @classmethod
    def genDefaultDebugMessage(cls, content, color: str = DefaultColor.Debug) -> T:
        return UiLogMessage(content=content, level=logging.DEBUG, color=color or UiLogMessage.DefaultColor.Debug)

    @classmethod
    def genDefaultWarnMessage(cls, content, color: str = DefaultColor.Warn) -> T:
        return UiLogMessage(content=content, level=logging.WARN, color=color or UiLogMessage.DefaultColor.Warn)

    @classmethod
    def genDefaultErrorMessage(cls, content, color: str = DefaultColor.Error) -> T:
        return UiLogMessage(content=content, level=logging.ERROR, color=color or UiLogMessage.DefaultColor.Error)


LoggingMsgCallback = Callable[[UiLogMessage], None]


def color_property(color_name: str, max_value: int = 255) -> property:
    def color_check(color) -> bool:
        return isinstance(color, (list, tuple)) and len(color) == 3 and all([0 <= x <= max_value for x in color])

    def color_getter(instance) -> Color:
        return instance.__dict__[color_name]

    def color_setter(instance, color):
        if color_check(color):
            instance.__dict__[color_name] = color
        else:
            raise ValueError(f'{color_name!r} invalid: {color}')

    return property(color_getter, color_setter, doc=f'{color_name}')
