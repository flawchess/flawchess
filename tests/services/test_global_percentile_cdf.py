"""DEPRECATED — Phase 94.3 tests for the flat ``GLOBAL_PERCENTILE_CDF`` registry.

Phase 94.4 Plan 04 (CONTEXT D-09) retires ``GLOBAL_PERCENTILE_CDF`` in favour
of ``COHORT_PERCENTILE_CDF`` (per-(metric, anchor, TC) nested registry) and
the new ``interpolate_cohort_percentile(metric, value, anchor, tc)`` helper.

The structural tests that lived here exercised the flat 16-key registry
shape and the 2-arg ``interpolate_percentile(metric, value)`` lookup; both
retire with Plan 04. Plan 05 (94.4-05) writes the replacement test module
(``test_cohort_percentile_cdf.py``) against the new shape — at which point
this file is deleted.

To keep the test suite collectible between Plan 04 and Plan 05, the module
is skipped at collection time via ``pytest.skip`` rather than left holding
a broken import of the retired ``GLOBAL_PERCENTILE_CDF`` symbol.
"""

from __future__ import annotations

import pytest

pytest.skip(
    "Phase 94.4 Plan 04: GLOBAL_PERCENTILE_CDF retired in favour of "
    "COHORT_PERCENTILE_CDF. Replacement test module ships in Plan 05.",
    allow_module_level=True,
)
