"""DEPRECATED — Phase 94.2 / 94.3 structural tests for the flat CDF SQL.

These tests exercised ``_build_metric_breakpoint_query`` and
``_build_per_bucket_sanity_query`` against the Phase 94.3 16-key flat
``GLOBAL_PERCENTILE_CDF`` registry. Phase 94.4 Plan 04 retired both
helpers in favour of ``_build_per_user_with_anchor_query(metric, tc, ...)``
and the per-(metric, anchor, TC) ``COHORT_PERCENTILE_CDF`` shape.

Plan 05 (94.4-05) will ship replacement structural tests against the new
SQL surface. Until then this module is skipped at collection time so the
test suite stays collectible — and the broken imports don't surface as
ty errors.
"""

from __future__ import annotations

import pytest

pytest.skip(
    "Phase 94.4 Plan 04: structural tests for the flat CDF SQL retired. "
    "Replacement test module ships in Plan 05.",
    allow_module_level=True,
)
