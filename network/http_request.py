# -*- coding: utf-8 -*-
import requests
import ipaddress
from typing import Optional
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

    def __init__(self, token_name: str = TOKEN_NAME, source_address: str = "", timeout: float = 5.0):
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

        self._section.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/65.0.3325.181 Safari/537.36'
        }

    @property
    def timeout(self) -> float:
        return self._timeout

    @property
    def token_name(self) -> str:
        return self.__token_name[:]

    @staticmethod
    def is_response_ok(res: requests.Response) -> bool:
        return res.status_code == HttpRequest.HTTP_OK

    @staticmethod
    def get_token_from_text(text: str, name: str = TOKEN_NAME) -> str:
        doc = PyQuery(text.encode())
        return doc('input[name="{}"]'.format(name)).attr("value").strip()

    def get_token(self, url: str) -> str:
        res = self.section_get(url)
        if not self.is_response_ok(res):
            return ""

        return self.get_token_from_text(res.text, self.__token_name)

    def section_get(self, url: str, **kwargs) -> requests.Response:
        kwargs.setdefault("timeout", self.timeout)
        return self._section.get(url, **kwargs)

    def section_post(self, url: str, **kwargs) -> requests.Response:
        kwargs.setdefault("timeout", self.timeout)
        return self._section.post(url, **kwargs)

    def login(self, url: str,
              login_data: dict,
              headers: Optional[dict] = None,
              require_token: bool = False, verify: bool = False) -> requests.Response:
        if require_token:
            login_data[self.token_name] = self.get_token(url)

        res = self.section_post(url, data=login_data, headers=headers, verify=verify)
        res.raise_for_status()
        return res
