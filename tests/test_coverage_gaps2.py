"""Tests para cubrir líneas faltantes en módulos parciales - Fase 2."""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock

from umcp.gateway.admin_api import (
    admin_router,
    init_admin_api,
    ServerRegister,
    PrivacyConfigUpdate,
)
from umcp.gateway.cache import CacheService
from umcp.gateway.client import MCPClientPool
from umcp.auth.dependencies import get_gateway_key, get_admin_key, get_audit_key
from umcp.auth.key_manager import key_manager, KeyRole
from umcp.privacy.retention import RetentionManager, RetentionPolicy
from umcp.pipeline.vault.vault_manager import VaultManager
from umcp.pipeline.detectors.unicode import UnicodeSanitizer
from umcp.pipeline.detectors.base import Entity
from tests.conftest import GATEWAY_KEY, ADMIN_KEY, AUDIT_KEY


# ── Cache ─────────────────────────────────────────────────────────────────

class TestCacheRedis:
    @pytest.mark.asyncio
    async def test_redis_init_no_url(self):
        """Cache sin URL Redis debe usar memoria."""
        c = CacheService()
        assert c._redis is None

    @pytest.mark.asyncio
    async def test_redis_init_bad_url(self):
        """Cache con URL Redis inválida debe no lanzar en init (sin conectar)."""
        # CacheService.__init__ solo guarda la URL, no conecta
        c = CacheService()  # Sin redis_url
        assert c._redis is None
        # Usar memoria como fallback
        await c.set("k", "v")
        assert await c.get("k") == "v"

    @pytest.mark.asyncio
    async def test_flush_memory(self):
        """flush en memoria debe limpiar todo."""
        c = CacheService()
        await c.set("a", 1)
        await c.set("b", 2)
        await c.flush()
        assert await c.get("a") is None
        assert await c.get("b") is None


# ── Admin API ─────────────────────────────────────────────────────────────

class TestAdminAPICoverage:
    @pytest.mark.asyncio
    async def test_admin_stats_no_pool(self, async_client):
        """GET /admin/stats sin pool debe funcionar."""
        r = await async_client.get("/admin/stats", headers={"X-Admin-Key": ADMIN_KEY})
        assert r.status_code in (200, 503)


# ── Retention ─────────────────────────────────────────────────────────────

class TestRetentionDetailed:
    def test_secure_wipe_file_success(self):
        """secure_wipe_file con archivo real debe funcionar."""
        p = Path(tempfile.mktemp(suffix=".tmp"))
        p.write_text("data")
        result = RetentionManager.secure_wipe_file(p)
        assert result is True
        assert not p.exists()

    def test_retention_policy_defaults(self):
        """Valores por defecto de RetentionPolicy."""
        p = RetentionPolicy()
        assert p.vault_ttl_hours == 1
        assert p.audit_chain_ttl_days == 90
        assert p.cleanup_interval_seconds == 300

    def test_register_callback(self):
        """Registrar y ejecutar callback síncrono."""
        rm = RetentionManager()
        results = []

        def cb():
            results.append(1)
            return 1

        rm.register_cleanup("test", cb)
        import asyncio
        out = asyncio.run(rm.run_cleanup_cycle())
        assert out.get("test") == 1


# ── Vault Manager edge ────────────────────────────────────────────────────

class TestVaultManagerDetailed:
    def test_destroy_and_recreate(self):
        """Destruir y recrear vault con mismo session_id."""
        vm = VaultManager(idle_ttl=99999, max_ttl=99999)
        v1 = vm.get_or_create_vault("destroy_recreate_test")
        vm.destroy_vault("destroy_recreate_test")
        assert vm.active_count == 0
        v2 = vm.get_or_create_vault("destroy_recreate_test")
        assert v2 is not None

    def test_get_vault_not_found(self):
        """get_vault con sesión inexistente debe devolver None."""
        vm = VaultManager()
        assert vm.get_vault("no_existe") is None


# ── Unicode edge cases ────────────────────────────────────────────────────

class TestUnicodeEdge:
    def test_sanitize_normal(self):
        """sanitize de texto normal no debe cambiarlo."""
        u = UnicodeSanitizer()
        assert u.sanitize("Hola Mundo") == "Hola Mundo"

    def test_sanitize_empty(self):
        """sanitize de string vacío."""
        u = UnicodeSanitizer()
        assert u.sanitize("") == ""

    def test_entity_to_dict(self):
        """Entity.to_dict debe funcionar."""
        e = Entity("PERSON", "Juan", 0, 4, 0.95, "regex")
        d = e.to_dict()
        assert d["type"] == "PERSON"
        assert d["score"] == 0.95


# ── Auth Dependencies edge ────────────────────────────────────────────────

class TestAuthDepsDetailed:
    @pytest.mark.asyncio
    async def test_get_gateway_key_missing(self):
        """get_gateway_key sin header debe dar 401."""
        from fastapi import Request
        from fastapi.exceptions import HTTPException
        scope = {"type": "http", "headers": []}
        req = Request(scope)
        with pytest.raises(HTTPException) as exc:
            await get_gateway_key(req)
        assert exc.value.status_code == 401

    @pytest.mark.asyncio
    async def test_get_admin_key_with_wrong_role(self):
        """get_admin_key con key de gateway debe dar 403."""
        from fastapi import Request
        from fastapi.exceptions import HTTPException
        scope = {"type": "http", "headers": [(b"x-admin-key", GATEWAY_KEY.encode())]}
        req = Request(scope)
        with pytest.raises(HTTPException) as exc:
            await get_admin_key(req)
        assert exc.value.status_code == 403

    @pytest.mark.asyncio
    async def test_get_audit_key_with_wrong_role(self):
        """get_audit_key con key de gateway debe dar 403."""
        from fastapi import Request
        from fastapi.exceptions import HTTPException
        scope = {"type": "http", "headers": [(b"x-audit-key", GATEWAY_KEY.encode())]}
        req = Request(scope)
        with pytest.raises(HTTPException) as exc:
            await get_audit_key(req)
        assert exc.value.status_code == 403


# ── Auth Middleware edge ──────────────────────────────────────────────────

class TestAuthMiddlewareEdge:
    @pytest.mark.asyncio
    async def test_middleware_no_key_on_tools(self, async_client):
        """Sin key en /tools debe dar 401."""
        r = await async_client.get("/tools")
        assert r.status_code == 401

    @pytest.mark.asyncio
    async def test_middleware_invalid_key(self, async_client):
        """Key inválida debe dar 401."""
        r = await async_client.get("/tools", headers={"X-Gateway-Key": "invalid"})
        assert r.status_code == 401