"""Whitelist — safe clinical terms that should NOT be anonymized.

Adapted from carmina_3_suite (lista_blanca.txt) and pseudo_datanex_notes.
"""

from typing import Set
from pathlib import Path


# ── Cargar whitelist desde archivo externo (con fallback) ────────────────
_DICT_DIR = (Path(__file__).parent.parent.parent.parent / "resources" / "dictionaries").resolve()


def _load_whitelist_from_file() -> Set[str]:
    """Load whitelist from whitelist.txt. Returns empty set if not found."""
    path = _DICT_DIR / "whitelist.txt"
    if not path.exists():
        return set()
    terms: Set[str] = set()
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                terms.add(line.lower())
    return terms


class Whitelist:
    """Manages a set of terms that are safe (never anonymized).

    Carga la whitelist desde resources/dictionaries/whitelist.txt.
    Si el archivo no existe, usa valores por defecto hardcodeados.
    Para modificar: edita el archivo, no el código.
    """

    def __init__(self, terms: Set[str] = None):
        loaded = _load_whitelist_from_file()
        self._terms: Set[str] = terms or loaded or self._default_terms()

    @staticmethod
    def _default_terms() -> Set[str]:
        """Valores por defecto (se usan si no hay archivo whitelist.txt)."""
        return {
            "trastorno", "síndrome", "enfermedad", "diabetes", "mellitus",
            "insuficiencia", "renal", "cardíaca", "respiratoria",
            "tratamiento", "dosis", "pauta", "comprimido", "pastilla",
            "paciente", "usuario", "historia", "clínica", "alta", "ingreso",
            "consulta", "visita", "diagnóstico", "evolución", "plan",
            "antecedentes", "personales", "familiares",
            "exploración", "física", "constantes", "vitales",
            "frecuencia", "temperatura", "saturación", "oxígeno",
            "peso", "talla", "índice", "masa", "corporal",
            "abilify", "adiro", "aspirina", "atorvastatina", "bisoprolol",
            "captopril", "depakine", "diazepam", "enalapril", "fluoxetina",
            "furosemida", "ibuprofeno", "insulina", "lorazepam", "metformina",
            "metamizol", "nolotil", "omeprazol", "paracetamol", "plavix",
            "prednisona", "quetiapina", "salbutamol", "sintrom", "simvastatina",
            "trankimazin", "ventolin", "zolpidem",
            "hígado", "higado", "nódulo", "nodulo", "páncreas", "pancreas",
            "cerebro", "riñón", "riñones", "rinon", "pulmón", "pulmon",
            "estómago", "estomago", "intestino", "colon", "vesícula",
            "vesicula", "tiroides", "próstata", "prostata",
            "hta", "dm", "mri", "tc", "tac", "ecg", "eeg", "erg",
            "emg", "bg", "rxt", "tto", "fco", "cmp", "amp", "vial",
        }

    def add_term(self, term: str) -> None:
        self._terms.add(term.lower())

    def add_terms(self, terms: Set[str]) -> None:
        self._terms.update(t.lower() for t in terms)

    def is_safe(self, text: str) -> bool:
        """Check if a detected entity text is a safe term."""
        lower = text.lower().strip()
        if lower in self._terms:
            return True
        words = lower.split()
        if len(words) > 1 and any(w.strip(".,;") in self._terms for w in words):
            return True
        return False

    def __contains__(self, text: str) -> bool:
        return self.is_safe(text)