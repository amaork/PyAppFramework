# -*- coding: utf-8 -*-
import os
import re
import time
import subprocess
from typing import List, Dict
import xml.etree.ElementTree as XmlElementTree

from ..core.datatype import *
from ..misc.util import awk_query
__all__ = ['WirelessNetwork', 'WirelessInterface', 'WirelessNetworkShell', 'LinuxWirelessNetworkShell']


class WirelessInterface(DynamicObject):
    _properties = {'name', 'desc', 'guid', 'connected', 'mac',
                   'ssid', 'bssid', 'type', 'auth', 'cipher',
                   'rx_rate', 'tx_rate', 'signal', 'channel', 'profile'}

    def __init__(self, **kwargs):
        kwargs.setdefault("desc", "")
        kwargs.setdefault("guid", "")
        kwargs.setdefault("mac", "")
        kwargs.setdefault("connected", False)

        kwargs.setdefault("ssid", "")
        kwargs.setdefault("bssid", "")
        kwargs.setdefault("type", "")
        kwargs.setdefault("auth", "")
        kwargs.setdefault("cipher", "")
        kwargs.setdefault("rx_rate", 0.0)
        kwargs.setdefault("tx_rate", 0.0)
        kwargs.setdefault("signal", "")
        kwargs.setdefault("channel", 0),
        kwargs.setdefault("profile", "")
        super(WirelessInterface, self).__init__(**kwargs)


class WirelessNetwork(DynamicObject):
    _properties = {'ssid', 'auth', 'encrypt'}

    ENCRYPTION_AES, ENCRYPTION_TKIP, ENCRYPTION_NONE = ('AES', 'TKIP', 'NONE')
    ALL_ENCRYPTION = (ENCRYPTION_AES, ENCRYPTION_TKIP, ENCRYPTION_NONE)

    AUTH_WPA, AUTH_WPA2, AUTH_OPEN = ('WPAPSK', 'WPA2PSK', 'OPEN')
    ALL_AUTH = (AUTH_OPEN, AUTH_WPA, AUTH_WPA2)

    def __init__(self, **kwargs):
        kwargs.setdefault('auth', '')
        kwargs.setdefault('encrypt', '')
        super(WirelessNetwork, self).__init__(**kwargs)


