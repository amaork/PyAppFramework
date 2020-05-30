# -*- coding: utf-8 -*-
import os
import requests
from pyquery import PyQuery
from .http_request import *
from ..core.datatype import DynamicObject
__all__ = ['GogsRequest', 'GogsRequestException']


class GogsRequestException(HttpRequestException):
    pass


class GogsRequest(HttpRequest):
    TOKEN_NAME = "_csrf"

    def __init__(self, host, username, password):
        super(GogsRequest, self).__init__(token_name=self.TOKEN_NAME)
        self.__host = host
        self.__username = username

        login_url = "{}/user/login".format(host)
        login_data = DynamicObject(user_name=username, password=password)
        try:
            login_response = self.login(login_url, login_data.dict, require_token=True)
            if login_response.url == login_url:
                doc = PyQuery(login_response.text)
                raise GogsRequestException(self.HTTP_Forbidden, doc('p').text().strip())
            self.__token = self.get_token_from_text(login_response.text, self.TOKEN_NAME)
        except requests.RequestException as err:
            raise GogsRequestException(err.response.status_code, err.response.text)

    def upload_repo_avatar(self, repo_path, avatar):
        avatar_url = "{}/{}/settings/avatar".format(self.__host, repo_path)
        avatar_from_data = DynamicObject(
            _csrf=(None, self.__token), avatar=(os.path.basename(avatar), open(avatar, "rb"))
        )
        ret = self._section.post(avatar_url, files=avatar_from_data.dict)
        ret.raise_for_status()
