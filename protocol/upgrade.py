# -*- coding: utf-8 -*-
import os
import socket
import httplib
import hashlib
import threading
import SocketServer
import SimpleHTTPServer
from ..core.datatype import str2float, str2number


NEW_VERSION_DURL_CMD = "GET_NEWEST_DURL"
NEW_VERSION_CHECK_CMD = "GET_NEWEST_VERSION"
__all__ = ['UpgradeClient', 'UpgradeServer', 'UpgradeServerHandler']


class UpgradeClient(object):
    def __init__(self, name, addr, port, timeout=3):
        timeout = timeout if isinstance(timeout, int) else 3
        if not isinstance(name, str):
            raise RuntimeError("Name TypeError: {0:s}".format(type(name)))

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
            print("Connect server:{0:s}:{1:d} error:{2:s}".format(self.__addr, self.__port, e))
            
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
        return "{0:s}:{1:s}".format(cmd, arg)

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
            recv = self.sock.recv(1024)
            
            # Check new version
            newest_version = str2float(recv)
            return newest_version > current_ver

        except StandardError as e:
            print("has_new_version Error:{0:s}".format(e))
            return False
        except socket.error as e:
            print("socket_error: {0:s}".format(e))
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
            recv = self.sock.recv(1024)
                    
            # Check if it's valid url
            if len(recv) == 0 or "http" not in recv or recv.count('#') != 2:
                print("Error:{0:s}".format(recv))
                return error

            data = recv.split("#")
            if len(data) != 3:
                return error

            url = data[0]
            md5 = data[1]
            size = str2number(data[2])
            name = os.path.basename(url)

            return True, url, name, md5, size

        except StandardError as e:
            print("get_new_version_url Error:{0:s}".format(e))
            return error
        except socket.error as e:
            print("socket_error: {0:s}".format(e))
            return error


# Upgrade File server provide upgrade file download services
class UpgradeFileServer(SocketServer.ThreadingMixIn, SocketServer.TCPServer):
    pass


# Upgrade server built in inquire service and file download service
class UpgradeServer(SocketServer.ThreadingMixIn, SocketServer.TCPServer):
    UPGRADE_PACKAGE_SUFFIX = ".tbz2"
    FILE_SERVER_ROOT = "upgrade_package_repo"

    def __init__(self, upgrade_server_port=9999, file_server_port=8888, file_server_root=FILE_SERVER_ROOT):
        SocketServer.TCPServer.__init__(self, ("0.0.0.0", upgrade_server_port), UpgradeServerHandler)

        # Init http file server
        if not self.__initHTTPFileServer(file_server_port, file_server_root):
            raise RuntimeError("Init upgrade http file server failed!")

        self.__file_server = "http://{0:s}:{1:d}".format(self.getHostIPAddr(), file_server_port)
        print("Upgrade server init success:\nInquire server:{0:s}\nDownload server:{1:s}".format(
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
            self.__httpd = UpgradeFileServer((self.getHostIPAddr(), port), SimpleHTTPServer.SimpleHTTPRequestHandler)

            # Create a threading serve it
            th = threading.Thread(target=self.__httpd.serve_forever, name="Upgrade file server")
            th.setDaemon(True)
            th.start()
            return True

        except StandardError as e:
            print("Init HttpFileServer error:{0:s}".format(e))
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

            test = httplib.HTTPConnection(server)
            test.request("HEAD", "")
            if test.getresponse().status == 200:
                return True
            else:
                return False

        except socket.error as e:
            print("Test http server:{0:s}, error:{1:s}".format(server, e))
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
            file_list = filter(lambda name: self.UPGRADE_PACKAGE_SUFFIX in name, os.listdir(package_dir))
            version_list = [str2float(os.path.splitext(name)[0]) for name in file_list]
            newest_version = str2float(max(version_list))
            return newest_version

        except StandardError as e:
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
            for name in filter(lambda x: self.UPGRADE_PACKAGE_SUFFIX in x, os.listdir(software)):
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

        except StandardError as e:
            return "Get software:{0:s} download url error:{1:s}".format(software, e)


class UpgradeServerHandler(SocketServer.BaseRequestHandler):
    # TCP handler
    def handle(self):
        
        while True:
            try:

                # Check server
                if not isinstance(self.server, UpgradeServer):
                    break

                # Received data
                data = self.request.recv(128).strip().split(":")

                # Check request
                if len(data) != 2:
                    self.request.sendall("Error:unknown request, request format error!")
                    break
        
                # Get request and request args
                request = data[0].upper()
                req_arg = data[1]

                # TODO: write log
                # Get newest software version
                if request == NEW_VERSION_CHECK_CMD:
                    self.request.sendall(str(self.server.get_newest_version(req_arg)))
                # Get newest version download url
                elif request == NEW_VERSION_DURL_CMD:
                    self.request.sendall(self.server.get_newest_version_durl(req_arg))
                else:
                    self.request.sendall("Error:unknown request!")
            
            except StandardError as e:
                self.request.close()
                print("Error:{0:s}".format(e))
                break
