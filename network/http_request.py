# -*- coding: utf-8 -*-
import requests
import ipaddress
import fake_useragent
from pyquery import PyQuery
import requests_toolbelt.adapters
__all__ = ['HttpRequest', 'HttpRequestException']


class HttpRequestException(Exception):
    def __init__(self, code, desc):
        super(HttpRequestException, self).__init__(Exception)
        self.code = code
        self.desc = desc


class HttpRequest(object):
    HTTP_OK = 200
    HTTP_Forbidden = 403
    HTTP_Unauthorized = 401

    TOKEN_NAME = "token"

    def __init__(self, token_name=TOKEN_NAME, source_address="", timeout=5.0):
        self._timeout = timeout
        self.__token_name = token_name
        self._section = requests.Session()
        try:
            source_address = str(ipaddress.ip_address(source_address))
            new_source = requests_toolbelt.adapters.source.SourceAddressAdapter(source_address)
            self._section.mount("http://", new_source)
            self._section.mount("https://", new_source)
        except ValueError:
            pass
        self._fake_ua = fake_useragent.UserAgent()
        self._section.headers = {'User-Agent': self._fake_ua.chrome}

    @property
    def timeout(self):
        return self._timeout

    @property
    def token_name(self):
        return self.__token_name[:]

    def get_token(self, url):
        res = self.section_get(url)
        if res.status_code != self.HTTP_OK:
            return ""

        return self.get_token_from_text(res.text, self.__token_name)

    @staticmethod
    def get_token_from_text(text, name=TOKEN_NAME):
        doc = PyQuery(text.encode())
        return doc('input[name="{}"]'.format(name)).attr("value").strip()

    def section_get(self, url, **kwargs):
        kwargs.setdefault("timeout", self.timeout)
        return self._section.get(url, **kwargs)

    def section_post(self, url, **kwargs):
        kwargs.setdefault("timeout", self.timeout)
        return self._section.post(url, **kwargs)

    def login(self, url, login_data, require_token=False):
        if require_token:
            login_data[self.token_name] = self.get_token(url)
        res = self.section_post(url, data=login_data)
        res.raise_for_status()
        return res

