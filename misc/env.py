# -*- coding: utf-8 -*-
import os
import sys
import time
import platform
__all__ = ['RunEnvironment']


class RunEnvironment(object):
    _LOG_TS_FMT = '%Y-%m-%d-%H%M%S'
    _SYSTEM = platform.system().lower()
    _MACHINE = platform.machine().lower()

    def __init__(self, name: str = '', version: float = 0.0, log_dir: str = 'logging', conf_dir: str = 'config'):
        """Software running environment

        :param name: software name
        :param version: software name
        :param log_dir: software logging directory
        :param conf_dir: software configure directory
        """
        self.__name = name
        self.__version = version
        self.__log_dir = log_dir
        self.__conf_dir = conf_dir
        os.makedirs(self.__log_dir, exist_ok=True)
        os.makedirs(self.__conf_dir, exist_ok=True)

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
        return RunEnvironment._MACHINE == "armv7l"

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
    def log_dir(self) -> str:
        return self.__log_dir[:]

    @property
    def conf_dir(self) -> str:
        return self.__conf_dir[:]

    def get_log_file(self, module_name: str, with_timestamp: bool = False) -> str:
        os.makedirs(os.path.join(self.log_dir, module_name), 0o755, True)
        timestamp = f'_{time.strftime(self._LOG_TS_FMT)}' if with_timestamp else ''
        return os.path.join(self.log_dir, module_name, f'{module_name}{timestamp}.log')

    def get_config_file(self, module_name: str):
        return os.path.join(self.conf_dir, f"{module_name}.json")

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
