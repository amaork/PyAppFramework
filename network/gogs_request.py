# -*- coding: utf-8 -*-
import os
import requests
from typing import *
import concurrent.futures
from pyquery import PyQuery
from contextlib import closing


from .http_request import *
from ..core.datatype import DynamicObject
__all__ = ['GogsRequest', 'GogsRequestException']


class GogsRequestException(HttpRequestException):
    pass


class RepoRelease(DynamicObject):
    _properties = {'name', 'date', 'desc', 'attachment'}


class GogsRequest(HttpRequest):
    TOKEN_NAME = "_csrf"

    def __init__(self, host: str, username: str, password: str, source_address: str = "", timeout: int = 5):
        super(GogsRequest, self).__init__(token_name=self.TOKEN_NAME, source_address=source_address, timeout=timeout)
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

    def get_repo_url(self, repo: str) -> str:
        return "{}/{}".format(self.__host, repo)

    def download(self, name: str, url: str,
                 chunk_size: int = 1024**32, timeout: int = 60,
                 callback: Callable[[str, bool], None] or None = None) -> bool:
        """
        Download file or attachment
        :param name: download file save path
        :param url: download url
        :param chunk_size: download chunk size
        :param timeout: download timeout
        :param callback: callback(name: str, finished: bool) -> None
        :return: success return ture
        """

        if hasattr(callback, "__call__"):
            callback(name, False)

        try:
            with closing(self.section_get(url, stream=True, timeout=timeout)) as response:
                with open(name, "wb") as file:
                    for data in response.iter_content(chunk_size=chunk_size):
                        file.write(data)
        except (OSError, requests.RequestException) as e:
            print("Download {} failed: {}".format(url, e))
            return False

        if hasattr(callback, "__call__"):
            callback(name, True)

        return True

    def download_pack(self, package: dict, path: str,
                      parallel: bool = True, max_workers: int = 4,
                      chunk_size: int = 1024 ** 32, timeout: int = 60,
                      ignore_error: bool = True, callback: Callable[[str, bool], None] or None = None) -> dict:
        """
        Download an a pack of file
        :param package: Package to download, package is dict include multi-files name is key url is value
        :param path: Download path, path should be a directory
        :param parallel: Thread pool parallel download parallel download
        :param max_workers: Thread pool max workers
        :param chunk_size: Download check size in bytes
        :param timeout: Download timeout for single file
        :param ignore_error: If set ignore error, when error occurred will ignore error continue download
        :param callback: Callback function, callback(name: str, finished: bool),
        will called twice first time means start download, second time means download finished
        :return: Success return each file download result, dict key is file name, value is download result
        """
        download_result = dict(zip(package.keys(), [False] * len(package)))

        # Check download path if is not exist create it
        try:
            if not os.path.isdir(path):
                os.makedirs(path)
        except (OSError, FileExistsError) as err:
            raise GogsRequestException("Download attachment error: {}".format(err))

        if parallel:
            # Thread pool parallel download attachment
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as pool:
                result = [pool.submit(self.download,
                                      **DynamicObject(name=os.path.join(path, name), url=url,
                                                      chunk_size=chunk_size, timeout=timeout, callback=callback).dict)
                          for name, url in package.items()]

            # Get each file download result
            for name, ret in zip(package.keys(), result):
                download_result[name] = ret.result() if ret.result() is not None else False
        else:
            for name, url in package.items():
                ret = self.download(name=os.path.join(path, name), url=url,
                                    chunk_size=chunk_size, timeout=timeout, callback=callback)
                download_result[name] = ret

                if ret or ignore_error:
                    continue
                else:
                    break

        return download_result

    def get_repo_releases(self, repo: str) -> List[RepoRelease]:
        releases = list()
        release_url = "{}/releases".format(self.get_repo_url(repo))

        try:
            response = self.section_get(release_url)
            response.raise_for_status()

            doc = PyQuery(response.text)
            for item in doc("#release-list")(".grid").items():
                name = item("h3")("a").text().strip()
                date = item(".time-since").attr("title")
                desc = item(".desc").text()

                attachment = dict()
                for a in item(".download").items():
                    for package in a(".octicon-package").items():
                        package_name = package.next().text()
                        package_href = package.next().attr("href")
                        attachment[package_name] = "{}{}".format(self.__host, package_href)

                releases.append(RepoRelease(name=name, date=date, desc=desc, attachment=attachment))

            return releases
        except requests.RequestException as e:
            print("get_repo_releases exception: {}".format(e))
            return list()

    def upload_repo_avatar(self, repo_path: str, avatar: str, timeout: int or None = None):
        avatar_url = "{}/{}/settings/avatar".format(self.__host, repo_path)
        avatar_from_data = DynamicObject(
            _csrf=(None, self.__token), avatar=(os.path.basename(avatar), open(avatar, "rb"))
        )
        ret = self._section.post(avatar_url, files=avatar_from_data.dict, timeout=timeout or self._timeout)
        ret.raise_for_status()
