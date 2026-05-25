"""Phase 94.3 canary: ``_build_metric_breakpoint_query`` SQL output is stable.

Drift here means a downstream consumer (``gen_global_percentile_cdf.py`` /
``user_benchmark_percentiles_service.py``) will produce inconsistent numbers
across the two paths. The byte-identical regression test asserts that the
SQL string emitted by ``_build_metric_breakpoint_query(metric_id,
snapshot_date=date(2026, 3, 31))`` is bytewise equal to the per-metric
golden fixture for every ``CdfMetricId``.

Regenerating goldens
--------------------

When the pooled SQL surface changes intentionally (e.g. a future inclusion
floor adjustment or recency-window tweak), re-run::

    uv run python - <<'PY'
    from datetime import date
    from pathlib import Path
    from scripts.gen_global_percentile_cdf import (
        IN_SCOPE_METRICS,
        _build_metric_breakpoint_query,
    )
    out_dir = Path('tests/scripts/fixtures/global_percentile_cdf')
    out_dir.mkdir(parents=True, exist_ok=True)
    for m in IN_SCOPE_METRICS:
        sql = _build_metric_breakpoint_query(m, snapshot_date=date(2026, 3, 31))
        (out_dir / f'{m}.sql').write_text(sql + '\n')
    PY

Fixtures live in ``tests/scripts/fixtures/global_percentile_cdf/<metric_id>.sql``
(one file per metric; trailing newline stripped on read so the in-memory
golden matches the function's no-trailing-newline output). The structure of
the test (one parametrised case per metric, byte-equality assertion) is the
canary contract — only the fixture content moves with intentional
methodology changes.

History
-------

- Phase 94.1 Plan 03: original goldens (per-cell stratified SQL).
- Phase 94.2 Plan 02: regenerated under the pooled-per-user methodology.
- Phase 94.3 Plan 03: widened from 4 to 16 metrics (12 new per-(metric × TC)
  time-management cells). Goldens moved out of the test module into per-
  metric ``.sql`` files under ``tests/scripts/fixtures/global_percentile_cdf/``
  because verbatim inlining 16 multi-KB SQL strings made the test file
  unreadable. The existing 4 metrics' SQL is byte-identical to the Phase 94.2
  fixtures; only the 12 new fixtures are net-new.
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
    IN_SCOPE_METRICS,
    _build_metric_breakpoint_query,
)

_FIXTURE_DIR: Path = Path(__file__).resolve().parent / "fixtures" / "global_percentile_cdf"
_SNAPSHOT_DATE: date = date(2026, 3, 31)


def _load_golden(metric_id: str) -> str:
    """Read the SQL golden fixture for ``metric_id``; strip the single trailing newline.

    The function-under-test returns SQL without a trailing newline (matches
    the original inline string format). Fixtures are written with a trailing
    newline so editors and ``git diff`` behave; the stripping here keeps the
    byte-equality assertion meaningful without forcing a newline-free file.
    """
    path = _FIXTURE_DIR / f"{metric_id}.sql"
    if not path.exists():
        raise FileNotFoundError(
            f"Missing golden fixture {path}. Regenerate via the snippet in the module docstring."
        )
    text = path.read_text()
    return text.rstrip("\n")


@pytest.mark.parametrize("metric_id", sorted(IN_SCOPE_METRICS))
def test_build_metric_breakpoint_query_byte_identical_after_refactor(
    metric_id: str,
) -> None:
    """SQL output is byte-identical to the committed Phase 94.3 fixture goldens.

    Imports ``_build_metric_breakpoint_query`` from the script directly
    (no DB required — the function is a pure SQL string builder). Asserts
    byte-identical equality against the fixture captured under Phase 94.3's
    pooled-per-user methodology widened to 16 entries.
    """
    expected = _load_golden(metric_id)
    actual = _build_metric_breakpoint_query(metric_id, snapshot_date=_SNAPSHOT_DATE)  # ty: ignore[invalid-argument-type]
    assert actual == expected, (
        f"SQL output for metric_id={metric_id!r} drifted from the Phase 94.3 golden.\n"
        f"Drift here breaks the canary contract — downstream consumers will produce\n"
        f"inconsistent numbers across paths. Either revert the SQL change or\n"
        f"regenerate the fixture (see module docstring).\n"
        f"First difference at char "
        f"{next((i for i, (a, b) in enumerate(zip(actual, expected)) if a != b), 'length mismatch')}."
    )


def test_fixture_directory_covers_all_in_scope_metrics() -> None:
    """Every entry in ``IN_SCOPE_METRICS`` has a corresponding ``.sql`` fixture.

    Catches the case where ``IN_SCOPE_METRICS`` is widened but a maintainer
    forgets to regenerate the goldens — the parametrised test above would
    miss new metrics that have no fixture file (parametrisation would error
    on the first ``_load_golden`` call, but a positive cardinality check
    here makes the failure mode explicit).
    """
    fixture_names = {p.stem for p in _FIXTURE_DIR.glob("*.sql")}
    in_scope = set(IN_SCOPE_METRICS)
    missing = in_scope - fixture_names
    extra = fixture_names - in_scope
    assert not missing, f"Missing golden fixtures for: {sorted(missing)}"
    assert not extra, f"Stale golden fixtures (not in IN_SCOPE_METRICS): {sorted(extra)}"
