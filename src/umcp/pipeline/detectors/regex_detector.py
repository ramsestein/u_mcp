"""Regex-based entity detector for structured PII patterns."""

import re
from typing import List, Pattern
from umcp.pipeline.detectors.base import Entity, EntityDetector


class RegexDetector(EntityDetector):
    """Detects structured PII using regex patterns."""

    PATTERNS: List[tuple[str, str, Pattern]] = [
        # IPv4
        ("IP", re.compile(
            r'\b(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\b'
        )),
        # Email
        ("EMAIL", re.compile(
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        )),
        # URL
        ("URL", re.compile(
            r'\bhttps?://[^\s<>"\'{}|\\^`\[\]]+'
        )),
        # Phone (Spanish format: +34 XXX XXX XXX, 6XX XXX XXX, 9XX XXX XXX)
        ("PHONE", re.compile(
            r'\b(?:\+34\s?)?[6-9]\d{2}\s?\d{3}\s?\d{3}\b'
        )),
        # NHC (Spanish National Health Card: 4 digits + 2 letters + optional digits)
        ("NHC", re.compile(
            r'\b\d{4}[A-Z]{2}\d{0,4}\b'
        )),
        # DNI/NIF (Spanish ID: 8 digits + letter)
        ("DNI", re.compile(
            r'\b\d{8}[A-Z]\b'
        )),
        # NASS (Spanish Social Security Number)
        ("NASS", re.compile(
            r'\b\d{2}/\d{8}/\d{2}\b'
        )),
        # MD5 hash
        ("HASH_MD5", re.compile(
            r'\b[a-fA-F0-9]{32}\b'
        )),
        # SHA1 hash
        ("HASH_SHA1", re.compile(
            r'\b[a-fA-F0-9]{40}\b'
        )),
        # SHA256 hash
        ("HASH_SHA256", re.compile(
            r'\b[a-fA-F0-9]{64}\b'
        )),
        # NTLM hash
        ("HASH_NTLM", re.compile(
            r'\b[a-fA-F0-9]{32}\b'
        )),
        # JWT (JSON Web Token)
        ("JWT", re.compile(
            r'\beyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b'
        )),
        # AWS Access Key
        ("AWS_KEY", re.compile(
            r'\bAKIA[0-9A-Z]{16}\b'
        )),
        # Generic API Key pattern
        ("API_KEY", re.compile(
            r'\b(?:sk|pk|api|key|token|secret)[-_]?[A-Za-z0-9]{16,}\b',
            re.IGNORECASE,
        )),
    ]

    def __init__(self):
        # Build named patterns
        self._patterns = [
            (name, compiled)
            for name, compiled in self.PATTERNS
        ]

    def detect(self, text: str) -> List[Entity]:
        entities = []
        seen_spans: set = set()

        for type_name, pattern in self._patterns:
            for match in pattern.finditer(text):
                span = (match.start(), match.end())
                if span not in seen_spans:
                    seen_spans.add(span)
                    entities.append(Entity(
                        type=type_name,
                        text=match.group(),
                        start=match.start(),
                        end=match.end(),
                        score=1.0,
                        detector="regex",
                    ))

        return sorted(entities, key=lambda e: e.start)