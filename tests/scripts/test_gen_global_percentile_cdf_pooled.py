"""DEPRECATED — structural tests for the flat CDF SQL.

These tests exercised ``_build_metric_breakpoint_query`` and
``_build_per_bucket_sanity_query`` against the 16-key flat
``GLOBAL_PERCENTILE_CDF`` registry. The cohort-CDF cutover retired both
helpers in favour of ``_build_per_user_with_anchor_query(metric, tc, ...)``
and the per-(metric, anchor, TC) ``COHORT_PERCENTILE_CDF`` shape.

Replacement structural coverage lives in
test_gen_global_percentile_cdf_unchanged.py. This module is skipped at collection
time so the test suite stays collectible — and the broken imports don't surface as
ty errors.
"""

from __future__ import annotations

import pytest

pytest.skip(
    "Phase 94.4 Plan 04: structural tests for the flat CDF SQL retired. "
    "Replacement test module ships in Plan 05.",
    allow_module_level=True,
)
