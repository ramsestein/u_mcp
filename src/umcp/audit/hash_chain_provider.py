"""Hash chain provider — SHA-256 hashing + HMAC signing + chain validation."""

import hashlib
import hmac
import logging
from typing import Optional, Tuple
from umcp.audit.models import AuditEvent
from umcp.audit.chain_store import ChainStore

logger = logging.getLogger(__name__)

GENESIS_HASH = "0" * 64  # Genesis block previous_hash


class HashChainProvider:
    """Manages the blockchain-like hash chain for audit events."""

    def __init__(self, store: ChainStore, gateway_secret: str):
        self.store = store
        self.gateway_secret = gateway_secret

    def record_event(
        self,
        event_type: str,
        actor_id: str,
        action: str,
        result: str,
        resource: Optional[dict] = None,
        metadata: Optional[dict] = None,
        error: Optional[str] = None,
        client_signature: Optional[str] = None,
        server_response_hash: Optional[str] = None,
    ) -> AuditEvent:
        """Create, hash, sign, and store an audit event."""
        # Get the last event's hash for chaining
        last_event = self.store.get_last_event()
        previous_hash = last_event.event_hash if last_event else GENESIS_HASH

        # Create the event
        event = AuditEvent(
            event_type=event_type,
            actor_id=actor_id,
            action=action,
            result=result,
            resource=resource or {},
            metadata=metadata or {},
            error=error,
            previous_hash=previous_hash,
            client_signature=client_signature,
            server_response_hash=server_response_hash,
        )

        # Compute event hash (SHA-256 of content)
        content = event.get_content_string()
        event.event_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()

        # Sign with gateway secret (HMAC-SHA256)
        signer = hmac.new(
            self.gateway_secret.encode("utf-8"),
            event.event_hash.encode("utf-8"),
            hashlib.sha256,
        )
        event.gateway_signature = signer.hexdigest()

        # Store (append-only)
        self.store.append(event)
        return event

    def validate_chain(self) -> Tuple[bool, int, int]:
        """Validate the entire chain. Returns (valid, events_checked, errors_found)."""
        events = self.store.get_all_events()
        errors = 0
        previous_hash = GENESIS_HASH

        for event in events:
            # Check previous_hash link
            if event.previous_hash != previous_hash:
                logger.error(
                    f"Chain break at {event.event_id}: "
                    f"expected prev_hash {previous_hash[:16]}..., "
                    f"got {event.previous_hash[:16]}..."
                )
                errors += 1

            # Recompute event hash
            expected_hash = hashlib.sha256(
                event.get_content_string().encode("utf-8")
            ).hexdigest()
            if event.event_hash != expected_hash:
                logger.error(
                    f"Hash mismatch at {event.event_id}: "
                    f"expected {expected_hash[:16]}..., "
                    f"got {event.event_hash[:16]}..."
                )
                errors += 1

            # Verify gateway signature
            verifier = hmac.new(
                self.gateway_secret.encode("utf-8"),
                event.event_hash.encode("utf-8"),
                hashlib.sha256,
            )
            if event.gateway_signature != verifier.hexdigest():
                logger.error(
                    f"Signature mismatch at {event.event_id}"
                )
                errors += 1

            previous_hash = event.event_hash

        return errors == 0, len(events), errors

    def validate_range(self, from_id: str, to_id: str) -> Tuple[bool, int]:
        """Validate a range of events. Returns (valid, events_checked)."""
        events = self.store.get_all_events()
        in_range = False
        errors = 0
        count = 0

        for i, event in enumerate(events):
            if event.event_id == from_id:
                in_range = True

            if in_range:
                count += 1
                # Check link to previous in chain
                if i > 0:
                    expected_prev = events[i - 1].event_hash
                    if event.previous_hash != expected_prev:
                        errors += 1

            if event.event_id == to_id:
                break

        return errors == 0, count