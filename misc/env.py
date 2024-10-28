# -*- coding: utf-8 -*-
import os
import sys
import time
import typing
import platform

from .settings import JsonSettings
from ..misc.crypto import AESCrypto
from ..core.datatype import DynamicObject
from ..protocol.upgrade import GogsUpgradeClient
__all__ = ['RunEnvironment', 'GogsReleasePublishEnvironment']


class RunEnvironment(object):
    _LOG_TS_FMT = '%Y-%m-%d-%H%M%S'
    _SYSTEM = platform.system().lower()
    _MACHINE = platform.machine().lower()

    def __init__(self, name: str = '', version: float = 0.0,
                 log_dir: str = 'logging', conf_dir: str = 'config',
                 logfile_keep_days: int = 0, gogs_repo: str = '', gogs_update_server: str = '',
                 server_user: str = '', server_pwd: str = '', aes_key: bytes = b'', aes_iv: bytes = b''):
        """Software running environment

        :param name: software name
        :param version: software name
        :param log_dir: software logging directory
        :param conf_dir: software configure directory
        :param logfile_keep_days: logfile keep max days
        :param gogs_repo: gogs software update server repo name
        :param gogs_update_server: gogs software update server(gogs release) url
        :param server_user: update server username
        :param server_pwd: update server user password
        :param aes_key: aes key using encrypt/decrypt software update packet
        :param aes_iv: aes iv using  encrypt/decrypt software update packet
        """
        self.__name = name
        self.__version = version
        self.__log_dir = log_dir
        self.__conf_dir = conf_dir

        # Software update using
        self.__aes_iv = aes_iv
        self.__aes_key = aes_key

        self.__gogs_repo = gogs_repo
        self.__server_pwd = server_pwd
        self.__server_user = server_user
        self.__gogs_update_server = gogs_update_server

        os.makedirs(self.__log_dir, exist_ok=True)
        os.makedirs(self.__conf_dir, exist_ok=True)

        if logfile_keep_days:
            for module in os.listdir(self.__log_dir):
                self.logfile_process(module, logfile_keep_days)

    @staticmethod
    def reboot():
        os.system("sync && reboot") if RunEnvironment.is_linux() else sys.exit(0)

    @staticmethod
    def is_osx():
        return RunEnvironment._SYSTEM == "darwin"

    @staticmethod
    def is_linux():
        return RunEnvironment._SYSTEM == "linux"

    @staticmethod
    def is_windows():
        return RunEnvironment._SYSTEM == "windows"

    @staticmethod
    def is_raspberry():
        # noinspection SpellCheckingInspection
        return RunEnvironment._MACHINE in 'armv7l aarch64'

    @staticmethod
    def system_version():
        return int(platform.release())

    @staticmethod
    def system_name() -> str:
        return RunEnvironment._SYSTEM[:]

    @property
    def software_name(self) -> str:
        return self.__name[:]

    @property
    def software_version(self) -> float:
        return self.__version

    @property
    def editor(self):
        if self.is_linux():
            # noinspection SpellCheckingInspection
            return "leafpad"
        else:
            return "notepad.exe" if os.path.isfile(os.path.join(r'C:\Windows', "notepad.exe")) else "write.exe"

    @property
    def log_dir(self) -> str:
        return self.__log_dir[:]

    @property
    def conf_dir(self) -> str:
        return self.__conf_dir[:]

    @property
    def gogs_repo(self) -> str:
        return self.__gogs_repo[:]

    @property
    def gogs_server_url(self) -> str:
        return self.__gogs_update_server[:]

    def __check_and_create_crypto(self, desc: str) -> AESCrypto:
        if not self.__aes_key or not self.__aes_iv:
            raise ValueError(f'software run env do not support {desc}')

        return AESCrypto(self.__aes_key, iv=self.__aes_iv)

    def encrypt(self, data: bytes) -> bytes:
        return self.__check_and_create_crypto('encrypt').encrypt(data)

    def decrypt(self, data: bytes) -> bytes:
        return self.__check_and_create_crypto('decrypt').decrypt(data)

    def encrypt_file(self, src: str, dest: str):
        self.__check_and_create_crypto('encrypt').encrypt_file(src, dest)

    def decrypt_file(self, src: str, dest: str):
        self.__check_and_create_crypto('decrypt').decrypt_file(src, dest)

    def logfile_process(self, module_name: str, keep_days: int):
        def get_logfile_date(name: str) -> str:
            return name.split('_')[-1][:10]

        dates = {get_logfile_date(x) for x in os.listdir(os.path.join(os.path.join(self.__log_dir, module_name)))}
        if len(dates) <= keep_days:
            return

        keep_date = sorted(dates, reverse=True)[:keep_days]
        for file in os.listdir(os.path.join(os.path.join(self.__log_dir, module_name))):
            if get_logfile_date(file) in keep_date:
                continue

            try:
                os.unlink(os.path.join(self.__log_dir, module_name, file))
            except OSError:
                pass

    def get_log_file(self, module_name: str, with_timestamp: bool = False) -> str:
        os.makedirs(os.path.join(self.log_dir, module_name), 0o755, True)
        timestamp = f'_{time.strftime(self._LOG_TS_FMT)}' if with_timestamp else ''
        return os.path.join(self.log_dir, module_name, f'{module_name}{timestamp}.log')

    def get_config_file(self, module_name: str):
        return os.path.join(self.conf_dir, f"{module_name}.json")

    def get_gogs_update_client(self, repo: str = '') -> GogsUpgradeClient:
        repo = repo or self.__gogs_repo
        return GogsUpgradeClient(self.__gogs_update_server, repo, self.__server_user, self.__server_pwd)

    def run_in_background(self, path: str, name: str) -> bool:
        """Run app in background

        :param path: app path
        :param name: app name
        :return: success return true
        """
        pwd = os.getcwd()

        try:

            os.chdir(path)

            if self.is_linux():
                os.system("./{} &".format(name))
            else:
                os.system("START /B {}".format(name))

            return True
        except Exception as err:
            print("Run app in background error:{}".format(err))
            return False
        finally:
            os.chdir(pwd)


class GogsReleasePublishEnvironment(JsonSettings):
    _properties = {'username', 'password', 'publish_keys'}

    @classmethod
    def default(cls) -> DynamicObject:
        return GogsReleasePublishEnvironment(username='', password='', publish_keys=dict())

    def get_key(self, name: str) -> typing.Tuple[bytes, bytes]:
        raw = self.publish_keys.get(name, '')
        try:
            _, key, iv, _ = raw.split('#')
            return key.encode(), iv.encode()
        except (TypeError, ValueError, AttributeError):
            return bytes(), bytes()
