# -*- coding: utf-8 -*-
import pyDes
import base64
import Crypto
import binascii
from Crypto import Random
from Crypto.Hash import SHA
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_v1_5 as PKCS1_cipher
from Crypto.Signature import PKCS1_v1_5 as PKCS1_signature
__all__ = ['RSAPublicKeyHandle', 'RSAPrivateKeyHandle', 'RSAKeyHandle', 'DESCrypto']


class RSAKeyHandle(object):
    def __init__(self, key: str):
        self._key = RSA.importKey(str(key))

    def encrypt(self, message: bytes) -> bytes:
        result = bytes()
        cipher = PKCS1_cipher.new(self._key)
        max_length = self.get_max_length(True)

        while message:
            result += cipher.encrypt(message[:max_length])
            message = message[max_length:]

        return base64.b64encode(result)

    def decrypt(self, message: bytes) -> bytes:
        try:
            result = bytes()
            message = base64.b64decode(message)
            cipher = PKCS1_cipher.new(self._key)
            max_length = self.get_max_length(False)

            while message:
                result += cipher.decrypt(message[:max_length], b'')
                message = message[max_length:]

            return result
        except binascii.Error:
            return bytes()

    def get_max_length(self, encrypt: bool) -> int:
        block_size = Crypto.Util.number.size(self._key.n) // 8
        reserve_size = 11
        if not encrypt:
            reserve_size = 0
        return block_size - reserve_size

    @staticmethod
    def generate_key_pair(bits: int = 2048) -> dict:
        random_generator = Random.new().read
        rsa = RSA.generate(bits, random_generator)

        private_key = rsa.exportKey()
        public_key = rsa.publickey().exportKey()
        return dict(public_key=public_key.decode(), private_key=private_key.decode())


class RSAPublicKeyHandle(RSAKeyHandle):
    def __init__(self, key: str):
        super(RSAPublicKeyHandle, self).__init__(key)

    def verify(self, message: bytes, signature):
        try:
            verifier = PKCS1_signature.new(self._key)
            return verifier.verify(SHA.new(message), base64.b64decode(signature))
        except binascii.Error:
            return False


class RSAPrivateKeyHandle(RSAKeyHandle):
    def __init__(self, key: str):
        super(RSAPrivateKeyHandle, self).__init__(key)

    def sign(self, message: bytes) -> bytes:
        singer = PKCS1_signature.new(self._key)
        return base64.b64encode(singer.sign(SHA.new(message)))


class DESCrypto(object):
    def __init__(self, key: str, iv: str):
        self._iv = iv
        self._key = key
        self._des = pyDes.des(self._key, pyDes.CBC, self._iv, pad=None, padmode=pyDes.PAD_PKCS5)

    def encrypt(self, data: bytes) -> bytes:
        return base64.b64encode(self._des.encrypt(data))

    def decrypt(self, data: bytes) -> bytes:
        return self._des.decrypt(base64.b64decode(data))