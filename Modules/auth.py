import base64
import hashlib
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend

BS = 32
pad = lambda s: s + (BS - len(s) % BS) * chr(BS - len(s) % BS).encode()


class AESCipher:
    def __init__(self, key: str):
        self.key = hashlib.sha256(key.encode()).digest()
        self.backend = default_backend()

    def encrypt(self, message: str) -> str:
        raw = pad(message.encode())
        iv = b"\x00" * 16
        cipher = Cipher(algorithms.AES(self.key), modes.CBC(iv), backend=self.backend)
        encryptor = cipher.encryptor()
        enc = encryptor.update(raw) + encryptor.finalize()
        return base64.b64encode(enc).decode("utf-8")
