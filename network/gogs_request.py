# -*- coding: utf-8 -*-
import os
import json
import typing

import requests
import mimetypes
import concurrent.futures
from pyquery import PyQuery
from contextlib import closing
from typing import List, Callable, Optional, Dict

from .http_request import *
from ..core.datatype import DynamicObject, DynamicObjectDecodeError
__all__ = ['GogsRequest', 'GogsRequestException', 'RepoRelease']


class GogsRequestException(HttpRequestException):
    pass


class RepoRelease(DynamicObject):
    _properties = {'name', 'date', 'desc', 'attachment'}

    @property
    def raw_desc(self) -> str:
        return self.desc[1] if len(self.desc) == 2 else ""

    @property
    def html_desc(self) -> str:
        return self.desc[0] if len(self.desc) == 2 else ""

    def attachments(self) -> List[str]:
        return list(self.attachment.keys())

    def get_attachment_url(self, name: str) -> str:
        return self.attachment.get(name, "")


class GogsRequest(HttpRequest):
    TOKEN_NAME = "_csrf"

    def __init__(self, host: str, username: str, password: str, source_address: str = "", timeout: float = 5):
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
            raise GogsRequestException(err.response.status_code if err.response else -1, err.response.text)

    def get_repo_url(self, repo: str) -> str:
        return "{}/{}".format(self.__host, repo)

    def download(self, name: str, url: str, timeout: int = 60,
                 callback: Optional[Callable[[str], None]] = None) -> bool:
        """
        Download file or attachment
        :param name: download file save path
        :param url: download url
        :param timeout: download timeout
        :param callback: callback(name: str) -> None
        :return: success return ture
        """
        try:
            with closing(self.section_get(url, timeout=timeout)) as response:
                with open(name, "wb") as file:
                    file.write(response.content)
        except (OSError, requests.RequestException) as e:
            print("Download {} failed: {}".format(url, e))
            return False

        if hasattr(callback, "__call__"):
            callback(name)

        return True

    def stream_download(self, name: str, url: str, size: int, chunk_size: int = 1024 * 32,
                        timeout: int = 60, callback: Optional[Callable[[float, str], bool]] = None) -> bool:
        """
        Stream download a file from gogs server
        :param name: download path
        :param url: download url
        :param size: download file size in bytes
        :param chunk_size: download chunk size in bytes
        :param timeout: download timeout
        :param callback: download progress callback
        :return: success return true, failed return false
        """
        try:
            if not isinstance(size, int) or not size:
                print("{!r} stream download must specific download file size".format(self.__class__.__name__))
                return False

            download_size = 0
            chunk_size = chunk_size if size > chunk_size else 1024
            chunk_size = chunk_size if size > chunk_size else 1
            with closing(self.section_get(url, timeout=timeout, stream=True)) as response:
                with open(name, "wb") as file:
                    for data in response.iter_content(chunk_size=chunk_size):
                        file.write(data)
                        download_size += len(data)

                        if hasattr(callback, "__call__"):
                            info = "{}K/{}K".format(download_size // 1024, size // 1024)
                            if not callback(round(download_size / size * 100, 2), info):
                                print("Download canceled")
                                return False
        except (OSError, requests.RequestException) as e:
            print("Download {} failed: {}".format(url, e))
            return False

        return True

    def download_package(self, package: dict, path: str,
                         timeout: int = 60, parallel: bool = True,
                         max_workers: int = 4, ignore_error: bool = True,
                         callback: Optional[Callable[[str, float], bool]] = None) -> Dict[str, bool]:
        """
        Download a pack of file
        :param package: Package to download, package is dict include multi-files name is key url is value
        :param path: Download path, path should be a directory
        :param parallel: Thread pool parallel download
        :param max_workers: Thread pool max workers
        :param timeout: Download timeout for single file
        :param ignore_error: If set ignore error, when error occurred will ignore error continue download
        :param callback: Callback function, callback(downloaded_file_name: str, download_progress: int) -> bool if
        callback return false mean's canceled, one serial download support this feature
        :return: Success return each file download result, dict key is file name, value is download result
        """
        download_result = dict(zip(package.keys(), [False] * len(package)))
        download_files = list(package.keys())
        download_count = len(download_files)

        def download_callback(name: str) -> bool:
            if not hasattr(callback, "__call__"):
                return True

            # Remove already downloaded file from list
            filename = os.path.basename(name)
            if filename not in download_files:
                return True
            else:
                download_files.remove(filename)

            # Calc download progress
            download_progress = round(100 - len(download_files) / download_count * 100, 2)
            return callback(name, download_progress)

        # Check download path if is not exist create it
        try:
            if not os.path.isdir(path):
                os.makedirs(path)
        except (OSError, FileExistsError) as err:
            raise GogsRequestException(404, "Download attachment error: {}".format(err))

        if parallel:
            # Thread pool parallel download attachment
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as pool:
                result = [pool.submit(self.download, **DynamicObject(name=os.path.join(path, name), url=url,
                                                                     timeout=timeout, callback=download_callback).dict)
                          for name, url in package.items()]

            # Get each file download result
            for name, ret in zip(package.keys(), result):
                download_result[name] = ret.result() if ret.result() is not None else False
        else:
            for name, url in package.items():
                ret = self.download(name=os.path.join(path, name), url=url, timeout=timeout)
                download_result[name] = ret

                # Callback and if return false means cancel download
                if not download_callback(os.path.join(path, name)):
                    break

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
                desc = str(item(".desc")), item(".desc").text()

                attachment = dict()
                for a in item(".download").items():
                    # noinspection SpellCheckingInspection
                    for package in a(".octicon-package").items():
                        package_name = package.next().text()
                        package_href = package.next().attr("href")
                        attachment[package_name] = "{}{}".format(self.__host, package_href)

                releases.append(RepoRelease(name=name, date=date, desc=desc, attachment=attachment))

            return releases
        except requests.RequestException as e:
            print("get_repo_releases exception: {}".format(e))
            return list()

    def upload_attachment(self, attachment: str, timeout: float = 30.0) -> str:
        """
        Upload attachment to server and return uuid
        """
        upload_url = f'{self.__host}/releases/attachments'

        form_data = DynamicObject(
            _csrf=(None, self.__token),
            file=(os.path.basename(attachment), open(attachment, 'rb'), mimetypes.guess_type(attachment)[0])
        )
        ret = self._section.post(upload_url, files=form_data.dict, timeout=timeout or self._timeout)
        ret.raise_for_status()

        try:
            return DynamicObject(**json.loads(ret.content)).uuid
        except (json.decoder.JSONDecodeError, DynamicObjectDecodeError) as e:
            raise GogsRequestException(ret.status_code, f'{e}')

    def upload_repo_avatar(self, repo_path: str, avatar: str, timeout: Optional[float] = None):
        avatar_url = "{}/{}/settings/avatar".format(self.__host, repo_path)
        from_data = DynamicObject(
            _csrf=(None, self.__token), avatar=(os.path.basename(avatar), open(avatar, "rb"))
        )
        ret = self._section.post(avatar_url, files=from_data.dict, timeout=timeout or self._timeout)
        ret.raise_for_status()

    def new_repo_release(self, repo: str, tag: str, title: str, content: str,
                         files: typing.List[str], branch: str = 'master', timeout: float = 30.0):
        url = f'{self.get_repo_url(repo)}/releases/new'
        form_data = DynamicObject(
            _csrf=self.__token, tag_name=tag, tag_target=branch, title=title, content=content, files=files
        )
        ret = self._section.post(url, data=form_data.dict, timeout=timeout or self._timeout)
        ret.raise_for_status()
