# -*- coding: utf-8 -*-
import os
import json
import codecs
from ..core.datatype import DynamicObject, DynamicObjectDecodeError
__all__ = ['JsonSettings', 'JsonSettingsDecodeError', 'UiInputSetting']


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
        "SELECT": (str, (list, tuple))
    }
    INPUT_TYPES = [k for k, _ in _attributes.items()]
    _properties = {'name', 'data', 'type', 'check', 'default'}

    # Min, max, step
    INT_TYPE_CHECK_DEMO = (1, 100, 1)
    FLOAT_TYPE_CHECK_DEMO = (3.3, 12.0, 0.1)

    BOOL_TYPE_CHECK_DEMO = (True, False)
    SELECT_TYPE_CHECK_DEMO = ("A", "B", "C")

    # Regular expression, max length
    TEXT_TYPE_CHECK_DEMO = ("^(\d+)\.(\d+)\.(\d+)\.(\d+)$", 16)

    def __init__(self, **kwargs):
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

    def is_int_type(self):
        return self.type == "INT"

    def is_bool_type(self):
        return self.type == "BOOL"

    def is_text_type(self):
        return self.type == "TEXT"

    def is_float_type(self):
        return self.type == "FLOAT"

    def is_select_type(self):
        return self.type == "SELECT"

    @staticmethod
    def getDemoSettings(d2=False):

        class JsonDemoSettings(DynamicObject):
            _properties = {'layout', 'int', 'float', 'bool', 'text', 'select'}

            def __init__(self, **kwargs):
                super(JsonDemoSettings, self).__init__(**kwargs)

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

        if d2:
            layout = [["int", "float"], ["bool"], ["text", "select"]]
        else:
            layout = ["int", "float", "bool", "text", "select"]
        return JsonDemoSettings(int=int_input.dict, bool=bool_input.dict, text=text_input.dict,
                                float=float_input.dict, select=select_input.dict, layout=layout)
