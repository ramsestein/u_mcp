"""Date preserver — detects dates and ensures they are NOT anonymized.

Adapted from carmina_3_suite: protects header patterns and date values.
"""

import re
from typing import List, Set, Tuple


# Pattern: "Fecha: DD.MM.YYYY Hora: HH:MM:SS"
HEADER_PATTERN = re.compile(
    r"(?:Fecha|Feecha|Fech|Fec\.?):\s*\d{1,2}[./]\d{1,2}[./]\d{2,4}\s*"
    r"(?:Hora|Hoora|Hor\.?):\s*\d{1,2}:\d{2}(?::\d{2})?",
    re.IGNORECASE,
)

# Bare date patterns (DD.MM.YYYY, DD/MM/YYYY, YYYY-MM-DD, DD-MM-YYYY)
DATE_PATTERNS = [
    re.compile(r'\b\d{1,2}\.\d{1,2}\.\d{2,4}\b'),     # DD.MM.YYYY
    re.compile(r'\b\d{1,2}/\d{1,2}/\d{2,4}\b'),       # DD/MM/YYYY
    re.compile(r'\b\d{4}-\d{2}-\d{2}\b'),              # YYYY-MM-DD
    re.compile(r'\b\d{2}-\d{2}-\d{4}\b'),              # DD-MM-YYYY
]

# Time patterns
TIME_PATTERN = re.compile(r'\b\d{2}:\d{2}(?::\d{2})?\b')


class DatePreserver:
    """Detects and preserves dates (marks them as non-anonymizable)."""

    def __init__(self):
        self._protected_ranges: List[Tuple[int, int]] = []

    def find_protected_ranges(self, text: str) -> List[Tuple[int, int]]:
        """Find all date/time ranges that should be protected."""
        ranges: Set[Tuple[int, int]] = set()

        # Full header patterns
        for m in HEADER_PATTERN.finditer(text):
            ranges.add((m.start(), m.end()))

        # Individual dates
        for pattern in DATE_PATTERNS:
            for m in pattern.finditer(text):
                ranges.add((m.start(), m.end()))

        # Individual times
        for m in TIME_PATTERN.finditer(text):
            ranges.add((m.start(), m.end()))

        return sorted(ranges)

    def is_protected(self, start: int, end: int, protected_ranges: List[Tuple[int, int]]) -> bool:
        """Check if a span overlaps with any protected range."""
        for ps, pe in protected_ranges:
            if not (end <= ps or start >= pe):
                return True
        return False

    def filter_protected(
        self, entities: list, text: str
    ) -> list:
        """Filter out entities that overlap with protected ranges."""
        protected = self.find_protected_ranges(text)
        return [e for e in entities if not self.is_protected(e.start, e.end, protected)]