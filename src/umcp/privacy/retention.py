"""Retention policies — TTL, cleanup worker, secure wipe."""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class RetentionPolicy:
    """Configuration for data retention."""
    vault_ttl_hours: float = 1
    vault_max_ttl_hours: float = 8
    audit_chain_ttl_days: int = 90
    intermediate_ttl_days: int = 0
    cleanup_interval_seconds: float = 300


class RetentionManager:
    """Manages data lifecycle with automatic cleanup."""

    def __init__(self, policy: RetentionPolicy = None):
        self.policy = policy or RetentionPolicy()
        self._cleanup_tasks: Dict[str, Callable] = {}

    def register_cleanup(self, name: str, callback: Callable) -> None:
        """Register a cleanup callback."""
        self._cleanup_tasks[name] = callback

    async def run_cleanup_cycle(self) -> Dict[str, int]:
        """Run all cleanup tasks. Returns {task_name: items_cleaned}."""
        results = {}
        for name, callback in self._cleanup_tasks.items():
            try:
                if asyncio.iscoroutinefunction(callback):
                    count = await callback()
                else:
                    count = callback()
                results[name] = count
                if count > 0:
                    logger.info(f"Cleanup '{name}': removed {count} items")
            except Exception as e:
                logger.error(f"Cleanup '{name}' failed: {e}")
                results[name] = -1
        return results

    async def cleanup_worker(self):
        """Async worker that periodically runs cleanup cycles."""
        while True:
            await asyncio.sleep(self.policy.cleanup_interval_seconds)
            await self.run_cleanup_cycle()

    @staticmethod
    def secure_wipe_file(path: Path) -> bool:
        """Securely wipe a file (3-pass overwrite)."""
        if not path.exists():
            return False
        try:
            size = path.stat().st_size
            with open(path, "wb") as f:
                f.write(b"\x00" * size)
                f.flush()
                f.seek(0)
                f.write(b"\xFF" * size)
                f.flush()
                f.seek(0)
                f.write(b"\xAA" * size)
                f.flush()
            path.unlink()
            return True
        except Exception as e:
            logger.error(f"Secure wipe failed for {path}: {e}")
            return False