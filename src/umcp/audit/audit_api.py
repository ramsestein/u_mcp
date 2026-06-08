"""Audit REST API — protected by audit_key (read-only)."""

from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import JSONResponse
from typing import Optional
from umcp.audit.hash_chain_provider import HashChainProvider, GENESIS_HASH
from umcp.audit.chain_store import ChainStore
from umcp.auth.dependencies import get_audit_key

audit_router = APIRouter(prefix="/audit", tags=["audit"])

# These will be set at startup
_provider: Optional[HashChainProvider] = None
_store: Optional[ChainStore] = None


def init_audit_api(provider: HashChainProvider, store: ChainStore) -> None:
    global _provider, _store
    _provider = provider
    _store = store


@audit_router.get("/events")
async def list_events(
    event_type: Optional[str] = Query(None),
    actor_id: Optional[str] = Query(None),
    limit: int = Query(100, le=1000),
    offset: int = Query(0),
    _=Depends(get_audit_key),
):
    """List audit events with optional filters."""
    if not _store:
        raise HTTPException(status_code=503, detail="Audit store not initialized")
    events = _store.get_events(
        event_type=event_type, actor_id=actor_id, limit=limit, offset=offset
    )
    total = _store.get_chain_length()
    return {
        "events": [e.to_dict() for e in events],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@audit_router.get("/chain")
async def get_chain(
    _=Depends(get_audit_key),
):
    """Get the full audit chain."""
    if not _store:
        raise HTTPException(status_code=503, detail="Audit store not initialized")
    events = _store.get_all_events()
    return {
        "chain_length": len(events),
        "genesis_hash": GENESIS_HASH,
        "events": [e.to_dict() for e in events],
    }


@audit_router.get("/chain/validate")
async def validate_chain(
    _=Depends(get_audit_key),
):
    """Validate the integrity of the entire audit chain."""
    if not _provider:
        raise HTTPException(status_code=503, detail="Audit provider not initialized")
    valid, count, errors = _provider.validate_chain()
    return {
        "valid": valid,
        "events_checked": count,
        "errors_found": errors,
        "chain_integrity": "OK" if valid else "COMPROMISED",
    }


@audit_router.get("/chain/export")
async def export_chain(
    _=Depends(get_audit_key),
):
    """Export the complete audit chain as signed JSON."""
    if not _store or not _provider:
        raise HTTPException(status_code=503, detail="Audit not initialized")
    events = _store.get_all_events()
    # Export with full detail (no truncation)
    export_data = {
        "genesis_hash": GENESIS_HASH,
        "chain_length": len(events),
        "exported_at": __import__("datetime").datetime.now().isoformat(),
        "events": [
            {
                "event_id": e.event_id,
                "timestamp": e.timestamp.isoformat(),
                "event_type": e.event_type,
                "actor_id": e.actor_id,
                "resource": e.resource,
                "action": e.action,
                "result": e.result,
                "previous_hash": e.previous_hash,
                "event_hash": e.event_hash,
                "gateway_signature": e.gateway_signature,
                "client_signature": e.client_signature,
                "metadata": e.metadata,
                "error": e.error,
            }
            for e in events
        ],
    }
    return JSONResponse(content=export_data)


@audit_router.get("/summary")
async def get_summary(
    _=Depends(get_audit_key),
):
    """Get a statistical summary of audit events."""
    if not _store:
        raise HTTPException(status_code=503, detail="Audit store not initialized")
    events = _store.get_all_events()
    by_type = {}
    by_result = {}
    for e in events:
        by_type[e.event_type] = by_type.get(e.event_type, 0) + 1
        by_result[e.result] = by_result.get(e.result, 0) + 1

    return {
        "total_events": len(events),
        "by_type": by_type,
        "by_result": by_result,
        "genesis_hash": GENESIS_HASH,
    }