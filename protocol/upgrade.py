# -*- coding: utf-8 -*-

import os
import socket
import hashlib
import SocketServer
from ..core.datatype import str2float, str2number


NEW_VERSION_DURL_CMD = "GET_NEWEST_DURL"
NEW_VERSION_CHECK_CMD = "GET_NEWEST_VERSION"


__all__ = ['UpgradeClient', 'UpgradeServer', 'UpgradeServerHandler']


class UpgradeClient(object):
    def __init__(self, name, addr, port, timeout=3):
        timeout = timeout if isinstance(timeout, int) else 3
        assert isinstance(name, str), "Name TypeError: {0:s}".format(type(name))
        assert isinstance(addr, str), "Address TypeError: {0:s}".format(type(addr))
        assert isinstance(port, int), "Port TypeError: {0:s}".format(type(port))
        assert 1024 < port <= 65536, "Port range error:{0:d}".format(port)
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
            
        except socket.error, e:
            self.__connected = False
            print "Connect server:{0:s}:{1:d} error:{2:s}".format(self.__addr, self.__port, e)
            
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

        except StandardError, e:
            print "has_new_version Error:{0:s}".format(e)
            return False
        except socket.error, e:
            print "socket_error: {0:s}".format(e)
            return False

    def get_new_version_info(self):
        """Get new version software infomaction

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
                return error

            data = recv.split("#")
            if len(data) != 3:
                return error

            url = data[0]
            md5 = data[1]
            size = str2number(data[2])
            name = os.path.basename(url)

            return True, url, name, md5, size

        except StandardError, e:
            print "get_new_version_url Error:{0:s}".format(e)
            return error
        except socket.error, e:
            print "socket_error: {0:s}".format(e)
            return error


class UpgradeServer(SocketServer.ThreadingMixIn, SocketServer.TCPServer):
    pass


class UpgradeServerHandler(SocketServer.BaseRequestHandler):
    
    # Upgrade package suffix
    UPGRADE_PACKAGE_SUFFIX = ".tbz2"
    
    # Upgrade packages store dir
    UPGRADE_PACKAGE_DIR ="/home/amaork/software_upgrade_server"
    
    # Upgrade server base url
    UPGRADE_SERVER_BASE_URL = "http://127.0.0.0:8888/"
    
    # TCP handler
    def handle(self):
        
        while True:
            try:
            
                # Received data
                data = self.request.recv(128).strip().split(":")
        
                # Check request
                if len(data) != 2:
                    self.request.sendall("Error:unknown request, request format error!")
                    return False
        
                # Get request and request args
                request = data[0].upper()
                req_arg = data[1]
                
                # Get newest software version
                if request == NEW_VERSION_CHECK_CMD:
                    self.request.sendall(str(self.get_newest_version(req_arg)))
                elif request == NEW_VERSION_DURL_CMD:
                    self.request.sendall(self.get_download_url(req_arg))
                else:
                    self.request.sendall("Error:unknown request!")
            
            except StandardError, e:
                self.request.close()
                print "Error:{0:s}".format(e)
                continue
                
    def get_newest_version(self, name):
        """Get newest software version

        :param name: software name
        :return: software newest version
        """

        package_dir = os.path.join(self.UPGRADE_PACKAGE_DIR, name)
        
        # Do not have new
        if not os.path.isdir(package_dir):
            return 0.0
        
        try:
        
            file_list = filter(lambda name: self.UPGRADE_PACKAGE_SUFFIX in name, os.listdir(package_dir))
            version_list = [float(os.path.splitext(name)[0]) for name in file_list]
            newest_version = str2float(max(version_list))
            return newest_version
                 
        except StandardError, e:
            print "get_newest_version Error: {0:s}".format(e)
            return 0.0

    def get_download_url(self, name):
        """Get newest software download address

        :param name: software name
        :return: software info and download url
        """

        file_md5 = ""
        # First get software newest version
        newest_version = self.get_newest_version(name)

        if newest_version == 0.0:
            return "No newest version to download"
        
        # Get newest version download path
        newest_version_file = str(newest_version) + self.UPGRADE_PACKAGE_SUFFIX
        download_url = self.UPGRADE_SERVER_BASE_URL + os.path.join(name, newest_version_file)
        local_file_path = os.path.join(self.UPGRADE_PACKAGE_DIR, os.path.join(name, newest_version_file))
        
        if os.path.isfile(local_file_path):
            file_md5 = hashlib.md5(open(local_file_path, 'rb').read()).hexdigest()
        
        return download_url + '#' + file_md5 + '#' + str(os.path.getsize(local_file_path))
