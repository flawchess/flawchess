"""Retired test module — replaced by direct integration coverage in Plan 06.

Phase 94.4 Plan 06 (94.4-06) cohort-CDF cutover finished the
``scripts/backfill_user_percentiles.py`` rewrite, replacing the
``_compute_and_count`` / ``_row_exists`` / ``_MetricSummary`` /
``skipped_below_pooled_floor`` classifier internals with two direct
DB probes (``_classify_anchor_rows`` + ``_classify_percentile_rows``)
that materialise the new per-(metric × TC) percentile summary and the
new per-(TC × source_platform) anchor summary.

The pre-Plan 06 unit tests in this module exercised the retired
internals (mocked ``_row_exists`` + asserted the ``_MetricSummary``
counters). With the classifier surface gone, the unit harness has no
target. Real-DB end-to-end coverage already lands via:

  - ``tests/scripts/test_backfill_user_percentiles.py`` — idempotency,
    --user-id filter, --metric filter, --target safety guards,
    summary-output shape.
  - The Plan 06 Task 2 dev backfill HUMAN-VERIFY against the live
    dev DB — exercises the full Stage A + Stage B path including the
    new anchor and percentile probes.

The skip pattern follows Plan 04's precedent for
``tests/services/test_global_percentile_cdf.py`` and
``tests/scripts/test_gen_global_percentile_cdf_pooled.py``: when a
structural cutover retires the surface a test module exercised,
collapsing the module to a single ``pytest.skip`` keeps the test
collector clean without expanding scope to rewrite tests that no
longer have a target.
"""

from __future__ import annotations

import pytest

pytest.skip(
    "Retired in Phase 94.4 Plan 06 — classifier internals removed; integration "
    "coverage lives in tests/scripts/test_backfill_user_percentiles.py and the "
    "Plan 06 Task 2 dev backfill HUMAN-VERIFY.",
    allow_module_level=True,
)
