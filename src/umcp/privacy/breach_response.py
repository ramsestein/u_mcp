"""Breach detection and response."""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class BreachEvent:
    """An immutable breach detection event."""
    timestamp: str
    breach_type: str        # PII_LEAK, REIDENTIFICATION_RISK, UNAUTHORIZED_ACCESS
    severity: str           # LOW | MEDIUM | HIGH | CRITICAL
    description: str
    source: str             # pipeline, audit, auth
    details: Dict[str, Any] = field(default_factory=dict)


class BreachResponse:
    """Detects PII leaks and triggers breach response."""

    def __init__(self, alert_webhook: Optional[str] = None):
        self.alert_webhook = alert_webhook
        self._breach_log: List[BreachEvent] = []

    def detect_pii_leak(
        self, text: str, entities: List[Dict[str, Any]]
    ) -> Optional[BreachEvent]:
        """Detect if PII leaked in output that should be clean."""
        # Check for known PII patterns in supposedly clean output
        import re
        patterns = {
            "PERSON_NAME": re.compile(r'\b[A-Z][a-z]+ [A-Z][a-z]+\b'),
            "EMAIL": re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b'),
            "PHONE": re.compile(r'\b(?:\+34\s?)?[6-9]\d{2}\s?\d{3}\s?\d{3}\b'),
            "NHC": re.compile(r'\b\d{4}[A-Z]{2}\d{0,4}\b'),
            "DNI": re.compile(r'\b\d{8}[A-Z]\b'),
        }

        leaks = []
        for ptype, pattern in patterns.items():
            matches = pattern.findall(text)
            for m in matches:
                leaks.append({"type": ptype, "value": m[:20]})

        if leaks:
            event = BreachEvent(
                timestamp=datetime.now(timezone.utc).isoformat(),
                breach_type="PII_LEAK",
                severity="HIGH",
                description=f"PII detected in output: {len(leaks)} potential leaks",
                source="pipeline",
                details={"leaks": leaks, "entity_count": len(entities)},
            )
            self._log_breach(event)
            return event
        return None

    def _log_breach(self, event: BreachEvent) -> None:
        """Log a breach event (immutable)."""
        self._breach_log.append(event)
        logger.critical(
            f"BREACH [{event.severity}] {event.breach_type}: {event.description}"
        )

    def get_breach_log(self) -> List[BreachEvent]:
        return list(self._breach_log)