"""
ClawFlow — Encryption Service (AES-256 via Fernet)
Used to encrypt/decrypt API keys and credentials at rest.
"""
import base64
import os

from cryptography.fernet import Fernet


class EncryptionService:
    """
    Symmetric encryption wrapper using Fernet (AES-128-CBC + HMAC).
    The key is read from the ENCRYPTION_KEY environment variable.
    """

    def __init__(self) -> None:
        raw_key = os.getenv("ENCRYPTION_KEY", "clawflow_enc_key_32_chars_exactly")
        # Pad/truncate to 32 bytes and base64-encode for Fernet
        key_bytes = raw_key.encode()[:32].ljust(32, b"0")
        self._fernet = Fernet(base64.urlsafe_b64encode(key_bytes))

    def encrypt(self, plain_text: str) -> str:
        return self._fernet.encrypt(plain_text.encode()).decode()

    def decrypt(self, cipher_text: str) -> str:
        return self._fernet.decrypt(cipher_text.encode()).decode()
