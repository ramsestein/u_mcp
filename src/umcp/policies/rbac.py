"""Role-based access control for tool permissions."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from enum import Enum


class Permission(Enum):
    ALLOW = "allow"
    DENY = "deny"


@dataclass
class RBACRule:
    """Permission rule for a role on a (server, tool) pair."""
    role: str
    server: str = "*"
    tool: str = "*"
    permission: Permission = Permission.DENY


class RBACEngine:
    """Role-based access control engine."""

    def __init__(self):
        self._rules: List[RBACRule] = []
        self.default_permission: Permission = Permission.DENY

    def add_rule(
        self,
        role: str,
        permission: Permission,
        server: str = "*",
        tool: str = "*",
    ) -> None:
        self._rules.append(RBACRule(
            role=role, server=server, tool=tool, permission=permission
        ))

    def check_access(self, role: str, server: str, tool: str) -> bool:
        """Check if a role can access a tool on a server."""
        import fnmatch
        # Most specific rules win (evaluated in order)
        for rule in reversed(self._rules):
            if (rule.role == role or rule.role == "*"):
                if fnmatch.fnmatch(server, rule.server):
                    if fnmatch.fnmatch(tool, rule.tool):
                        return rule.permission == Permission.ALLOW
        return self.default_permission == Permission.ALLOW


# Singleton
rbac = RBACEngine()