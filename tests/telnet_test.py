# -*- coding: utf-8 -*-
import os
import json
import unittest
from framework.protocol.rmi_shell import *
from framework.core.datatype import DynamicObject


class TelnetClientTest(unittest.TestCase):
    def setUp(self) -> None:
        env = os.environ.get("TELNET_ENV")
        env = DynamicObject(**json.loads(env[1:-1]))
        self.client = TelnetClient(host=env.address, port=env.port,
                                   user="root", password=env.password)

    def testConnect(self):
        self.assertEqual(self.client.connected(), True)

    def testDirFileCheck(self):
        self.assertEqual(self.client.is_dir_exist("/tmp"), True)

    def testExec(self):
        self.assertEqual("Linux" in self.client.exec("uname"), True)

    def testUploadFile(self):
        test_file = "/tmp/{}".format(os.path.basename(__file__))
        self.assertEqual(self.client.tftp_upload_file(os.path.abspath(__file__)), True)
        self.assertEqual(self.client.is_file_exist(test_file), True)
        self.assertEqual(os.path.basename(__file__) in self.client.exec("ls /tmp"), True)
        self.client.exec("rm {}".format(test_file))
        self.assertEqual(self.client.is_file_exist(test_file), False)


if __name__ == "__main__":
    unittest.main()
