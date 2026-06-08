"""FastAPI dependency injection for authentication."""

from fastapi import Request, Depends, HTTPException
from umcp.auth.key_manager import KeyRole, key_manager, APIKey


async def get_gateway_key(request: Request) -> APIKey:
    """Dependency: extract and validate gateway_key."""
    raw = request.headers.get("X-Gateway-Key")
    if not raw:
        raise HTTPException(status_code=401, detail="Missing X-Gateway-Key")
    stored = key_manager.validate_key(raw)
    if not stored:
        raise HTTPException(status_code=401, detail="Invalid gateway key")
    if stored.role != KeyRole.GATEWAY:
        raise HTTPException(status_code=403, detail="Not a gateway key")
    return stored


async def get_admin_key(request: Request) -> APIKey:
    """Dependency: extract and validate admin_key."""
    raw = request.headers.get("X-Admin-Key")
    if not raw:
        raise HTTPException(status_code=401, detail="Missing X-Admin-Key")
    stored = key_manager.validate_key(raw)
    if not stored:
        raise HTTPException(status_code=401, detail="Invalid admin key")
    if stored.role != KeyRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not an admin key")
    return stored


async def get_audit_key(request: Request) -> APIKey:
    """Dependency: extract and validate audit_key."""
    raw = request.headers.get("X-Audit-Key")
    if not raw:
        raise HTTPException(status_code=401, detail="Missing X-Audit-Key")
    stored = key_manager.validate_key(raw)
    if not stored:
        raise HTTPException(status_code=401, detail="Invalid audit key")
    if stored.role != KeyRole.AUDIT:
        raise HTTPException(status_code=403, detail="Not an audit key")
    return stored