"""Tests para ReIdentificationGuard (k-anonymity / l-diversity)."""

import pytest
from umcp.privacy.reidentification import ReIdentificationGuard, KAnonymityMode
from umcp.gateway.exceptions import ReIdentificationRiskError
from umcp.pipeline.detectors.base import Entity


def make_entities(*types: str):
    """Crea N entidades de tipos dados."""
    return [Entity(t, f"val_{i}", i, i + 1, 1.0, "regex") for i, t in enumerate(types)]


def test_detect_mode_no_raise():
    """Modo detect no debe lanzar excepción."""
    guard = ReIdentificationGuard(mode="detect", k_threshold=5)
    ents = make_entities("PERSON", "NHC")
    report = guard.assess("test", ents)
    assert not report.passed
    assert report.mode == "detect"
    assert not report.blocked


def test_block_mode_raises():
    """Modo block debe lanzar ReIdentificationRiskError si k bajo."""
    guard = ReIdentificationGuard(mode="block", k_threshold=10)
    ents = make_entities("PERSON", "NHC")
    with pytest.raises(ReIdentificationRiskError) as exc:
        guard.assess("test", ents)
    assert "k=" in str(exc.value)


def test_high_k_passes():
    """k alto debe pasar sin warnings de rareza."""
    guard = ReIdentificationGuard(mode="detect", k_threshold=1)
    # 6 entidades, 3 tipos → k=2, l=6, sin tipos únicos
    ents = make_entities("PERSON", "PERSON", "NHC", "NHC", "PHONE", "PHONE")
    report = guard.assess("test", ents)
    assert report.passed


def test_single_entity_warning():
    """Una sola ocurrencia de un tipo debe generar warning."""
    guard = ReIdentificationGuard(mode="detect", k_threshold=1)
    ents = make_entities("PERSON")
    report = guard.assess("test", ents)
    assert len(report.warnings) >= 1


def test_custom_thresholds():
    """Thresholds personalizados: block con k=1, l=1 pasa con entidades repetidas."""
    guard = ReIdentificationGuard(mode="block", k_threshold=1, l_threshold=1)
    # 3 PERSON → k=3//1=3 >= 1, l=3 >= 1, 1 tipo con count=3 → sin warning
    ents = make_entities("PERSON", "PERSON", "PERSON")
    report = guard.assess("test", ents)
    assert report.passed
    assert report.passed


def test_block_mode_detailed_error():
    """El error debe incluir k, l y thresholds."""
    guard = ReIdentificationGuard(mode="block", k_threshold=5, l_threshold=3)
    ents = make_entities("PERSON")
    with pytest.raises(ReIdentificationRiskError) as exc:
        guard.assess("test", ents)
    msg = str(exc.value)
    assert "k=" in msg
    assert "l=" in msg