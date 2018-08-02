# -*- coding: utf-8 -*-
import unittest
from framework.misc.settings import UiInputSetting


class UiInputSettingTest(unittest.TestCase):
    def testName(self):
        with self.assertRaises(TypeError):
            UiInputSetting(name=1, type="INT", data=1, check="", default="21")

        with self.assertRaises(TypeError):
            UiInputSetting(name=0.2, type="INT", data=1, check="", default=1)

        with self.assertRaises(TypeError):
            UiInputSetting(name=bool, type="INT", data=1, check=(1, "21"), default=1)

        with self.assertRaises(TypeError):
            UiInputSetting(name=[], type="INT", data=1, check=(1, "21"), default=1)

        self.assertEqual(UiInputSetting(name="数字", type="INT", data=1, check=(1, 100), default=10).name, "数字")

    def testType(self):
        with self.assertRaises(ValueError):
            UiInputSetting(name="数字", type=21, data=1, check="", default=1)

        with self.assertRaises(ValueError):
            UiInputSetting(name="数字", type="211", data=1, check="", default=1)

        with self.assertRaises(ValueError):
            UiInputSetting(name="数字", type=0.1, data=1, check="", default=1)

        with self.assertRaises(ValueError):
            UiInputSetting(name="数字", type=[], data=1, check="", default=1)

        self.assertEqual(UiInputSetting(name="数字", type="INT", data=1,
                                        check=(1, 100), default=99).type, "INT")
        self.assertEqual(UiInputSetting(name="文本", type="TEXT", data="1",
                                        check=("",), default="123456").type, "TEXT")
        self.assertEqual(UiInputSetting(name="布尔", type="BOOL", data=False,
                                        check=(True, False), default=True).type, "BOOL")
        self.assertEqual(UiInputSetting(name="浮点", type="FLOAT", data=0.1,
                                        check=(0.1, 11.0), default=0.12).type, "FLOAT")
        self.assertEqual(UiInputSetting(name="选择", type="SELECT", data="A",
                                        check=["A", "B", "C"], default="A").type, "SELECT")

    def testCheck(self):
        with self.assertRaises(TypeError):
            UiInputSetting(name="数字", type="INT", data=1, check="", default=1)

        with self.assertRaises(TypeError):
            UiInputSetting(name="文本", type="TEXT", data=1, check=12, default="21")

        with self.assertRaises(TypeError):
            UiInputSetting(name="浮点", type="FLOAT", data=1, check=(1, 2), default=1.0)

        with self.assertRaises(TypeError):
            UiInputSetting(name="布尔", type="BOOL", data=1, check=(1, "21"), default=1)

        with self.assertRaises(TypeError):
            UiInputSetting(name="选择", type="SELECT", data=1, check="", default="A")

    def testDefault(self):
        self.assertEqual(UiInputSetting(name="数字", type="INT", data=1,
                                        check=(1, 100), default=99).default, 99)
        self.assertEqual(UiInputSetting(name="文本", type="TEXT", data="1",
                                        check=("", 16), default="123456").default, "123456")
        self.assertEqual(UiInputSetting(name="布尔", type="BOOL", data=True,
                                        check=(True, False), default=True).default, True)
        self.assertEqual(UiInputSetting(name="浮点", type="FLOAT", data=0.1,
                                        check=(0.1, 11.0), default=0.12).default, 0.12)
        self.assertEqual(UiInputSetting(name="选择", type="SELECT", data="C",
                                        check=["A", "B", "C"], default="A").default, "A")


if __name__ == "__main__":
    unittest.main()
