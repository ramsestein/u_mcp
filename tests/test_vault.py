"""Tests para Vault (SQLite session-scoped)."""

from pathlib import Path
import tempfile

import pytest
from umcp.pipeline.vault.vault import Vault


def test_get_or_create_surrogate_new(vault):
    """Un nuevo valor debe generar un surrogate único."""
    surr = vault.get_or_create_surrogate("PERSON", "Juan Pérez")
    assert surr.startswith("PACIENTE_")
    assert len(surr) > 10


def test_get_or_create_surrogate_idempotent(vault):
    """El mismo valor debe devolver el mismo surrogate."""
    s1 = vault.get_or_create_surrogate("PERSON", "Juan Pérez")
    s2 = vault.get_or_create_surrogate("PERSON", "Juan Pérez")
    assert s1 == s2


def test_get_or_create_surrogate_different_values(vault):
    """Valores distintos deben generar surrogates distintos."""
    s1 = vault.get_or_create_surrogate("PERSON", "Juan")
    s2 = vault.get_or_create_surrogate("PERSON", "María")
    assert s1 != s2


def test_get_or_create_surrogate_different_types(vault):
    """Distintos tipos pueden generar prefijos distintos."""
    s1 = vault.get_or_create_surrogate("PERSON", "Juan")
    s2 = vault.get_or_create_surrogate("NHC", "1234ABCD")
    assert s1.startswith("PACIENTE_")
    assert s2.startswith("NHC_")


def test_get_real_found(vault):
    """get_real debe devolver el valor original."""
    surr = vault.get_or_create_surrogate("PERSON", "Juan Pérez")
    real = vault.get_real(surr)
    assert real == "Juan Pérez"


def test_get_real_not_found(vault):
    """get_real con surrogate inexistente debe devolver None."""
    assert vault.get_real("FAKE_12345678") is None


def test_is_expired_by_idle():
    """Un vault con last_activity viejo debe estar expirado."""
    import time
    p = Path(tempfile.mktemp(suffix=".db"))
    v = Vault("test", db_path=p)
    v._last_activity = time.time() - 10000
    assert v.is_expired(idle_ttl=1, max_ttl=99999)
    v.secure_wipe()


def test_is_expired_by_max():
    """Un vault con created_at viejo debe estar expirado."""
    import time
    p = Path(tempfile.mktemp(suffix=".db"))
    v = Vault("test", db_path=p)
    v._created_at = time.time() - 10000
    assert v.is_expired(idle_ttl=99999, max_ttl=1)
    v.secure_wipe()


def test_is_expired_not():
    """Un vault recién creado no debe estar expirado."""
    p = Path(tempfile.mktemp(suffix=".db"))
    v = Vault("test", db_path=p)
    assert not v.is_expired(idle_ttl=99999, max_ttl=99999)
    v.secure_wipe()


def test_secure_wipe_clears_db(vault):
    """Después de secure_wipe el archivo de base de datos debe eliminarse."""
    import tempfile
    from pathlib import Path
    db_path = Path(tempfile.mktemp(suffix=".db"))
    v = Vault("test-wipe", db_path=db_path)
    v.get_or_create_surrogate("PERSON", "Juan")
    assert db_path.exists()
    v.secure_wipe()
    assert not db_path.exists()


def test_mapping_count(vault):
    """mapping_count debe reflejar el número de mappings."""
    assert vault.mapping_count == 0
    vault.get_or_create_surrogate("PERSON", "Juan")
    assert vault.mapping_count == 1
    vault.get_or_create_surrogate("NHC", "1234")
    assert vault.mapping_count == 2