# -*- coding: utf-8 -*-
import os
import json
import codecs
from ..core.datatype import DynamicObject
__all__ = ['JsonSettings']


class JsonSettings(DynamicObject):
    _default_path = "settings.json"

    def __init__(self, **kwargs):
        super(JsonSettings, self).__init__(**kwargs)

    def save(self, path=None):
        return self.store(self, path)

    @classmethod
    def load(cls, path=None):
        path = path or cls._default_path
        if not os.path.isfile(path):
            cls.store(cls.default())
            return cls.default()

        with codecs.open(path, "r", "utf-8") as fp:
            dict_ = json.load(fp)

        return cls(**dict_) if dict_ else cls.default()

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
