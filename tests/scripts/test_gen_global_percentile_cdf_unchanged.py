"""Phase 94.4 canary: ``_build_per_user_with_anchor_query`` SQL is stable.

Drift here means a downstream consumer (``gen_global_percentile_cdf.py`` re-
runs) will produce a different cohort CDF than the one committed in
``app/services/global_percentile_cdf.py``. The byte-identical regression
test asserts that the SQL string emitted by
``_build_per_user_with_anchor_query(metric, tc, snapshot_date=date(2026, 5, 26))``
is bytewise equal to the per-(metric, tc) golden fixture for every
``CdfMetricId × TimeControlBucket`` cell (8 × 4 = 32 fixtures).

Regenerating goldens
--------------------

When the per-(metric, TC) SQL surface changes intentionally (e.g. a future
inclusion-floor adjustment or recency-window tweak, or a Plan 02/03 builder
change), re-run::

    uv run python - <<'PY'
    from datetime import date
    from pathlib import Path
    from scripts.gen_global_percentile_cdf import (
        IN_SCOPE_METRICS,
        ALL_TIME_CONTROLS,
        _build_per_user_with_anchor_query,
    )
    out_dir = Path('tests/scripts/fixtures/global_percentile_cdf')
    out_dir.mkdir(parents=True, exist_ok=True)
    # Remove stale Phase 94.3 fixtures (named ``{metric}.sql`` without _tc suffix).
    for p in out_dir.glob('*.sql'):
        p.unlink()
    for m in IN_SCOPE_METRICS:
        for tc in ALL_TIME_CONTROLS:
            sql = _build_per_user_with_anchor_query(m, tc, snapshot_date=date(2026, 5, 26))
            (out_dir / f'{m}__{tc}.sql').write_text(sql + '\n')
    PY

Fixtures live in
``tests/scripts/fixtures/global_percentile_cdf/{metric}__{tc}.sql`` (one
file per (metric, tc) cell; double-underscore separator avoids collision
with the legacy ``time_pressure_score_gap_bullet.sql`` Phase 94.3 naming).
Trailing newline stripped on read so the in-memory golden matches the
function's no-trailing-newline output.

History
-------

- Phase 94.1 Plan 03: original goldens (per-cell stratified SQL).
- Phase 94.2 Plan 02: regenerated under pooled-per-user methodology.
- Phase 94.3 Plan 03: widened to 16 metrics (still one query per metric).
- Phase 94.4 Plan 04: SQL surface widened from per-metric to per-(metric,
  TC) — joins per_user_values × per_user_anchor on user_id (RESEARCH
  Pitfall 1 + 8). Fixtures regenerated; the prior 16-file flat fixture
  set is replaced by a 32-file per-(metric, tc) set. The 8-value
  ``CdfMetricId`` Literal × 4-value ``TimeControlBucket`` = 32 cells.
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import pytest

# Ensure the scripts/ directory is importable so the function-under-test resolves.
_SCRIPTS_DIR = str(Path(__file__).resolve().parent.parent.parent / "scripts")
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

from scripts.gen_global_percentile_cdf import (  # noqa: E402
    ALL_TIME_CONTROLS,
    IN_SCOPE_METRICS,
    _build_per_user_with_anchor_query,
)

_FIXTURE_DIR: Path = Path(__file__).resolve().parent / "fixtures" / "global_percentile_cdf"
_SNAPSHOT_DATE: date = date(2026, 5, 26)


def _load_golden(metric_id: str, tc: str) -> str:
    """Read the SQL golden fixture for ``(metric_id, tc)``; strip the trailing newline."""
    path = _FIXTURE_DIR / f"{metric_id}__{tc}.sql"
    if not path.exists():
        raise FileNotFoundError(
            f"Missing golden fixture {path}. Regenerate via the snippet in the module docstring."
        )
    text = path.read_text()
    return text.rstrip("\n")


@pytest.mark.parametrize(
    ("metric_id", "tc"),
    [(m, tc) for m in sorted(IN_SCOPE_METRICS) for tc in ALL_TIME_CONTROLS],
)
def test_build_per_user_with_anchor_query_byte_identical_after_refactor(
    metric_id: str,
    tc: str,
) -> None:
    """SQL output is byte-identical to the committed Phase 94.4 fixture goldens.

    Imports ``_build_per_user_with_anchor_query`` from the script directly
    (no DB required — the function is a pure SQL string builder). Asserts
    byte-identical equality against the fixture captured under Phase 94.4's
    cohort sliding-window methodology.
    """
    expected = _load_golden(metric_id, tc)
    actual = _build_per_user_with_anchor_query(
        metric_id,  # type: ignore[arg-type]
        tc,  # type: ignore[arg-type]
        snapshot_date=_SNAPSHOT_DATE,
    )
    assert actual == expected, (
        f"SQL output for (metric_id={metric_id!r}, tc={tc!r}) drifted from the "
        f"Phase 94.4 golden.\n"
        f"Drift here breaks the canary contract — re-running the regen script "
        f"would produce a different cohort CDF than the one committed.\n"
        f"Either revert the SQL change or regenerate the fixture (see module docstring).\n"
        f"First difference at char "
        f"{next((i for i, (a, b) in enumerate(zip(actual, expected)) if a != b), 'length mismatch')}."
    )


def test_fixture_directory_covers_all_in_scope_cells() -> None:
    """Every (metric, tc) cell has a corresponding ``{metric}__{tc}.sql`` fixture.

    Catches the case where ``IN_SCOPE_METRICS`` or ``ALL_TIME_CONTROLS`` is
    widened but a maintainer forgets to regenerate the goldens.
    """
    fixture_names = {p.stem for p in _FIXTURE_DIR.glob("*.sql")}
    in_scope = {f"{m}__{tc}" for m in IN_SCOPE_METRICS for tc in ALL_TIME_CONTROLS}
    missing = in_scope - fixture_names
    extra = fixture_names - in_scope
    assert not missing, f"Missing golden fixtures for: {sorted(missing)}"
    assert not extra, f"Stale golden fixtures (not in IN_SCOPE_METRICS × ALL_TIME_CONTROLS): {sorted(extra)}"
