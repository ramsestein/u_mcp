"""Fixtures compartidas para todos los tests de uMCP."""

import tempfile
from pathlib import Path
from typing import Dict

import pytest
from httpx import ASGITransport, AsyncClient

from umcp.auth.key_manager import key_manager, KeyRole
from umcp.gateway.server import app, vault_manager
from umcp.gateway.config import settings
from umcp.pipeline.vault.vault import Vault
from umcp.pipeline.whitelist import Whitelist
from umcp.pipeline.detectors.regex_detector import RegexDetector
from umcp.pipeline.detectors.ensemble import EnsembleDetector
from umcp.pipeline.detectors.unicode import UnicodeSanitizer
from umcp.tool_loader import tool_registry
from umcp.audit.chain_store import ChainStore
from umcp.audit.hash_chain_provider import HashChainProvider
from umcp.gateway.admin_api import init_admin_api
from umcp.audit.audit_api import init_audit_api


# ── Keys de test ──────────────────────────────────────────────────────────

GATEWAY_KEY = "test-gateway-key-123"
ADMIN_KEY = "test-admin-key-456"
AUDIT_KEY = "test-audit-key-789"


@pytest.fixture(autouse=True)
def setup_test_keys():
    """Registra keys de test e inicializa servicios antes de cada test."""
    old_keys = dict(key_manager._keys)
    key_manager._keys = {}
    key_manager.register_key(GATEWAY_KEY, KeyRole.GATEWAY, "test-gateway")
    key_manager.register_key(ADMIN_KEY, KeyRole.ADMIN, "test-admin")
    key_manager.register_key(AUDIT_KEY, KeyRole.AUDIT, "test-audit")
    
    # Inicializar audit store para tests
    from umcp.gateway.server import chain_store, audit_provider
    init_audit_api(audit_provider, chain_store)
    
    yield
    # Restaurar no es necesario, cada test empieza limpio


@pytest.fixture(autouse=True)
def discover_tools():
    """Descubre herramientas locales antes de los tests de API."""
    tool_registry.discover_tools()
    yield


@pytest.fixture
async def async_client():
    """Cliente HTTP async contra la app FastAPI (sin servidor real)."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture
def temp_db_path() -> Path:
    """Path temporal para bases de datos SQLite."""
    return Path(tempfile.mktemp(suffix=".db"))


@pytest.fixture
def vault(temp_db_path) -> Vault:
    """Vault temporal listo para tests."""
    v = Vault("test-session", db_path=temp_db_path)
    yield v
    try:
        v.secure_wipe()
    except Exception:
        pass


@pytest.fixture
def whitelist() -> Whitelist:
    """Whitelist cargada desde whitelist.txt."""
    return Whitelist()


@pytest.fixture
def regex_detector() -> RegexDetector:
    """Detector de regex."""
    return RegexDetector()


@pytest.fixture
def ensemble_detector() -> EnsembleDetector:
    """Ensemble con regex y unicode (sin BERT ni Aho-Corasick)."""
    return EnsembleDetector(
        regex=RegexDetector(),
        unicode_sanitizer=UnicodeSanitizer(),
    )


@pytest.fixture(autouse=True)
def reset_settings():
    """Resetea settings de privacidad antes de cada test."""
    settings.privacy.k_anonymity_mode = "detect"
    settings.privacy.k_anonymity_threshold = 5
    settings.privacy.l_diversity_threshold = 3