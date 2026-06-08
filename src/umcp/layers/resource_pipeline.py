"""Resource pipeline — intercepts resource access, anonymizes before LLM context.

When the LLM requests a resource (data source), this pipeline
anonymizes it before the data enters the LLM's context window.
"""

from typing import Any, Dict, Optional, Tuple
from umcp.pipeline.detectors.ensemble import EnsembleDetector
from umcp.pipeline.vault.vault import Vault
from umcp.pipeline.vault.substitutor import Substitutor
from umcp.pipeline.date_preserver import DatePreserver
from umcp.pipeline.whitelist import Whitelist


class ResourcePipeline:
    """Intercepts resource access and anonymizes data for LLM context."""

    def __init__(
        self,
        vault: Vault,
        detector: EnsembleDetector,
        date_preserver: Optional[DatePreserver] = None,
        whitelist: Optional[Whitelist] = None,
    ):
        self.vault = vault
        self.detector = detector
        self.substitutor = Substitutor(vault)
        self.date_preserver = date_preserver or DatePreserver()
        self.whitelist = whitelist or Whitelist()
        self._cache: Dict[str, str] = {}

    async def process_resource(
        self, resource_id: str, raw_data: str
    ) -> Tuple[str, dict]:
        """Process a resource: anonymize data for LLM context.

        Args:
            resource_id: Identifier for this resource (for caching).
            raw_data: The raw data from the resource.

        Returns:
            (anonymized_data, processing_log)
        """
        # Check cache
        cache_key = f"{resource_id}:{hash(raw_data)}"
        if cache_key in self._cache:
            return self._cache[cache_key], {"cached": True}

        # Detect and anonymize
        clean_text, entities = self.detector.detect_and_sanitize(raw_data)

        protected = self.date_preserver.find_protected_ranges(clean_text)
        entities = [
            e for e in entities
            if not self.date_preserver.is_protected(e.start, e.end, protected)
        ]
        entities = [e for e in entities if not self.whitelist.is_safe(e.text)]

        anonymized, substitutions = self.substitutor.anonymize(clean_text, entities)

        log = {
            "resource_id": resource_id,
            "entity_count": len(substitutions),
            "substitutions": substitutions,
            "cached": False,
        }

        # Cache the result
        self._cache[cache_key] = anonymized

        return anonymized, log

    def clear_cache(self) -> None:
        """Clear the resource cache."""
        self._cache.clear()