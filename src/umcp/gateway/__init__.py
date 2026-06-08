"""
gateway — FastMCP server/client core.

- server.py: FastMCP Server (SSE + Streamable HTTP)
- client.py: Async MCP client for upstream servers
- config.py: Unified YAML/env configuration via pydantic-settings
- admin_api.py: REST API for server administration (protected by admin_key)
- cache.py: Redis cache with in-memory fallback
- exceptions.py: Exception hierarchy with HTTP codes
"""