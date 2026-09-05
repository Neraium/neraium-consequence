import json
import os
import time
from copy import deepcopy

import pytest

from neraium_consequence import RESOURCE_PROFILES, quantify_consequence


def rows(times=(0, 60, 120), deviations=(10, 10, 10)):
    return [
        dict(timestamp=t, observed=20 + d, expected=20)
        for t, d in zip(times, deviations, strict=False)
    ]


def quantify(observations=None, **kwargs):
    return quantify_consequence(observations, profile_key="water_gpm", **kwargs)


def test_fixed_cadence():
    result = quantify(rows())
    assert result["cumulative_amount"] == 20
    assert result["duration_seconds"] == 120
    assert result["contributing_interval_count"] == 2
    assert (result["start_timestamp"], result["end_timestamp"]) == (0, 120)


def test_original_irregular_cadence_regression():
    result = quantify(rows((0, 60, 180), (20, 22, 24)))
    assert result["cumulative_amount"] == pytest.approx(67)
    assert result["duration_seconds"] == 180
    assert result["observed_rate"] == pytest.approx(20 + 67 / 3)


@pytest.mark.parametrize(
    "profile,unit,period",
    [
        ("water_gpm", "gal", 60),
        ("electricity_kw", "kWh", 3600),
        ("steam_lb_per_hr", "lb", 3600),
        ("chemical_feed_gal_per_hr", "gal", 3600),
        ("compressed_air_scfm", "scf", 60),
        ("steam_lb_hr", "lb", 3600),
        ("chemical_gal_hr", "gal", 3600),
    ],
)
def test_profiles(profile, unit, period):
    result = quantify_consequence(rows((0, period), (14.2, 14.2)), profile_key=profile)
    assert result["cumulative_amount"] == pytest.approx(14.2)
    assert result["cumulative_unit"] == unit
    assert result["profile_key"] == profile


@pytest.mark.parametrize(
    "deviations,total,direction",
    [
        ((5, 5, 5), 10, "above_expected"),
        ((-5, -5, -5), -10, "below_expected"),
        ((0, 0, 0), 0, "aligned"),
        ((-10, 0, 10), 0, "aligned"),
        ((-10, 10, 10), 10, "above_expected"),
        ((10, -10, -10), -10, "below_expected"),
    ],
)
def test_sign(deviations, total, direction):
    result = quantify(rows(deviations=deviations))
    assert result["status"] == "quantified"
    assert result["cumulative_amount"] == pytest.approx(total)
    assert result["direction"] == direction


def test_absolute_crossing_integral():
    result = quantify(rows((0, 60), (-10, 10)))
    assert result["cumulative_amount"] == 0
    assert result["absolute_cumulative_amount"] == pytest.approx(5)
    assert "both directions" in result["limitations"][0]


@pytest.mark.parametrize(
    "times",
    [
        (0, 60, 120),
        (0.25, 60.25, 120.25),
        ("2026-09-05T00:00:00Z", "2026-09-05T00:01:00Z", "2026-09-05T00:02:00Z"),
        ("2026-09-05T02:00:00+02:00", "2026-09-05T02:01:00+02:00", "2026-09-05T02:02:00+02:00"),
        ("2026-09-05T00:00:00", "2026-09-05T00:01:00", "2026-09-05T00:02:00"),
    ],
)
def test_timestamps(times):
    assert quantify(rows(times))["cumulative_amount"] == 20


def test_timezone_independent():
    if not hasattr(time, "tzset"):
        pytest.skip("tzset unavailable")
    old = os.environ.get("TZ")
    try:
        outcomes = []
        for zone in ("UTC", "America/Los_Angeles"):
            os.environ["TZ"] = zone
            time.tzset()
            outcomes.append(quantify(rows(("2026-09-05T00:00:00", "2026-09-05T00:01:00"))))
        assert outcomes[0] == outcomes[1]
    finally:
        if old is None:
            os.environ.pop("TZ", None)
        else:
            os.environ["TZ"] = old
        time.tzset()


@pytest.mark.parametrize(
    "changes",
    [
        {"valid": False},
        {"valid": 0},
        {"valid": None},
        {"valid": "false"},
        {"observed": None},
        {"expected": None},
        {"observed": "bad"},
        {"observed": float("nan")},
        {"expected": float("inf")},
        {"observed": True},
        {"observed": 1e308, "expected": -1e308},
    ],
)
def test_invalid_rows_are_barriers_without_explicit_gap(changes):
    observations = rows()
    observations[1].update(changes)
    result = quantify(observations)
    assert result["status"] == "not_quantifiable"
    assert "cumulative_amount" not in result
    assert result["skipped_interval_count"] == 2
    json.dumps(result, allow_nan=False)


def test_partial_coverage_does_not_bridge_invalid():
    observations = rows((0, 60, 120, 180, 240), (10,) * 5)
    observations[2]["valid"] = False
    result = quantify(observations)
    assert result["cumulative_amount"] == 20
    assert result["duration_seconds"] == 120
    assert result["skipped_interval_count"] == 2
    assert result["observation_count"] == 5
    assert result["rejected_observation_count"] == 1


@pytest.mark.parametrize(
    "observations",
    [
        None,
        [],
        [{}],
        [None],
        rows()[:1],
        [{"timestamp": 0, "valid": False}, {"timestamp": 60, "valid": False}],
        [{"timestamp": 0, "observed": 20}, {"timestamp": 60, "expected": 20}],
    ],
)
def test_insufficient_never_zero(observations):
    result = quantify(observations)
    assert result["status"] == "not_quantifiable"
    assert result["statement"] == "Consequence not quantifiable from available evidence."
    assert "cumulative_amount" not in result
    json.dumps(result, allow_nan=False)


