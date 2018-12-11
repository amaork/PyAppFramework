# -*- coding: utf-8 -*-
import os
import json
import codecs
import logging
from string import Template
from ..core.datatype import DynamicObject, DynamicObjectDecodeError, str2number
__all__ = ['JsonSettings', 'JsonSettingsDecodeError',
           'UiLogMessage',
           'UiInputSetting', 'UiLayout',
           'UiFontInput', 'UiColorInput',
           'UiTextInput', 'UiTimeInput', 'UiAddressInput',
           'UiFileInput', 'UiFolderInput', 'UiSerialInput',
           'UiSelectInput', 'UiCheckBoxInput', 'UiIntegerInput', 'UiDoubleInput']


class JsonSettingsDecodeError(Exception):
    pass


class JsonSettings(DynamicObject):
    _default_path = "settings.json"

    def __init__(self, **kwargs):
        super(JsonSettings, self).__init__(**kwargs)

    def save(self, path=None):
        return self.store(self, path)

    @classmethod
    def file_path(cls):
        return cls._default_path[:]

    @classmethod
    def load(cls, path=None):
        try:
            path = path or cls._default_path
            if not os.path.isfile(path):
                cls.store(cls.default())
                return cls.default()

            with codecs.open(path, "r", "utf-8") as fp:
                dict_ = json.load(fp)

            return cls(**dict_) if dict_ else cls.default()
        except (JsonSettingsDecodeError, DynamicObjectDecodeError) as err:
            raise JsonSettingsDecodeError(err)

    @classmethod
    def store(cls, settings, path=None):
        if not isinstance(settings, cls):
            print("TypeError: require:{!r}".format(cls.__name__))
            return False

        path = path if path else cls._default_path
        if not os.path.isdir(os.path.dirname(path)) and len(os.path.dirname(path)):
            os.makedirs(os.path.dirname(path))
        with codecs.open(path, "w", "utf-8") as fp:
            json.dump(settings.dict, fp, indent=4, ensure_ascii=False)

        return True

    @classmethod
    def default(cls):
        pass


class UiInputSetting(DynamicObject):
    _attributes = {

        "INT": (int, (list, tuple)),
        "BOOL": (bool, (list, tuple)),
        "FLOAT": (float, (list, tuple)),
        "TEXT": (str, (list, tuple)),
        "FILE": (str, (list, tuple)),
        "FOLDER": (str, str),
        "FONT": (str, str),
        "COLOR": (str, str),
        "SELECT": (str, (list, tuple)),
        "SERIAL": (str, str),
    }
    INPUT_TYPES = [k for k, _ in _attributes.items()]
    _properties = {'name', 'data', 'type', 'check', 'default', 'readonly', 'label_left'}

    # Min, max, step
    INT_TYPE_CHECK_DEMO = (1, 100, 1)
    FLOAT_TYPE_CHECK_DEMO = (3.3, 12.0, 0.1)

    BOOL_TYPE_CHECK_DEMO = (True, False)
    SELECT_TYPE_CHECK_DEMO = ("A", "B", "C")

    # Regular expression, max length
    TEXT_TYPE_CHECK_DEMO = ("^(\d+)\.(\d+)\.(\d+)\.(\d+)$", 16)

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

        # Check check type
        if not isinstance(self.check, check_type):
            raise TypeError("check type error, it require {!r}".format(data_type.__name__))

        if isinstance(self.check, (list, tuple)) and not self.is_text_type():
            for item in self.check:
                if not isinstance(item, data_type):
                    raise TypeError("check type error, it require a tuple or list of {!r}".format(data_type.__name__))

        # Check default value
        if not isinstance(self.data, data_type) or not isinstance(self.default, data_type):
            raise TypeError("default must match type, it require {!r}".format(data_type.__name__))

    def get_data(self):
        return self.data

    def get_name(self):
        return self.name

    def get_check(self):
        return self.check

    def get_default(self):
        return self.default

    def is_readonly(self):
        return True if self.readonly else False

    def is_int_type(self):
        return self.type == "INT"

    def is_bool_type(self):
        return self.type == "BOOL"

    def is_text_type(self):
        return self.type == "TEXT"

    def is_file_type(self):
        return self.type == "FILE"

    def is_font_type(self):
        return self.type == "FONT"

    def is_float_type(self):
        return self.type == "FLOAT"

    def is_color_type(self):
        return self.type == "COLOR"

    def is_folder_type(self):
        return self.type == "FOLDER"

    def is_select_type(self):
        return self.type == "SELECT"

    def is_serial_type(self):
        return self.type == "SERIAL"

    @staticmethod
    def getDemoSettings(d2=False):
        font_input = UiFontInput(name="字体")
        color_input = UiColorInput(name="颜色", r=255, g=255, b=255)
        int_input = UiInputSetting(name="数字", type="INT", data=10,
                                   check=UiInputSetting.INT_TYPE_CHECK_DEMO, default=50)
        text_input = UiInputSetting(name="文本", type="TEXT", data="192.168.1.1",
                                    check=UiInputSetting.TEXT_TYPE_CHECK_DEMO, default="192.168.1.11")
        bool_input = UiInputSetting(name="布尔", type="BOOL", data=False,
                                    check=UiInputSetting.BOOL_TYPE_CHECK_DEMO, default=True)
        float_input = UiInputSetting(name="浮点", type="FLOAT", data=5.0,
                                     check=UiInputSetting.FLOAT_TYPE_CHECK_DEMO, default=3.3)
        select_input = UiInputSetting(name="选择", type="SELECT", data="C",
                                      check=UiInputSetting.SELECT_TYPE_CHECK_DEMO, default="B")
        file_input = UiInputSetting(name="文件", type="FILE", data="", default="", check=("*.jpg", "*.bmp"))
        folder_input = UiInputSetting(name="文件夹", type="FOLDER", data="", default="", check="")

        serial_input = UiSerialInput(name="串口", port="COM1")

        if d2:
            layout = UiLayout(name="Json Demo 设置（Gird）",
                              layout=[
                                  ["int", "float"],
                                  ["bool"],
                                  ["text", "select"],
                                  ["file", "serial"],
                                  ["font", "color"],
                                  ['folder'],
                              ])
        else:
            layout = UiLayout(name="Json Demo 设置 （VBox）",
                              layout=["int", "float", "bool", "text", "select",
                                      "file", "folder", "serial", "font", "color"])
        return DynamicObject(int=int_input.dict, bool=bool_input.dict,
                             font=font_input.dict, color=color_input.dict,
                             folder=folder_input.dict,
                             text=text_input.dict, file=file_input.dict, serial=serial_input.dict,
                             float=float_input.dict, select=select_input.dict, layout=layout.dict)


