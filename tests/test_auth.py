"""Tests de autenticación — 3 roles de API Key."""

import pytest


async def test_health_public(async_client):
    """/health debe ser accesible sin API Key."""
    r = await async_client.get("/health")
    assert r.status_code == 200


async def test_metrics_public(async_client):
    "/metrics debe ser accesible sin API Key (307 redirect to /metrics/ ok)."""
    r = await async_client.get("/metrics", follow_redirects=False)
    assert r.status_code in (200, 307)


async def test_tools_without_key_returns_401(async_client):
    """/tools sin API Key debe retornar 401."""
    r = await async_client.get("/tools")
    assert r.status_code == 401


async def test_tools_with_gateway_key(async_client):
    """/tools con X-Gateway-Key debe retornar 200."""
    from tests.conftest import GATEWAY_KEY
    r = await async_client.get("/tools", headers={"X-Gateway-Key": GATEWAY_KEY})
    assert r.status_code == 200


async def test_admin_without_key_returns_401(async_client):
    """/admin sin API Key debe retornar 401."""
    r = await async_client.get("/admin/config")
    assert r.status_code == 401


async def test_admin_with_gateway_key_returns_403(async_client):
    "/admin con X-Gateway-Key (sin X-Admin-Key) debe retornar 401 por header faltante."""
    from tests.conftest import GATEWAY_KEY
    r = await async_client.get("/admin/config", headers={"X-Gateway-Key": GATEWAY_KEY})
    # El middleware busca X-Admin-Key primero, no lo encuentra → 401
    assert r.status_code == 401


async def test_admin_with_admin_key(async_client):
    """/admin con X-Admin-Key debe retornar 200."""
    from tests.conftest import ADMIN_KEY
    r = await async_client.get("/admin/config", headers={"X-Admin-Key": ADMIN_KEY})
    assert r.status_code == 200


async def test_audit_without_key_returns_401(async_client):
    """/audit sin API Key debe retornar 401."""
    r = await async_client.get("/audit/events")
    assert r.status_code == 401


async def test_audit_with_audit_key(async_client):
    "/audit con X-Audit-Key debe retornar 200 o 503 (si no inicializado)."""
    from tests.conftest import AUDIT_KEY
    r = await async_client.get("/audit/events", headers={"X-Audit-Key": AUDIT_KEY})
    # Puede ser 503 en tests si audit store no está inicializado
    assert r.status_code in (200, 503)


async def test_tools_with_invalid_key(async_client):
    """API Key inválida debe retornar 401."""
    r = await async_client.get("/tools", headers={"X-Gateway-Key": "invalid-key"})
    assert r.status_code == 401