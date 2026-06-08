"""BERT NER entity detector — uses carmen-anon and meddocan models.

Adapted from carmina_3_suite (step3_bert_marking.py).
Supports chunking for long texts, GPU acceleration, and label mapping.
"""

import re
import logging
from pathlib import Path
from typing import List, Optional
from umcp.pipeline.detectors.base import Entity, EntityDetector

logger = logging.getLogger(__name__)


# Label mapping: CARMEN-ANON / MEDDOCAN → simplified types
_LABEL_MAP = {
    "FECHAS": "DATE",
    "FECHA": "DATE",
    "NOMBRE_SUJETO_ASISTENCIA": "PERSON",
    "NOMBRE_PERSONAL_ASISTENCIA": "PERSON",
    "NOMBRE_PERSONAL_SANITARIO": "PERSON",
    "FAMILIARES_SUJETO_ASISTENCIA": "PERSON",
    "CALLE": "LOCATION",
    "TERRITORIO": "LOCATION",
    "CENTRO_SALUD": "LOCATION",
    "PAIS": "LOCATION",
    "NUMERO_TELEFONO": "PHONE",
    "TELEFONO": "PHONE",
    "EDAD_SUJETO_ASISTENCIA": "AGE",
    "SEXO_SUJETO_ASISTENCIA": "SEX",
    "NUMERO_FAX": "PHONE",
    "URL_WEB": "URL",
    "CORREO_ELECTRONICO": "EMAIL",
    "IDENTIF_BIOMETRICOS": "ID",
    "IDENTIF_DISPOSITIVOS": "ID",
    "IDENTIF_N_HISTORIA_CLINICA": "NHC",
    "IDENTIF_N_SEGURIDAD_SOCIAL": "NASS",
    "IDENTIF_TITULACION_CERTIFICACION": "ID",
    "PROFESION": "JOB",
}

# Labels that should NOT be anonymized (preserved)
_PRESERVED_LABELS = {"DATE", "TIME", "AGE", "SEX", "JOB"}


def _map_label(bert_label: str) -> str:
    """Map a BERT label to simplified type."""
    base = bert_label.split("-")[-1]
    return _LABEL_MAP.get(base, base)


# ── Cargar whitelist desde archivo externo ────────────────────────────────
_DICT_DIR = (Path(__file__).parent.parent.parent.parent.parent / "resources" / "dictionaries").resolve()


def _load_whitelist() -> set:
    """Load whitelist from whitelist.txt."""
    path = _DICT_DIR / "whitelist.txt"
    if not path.exists():
        return set()
    terms = set()
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                terms.add(line.lower())
    return terms


class BERTDetector(EntityDetector):
    """BERT NER detector using local models.

    La whitelist se carga desde resources/dictionaries/whitelist.txt
    (compartida con el resto del sistema).
    """

    def __init__(
        self,
        models_dir: Path,
        model_names: Optional[List[str]] = None,
        threshold: float = 0.3,
        chunk_size: int = 2000,
        batch_size: int = 8,
        whitelist: Optional[set] = None,
    ):
        self.models_dir = models_dir
        self.model_names = model_names or ["bsc-bio-ehr-es-carmen-anon", "bsc-bio-ehr-es-meddocan"]
        self.threshold = threshold
        self.chunk_size = chunk_size
        self.batch_size = batch_size
        self.whitelist = whitelist or _load_whitelist()
        self._pipelines = {}

    def _load_pipelines(self):
        """Lazy-load BERT pipelines."""
        if self._pipelines:
            return

        try:
            import torch
            from transformers import (
                AutoTokenizer,
                AutoModelForTokenClassification,
                pipeline,
            )
        except ImportError:
            logger.warning("transformers/torch not available, BERT detector disabled")
            return

        for name in self.model_names:
            model_path = self.models_dir / name
            if not model_path.exists():
                logger.warning(f"BERT model not found: {model_path}")
                continue

            try:
                logger.info(f"Loading BERT model: {name}...")
                abs_path = str(model_path.resolve())
                tokenizer = AutoTokenizer.from_pretrained(abs_path, local_files_only=True)
                model = AutoModelForTokenClassification.from_pretrained(
                    abs_path, local_files_only=True
                )
                device = 0 if torch.cuda.is_available() else -1
                self._pipelines[name] = pipeline(
                    "ner",
                    model=model,
                    tokenizer=tokenizer,
                    device=device,
                    aggregation_strategy="simple",
                )
                logger.info(f"BERT model {name} loaded (device: {'GPU' if device == 0 else 'CPU'})")
            except Exception as e:
                logger.error(f"Failed to load BERT model {name}: {e}")

    def is_false_positive(self, text: str) -> bool:
        """Check if a detected entity is a false positive (whitelisted term)."""
        lower = text.lower().strip()
        if lower in self.whitelist:
            return True
        words = lower.split()
        if any(w.strip(".,;") in self.whitelist for w in words):
            return True
        return False

    def detect(self, text: str) -> List[Entity]:
        self._load_pipelines()
        if not self._pipelines:
            return []

        entities = []

        # Chunk text
        chunks = [text[i:i + self.chunk_size] for i in range(0, len(text), self.chunk_size)]
        offsets = list(range(0, len(text), self.chunk_size))

        for model_name, nlp in self._pipelines.items():
            try:
                batch_results = nlp(chunks, batch_size=self.batch_size)
                for i, chunk_ents in enumerate(batch_results):
                    off = offsets[i]
                    for ent in chunk_ents:
                        if ent["score"] < self.threshold:
                            continue
                        entity_text = ent["word"].strip()
                        if self.is_false_positive(entity_text):
                            continue
                        label = _map_label(ent["entity_group"])
                        entities.append(Entity(
                            type=label,
                            text=ent["word"],
                            start=ent["start"] + off,
                            end=ent["end"] + off,
                            score=float(ent["score"]),
                            detector=model_name,
                        ))
            except Exception as e:
                logger.warning(f"BERT {model_name} inference error: {e}")

        return sorted(entities, key=lambda e: e.start)