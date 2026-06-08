"""
Gateway server — FastMCP main entry point.

Integrates all framework layers:
  - Auth middleware (3 API Keys)
  - Admin REST API (server/tool management)
  - Tool auto-discovery (tools/ directory)
  - Resources (resources/ directory)
  - Audit API (blockchain-like hash chain)
  - Anonymization pipeline (regex + Aho-Corasick + BERT)
  - MCP server (Streamable HTTP + SSE)
  - Prometheus /metrics endpoint
"""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from prometheus_client import make_asgi_app

from umcp.gateway.config import settings
from umcp.gateway.client import MCPClientPool
from umcp.gateway.admin_api import admin_router, init_admin_api
from umcp.auth.api_key_auth import AuthMiddleware
from umcp.auth.key_manager import key_manager, KeyRole
from umcp.audit.chain_store import ChainStore
from umcp.audit.hash_chain_provider import HashChainProvider
from umcp.audit.audit_api import audit_router, init_audit_api
from umcp.privacy.retention import RetentionManager, RetentionPolicy
from umcp.pipeline.vault.vault_manager import VaultManager
from umcp.pipeline.detectors.ensemble import EnsembleDetector
from umcp.pipeline.detectors.regex_detector import RegexDetector
from umcp.pipeline.detectors.aho_corasick import AhoCorasickDetector
from umcp.pipeline.detectors.unicode import UnicodeSanitizer
from umcp.observability.logging import configure_logging, get_logger
from umcp.tool_loader import tool_registry, resource_loader, ToolDefinition

logger = get_logger(__name__)


# ── Global state ──────────────────────────────────────────────────────────
client_pool: MCPClientPool = MCPClientPool()
vault_manager: VaultManager = VaultManager(
    idle_ttl=settings.retention.vault_ttl_hours * 3600,
    max_ttl=settings.retention.vault_max_ttl_hours * 3600,
    encryption_key=settings.encryption.vault_key,
)
retention_mgr = RetentionManager(
    RetentionPolicy(
        vault_ttl_hours=settings.retention.vault_ttl_hours,
        vault_max_ttl_hours=settings.retention.vault_max_ttl_hours,
        audit_chain_ttl_days=settings.retention.audit_chain_ttl_days,
    )
)
chain_store: ChainStore = ChainStore(Path(settings.audit.chain_db_path))
audit_provider: HashChainProvider = HashChainProvider(
    store=chain_store,
    gateway_secret=settings.auth.admin_key,  # gateway HMAC secret
)

# Shared ensemble detector (lazy init with BERT)
_detector: EnsembleDetector = None


def get_detector() -> EnsembleDetector:
    """Get or create the shared ensemble detector."""
    global _detector
    if _detector is None:
        import logging as py_logging
        py_logging.getLogger("transformers").setLevel(py_logging.WARNING)
        py_logging.getLogger("torch").setLevel(py_logging.WARNING)

        models_dir = Path(settings.pipeline.models_dir)
        dict_dir = models_dir.parent.parent / "resources" / "dictionaries"

        detector = EnsembleDetector(
            regex=RegexDetector(),
            unicode_sanitizer=UnicodeSanitizer(),
        )

        # Cargar Aho-Corasick con diccionario clínico desde CSV externo
        entidades_csv = dict_dir / "entidades.csv"
        if entidades_csv.exists():
            try:
                aho = AhoCorasickDetector(dictionary_path=entidades_csv)
                detector.aho_corasick = aho
                logger.info(f"Aho-Corasick loaded: {entidades_csv}")
            except Exception as e:
                logger.warning(f"Aho-Corasick not available: {e}")
        else:
            logger.info(f"No entities CSV found at {entidades_csv}, Aho-Corasick disabled")

        # Try to load BERT if models exist
        if (models_dir / "bsc-bio-ehr-es-carmen-anon").exists():
            try:
                from umcp.pipeline.detectors.bert_detector import BERTDetector
                detector.bert = BERTDetector(
                    models_dir=models_dir,
                    threshold=settings.pipeline.bert_threshold,
                    chunk_size=settings.pipeline.bert_chunk_size,
                    batch_size=settings.pipeline.bert_batch_size,
                )
                logger.info("BERT detector loaded successfully")
            except Exception as e:
                logger.warning(f"BERT detector not available: {e}")
        else:
            logger.info("No BERT models found, running with regex + Aho-Corasick only")

        _detector = detector
    return _detector


# ── App factory ────────────────────────────────────────────────────────────

