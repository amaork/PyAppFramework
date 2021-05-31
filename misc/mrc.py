# -*- coding: utf-8 -*-
import os
import wmi
import hashlib
import ipaddress
import collections
from typing import List

from ..misc.crypto import *
from ..core.datatype import DynamicObject
__all__ = ['MachineInfo', 'MachineCode', 'RegistrationCode']

_RAW_MC_LEN = 64
_RSA_MSG_LEN = 344

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
        """
        self._wmi = wmi.WMI()

    def get_os_info(self) -> dict:
        os = self._wmi.Win32_OperatingSystem()[0]
        return dict(caption=os.Caption, version=os.Version,
                    tz=os.CurrentTimeZone, language=os.MUILanguages[0],
                    arch=os.OSArchitecture, sn=os.SerialNumber, system_device=os.SystemDevice)

    def get_cpu_info(self) -> List[dict]:
        cpu = list()
        for processor in self._wmi.Win32_Processor():
            cpu.append(
                {
                    'name': processor.Name,
                    'sn': processor.ProcessorId,
                    'core_num': processor.NumberOfCores
                }
            )

        return cpu

    def get_disk_info(self) -> List[dict]:
        disk = list()
        for dd in self._wmi.Win32_DiskDrive():
            disk.append(
                {
                    "sn": self._wmi.Win32_PhysicalMedia()[0].SerialNumber.lstrip().rstrip(),
                    "id": dd.deviceid,
                    "caption": dd.Caption,
                    "size": str(int(float(dd.Size) / 1024 / 1024 / 1024))
                }
            )

        return disk

    def get_network_info(self) -> List[dict]:
        network = list()
        for nac in self._wmi.Win32_NetworkAdapterConfiguration():
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

    def get_logic_disk_info(self) -> List[dict]:
        logic_disk = list()
        for disk in self._wmi.Win32_LogicalDisk(DriveType=3):
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


class MachineCode(object):
    ERROR_CODE = collections.namedtuple('ErrorCode', ['PASS', 'NONE', 'FAIL'])(*range(3))

    def __init__(self, rsa_public_key: str, register_file: str):
        self._mci = MachineInfo()
        self._register_file = register_file
        self._public_key = RSAPublicKeyHandle(rsa_public_key)

    def raw_fingerprint(self) -> bytes:
        cpu = DynamicObject(**self._mci.get_cpu_info()[0])
        disk = DynamicObject(**self._mci.get_disk_info()[0])
        network = DynamicObject(**self._mci.get_network_info()[0])
        machine_fingerprint = cpu.sn + str(cpu.core_num) + disk.sn + str(disk.size) + "".join(network.mac.split(":"))
        return hashlib.sha512(machine_fingerprint.encode()).digest()

    def verify(self) -> ERROR_CODE:
        """
        1. if register file exit, load to memory
        2. call register to verify registration code is correct
        :return: PASS/NONE/FAIL
        """
        if not os.path.isfile(self._register_file):
            return self.ERROR_CODE.NONE

        with open(self._register_file, 'rb') as fp:
            code = fp.read()

        return self.ERROR_CODE.PASS if self.register(code) else self.ERROR_CODE.FAIL

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

    @staticmethod
    def get_error_desc(code: ERROR_CODE) -> str:
        return {
            MachineCode.ERROR_CODE.PASS: "Registered",
            MachineCode.ERROR_CODE.NONE: "Not register",
            MachineCode.ERROR_CODE.FAIL: "Verify Fail"
        }.get(code, "Unknown")


class RegistrationCode(object):
    def __init__(self, rsa_private_key: str):
        self.__private_key = RSAPrivateKeyHandle(rsa_private_key)

    def get_registration_code(self, machine_code: bytes) -> bytes:
        if not isinstance(machine_code, bytes):
            return bytes()

        if len(machine_code) != _RSA_MSG_LEN:
            return bytes()

        # First decrypt get raw machine code
        raw_mc = self.__private_key.decrypt(machine_code)

        if len(raw_mc) != _RAW_MC_LEN:
            return bytes()

        # Return raw machine code signature
        return self.__private_key.sign(raw_mc)