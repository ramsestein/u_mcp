"""Abstract base for entity detectors."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Entity:
    """A detected entity in text."""
    type: str              # PERSON, LOCATION, NHC, PHONE, EMAIL, GENERICA, DATE, etc.
    text: str
    start: int
    end: int
    score: float
    detector: str          # "regex", "ahocorasick", "bert_carmen", "bert_meddocan"

    def to_dict(self) -> dict:
        return {
            "type": self.type,
            "text": self.text,
            "start": self.start,
            "end": self.end,
            "score": self.score,
            "detector": self.detector,
        }


class EntityDetector(ABC):
    """Abstract detector. Each detector implements detect()."""

    @abstractmethod
    def detect(self, text: str) -> List[Entity]:
        """Detect entities in the given text."""
        ...