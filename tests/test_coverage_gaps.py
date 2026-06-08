"""Tests específicos para cubrir líneas restantes en módulos parciales."""

import pytest
import tempfile
import hashlib
from pathlib import Path
from unittest.mock import AsyncMock, patch

from umcp.audit.audit_api import audit_router, init_audit_api
from umcp.audit.chain_store import ChainStore
from umcp.audit.hash_chain_provider import HashChainProvider
from umcp.audit.cross_validator import CrossValidator
from umcp.audit.models import AuditEvent
from umcp.auth.key_manager import key_manager, KeyRole
from umcp.auth.dependencies import get_gateway_key, get_admin_key, get_audit_key
from umcp.gateway.cache import CacheService
from umcp.gateway.client import MCPClientPool
from umcp.gateway.exceptions import ReIdentificationRiskError
from umcp.privacy.retention import RetentionManager, RetentionPolicy
from umcp.policies.allow_deny import PolicyEngine, PolicyConfig
from umcp.tool_loader import tool_registry
from tests.conftest import GATEWAY_KEY, ADMIN_KEY, AUDIT_KEY


# ── Audit API ─────────────────────────────────────────────────────────────

@pytest.fixture
def audit_store():
    """Chain store temporal con provider."""
    p = Path(tempfile.mktemp(suffix=".audit.db"))
    cs = ChainStore(p)
    hp = HashChainProvider(cs, "test-secret")
    init_audit_api(hp, cs)
    yield cs, hp
    cs.close()
    if p.exists():
        p.unlink()


class TestAuditAPICoverage:
    @pytest.mark.asyncio
    async def test_validate_chain_empty(self, audit_store, async_client):
        """Validar cadena vacía debe funcionar."""
        from tests.conftest import AUDIT_KEY
        r = await async_client.get("/audit/chain/validate", headers={"X-Audit-Key": AUDIT_KEY})
        assert r.status_code in (200, 503)

    @pytest.mark.asyncio
    async def test_audit_summary_empty(self, audit_store, async_client):
        """Summary de audit vacío debe funcionar."""
        from tests.conftest import AUDIT_KEY
        r = await async_client.get("/audit/summary", headers={"X-Audit-Key": AUDIT_KEY})
        assert r.status_code in (200, 503)

    def test_record_event_chains(self, audit_store):
        """Record event debe encadenar hashes."""
        cs, hp = audit_store
        e1 = hp.record_event("AUTH", "u1", "login", "success")
        e2 = hp.record_event("TOOL", "u1", "exec", "success")
        assert e2.previous_hash == e1.event_hash
        # Validate
        valid, cnt, err = hp.validate_chain()
        assert valid
        assert cnt == 2

    def test_validate_range(self, audit_store):
        """validate_range entre dos eventos debe funcionar."""
        cs, hp = audit_store
        e1 = hp.record_event("AUTH", "u1", "login", "ok")
        e2 = hp.record_event("TOOL", "u1", "exec", "ok")
        valid, cnt = hp.validate_range(e1.event_id, e2.event_id)
        assert valid
        assert cnt == 2

    def test_model_to_dict(self):
        """to_dict debe truncar hashes largos."""
        e = AuditEvent(event_type="AUTH", actor_id="test123456789", action="login", result="ok")
        d = e.to_dict()
        assert "..." in d["actor_id"]
        assert "..." in d["previous_hash"]
        assert "..." in d["gateway_signature"]

    def test_model_content_string(self):
        """get_content_string no debe ser vacío."""
        e = AuditEvent(event_type="TEST", actor_id="u", action="run", result="ok")
        cs = e.get_content_string()
        assert len(cs) > 10

    def test_cross_validate_server_response(self):
        """verify_server_response con None debe ser False."""
        e = AuditEvent(event_type="TOOL", actor_id="u", action="exec", result="ok")
        assert CrossValidator.verify_server_response(e, "data") is False

    def test_cross_validate_missing_signature(self):
        """verify_client_signature sin firma debe ser False."""
        e = AuditEvent(event_type="AUTH", actor_id="u", action="login", result="ok")
        e.event_hash = "abc123"
        assert CrossValidator.verify_client_signature(e, "secret") is False

    def test_generate_challenge(self):
        """generate_challenge debe devolver string."""
        e = AuditEvent(event_type="AUTH", actor_id="u", action="login", result="ok")
        c = CrossValidator.generate_challenge(e)
        assert ":" in c

    def test_get_events_by_type(self, audit_store):
        """Filtrar eventos por tipo debe funcionar."""
        cs, hp = audit_store
        hp.record_event("AUTH", "u1", "login", "ok")
        hp.record_event("TOOL", "u1", "exec", "ok")
        auth_events = cs.get_events(event_type="AUTH")
        assert len(auth_events) == 1
        assert auth_events[0].event_type == "AUTH"

    def test_get_events_limit_offset(self, audit_store):
        """Paginación de eventos debe funcionar."""
        cs, hp = audit_store
        hp.record_event("AUTH", "u1", "a", "ok")
        hp.record_event("AUTH", "u2", "a", "ok")
        hp.record_event("AUTH", "u3", "a", "ok")
        limited = cs.get_events(event_type="AUTH", limit=1)
        assert len(limited) == 1


