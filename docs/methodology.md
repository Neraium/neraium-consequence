# Methodology 1.0.0

For adjacent, eligible observations at times `t0 < t1`, compute
`((observed0 - expected0) / 2 + (observed1 - expected1) / 2) * (t1 - t0) / rate_period_seconds`.
The signed sum uses `math.fsum`. Rates are piecewise linear only within supported
intervals. There is no extrapolation. Expected rates must already be established
by the caller; this package fits no expected-behavior model.

## Evidence and time

- Input is an iterable of JSON-shaped observation mappings, with `timestamp`,
  `observed`, `expected`, and optional `valid` (only literal `True` passes).
  Finite numeric strings for rates are accepted. Booleans are not numeric evidence.
- Epochs are seconds, bounded by Python's UTC calendar. ISO timestamps with
  offsets are normalized to epoch seconds. Naive ISO timestamps explicitly mean
  UTC, independent of host timezone. Millisecond epochs are not auto-detected.
- Unsorted rows are sorted by timestamp; original input order and indices remain
  in provenance. Every duplicate timestamp group is ambiguous and gated,
  including equal-valued duplicates. No arbitrary duplicate wins.
- An invalid value at a known timestamp blocks both adjacent intervals. Missing
  values are never removed before integration. An unparseable/missing timestamp
  prevents quantification of the entire supplied window: its gap cannot be located.
- `max_gap_seconds` is inclusive. `None` selects a fixed 3600-second ceiling,
  never unlimited bridging or a cadence inferred from the data. Callers should
  supply their acquisition system's stricter continuity limit. A missing sample
  with no explicit marker can only be detected through this limit; no quantifier
  can identify an unreported dropout inside an otherwise acceptable interval.
- Invalid gap settings and nonfinite arithmetic return `not_quantifiable`.
  Unsupported non-JSON Python objects or incorrectly typed identity arguments
  raise `TypeError` as caller contract errors.

## Results

`quantified` requires at least one supported positive-duration interval. A real
zero is `quantified` with `direction="aligned"`. Insufficient evidence has no
`cumulative_amount`, `direction`, or invented duration. Both outcomes retain
identities, support level, original observations, validation, settings, and reasons.

`observation_count` counts supplied rows; valid/rejected counts include duplicate
gating. `skipped_interval_count` counts rejected adjacent pairs after sorting.
Unplaceable timestamps prevent interval evaluation; their interval counts are 0.
`duration_seconds` sums contributing durations, not elapsed wall-clock span.
Start/end timestamps enclose contributing intervals, and may span excluded gaps.
`contributing_intervals` and `skipped_intervals` identify original row indices.

Direction is the sign of the signed net integral. Mixed deviations may cancel;
the limitations say so. `absolute_cumulative_amount` integrates the absolute
piecewise-linear residual, splitting at zero crossings. Observed/expected mean
rates are duration-weighted across contributing intervals. Values are not rounded
for presentation. Floating-point comparisons should use an appropriate tolerance.

`provenance.observations` is a detached snapshot of original JSON values, including
unknown observation metadata. Rejected NaN and infinity are encoded as
`{"nonfinite_float": "nan"}`, `"inf"`, or `"-inf"` so the result remains strict JSON.
IDs preserve exact strings, ordering, and duplicates. No random IDs, wall clock,
environment-derived settings, or mutable profile registry enter the calculation.
Retain the complete result in canonical storage; UI projections must disclose any
truncation and must never recalculate from truncated evidence.

## Evidence boundary

The output measures associated observed-minus-expected resource use. It supplies
no cause, probable cause, root cause, diagnosis, automated corrective action,
optimization advice, monetary savings, or unsupported inference. Support level
is caller-supplied provenance, not a probability or confidence computed here.
