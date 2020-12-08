# -*- coding: utf-8 -*-
import os
import json
import socket
import http.client
import pathlib
import hashlib
import datetime
import threading
import socketserver
import http.server
from typing import *
from ..core.datatype import *
from ..misc.settings import *
from ..network.gogs_request import *


NEW_VERSION_DURL_CMD = "GET_NEWEST_DURL"
NEW_VERSION_CHECK_CMD = "GET_NEWEST_VERSION"
__all__ = ['UpgradeClient', 'UpgradeServer', 'UpgradeServerHandler', 'GogsUpgradeClient',
           'GogsSoftwareReleaseDesc', 'GogsUpgradeClientDownloadError']


class UpgradeClient(object):
    def __init__(self, name, addr, port, timeout=3):
        timeout = timeout if isinstance(timeout, int) else 3
        if not isinstance(name, str):
            raise TypeError("name require {!r} not {!r}".format(str.__name__, name.__class__.__name__))

        self.__key = name
        self.__addr = addr
        self.__port = port
        self.__connected = False
        
        # Create a tcp socket
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        try:
            # Connect upgrade server
            self.sock.settimeout(timeout)
            self.sock.connect((self.__addr, self.__port))
            
            # Mark connect success
            self.__connected = True
            
        except (TypeError, socket.error) as e:
            self.__connected = False
            print("Connect server:{}:{} error:{}".format(self.__addr, self.__port, e))
            
    def __del__(self):
        if self.__connected:
            self.sock.close()

    @staticmethod
    def __format_cmd__(cmd, arg):
        """Internal using format command

        :param cmd: commands
        :param arg: commands arg
        :return: return format command
        """
        return "{0:s}:{1:s}".format(cmd, arg).encode()

    def is_connected(self):
        """Check if success connect upgrade server

        :return: True is connected 
        """
        return self.__connected
    
    def has_new_version(self, current_ver):
        """Check if have new version software to upgrade

        :param current_ver: current software version
        :return: True if has new version else False
        """
        try:
            
            if not self.is_connected():
                return False

            current_ver = str2float(current_ver)
            
            # Send request get server newest version info
            self.sock.sendall(self.__format_cmd__(NEW_VERSION_CHECK_CMD, self.__key))
            
            # Get receive data
            recv = self.sock.recv(1024).decode()
            
            # Check new version
            newest_version = str2float(recv)
            return newest_version > current_ver

        except Exception as e:
            print("has_new_version Error:{}".format(e))
            return False
        except socket.error as e:
            print("socket_error: {}".format(e))
            return False

    def get_new_version_info(self):
        """Get new version software information

        :return: result(True or False), download url, file name, file md5, file size
        """
        url = ""
        name = ""
        md5 = ""
        size = 0
        error = (False, url, name, md5, size)

        try:
            
            if not self.is_connected():
                return error
            
            # Send request to get new version download url
            self.sock.sendall(self.__format_cmd__(NEW_VERSION_DURL_CMD, self.__key))
            
            # Get receive data
            recv = self.sock.recv(1024).decode()
                    
            # Check if it's valid url
            if len(recv) == 0 or "http" not in recv or recv.count('#') != 2:
                print("Error:{}".format(recv))
                return error

            data = recv.split("#")
            if len(data) != 3:
                return error

            url = data[0]
            md5 = data[1]
            size = str2number(data[2])
            name = os.path.basename(url)

            return True, url, name, md5, size

        except socket.error as e:
            print("socket_error: {}".format(e))
            return error


# Upgrade File server provide upgrade file download services
class UpgradeFileServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    pass


