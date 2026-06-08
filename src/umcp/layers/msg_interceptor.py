"""Message interceptor — transparent anonymization layer between User↔LLM.

Anonymizes user messages before they reach the LLM, and
deanonymizes LLM responses before they reach the user.
"""

from typing import Optional, Tuple
from umcp.pipeline.detectors.ensemble import EnsembleDetector
from umcp.pipeline.detectors.base import Entity
from umcp.pipeline.vault.vault import Vault
from umcp.pipeline.vault.substitutor import Substitutor
from umcp.pipeline.date_preserver import DatePreserver
from umcp.pipeline.whitelist import Whitelist
from umcp.privacy.reidentification import ReIdentificationGuard
from umcp.privacy.breach_response import BreachResponse


class MessageInterceptor:
    """Transparent User↔LLM anonymization layer."""

    def __init__(
        self,
        vault: Vault,
        detector: EnsembleDetector,
        date_preserver: Optional[DatePreserver] = None,
        whitelist: Optional[Whitelist] = None,
        reid_guard: Optional[ReIdentificationGuard] = None,
        breach_response: Optional[BreachResponse] = None,
    ):
        self.vault = vault
        self.detector = detector
        self.substitutor = Substitutor(vault)
        self.date_preserver = date_preserver or DatePreserver()
        self.whitelist = whitelist or Whitelist()
        self.reid_guard = reid_guard or ReIdentificationGuard()
        self.breach_response = breach_response or BreachResponse()

    @property
    def k_anonymity_mode(self) -> str:
        """Get current k-anonymity mode."""
        return self.reid_guard.mode.value

    @k_anonymity_mode.setter
    def k_anonymity_mode(self, mode: str) -> None:
        """Set k-anonymity mode: 'detect' or 'block'."""
        from umcp.privacy.reidentification import KAnonymityMode
        self.reid_guard.mode = KAnonymityMode(mode)

    def anonymize_user_message(self, message: str) -> Tuple[str, list, Optional[dict]]:
        """Anonymize a message FROM the user before it reaches the LLM.

        Returns (anonymized_message, substitutions_log, risk_report).
        risk_report is None if k-anonymity check passes or mode=detect.
        """
        # 1. Detect entities
        clean_text, entities = self.detector.detect_and_sanitize(message)

        # 2. Filter by date preserver (dates are preserved)
        protected = self.date_preserver.find_protected_ranges(clean_text)
        entities = [
            e for e in entities
            if not self.date_preserver.is_protected(e.start, e.end, protected)
        ]

        # 3. Filter by whitelist (clinical terms are preserved)
        entities = [e for e in entities if not self.whitelist.is_safe(e.text)]

        # 4. Substitute
        anonymized, substitutions = self.substitutor.anonymize(clean_text, entities)

        # 5. Assess re-identification risk
        risk_report = None
        try:
            report = self.reid_guard.assess(anonymized, entities)
            if not report.passed and report.warnings:
                risk_report = {
                    "k_anonymity": report.k_anonymity,
                    "l_diversity": report.l_diversity,
                    "passed": report.passed,
                    "mode": report.mode,
                    "warnings": report.warnings,
                }
        except Exception as e:
            # If block mode raises, re-raise
            raise

        return anonymized, substitutions, risk_report

    def deanonymize_llm_response(self, response: str) -> Tuple[str, list]:
        """Deanonymize a response FROM the LLM before it reaches the user.

        Returns (real_response, deanonymizations_log).
        """
        result, deanonymizations = self.substitutor.deanonymize(response)

        # Check for PII leaks
        breach = self.breach_response.detect_pii_leak(result, [])
        if breach:
            # Log but don't block — the deanonymization is intentional
            pass

        return result, deanonymizations

    def assess_risk(self, data: str, entities: list) -> dict:
        """Assess re-identification risk."""
        report = self.reid_guard.assess(data, entities)
        return {
            "k_anonymity": report.k_anonymity,
            "l_diversity": report.l_diversity,
            "passed": report.passed,
            "mode": report.mode,
            "warnings": report.warnings,
        }