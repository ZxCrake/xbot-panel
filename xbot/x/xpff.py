import os
import binascii
import hashlib
import json
import time
from typing import Tuple
#from pydantic import BaseModel
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes

BASE_KEY = os.getenv(
    "XPFF_BASE_KEY",
    "0e6be1f1e21ffc33590b888fd4dc81b19713e570e805d4e5df80a493c9571a05",
)

class XPFFHeaderGenerator:

    __slots__ = ("base_key",)

    def __init__(self, base_key: str):
        self.base_key = base_key

    def _derive_key(self, guest_id: str) -> bytes:
        return hashlib.sha256((self.base_key + guest_id).encode()).digest()

    def _aes_gcm_encrypt(self, payload: str, guest_id: str) -> str:
        key = self._derive_key(guest_id)
        nonce = get_random_bytes(12)  # 96‑bit GCM nonce
        cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
        ct, tag = cipher.encrypt_and_digest(payload.encode())
        return binascii.hexlify(nonce + ct + tag).decode()

    def _aes_gcm_decrypt(self, token_hex: str, guest_id: str) -> str:
        raw = binascii.unhexlify(token_hex)
        nonce, ct, tag = raw[:12], raw[12:-16], raw[-16:]
        cipher = AES.new(self._derive_key(guest_id), AES.MODE_GCM, nonce=nonce)
        return cipher.decrypt_and_verify(ct, tag).decode()

    def generate(self, user_agent: str, guest_id: str, has_been_active: bool = False) -> Tuple[str, int]:
        payload_obj = {
            "navigator_properties": {
                "hasBeenActive": "true",
                "userAgent": user_agent,
                "webdriver": "false",
            },
            "created_at": int(time.time() * 1000),
        }
        payload = json.dumps(payload_obj, separators=(",", ":"))
        token_hex = self._aes_gcm_encrypt(payload, guest_id)
        return token_hex, payload_obj["created_at"]

    def decode(self, token_hex: str, guest_id: str) -> dict:
        decrypted = self._aes_gcm_decrypt(token_hex, guest_id)
        return json.loads(decrypted)

"""
xpff = XPFFHeaderGenerator(BASE_KEY)
token, ts = xpff.generate("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36", "1939217445140525467", False)
print(token)
"""