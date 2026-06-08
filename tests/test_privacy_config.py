"""Tests para configuración dinámica de privacidad (k-anonymity)."""

import pytest
from tests.conftest import ADMIN_KEY


async def test_get_privacy_config(async_client):
    """GET /admin/config debe incluir config de privacidad."""
    r = await async_client.get("/admin/config", headers={"X-Admin-Key": ADMIN_KEY})
    assert r.status_code == 200
    data = r.json()
    assert "privacy" in data
    assert data["privacy"]["k_anonymity_mode"] in ("detect", "block")


async def test_update_privacy_mode(async_client):
    """PUT /admin/config/privacy debe cambiar modo."""
    r = await async_client.put(
        "/admin/config/privacy",
        headers={"X-Admin-Key": ADMIN_KEY, "Content-Type": "application/json"},
        json={"k_anonymity_mode": "block"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "updated"
    assert data["privacy"]["k_anonymity_mode"] == "block"


async def test_update_privacy_threshold(async_client):
    """PUT /admin/config/privacy debe cambiar threshold."""
    r = await async_client.put(
        "/admin/config/privacy",
        headers={"X-Admin-Key": ADMIN_KEY, "Content-Type": "application/json"},
        json={"k_anonymity_threshold": 3},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["privacy"]["k_anonymity_threshold"] == 3


async def test_update_invalid_mode(async_client):
    """Modo inválido debe retornar 400."""
    r = await async_client.put(
        "/admin/config/privacy",
        headers={"X-Admin-Key": ADMIN_KEY, "Content-Type": "application/json"},
        json={"k_anonymity_mode": "invalid"},
    )
    assert r.status_code == 400


async def test_update_invalid_threshold(async_client):
    """Threshold < 1 debe retornar 400."""
    r = await async_client.put(
        "/admin/config/privacy",
        headers={"X-Admin-Key": ADMIN_KEY, "Content-Type": "application/json"},
        json={"k_anonymity_threshold": 0},
    )
    assert r.status_code == 400


async def test_health_includes_k_anonymity(async_client):
    """GET /health debe incluir k_anonymity."""
    r = await async_client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert "k_anonymity" in data


async def test_change_reflected_in_health(async_client):
    """Cambiar modo debe reflejarse en /health."""
    # Cambiar a block
    await async_client.put(
        "/admin/config/privacy",
        headers={"X-Admin-Key": ADMIN_KEY, "Content-Type": "application/json"},
        json={"k_anonymity_mode": "block"},
    )
    # Verificar en health
    r = await async_client.get("/health")
    assert r.json()["k_anonymity"] == "block"