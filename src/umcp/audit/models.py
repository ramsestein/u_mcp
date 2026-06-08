"""Audit event models with hash chain fields."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import uuid4


@dataclass
class AuditEvent:
    """A single event in the blockchain-like audit chain."""

    # Identity
    event_id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    # Event metadata
    event_type: str = ""       # AUTH | TOOL_CALL | GUARDRAIL | ANONYMIZATION | CONFIG_CHANGE | BREACH
    actor_id: str = ""         # gateway_key or user identifier
    resource: Dict[str, Any] = field(default_factory=dict)
    action: str = ""           # requested | executed | blocked | modified | detected
    result: str = ""           # success | failure | blocked | error

    # Hash chain (blockchain-like)
    previous_hash: str = ""    # SHA-256 of previous event
    event_hash: str = ""       # SHA-256 of this event's content
    gateway_signature: str = ""  # HMAC-SHA256(event_hash, gateway_secret)

    # Cross-validation
    client_signature: Optional[str] = None  # HMAC-SHA256(event_hash, client_secret)
    server_response_hash: Optional[str] = None

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict (excluding sensitive fields)."""
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp.isoformat(),
            "event_type": self.event_type,
            "actor_id": self.actor_id[:8] + "..." if len(self.actor_id) > 8 else self.actor_id,
            "resource": self.resource,
            "action": self.action,
            "result": self.result,
            "previous_hash": self.previous_hash[:16] + "...",
            "event_hash": self.event_hash,
            "gateway_signature": self.gateway_signature[:16] + "...",
            "client_signature": self.client_signature is not None,
            "metadata": self.metadata,
            "error": self.error,
        }

    def get_content_string(self) -> str:
        """Get the content string used for hashing."""
        return "|".join([
            self.event_id,
            self.timestamp.isoformat(),
            self.event_type,
            self.actor_id,
            self.action,
            self.result,
            self.previous_hash,
            str(self.resource),
            str(self.metadata),
            str(self.error),
        ])