"""Admin REST API — server/tool/config management (protected by admin_key)."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Any, Dict, List, Optional
from umcp.gateway.client import MCPClientPool
from umcp.gateway.config import settings
from umcp.auth.dependencies import get_admin_key

admin_router = APIRouter(prefix="/admin", tags=["admin"])

# Set at startup
_client_pool: Optional[MCPClientPool] = None


def init_admin_api(client_pool: MCPClientPool) -> None:
    global _client_pool
    _client_pool = client_pool


class ServerRegister(BaseModel):
    name: str
    url: str


class PrivacyConfigUpdate(BaseModel):
    k_anonymity_mode: Optional[str] = None  # "detect" | "block"
    k_anonymity_threshold: Optional[int] = None
    l_diversity_threshold: Optional[int] = None


@admin_router.get("/health")
async def health():
    return {
        "status": "ok",
        "version": "0.1.0",
        "servers_connected": len(_client_pool._servers) if _client_pool else 0,
    }


@admin_router.get("/servers")
async def list_servers(_=Depends(get_admin_key)):
    if not _client_pool:
        return {"servers": []}
    servers = []
    for name, conn in _client_pool._servers.items():
        servers.append({
            "name": name,
            "url": conn.url,
            "connected": conn.connected,
            "tool_count": len(conn.tools),
        })
    return {"servers": servers}


@admin_router.post("/servers/register")
async def register_server(
    data: ServerRegister,
    _=Depends(get_admin_key),
):
    if not _client_pool:
        raise HTTPException(503, "Client pool not initialized")
    try:
        conn = await _client_pool.register_server(data.name, data.url)
        return {
            "status": "registered",
            "name": data.name,
            "url": data.url,
            "tool_count": len(conn.tools),
        }
    except Exception as e:
        raise HTTPException(400, detail=str(e))


@admin_router.delete("/servers/{server_name}")
async def remove_server(
    server_name: str,
    _=Depends(get_admin_key),
):
    if not _client_pool:
        raise HTTPException(503, "Client pool not initialized")
    await _client_pool.remove_server(server_name)
    return {"status": "removed", "name": server_name}


@admin_router.get("/tools")
async def list_tools(_=Depends(get_admin_key)):
    if not _client_pool:
        return {"tools": {}}
    return {"tools": await _client_pool.get_all_tools()}


@admin_router.get("/config")
async def get_config(_=Depends(get_admin_key)):
    """Get current configuration (without sensitive fields)."""
    return {
        "server": {
            "host": settings.server.host,
            "port": settings.server.port,
        },
        "pipeline": {
            "bert_threshold": settings.pipeline.bert_threshold,
            "bert_chunk_size": settings.pipeline.bert_chunk_size,
        },
        "privacy": {
            "k_anonymity_mode": settings.privacy.k_anonymity_mode,
            "k_anonymity_threshold": settings.privacy.k_anonymity_threshold,
            "l_diversity_threshold": settings.privacy.l_diversity_threshold,
        },
        "retention": {
            "vault_ttl_hours": settings.retention.vault_ttl_hours,
            "audit_chain_ttl_days": settings.retention.audit_chain_ttl_days,
        },
        "audit": {
            "enabled": settings.audit.enabled,
        },
    }


@admin_router.put("/config/privacy")
async def update_privacy_config(
    data: PrivacyConfigUpdate,
    _=Depends(get_admin_key),
):
    """Update privacy/k-anonymity configuration dynamically."""
    if data.k_anonymity_mode is not None:
        if data.k_anonymity_mode not in ("detect", "block"):
            raise HTTPException(400, detail="k_anonymity_mode must be 'detect' or 'block'")
        settings.privacy.k_anonymity_mode = data.k_anonymity_mode
    if data.k_anonymity_threshold is not None:
        if data.k_anonymity_threshold < 1:
            raise HTTPException(400, detail="k_anonymity_threshold must be ≥ 1")
        settings.privacy.k_anonymity_threshold = data.k_anonymity_threshold
    if data.l_diversity_threshold is not None:
        if data.l_diversity_threshold < 1:
            raise HTTPException(400, detail="l_diversity_threshold must be ≥ 1")
        settings.privacy.l_diversity_threshold = data.l_diversity_threshold
    return {
        "status": "updated",
        "privacy": {
            "k_anonymity_mode": settings.privacy.k_anonymity_mode,
            "k_anonymity_threshold": settings.privacy.k_anonymity_threshold,
            "l_diversity_threshold": settings.privacy.l_diversity_threshold,
        },
    }


@admin_router.get("/stats")
async def get_stats(_=Depends(get_admin_key)):
    """Get system statistics."""
    return {
        "servers": len(_client_pool._servers) if _client_pool else 0,
        "total_tools": sum(
            len(conn.tools) for conn in _client_pool._servers.values()
        ) if _client_pool else 0,
    }