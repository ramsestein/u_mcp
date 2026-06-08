"""Tests para endpoints de herramientas (autodescubrimiento local)."""

import pytest
from tests.conftest import GATEWAY_KEY, ADMIN_KEY


async def test_list_tools(async_client):
    """GET /tools debe listar herramientas."""
    r = await async_client.get("/tools", headers={"X-Gateway-Key": GATEWAY_KEY})
    assert r.status_code == 200
    data = r.json()
    assert "tools" in data
    assert data["count"] >= 1
    names = [t["name"] for t in data["tools"]]
    assert "saludar" in names


async def test_get_tool_info(async_client):
    """GET /tools/{name} debe devolver info de una herramienta."""
    r = await async_client.get("/tools/saludar", headers={"X-Gateway-Key": GATEWAY_KEY})
    assert r.status_code == 200
    data = r.json()
    assert data["name"] == "saludar"
    assert "input_schema" in data


async def test_get_tool_not_found(async_client):
    """GET /tools/inexistente debe retornar 404."""
    r = await async_client.get("/tools/inexistente", headers={"X-Gateway-Key": GATEWAY_KEY})
    assert r.status_code == 404


async def test_execute_saludar(async_client):
    """POST /tools/saludar debe ejecutar la herramienta."""
    r = await async_client.post(
        "/tools/saludar",
        headers={"X-Gateway-Key": GATEWAY_KEY, "Content-Type": "application/json"},
        json={"nombre": "María"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["tool"] == "saludar"
    assert "María" in data["result"]["mensaje"]


async def test_execute_consultar_paciente(async_client):
    """POST /tools/consultar_paciente debe devolver datos."""
    r = await async_client.post(
        "/tools/consultar_paciente",
        headers={"X-Gateway-Key": GATEWAY_KEY, "Content-Type": "application/json"},
        json={"nhc": "NHC_ABCD"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["tool"] == "consultar_paciente"
    assert "nombre" in data["result"]
    assert data["result"]["edad"] == 45


async def test_execute_tool_not_found(async_client):
    """POST /tools/inexistente debe retornar 404."""
    r = await async_client.post(
        "/tools/inexistente",
        headers={"X-Gateway-Key": GATEWAY_KEY, "Content-Type": "application/json"},
        json={},
    )
    assert r.status_code == 404


async def test_execute_enviar_alerta(async_client):
    """POST /tools/enviar_alerta debe ejecutarse."""
    r = await async_client.post(
        "/tools/enviar_alerta",
        headers={"X-Gateway-Key": GATEWAY_KEY, "Content-Type": "application/json"},
        json={
            "paciente_id": "PACIENTE_1A2B",
            "tipo_alerta": "urgencia",
            "mensaje": "En observación",
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert data["tool"] == "enviar_alerta"
    assert data["result"]["status"] == "enviada"