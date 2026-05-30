"""Chapter 4 §4 — Global / Cohort Percentile CDF (reference only, NOT re-derived here).

The percentile CDF is a SEPARATE deliverable from the benchmark report. Unlike every
other chapter it is NOT part of `reports/benchmark/benchmarks-latest.md` (the benchmark
report has no §4 section), so this chapter computes nothing and renders nothing into the
benchmark report body — it only records cross-reference pointers in the JSON artifact so
the generated bundle is self-documenting.

The CDF has its own deterministic generator, its own committed artifact, its own report,
and its own acceptance tests:

  - Generator : `scripts/gen_global_percentile_cdf.py` (`--target benchmark`, manual recalibration)
  - Artifact  : `app/services/global_percentile_cdf.py` (`COHORT_PERCENTILE_CDF` registry)
  - Report    : `reports/percentile/cohort-percentile-cdf-latest.md`
  - Gates     : `tests/scripts/test_gen_global_percentile_cdf_pooled.py`,
                `tests/scripts/test_gen_global_percentile_cdf_unchanged.py`

NB: the SKILL.md §4 prose still describes the retired Phase 93/94.2 *flat*
`GLOBAL_PERCENTILE_CDF` (99 breakpoints pooled across the TC×ELO grid). The live artifact
is the Phase 94.4 *cohort sliding-window* `COHORT_PERCENTILE_CDF` (8 metrics × ~37 anchors
× 4 TC, K-nearest-anchor cohorts). The SKILL rewrite (final Phase-A step) reconciles that;
this chapter points at the current reality, not the stale prose.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

SECTION = "SKILL.md §4 — Global/Cohort Percentile CDF (separate deliverable; see gen_global_percentile_cdf.py)"

# Cross-reference pointers recorded in the artifact (NOT rendered into the benchmark report).
REFERENCE: dict[str, str] = {
    "generator": "scripts/gen_global_percentile_cdf.py",
    "artifact": "app/services/global_percentile_cdf.py",
    "registry": "COHORT_PERCENTILE_CDF",
    "report": "reports/percentile/cohort-percentile-cdf-latest.md",
    "tests": "tests/scripts/test_gen_global_percentile_cdf_{pooled,unchanged}.py",
    "note": (
        "Separate deterministic deliverable — not part of benchmarks-latest.md. "
        "Regenerate with `uv run python scripts/gen_global_percentile_cdf.py --target benchmark`."
    ),
}


async def build(_session: AsyncSession) -> dict[str, Any]:
    """Reference-only chapter: no DB query, no benchmark-report body.

    Returns a REFERENCE payload (markdown=None) so `gen_benchmarks` omits §4 from the
    benchmark report body while still carrying the cross-reference in the JSON artifact.
    """
    return {
        "status": "REFERENCE",
        "section": SECTION,
        "markdown": None,
        "reference": REFERENCE,
    }
