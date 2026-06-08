"""Ensemble detector — fuses results from all detectors."""

from typing import List, Optional
from umcp.pipeline.detectors.base import Entity
from umcp.pipeline.detectors.unicode import UnicodeSanitizer
from umcp.pipeline.detectors.regex_detector import RegexDetector
from umcp.pipeline.detectors.aho_corasick import AhoCorasickDetector
from umcp.pipeline.detectors.bert_detector import BERTDetector


# Detector priority for label conflicts (higher = wins)
_DETECTOR_PRIORITY = {
    "regex": 4,
    "bert_carmen": 3,
    "bert_meddocan": 3,
    "ahocorasick": 2,
}

# Labels that are preserved (not anonymized)
_PRESERVED_LABELS = {"DATE", "TIME", "AGE", "SEX", "JOB"}


class EnsembleDetector:
    """Runs all detectors and merges results."""

    def __init__(
        self,
        regex: Optional[RegexDetector] = None,
        aho_corasick: Optional[AhoCorasickDetector] = None,
        bert: Optional[BERTDetector] = None,
        unicode_sanitizer: Optional[UnicodeSanitizer] = None,
    ):
        self.regex = regex or RegexDetector()
        self.aho_corasick = aho_corasick
        self.bert = bert
        self.unicode_sanitizer = unicode_sanitizer or UnicodeSanitizer()

    def detect(self, text: str) -> List[Entity]:
        """Run all detectors and merge results."""

        # 1. Unicode sanitization (always first)
        unicode_ents = self.unicode_sanitizer.detect(text)

        # 2. Run all detectors
        all_entities: List[Entity] = []

        all_entities.extend(self.regex.detect(text))

        if self.aho_corasick:
            all_entities.extend(self.aho_corasick.detect(text))

        if self.bert:
            all_entities.extend(self.bert.detect(text))

        # 3. Filter preserved labels (DATE, TIME, AGE, SEX, JOB)
        #    They are detected but NOT anonymized
        preserved = [e for e in all_entities if e.type in _PRESERVED_LABELS]
        to_anonymize = [e for e in all_entities if e.type not in _PRESERVED_LABELS]

        # 4. Merge overlapping entities
        merged = self._merge(to_anonymize)

        # 5. Return merged + unicode + preserved (preserved go as-is, marked as `anonymize: false`)
        result = merged + unicode_ents + preserved
        for e in result:
            if e.type in _PRESERVED_LABELS:
                e.score = 0.0  # Mark as "do not anonymize"

        return sorted(result, key=lambda e: e.start)

    def detect_and_sanitize(self, text: str) -> tuple[str, List[Entity]]:
        """Detect entities and sanitize Unicode in one pass."""
        clean_text = self.unicode_sanitizer.sanitize(text)
        entities = self.detect(clean_text)
        return clean_text, entities

    def _merge(self, entities: List[Entity]) -> List[Entity]:
        """Merge overlapping/adjacent entities."""
        if not entities:
            return []

        sorted_ents = sorted(entities, key=lambda e: (e.start, -e.end))
        merged: List[Entity] = []
        current = sorted_ents[0]

        for next_ent in sorted_ents[1:]:
            # Overlap or adjacent (distance ≤ 1)
            if next_ent.start <= current.end + 1:
                if next_ent.end > current.end:
                    current.end = next_ent.end
                    current.text = ""  # Will recompute
                # Label priority: higher detector priority wins
                current_prio = _DETECTOR_PRIORITY.get(current.detector, 0)
                next_prio = _DETECTOR_PRIORITY.get(next_ent.detector, 0)
                if next_prio > current_prio:
                    current.type = next_ent.type
                    current.detector = next_ent.detector
                    current.score = max(current.score, next_ent.score)
            else:
                merged.append(current)
                current = next_ent

        merged.append(current)
        return merged