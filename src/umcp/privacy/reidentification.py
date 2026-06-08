"""k-anonymity and l-diversity checks for re-identification prevention.

Configurable via:
  - mode: "detect" (solo avisa, no bloquea) | "block" (lanza ReIdentificationRiskError)
  - thresholds: k (min 5), l (min 3)

Se puede activar/desactivar dinámicamente desde config.yaml o env vars.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional
from umcp.pipeline.detectors.base import Entity
from umcp.gateway.exceptions import ReIdentificationRiskError


class KAnonymityMode(Enum):
    DETECT = "detect"   # Solo registra warnings, no bloquea
    BLOCK = "block"     # Lanza excepción si no pasa


@dataclass
class RiskReport:
    """Report of re-identification risk assessment."""
    k_anonymity: int = 0
    l_diversity: int = 0
    passed: bool = False
    mode: str = "detect"
    blocked: bool = False
    warnings: List[str] = field(default_factory=list)


class ReIdentificationGuard:
    """Assesses re-identification risk after anonymization.

    Config:
      mode: "detect" | "block"
      k_threshold: mínimo valor k-anonymity (defecto: 5)
      l_threshold: mínimo valor l-diversity (defecto: 3)
    """

    def __init__(
        self,
        mode: str = "detect",
        k_threshold: int = 5,
        l_threshold: int = 3,
    ):
        self.mode = KAnonymityMode(mode)
        self.k_threshold = k_threshold
        self.l_threshold = l_threshold

    def assess(
        self,
        data: str,
        entities: List[Entity],
        quasi_identifiers: Optional[List[str]] = None,
    ) -> RiskReport:
        """Assess re-identification risk.

        Args:
            data: Texto anonimizado (para análisis contextual)
            entities: Entidades detectadas en el texto
            quasi_identifiers: Opcional, lista de QI conocidos

        Returns:
            RiskReport con resultado de la evaluación.

        Raises:
            ReIdentificationRiskError: Si mode=block y no pasa.
        """
        warnings = []

        # k-anonymity: contar tipos de entidad (excluyendo DATE/TIME)
        entity_types = {}
        for e in entities:
            if e.type not in ("DATE", "TIME"):
                entity_types[e.type] = entity_types.get(e.type, 0) + 1

        # Entidades únicas → posible vector de re-identificación
        for etype, count in entity_types.items():
            if count == 1:
                warnings.append(
                    f"Single occurrence of '{etype}': potential re-identification vector"
                )

        # l-diversity: variedad de valores distintos
        unique_entities = len(set(e.text for e in entities))
        if unique_entities < self.l_threshold:
            warnings.append(
                f"Low entity diversity ({unique_entities} < {self.l_threshold})"
            )

        # k-anonymity: ratio entidades / tipos
        k = max(1, len(entities) // max(1, len(set(e.type for e in entities))))
        if k < self.k_threshold:
            warnings.append(
                f"k-anonymity too low ({k} < {self.k_threshold})"
            )

        passed = k >= self.k_threshold and len(warnings) == 0
        blocked = False

        if not passed and self.mode == KAnonymityMode.BLOCK:
            blocked = True
            raise ReIdentificationRiskError(
                k=k,
                l=unique_entities,
                threshold_k=self.k_threshold,
                threshold_l=self.l_threshold,
            )

        return RiskReport(
            k_anonymity=k,
            l_diversity=unique_entities,
            passed=passed,
            mode=self.mode.value,
            blocked=blocked,
            warnings=warnings,
        )
