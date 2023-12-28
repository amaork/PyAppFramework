# -*- coding: utf-8 -*-
import os
import socket
import psutil
import hashlib
import platform
import ipaddress
import subprocess
from typing import List, Optional, Dict

from ..misc.crypto import *
from ..core.datatype import DynamicObject, str2number, str2float
__all__ = ['MachineInfo', 'MachineCode', 'RegistrationCode']

_RAW_MC_LEN = 64
_RSA_MSG_LEN = 384

"""
Logic:
Software build-in `MachineCode` with RSA public key
Registration Machine build-in `RegistrationCode` with RSA private key

Everytime software boot will check MachineCode.verify function to check if software is registered, if not do something

Software register process:
1. Software through MachineCode.get_machine_code to get machine fingerprint then using public encrypt send to developer
2. Developer decrypt to get raw fingerprint, then using private key sign raw fingerprint send signature to user
3. User launch register interface, fill signature, then call MachineCode.register(verify signature) finished register

Notice:
1. Machine's fingerprint must be unique
2. Software build-in RSA public key using encrypt fingerprint and verify signature
3. Registration Machine build-in RSA private decrypt fingerprint and distribute signature

"""


class MachineInfo(object):
    def __init__(self):
        """
        Get machine hardware info to generate unique fingerprint
          try:
            pythoncom.CoInitialize()
            XXX: Get machine info
        finally:
            pythoncom.CoUninitialize()
        """

    @staticmethod
    def get_os_info() -> dict:
        if platform.system().lower() == "windows":
            import wmi

            w = wmi.WMI()
            os_ = w.Win32_OperatingSystem()[0]
            return dict(caption=os_.Caption, version=os_.Version,
                        tz=os_.CurrentTimeZone, language=os_.MUILanguages[0],
                        arch=os_.OSArchitecture, sn=os_.SerialNumber, system_device=os_.SystemDevice)
        else:
            os_ = os.uname()
            return dict(caption="{}/{}".format(os_[0], os_[1]), version=os_[3], arch=os_[4])

    @staticmethod
    def get_cpu_info() -> List[dict]:
        if platform.system().lower() == "windows":
            import wmi

            cpu = list()
            w = wmi.WMI()
            for processor in w.Win32_Processor():
                cpu.append(
                    {
                        'name': processor.Name,
                        'sn': processor.ProcessorId,
                        'core_num': processor.NumberOfCores
                    }
                )

            return cpu
        else:
            sn = ''
            name = ''
            core_num = 1
            data = open('/proc/cpuinfo').read()
            for line in data.split('\n'):
                if 'model name' in line:
                    name = line.split(':')[-1].strip()

                if 'cpu cores' in line:
                    core_num = str2number(line.split(':')[-1].strip())

                if 'Serial' in line:
                    sn = line.split(':')[-1].strip()

            return [dict(name=name, sn=sn, core_num=core_num)]

    @staticmethod
    def get_disk_info() -> List[dict]:
        if platform.system().lower() == "windows":
            import wmi
            w = wmi.WMI()
            disk = list()
            for dd in w.Win32_DiskDrive():
                try:
                    sn = w.Win32_PhysicalMedia()[0].SerialNumber.lstrip().rstrip()
                except AttributeError:
                    sn = ""

                if not dd.Size:
                    continue

                disk.append(
                    {
                        "sn": sn,
                        "id": dd.deviceid,
                        "caption": dd.Caption,
                        "size": str(int(str2float(dd.Size) / 1024 / 1024 / 1024))
                    }
                )

            return disk
        else:
            disk = list()
            header = ['filesystem', 'size', 'used', 'available', 'percentage', 'mounted_on']
            si = subprocess.Popen('df -h', stdout=subprocess.PIPE, shell=True)
            result = si.communicate()[0].decode().split('\n')

            for item in result[1:]:
                item.strip()
                data = [x.strip() for x in item.split(" ") if len(x)]
                disk.append(dict(zip(header, data)))

            return disk

    @staticmethod
    def get_network_info() -> List[dict]:
        if platform.system().lower() == "windows":
            import wmi
            w = wmi.WMI()
            network = list()
            for nac in w.Win32_NetworkAdapterConfiguration():
                if nac.MacAddress is None or nac.IPAddress is None:
                    continue

                if ipaddress.ip_address(nac.IPAddress[0]).is_loopback:
                    continue

                network.append(
                    {
                        'desc': nac.Description,
                        'mac': nac.MACAddress,
                        'ip': nac.IPAddress
                    }
                )

            return network
        else:
            network = list()
            for name, data in psutil.net_if_addrs().items():
                ip = ""
                mac = ""
                for item in data:
                    if item.family == psutil.AF_LINK:
                        mac = item.address

                    if item.family == socket.AF_INET:
                        ip = item.address

                if not mac or not ip:
                    continue

                if ipaddress.ip_address(ip).is_loopback:
                    continue

                network.append(dict(desc=name, ip=ip, mac=mac))

            return network

    @staticmethod
    def get_logic_disk_info() -> List[dict]:
        if platform.system().lower() == "windows":
            import wmi
            w = wmi.WMI()
            logic_disk = list()
            for disk in w.Win32_LogicalDisk(DriveType=3):
                logic_disk.append(
                    {
                        'caption': disk.Caption,
                        'filesystem': disk.FileSystem,
                        'free': disk.FreeSpace,
                        'size': disk.Size,
                        'name': disk.VolumeName,
                        'sn': disk.VolumeSerialNumber
                    }
                )

            return logic_disk
        else:
            return MachineInfo.get_disk_info()


