"""Tool security classification — secure vs insecure tools."""

from dataclasses import dataclass, field
from typing import List, Optional
from enum import Enum


class ToolSecurityMode(Enum):
    SECURE = "secure"        # Deanonymize args → re-anonymize response
    INSECURE = "insecure"    # Everything stays anonymized


@dataclass
class ToolSecurityRule:
    """Defines the security mode for a tool pattern."""
    pattern: str                    # fnmatch pattern
    mode: ToolSecurityMode
    reason: str = ""


class ToolSecurityConfig:
    """Configuration for tool security classification."""

    def __init__(self):
        self._rules: List[ToolSecurityRule] = []
        self.default_mode: ToolSecurityMode = ToolSecurityMode.INSECURE

    def add_rule(self, pattern: str, mode: ToolSecurityMode, reason: str = "") -> None:
        self._rules.append(ToolSecurityRule(pattern=pattern, mode=mode, reason=reason))

    def get_mode(self, tool_name: str) -> tuple[ToolSecurityMode, str]:
        """Determine the security mode for a tool name."""
        import fnmatch
        for rule in self._rules:
            if fnmatch.fnmatch(tool_name, rule.pattern):
                return rule.mode, rule.reason
        return self.default_mode, "default"

    def is_secure(self, tool_name: str) -> bool:
        return self.get_mode(tool_name)[0] == ToolSecurityMode.SECURE

    def load_from_yaml(self, data: dict) -> None:
        """Load rules from a YAML config section."""
        self.default_mode = ToolSecurityMode(
            data.get("by_default", "insecure")
        )
        for entry in data.get("secure_tools", []):
            self.add_rule(
                pattern=entry["name"],
                mode=ToolSecurityMode.SECURE,
                reason=entry.get("reason", ""),
            )
        for entry in data.get("insecure_tools", []):
            self.add_rule(
                pattern=entry["name"],
                mode=ToolSecurityMode.INSECURE,
                reason=entry.get("reason", ""),
            )


# Singleton
tool_security = ToolSecurityConfig()