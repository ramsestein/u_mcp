"""Vault lifecycle manager — creates, tracks, and cleans up vaults."""

import time
import logging
from typing import Dict, Optional
from umcp.pipeline.vault.vault import Vault

logger = logging.getLogger(__name__)


class VaultManager:
    """Manages vault lifecycle across sessions."""

    def __init__(
        self,
        idle_ttl: float = 3600,      # 1 hour idle
        max_ttl: float = 28800,      # 8 hours max
        cleanup_interval: float = 300,  # Check every 5 minutes
        encryption_key: Optional[str] = None,
    ):
        self._vaults: Dict[str, Vault] = {}
        self._idle_ttl = idle_ttl
        self._max_ttl = max_ttl
        self._cleanup_interval = cleanup_interval
        self._encryption_key = encryption_key
        self._last_cleanup = time.time()

    def get_or_create_vault(self, session_id: str) -> Vault:
        """Get existing vault or create a new one."""
        if session_id not in self._vaults:
            self._vaults[session_id] = Vault(
                session_id=session_id,
                encryption_key=self._encryption_key,
            )
            logger.info(f"Created vault for session {session_id}")
        return self._vaults[session_id]

    def get_vault(self, session_id: str) -> Optional[Vault]:
        return self._vaults.get(session_id)

    def cleanup_expired(self) -> int:
        """Clean up expired vaults. Returns number of vaults cleaned."""
        now = time.time()
        if now - self._last_cleanup < self._cleanup_interval:
            return 0

        self._last_cleanup = now
        expired = []

        for session_id, vault in self._vaults.items():
            if vault.is_expired(idle_ttl=self._idle_ttl, max_ttl=self._max_ttl):
                expired.append(session_id)

        for session_id in expired:
            try:
                vault = self._vaults.pop(session_id)
                vault.secure_wipe()
                logger.info(f"Cleaned up vault for session {session_id}")
            except Exception as e:
                logger.error(f"Failed to clean up vault {session_id}: {e}")

        return len(expired)

    def destroy_vault(self, session_id: str) -> bool:
        """Immediately destroy a vault."""
        vault = self._vaults.pop(session_id, None)
        if vault:
            vault.secure_wipe()
            return True
        return False

    async def cleanup_worker(self):
        """Async worker that periodically cleans up expired vaults."""
        import asyncio
        while True:
            count = self.cleanup_expired()
            if count:
                logger.info(f"Auto-cleanup: removed {count} expired vaults")
            await asyncio.sleep(self._cleanup_interval)

    @property
    def active_count(self) -> int:
        return len(self._vaults)

    @property
    def total_mappings(self) -> int:
        return sum(v.mapping_count for v in self._vaults.values())