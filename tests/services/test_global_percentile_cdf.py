"""DEPRECATED: tests for the flat ``GLOBAL_PERCENTILE_CDF`` registry.

``GLOBAL_PERCENTILE_CDF`` is retired in favour of ``COHORT_PERCENTILE_CDF``
(per-(metric, anchor, TC) nested registry) and the new
``interpolate_cohort_percentile(metric, value, anchor, tc)`` helper.

The structural tests that lived here exercised the flat 16-key registry
shape and the 2-arg ``interpolate_percentile(metric, value)`` lookup; both
are retired. This file holds no tests and can be deleted.

The module is skipped at collection time via ``pytest.skip`` rather than
left holding a broken import of the retired ``GLOBAL_PERCENTILE_CDF`` symbol.
"""

from __future__ import annotations

import pytest

pytest.skip(
    "Phase 94.4 Plan 04: GLOBAL_PERCENTILE_CDF retired in favour of "
    "COHORT_PERCENTILE_CDF. Replacement test module ships in Plan 05.",
    allow_module_level=True,
)
