"""Signed timestamp-aware integration extracted and hardened from platform PR #124."""

from collections.abc import Iterable, Mapping
from math import fsum, isfinite
from typing import Any

from .models import ConsequenceResult, Direction
from .profiles import DEFAULT_MAX_GAP_SECONDS, RESOURCE_PROFILES
from .provenance import METHODOLOGY, METHODOLOGY_VERSION, identifiers, snapshot
from .validation import finite_number, prepare

INSUFFICIENT_STATEMENT = "Consequence not quantifiable from available evidence."


def quantify_consequence(
    observations: Iterable[Mapping[str, Any] | Any] | None,
    *,
    profile_key: str,
    max_gap_seconds: float | None = None,
    source_relationship_ids: list[str] | None = None,
    source_tag_ids: list[str] | None = None,
    support_level: str | None = None,
    finding_id: str | None = None,
    evidence_id: str | None = None,
    analysis_run_id: str | None = None,
) -> ConsequenceResult:
    """Integrate aligned rates; never fill, extrapolate, or infer expected behavior.

    See docs/methodology.md for gap, duplicate, timestamp, and provenance rules.
    Missing evidence returns ``not_quantifiable`` without a numeric amount.
    """
    if not isinstance(profile_key, str):
        raise TypeError("profile_key must be a string.")
    if support_level is not None and not isinstance(support_level, str):
        raise TypeError("support_level must be a string or None.")
    supplied = list(observations) if observations is not None else []
    original = snapshot(supplied)
    profile = RESOURCE_PROFILES.get(profile_key)
    result: ConsequenceResult = {
        "status": "not_quantifiable",
        "profile_key": profile_key,
        "resource_type": profile.resource_type if profile else None,
        "source_relationship_ids": identifiers(source_relationship_ids),
        "source_tag_ids": identifiers(source_tag_ids),
        "support_level": support_level,
        "methodology": METHODOLOGY,
        "methodology_version": METHODOLOGY_VERSION,
        "observation_count": len(supplied),
        "contributing_interval_count": 0,
        "skipped_interval_count": 0,
        "limitations": [],
        "statement": INSUFFICIENT_STATEMENT,
        "provenance": {"observations": original, "max_gap_seconds": snapshot(max_gap_seconds)},
    }
    for key, value in (
        ("finding_id", finding_id),
        ("evidence_id", evidence_id),
        ("analysis_run_id", analysis_run_id),
    ):
        if value is not None:
            if not isinstance(value, str):
                raise TypeError(f"{key} must be a string or None.")
            result[key] = value  # type: ignore[literal-required]

    def insufficient(reason: str) -> ConsequenceResult:
        result["reason"] = reason
        result["limitations"].append(reason)
        return result

    if profile is None:
        return insufficient(f"Unknown resource profile: {profile_key}")
    try:
        gap = DEFAULT_MAX_GAP_SECONDS if max_gap_seconds is None else finite_number(max_gap_seconds)
        if gap <= 0:
            raise ValueError("nonpositive gap")
    except (ValueError, TypeError, OverflowError):
        return insufficient("A finite positive maximum supported gap is required.")
    result["provenance"]["effective_max_gap_seconds"] = gap
    rows, unknown_time = prepare(supplied)
    result["provenance"]["observation_validation"] = [
        {key: row[key] for key in ("input_index", "timestamp", "valid", "reason") if key in row}
        for row in rows
    ]
    result["valid_observation_count"] = sum(row["valid"] for row in rows)
    result["rejected_observation_count"] = len(rows) - result["valid_observation_count"]
    if unknown_time:
        return insufficient("An observation cannot be placed in time; continuity is unsupported.")

    intervals = []
    skipped = []
    for left, right in zip(rows, rows[1:], strict=False):
        dt = right["timestamp"] - left["timestamp"]
        interval = {
            "start_timestamp": left["timestamp"],
            "end_timestamp": right["timestamp"],
            "duration_seconds": dt,
            "source_observation_indices": [left["input_index"], right["input_index"]],
        }
        reason = (
            "invalid_endpoint"
            if not left["valid"] or not right["valid"]
            else "nonpositive_duration"
            if dt <= 0
            else "unsupported_gap"
            if dt > gap
            else None
        )
        if reason:
            skipped.append({**interval, "reason": reason})
            continue
        a, b = left["residual"], right["residual"]
        scale = dt / profile.rate_period_seconds
        amount = (a / 2.0 + b / 2.0) * scale
        # Integrate the absolute piecewise-linear residual exactly at zero crossings.
        absolute = (abs(a) / 2.0 + abs(b) / 2.0) * scale
        if (a < 0 < b) or (b < 0 < a):
            largest, smallest = max(abs(a), abs(b)), min(abs(a), abs(b))
            ratio = smallest / largest
            absolute = (largest / 2.0) * ((1 + ratio * ratio) / (1 + ratio)) * scale
        interval.update(
            start_deviation_rate=a,
            end_deviation_rate=b,
            integrated_amount=amount,
            absolute_integrated_amount=absolute,
            observed_integral=(left["observed"] / 2 + right["observed"] / 2) * dt,
            expected_integral=(left["expected"] / 2 + right["expected"] / 2) * dt,
        )
        intervals.append(interval)
    result.update(
        {
            "contributing_interval_count": len(intervals),
            "skipped_interval_count": len(skipped),
            "excluded_interval_count": len(skipped),
            "skipped_intervals": skipped,
        }
    )
    if skipped:
        result["limitations"].append("Unsupported intervals were excluded; coverage is partial.")
    if not intervals:
        return insufficient("No valid contiguous intervals support accumulation.")
    try:
        total = fsum(item["integrated_amount"] for item in intervals)
        absolute_total = fsum(item["absolute_integrated_amount"] for item in intervals)
        duration = fsum(item["duration_seconds"] for item in intervals)
        observed = fsum(item["observed_integral"] for item in intervals) / duration
        expected = fsum(item["expected_integral"] for item in intervals) / duration
        deviation = observed - expected
        if not all(
            isfinite(value)
            for value in (total, absolute_total, duration, observed, expected, deviation)
        ):
            raise OverflowError
    except (OverflowError, ValueError):
        result["contributing_interval_count"] = 0
        return insufficient("Numerical range exceeds finite integration support.")
    direction: Direction = (
        "above_expected" if total > 0 else "below_expected" if total < 0 else "aligned"
    )
    relative = deviation / abs(expected) if expected else None
    if relative is not None and not isfinite(relative):
        relative = None
    if any(
        item["start_deviation_rate"] < 0 or item["end_deviation_rate"] < 0 for item in intervals
    ) and any(
        item["start_deviation_rate"] > 0 or item["end_deviation_rate"] > 0 for item in intervals
    ):
        result["limitations"].append("Signed net amount includes deviations in both directions.")
    for item in intervals:
        del item["observed_integral"], item["expected_integral"]
    result.update(
        {
            "status": "quantified",
            "direction": direction,
            "cumulative_amount": total,
            "cumulative_unit": profile.cumulative_unit,
            "duration_seconds": duration,
            "start_timestamp": intervals[0]["start_timestamp"],
            "end_timestamp": intervals[-1]["end_timestamp"],
            "rate_unit": profile.rate_unit,
            "observed_rate": observed,
            "expected_rate": expected,
            "deviation_rate": deviation,
            "relative_deviation": relative,
            "absolute_cumulative_amount": absolute_total,
            "contributing_intervals": intervals,
            "calculation_method": (
                "timestamp-aware trapezoidal integration of observed-minus-expected rate"
            ),
            "evidence_boundary": (
                "Associated measurable deviation only; no cause attribution is performed."
            ),
            "statement": f"{profile.resource_type.replace('_', ' ').capitalize()} "
            "observed-minus-expected "
            f"amount: {total:.12g} {profile.cumulative_unit} across {duration:.12g} seconds.",
        }
    )
    return result
