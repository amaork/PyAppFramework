# -*- coding: utf-8 -*-
import os
import time
import tftpy
import random
import telnetlib
import threading
from ..protocol.ftp import FTPClient
from ..network.utility import get_host_address
__all__ = ['TelnetClient', 'TelnetClientException']


class TelnetClientException(Exception):
    pass


class TelnetClient(object):
    TFTP_CLIENT='tftp'
    TFTP_DEF_PORT = 69
    LOGIN_PROPMT, PASSWORD_PROPMT, SHELL_PROPMT = (b'login:', b'Password:', b'#')

    def __init__(self, host, user, password, port=22, timeout=5, shell_prompt=SHELL_PROPMT, verbose=False):
        self._port = port
        self._host = host
        self._user = user
        self._verbose = verbose
        self._timeout = timeout
        self._password = password
        self._shell_prompt = shell_prompt
        self.client = self.create_new_connection()
        if verbose:
            print("Login in:{}".format("success" if self.connected() else "failed"))

    def create_new_connection(self):
        client = telnetlib.Telnet(host=self._host, port=self._port, timeout=self._timeout)

        try:
            # Login in
            if self.LOGIN_PROPMT not in client.read_until(self.LOGIN_PROPMT, self._timeout):
                raise TelnetClientException("Login failed")

            client.write("{}\n".format(self._user).encode())

            if self._password:
                if self.PASSWORD_PROPMT not in client.read_until(self.PASSWORD_PROPMT, self._timeout):
                    raise TelnetClientException("Wait input password failed")

                client.write("{}\n".format(self._password).encode())

            # Wait shell prompt
            if self._shell_prompt not in client.read_until(self._shell_prompt, self._timeout):
                raise TelnetClientException("Wait shell prompt[{}] failed".format(self._shell_prompt))

            return client
        except (EOFError, ConnectionError) as error:
            raise TelnetClientException("Login error: {}".format(error))

    def exec(self, command, params=None, tail=None, timeout=0, verbose=False):
        try:
            command.strip()
            params = params or list()
            tail = tail or self._shell_prompt
            timeout = timeout or self._timeout
            cmd = "{} {}\n".format(command, " ".join(params)) if params else "{}\n".format(command)
            if verbose or self._verbose:
                print(cmd.strip())
            self.client.write(cmd.encode())
            result = self.client.read_until(tail, timeout=timeout).decode()
            return "\n".join(result.split("\n")[1:-1])
        except EOFError as err:
            print("Exec:[{}] error:{}".format(command, err))
            return ""

    def connected(self):
        return self.is_dir_exist('/')

    def is_exist(self, abs_path):
        return True if '0' in self.exec("test", ["-e", abs_path, "&&", "echo $?"]) else False

    def is_dir_exist(self, dir_abs_path):
        return True if '0' in self.exec("test", ["-d", dir_abs_path, "&&", "echo $?"]) else False

    def is_file_exist(self, file_abs_path):
        return True if '0' in self.exec("test", ["-f", file_abs_path, "&&", "echo $?"]) else False

    def exec_script_get_result(self, script_path, timeout=0):
        if not self.is_file_exist(script_path):
            raise TelnetClientException("Script: [{}] do not exist".format(script_path))

        return self.exec("chmod", ["a+x", script_path, "&&", script_path], timeout=timeout)

    def tftp_upload_file(self, local_file, remote_path="/tmp", remote_name="", verbose=False, random_port=True):
        """
        Uoload a local_file from local to remote
        :param local_file: file to upload
        :param remote_path: file upload to remote path
        :param remote_name: if is not empty will rename to this name
        :param verbose: display verbose info
        :param random_port: tftp using random port
        :return: success return true, failed return false
        """
        def server_listen(server, address, port):
            if not isinstance(tftp_server, tftpy.TftpServer):
                return

            server.listen(address, port)

        if not os.path.isfile(local_file):
            return False

        remote_name = remote_name or os.path.basename(local_file)
        remote_file = FTPClient.join(remote_path, remote_name)

        # Start ftp server
        server_address = get_host_address()
        server_port = random.randint(1024, 65535) if random_port else self.TFTP_DEF_PORT

        tftp_server = tftpy.TftpServer(os.path.dirname(local_file))
        args = args=(tftp_server, server_address, server_port)
        tftp_listen_thread = threading.Thread(target=server_listen, args=args)
        tftp_listen_thread.setDaemon(True)
        tftp_listen_thread.start()
        time.sleep(1)

        # Download file
        ret = self.exec(self.TFTP_CLIENT,
                        ["-g", "-r", os.path.basename(local_file), "-l", remote_file, server_address, str(server_port)],
                        verbose=verbose)

        if self._verbose or verbose:
            print(ret)

        # Stop ftp server
        tftp_server.stop(True)
        self.exec("sync")

        # Check if download success
        return self.is_file_exist(remote_file)
