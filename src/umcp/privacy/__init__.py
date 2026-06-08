"""
privacy — Data privacy layer.

- encryption.py: AES-256-GCM encryption for vault + audit chain
- key_rotation.py: Monthly key rotation + re-encryption
- retention.py: TTL policies + async cleanup worker + secure wipe
- reidentification.py: k-anonymity (≥5) + l-diversity (≥3) checks
- breach_response.py: PII leak detection + alert + immutable log
"""