# Upgrade server built in inquire service and file download service
class UpgradeServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    UPGRADE_PACKAGE_SUFFIX = ".tbz2"
    FILE_SERVER_ROOT = "upgrade_package_repo"

    def __init__(self, upgrade_server_port=9999, file_server_port=8888, file_server_root=FILE_SERVER_ROOT):
        socketserver.TCPServer.__init__(self, ("0.0.0.0", upgrade_server_port), UpgradeServerHandler)

        # Init http file server
        if not self.__initHTTPFileServer(file_server_port, file_server_root):
            raise RuntimeError("Init upgrade http file server failed!")

        self.__file_server = "http://{0:s}:{1:d}".format(self.getHostIPAddr(), file_server_port)
        print("Upgrade server init success:\nInquire server:{}\nDownload server:{}".format(
            (self.getHostIPAddr(), upgrade_server_port), (self.getHostIPAddr(), file_server_port)
        ))

    @staticmethod
    def getHostIPAddr():
        """Get host ip address

        :return:
        """
        try:

            for addr in socket.gethostbyname_ex(socket.gethostname())[2]:
                if not addr.startswith("127."):
                    return addr

            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 53))
            return s.getsockname()[0]
        except socket.error:
            return socket.gethostbyname(socket.gethostname())

    def __initHTTPFileServer(self, port, root):
        """Init a http file server

        :param: file server port
        :param: file server root dir
        :return: do not return
        """
        try:

            # Check root, if is not exist create it
            if not os.path.isdir(root):
                os.makedirs(root)

            # Enter file server root
            os.chdir(root)

            # Create a file server instance
            self.__httpd = UpgradeFileServer((self.getHostIPAddr(), port), http.server.SimpleHTTPRequestHandler)

            # Create a threading serve it
            th = threading.Thread(target=self.__httpd.serve_forever, name="Upgrade file server")
            th.setDaemon(True)
            th.start()
            return True

        except Exception as e:
            print("Init HttpFileServer error:{}".format(e))
            return False

    @staticmethod
    def testHTTPFileServer(server):
        try:

            if not isinstance(server, (tuple, list)) or len(server) != 2:
                return False

            addr, port = server
            if not isinstance(addr, str) or not isinstance(port, int):
                return False

            server = "{0:s}:{1:d}".format(addr, port)

            test = http.client.HTTPConnection(server)
            test.request("HEAD", "")
            if test.getresponse().status == 200:
                return True
            else:
                return False

        except socket.error as e:
            print("Test http server:{}, error:{}".format(server, e))
            return False

    def get_file_server_address(self):
        return self.__file_server

    def get_newest_version(self, software):
        """Get newest software version

        :param software: software name
        :return: software newest version
        """

        package_dir = software

        # Do not have new
        if not os.path.isdir(package_dir):
            return 0.0

        try:

            # Get software upgrade package dir all upgrade files
            file_list = [name for name in os.listdir(package_dir) if self.UPGRADE_PACKAGE_SUFFIX in name]
            version_list = [str2float(os.path.splitext(name)[0]) for name in file_list]
            newest_version = str2float(max(version_list))
            return newest_version

        except Exception as e:
            return 0.0

    def get_newest_version_durl(self, software):
        """Get newest software download address

        :param software: software name
        :return: software info and download url
        """

        try:

            file_md5 = ""

            # First get software newest version
            version = self.get_newest_version(software)

            if version == 0.0:
                return "No new version to download"

            # Get newest version download path
            for name in [x for x in os.listdir(software) if self.UPGRADE_PACKAGE_SUFFIX in x]:
                if str2float(os.path.splitext(name)[0]) == version:
                    file_name = name
                    break
            else:
                return "Do not found software:{0:s}, newest version:{1:f}".format(software, version)

            local_file_path = software + "/" + file_name
            download_url = self.__file_server + "/" + local_file_path

            if os.path.isfile(local_file_path):
                file_md5 = hashlib.md5(open(local_file_path, 'rb').read()).hexdigest()

            return download_url + '#' + file_md5 + '#' + str(os.path.getsize(local_file_path))

        except Exception as e:
            return "Get software:{0:s} download url error:{1:s}".format(software, e)


