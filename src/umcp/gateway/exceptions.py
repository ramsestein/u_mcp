"""Exception hierarchy for the uMCP framework."""

from fastapi import HTTPException


class uMCPError(Exception):
    """Base exception for uMCP."""
    pass


class AuthenticationError(HTTPException):
    def __init__(self, detail: str = "Invalid or missing API key"):
        super().__init__(status_code=401, detail=detail)


class AuthorizationError(HTTPException):
    def __init__(self, detail: str = "Insufficient permissions"):
        super().__init__(status_code=403, detail=detail)


class PolicyViolationError(HTTPException):
    def __init__(self, detail: str, reason: str = ""):
        super().__init__(status_code=403, detail={"error": detail, "reason": reason})


class ToolNotFoundError(HTTPException):
    def __init__(self, tool_name: str):
        super().__init__(status_code=404, detail=f"Tool '{tool_name}' not found")


class ServerNotFoundError(HTTPException):
    def __init__(self, server_name: str):
        super().__init__(status_code=404, detail=f"Server '{server_name}' not found")


class EncryptionError(uMCPError):
    """Raised when encryption/decryption fails."""
    pass


class ReIdentificationRiskError(uMCPError):
    """Raised when k-anonymity or l-diversity check fails."""
    def __init__(self, k: int, l: int, threshold_k: int = 5, threshold_l: int = 3):
        self.k = k
        self.l = l
        super().__init__(
            f"Re-identification risk: k={k} < {threshold_k} or l={l} < {threshold_l}"
        )


class PIILeakError(uMCPError):
    """Raised when PII is detected in output that should be clean."""
    pass


class ChainIntegrityError(uMCPError):
    """Raised when audit chain validation fails."""
    pass