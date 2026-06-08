"""SHA-256 reproducible surrogate generation.

Adapted from pseudo_datanex_notes — deterministic surrogates
using SHA-256 seeds for reproducibility.
"""

import hashlib
import random
from typing import Dict, Optional


class SurrogateGenerator:
    """Generates reproducible surrogates for entity values."""

    def __init__(self, seed_base: str = "umcp"):
        self.seed_base = seed_base
        self._counter: int = 0

    def _derive_seed(self, original: str) -> int:
        """Derive a reproducible seed from the original value."""
        combined = f"{self.seed_base}:{original}"
        digest = hashlib.sha256(combined.encode("utf-8")).digest()
        return int.from_bytes(digest, byteorder="big")

    def generate(self, entity_type: str, original: str) -> str:
        """Generate a deterministic surrogate for an entity value."""
        seed = self._derive_seed(original)
        rng = random.Random(seed)

        prefix_map = {
            "PERSON": "PACIENTE",
            "LOCATION": "UBICACION",
            "NHC": "NHC",
            "NASS": "NASS",
            "PHONE": "TELF",
            "EMAIL": "EMAIL",
            "DNI": "DNI",
            "IP": "IP",
            "URL": "URL",
            "GENERICA": "ENT",
            "ID": "ID",
            "HASH_MD5": "HASH",
            "HASH_SHA1": "HASH",
            "HASH_SHA256": "HASH",
            "HASH_NTLM": "HASH",
            "JWT": "TOKEN",
            "AWS_KEY": "AWS",
            "API_KEY": "KEY",
            "UNICODE_ZERO_WIDTH": "UNI",
            "UNICODE_BIDI_OVERRIDE": "BIDI",
            "UNICODE_PUA": "PUA",
            "UNICODE_HOMOGLYPH": "HOM",
        }

        prefix = prefix_map.get(entity_type, "ENT")
        # Generate random hex suffix
        suffix = format(rng.getrandbits(40), "08x").upper()
        return f"{prefix}_{suffix}"


class MappingStore:
    """In-memory bidirectional mapping store."""

    def __init__(self):
        self._real_to_surrogate: Dict[str, str] = {}
        self._surrogate_to_real: Dict[str, str] = {}

    def add(self, real: str, surrogate: str) -> None:
        self._real_to_surrogate[real] = surrogate
        self._surrogate_to_real[surrogate] = real

    def get_surrogate(self, real: str) -> Optional[str]:
        return self._real_to_surrogate.get(real)

    def get_real(self, surrogate: str) -> Optional[str]:
        return self._surrogate_to_real.get(surrogate)

    def clear(self) -> None:
        self._real_to_surrogate.clear()
        self._surrogate_to_real.clear()

    @property
    def count(self) -> int:
        return len(self._real_to_surrogate)

    def get_all_mappings(self) -> Dict[str, str]:
        return dict(self._real_to_surrogate)