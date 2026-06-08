"""Tests para endpoints de resources."""

import pytest
from tests.conftest import GATEWAY_KEY


async def test_list_resources(async_client):
    """GET /resources debe listar resources."""
    r = await async_client.get("/resources", headers={"X-Gateway-Key": GATEWAY_KEY})
    assert r.status_code == 200
    data = r.json()
    assert "resources" in data
    assert "pacientes.json" in data["resources"]


async def test_get_resource(async_client):
    """GET /resources/pacientes.json debe devolver datos."""
    r = await async_client.get("/resources/pacientes.json", headers={"X-Gateway-Key": GATEWAY_KEY})
    assert r.status_code == 200
    data = r.json()
    assert data["resource"] == "pacientes.json"
    assert len(data["data"]) == 5
    assert data["data"][0]["nhc"] == "NHC_ABCD"


async def test_get_resource_not_found(async_client):
    """GET /resources/no-existe debe retornar 404."""
    r = await async_client.get("/resources/no-existe.json", headers={"X-Gateway-Key": GATEWAY_KEY})
    assert r.status_code == 404