class WirelessNetworkShell(object):
    def __init__(self, interface: str = "", verbose: bool = False):
        self._interface = interface
        self._verbose = True if verbose else False

        ifc_info = self.get_interfaces()
        if not self._interface and ifc_info:
            self._interface = list(ifc_info.keys())[0]

        if not self._interface:
            raise RuntimeError("There is not wireless interface available currently")

        if self._interface not in ifc_info:
            raise RuntimeError("Unknown wireless interface name: {!r}".format(interface))

        self.__print_msg("Interface: {}".format(ifc_info.get(self._interface).dict))

    def __print_msg(self, *args):
        if self._verbose:
            print(*args)

    @staticmethod
    def get_interfaces() -> Dict[str, WirelessInterface]:
        """Return wireless interface dict"""
        result = subprocess.Popen('netsh wlan show interface', stdout=subprocess.PIPE,
                                  stdin=subprocess.PIPE, stderr=subprocess.PIPE).stdout.read().decode('gbk')

        ifc_dict = dict()
        current_interface = ""

        kv_bind_dict = {
            'guid': ('GUID', 'GUID', 'XXX'),
            'ssid': ('SSID', 'SSID', 'BSSID'),
            'bssid': ('BSSID', 'BSSID', 'XXX'),
            'desc': ('描述', 'Description', 'XXX'),
            'connected': ('状态', 'State', "承载网络状态"),

            'type': ('无线电类型', 'Radio type', 'XXX'),
            'auth': ('身份验证', 'Authentication', 'XXX'),
            'cipher': ('密码', 'Cipher', 'XXX'),
            'rx_rate': ('接收速率', 'Receive rate', 'XXX'),
            'tx_rate': ('传输速率', 'Transmit rate', "XXX"),
            'signal': ('信号', 'Signal', 'XXX'),
            'channel': ('信道', 'Channel', 'XXX'),
            'profile': ('配置文件', 'Profile', 'XXX'),
        }

        for line in result.split('\r\n'):
            if '名称' in line or 'Name' in line:
                name = line.split(":")[-1].strip()
                current_interface = name
                ifc_dict[current_interface] = WirelessInterface(name=name)

            if '承载网络状态' in line or 'Hosted network status' in line:
                current_interface = ''

            for k, v in kv_bind_dict.items():
                if (v[0] in line or v[1] in line) and v[2] not in line and current_interface in ifc_dict:
                    data = re.findall(":\\s?(.+)", line)
                    if k == 'connected':
                        ifc_dict[current_interface].update(
                            {k: data[0].strip() in ('connected', '已连接') if data else False}
                        )
                    elif k in ('rx_rate', 'tx_rate'):
                        ifc_dict[current_interface].update({k: str2float(data[0].strip()) if data else 0.0})
                    elif k in ('channel',):
                        ifc_dict[current_interface].update({k: str2number(data[0].strip()) if data else 0})
                    else:
                        ifc_dict[current_interface].update({k: data[0].strip() if data else ""})

        return ifc_dict

    @staticmethod
    def get_profile_template() -> str:
        return "<?xml version=\"1.0\"?>" \
               "<WLANProfile xmlns=\"http://www.microsoft.com/networking/WLAN/profile/v1\">" \
               "<name>WIFI_NAME</name>" \
               "<SSIDConfig>" \
               "<SSID>" \
               "<name>WIFI_NAME</name>" \
               "</SSID>" \
               "<nonBroadcast>false</nonBroadcast>" \
               "</SSIDConfig>" \
               "<connectionType>ESS</connectionType>" \
               "<connectionMode>manual</connectionMode>" \
               "<autoSwitch>false</autoSwitch>" \
               "<MSM>" \
               "<security>" \
               "<authEncryption>" \
               "<authentication>WPA2PSK</authentication>" \
               "<encryption>AES</encryption>" \
               "<useOneX>false</useOneX>" \
               "</authEncryption>" \
               "<sharedKey>" \
               "<keyType>passPhrase</keyType>" \
               "<protected>false</protected>" \
               "<keyMaterial>PASSWORD</keyMaterial>" \
               "</sharedKey>" \
               "</security>" \
               "</MSM>" \
               "</WLANProfile>"

    def get_profiles(self) -> List[str]:
        """Return wireless interface all profiles name list"""
        result = subprocess.Popen('netsh wlan show profiles interface="{}"'.format(self._interface),
                                  stdout=subprocess.PIPE, stdin=subprocess.PIPE,
                                  stderr=subprocess.PIPE).stdout.read().decode('gbk')
        profiles = list()
        for line in result.split('\r\n'):
            if '所有用户配置文件' in line or 'All User Profile' in line:
                profiles.append(re.findall(":\\s?(.+)", line)[0])

        return profiles

    def get_networks(self) -> Dict[str, WirelessNetwork]:
        """Return interface visible network dict"""
        result = subprocess.Popen('netsh wlan show networks interface="{}"'.format(self._interface),
                                  stdout=subprocess.PIPE, stdin=subprocess.PIPE,
                                  stderr=subprocess.PIPE).stdout.read().decode('gbk')
        current_network = ""
        network_dict = dict()

        for line in result.split('\r\n'):
            if 'SSID' in line:
                current_network = re.findall(":\\s?(.+)", line)[0]
                network_dict[current_network] = WirelessNetwork(ssid=current_network)

            if '身份验证' in line or 'Authentication' in line and current_network in network_dict:
                network_dict[current_network].update(dict(auth=re.findall(":\\s?(.+)", line)[0]))

            if '加密' in line or 'Encryption' in line and current_network in network_dict:
                network_dict[current_network].update(dict(encrypt=re.findall(":\\s?(.+)", line)[0]))
                current_network = ""

        return network_dict

    def delete_profile(self, profile: str) -> bool:
        """Delete specified profile"""
        if profile not in self.get_profiles():
            print("Profile: {} is not exist".format(profile))
            self.__print_msg("Profiles: {}".format(self.get_profiles()))
            return False

        subprocess.Popen('netsh wlan delete profile name="{}" interface="{}"'.format(profile, self._interface),
                         stdout=subprocess.PIPE, stdin=subprocess.PIPE,
                         stderr=subprocess.PIPE).stdout.read().decode('gbk')
        return profile not in self.get_profiles()

    def add_profile(self, ssid: str,
                    auth: str = WirelessNetwork.AUTH_OPEN,
                    password: str = "", encryption: str = WirelessNetwork.ENCRYPTION_NONE) -> bool:
        if not ssid or not isinstance(ssid, str):
            raise ValueError('{!r} is required'.format("ssid"))

        if auth not in WirelessNetwork.ALL_AUTH:
            raise ValueError('{!r} is invalid, must be one of: {}'.format('auth', WirelessNetwork.ALL_AUTH))

        if encryption not in WirelessNetwork.ALL_ENCRYPTION:
            raise ValueError('{!r} is invalid, must be one of: {}'.format('encryption', WirelessNetwork.ALL_ENCRYPTION))

        if auth == WirelessNetwork.AUTH_OPEN:
            auth = 'open'
            password = ''
            encryption = 'none'

        # Profile exist delete old profile
        if ssid in self.get_profiles() and not self.delete_profile(ssid):
            print("Profile {} is exist, and delete profile failed!".format(ssid))
            return False

        # Generate xml profile
        profile_name = '{}.xml'.format(ssid)
        XmlElementTree.register_namespace('', "http://www.microsoft.com/networking/WLAN/profile/v1")
        with open(profile_name, 'w', encoding='utf-8') as fp:
            fp.write(self.get_profile_template())

        xml_tree = XmlElementTree.parse(profile_name)
        xml_root = xml_tree.getroot()
        for elem in xml_root.iter():
            if "name" in elem.tag:
                elem.text = ssid
            if "keyMaterial" in elem.tag:
                elem.text = password
            if "authentication" in elem.tag:
                elem.text = auth
            if "encryption" in elem.tag:
                elem.text = encryption

        xml_tree.write(profile_name)

        try:
            result = subprocess.Popen(
                'netsh wlan add profile filename="{}" interface="{}"'.format(profile_name, self._interface),
                stdout=subprocess.PIPE, stdin=subprocess.PIPE,
                stderr=subprocess.PIPE).stdout.read().decode('gbk')

            if ssid not in self.get_profiles():
                raise RuntimeError(result)

            self.__print_msg("Profiles: {}".format(self.get_profiles()))
            return True
        except Exception as e:
            print("Add profile {} failed: {}".format(profile_name, e))
            return False
        finally:
            if os.path.isfile(profile_name):
                os.remove(profile_name)

    def disconnect(self, delete_profile: bool = False) -> bool:
        ifc = self.get_interfaces().get(self._interface)
        if not isinstance(ifc, WirelessInterface):
            print("No such interface")
            return False

        if not ifc.connected:
            return True

        subprocess.Popen('netsh wlan disconnect interface="{}"'.format(self._interface),
                         stdout=subprocess.PIPE, stdin=subprocess.PIPE,
                         stderr=subprocess.PIPE).stdout.read().decode('gbk')
        time.sleep(1)
        if self.get_interfaces().get(self._interface).connected:
            return False

        return self.delete_profile(ifc.profile) if delete_profile else True

    def connect(self, ssid: str, auth: str = "", password: str = "", encryption: str = "") -> bool:
        ifc = self.get_interfaces().get(self._interface)
        if not isinstance(ifc, WirelessInterface):
            print("No such interface")
            return False

        if ifc.connected and ifc.ssid == ssid:
            print("Already connected {}".format(ssid))
            return True
        elif ifc.connected and self.disconnect():
            print("Disconnect {} failed".format(ifc.ssid))
            return False

        # Re-add ssid profile
        if not self.add_profile(ssid=ssid, auth=auth, password=password, encryption=encryption):
            return False

        # Connect to ssid specified network
        result = subprocess.Popen('netsh wlan connect name={} ssid={} interface="{}"'.format(
            ssid, ssid, self._interface),
            stdout=subprocess.PIPE, stdin=subprocess.PIPE,
            stderr=subprocess.PIPE).stdout.read().decode('gbk')

        time.sleep(3)
        # Check if connected success
        ifc = self.get_interfaces().get(self._interface)
        if not isinstance(ifc, WirelessInterface):
            print("No such interface")
            return False

        self.__print_msg("Interface: {}".format(ifc.dict))

        if not ifc.connected or ifc.ssid != ssid:
            print("Connect {} failed: {}".format(ssid, result))
            return False

        return True


class LinuxWirelessNetworkShell:
    def __init__(self, interface: str = 'wlan0'):
        self._interface = interface
        self._iw_config = f'iwconfig {self._interface}'

    def __repr__(self):
        return f'{self.attr.dict}'

    @property
    def attr(self) -> DynamicObject:
        return DynamicObject(ssid=self.get_ssid(),
                             quality=self.get_quality(),
                             signal_level=self.get_signal_level(), mode=self.get_mode(), ap=self.get_ap())

    def get_ap(self) -> str:
        pass

    def get_mode(self) -> str:
        pass

    def get_ssid(self) -> str:
        return awk_query(self._iw_config, 'ESSID', 4).split(":")[-1]

    def get_quality(self) -> int:
        try:
            dbm = self.get_signal_level()
            return max(min(2 * (dbm + 100), 0), 100)
        except ValueError:
            return 0

    def get_signal_level(self) -> int:
        try:
            return int(awk_query(self._iw_config, '"Signal level"', 4).split('=')[-1])
        except ValueError:
            return 0
