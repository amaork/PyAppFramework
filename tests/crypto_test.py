# -*- coding: utf-8 -*-
import unittest
from ..misc.crypto import *


class CRC16Test(unittest.TestCase):
    def setUp(self) -> None:
        self.des = DESCrypto(key="12345678", iv="ABCDEFGH")
        self.rsa_key = RSAKeyHandle.generate_key_pair()
        self.public_key = RSAPublicKeyHandle(key=self.rsa_key.public_key)
        self.private_key = RSAPrivateKeyHandle(key=self.rsa_key.private_key)

    def testDESEncrypt(self):
        string = "amaork0123456789"
        self.assertEqual(self.des.decrypt(self.des.encrypt(string.encode())).decode(), string)

    def testRSAEncrypt(self):
        string = "amaork0123456789"
        self.assertEqual(self.private_key.decrypt(self.public_key.encrypt(string.encode())).decode(), string)

    def testRSAMessageSign(self):
        string = "amaork0123456789"
        signature = self.private_key.sign(string.encode())
        self.assertEqual(self.public_key.verify(string.encode(), signature), True)


if __name__ == "__main__":
    unittest.main()
