# neraium-consequence

Neraium's standalone consequence quantification package. Integrates timestamped
observed-minus-expected engineering rates into signed resource quantities.
No runtime dependencies. Python 3.11+.

```python
from neraium_consequence import quantify_consequence

result = quantify_consequence(
    observations=[
        {"timestamp": i * 3600, "observed": 135.66666666666666, "expected": 100.0} for i in range(7)
    ],
    profile_key="water_gpm",
    source_relationship_ids=["water:load"],
    source_tag_ids=["water-flow", "cooling-load"],
    support_level="high",
    finding_id="finding-1",
    evidence_id="evidence-1",
    analysis_run_id="run-1",
)
# status: quantified; cumulative_amount: approximately 12840.0 gal;
# duration_seconds: 21600.0; direction: above_expected
```

The public function accepts `observations` plus keyword-only `profile_key`,
`max_gap_seconds`, `source_relationship_ids`, `source_tag_ids`, `support_level`,
`finding_id`, `evidence_id`, and `analysis_run_id`. It returns a plain JSON-serializable
dictionary; public `Observation` and `ConsequenceResult` types support typed callers.

| Profile | Rate | Cumulative unit |
| --- | --- | --- |
| `water_gpm` | gallons/minute | `gal` |
| `electricity_kw` | kilowatts | `kWh` |
| `steam_lb_per_hr` | pounds/hour | `lb` |
| `chemical_feed_gal_per_hr` | gallons/hour | `gal` |
| `compressed_air_scfm` | standard cubic feet/minute | `scf` |

Invalid observations and duplicate timestamps block adjacent intervals. A malformed
timestamp prevents quantification. Gaps over the explicitly supplied limit are
excluded; the default limit is 3600 seconds. Supply the acquisition system's
supported continuity limit. Exact source IDs, inputs, and interval decisions are
retained in both outcome states.

```python
insufficient = quantify_consequence(observations=[], profile_key="water_gpm")
assert insufficient["status"] == "not_quantifiable"
assert insufficient["statement"] == "Consequence not quantifiable from available evidence."
assert "cumulative_amount" not in insufficient
```

Insufficient evidence never silently becomes zero. A supported zero remains a
quantified zero. Duration counts only contributing intervals; mixed deviations
retain their sign and may cancel in the net amount.

The package supplies no cause, probable cause, root cause, diagnosis, automated
corrective action, generic optimization advice, monetary savings, or unsupported
inference. Expected rates and evidence support come from the caller.

## Development

```sh
python -m pip install -e '.[dev]'
python -m pytest
ruff check .
ruff format --check .
mypy
python -m compileall -q neraium_consequence
python -m build
```

Install a reviewed source checkout with `python -m pip install .`. Registry
publication is not required for the platform's immutable source-archive dependency.

See [methodology and result semantics](docs/methodology.md) and
[extraction provenance and platform integration](docs/extraction.md).
