"""Allow/Deny lists and server allowlisting policies."""

import fnmatch
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from pathlib import Path


@dataclass
class DenyRule:
    """A rule denying access to a tool pattern."""
    pattern: str          # fnmatch pattern, e.g. "db:delete_*"
    reason: str           # Why this tool is denied
    server: str = "*"     # Server scope, "*" for all


@dataclass
class AllowRule:
    """A rule allowing access (used in allowlist mode)."""
    pattern: str
    server: str = "*"


@dataclass
class PolicyConfig:
    """Full policy configuration."""
    allowed_servers: List[str] = field(default_factory=list)
    """Whitelist of server URLs. Empty = allow all."""

    denied_tools: List[DenyRule] = field(default_factory=list)
    """Glob patterns for tools that are always denied."""

    allowed_tools: List[AllowRule] = field(default_factory=list)
    """If non-empty, only matching tools are allowed (allowlist mode)."""

    mode: str = "deny"
    """'deny' = deny-list mode, 'allow' = allowlist mode."""


class PolicyEngine:
    """Evaluates tool access against configured policies."""

    def __init__(self, config: Optional[PolicyConfig] = None):
        self.config = config or PolicyConfig()

    def is_server_allowed(self, server_url: str) -> bool:
        """Check if a server URL is in the allowlist."""
        if not self.config.allowed_servers:
            return True  # No restriction
        for pattern in self.config.allowed_servers:
            if fnmatch.fnmatch(server_url, pattern):
                return True
        return False

    def is_tool_allowed(self, tool_name: str, server_name: str = "*") -> bool:
        """Check if a tool call is allowed."""

        # Allowlist mode: only explicitly allowed tools
        if self.config.mode == "allow":
            if not self.config.allowed_tools:
                return False, "Empty allowlist = deny all"  # Empty allowlist = deny all
            for rule in self.config.allowed_tools:
                if fnmatch.fnmatch(tool_name, rule.pattern):
                    if rule.server == "*" or rule.server == server_name:
                        return True, ""
            return False, "Not in allowlist"

        # Deny mode: check deny list
        for rule in self.config.denied_tools:
            if fnmatch.fnmatch(tool_name, rule.pattern):
                if rule.server == "*" or rule.server == server_name:
                    return False, rule.reason
        return True, ""

    def load_from_yaml(self, path: Path) -> None:
        """Load policy configuration from a YAML file."""
        import yaml
        with open(path) as f:
            data = yaml.safe_load(f)

        policies = data.get("policies", {})

        self.config.allowed_servers = policies.get("allowed_servers", [])
        self.config.mode = policies.get("mode", "deny")
        self.config.denied_tools = [
            DenyRule(pattern=d["name"], reason=d.get("reason", ""), server=d.get("server", "*"))
            for d in policies.get("denied_tools", [])
        ]
        self.config.allowed_tools = [
            AllowRule(pattern=a["name"], server=a.get("server", "*"))
            for a in policies.get("allowed_tools", [])
        ]