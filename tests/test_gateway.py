"""Tests para gateway: client, cache, exceptions."""

import pytest
from umcp.gateway.client import MCPClientPool
from umcp.gateway.cache import CacheService
from umcp.gateway.exceptions import (
    uMCPError,
    AuthenticationError,
    AuthorizationError,
    PolicyViolationError,
    ToolNotFoundError,
    EncryptionError,
    ReIdentificationRiskError,
    PIILeakError,
    ChainIntegrityError,
)


# ── Exceptions ────────────────────────────────────────────────────────────

class TestExceptions:
    def test_umcp_error(self):
        """Base exception."""
        with pytest.raises(uMCPError):
            raise uMCPError()

    def test_authentication_error(self):
        """AuthenticationError debe retornar 401."""
        exc = AuthenticationError()
        assert exc.status_code == 401

    def test_authorization_error(self):
        """AuthorizationError debe retornar 403."""
        exc = AuthorizationError()
        assert exc.status_code == 403

    def test_policy_violation(self):
        """PolicyViolation debe tener reason."""
        exc = PolicyViolationError("Denied", "no permission")
        assert exc.status_code == 403

    def test_tool_not_found(self):
        exc = ToolNotFoundError("test")
        assert "test" in str(exc.detail)

    def test_reidentification_error(self):
        exc = ReIdentificationRiskError(k=1, l=2, threshold_k=5, threshold_l=3)
        assert "k=1" in str(exc)
        assert "l=2" in str(exc)

    def test_chain_integrity_error(self):
        with pytest.raises(ChainIntegrityError):
            raise ChainIntegrityError("Chain broken")


# ── Cache ─────────────────────────────────────────────────────────────────

class TestCache:
    @pytest.mark.asyncio
    async def test_set_and_get(self):
        """Set y get deben funcionar."""
        cache = CacheService()
        await cache.set("key1", "value1")
        val = await cache.get("key1")
        assert val == "value1"

    @pytest.mark.asyncio
    async def test_get_missing(self):
        """Key inexistente debe devolver None."""
        cache = CacheService()
        val = await cache.get("no_existe")
        assert val is None

    @pytest.mark.asyncio
    async def test_delete(self):
        """Delete debe eliminar key."""
        cache = CacheService()
        await cache.set("key", "val")
        await cache.delete("key")
        assert await cache.get("key") is None

    @pytest.mark.asyncio
    async def test_flush(self):
        """Flush debe limpiar todo."""
        cache = CacheService()
        await cache.set("a", 1)
        await cache.set("b", 2)
        await cache.flush()
        assert await cache.get("a") is None


# ── Client Pool ───────────────────────────────────────────────────────────

class TestClientPool:
    @pytest.mark.asyncio
    async def test_register_server_unknown(self):
        """Registrar servidor en URL inexistente debe fallar."""
        pool = MCPClientPool(timeout=1)
        with pytest.raises(Exception):
            await pool.register_server("test", "http://localhost:1")
        await pool.close_all()

    @pytest.mark.asyncio
    async def test_get_all_tools_empty(self):
        """Sin servidores, get_all_tools debe devolver vacío."""
        pool = MCPClientPool()
        tools = await pool.get_all_tools()
        assert tools == {}
        await pool.close_all()

    @pytest.mark.asyncio
    async def test_call_tool_not_registered(self):
        """Tool en servidor no registrado debe lanzar ValueError."""
        pool = MCPClientPool()
        with pytest.raises(ValueError, match="not registered"):
            await pool.call_tool("no_existe", "tool", {})
        await pool.close_all()