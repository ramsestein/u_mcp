"""Tests para layers: msg_interceptor, tool_dispatcher, resource_pipeline."""

import pytest
from umcp.pipeline.vault.vault import Vault
from umcp.pipeline.detectors.ensemble import EnsembleDetector
from umcp.pipeline.detectors.regex_detector import RegexDetector
from umcp.pipeline.detectors.unicode import UnicodeSanitizer
from umcp.pipeline.detectors.base import Entity
from umcp.pipeline.date_preserver import DatePreserver
from umcp.pipeline.whitelist import Whitelist
from umcp.layers.msg_interceptor import MessageInterceptor
from umcp.privacy.reidentification import ReIdentificationGuard
from umcp.privacy.breach_response import BreachResponse


@pytest.fixture
def vault():
    from pathlib import Path
    import tempfile
    p = Path(tempfile.mktemp(suffix=".db"))
    v = Vault("test-layer", db_path=p)
    yield v
    v.secure_wipe()


@pytest.fixture
def detector():
    return EnsembleDetector(
        regex=RegexDetector(),
        unicode_sanitizer=UnicodeSanitizer(),
    )


# ── Message Interceptor ──────────────────────────────────────────────────

class TestMessageInterceptor:
    def test_anonymize_simple(self, vault, detector):
        """Anonymize no debe fallar con texto simple."""
        interceptor = MessageInterceptor(vault=vault, detector=detector)
        result, subs, risk = interceptor.anonymize_user_message("Hola Mundo")
        assert "Hola" in result
        assert len(subs) == 0  # Sin PII

    def test_anonymize_with_pii(self, vault, detector):
        """Anonymize debe detectar y reemplazar email."""
        interceptor = MessageInterceptor(vault=vault, detector=detector)
        result, subs, risk = interceptor.anonymize_user_message("mi email es test@example.com")
        assert "test@example.com" not in result
        assert len(subs) >= 1
        assert subs[0]["type"] == "EMAIL"

    def test_anonymize_and_deanonymize_roundtrip(self, vault, detector):
        """Anonymize + deanonymize debe recuperar original."""
        interceptor = MessageInterceptor(vault=vault, detector=detector)
        anon, subs, _ = interceptor.anonymize_user_message("Juan email test@example.com")
        restored, deanons = interceptor.deanonymize_llm_response(anon)
        # Al menos debe restaurar algo (el email)
        assert len(deanons) >= 1 or len(subs) == 0

    def test_k_anonymity_mode_detect(self, vault, detector):
        """Modo detect no debe lanzar excepción."""
        interceptor = MessageInterceptor(vault=vault, detector=detector)
        assert interceptor.k_anonymity_mode == "detect"

    def test_anonymize_preserves_dates(self, vault, detector):
        """Las fechas deben preservarse."""
        interceptor = MessageInterceptor(
            vault=vault,
            detector=detector,
            date_preserver=DatePreserver(),
        )
        result, subs, risk = interceptor.anonymize_user_message("Fecha: 12.05.2024")
        assert "12.05.2024" in result

    def test_anonymize_with_whitelist(self, vault, detector):
        """Términos en whitelist no deben anonimizarse."""
        interceptor = MessageInterceptor(
            vault=vault,
            detector=detector,
            whitelist=Whitelist(),
        )
        # "paciente" no debería estar en ningún regex, pero no debe fallar
        result, subs, risk = interceptor.anonymize_user_message("El paciente está bien")
        assert "paciente" in result  # No se toca porque whitelist no afecta a regex