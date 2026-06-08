"""Unicode sanitization — filter invisible/malicious Unicode characters."""

import re
import unicodedata
from typing import List
from umcp.pipeline.detectors.base import Entity, EntityDetector


# Unicode categories to flag
ZERO_WIDTH_CHARS = {
    '\u200B',  # Zero Width Space
    '\u200C',  # Zero Width Non-Joiner
    '\u200D',  # Zero Width Joiner
    '\uFEFF',  # Zero Width No-Break Space (BOM)
    '\u200E',  # Left-to-Right Mark
    '\u200F',  # Right-to-Left Mark
    '\u2060',  # Word Joiner
    '\u2061',  # Function Application
    '\u2062',  # Invisible Times
    '\u2063',  # Invisible Separator
    '\u2064',  # Invisible Plus
    '\u2066',  # Left-to-Right Isolate
    '\u2067',  # Right-to-Left Isolate
    '\u2068',  # First Strong Isolate
    '\u2069',  # Pop Directional Isolate
    '\u202A',  # Left-to-Right Embedding
    '\u202B',  # Right-to-Left Embedding
    '\u202C',  # Pop Directional Formatting
    '\u202D',  # Left-to-Right Override
    '\u202E',  # Right-to-Left Override (BIDI override)
}

# PUA (Private Use Areas) — often used for steganography
PUA_RANGES = [
    (0xE000, 0xF8FF),
    (0xF0000, 0xFFFFD),
    (0x100000, 0x10FFFD),
]


class UnicodeSanitizer(EntityDetector):
    """Detects invisible/malicious Unicode characters."""

    def __init__(self, strip: bool = True):
        self.strip = strip

    def detect(self, text: str) -> List[Entity]:
        entities = []
        for i, char in enumerate(text):
            codepoint = ord(char)

            # Zero-width characters
            if char in ZERO_WIDTH_CHARS:
                cat = unicodedata.category(char)
                entities.append(Entity(
                    type="UNICODE_ZERO_WIDTH",
                    text=repr(char),
                    start=i,
                    end=i + 1,
                    score=1.0,
                    detector="unicode",
                ))
                continue

            # Bidirectional override
            if cat := self._is_bidi_override(char):
                entities.append(Entity(
                    type=cat,
                    text=repr(char),
                    start=i,
                    end=i + 1,
                    score=1.0,
                    detector="unicode",
                ))
                continue

            # PUA
            if self._is_pua(codepoint):
                entities.append(Entity(
                    type="UNICODE_PUA",
                    text=repr(char),
                    start=i,
                    end=i + 1,
                    score=1.0,
                    detector="unicode",
                ))
                continue

            # Homoglyph detection (confusable characters)
            if self._is_homoglyph(char):
                entities.append(Entity(
                    type="UNICODE_HOMOGLYPH",
                    text=char,
                    start=i,
                    end=i + 1,
                    score=0.8,
                    detector="unicode",
                ))

        return entities

    def sanitize(self, text: str) -> str:
        """Remove or replace malicious Unicode characters."""
        result = []
        for char in text:
            codepoint = ord(char)
            if char in ZERO_WIDTH_CHARS:
                continue  # Strip
            if self._is_bidi_override(char):
                continue  # Strip
            if self._is_pua(codepoint):
                continue  # Strip
            result.append(char)
        return ''.join(result)

    @staticmethod
    def _is_bidi_override(char: str) -> str:
        if char in ('\u202E', '\u202D', '\u202B', '\u202A'):
            return "UNICODE_BIDI_OVERRIDE"
        return ""

    @staticmethod
    def _is_pua(codepoint: int) -> bool:
        for lo, hi in PUA_RANGES:
            if lo <= codepoint <= hi:
                return True
        return False

    @staticmethod
    def _is_homoglyph(char: str) -> bool:
        """Detect characters that look like ASCII but aren't."""
        suspicious = {
            '\u0430',  # Cyrillic 'а' (looks like Latin 'a')
            '\u0435',  # Cyrillic 'е' (looks like Latin 'e')
            '\u043E',  # Cyrillic 'о' (looks like Latin 'o')
            '\u0440',  # Cyrillic 'р' (looks like Latin 'p')
            '\u0441',  # Cyrillic 'с' (looks like Latin 'c')
            '\u0445',  # Cyrillic 'х' (looks like Latin 'x')
            '\u0456',  # Cyrillic 'і' (looks like Latin 'i')
        }
        return char in suspicious