class UpgradeServerHandler(socketserver.BaseRequestHandler):
    # TCP handler
    def handle(self):
        
        while True:
            try:

                # Check server
                if not isinstance(self.server, UpgradeServer):
                    break

                # Received data
                data = self.request.recv(128).decode().strip().split(":")

                # Check request
                if len(data) != 2:
                    self.request.sendall(b"Error:unknown request, request format error!")
                    break
        
                # Get request and request args
                request = data[0].upper()
                req_arg = data[1]

                # TODO: write log
                # Get newest software version
                if request == NEW_VERSION_CHECK_CMD:
                    self.request.sendall(str(self.server.get_newest_version(req_arg)).encode())
                # Get newest version download url
                elif request == NEW_VERSION_DURL_CMD:
                    self.request.sendall(self.server.get_newest_version_durl(req_arg.encode()))
                else:
                    self.request.sendall(b"Error:unknown request!")
            
            except Exception as e:
                self.request.close()
                print("Error:{}".format(e))
                break


class GogsSoftwareReleaseDesc(JsonSettings):
    _default_path = "release.json"
    _properties = {'name', 'desc', 'size', 'date', 'md5', 'version', 'url'}

    def check(self):
        return self.name and self.size and self.md5 and self.url

    @classmethod
    def default(cls):
        return GogsSoftwareReleaseDesc(name="", desc="", size=0, date="", md5="", version=0.0, url="")

    @classmethod
    def generate(cls, path: str, version: float) -> bool:
        """
        Generate #path specified software release desc
        :param path: software path
        :param version: software version
        :return: success return True
        """
        try:
            desc = GogsSoftwareReleaseDesc(
                date=str(datetime.datetime.fromtimestamp(pathlib.Path(path).stat().st_mtime)),
                md5=hashlib.md5(open(path, "rb").read()).hexdigest(),
                name=os.path.basename(path),
                size=os.path.getsize(path),
                version=version,
                desc="",
                url=""
            )

            return desc.save(os.path.join(os.path.dirname(path), GogsSoftwareReleaseDesc.file_path()))
        except (OSError, ValueError, DynamicObjectEncodeError, AttributeError) as e:
            print("Generate {!r} release desc failed: {}".format(path, e))
            return True


class GogsUpgradeClientDownloadError(Exception):
    pass


class GogsUpgradeClient(object):
    DESC_FILE = GogsSoftwareReleaseDesc.file_path()

    def __init__(self, server: str, repo: str, username="", password=""):
        self._repo = repo
        self._server = server
        self._gogs_client = GogsRequest(server, username, password)

    def get_releases(self) -> List[GogsSoftwareReleaseDesc]:
        release_list = list()

        for release in self._gogs_client.get_repo_releases(self._repo):
            if not isinstance(release, RepoRelease):
                continue

            if self.DESC_FILE not in release.attachments():
                continue

            try:
                response = self._gogs_client.section_get(release.get_attachment_url(self.DESC_FILE))
                if not GogsRequest.is_response_ok(response):
                    continue

                desc = GogsSoftwareReleaseDesc.default()
                desc.update(json.loads(response.content))
                desc.update(DynamicObject(desc=release.desc))
                desc.update(DynamicObject(url=release.get_attachment_url(desc.name)))

                release_list.append(desc)
            except (ValueError, AttributeError, DynamicObjectEncodeError) as e:
                print("{!r} get_releases error {}".format(self.__class__.__name__, e))
                continue

        return release_list

    def get_newest_release(self) -> GogsSoftwareReleaseDesc or None:
        releases = self.get_releases()
        releases = sorted(releases, key=lambda x: x.version, reverse=True)
        return releases[0] if releases else None

    def download_release(self, release: GogsSoftwareReleaseDesc, path: str,
                         callback: Callable[[float, str], bool] or None = None) -> bool:
        if not isinstance(release, GogsSoftwareReleaseDesc) or not release.check():
            raise GogsUpgradeClientDownloadError("Invalid software release desc")

        try:
            if not os.path.isdir(path):
                os.makedirs(path)
        except OSError as e:
            raise GogsUpgradeClientDownloadError("Create download directory failed: {}".format(e))

        download_path = os.path.join(path, release.name)
        if not self._gogs_client.stream_download(download_path, release.url, release.size, callback=callback):
            return False

        if not os.path.isfile(download_path):
            return False

        return hashlib.md5(open(download_path, "rb").read()).hexdigest() == release.md5
