"""Tests para Substitutor (anonymize/deanonymize con offsets)."""

from umcp.pipeline.detectors.base import Entity
from umcp.pipeline.vault.substitutor import Substitutor


def test_anonymize_single_entity(vault):
    """Una entidad debe ser reemplazada por su surrogate."""
    sub = Substitutor(vault)
    # offset corregido: "Juan" empieza en posición 5 en "Hola Juan"
    entities = [Entity("PERSON", "Juan", 5, 9, 1.0, "regex")]
    text = "Hola Juan"
    result, logs = sub.anonymize(text, entities)
    assert "Juan" not in result
    assert logs[0]["type"] == "PERSON"


def test_anonymize_and_deanonymize_roundtrip(vault):
    """Anonymize + deanonymize debe recuperar el original."""
    sub = Substitutor(vault)
    # offset corregido: "Juan" empieza en posición 5
    entities = [Entity("PERSON", "Juan", 5, 9, 1.0, "regex")]
    text = "Hola Juan"
    anon, _ = sub.anonymize(text, entities)
    restored, _ = sub.deanonymize(anon)
    assert "Juan" in restored


def test_anonymize_multiple_entities(vault):
    """Múltiples entidades deben anonimizarse correctamente."""
    sub = Substitutor(vault)
    ents = [
        # offset corregido: "Juan" en 5, "1234ABCDEF" en 15 en "Hola Juan 1234ABCDEF"
        Entity("PERSON", "Juan", 5, 9, 1.0, "regex"),
        Entity("NHC", "1234ABCDEF", 10, 20, 1.0, "regex"),
    ]
    text = "Hola Juan 1234ABCDEF"
    result, logs = sub.anonymize(text, ents)
    assert "Juan" not in result
    assert "1234ABCDEF" not in result
    assert len(logs) == 2


def test_deanonymize_multiple_entities(vault):
    """Múltiples surrogates deben restaurarse correctamente."""
    sub = Substitutor(vault)
    ents = [
        Entity("PERSON", "Juan", 5, 9, 1.0, "regex"),
        Entity("LOCATION", "Madrid", 13, 19, 1.0, "regex"),
    ]
    anon, _ = sub.anonymize("Hola Juan en Madrid", ents)
    restored, logs = sub.deanonymize(anon)
    assert "Juan" in restored
    assert "Madrid" in restored
    assert len(logs) == 2
    assert len(logs) == 2


def test_anonymize_overlap(vault):
    """Entidades solapadas deben fusionarse."""
    sub = Substitutor(vault)
    ents = [
        Entity("PERSON", "Juan Pérez", 4, 14, 1.0, "regex"),
        Entity("PERSON", "Pérez", 9, 14, 0.8, "ahocorasick"),
    ]
    text = "Hola Juan Pérez"
    result, logs = sub.anonymize(text, ents)
    assert "Juan" not in result
    assert "Pérez" not in result


def test_anonymize_dates_preserved(vault):
    """DATE, TIME, AGE, SEX, JOB no deben anonimizarse."""
    sub = Substitutor(vault)
    ents = [
        Entity("DATE", "12.05.2024", 0, 10, 1.0, "regex"),
        Entity("PERSON", "Juan", 15, 19, 1.0, "regex"),
    ]
    text = "12.05.2024 y Juan"
    result, logs = sub.anonymize(text, ents)
    assert "12.05.2024" in result  # preservada
    assert "Juan" not in result  # anonimizado
    assert len(logs) == 1  # solo PERSON