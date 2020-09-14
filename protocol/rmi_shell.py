# -*- coding: utf-8 -*-
import os
import time
import ping3
import tftpy
import random
import string
import socket
import paramiko
import telnetlib
import threading
import ipaddress
from ..protocol.ftp import FTPClient
from ..network.utility import get_host_address
__all__ = ['RMIShellClient', 'RMIShellClientException', 'RMISTelnetClient', 'RMISSecureShellClient', 'TelnetBindNic']


class RMIShellClientException(Exception):
    pass


class TelnetBindNic(telnetlib.Telnet):
    def __init__(self, host=None, port=0, timeout=5, source="", verbose=False):
        super(TelnetBindNic, self).__init__()
        source_address = (source, 0) if source else None
        self.sock = socket.create_connection((host, port), timeout, source_address=source_address)

        if verbose:
            print("Telnet connect: {} ===> {}".format(self.sock.getsockname(), (host, port)))


class RMIShellClient(object):
    TFTP_CLIENT = 'tftp'
    TFTP_DEF_PORT = 69

    def __init__(self, host, timeout=5, source="", verbose=False):
        self._host = host
        self._source = source
        self._timeout = timeout
        self._verbose = verbose

    @staticmethod
    def create_client(connection_type, host, user, password, port=None, timeout=5, source=""):
        if connection_type == "telnet":
            port = port or RMISTelnetClient.DEF_PORT
            return RMISTelnetClient(host=host, user=user, password=password,
                                    port=port, timeout=timeout, source=source)
        elif connection_type == "ssh":
            port = port or RMISSecureShellClient.DEF_PORT
            return RMISSecureShellClient(host=host, user=user, password=password,
                                         port=port, timeout=timeout, source=source)
        else:
            raise RMIShellClientException("Unknown connection type: {!r}".format(connection_type))

    @staticmethod
    def check_exec_result(result, pass_output):
        for ret in result.split("\r\n"):
            if pass_output in ret:
                return True

        return False

    def create_new_connection(self, source):
        return None

    def exec(self, command, params=None, tail=None, timeout=0, verbose=False):
        pass

    def connected(self):
        return self.is_dir_exist('/')

    def get_memory_info(self):
        """Get memory usage from /proc/meminfo

        :return: MemTotal/MemFree
        """
        result = self.exec("cat /proc/meminfo | awk '{print $2}' | head -2").split('\n')
        if len(result) != 2:
            raise RMIShellClientException("Get memory usage failed")
        return tuple([int(x) for x in result])

    def get_cpu_usage_dict(self):
        """Get cpu usage from top

        :return: cpu usage
        """
        result = self.exec("top -n 1 | sed '2!d'").strip()
        result = [x for x in result.split(":")[-1].split(" ") if len(x)]
        return dict(zip(result[1::2], result[::2]))

    def get_disk_usage_dict(self):
        disk = dict()
        header = ['filesystem', 'size', 'used', 'available', 'percentage', 'mounted_on']
        result = self.exec("df -h").strip().split("\n")
        if len(result) < 2:
            return dict()

        for item in result[1:]:
            item.strip()
            data = [x.strip() for x in item.split(" ") if len(x)]
            disk[data[0]] = dict(zip(header, data))

        return disk

    def get_memory_usage_dict(self):
        cmd = string.Template("top -n 1 | sed '1!d' | awk '{print $column}'").substitute(
            column=" ".join(["${}".format(c) for c in range(2, 12)])
        )
        usage = dict()
        result = self.exec(cmd).strip()
        for item in result.split(","):
            mem = item.split("K")
            if len(mem) != 2:
                continue

            usage[mem[1]] = int(mem[0])

        return usage

    def get_process_info_dict(self, pid):
        """cat /proc/pid/status"""
        result = self.exec("cat /proc/{}/status".format(pid)).strip().split('\n')
        return dict(
            zip([x.split(":")[0] for x in result if ":" in x], [x.split(":")[-1].strip() for x in result if ":" in x])
        )

    def get_memory_info_dict(self, unit="kB"):
        """cat cat /proc/meminfo"""
        info = dict()
        unit = unit.lower() if isinstance(unit, str) else "kb"

        memory_unit_factor = {
            "kb": 1,
            "mb": 1024,
            "gb": 1024 ** 2
        }.get(unit, 1)

        result = self.exec("cat /proc/meminfo").strip().split('\n')
        for item in result:
            if ":" not in item:
                continue

            data = item.split(":")
            usage = data[-1].strip().split(" ")
            info[data[0].strip()] = int(usage[0]) // memory_unit_factor

        return info

    def is_alive(self, timeout=1):
        return ping3.ping(dest_addr=self._host, timeout=timeout) is not None

    def is_exist(self, abs_path):
        return True if '0' in self.exec("test", ["-e", abs_path, "&&", "echo $?"]) else False

    def is_dir_exist(self, dir_abs_path):
        return True if '0' in self.exec("test", ["-d", dir_abs_path, "&&", "echo $?"]) else False

    def is_file_exist(self, file_abs_path):
        return True if '0' in self.exec("test", ["-f", file_abs_path, "&&", "echo $?"]) else False

    def exec_script_get_result(self, script_path, timeout=0):
        if not self.is_file_exist(script_path):
            raise RMIShellClientException("Script: [{}] do not exist".format(script_path))

        return self.exec("chmod", ["a+x", script_path, "&&", script_path], timeout=timeout)

    def tftp_upload_file(self, local_file, remote_path="/tmp", remote_name="",
                         network=None, random_port=True, verbose=False):
        """
        Uoload a local_file from local to remote
        :param local_file: file to upload
        :param remote_path: file upload to remote path
        :param remote_name: if is not empty will rename to this name
        :param network: tftp server network(ipaddress.IPv4Network)
        :param random_port: tftp using random port
        :param verbose: display verbose info
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
        try:
            server_address = str(ipaddress.ip_address(self._source))
        except ValueError:
            server_address = get_host_address(network)[0]

        server_port = random.randint(1024, 65535) if random_port else self.TFTP_DEF_PORT

        tftp_server = tftpy.TftpServer(os.path.dirname(local_file))
        tftp_listen_thread = threading.Thread(target=server_listen, args=(tftp_server, server_address, server_port))
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


class RMISTelnetClient(RMIShellClient):
    DEF_PORT = 23
    LOGIN_PROPMT, PASSWORD_PROPMT, SHELL_PROPMT = (b'login:', b'Password:', b'#')

    def __init__(self, host, user, password, port=DEF_PORT,
                 timeout=5, shell_prompt=SHELL_PROPMT, source="", verbose=False):
        super(RMISTelnetClient, self).__init__(host, timeout, source, verbose)
        self._port = port
        self._user = user
        self._password = password
        self._shell_prompt = shell_prompt
        self.client = self.create_new_connection(source)
        if verbose:
            print("Login in:{}".format("success" if self.connected() else "failed"))

    def __del__(self):
        try:
            self.client.close()
        except AttributeError:
            pass

    def create_new_connection(self, source):
        try:
            client = TelnetBindNic(host=self._host, port=self._port,
                                   timeout=self._timeout, source=source, verbose=self._verbose)
            # Login in
            if self.LOGIN_PROPMT not in client.read_until(self.LOGIN_PROPMT, self._timeout):
                raise RMIShellClientException("Login failed")

            client.write("{}\n".format(self._user).encode())

            if self._password:
                if self.PASSWORD_PROPMT not in client.read_until(self.PASSWORD_PROPMT, self._timeout):
                    raise RMIShellClientException("Wait input password failed")

                client.write("{}\n".format(self._password).encode())

            # Wait shell prompt
            if self._shell_prompt not in client.read_until(self._shell_prompt, self._timeout):
                raise RMIShellClientException("Wait shell prompt[{}] failed".format(self._shell_prompt))

            return client
        except (EOFError, ConnectionError, ConnectionRefusedError, TimeoutError, socket.timeout, OSError) as error:
            raise RMIShellClientException("Login error: {}".format(error))

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
        except (AttributeError, EOFError, UnicodeDecodeError) as err:
            print("Exec:[{}] error:{}".format(command, err))
            return ""


class RMISSecureShellClient(RMIShellClient):
    DEF_PORT = 22

    def __init__(self, host, user, password, port=DEF_PORT, timeout=5, source="",  verbose=False):
        super(RMISSecureShellClient, self).__init__(host, timeout, source, verbose)
        self._port = port
        self._user = user
        self._password = password
        self.client = self.create_new_connection(source)
        if verbose:
            print("Login in:{}".format("success" if self.connected() else "failed"))

    def __del__(self):
        try:
            self.client.close()
        except AttributeError:
            pass

    def create_new_connection(self, source):
        sock = None

        try:
            client = paramiko.SSHClient()
            address = (self._host, self._port)
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            sock = socket.create_connection(address, self._timeout, source_address=(source, 0)) if source else None

            if self._verbose:
                print("SSH connect: {} ===> {}".format(sock.getsockname(), address))

            client.connect(hostname=self._host, port=self._port,
                           username=self._user, password=self._password, sock=sock)

            return client
        except (paramiko.ssh_exception.SSHException, paramiko.ssh_exception.NoValidConnectionsError,
                ConnectionError, TimeoutError, socket.error, OSError) as error:
            if isinstance(sock, socket.socket):
                sock.close()
            raise RMIShellClientException(error)

    def exec(self, command, params=None, tail=None, timeout=0, verbose=False):
        try:
            command.strip()
            params = params or list()
            timeout = timeout or self._timeout
            cmd = "{} {}\n".format(command, " ".join(params)) if params else "{}\n".format(command)
            if verbose or self._verbose:
                print(cmd.strip())
            _, out, err = self.client.exec_command(cmd, timeout=timeout)
            result = (out.read() + err.read()).decode()
            return "\n".join(result.split("\n"))[:-1]
        except (paramiko.SSHException, socket.timeout, AttributeError, UnicodeDecodeError) as err:
            print("Exec:[{}] error:{}".format(command, err))
            return ""
