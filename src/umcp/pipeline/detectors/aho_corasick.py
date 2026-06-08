"""Aho-Corasick dictionary-based entity detector.

Adapted from pseudo_datanex_notes — uses automaton-based pattern matching
with stopwords, word boundary enforcement, and clinical terms filtering.
"""

import csv
import re
from pathlib import Path
from typing import List, Optional, Set
from umcp.pipeline.detectors.base import Entity, EntityDetector
import ahocorasick


# ── Ruta a los diccionarios editables ────────────────────────────────────
_DICT_DIR = (
    Path(__file__).parent.parent.parent.parent.parent
    / "resources"
    / "dictionaries"
).resolve()


def _load_dict(name: str) -> List[str]:
    """Load a dictionary file, one term per line."""
    path = _DICT_DIR / name
    if not path.exists():
        return []
    terms = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                terms.append(line.lower())
    return terms


# Separator chars for normalization
_RE_SEPARATORS = re.compile(r'[^\w\s]', re.UNICODE)
_RE_MULTI_SPACE = re.compile(r'\s+')

_MIN_PATTERN_LENGTH = 3

# Cargar stopwords y palabras clínicas desde archivos externos editables
# Si los archivos no existen, se usan listas vacías
_STOPWORDS: frozenset[str] = frozenset(_load_dict("stopwords.txt"))
_CLINICAL_WORDS: frozenset[str] = frozenset(_load_dict("clinical_words.txt"))


# Separator chars for normalization
_RE_SEPARATORS = re.compile(r'[^\w\s]', re.UNICODE)
_RE_MULTI_SPACE = re.compile(r'\s+')

_MIN_PATTERN_LENGTH = 3

# Cargar stopwords y palabras clínicas desde archivos externos editables
# Si los archivos no existen, se usan listas vacías
_STOPWORDS: frozenset[str] = frozenset(_load_dict("stopwords.txt"))
_CLINICAL_WORDS: frozenset[str] = frozenset(_load_dict("clinical_words.txt"))


class AhoCorasickDetector(EntityDetector):
    """Dictionary-based entity detector using Aho-Corasick automaton.

    Carga stopwords y palabras clínicas desde:
      resources/dictionaries/stopwords.txt
      resources/dictionaries/clinical_words.txt
      resources/dictionaries/entidades.csv (diccionario de entidades)
    """

    def __init__(self, dictionary_path: Optional[Path] = None):
        self._automaton: Optional[ahocorasick.Automaton] = None
        self._entity_type = "PERSON"
        if dictionary_path and dictionary_path.exists():
            self.load_dictionary(dictionary_path)

    def load_dictionary(self, csv_path: Path, entity_type: str = "PERSON") -> None:
        """Build the Aho-Corasick automaton from a CSV dictionary."""
        A = ahocorasick.Automaton()

        with csv_path.open(encoding="utf-8") as f:
            for row in csv.DictReader(f):
                tipo = row.get("tipo", entity_type).strip()
                valor = row.get("valor", "").strip()
                if not valor:
                    continue

                # Normalize
                valor_norm = _RE_SEPARATORS.sub(" ", valor.lower())
                valor_norm = _RE_MULTI_SPACE.sub(" ", valor_norm).strip()
                if len(valor_norm) < _MIN_PATTERN_LENGTH:
                    continue
                if valor_norm in _STOPWORDS:
                    continue

                # Check clinical words — only allow if original
                is_original = row.get("es_original", "0") == "1"
                if valor_norm in _CLINICAL_WORDS and not is_original:
                    continue

                # Enforce word boundary with spaces
                pattern = f" {valor_norm} "
                if pattern not in A:
                    A.add_word(pattern, (tipo, valor))

        A.make_automaton()
        self._automaton = A

    def detect(self, text: str) -> List[Entity]:
        entities = []
        seen: Set[tuple[str, str]] = set()

        if not self._automaton:
            return entities

        # Normalize text
        text_norm = text.lower()
        text_norm = _RE_SEPARATORS.sub(" ", text_norm)
        text_norm = _RE_MULTI_SPACE.sub(" ", text_norm).strip()
        text_norm = f" {text_norm} "

        for end_idx, (entity_type, raw_value) in self._automaton.iter(text_norm):
            # Calculate position in original text
            pattern_len = len(raw_value) if raw_value else 0
            key = (entity_type, raw_value)
            if key not in seen:
                seen.add(key)
                # Estimate start position (normalized space padding offset)
                start = max(0, end_idx - pattern_len - 1)  # -1 for the leading space
                entities.append(Entity(
                    type=entity_type,
                    text=raw_value,
                    start=start,
                    end=end_idx,
                    score=1.0,
                    detector="ahocorasick",
                ))

        return sorted(entities, key=lambda e: e.start)