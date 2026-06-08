"""Tests para auditoría: hash chain, cross_validator, audit_api."""

import pytest
from pathlib import Path
import tempfile

from umcp.audit.models import AuditEvent
from umcp.audit.chain_store import ChainStore
from umcp.audit.hash_chain_provider import HashChainProvider, GENESIS_HASH
from umcp.audit.cross_validator import CrossValidator


@pytest.fixture
def chain_store():
    """Chain store temporal."""
    p = Path(tempfile.mktemp(suffix=".db"))
    cs = ChainStore(p)
    yield cs
    cs.close()
    if p.exists():
        p.unlink()


@pytest.fixture
def hash_provider(chain_store):
    """Hash chain provider con secret de test."""
    return HashChainProvider(store=chain_store, gateway_secret="test-secret")


# ── AuditEvent model ─────────────────────────────────────────────────────

class TestAuditEvent:
    def test_create_event(self):
        """Crear evento debe generar uuid y timestamp."""
        e = AuditEvent(event_type="AUTH", actor_id="test", action="requested", result="success")
        assert e.event_id is not None
        assert e.event_type == "AUTH"
        assert e.result == "success"

    def test_content_string(self):
        """Content string debe incluir todos los campos."""
        e = AuditEvent(event_type="TEST", actor_id="user", action="exec", result="ok")
        content = e.get_content_string()
        assert "TEST" in content
        assert "user" in content


# ── Chain Store ──────────────────────────────────────────────────────────

class TestChainStore:
    def test_append_and_get(self, chain_store):
        """Append y get de evento."""
        e = AuditEvent(event_type="AUTH", actor_id="tester", action="login", result="ok")
        chain_store.append(e)
        retrieved = chain_store.get_event(e.event_id)
        assert retrieved is not None
        assert retrieved.event_type == "AUTH"

    def test_get_last_event(self, chain_store):
        """get_last_event debe devolver el último."""
        import hashlib
        e1 = AuditEvent(event_type="AUTH", actor_id="u1", action="login", result="ok")
        e2 = AuditEvent(event_type="TOOL_CALL", actor_id="u2", action="exec", result="ok")
        # Asignar hashes únicos para evitar UNIQUE constraint
        e1.event_hash = hashlib.sha256(e1.get_content_string().encode()).hexdigest()
        e2.event_hash = hashlib.sha256(e2.get_content_string().encode()).hexdigest()
        chain_store.append(e1)
        chain_store.append(e2)
        last = chain_store.get_last_event()
        assert last.event_type == "TOOL_CALL"

    def test_get_chain_length(self, chain_store):
        """Chain length debe contar eventos."""
        import hashlib
        assert chain_store.get_chain_length() == 0
        e = AuditEvent(event_type="T1", actor_id="u", action="a", result="ok")
        e.event_hash = hashlib.sha256(e.get_content_string().encode()).hexdigest()
        chain_store.append(e)
        assert chain_store.get_chain_length() == 1

    def test_get_all_events(self, chain_store):
        """get_all_events debe devolver todos."""
        import hashlib
        e1 = AuditEvent(event_type="T1", actor_id="u", action="a", result="ok")
        e2 = AuditEvent(event_type="T2", actor_id="u", action="a", result="ok")
        e1.event_hash = hashlib.sha256(e1.get_content_string().encode()).hexdigest()
        e2.event_hash = hashlib.sha256(e2.get_content_string().encode()).hexdigest()
        chain_store.append(e1)
        chain_store.append(e2)
        all_e = chain_store.get_all_events()
        assert len(all_e) == 2


# ── Hash Chain Provider ──────────────────────────────────────────────────

class TestHashChainProvider:
    def test_record_event(self, hash_provider):
        """Record debe crear evento con hash y firma."""
        e = hash_provider.record_event("AUTH", "user1", "login", "success")
        assert e.event_hash is not None
        assert e.gateway_signature is not None
        assert e.previous_hash == GENESIS_HASH

    def test_chain_linking(self, hash_provider):
        """Dos eventos deben estar enlazados."""
        e1 = hash_provider.record_event("AUTH", "u1", "login", "ok")
        e2 = hash_provider.record_event("TOOL", "u1", "exec", "ok")
        assert e2.previous_hash == e1.event_hash

    def test_validate_chain_valid(self, hash_provider):
        """Cadena válida debe validarse correctamente."""
        hash_provider.record_event("AUTH", "u1", "login", "ok")
        hash_provider.record_event("TOOL", "u1", "exec", "ok")
        valid, count, errors = hash_provider.validate_chain()
        assert valid is True
        assert count == 2
        assert errors == 0


# ── Cross Validator ──────────────────────────────────────────────────────

class TestCrossValidator:
    def test_sign_and_verify(self):
        """Firma y verificación deben coincidir."""
        event = AuditEvent(event_type="AUTH", actor_id="u", action="login", result="ok")
        event.event_hash = "a1b2c3d4"
        sig = CrossValidator.sign_event(event.event_hash, "client-secret")
        event.client_signature = sig
        assert CrossValidator.verify_client_signature(event, "client-secret") is True

    def test_wrong_secret_fails(self):
        """Secret incorrecto debe fallar verificación."""
        event = AuditEvent(event_type="AUTH", actor_id="u", action="login", result="ok")
        event.event_hash = "a1b2c3d4"
        sig = CrossValidator.sign_event(event.event_hash, "real-secret")
        event.client_signature = sig
        assert CrossValidator.verify_client_signature(event, "wrong-secret") is False

    def test_verify_server_response(self):
        """Hash de respuesta debe verificarse."""
        event = AuditEvent(event_type="TOOL", actor_id="u", action="exec", result="ok")
        import hashlib
        response = '{"data": "test"}'
        event.server_response_hash = hashlib.sha256(response.encode()).hexdigest()
        assert CrossValidator.verify_server_response(event, response) is True
        assert CrossValidator.verify_server_response(event, '{"data": "other"}') is False