# -*- coding: utf-8 -*-
import unittest
from ..misc.crypto import *


class CRC16Test(unittest.TestCase):
    def setUp(self) -> None:
        self.des = DESCrypto(key="12345678", iv="ABCDEFGH")
        self.aes_ecb = AESCrypto(key=b'amaork', mode=AESCrypto.AES_ECB)
        self.aes_cbc = AESCrypto(key=b'amaork', mode=AESCrypto.AES_CBC)

        self.rsa_key = RSAKeyHandle.generate_key_pair()
        self.public_key = RSAPublicKeyHandle(key=self.rsa_key.public_key)
        self.private_key = RSAPrivateKeyHandle(key=self.rsa_key.private_key)

    def testAES(self):
        with self.assertRaises(TypeError):
            AESCrypto(key='amaork')

        with self.assertRaises(ValueError):
            AESCrypto(key=b'amaork', mode="cbc")

    def testAESPad(self):
        self.assertEqual(AESCrypto.unpad(AESCrypto.pad(b"123")), b"123")
        self.assertEqual(AESCrypto.pad(b"0123456789abcdef"), b'0123456789abcdef')
        self.assertEqual(AESCrypto.unpad(AESCrypto.pad(b"0123456789abcde")), b'0123456789abcde')
        self.assertEqual(AESCrypto.unpad(AESCrypto.pad(b"0123456789abcdef123")), b'0123456789abcdef123')

    def testAESEncrypt(self):
        with self.assertRaises(TypeError):
            self.aes_ecb.encrypt("123")

        with self.assertRaises(TypeError):
            self.aes_ecb.decrypt("123")

        self.assertEqual(self.aes_ecb.decrypt(self.aes_ecb.encrypt(b'hello'), 5), b'hello')
        self.assertEqual(self.aes_ecb.decrypt(self.aes_ecb.encrypt(bytes(range(256))), 256) == bytes(range(256)), True)

        self.assertEqual(self.aes_cbc.decrypt(self.aes_cbc.encrypt(b'hello'), 5), b'hello')
        self.assertEqual(self.aes_cbc.decrypt(self.aes_cbc.encrypt(bytes(range(256))), 256) == bytes(range(256)), True)

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
