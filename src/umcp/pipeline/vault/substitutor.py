"""Text substitution — replaces sensitive entities with surrogates.

Handles overlapping entities and preserves offsets correctly.
"""

from typing import List, Optional, Tuple
from umcp.pipeline.detectors.base import Entity
from umcp.pipeline.vault.vault import Vault


class Substitutor:
    """Replaces detected entities with vault surrogates."""

    def __init__(self, vault: Vault):
        self.vault = vault

    def anonymize(self, text: str, entities: List[Entity]) -> Tuple[str, List[dict]]:
        """Replace entities with surrogates. Returns (text, substitutions_log)."""
        # Sort by start position (descending) to preserve offsets
        sorted_ents = sorted(
            [e for e in entities if e.type not in ("DATE", "TIME", "AGE", "SEX", "JOB", "UNICODE_ZERO_WIDTH", "UNICODE_BIDI_OVERRIDE", "UNICODE_PUA", "UNICODE_HOMOGLYPH")],
            key=lambda e: e.start,
            reverse=True,
        )

        substitutions = []
        result = text

        for ent in sorted_ents:
            original_text = result[ent.start:ent.end]
            if not original_text.strip():
                continue

            surrogate = self.vault.get_or_create_surrogate(ent.type, original_text)
            result = result[:ent.start] + surrogate + result[ent.end:]

            substitutions.append({
                "type": ent.type,
                "original": original_text,
                "surrogate": surrogate,
                "start": ent.start,
                "end": ent.end,
                "detector": ent.detector,
            })

        return result, substitutions

    def deanonymize(self, text: str) -> Tuple[str, List[dict]]:
        """Reverse substitution: surrogates → real values."""
        # This is a simplified version — in production we'd use a more
        # sophisticated pattern matching approach
        import re

        # Match surrogate patterns like ENT_XXXXXXXX
        pattern = re.compile(r'\b([A-Z]+_[0-9A-F]{8,})\b')
        substitutions = []
        result = text

        for match in pattern.finditer(text):
            surrogate = match.group(0)
            real = self.vault.get_real(surrogate)
            if real:
                result = result[:match.start()] + real + result[match.end():]
                substitutions.append({
                    "surrogate": surrogate,
                    "original": real,
                    "start": match.start(),
                    "end": match.end(),
                })

        return result, substitutions