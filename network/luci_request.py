# -*- coding: utf-8 -*-
import os
import json
import time
import ping3
import random
import requests
import ipaddress
import urllib.parse
from pyquery import PyQuery
from .http_request import *
from ..core.datatype import DynamicObject
__all__ = ['LuciRequest', 'LuciRequestException']


class LuciRequestException(HttpRequestException):
    pass


class LuciRequest(HttpRequest):
    def __init__(self, host, username, password, main_container_id="", source_address="", timeout=5):
        super(LuciRequest, self).__init__(source_address=source_address, timeout=timeout)
        try:
            self._address = ipaddress.IPv4Address(host.split("//")[-1].split(":")[0])
        except ipaddress.AddressValueError as err:
            raise LuciRequestException(0, "{}".format(err))

        self._main_container_id = main_container_id
        self._root = "{}/cgi-bin/luci".format(host)
        login_data = DynamicObject(luci_username=username, luci_password=password)

        try:
            self._stok = ""
            login_response = self.login(self._root, login_data.dict)
            self._stok = urllib.parse.urlparse(login_response.url).params.split("=")[-1]
        except requests.RequestException as err:
            if isinstance(err.response, requests.Response):
                doc = PyQuery(err.response.text.encode())
                raise LuciRequestException(err.response.status_code, doc('p').text().strip())
            else:
                raise LuciRequestException(err, "{}".format(err))

    def _get_url(self, path):
        return "{}/;stok={}/{}".format(self._root, self._stok, path) if self._stok else "{}/{}".format(self._root, path)

    def is_alive(self, timeout=1):
        return ping3.ping(dest_addr=str(self._address), timeout=timeout)

    def get_context(self, text):
        doc = PyQuery(text.encode())
        content = doc("#{} .cbi-section") if self._main_container_id else doc(".cbi-section")
        return content.text().strip()

    def get_static_status(self):
        url = self._get_url("admin/status/overview")
        res = self.section_get(url)
        context = self.get_context(res.text)
        status = context.split("Local Time")[0].split("\n")[1:]
        return dict(zip(status[::2], status[1::2]))

    def get_dynamic_status(self):
        res = self.section_get(self._get_url(""), params={"status": 1, "&_": random.random()})
        try:
            return json.loads(res.text)
        except json.JSONDecodeError as err:
            print("Decode error:{}".format(err))
            return dict()

    def get_firmware_version(self):
        status = self.get_static_status()
        return status.get("Firmware Version")

    def get_multipart_from_data(self, token_url, name, file, params):
        params[name] = (os.path.basename(file), open(file, "rb"))

        if not self._stok:
            params[self.token_name] = self.get_token(token_url)

        return params

    def firmware_upgrade(self, firmware, keep=True, timeout=120, reboot_wait=30, output_msg=print):
        total_start = time.time()
        flash_ops_url = self._get_url("admin/system/flashops")
        flash_ops_form_token = "" if self._stok else self.get_token(flash_ops_url)

        def print_msg(msg):
            if hasattr(output_msg, "__call__"):
                output_msg(msg)

        # Step one upload firmware
        form_data = {
            "keep": (None, "on"),
            "image": (os.path.basename(firmware), open(firmware, "rb"))
        }

        if not keep:
            form_data.pop("keep")

        # Token mode
        if not self._stok:
            form_data[self.token_name] = (None, flash_ops_form_token)
            flash_ops_url = "{}/sysupgrade".format(flash_ops_url)

        upload_res = self._section.post(flash_ops_url, files=form_data, timeout=timeout)
        upload_res.raise_for_status()

        # Upload success get firmware information
        print_msg("Firmware upload success")
        print_msg(self.get_context(upload_res.text))

        # Step two flash firmware
        form_data = {
            "step": "2",
            "keep": "1" if keep else ""
        }

        # Token mode
        if not self._stok:
            form_data[self.token_name] = flash_ops_form_token

        flash_res = self._section.post(flash_ops_url, data=form_data, timeout=timeout)
        flash_res.raise_for_status()

        print_msg("Firmware flash success")
        print_msg("Wait system reboot")

        cnt = 0
        time.sleep(reboot_wait)
        detect_start = time.time()
        while time.time() - detect_start < timeout:
            cnt += 1
            print_msg("Wait system reboot.{}".format("." * cnt))
            if self.is_alive():
                print_msg("System reboot success, total consuming: {0:.2f} secs".format(time.time() - total_start))
                return True

        print_msg("Wait system reboot timeout")
        return False
