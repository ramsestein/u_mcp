"""MCP Client — Async client connecting to upstream MCP servers."""

import httpx
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from uuid import uuid4


@dataclass
class MCPServerConnection:
    """Represents a connection to an upstream MCP server."""
    name: str
    url: str
    client: httpx.AsyncClient = field(repr=False)
    tools: List[Dict[str, Any]] = field(default_factory=list)
    connected: bool = False


class MCPClientPool:
    """Pool of async MCP clients for upstream servers."""

    def __init__(self, timeout: float = 30.0, max_retries: int = 3):
        self._servers: Dict[str, MCPServerConnection] = {}
        self._timeout = timeout
        self._max_retries = max_retries

    async def register_server(self, name: str, url: str) -> MCPServerConnection:
        """Register and connect to an upstream MCP server."""
        client = httpx.AsyncClient(
            base_url=url,
            timeout=self._timeout,
        )
        conn = MCPServerConnection(name=name, url=url, client=client)
        await self._discover_tools(conn)
        self._servers[name] = conn
        return conn

    async def _discover_tools(self, conn: MCPServerConnection) -> None:
        """Discover available tools from a server."""
        try:
            resp = await conn.client.get("/tools")
            resp.raise_for_status()
            data = resp.json()
            conn.tools = data.get("tools", [])
            conn.connected = True
        except Exception as e:
            conn.tools = []
            conn.connected = False
            raise

    async def call_tool(
        self, server_name: str, tool_name: str, arguments: Dict[str, Any]
    ) -> Any:
        """Call a tool on a specific server."""
        conn = self._servers.get(server_name)
        if not conn:
            raise ValueError(f"Server '{server_name}' not registered")
        resp = await conn.client.post(
            f"/tools/{tool_name}",
            json=arguments,
        )
        resp.raise_for_status()
        return resp.json()

    async def get_all_tools(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get all tools from all registered servers."""
        return {name: conn.tools for name, conn in self._servers.items()}

    async def remove_server(self, name: str) -> None:
        """Remove and disconnect a server."""
        conn = self._servers.pop(name, None)
        if conn:
            await conn.client.aclose()

    async def close_all(self) -> None:
        """Close all connections."""
        for conn in self._servers.values():
            await conn.client.aclose()
        self._servers.clear()