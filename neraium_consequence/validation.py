"""Observation validation that retains barriers instead of dropping bad rows."""

from collections import Counter
from collections.abc import Mapping
from datetime import UTC, datetime
from math import isfinite
from typing import Any


def finite_number(value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        raise ValueError("not a numeric rate")
    number = float(value)
    if not isfinite(number):
        raise ValueError("non-finite rate")
    return number


def timestamp_seconds(value: Any) -> float:
    if isinstance(value, bool):
        raise ValueError("boolean timestamp")
    if isinstance(value, (int, float)):
        number = finite_number(value)
        # Reject epochs beyond the supported calendar range (including millisecond
        # epochs that are accidentally passed as seconds).
        datetime.fromtimestamp(number, UTC)
        return number
    if not isinstance(value, str) or not value.strip():
        raise ValueError("missing timestamp")
    parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.timestamp()


def prepare(observations: list[Any]) -> tuple[list[dict[str, Any]], bool]:
    rows = []
    unknown_time = False
    for index, item in enumerate(observations):
        row: dict[str, Any] = {"input_index": index, "valid": False, "timestamp": None}
        rows.append(row)
        if not isinstance(item, Mapping):
            row["reason"] = "invalid_observation"
            unknown_time = True
            continue
        try:
            row["timestamp"] = timestamp_seconds(item.get("timestamp"))
        except (ValueError, TypeError, OverflowError, OSError):
            row["reason"] = "malformed_timestamp"
            unknown_time = True
            continue
        try:
            if item.get("valid", True) is not True:
                raise ValueError("quality gate")
            row["observed"] = finite_number(item.get("observed"))
            row["expected"] = finite_number(item.get("expected"))
            row["residual"] = finite_number(row["observed"] - row["expected"])
            row["valid"] = True
        except (ValueError, TypeError, OverflowError):
            row["reason"] = "invalid_observation"
    counts = Counter(row["timestamp"] for row in rows if row["timestamp"] is not None)
    for row in rows:
        if row["timestamp"] is not None and counts[row["timestamp"]] > 1:
            row.update(valid=False, reason="duplicate_timestamp")
    rows.sort(key=lambda row: (row["timestamp"] is None, row["timestamp"] or 0))
    return rows, unknown_time
