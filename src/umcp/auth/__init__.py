"""
auth — Authentication layer (3-level API Key).

- api_key_auth.py: FastAPI middleware validating X-Gateway-Key, X-Admin-Key, X-Audit-Key
- key_manager.py: Key generation, hashing, and revocation
- dependencies.py: FastAPI dependency injection for endpoints
"""