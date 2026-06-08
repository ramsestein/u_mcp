"""Tool dispatcher — routes tool calls based on security classification.

Secure tools: deanonymize arguments, execute with real data,
             then re-anonymize the response for the LLM.
Insecure tools: everything stays anonymized.
"""

from typing import Any, Dict, Optional, Tuple
from umcp.pipeline.detectors.ensemble import EnsembleDetector
from umcp.pipeline.vault.vault import Vault
from umcp.pipeline.vault.substitutor import Substitutor
from umcp.policies.tool_security import tool_security, ToolSecurityMode


class ToolDispatcher:
    """Dispatches tool calls with appropriate anonymization handling."""

    def __init__(
        self,
        vault: Vault,
        detector: EnsembleDetector,
    ):
        self.vault = vault
        self.detector = detector
        self.substitutor = Substitutor(vault)

    async def dispatch(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        server_name: str = "default",
    ) -> Tuple[Dict[str, Any], dict]:
        """Dispatch a tool call based on security classification.

        Args:
            tool_name: Name of the tool being called.
            arguments: Arguments (from LLM, already anonymized).
            server_name: Server hosting the tool.

        Returns:
            (response, dispatch_log)
        """
        # Determine security mode
        mode, reason = tool_security.get_mode(tool_name)
        is_secure = mode == ToolSecurityMode.SECURE

        dispatch_log = {
            "tool_name": tool_name,
            "server": server_name,
            "mode": mode.value,
            "reason": reason,
            "deanonymized_args": [],
            "reanonymized_response": [],
        }

        if is_secure:
            # TOOL SEGURA: Deanonymize arguments
            real_args = {}
            for key, value in arguments.items():
                if isinstance(value, str):
                    real_value, deanons = self.substitutor.deanonymize(value)
                    real_args[key] = real_value
                    for d in deanons:
                        dispatch_log["deanonymized_args"].append({
                            "arg": key,
                            "surrogate": d["surrogate"],
                            "value": d["original"],
                        })
                else:
                    real_args[key] = value

            # Here we would call the actual tool with real_args
            # For now, return a placeholder
            response = {"status": "secure_tool_executed", "args": real_args}

            # Re-anonymize the response for the LLM
            response_str = str(response)
            anonymized_resp, reanons = self.substitutor.anonymize(
                response_str, self.detector.detect(response_str)
            )
            for r in reanons:
                dispatch_log["reanonymized_response"].append(r)

            return eval(anonymized_resp) if anonymized_resp.startswith("{") else {"result": anonymized_resp}, dispatch_log

        else:
            # TOOL INSEGURA: Arguments are already anonymized, pass through
            # Here we would call the actual tool with arguments as-is
            response = {"status": "insecure_tool_executed", "args": arguments}
            return response, dispatch_log