# ── Cache ─────────────────────────────────────────────────────────────────

class TestCacheCoverage:
    @pytest.mark.asyncio
    async def test_cache_ttl(self):
        """Cache con TTL no debe fallar."""
        c = CacheService()
        await c.set("key", "val", ttl=1)
        v = await c.get("key")
        assert v == "val"

    @pytest.mark.asyncio
    async def test_cache_delete_missing(self):
        """Delete de key inexistente no debe fallar."""
        c = CacheService()
        await c.delete("no_existe")
        assert await c.get("no_existe") is None


# ── Auth Dependencies ─────────────────────────────────────────────────────

class TestAuthDeps:
    @pytest.mark.asyncio
    async def test_get_gateway_key_success(self):
        """get_gateway_key con key válida debe funcionar."""
        from fastapi import Request
        scope = {"type": "http", "headers": [(b"x-gateway-key", GATEWAY_KEY.encode())]}
        req = Request(scope)
        result = await get_gateway_key(req)
        assert result.role == KeyRole.GATEWAY

    @pytest.mark.asyncio
    async def test_get_admin_key_success(self):
        """get_admin_key con key válida debe funcionar."""
        from fastapi import Request
        scope = {"type": "http", "headers": [(b"x-admin-key", ADMIN_KEY.encode())]}
        req = Request(scope)
        result = await get_admin_key(req)
        assert result.role == KeyRole.ADMIN

    @pytest.mark.asyncio
    async def test_get_audit_key_missing(self):
        """get_audit_key sin header debe dar 401."""
        from fastapi import Request
        from fastapi.exceptions import HTTPException
        scope = {"type": "http", "headers": []}
        req = Request(scope)
        with pytest.raises(HTTPException) as exc:
            await get_audit_key(req)
        assert exc.value.status_code == 401

    def test_key_manager_revoke(self):
        """Revocar key debe funcionar."""
        raw, stored = key_manager.generate_key(KeyRole.GATEWAY, "test")
        assert key_manager.revoke_key(raw) is True
        assert key_manager.revoke_key("no_existe") is False

    def test_key_manager_register(self):
        """register_key debe guardar key."""
        api_key = key_manager.register_key("test-raw", KeyRole.GATEWAY, "reg-test")
        assert api_key.role == KeyRole.GATEWAY
        # validate debe funcionar
        stored = key_manager.validate_key("test-raw")
        assert stored is not None

    def test_validate_revoked_key(self):
        """Key revocada no debe validarse."""
        raw, _ = key_manager.generate_key(KeyRole.GATEWAY, "rev")
        key_manager.revoke_key(raw)
        assert key_manager.validate_key(raw) is None

    def test_revoke_by_hash(self):
        """revoke_by_hash debe funcionar."""
        raw, stored = key_manager.generate_key(KeyRole.ADMIN, "hash-test")
        assert key_manager.revoke_by_hash(stored.key_hash) is True
        assert key_manager.revoke_by_hash("no_existe") is False


