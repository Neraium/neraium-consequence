# Extraction and platform integration

Recovered from [Neraium-1.0 PR #124](https://github.com/Neraium/Neraium-1.0/pull/124),
merge `74a7d4bf86d2f55f51a8a4cded2bef612cffbe3e`, specifically
`backend/app/services/consequence_quantification.py` and its five regression tests.
The five resource conversions, trapezoidal rate integration, signed deficit,
explicit insufficient outcome, and relationship/tag identifiers are preserved.
Legacy profile aliases `steam_lb_hr` and `chemical_gal_hr` remain accepted.

Hardening fixes invalid-row bridging, ambiguous duplicates, timezone dependence,
unlimited default gaps, nonfinite arithmetic, lost insufficient-case provenance,
unweighted mean rates, and absolute-integral overstatement at zero crossings.
`methodology_version=1.0.0` identifies these intentional semantic changes.

The platform owns telemetry quality, operating context, expected-model validation,
persistence, relationship ownership, and rate-unit mapping. It supplies aligned
rates to this package, stores `measurable_consequence` in the canonical artifact,
and projects that recorded result to Findings. The package imports no platform
code and has no runtime dependencies. The platform must remove its original
engine, using this package as its sole consequence authority.

For reproducible initial delivery the platform can install the source archive
at an exact package commit, with its SHA-256 recorded in requirements. This works
in slim production containers without Git. Merge the package PR before the
platform PR. A future registry release may replace the archive only after
verifying it contains the same reviewed source; publishing to PyPI is separate
from opening these PRs.
