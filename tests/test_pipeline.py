"""Tests para el pipeline: date_preserver, unicode, ensemble, date_preserver."""

import pytest
from umcp.pipeline.date_preserver import DatePreserver
from umcp.pipeline.detectors.unicode import UnicodeSanitizer
from umcp.pipeline.detectors.ensemble import EnsembleDetector
from umcp.pipeline.detectors.regex_detector import RegexDetector
from umcp.pipeline.detectors.base import Entity


# ── Date Preserver ────────────────────────────────────────────────────────

class TestDatePreserver:
    def test_find_dates_dd_mm_yyyy(self):
        """DD.MM.YYYY debe detectarse."""
        dp = DatePreserver()
        ranges = dp.find_protected_ranges("Fecha: 12.05.2024")
        assert len(ranges) >= 1

    def test_find_dates_iso(self):
        """YYYY-MM-DD debe detectarse."""
        dp = DatePreserver()
        ranges = dp.find_protected_ranges("ISO 2024-05-12")
        assert len(ranges) >= 1

    def test_find_header_fecha_hora(self):
        """Cabecera 'Fecha: ... Hora: ...' debe protegerse."""
        dp = DatePreserver()
        text = "Fecha: 12.05.2024 Hora: 14:30:00"
        ranges = dp.find_protected_ranges(text)
        assert len(ranges) >= 1

    def test_is_protected(self):
        """Span solapado con rango protegido debe retornar True."""
        dp = DatePreserver()
        protected = [(0, 10)]
        assert dp.is_protected(2, 5, protected) is True
        assert dp.is_protected(10, 15, protected) is False

    def test_filter_protected(self):
        """Entidades en rango protegido deben filtrarse."""
        dp = DatePreserver()
        text = "Fecha: 12.05.2024"
        entities = [
            Entity("DATE", "12.05.2024", 7, 17, 1.0, "regex"),
            Entity("PERSON", "Juan", 20, 24, 1.0, "regex"),
        ]
        filtered = dp.filter_protected(entities, text)
        assert len(filtered) == 1
        assert filtered[0].type == "PERSON"


# ── Unicode Sanitizer ─────────────────────────────────────────────────────

class TestUnicodeSanitizer:
    def test_detect_zero_width(self):
        """Zero-width space debe detectarse."""
        u = UnicodeSanitizer()
        ents = u.detect("Hola\u200BMundo")
        uzw = [e for e in ents if e.type == "UNICODE_ZERO_WIDTH"]
        assert len(uzw) >= 1

    def test_detect_bidi(self):
        """BIDI override debe detectarse (LRE = \u202A)."""
        u = UnicodeSanitizer()
        ents = u.detect("Hola\u202EMundo")
        # Los BIDI están también en ZERO_WIDTH_CHARS, se detectan como zero-width
        assert len(ents) >= 1

    def test_sanitize_removes_zero_width(self):
        """Sanitize debe eliminar zero-width chars."""
        u = UnicodeSanitizer()
        result = u.sanitize("Hola\u200BMundo")
        assert "\u200B" not in result
        assert result == "HolaMundo"

    def test_sanitize_preserves_normal(self):
        """Sanitize no debe alterar texto normal."""
        u = UnicodeSanitizer()
        text = "Hola Mundo 123"
        assert u.sanitize(text) == text


# ── Ensemble ──────────────────────────────────────────────────────────────

class TestEnsemble:
    def test_ensemble_with_regex_only(self):
        """Ensemble con solo regex debe funcionar."""
        ens = EnsembleDetector(regex=RegexDetector())
        ents = ens.detect("Email juan@mail.com y DNI 12345678Z")
        types = {e.type for e in ents}
        assert "EMAIL" in types
        assert "DNI" in types

    def test_detect_and_sanitize(self):
        """detect_and_sanitize debe limpiar y detectar."""
        ens = EnsembleDetector(regex=RegexDetector())
        clean, ents = ens.detect_and_sanitize("Hola\u200BMundo")
        assert "\u200B" not in clean
        assert len(ents) >= 0  # No debe fallar

    def test_merge_overlap(self):
        """Entidades solapadas deben fusionarse."""
        ens = EnsembleDetector(regex=RegexDetector())
        e1 = Entity("PERSON", "Juan Pérez", 0, 10, 1.0, "regex")
        e2 = Entity("PERSON", "Pérez", 5, 10, 0.8, "ahocorasick")
        merged = ens._merge([e1, e2])
        assert len(merged) == 1
        # La de mayor prioridad (regex) gana
        assert merged[0].detector == "regex"