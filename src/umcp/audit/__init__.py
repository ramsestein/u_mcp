"""
audit — Blockchain-like hash chain auditor.

- models.py: AuditEvent dataclass with hash chain fields
- chain_store.py: Append-only SQLite store
- hash_chain_provider.py: record_event, validate_chain, validate_range
- cross_validator.py: Client-server cross-validation signatures
- audit_api.py: REST API protected by audit_key (read-only, export, validate)
"""