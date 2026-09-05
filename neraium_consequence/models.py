"""Dependency-free public input and result types."""

from dataclasses import dataclass
from typing import Any, Literal, NotRequired, TypedDict

QuantificationStatus = Literal["quantified", "not_quantifiable"]
Direction = Literal["above_expected", "below_expected", "aligned"]


@dataclass(frozen=True)
class ResourceProfile:
    resource_type: str
    rate_unit: str
    cumulative_unit: str
    rate_period_seconds: float


class Observation(TypedDict):
    timestamp: str | float
    observed: float
    expected: float
    valid: NotRequired[bool]


class ConsequenceResult(TypedDict, total=False):
    status: QuantificationStatus
    resource_type: str | None
    profile_key: str
    direction: Direction
    cumulative_amount: float
    cumulative_unit: str
    duration_seconds: float
    start_timestamp: float
    end_timestamp: float
    observation_count: int
    contributing_interval_count: int
    skipped_interval_count: int
    source_relationship_ids: list[str]
    source_tag_ids: list[str]
    finding_id: str
    evidence_id: str
    analysis_run_id: str
    support_level: str | None
    methodology: str
    methodology_version: str
    limitations: list[str]
    statement: str
    reason: str
    provenance: dict[str, Any]
    rate_unit: str
    observed_rate: float
    expected_rate: float
    deviation_rate: float
    relative_deviation: float | None
    absolute_cumulative_amount: float
    contributing_intervals: list[dict[str, Any]]
    skipped_intervals: list[dict[str, Any]]
    valid_observation_count: int
    rejected_observation_count: int
    excluded_interval_count: int
    calculation_method: str
    evidence_boundary: str
