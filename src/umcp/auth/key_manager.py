"""API Key authentication — 3-level key management."""

import hashlib
import hmac
import secrets
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class KeyRole(Enum):
    GATEWAY = "gateway"  # Can call tools
    ADMIN = "admin"      # Can manage servers/config
    AUDIT = "audit"      # Read-only audit access


@dataclass
class APIKey:
    """Represents a stored API key."""
    key_hash: str       # SHA-256 hash of the key
    role: KeyRole
    label: str = ""
    revoked: bool = False


class KeyManager:
    """Manages API key generation, storage, and validation."""

    def __init__(self):
        self._keys: dict[str, APIKey] = {}

    def generate_key(self, role: KeyRole, label: str = "") -> tuple[str, APIKey]:
        """Generate a new API key and return (raw_key, stored_key)."""
        raw_key = f"umcp-{role.value}-{secrets.token_hex(24)}"
        key_hash = self._hash_key(raw_key)
        stored = APIKey(key_hash=key_hash, role=role, label=label)
        self._keys[key_hash] = stored
        return raw_key, stored

    def register_key(self, raw_key: str, role: KeyRole, label: str = "") -> APIKey:
        """Register a pre-existing key."""
        key_hash = self._hash_key(raw_key)
        stored = APIKey(key_hash=key_hash, role=role, label=label)
        self._keys[key_hash] = stored
        return stored

    def validate_key(self, raw_key: str) -> Optional[APIKey]:
        """Validate a raw key and return its metadata, or None."""
        key_hash = self._hash_key(raw_key)
        stored = self._keys.get(key_hash)
        if stored and not stored.revoked:
            return stored
        return None

    def revoke_key(self, raw_key: str) -> bool:
        """Revoke a key by its raw value."""
        key_hash = self._hash_key(raw_key)
        stored = self._keys.get(key_hash)
        if stored:
            stored.revoked = True
            return True
        return False

    def revoke_by_hash(self, key_hash: str) -> bool:
        """Revoke a key by its hash."""
        stored = self._keys.get(key_hash)
        if stored:
            stored.revoked = True
            return True
        return False

    @staticmethod
    def _hash_key(raw_key: str) -> str:
        return hashlib.sha256(raw_key.encode()).hexdigest()


# Singleton
key_manager = KeyManager()