class MachineCode(object):
    CPU_KEY, DISK_KEY, NETWORK_KEY = ('cpu', 'disk', 'network')

    def __init__(self, rsa_public_key: str, register_file: str, options: Optional[Dict[str, bool]] = None):
        self._mci = MachineInfo()
        self._register_file = register_file
        self._public_key = RSAPublicKeyHandle(rsa_public_key)
        self._options = options if isinstance(options, dict) else dict(cpu=True, disk=True, network=True)

        if set([self._options.get(x) for x in (self.CPU_KEY, self.DISK_KEY, self.NETWORK_KEY)]) == {False}:
            raise ValueError("'options' required one of {!r} set")

        if not self._register_file:
            raise RuntimeError('please specified register file')

    def raw_fingerprint(self) -> bytes:
        if platform.system().lower() == "windows":
            import pythoncom

            try:
                pythoncom.CoInitialize()
                return self._generate_fingerprint()
            finally:
                pythoncom.CoUninitialize()
        else:
            return self._generate_fingerprint()

    def _generate_fingerprint(self) -> bytes:
        """Your can implement your own version machine fingerprint"""
        if self._options.get(self.CPU_KEY):
            cpu = DynamicObject(**self._mci.get_cpu_info()[0])
            cpu_id = cpu.sn + str(cpu.core_num)
        else:
            cpu_id = ''

        if self._options.get(self.DISK_KEY):
            disk = DynamicObject(**self._mci.get_disk_info()[0])
            disk_id = disk.sn + str(disk.size)
        else:
            disk_id = ''

        try:
            if self._options.get(self.NETWORK_KEY):
                network = DynamicObject(**self._mci.get_network_info()[0])
                network_id = "".join(network.mac.split(":"))
            else:
                network_id = ''
        except IndexError:
            network_id = ''

        machine_fingerprint = cpu_id + disk_id + network_id
        return hashlib.sha512(machine_fingerprint.encode()).digest()

    def verify(self) -> bool:
        """
        1. if register file exit, load to memory
        2. call register to verify registration code is correct
        """
        if not os.path.isfile(self._register_file):
            return False

        with open(self._register_file, 'rb') as fp:
            code = fp.read()

        return self.register(code)

    def register(self, code: bytes) -> bool:
        """
        Verify machine fingerprint signature
        :param code:  RegistrationCode generate registration code(machine fingerprint signature)
        :return: success write registration code to file and return true, failed return false
        """
        if not isinstance(code, bytes) or len(code) != _RSA_MSG_LEN:
            return False

        if not self._public_key.verify(self.raw_fingerprint(), code):
            return False

        with open(self._register_file, 'wb') as fp:
            fp.write(code)

        return True

    def get_machine_code(self) -> bytes:
        """Using public key encrypt machine fingerprint"""
        return self._public_key.encrypt(self.raw_fingerprint())

    def get_registration_code(self) -> bytes:
        try:
            with open(self._register_file, 'rb') as fp:
                return fp.read()
        except OSError:
            return bytes()


class RegistrationCode(object):
    def __init__(self, rsa_private_key: str, cipher: str = None):
        self.__private_key = RSAPrivateKeyHandle(rsa_private_key, cipher)

    def get_raw_machine_code(self, machine_code: bytes) -> bytes:
        if not isinstance(machine_code, bytes):
            return bytes()

        if len(machine_code) != _RSA_MSG_LEN:
            return bytes()

        return self.__private_key.decrypt(machine_code)

    def get_registration_code(self, machine_code: bytes) -> bytes:
        # First decrypt get raw machine code
        raw_mc = self.get_raw_machine_code(machine_code)

        if len(raw_mc) != _RAW_MC_LEN:
            return bytes()

        # Return raw machine code signature
        return self.__private_key.sign(raw_mc)
