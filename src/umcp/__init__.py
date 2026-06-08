"""
uMCP — Unified MCP Security Framework.

Secure Agentic Framework with double-plane privacy:
  - Real plane (user): sees real data
  - Anonymized plane (LLM): operates in anonymized space

Capas:
  - Gateway: FastMCP server/client core
  - Auth: 3-level API Key authentication
  - Policies: access control, tool security, allow/deny
  - Pipeline: anonymization engine (Regex → Aho-Corasick → BERT)
  - Layers: msg_interceptor, resource_pipeline, tool_dispatcher
  - Privacy: encryption, retention, re-identification prevention, breach response
  - Audit: blockchain-like hash chain with cross-validation
  - Observability: OTel + Prometheus + structlog
"""

__version__ = "0.1.0"