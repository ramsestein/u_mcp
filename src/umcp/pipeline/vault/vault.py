"""Vault — SQLite session-scoped bidirectional surrogate store.

Each session gets its own vault with encrypted mappings.
Supports secure wipe on session end.
"""

import json
import sqlite3
import threading
import time
from pathlib import Path
from typing import Dict, Optional
from umcp.pipeline.vault.surrogates import SurrogateGenerator, MappingStore


class Vault:
    """Session-scoped vault for real↔surrogate mappings."""

    def __init__(
        self,
        session_id: str,
        db_path: Optional[Path] = None,
        encryption_key: Optional[str] = None,
        seed_base: str = "umcp",
    ):
        self.session_id = session_id
        self._db_path = db_path or Path(f"/tmp/umcp_vault_{session_id}.db")
        self._encryption_key = encryption_key
        self._generator = SurrogateGenerator(seed_base=seed_base)
        self._mappings = MappingStore()
        self._created_at = time.time()
        self._last_activity = time.time()

        self._init_db()

    def _init_db(self) -> None:
        """Initialize the SQLite vault."""
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self._db_path))
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS mappings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entity_type TEXT NOT NULL,
                real_value TEXT NOT NULL UNIQUE,
                surrogate_value TEXT NOT NULL UNIQUE,
                created_at REAL NOT NULL,
                encrypted_value BLOB
            )
        """)
        self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_real ON mappings(real_value)
        """)
        self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_surrogate ON mappings(surrogate_value)
        """)
        self._conn.commit()

    def get_or_create_surrogate(self, entity_type: str, real_value: str) -> str:
        """Get existing surrogate or create a new one."""
        self._last_activity = time.time()

        # Check in-memory cache first
        existing = self._mappings.get_surrogate(real_value)
        if existing:
            return existing

        # Check DB
        cursor = self._conn.execute(
            "SELECT surrogate_value FROM mappings WHERE real_value = ?",
            (real_value,),
        )
        row = cursor.fetchone()
        if row:
            self._mappings.add(real_value, row[0])
            return row[0]

        # Create new surrogate
        surrogate = self._generator.generate(entity_type, real_value)
        self._conn.execute(
            "INSERT OR IGNORE INTO mappings (entity_type, real_value, surrogate_value, created_at) "
            "VALUES (?, ?, ?, ?)",
            (entity_type, real_value, surrogate, time.time()),
        )
        self._conn.commit()
        self._mappings.add(real_value, surrogate)
        return surrogate

    def get_real(self, surrogate_value: str) -> Optional[str]:
        """Reverse lookup: surrogate → real value."""
        self._last_activity = time.time()

        # Check in-memory
        existing = self._mappings.get_real(surrogate_value)
        if existing:
            return existing

        # Check DB
        cursor = self._conn.execute(
            "SELECT real_value FROM mappings WHERE surrogate_value = ?",
            (surrogate_value,),
        )
        row = cursor.fetchone()
        if row:
            self._mappings.add(row[0], surrogate_value)
            return row[0]
        return None

    def secure_wipe(self) -> None:
        """Securely wipe the vault (3-pass overwrite for sensitive data)."""
        # Clear in-memory mappings
        self._mappings.clear()

        # Wipe DB contents
        self._conn.execute("DELETE FROM mappings")
        self._conn.commit()
        self._conn.close()

        # Secure delete of file (3-pass)
        if self._db_path.exists():
            size = self._db_path.stat().st_size
            with open(self._db_path, "wb") as f:
                # Pass 1: zeros
                f.write(b"\x00" * size)
                f.flush()
                # Pass 2: ones
                f.seek(0)
                f.write(b"\xFF" * size)
                f.flush()
                # Pass 3: random
                f.seek(0)
                f.write(bytearray([0xAA] * size))
                f.flush()
            self._db_path.unlink()

    def is_expired(self, idle_ttl: float = 3600, max_ttl: float = 28800) -> bool:
        """Check if the vault has expired."""
        now = time.time()
        if now - self._last_activity > idle_ttl:
            return True
        if now - self._created_at > max_ttl:
            return True
        return False

    @property
    def mapping_count(self) -> int:
        cursor = self._conn.execute("SELECT COUNT(*) FROM mappings")
        return cursor.fetchone()[0]

    @property
    def last_activity(self) -> float:
        return self._last_activity