class UiFileInput(UiInputSetting):
    def __init__(self, name, fmt, default=""):
        super(UiFileInput, self).__init__(name=name, data="", default=default, check=fmt, readonly=False, type="FILE")


class UiFolderInput(UiInputSetting):
    def __init__(self, name, default=""):
        super(UiFolderInput, self).__init__(name=name, data="", default=default,
                                            check="", readonly=False, type="FOLDER")


class UiFontInput(UiInputSetting):
    def __init__(self, name, font_name="宋体", point_size=9, weight=50):
        font = font_name, point_size, weight
        super(UiFontInput, self).__init__(name=name, data="{}".format(font), default="{}".format(font),
                                          check="", readonly=False, type="FONT")

    @staticmethod
    def get_font(font_setting):
        default_font = "宋体", 9, 50
        try:
            font_setting = font_setting[1:-1].split(", ")
            return font_setting[0][1:-1], str2number(font_setting[1]), str2number(font_setting[2])
        except AttributeError:
            return tuple(font_setting) if isinstance(font_setting, (list, tuple)) else default_font
        except (TypeError, IndexError, ValueError):
            return default_font

    @staticmethod
    def get_stylesheet(font_setting):
        try:
            font_name, point_size, _ = UiFontInput.get_font(font_setting)
            return 'font: {}pt "{}";'.format(point_size, font_name)
        except (IndexError, TypeError, ValueError):
            return ""


class UiTextInput(UiInputSetting):
    def __init__(self, name, length, default="", re_="[\s\S]*", readonly=False):
        super(UiTextInput, self).__init__(name=name, data=default, default=default,
                                          check=(re_, length), readonly=readonly, type="TEXT")


class UiTimeInput(UiTextInput):
    def __init__(self, name, default="00:00:00", hour_number=4, readonly=False):

        h = str(hour_number)
        length = 6 + hour_number
        re_ = Template("^(\d{0,$h}):([0-5]{1})([0-9]{1}):([0-5]{1})([0-9]{1})$$")
        super(UiTimeInput, self).__init__(name, length, default=default, re_=re_.substitute(h=h), readonly=readonly)

    @staticmethod
    def str2time(time_string):
        return UiTimeInput.seconds2time(UiTimeInput.str2seconds(time_string))

    @staticmethod
    def str2seconds(time_string):
        try:
            times = time_string.split(":")
            if len(times) != 3:
                return 0
            return int(times[0]) * 3600 + int(times[1]) * 60 + int(times[2])
        except (AttributeError, ValueError):
            return 0

    @staticmethod
    def second2str(seconds):
        h, m, s = UiTimeInput.seconds2time(seconds)
        return "{0:02d}:{1:02d}:{2:02d}".format(h, m, s)

    @staticmethod
    def seconds2time(seconds):
        try:
            h = seconds // 3600
            m = (seconds % 3600) // 60
            s = (seconds % 60)
            return h, m, s
        except TypeError:
            return 0, 0, 0


