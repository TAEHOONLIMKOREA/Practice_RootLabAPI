import base64
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad


class AESCipher:
    """AES 암호화 (C# 호환)"""

    def __init__(self, key: str):
        self.key = key.encode('utf-8')[:32].ljust(32, b'\0')

    def encrypt(self, plaintext: str) -> str:
        """문자열 암호화"""
        cipher = AES.new(self.key, AES.MODE_ECB)
        padded_data = pad(plaintext.encode('utf-8'), AES.block_size)
        encrypted = cipher.encrypt(padded_data)
        return base64.b64encode(encrypted).decode('utf-8')
