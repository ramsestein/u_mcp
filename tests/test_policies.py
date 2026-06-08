"""Tests para políticas de seguridad (allow_deny, rbac, tool_security)."""

import pytest
from umcp.policies.allow_deny import PolicyEngine, PolicyConfig, DenyRule, AllowRule
from umcp.policies.rbac import RBACEngine, Permission
from umcp.policies.tool_security import ToolSecurityConfig, ToolSecurityMode


# ── Allow/Deny ────────────────────────────────────────────────────────────

class TestPolicyEngine:
    def test_server_allowed_empty_whitelist(self):
        """Sin whitelist, todos los servidores están permitidos."""
        engine = PolicyEngine()
        assert engine.is_server_allowed("http://any.com/mcp") is True

    def test_server_allowed_in_whitelist(self):
        """Servidor en whitelist debe estar permitido."""
        cfg = PolicyConfig(allowed_servers=["https://trusted.com/*"])
        engine = PolicyEngine(cfg)
        assert engine.is_server_allowed("https://trusted.com/mcp")
        assert not engine.is_server_allowed("https://evil.com/mcp")

    def test_deny_tool(self):
        """Tool en deny list debe estar denegada."""
        cfg = PolicyConfig(denied_tools=[
            DenyRule(pattern="shell_exec", reason="RCE"),
        ])
        engine = PolicyEngine(cfg)
        allowed, reason = engine.is_tool_allowed("shell_exec")
        assert allowed is False
        assert "RCE" in reason

    def test_allow_tool_by_default(self):
        """Tool no listada en deny debe estar permitida en modo deny."""
        engine = PolicyEngine()
        allowed, _ = engine.is_tool_allowed("safe_tool")
        assert allowed is True

    def test_allow_mode_deny_all(self):
        """Modo allowlist con lista vacía debe denegar todo."""
        cfg = PolicyConfig(mode="allow")
        engine = PolicyEngine(cfg)
        allowed, reason = engine.is_tool_allowed("anything")
        assert allowed is False
        assert "Empty" in reason

    def test_allow_mode_allow_specific(self):
        """Modo allowlist debe permitir solo tools listadas."""
        cfg = PolicyConfig(
            mode="allow",
            allowed_tools=[AllowRule(pattern="safe_tool")],
        )
        engine = PolicyEngine(cfg)
        allowed, reason = engine.is_tool_allowed("safe_tool")
        assert allowed is True
        allowed, reason = engine.is_tool_allowed("evil_tool")
        assert allowed is False
        assert "Not in allowlist" in reason

    def test_denied_tool_wildcard(self):
        """Patrón comodín debe funcionar."""
        cfg = PolicyConfig(denied_tools=[
            DenyRule(pattern="db:delete_*", reason="Destructive"),
        ])
        engine = PolicyEngine(cfg)
        allowed, _ = engine.is_tool_allowed("db:delete_all")
        assert allowed is False
        allowed, _ = engine.is_tool_allowed("db:query")
        assert allowed is True


# ── RBAC ──────────────────────────────────────────────────────────────────

class TestRBAC:
    def test_default_deny(self):
        """Por defecto, todo debe estar denegado."""
        rbac = RBACEngine()
        assert rbac.check_access("user", "server", "tool") is False

    def test_allow_specific_role(self):
        """Rol específico debe tener acceso a tool específica."""
        rbac = RBACEngine()
        rbac.add_rule("admin", Permission.ALLOW, tool="admin_tool")
        assert rbac.check_access("admin", "srv", "admin_tool") is True
        assert rbac.check_access("user", "srv", "admin_tool") is False

    def test_server_scoped_rule(self):
        """Regla por servidor específico."""
        rbac = RBACEngine()
        rbac.add_rule("operator", Permission.ALLOW, server="db", tool="query")
        assert rbac.check_access("operator", "db", "query") is True
        assert rbac.check_access("operator", "api", "query") is False

    def test_wildcard_role(self):
        """Rol comodín debe aplicar a todos."""
        rbac = RBACEngine()
        rbac.add_rule("*", Permission.ALLOW, tool="public_tool")
        assert rbac.check_access("anyone", "srv", "public_tool") is True

    def test_deny_overrides_allow(self):
        """Denegación explícita debe sobreescribir permiso."""
        rbac = RBACEngine()
        rbac.add_rule("admin", Permission.ALLOW, tool="*")
        rbac.add_rule("admin", Permission.DENY, tool="forbidden")
        assert rbac.check_access("admin", "srv", "safe") is True
        assert rbac.check_access("admin", "srv", "forbidden") is False


# ── Tool Security ─────────────────────────────────────────────────────────

class TestToolSecurity:
    def test_default_insecure(self):
        """Por defecto las tools son inseguras."""
        cfg = ToolSecurityConfig()
        mode, _ = cfg.get_mode("any_tool")
        assert mode == ToolSecurityMode.INSECURE

    def test_secure_tool(self):
        """Tool marcada como secure debe devolver SECURE."""
        cfg = ToolSecurityConfig()
        cfg.add_rule("safe_tool", ToolSecurityMode.SECURE, "needs real data")
        mode, reason = cfg.get_mode("safe_tool")
        assert mode == ToolSecurityMode.SECURE
        assert "needs" in reason

    def test_insecure_tool(self):
        """Tool marcada como insecure debe devolver INSECURE."""
        cfg = ToolSecurityConfig()
        cfg.add_rule("external", ToolSecurityMode.INSECURE)
        assert cfg.is_secure("external") is False

    def test_wildcard_pattern(self):
        """Patrón comodín debe funcionar."""
        cfg = ToolSecurityConfig()
        cfg.add_rule("db:*", ToolSecurityMode.SECURE)
        assert cfg.is_secure("db:query") is True
        assert cfg.is_secure("api:call") is False

    def test_load_from_yaml(self):
        """Carga desde dict YAML debe funcionar."""
        data = {
            "by_default": "insecure",
            "secure_tools": [{"name": "db:*", "reason": "needs real IDs"}],
            "insecure_tools": [{"name": "notify:*", "reason": "external"}],
        }
        cfg = ToolSecurityConfig()
        cfg.load_from_yaml(data)
        assert cfg.is_secure("db:query") is True
        assert cfg.is_secure("notify:send") is False