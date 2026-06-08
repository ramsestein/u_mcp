"""Cross-validation — client-server signature verification."""

import hashlib
import hmac
from typing import Optional
from umcp.audit.models import AuditEvent


class CrossValidator:
    """Validates events across client and server sides."""

    @staticmethod
    def sign_event(event_hash: str, client_secret: str) -> str:
        """Client signs an event hash with their secret."""
        signer = hmac.new(
            client_secret.encode("utf-8"),
            event_hash.encode("utf-8"),
            hashlib.sha256,
        )
        return signer.hexdigest()

    @staticmethod
    def verify_client_signature(
        event: AuditEvent, client_secret: str
    ) -> bool:
        """Verify that the client's signature matches."""
        if not event.client_signature:
            return False
        expected = CrossValidator.sign_event(event.event_hash, client_secret)
        return hmac.compare_digest(event.client_signature, expected)

    @staticmethod
    def verify_server_response(
        event: AuditEvent, response_body: str
    ) -> bool:
        """Verify that the stored response hash matches the actual response."""
        if not event.server_response_hash:
            return False
        actual = hashlib.sha256(response_body.encode("utf-8")).hexdigest()
        return actual == event.server_response_hash

    @staticmethod
    def generate_challenge(event: AuditEvent) -> str:
        """Generate a challenge for the client to sign."""
        return f"{event.event_id}:{event.event_hash}:{event.timestamp.isoformat()}"