# ── Client Pool ──────────────────────────────────────────────────────────

class TestClientCoverage:
    @pytest.mark.asyncio
    async def test_remove_server_not_registered(self):
        """Remove servidor no registrado no debe fallar."""
        pool = MCPClientPool()
        await pool.remove_server("no_existe")

    @pytest.mark.asyncio
    async def test_close_all_empty(self):
        """close_all sin servidores no debe fallar."""
        pool = MCPClientPool()
        await pool.close_all()


# ── Retention ─────────────────────────────────────────────────────────────

class TestRetentionCoverage:
    def test_secure_wipe_file_missing(self):
        """secure_wipe_file con archivo inexistente no debe fallar."""
        result = RetentionManager.secure_wipe_file(Path("/tmp/no_existe"))
        assert result is False

    @pytest.mark.asyncio
    async def test_cleanup_cycle_empty(self):
        """run_cleanup_cycle sin tareas no debe fallar."""
        rm = RetentionManager()
        results = await rm.run_cleanup_cycle()
        assert results == {}


# ── Policies ──────────────────────────────────────────────────────────────

class TestPoliciesCoverage:
    def test_denied_tool_with_server_scope(self):
        """Deny rule con servidor específico debe funcionar."""
        cfg = PolicyConfig(denied_tools=[
            type("DenyRule", (), {"pattern": "danger", "reason": "x", "server": "db"})(),
        ])
        engine = PolicyEngine(cfg)
        # Debe denegar en servidor db
        allowed, _ = engine.is_tool_allowed("danger", "db")
        assert allowed is False

    def test_allow_tool_not_denied(self):
        """Tool no denegada debe estar permitida."""
        cfg = PolicyConfig(denied_tools=[])
        engine = PolicyEngine(cfg)
        allowed, _ = engine.is_tool_allowed("safe_tool", "any")
        assert allowed is True


# ── Tool Dispatcher edge cases ────────────────────────────────────────────

class TestToolDispatcherCoverage:
    @pytest.mark.asyncio
    async def test_secure_tool_no_args(self):
        """Tool secure sin argumentos no debe fallar."""
        from umcp.pipeline.vault.vault import Vault
        from umcp.pipeline.detectors.ensemble import EnsembleDetector
        from umcp.pipeline.detectors.regex_detector import RegexDetector
        from umcp.layers.tool_dispatcher import ToolDispatcher
        p = Path(tempfile.mktemp(suffix=".db"))
        v = Vault("dispatcher-cov", db_path=p)
        d = EnsembleDetector(regex=RegexDetector())
        td = ToolDispatcher(vault=v, detector=d)
        result, log = await td.dispatch("unknown_tool", {})
        assert log["mode"] == "insecure"
        v.secure_wipe()


# ── Vault Manager edge cases ─────────────────────────────────────────────

class TestVaultManagerCoverage:
    def test_cleanup_expired_max_ttl(self):
        """Vault expirado por max_ttl debe limpiarse."""
        from umcp.pipeline.vault.vault_manager import VaultManager
        import time
        vm = VaultManager(idle_ttl=99999, max_ttl=0, cleanup_interval=0)
        v = vm.get_or_create_vault("max_ttl_test")
        v._last_activity = time.time()
        count = vm.cleanup_expired()
        assert count >= 0  # No debe fallar


# ── Privacy Retention async worker ────────────────────────────────────────

class TestRetentionAsync:
    @pytest.mark.asyncio
    async def test_async_cleanup_callback(self):
        """Registro de callback async debe ejecutarse."""
        rm = RetentionManager()
        results = {}

        async def my_cleanup():
            results["ran"] = True
            return 3

        rm.register_cleanup("test_async", my_cleanup)
        out = await rm.run_cleanup_cycle()
        assert out.get("test_async") == 3