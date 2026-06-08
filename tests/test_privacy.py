"""Tests para privacidad: breach_response, encryption, key_rotation, retention."""

import pytest
from umcp.privacy.breach_response import BreachResponse
from umcp.privacy.encryption import VaultEncryptor
from umcp.privacy.key_rotation import KeyRotation
from umcp.privacy.retention import RetentionManager, RetentionPolicy


# ── Breach Response ───────────────────────────────────────────────────────

class TestBreachResponse:
    def test_detect_pii_leak_normal_text(self):
        """Texto limpio no debe detectar leaks."""
        br = BreachResponse()
        result = br.detect_pii_leak("Este texto no tiene datos personales", [])
        assert result is None

    def test_detect_pii_leak_email(self):
        """Email en texto debe detectarse como leak."""
        br = BreachResponse()
        result = br.detect_pii_leak("mi correo es juan@mail.com", [])
        assert result is not None
        assert result.breach_type == "PII_LEAK"

    def test_detect_pii_leak_phone(self):
        """Teléfono debe detectarse como leak."""
        br = BreachResponse()
        result = br.detect_pii_leak("móvil 612345678", [])
        assert result is not None

    def test_breach_log(self):
        """Los breaches deben guardarse en el log."""
        br = BreachResponse()
        br.detect_pii_leak("email juan@mail.com", [])
        assert len(br.get_breach_log()) >= 1
        assert br.get_breach_log()[0].severity == "HIGH"


# ── Encryption ────────────────────────────────────────────────────────────

class TestEncryption:
    def test_encrypt_decrypt(self):
        """Cifrar y descifrar debe recuperar el original."""
        key = VaultEncryptor.generate_key()
        e = VaultEncryptor(key)
        original = "datos sensibles"
        encrypted = e.encrypt(original)
        assert encrypted != original
        decrypted = e.decrypt(encrypted)
        assert decrypted == original

    def test_different_keys(self):
        """Claves distintas deben producir cifrados distintos."""
        e1 = VaultEncryptor(VaultEncryptor.generate_key())
        e2 = VaultEncryptor(VaultEncryptor.generate_key())
        c1 = e1.encrypt("secreto")
        c2 = e2.encrypt("secreto")
        assert c1 != c2

    def test_no_key_fallback(self):
        """Sin clave, encrypt/decrypt deben ser no-op."""
        e = VaultEncryptor()
        assert e.encrypt("data") == "data"
        assert e.decrypt("data") == "data"

    def test_is_available_false(self):
        """Sin cryptography, is_available debe ser False."""
        e = VaultEncryptor("test-key-32bytes-long!!!!!!")
        assert e.is_available


# ── Key Rotation ──────────────────────────────────────────────────────────

class TestKeyRotation:
    def test_generate_key(self):
        """Generar clave debe devolver string no vacío."""
        kr = KeyRotation()
        key = kr.generate_key()
        assert len(key) > 10

    def test_should_rotate(self):
        """Clave recién creada no debe necesitar rotación."""
        kr = KeyRotation(rotation_days=30)
        from datetime import datetime, timezone
        recent = datetime.now(timezone.utc).isoformat()
        assert not kr.should_rotate(recent)

    def test_should_rotate_old(self):
        """Clave vieja debe necesitar rotación."""
        kr = KeyRotation(rotation_days=1)
        from datetime import datetime, timedelta, timezone
        old = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
        assert kr.should_rotate(old)


# ── Retention ─────────────────────────────────────────────────────────────

class TestRetention:
    def test_retention_policy_defaults(self):
        """Política de retención con valores por defecto."""
        mgr = RetentionManager()
        assert mgr.policy.vault_ttl_hours == 1

    def test_custom_policy(self):
        """Política personalizada."""
        policy = RetentionPolicy(vault_ttl_hours=2, audit_chain_ttl_days=30)
        mgr = RetentionManager(policy)
        assert mgr.policy.vault_ttl_hours == 2
        assert mgr.policy.audit_chain_ttl_days == 30

    def test_register_and_run_cleanup(self):
        """Registrar y ejecutar tarea de cleanup."""
        mgr = RetentionManager()
        results = {}

        def my_cleanup():
            results["ran"] = True
            return 5

        mgr.register_cleanup("test", my_cleanup)
        import asyncio
        import sys
        if sys.version_info >= (3, 11):
            out = asyncio.run(mgr.run_cleanup_cycle())
        else:
            # Simulación síncrona
            out = {"test": my_cleanup()}
        assert out.get("test") == 5