class UiAddressInput(UiTextInput):
    def __init__(self, name, default="000.000.000.000", readonly=False):
        re_ = "((?:(?:25[0-5]|2[0-4]\\d|[01]?\\d?\\d)\\.){3}(?:25[0-5]|2[0-4]\\d|[01]?\\d?\\d))"
        super(UiAddressInput, self).__init__(name, 16, default=default, re_=re_, readonly=readonly)


class UiColorInput(UiInputSetting):
    def __init__(self, name, r, g, b):
        color = r, g, b
        super(UiColorInput, self).__init__(name=name, data="{}".format(color), default="{}".format(color),
                                           check="", readonly=False, type="COLOR")

    @staticmethod
    def get_color(color_setting):
        default_color = 255, 255, 255
        try:
            color_setting = color_setting[1:-1].split(", ")
            return str2number(color_setting[0]), str2number(color_setting[1]), str2number(color_setting[2])
        except AttributeError:
            return color_setting if isinstance(color_setting, (list, tuple)) else default_color
        except (TypeError, IndexError, ValueError):
            return default_color

    @staticmethod
    def get_color_stylesheet(color_setting, border=False):
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
    def get_bg_color_stylesheet(color_setting, border=False):
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
    def __init__(self, name, minimum, maximum, default=0.0, step=1.0, readonly=False):
        super(UiDoubleInput, self).__init__(name=name, data=default, default=default,
                                            check=(minimum, maximum, step), readonly=readonly, type="FLOAT")


class UiIntegerInput(UiInputSetting):
    def __init__(self, name, minimum, maximum, default=0, step=1, readonly=False):
        super(UiIntegerInput, self).__init__(name=name, data=default, default=default,
                                             check=(minimum, maximum, step), readonly=readonly, type="INT")


class UiSelectInput(UiInputSetting):
    def __init__(self, name, options, default, readonly=False):
        super(UiSelectInput, self).__init__(name=name, data=default, default=default,
                                            check=options, readonly=readonly, type="SELECT")


class UiSerialInput(UiInputSetting):
    def __init__(self, name, port=""):
        super(UiSerialInput, self).__init__(name=name, data=port, default=port,
                                            check=port, readonly=False, type="SERIAL")


class UiCheckBoxInput(UiInputSetting):
    def __init__(self, name, default=False, readonly=False, label_left=False):
        super(UiCheckBoxInput, self).__init__(name=name, data=default, default=default, label_left=label_left,
                                              check=(True, False), readonly=readonly, type="BOOL")


class UiLayout(DynamicObject):
    _properties = {'name', 'layout'}

    def __init__(self, **kwargs):
        kwargs.setdefault("name", "")
        super(UiLayout, self).__init__(**kwargs)

        if not isinstance(self.name, str):
            raise TypeError("name must be a 'str'")

        if not isinstance(self.layout, (list, tuple)):
            raise TypeError("layout must be a tuple or list")

    def get_name(self):
        return self.name

    def get_layout(self):
        return self.layout

    def check_layout(self, settings):
        return self.is_vertical_layout(self.get_layout(), settings) or self.is_grid_layout(self.get_layout(), settings)

    def get_grid_layout(self, settings):
        if self.is_grid_layout(self.get_layout(), settings):
            return self.get_layout()
        else:
            return [[x] for x in self.get_layout()]

    def get_vertical_layout(self, settings):
        if self.is_vertical_layout(self.get_layout(), settings):
            return self.get_layout()
        else:
            layout = list()
            [layout.extend(a) for a in self.get_layout()]
            return layout

    @staticmethod
    def is_grid_layout(layout, settings):
        return set([isinstance(x, (list, tuple)) and UiLayout.is_vertical_layout(x, settings)
                    for x in layout]) == {True}

    @staticmethod
    def is_vertical_layout(layout, settings):
        return set([isinstance(x, str) and settings.get(x) is not None for x in layout]) == {True}


class UiLogMessage(DynamicObject):
    _properties = {'level', 'color', 'font_size', 'content'}

    def __init__(self, **kwargs):
        # Default is info level color is black size is 3
        kwargs.setdefault('font_size', 3)
        kwargs.setdefault('color', "#000000")
        kwargs.setdefault('level', logging.INFO)
        super(UiLogMessage, self).__init__(**kwargs)

    @staticmethod
    def genDefaultMessage(content, level):
        return {

            logging.INFO: UiLogMessage.genDefaultInfoMessage,
            logging.DEBUG: UiLogMessage.genDefaultDebugMessage,
            logging.ERROR: UiLogMessage.genDefaultErrorMessage,
        }.get(level, UiLogMessage.genDefaultInfoMessage)(content)

    @staticmethod
    def genDefaultInfoMessage(content):
        return UiLogMessage(content=content, level=logging.INFO, color="#000000")

    @staticmethod
    def genDefaultDebugMessage(content):
        return UiLogMessage(content=content, level=logging.DEBUG, color="#0000FF")

    @staticmethod
    def genDefaultErrorMessage(content):
        return UiLogMessage(content=content, level=logging.ERROR, color="#FF0000")
