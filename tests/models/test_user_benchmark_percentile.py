"""Tests for the benchmark_metric_enum SAEnum descriptor.

Asserts that all 12 new rate-metric ENUM members are present in the SAEnum
declared in app.models.user_benchmark_percentile.

The 12 rate-metric values (conversion_rate_{bullet,blitz,rapid,classical},
parity_rate_*, recovery_rate_*) must all be present in the ENUM. The
parametrized test below fails if the SAEnum drops any of them.
"""

from __future__ import annotations

import pytest

from app.models.user_benchmark_percentile import benchmark_metric_enum

# ── 12 rate-metric ENUM members to assert ──────────────────────────────────
#
# Order matches the migration's _NEW_VALUES tuple.
# 3 families × 4 TCs = 12. All must be present in benchmark_metric_enum.enums.

_EXPECTED_RATE_MEMBERS: tuple[str, ...] = (
    "conversion_rate_bullet",
    "conversion_rate_blitz",
    "conversion_rate_rapid",
    "conversion_rate_classical",
    "parity_rate_bullet",
    "parity_rate_blitz",
    "parity_rate_rapid",
    "parity_rate_classical",
    "recovery_rate_bullet",
    "recovery_rate_blitz",
    "recovery_rate_rapid",
    "recovery_rate_classical",
)


@pytest.mark.parametrize("member", _EXPECTED_RATE_MEMBERS)
def test_rate_enum_member_present(member: str) -> None:
    """Each of the 12 rate-metric names must appear in benchmark_metric_enum.enums.

    Fails if the SAEnum descriptor and the migration's ENUM values drift apart.
    """
    assert member in benchmark_metric_enum.enums, (
        f"ENUM member {member!r} missing from benchmark_metric_enum "
        f"(expected by Phase 99 D-09 — Plan 02 must add it)"
    )
