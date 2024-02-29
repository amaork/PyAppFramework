# -*- coding: utf-8 -*-
import os
import pyDes
import typing
import Crypto
import binascii
from Crypto import Random
from Crypto.Cipher import AES
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_v1_5 as PKCS1_cipher
from Crypto.Signature import PKCS1_v1_5 as PKCS1_signature
from Crypto.Hash import SHA1, SHA, SHA224, SHA256, SHA384, SHA512, SHA3_224, SHA3_256, SHA3_384, SHA3_512, \
    MD5, RIPEMD160, RIPEMD
from ..core.datatype import DynamicObject
__all__ = [
    'RSAPublicKeyHandle', 'RSAPrivateKeyHandle', 'RSAKeyHandle', 'RSAKeyPair', 'DESCrypto', 'AESCrypto',
    'CryptoCommException', 'CryptoCommLengthException', 'CryptoCommDecodeException', 'CryptoCommVerifyException',
    'crypto_encrypt_data', 'crypto_decrypt_data', 'crypto_communication'
]


class RSAKeyPair(DynamicObject):
    _properties = {'public_key', 'private_key'}
    _check = {
        'public_key': lambda x: isinstance(x, str),
        'private_key': lambda x: isinstance(x, str)
    }


class RSAKeyHandle(object):
    KEYWORDS = ('',)
    Protections = (
        'None',
        'PBKDF2WithHMAC-SHA1AndAES128-CBC',
        'PBKDF2WithHMAC-SHA1AndAES192-CBC',
        'PBKDF2WithHMAC-SHA1AndAES256-CBC',
        'PBKDF2WithHMAC-SHA1AndDES-EDE3-CBC',
        'scryptAndAES128-CBC',
        'scryptAndAES192-CBC',
        'scryptAndAES256-CBC'
    )

    HashAlgo = {
        'MD5': MD5,

        'SHA': SHA,
        'SHA1': SHA1,

        'SHA224': SHA224,
        'SHA256': SHA256,
        'SHA384': SHA384,
        'SHA512': SHA512,

        'SHA3_224': SHA3_224,
        'SHA3_256': SHA3_256,
        'SHA3_384': SHA3_384,
        'SHA3_512': SHA3_512,

        'RIPEMD': RIPEMD,
        'RIPEMD160': RIPEMD160
    }

    def __init__(self, key: str, pwd: str = None):
        self._key = RSA.importKey(str(key), passphrase=pwd)
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

        return result

    def decrypt(self, message: bytes) -> bytes:
        try:
            result = bytes()
            cipher = PKCS1_cipher.new(self._key)
            max_length = self.get_max_length(False)

            while message:
                result += cipher.decrypt(message[:max_length], b'')
                message = message[max_length:]

            return result
        except (binascii.Error, ValueError):
            return bytes()

    def get_max_length(self, encrypt: bool) -> int:
        block_size = Crypto.Util.number.size(self._key.n) // 8
        reserve_size = 11
        if not encrypt:
            reserve_size = 0
        return block_size - reserve_size

    @classmethod
    def load_from_file(cls, file: str, **kwargs):
        with open(file) as fp:
            return cls(fp.read(), **kwargs)

    @classmethod
    def get_hash_algo_from_str(cls, hash_algo: str):
        return cls.HashAlgo.get(hash_algo)

    @staticmethod
    def generate_key_pair(bits: int = 3072, **kwargs) -> RSAKeyPair:
        random_generator = Random.new().read
        rsa = RSA.generate(bits, random_generator)

        private_key = rsa.exportKey(**kwargs)
        public_key = rsa.publickey().exportKey()
        return RSAKeyPair(public_key=public_key.decode(), private_key=private_key.decode())

    @staticmethod
    def get_key_pair_name(prefix: str = '', binary: bool = False) -> typing.Tuple[str, str]:
        prefix = f'{prefix}_' if prefix else ''
        extension = '.bin' if binary else '.txt'
        return f'{prefix}public_key' + extension, f'{prefix}private_key' + extension

    @staticmethod
    def generate_key_pair_and_save(path: str = "", prefix: str = '',
                                   binary: bool = False, bits: int = 3072,  **kwargs) -> bool:
        key = RSAKeyHandle.generate_key_pair(bits, **kwargs)
        if not isinstance(key, RSAKeyPair):
            return False

        try:
            mode = 'wb' if binary else 'w'
            public_key, private_key = RSAKeyHandle.get_key_pair_name(prefix, binary)

            with open(os.path.join(path, private_key), mode) as fp:
                fp.write(key.private_key.encode()) if binary else fp.write(key.private_key)

            with open(os.path.join(path, public_key), mode) as fp:
                fp.write(key.public_key.encode()) if binary else fp.write(key.public_key)

            return True
        except OSError as e:
            print("'generate_key_pair_and_save' error: {}".format(e))
            return False


