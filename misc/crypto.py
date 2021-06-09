# -*- coding: utf-8 -*-
import os
import pyDes
import typing
import base64
import Crypto
import binascii
from Crypto import Random
from Crypto.Hash import SHA
from Crypto.Cipher import AES
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_v1_5 as PKCS1_cipher
from Crypto.Signature import PKCS1_v1_5 as PKCS1_signature
from ..core.datatype import DynamicObject
__all__ = ['RSAPublicKeyHandle', 'RSAPrivateKeyHandle', 'RSAKeyHandle', 'RSAKeyPair', 'DESCrypto', 'AESCrypto']


class RSAKeyPair(DynamicObject):
    _properties = {'public_key', 'private_key'}
    _check = {
        'public_key': lambda x: isinstance(x, str),
        'private_key': lambda x: isinstance(x, str)
    }


class RSAKeyHandle(object):
    KEYWORDS = ('',)

    def __init__(self, key: str):
        self._key = RSA.importKey(str(key))
        if not self.check():
            raise ValueError("Invalid format")

    def check(self) -> bool:
        raw_key_str = self._key.export_key().decode()
        return all([kw in raw_key_str for kw in self.KEYWORDS])

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
    def generate_key_pair(bits: int = 2048) -> RSAKeyPair:
        random_generator = Random.new().read
        rsa = RSA.generate(bits, random_generator)

        private_key = rsa.exportKey()
        public_key = rsa.publickey().exportKey()
        return RSAKeyPair(public_key=public_key.decode(), private_key=private_key.decode())

    @staticmethod
    def generate_key_pair_and_save(path: str = "", binary: bool = False, bits: int = 2048) ->bool:
        key = RSAKeyHandle.generate_key_pair(bits)
        if not isinstance(key, RSAKeyPair):
            return False

        try:
            mode = 'wb' if binary else 'w'
            extension = '.bin' if binary else '.txt'
            with open(os.path.join(path, 'private_key' + extension), mode) as fp:
                fp.write(key.private_key.encode()) if binary else fp.write(key.private_key)

            with open(os.path.join(path, 'public_key' + extension), mode) as fp:
                fp.write(key.public_key.encode()) if binary else fp.write(key.public_key)

            return True
        except OSError as e:
            print("'generate_key_pair_and_save' error: {}".format(e))
            return False


class RSAPublicKeyHandle(RSAKeyHandle):
    KEYWORDS = ('BEGIN PUBLIC KEY', 'END PUBLIC KEY')

    def __init__(self, key: str):
        super(RSAPublicKeyHandle, self).__init__(key)

    def verify(self, message: bytes, signature):
        try:
            verifier = PKCS1_signature.new(self._key)
            return verifier.verify(SHA.new(message), base64.b64decode(signature))
        except binascii.Error:
            return False


class RSAPrivateKeyHandle(RSAKeyHandle):
    KEYWORDS = ('BEGIN RSA PRIVATE KEY', 'END RSA PRIVATE KEY')

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


class AESCrypto(object):
    BLOCK_SIZE = 16
    AES_CBC, AES_ECB = 'CBC', 'ECB'

    AES_MODE = {
        AES_CBC: AES.MODE_CBC,
        AES_ECB: AES.MODE_ECB
    }

    def __init__(self, key: str, mode: str = AES_ECB, vi: bytes = bytes(range(BLOCK_SIZE))):
        if mode not in self.AES_MODE:
            raise ValueError('Invalid mode: {!r} mode must be: {}'.format(mode, list(self.AES_MODE.keys())))

        self.__vi = vi
        self.__mode = mode
        self.__key = self.pad(key).encode()

    def cipher(self):
        if self.__mode == self.AES_ECB:
            return AES.new(self.__key, self.AES_MODE.get(self.__mode))
        else:
            return AES.new(self.__key, self.AES_MODE.get(self.__mode), self.__vi)

    @staticmethod
    def pad(data: str) -> str:
        pl = (AESCrypto.BLOCK_SIZE - len(data) % AESCrypto.BLOCK_SIZE)
        return data + chr(pl) * pl

    @staticmethod
    def unpad(data: str) -> str:
        return data[:-ord(data[len(data) - 1])]

    @staticmethod
    def check(msg: str, data: typing.Any):
        if not isinstance(data, bytes):
            raise TypeError("{!r} data must be bytes".format(msg))

        if not data:
            raise ValueError('{!r} data is empty'.format(msg))

    def encrypt(self, data: bytes) -> bytes:
        self.check('encrypt', data)
        data = base64.b64encode(data)
        return self.cipher().encrypt(self.pad(data.decode()).encode())

    def decrypt(self, data: bytes) -> bytes:
        self.check('decrypt', data)
        return base64.b64decode(self.unpad(self.cipher().decrypt(data).decode()).encode())
