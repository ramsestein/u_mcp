"""Tests para Whitelist (términos clínicos seguros)."""

from umcp.pipeline.whitelist import Whitelist


def test_is_safe_returns_true(whitelist):
    """Términos clínicos deben ser seguros."""
    assert whitelist.is_safe("diabetes")
    assert whitelist.is_safe("ibuprofeno")
    assert whitelist.is_safe("paciente")
    assert whitelist.is_safe("tratamiento")


def test_is_safe_returns_false(whitelist):
    """Nombres propios no deben ser seguros."""
    assert not whitelist.is_safe("Juan Pérez")
    assert not whitelist.is_safe("María García")
    assert not whitelist.is_safe("Dr. González")


def test_is_safe_case_insensitive(whitelist):
    """La comprobación debe ser case-insensitive."""
    assert whitelist.is_safe("DIABETES")
    assert whitelist.is_safe("Ibuprofeno")


def test_is_safe_multiword(whitelist):
    """Términos multi-palabra con una palabra en whitelist."""
    assert whitelist.is_safe("paciente crítico")
    assert whitelist.is_safe("diabetes mellitus tipo 2")


def test_add_term(whitelist):
    """Añadir un término dinámicamente."""
    assert not whitelist.is_safe("mi_termino")
    whitelist.add_term("mi_termino")
    assert whitelist.is_safe("mi_termino")


def test_custom_terms():
    """Pasar términos custom en el constructor."""
    w = Whitelist(terms={"term1", "term2"})
    assert w.is_safe("term1")
    assert not w.is_safe("otro")


def test_contains(whitelist):
    """__contains__ debe funcionar igual que is_safe."""
    assert "diabetes" in whitelist
    assert "Juan Pérez" not in whitelist