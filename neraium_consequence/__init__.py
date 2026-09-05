"""Neraium's standalone, evidence-supported consequence quantification API."""

from .models import ConsequenceResult, Observation, QuantificationStatus, ResourceProfile
from .profiles import DEFAULT_MAX_GAP_SECONDS, RESOURCE_PROFILES
from .provenance import METHODOLOGY, METHODOLOGY_VERSION
from .quantifier import quantify_consequence

__version__ = "1.0.0"
__all__ = [
    "quantify_consequence",
    "ConsequenceResult",
    "Observation",
    "QuantificationStatus",
    "ResourceProfile",
    "RESOURCE_PROFILES",
    "DEFAULT_MAX_GAP_SECONDS",
    "METHODOLOGY",
    "METHODOLOGY_VERSION",
    "__version__",
]