@pytest.mark.parametrize(
    "timestamp",
    [
        None,
        "",
        "garbage",
        "2026-99-05",
        True,
        float("nan"),
        float("inf"),
        1e300,
        1700000000000,
        [],
        {},
    ],
)
def test_malformed_timestamp_cannot_be_silently_dropped(timestamp):
    observations = rows()
    observations[1]["timestamp"] = timestamp
    result = quantify(observations)
    assert result["status"] == "not_quantifiable"
    assert "placed in time" in result["reason"]
    json.dumps(result, allow_nan=False)


def test_large_gap_default_and_explicit_limit():
    assert quantify(rows((0, 7200), (10, 10)))["status"] == "not_quantifiable"
    assert quantify(rows((0, 120), (10, 10)), max_gap_seconds=90)["status"] == "not_quantifiable"
    assert quantify(rows((0, 120), (10, 10)), max_gap_seconds=120)["cumulative_amount"] == 20


@pytest.mark.parametrize("gap", [0, -1, float("inf"), float("nan"), "bad", True])
def test_invalid_gap(gap):
    result = quantify(rows(), max_gap_seconds=gap)
    assert result["status"] == "not_quantifiable"
    json.dumps(result, allow_nan=False)


def test_gap_excluded_duration_and_window():
    result = quantify(rows((0, 60, 7200, 7260), (10,) * 4))
    assert result["duration_seconds"] == 120
    assert result["end_timestamp"] == 7260
    assert result["cumulative_amount"] == 20
    assert result["skipped_intervals"][0]["reason"] == "unsupported_gap"


def test_duplicate_groups_are_ambiguous_even_if_equal():
    observations = rows((0, 60, 60, 120), (10,) * 4)
    assert quantify(observations)["status"] == "not_quantifiable"
    observations[2]["observed"] = 1000
    assert quantify(observations)["status"] == "not_quantifiable"


def test_unsorted_and_unsorted_invalid():
    observations = rows((120, 0, 60), (10, 10, 10))
    result = quantify(observations)
    assert result["cumulative_amount"] == 20
    assert result["contributing_intervals"][0]["source_observation_indices"] == [1, 2]
    observations[2]["valid"] = False
    assert quantify(observations)["status"] == "not_quantifiable"


def test_original_and_identifier_provenance_detached_and_exact():
    observations = rows()
    observations[0]["timestamp"] = "1970-01-01T01:00:00+01:00"
    observations[0]["source"] = {"row": 7, "quality": ["good"]}
    original = deepcopy(observations)
    ids = [" R/01 ", "R/01", "R/01"]
    result = quantify(
        observations,
        source_relationship_ids=ids,
        source_tag_ids=["tag:a", "tag:b"],
        support_level="high",
        finding_id="finding",
        evidence_id="evidence",
        analysis_run_id="run",
    )
    assert result["provenance"]["observations"] == original
    assert result["source_relationship_ids"] == ids
    assert result["finding_id"] == "finding"
    assert result["evidence_id"] == "evidence"
    assert result["analysis_run_id"] == "run"
    observations[0]["source"]["quality"].clear()
    ids.clear()
    assert result["provenance"]["observations"] == original
    assert len(result["source_relationship_ids"]) == 3


def test_unknown_profile_keeps_provenance():
    result = quantify_consequence(
        rows(),
        profile_key="unknown",
        source_tag_ids=["a"],
        finding_id="finding",
        evidence_id="e",
        analysis_run_id="r",
    )
    assert result["status"] == "not_quantifiable"
    assert result["source_tag_ids"] == ["a"]
    assert result["finding_id"] == "finding"
    assert result["provenance"]["observations"] == rows()


def test_replay_and_strict_json():
    expected = json.dumps(quantify(rows()), allow_nan=False, sort_keys=True)
    for _ in range(20):
        assert json.dumps(quantify(iter(rows())), allow_nan=False, sort_keys=True) == expected
    assert json.loads(expected) == quantify(rows())


def test_floating_point_tolerance():
    observations = [dict(timestamp=i * 0.1, observed=0.3, expected=0.2) for i in range(1001)]
    assert quantify(observations)["cumulative_amount"] == pytest.approx(1 / 6, rel=1e-12)


def test_numeric_overflow_is_insufficient_and_serializable():
    result = quantify([dict(timestamp=t, observed=1e308, expected=0) for t in (0, 3600)])
    assert result["status"] == "not_quantifiable"
    assert "cumulative_amount" not in result
    json.dumps(result, allow_nan=False)


def test_profiles_are_immutable():
    with pytest.raises(TypeError):
        RESOURCE_PROFILES["fake"] = RESOURCE_PROFILES["water_gpm"]


def test_evidence_boundary():
    forbidden = {
        "cause",
        "probable_cause",
        "root_cause",
        "diagnosis",
        "corrective_action",
        "optimization_advice",
        "savings",
        "dollar_savings",
    }
    assert not forbidden.intersection(quantify(rows()))


def test_absolute_crossing_does_not_underflow_sign_detection():
    result = quantify(
        [
            {"timestamp": 0, "observed": -1e-170, "expected": 0},
            {"timestamp": 60, "observed": 1e-170, "expected": 0},
        ]
    )
    assert result["cumulative_amount"] == 0
    assert result["absolute_cumulative_amount"] == pytest.approx(5e-171, rel=1e-12, abs=0)
