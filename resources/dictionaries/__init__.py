"""
dictionary_loader — carga diccionarios editables desde resources/dictionaries/.

Todas las funciones intentan cargar desde archivo. Si el archivo no existe,
devuelven los valores por defecto hardcodeados (nunca fallan).
Los archivos se pueden modificar SIN TOCAR CÓDIGO PYTHON.
"""

import csv
import logging
from pathlib import Path
from typing import List, Optional, Set, Tuple

logger = logging.getLogger(__name__)

DICT_DIR = Path(__file__).parent


# ── Whitelist ─────────────────────────────────────────────────────────────

_DEFAULT_WHITELIST: Set[str] = {
    "trastorno", "síndrome", "enfermedad", "patología", "condición",
    "diabetes", "mellitus", "insuficiencia", "renal", "cardíaca",
    "respiratoria", "hepática", "aguda", "crónica", "severa", "leve",
    "moderada", "benigna", "maligna", "hipertensión", "arterial",
    "diabetes tipo 2", "diabetes tipo 1", "asma", "bronquial",
    "artrosis", "cáncer", "tumor", "neumonía", "infección", "fractura",
    "tratamiento", "dosis", "pauta", "comprimido", "pastilla",
    "jarabe", "solución", "inyección", "vía oral", "vía intravenosa",
    "vía intramuscular", "vía subcutánea", "posología",
    "abilify", "adiro", "aspirina", "atorvastatina", "bisoprolol",
    "captopril", "depakine", "diazepam", "enalapril", "fluoxetina",
    "furosemida", "ibuprofeno", "insulina", "lorazepam", "metformina",
    "metamizol", "nolotil", "omeprazol", "paracetamol", "plavix",
    "prednisona", "quetiapina", "salbutamol", "sintrom", "simvastatina",
    "trankimazin", "ventolin", "zolpidem", "espironolactona",
    "budesonida", "sitagliptina", "hidroclorotiazida",
    "paciente", "usuario", "historia", "clínica", "alta", "ingreso",
    "consulta", "visita", "diagnóstico", "evolución", "plan",
    "antecedentes", "personales", "familiares", "quirúrgicos",
    "patológicos", "psiquiátricos", "alergias", "hábitos",
    "exploración", "física", "constantes", "vitales",
    "tensión", "frecuencia", "temperatura", "saturación", "oxígeno",
    "peso", "talla", "índice", "masa", "corporal",
    "fármaco", "medicamento", "principio activo",
    "hígado", "higado", "nódulo", "nodulo", "páncreas", "pancreas",
    "cerebro", "riñón", "riñones", "rinon", "pulmón", "pulmon",
    "estómago", "estomago", "intestino", "colon", "vesícula",
    "vesicula", "tiroides", "próstata", "prostata",
    "cabeza", "brazo", "pierna", "mano", "pie", "espalda",
    "hta", "dm", "mri", "tc", "tac", "ecg", "eeg", "erg",
    "emg", "bg", "rxt", "tto", "fco", "cmp", "amp", "vial",
    "ing", "cons", "quir",
}


def load_whitelist(path: Optional[Path] = None) -> Set[str]:
    """
    Carga la whitelist desde un archivo de texto.
    Formato: un término por línea. # para comentarios. Case-insensitive.
    Si el archivo no existe, devuelve los valores por defecto.
    """
    path = path or (DICT_DIR / "whitelist.txt")
    if not path.exists():
        logger.info(f"Whitelist file not found: {path}, using defaults")
        return _DEFAULT_WHITELIST

    terms: Set[str] = set()
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            terms.add(line.lower())

    if not terms:
        logger.warning(f"Whitelist file empty: {path}, using defaults")
        return _DEFAULT_WHITELIST

    logger.info(f"Loaded {len(terms)} whitelist terms from {path}")
    return terms


# ── Stopwords ─────────────────────────────────────────────────────────────

_DEFAULT_STOPWORDS: Set[str] = {
    "a", "ante", "bajo", "con", "contra", "de", "del", "desde", "durante",
    "en", "entre", "hacia", "hasta", "para", "por", "según", "sin", "sobre",
    "tras", "y", "e", "ni", "o", "u", "mas", "más", "pero", "sino",
    "aunque", "como", "conforme", "cuando", "donde", "mientras", "porque",
    "pues", "que", "salvo", "si", "el", "la", "las", "lo", "los", "un",
    "una", "unos", "unas", "este", "esta", "esto", "ese", "esa", "eso",
    "todo", "toda", "cada", "otro", "otra", "algún", "alguna",
    "ningún", "ninguna", "mucho", "poco", "es", "ha", "le", "se", "su",
    # Catalan
    "amb", "cap", "contra", "des", "durant", "entre", "fins", "per",
    "sense", "sota", "però", "doncs", "mentre", "perquè", "quan",
    "els", "les", "uns", "unes", "aquest", "aquesta", "aquell",
    "meu", "teu", "seu", "nostre", "tot", "poc", "molt", "tant",
    "altre", "altra", "algun", "alguna", "qualsevol",
}


def load_stopwords(path: Optional[Path] = None) -> Set[str]:
    """Carga stopwords desde archivo. Un término por línea."""
    path = path or (DICT_DIR / "stopwords.txt")
    if not path.exists():
        return _DEFAULT_STOPWORDS

    words: Set[str] = set()
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            words.add(line.lower())

    return words or _DEFAULT_STOPWORDS


# ── Clinical Words ───────────────────────────────────────────────────────

_DEFAULT_CLINICAL_WORDS: Set[str] = {
    "agudo", "aguda", "dolor", "dolores", "dolors", "dias", "dia",
    "nora", "pero", "post", "aula", "buen", "toma", "min",
    "oral", "orales", "años", "año", "vida", "vive", "alarma",
    "abd", "rota", "dura", "media", "cara", "caso", "gota",
    "coma", "tto", "ayer", "venosa", "figura", "menos", "gas",
    "agua", "herida", "vaso", "cosa", "roce", "grado", "era",
    "coca", "mama", "banco", "navajas",
}


def load_clinical_words(path: Optional[Path] = None) -> Set[str]:
    """Carga palabras clínicas (falsos positivos) desde archivo."""
    path = path or (DICT_DIR / "clinical_words.txt")
    if not path.exists():
        return _DEFAULT_CLINICAL_WORDS

    words: Set[str] = set()
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            words.add(line.lower())

    return words or _DEFAULT_CLINICAL_WORDS


# ── Entidades CSV (para Aho-Corasick) ────────────────────────────────────

def load_entities_csv(path: Optional[Path] = None) -> List[Tuple[str, str, bool]]:
    """
    Carga diccionario de entidades desde CSV.
    Columnas: tipo, valor, es_original
    Devuelve lista de (tipo, valor, es_original).
    Si el archivo no existe, devuelve lista vacía.
    """
    path = path or (DICT_DIR / "entidades.csv")
    if not path.exists():
        logger.info(f"Entities CSV not found: {path}")
        return []

    entities: List[Tuple[str, str, bool]] = []
    with open(path, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            tipo = row.get("tipo", "PERSON").strip()
            valor = row.get("valor", "").strip()
            es_original = row.get("es_original", "1").strip() == "1"
            if valor:
                entities.append((tipo, valor, es_original))

    logger.info(f"Loaded {len(entities)} entities from {path}")
    return entities