def create_app() -> FastAPI:
    """Create and configure the uMCP FastAPI application."""

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # ── STARTUP ──────────────────────────────────────────────────────
        configure_logging(settings.server.log_level)

        # Register default dev keys (in production, load from env/DB)
        key_manager.register_key(settings.auth.gateway_key, KeyRole.GATEWAY, "default-gateway")
        key_manager.register_key(settings.auth.admin_key, KeyRole.ADMIN, "default-admin")
        key_manager.register_key(settings.auth.audit_key, KeyRole.AUDIT, "default-audit")
        logger.info("API keys registered (gateway/admin/audit)")

        # Init admin API
        init_admin_api(client_pool)

        # Init audit API
        init_audit_api(audit_provider, chain_store)

        # Register retention cleanup
        async def cleanup_vaults():
            return vault_manager.cleanup_expired()
        retention_mgr.register_cleanup("vaults", cleanup_vaults)

        async def purge_audit_chain():
            return chain_store.purge_older_than(settings.retention.audit_chain_ttl_days)
        retention_mgr.register_cleanup("audit_chain", purge_audit_chain)

        # ── Auto-descubrir herramientas locales ──────────────────────────
        n_tools = tool_registry.discover_tools()
        resource_list = resource_loader.list_resources()
        logger.info(
            f"Tools cargadas: {n_tools} ({', '.join(tool_registry.get_tool_names())})"
        )
        logger.info(f"Resources disponibles: {resource_list}")

        logger.info(
            "uMCP gateway started",
            host=settings.server.host,
            port=settings.server.port,
        )
        yield

        # ── SHUTDOWN ─────────────────────────────────────────────────────
        await client_pool.close_all()
        chain_store.close()
        logger.info("uMCP gateway shut down")

    app = FastAPI(
        title="uMCP Security Framework",
        description="Unified MCP Security Framework — Secure Agentic Framework with Privacy",
        version="0.1.0",
        lifespan=lifespan,
    )

    # ── Middleware ────────────────────────────────────────────────────────
    app.add_middleware(AuthMiddleware)

    @app.middleware("http")
    async def add_security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Framework"] = "uMCP"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        return response

    # ── Routes ────────────────────────────────────────────────────────────

    @app.get("/health")
    async def health():
        return {
            "status": "ok",
            "version": "0.1.0",
            "k_anonymity": settings.privacy.k_anonymity_mode,
            "servers": len(client_pool._servers),
            "vaults_active": vault_manager.active_count,
            "audit_events": chain_store.get_chain_length(),
        }

    # Prometheus metrics
    metrics_app = make_asgi_app()
    app.mount("/metrics", metrics_app)

    # Admin API
    app.include_router(admin_router)

    # Audit API
    app.include_router(audit_router)

    # ── MCP endpoint placeholder ─────────────────────────────────────────
    @app.post("/mcp/{server_name}/{tool_name}")
    async def call_remote_tool(server_name: str, tool_name: str, request: Request):
        """Call a tool on a registered MCP server."""
        body = await request.json()
        try:
            result = await client_pool.call_tool(server_name, tool_name, body)
            return {"result": result}
        except ValueError as e:
            return JSONResponse(status_code=404, content={"detail": str(e)})

    # ── Tools endpoints (auto-descubiertas) ──────────────────────────────

    @app.get("/tools")
    async def list_local_tools():
        """Lista todas las herramientas locales auto-descubiertas."""
        tools = tool_registry.list_tools()
        return {
            "tools": tools,
            "count": len(tools),
        }

    @app.get("/tools/{tool_name}")
    async def get_tool_info(tool_name: str):
        """Obtiene información detallada de una herramienta local."""
        tool = tool_registry.get_tool(tool_name)
        if not tool:
            return JSONResponse(status_code=404, content={"error": f"Tool '{tool_name}' no encontrada"})
        return {
            "name": tool.name,
            "description": tool.description,
            "security": tool.security,
            "version": tool.version,
            "input_schema": tool.input_schema,
            "output_schema": tool.output_schema,
            "examples": tool.examples,
        }

    @app.post("/tools/{tool_name}")
    async def execute_local_tool(tool_name: str, request: Request):
        """Ejecuta una herramienta local."""
        tool = tool_registry.get_tool(tool_name)
        if not tool:
            return JSONResponse(status_code=404, content={"error": f"Tool '{tool_name}' no encontrada"})

        body = await request.json()
        context = {"gateway_key": request.headers.get("X-Gateway-Key", "")}

        try:
            result = await tool_registry.call_tool(tool_name, body, context)
            return {"tool": tool_name, "result": result}
        except Exception as e:
            return JSONResponse(status_code=500, content={"error": str(e)})

    # ── Resources endpoints ──────────────────────────────────────────────

    @app.get("/resources")
    async def list_resources():
        """Lista los resources disponibles."""
        return {
            "resources": resource_loader.list_resources(),
        }

    @app.get("/resources/{resource_name}")
    async def get_resource(resource_name: str):
        """Obtiene el contenido de un resource."""
        data = resource_loader.load_json(resource_name)
        if data is None:
            return JSONResponse(status_code=404, content={"error": f"Resource '{resource_name}' no encontrado"})
        return {"resource": resource_name, "data": data}

    return app


app = create_app()