class RSAPublicKeyHandle(RSAKeyHandle):
    KEYWORDS = ('BEGIN PUBLIC KEY', 'END PUBLIC KEY')

    def __init__(self, key: str):
        super(RSAPublicKeyHandle, self).__init__(key)

    def verify(self, message: bytes, signature, hash_algo: str = 'SHA'):
        try:
            verifier = PKCS1_signature.new(self._key)
            return verifier.verify(self.get_hash_algo_from_str(hash_algo).new(message), signature)
        except binascii.Error:
            return False


class RSAPrivateKeyHandle(RSAKeyHandle):
    KEYWORDS = ('BEGIN RSA PRIVATE KEY', 'END RSA PRIVATE KEY')

    def __init__(self, key: str, pwd: str = None):
        super(RSAPrivateKeyHandle, self).__init__(key, pwd)

    def sign(self, message: bytes, hash_algo: str = 'SHA') -> bytes:
        singer = PKCS1_signature.new(self._key)
        return singer.sign(self.get_hash_algo_from_str(hash_algo).new(message))


class DESCrypto(object):
    def __init__(self, key: str, iv: str):
        self._iv = iv
        self._key = key
        self._des = pyDes.des(self._key, pyDes.CBC, self._iv, pad=None, padmode=pyDes.PAD_PKCS5)

    def encrypt(self, data: bytes) -> bytes:
        return self._des.encrypt(data)

    def decrypt(self, data: bytes) -> bytes:
        return self._des.decrypt(data)


class AESCrypto(object):
    BLOCK_SIZE = 16
    AES_CBC, AES_ECB, AES_GCM, AES_CTR = 'CBC', 'ECB', 'GCM', 'CTR'

    AES_MODE = {
        AES_CBC: AES.MODE_CBC,
        AES_ECB: AES.MODE_ECB,
        AES_CTR: AES.MODE_CTR,
        AES_GCM: AES.MODE_GCM
    }

    def __init__(self, key: bytes, mode: str = AES_ECB, vi: bytes = bytes(range(BLOCK_SIZE))):
        if mode not in self.AES_MODE:
            raise ValueError('Invalid mode: {!r} mode must be: {}'.format(mode, list(self.AES_MODE.keys())))

        self.__vi = vi
        self.__mode = mode
        self.__key = self.pad(key)

    def cipher(self):
        if self.__mode == self.AES_ECB:
            return AES.new(self.__key, self.AES_MODE.get(self.__mode))
        else:
            return AES.new(self.__key, self.AES_MODE.get(self.__mode), self.__vi)

    @staticmethod
    def pad(data: bytes) -> bytes:
        pl = AESCrypto.BLOCK_SIZE - (len(data) % AESCrypto.BLOCK_SIZE)
        return data + bytes([pl]) * pl

    @staticmethod
    def unpad(data: bytes) -> bytes:
        return data[:-data[-1]]

    @staticmethod
    def check(func: str, data: typing.Any):
        if not isinstance(data, bytes):
            raise TypeError("{!r} data must be bytes".format(func))

        if not data:
            raise ValueError('{!r} data is empty'.format(func))

    def encrypt(self, data: bytes) -> bytes:
        self.check('encrypt', data)
        return self.cipher().encrypt(self.pad(data))

    def decrypt(self, data: bytes) -> bytes:
        self.check('decrypt', data)
        plaintext = self.cipher().decrypt(data)
        return self.unpad(plaintext)


class CryptoCommException(Exception):
    pass


class CryptoCommLengthException(CryptoCommException):
    pass


class CryptoCommDecodeException(CryptoCommException):
    pass


class CryptoCommVerifyException(CryptoCommException):
    pass


def crypto_decrypt_data(
        public_key: RSAPublicKeyHandle, private_key: RSAPrivateKeyHandle, data: bytes, hash_algo: str = 'SHA256'
) -> bytes:
    sign_length = -384
    if len(data) <= sign_length:
        raise CryptoCommLengthException('request too short')

    cipher, sign = data[:sign_length], data[sign_length:]

    if not public_key.verify(cipher, sign, hash_algo):
        raise CryptoCommVerifyException('verify request failed')

    raw = private_key.decrypt(cipher)
    if not raw:
        raise CryptoCommDecodeException('decrypt request failed')

    return raw


def crypto_encrypt_data(
        public_key: RSAPublicKeyHandle, private_key: RSAPrivateKeyHandle, data: bytes, hash_algo: str = 'SHA256'
) -> bytes:
    cipher = public_key.encrypt(data)
    sign = private_key.sign(cipher, hash_algo)
    return cipher + sign


def crypto_communication(
        public_key: RSAPublicKeyHandle, private_key: RSAPrivateKeyHandle,
        data: bytes, comm_core: typing.Callable[[bytes], bytes], hash_algo: str = 'SHA256'
) -> bytes:
    data = crypto_encrypt_data(public_key, private_key, data, hash_algo)
    return crypto_decrypt_data(public_key, private_key, comm_core(data), hash_algo)
