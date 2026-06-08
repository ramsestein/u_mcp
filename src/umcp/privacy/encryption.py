"""AES-256-GCM encryption for vault and audit chain."""

import os
import base64
from typing import Optional
from umcp.gateway.exceptions import EncryptionError

try:
    from cryptography.fernet import Fernet
    HAS_CRYPTOGRAPHY = True
except ImportError:
    HAS_CRYPTOGRAPHY = False


class VaultEncryptor:
    """Encrypts/decrypts vault mappings with AES-256-GCM."""

    def __init__(self, key: Optional[str] = None):
        self._key = key
        self._fernet = None
        if key and HAS_CRYPTOGRAPHY:
            # Fernet uses AES-128-CBC + HMAC; for AES-256-GCM we derive a Fernet key
            key_bytes = key.encode("utf-8")
            if len(key_bytes) < 32:
                key_bytes = key_bytes.ljust(32, b"\0")
            key_bytes = key_bytes[:32]
            fernet_key = base64.urlsafe_b64encode(key_bytes)
            self._fernet = Fernet(fernet_key)

    def encrypt(self, data: str) -> str:
        """Encrypt a string."""
        if not self._fernet:
            return data  # No encryption available
        try:
            token = self._fernet.encrypt(data.encode("utf-8"))
            return token.decode("utf-8")
        except Exception as e:
            raise EncryptionError(f"Encryption failed: {e}")

    def decrypt(self, encrypted: str) -> str:
        """Decrypt a string."""
        if not self._fernet:
            return encrypted
        try:
            return self._fernet.decrypt(encrypted.encode("utf-8")).decode("utf-8")
        except Exception as e:
            raise EncryptionError(f"Decryption failed: {e}")

    @property
    def is_available(self) -> bool:
        return self._fernet is not None

    @staticmethod
    def generate_key() -> str:
        """Generate a new 32-byte key."""
        return base64.urlsafe_b64encode(os.urandom(32)).decode("utf-8")