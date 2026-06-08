"""FastAPI middleware for 3-level API Key authentication."""

from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from umcp.auth.key_manager import KeyManager, KeyRole, key_manager


AUTH_ENDPOINTS = {
    "admin": {"prefix": "/admin", "role": KeyRole.ADMIN},
    "audit": {"prefix": "/audit", "role": KeyRole.AUDIT},
}

# Tool endpoints require gateway_key
TOOL_PREFIXES = ["/mcp/", "/tools/"]


async def authenticate_request(
    request: Request,
    km: KeyManager = key_manager,
) -> None:
    """Authenticate a request based on the endpoint and API key header."""

    # Health and metrics endpoints are public
    if request.url.path in ("/health", "/metrics"):
        return

    # Determine required role based on path
    for config in AUTH_ENDPOINTS.values():
        if request.url.path.startswith(config["prefix"]):
            required_role = config["role"]
            break
    else:
        # Default: gateway_key for tool endpoints
        if any(request.url.path.startswith(p) for p in TOOL_PREFIXES):
            required_role = KeyRole.GATEWAY
        else:
            required_role = KeyRole.GATEWAY

    # Extract API key from header
    header_map = {
        KeyRole.GATEWAY: "X-Gateway-Key",
        KeyRole.ADMIN: "X-Admin-Key",
        KeyRole.AUDIT: "X-Audit-Key",
    }

    raw_key = request.headers.get(header_map[required_role])
    if not raw_key:
        raise HTTPException(
            status_code=401,
            detail=f"Missing {header_map[required_role]} header",
        )

    stored = km.validate_key(raw_key)
    if not stored:
        raise HTTPException(status_code=401, detail="Invalid or revoked API key")

    if stored.role != required_role:
        raise HTTPException(
            status_code=403,
            detail=f"Key with role '{stored.role.value}' cannot access '{required_role.value}' endpoints",
        )


class AuthMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware that validates API keys on every request."""

    async def dispatch(self, request: Request, call_next):
        try:
            await authenticate_request(request)
        except HTTPException as exc:
            return JSONResponse(
                status_code=exc.status_code,
                content={"detail": exc.detail},
            )
        return await call_next(request)