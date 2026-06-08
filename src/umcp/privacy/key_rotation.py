"""Key rotation — monthly rotation of encryption keys."""

import os
import base64
import logging
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)


class KeyRotation:
    """Manages encryption key lifecycle and rotation."""

    def __init__(self, rotation_days: int = 30):
        self.rotation_days = rotation_days
        self._key_history: list = []

    def generate_key(self) -> str:
        """Generate a new 32-byte encryption key."""
        key = base64.urlsafe_b64encode(os.urandom(32)).decode("utf-8")
        self._key_history.append({
            "key": key,
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        return key

    def should_rotate(self, key_created_at: str) -> bool:
        """Check if a key should be rotated based on age."""
        from datetime import datetime
        try:
            created = datetime.fromisoformat(key_created_at)
            age = (datetime.now(timezone.utc) - created).days
            return age >= self.rotation_days
        except (ValueError, TypeError):
            return True

    def rotate_key(self, old_key: str) -> str:
        """Rotate an old key and return a new one."""
        new_key = self.generate_key()
        logger.info(
            f"Key rotated: old_key={old_key[:8]}... → "
            f"new_key={new_key[:8]}..."
        )
        return new_key