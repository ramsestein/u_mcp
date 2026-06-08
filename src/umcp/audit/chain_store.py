"""Append-only SQLite store for the audit chain."""

import json
import sqlite3
import time
from pathlib import Path
from typing import List, Optional
from umcp.audit.models import AuditEvent


class ChainStore:
    """Append-only SQLite store for audit events."""

    def __init__(self, db_path: Path):
        self._db_path = db_path
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(db_path))
        self._init_schema()

    def _init_schema(self) -> None:
        """Initialize the append-only schema."""
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS audit_chain (
                event_id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                event_type TEXT NOT NULL,
                actor_id TEXT NOT NULL,
                resource TEXT,
                action TEXT,
                result TEXT,
                previous_hash TEXT NOT NULL,
                event_hash TEXT NOT NULL UNIQUE,
                gateway_signature TEXT NOT NULL,
                client_signature TEXT,
                server_response_hash TEXT,
                metadata TEXT,
                error TEXT,
                created_at REAL NOT NULL
            )
        """)
        self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_chain_type ON audit_chain(event_type)
        """)
        self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_chain_actor ON audit_chain(actor_id)
        """)
        self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_chain_timestamp ON audit_chain(timestamp)
        """)
        self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_chain_hash ON audit_chain(event_hash)
        """)
        self._conn.commit()

    def append(self, event: AuditEvent) -> None:
        """Append an event (INSERT only, never UPDATE or DELETE)."""
        self._conn.execute("""
            INSERT INTO audit_chain (
                event_id, timestamp, event_type, actor_id,
                resource, action, result, previous_hash,
                event_hash, gateway_signature, client_signature,
                server_response_hash, metadata, error, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            event.event_id,
            event.timestamp.isoformat(),
            event.event_type,
            event.actor_id,
            json.dumps(event.resource),
            event.action,
            event.result,
            event.previous_hash,
            event.event_hash,
            event.gateway_signature,
            event.client_signature,
            event.server_response_hash,
            json.dumps(event.metadata),
            event.error,
            time.time(),
        ))
        self._conn.commit()

    def get_event(self, event_id: str) -> Optional[AuditEvent]:
        """Get an event by ID."""
        cursor = self._conn.execute(
            "SELECT * FROM audit_chain WHERE event_id = ?", (event_id,)
        )
        row = cursor.fetchone()
        return self._row_to_event(row) if row else None

    def get_last_event(self) -> Optional[AuditEvent]:
        """Get the most recent event."""
        cursor = self._conn.execute(
            "SELECT * FROM audit_chain ORDER BY created_at DESC LIMIT 1"
        )
        row = cursor.fetchone()
        return self._row_to_event(row) if row else None

    def get_events(
        self,
        event_type: Optional[str] = None,
        actor_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[AuditEvent]:
        """Get events with optional filters."""
        query = "SELECT * FROM audit_chain WHERE 1=1"
        params = []

        if event_type:
            query += " AND event_type = ?"
            params.append(event_type)
        if actor_id:
            query += " AND actor_id = ?"
            params.append(actor_id)

        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        cursor = self._conn.execute(query, params)
        return [self._row_to_event(row) for row in cursor.fetchall()]

    def get_all_events(self) -> List[AuditEvent]:
        """Get ALL events (for export)."""
        cursor = self._conn.execute(
            "SELECT * FROM audit_chain ORDER BY created_at ASC"
        )
        return [self._row_to_event(row) for row in cursor.fetchall()]

    def get_chain_length(self) -> int:
        cursor = self._conn.execute("SELECT COUNT(*) FROM audit_chain")
        return cursor.fetchone()[0]

    def purge_older_than(self, days: int) -> int:
        """Purge events older than N days. Returns count purged."""
        cutoff = time.time() - (days * 86400)
        cursor = self._conn.execute(
            "DELETE FROM audit_chain WHERE created_at < ?", (cutoff,)
        )
        self._conn.commit()
        return cursor.rowcount

    def close(self) -> None:
        self._conn.close()

    @staticmethod
    def _row_to_event(row) -> Optional[AuditEvent]:
        if not row:
            return None
        from datetime import datetime
        return AuditEvent(
            event_id=row[0],
            timestamp=datetime.fromisoformat(row[1]),
            event_type=row[2],
            actor_id=row[3],
            resource=json.loads(row[4]) if row[4] else {},
            action=row[5],
            result=row[6],
            previous_hash=row[7],
            event_hash=row[8],
            gateway_signature=row[9],
            client_signature=row[10],
            server_response_hash=row[11],
            metadata=json.loads(row[12]) if row[12] else {},
            error=row[13],
        )