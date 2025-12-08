import base64
import hashlib
import sys

# from Crypto.Cipher import AES
# from Cryptodome.Cipher import AES

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
import base64

sys.stdout.reconfigure(encoding="utf-8")
KEY = "3dpdx!*#$rootlabaes!&$#2025&$#%5"
BS = 32  # 블록 크기
pad = lambda s: s + (BS - len(s) % BS) * chr(BS - len(s) % BS).encode()
unpad = lambda s: s[:-ord(s[-1:])]
# 기존 구조 유지: aescrypto 패키지처럼 동일한 클래스와 KEY 사용
class AESCipher:
    def __init__(self, key):
        self.key = hashlib.sha256(key.encode()).digest()
        self.backend = default_backend()

    def encrypt(self, message):
        message = message.encode()
        raw = pad(message)
        iv = b"\x00" * 16  # 초기화 벡터 (IV)
        cipher = Cipher(algorithms.AES(self.key), modes.CBC(iv), backend=self.backend)
        encryptor = cipher.encryptor()
        enc = encryptor.update(raw) + encryptor.finalize()
        return base64.b64encode(enc).decode("utf-8")

    def decrypt(self, enc):
        enc = base64.b64decode(enc)
        iv = b"\x00" * 16  # 초기화 벡터 (IV)
        cipher = Cipher(algorithms.AES(self.key), modes.CBC(iv), backend=self.backend)
        decryptor = cipher.decryptor()
        dec = decryptor.update(enc) + decryptor.finalize()
        return unpad(dec).decode("utf-8")

    def _pad(self, s):
        # PKCS7 패딩
        block_size = 16
        pad_len = block_size - (len(s) % block_size)
        return s + (chr(pad_len) * pad_len)
