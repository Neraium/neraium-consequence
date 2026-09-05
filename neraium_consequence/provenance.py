"""Detached, deterministic input evidence suitable for strict JSON serialization."""

from collections.abc import Mapping
from math import isfinite
from typing import Any

METHODOLOGY = "timestamp_aware_trapezoidal_integration"
METHODOLOGY_VERSION = "1.0.0"
SOURCE_IMPLEMENTATION = (
    "https://github.com/Neraium/Neraium-1.0/blob/"
    "74a7d4bf86d2f55f51a8a4cded2bef612cffbe3e/"
    "backend/app/services/consequence_quantification.py"
)


def snapshot(value: Any) -> Any:
    """Copy JSON-shaped evidence; encode rejected nonfinite floats by exact hex value.

    Non-JSON Python objects are programming errors, not observation evidence.
    Tagged floats occur only in this input snapshot, never in calculated values.
    """
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        return value if isfinite(value) else {"nonfinite_float": value.hex()}
    if isinstance(value, Mapping):
        if not all(isinstance(key, str) for key in value):
            raise TypeError("Evidence object keys must be strings.")
        return {key: snapshot(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [snapshot(item) for item in value]
    raise TypeError("Evidence must contain only JSON-shaped values.")


def identifiers(values: list[str] | None) -> list[str]:
    if values is None:
        return []
    if not isinstance(values, list) or not all(isinstance(item, str) for item in values):
        raise TypeError("Source identifiers must be lists of strings.")
    return values.copy()
