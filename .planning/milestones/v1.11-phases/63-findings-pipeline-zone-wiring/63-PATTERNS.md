# Phase 63: Findings Pipeline & Zone Wiring - Pattern Map

**Mapped:** 2026-04-20
**Files analyzed:** 10 (7 created, 3 modified)
**Analogs found:** 9 / 10

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `app/services/endgame_zones.py` | service/registry | transform | `app/services/endgame_service.py` (constants block) | role-match |
| `app/schemas/insights.py` | schema | request-response | `app/schemas/endgames.py` + `app/schemas/normalization.py` | exact |
| `app/services/insights_service.py` | service | request-response | `app/services/endgame_service.py::get_endgame_overview` | exact |
| `scripts/gen_endgame_zones_ts.py` | utility/codegen | batch | `scripts/seed_openings.py` (script shell) | partial |
| `frontend/src/generated/endgameZones.ts` | config | — | none (fresh pattern) | none |
| `tests/services/test_insights_service.py` | test | — | `tests/test_endgame_service.py` | exact |
| `tests/services/test_endgame_zones.py` | test | — | `tests/test_endgame_service.py::TestClassifyEndgameClass` | exact |
| `tests/services/test_endgame_zones_consistency.py` | test | — | none (fresh regex-parse pattern) | none |
| `frontend/src/components/charts/EndgameScoreGapSection.tsx` | component | — | self (single-line edit) | self |
| `.github/workflows/ci.yml` | config | — | self (insert step) | self |

---

## Pattern Assignments

### `app/services/endgame_zones.py` (service/registry, transform)

**Analog:** `app/services/endgame_service.py` (constants block, lines 1-100 area) and `app/services/openings_service.py` (named constants pattern)

**Imports pattern** (`app/services/openings_service.py` lines 1-8):
```python
"""Openings service: W/D/L derivation, stats computation, and orchestration."""

import datetime
import io
from typing import Literal

import sentry_sdk
```

For `endgame_zones.py` the equivalent is:
```python
"""Gauge zone registry: authoritative Python source of truth for endgame metric thresholds.

Exported constants are consumed by insights_service.py and codegen'd to
frontend/src/generated/endgameZones.ts via scripts/gen_endgame_zones_ts.py.
"""

from dataclasses import dataclass
from collections.abc import Mapping
from typing import Literal
```

**Named-constants pattern** (`app/services/openings_service.py` lines 39-53):
```python
# Rolling window size for win-rate time series computation.
ROLLING_WINDOW_SIZE = 50

# Minimum games in a rolling window before emitting a timeline data point.
MIN_GAMES_FOR_TIMELINE = 10

# Maps recency filter strings to timedelta offsets.
RECENCY_DELTAS: dict[str, datetime.timedelta] = {
    "week": datetime.timedelta(days=7),
    ...
}
```
Copy this docstring-above-constant style for every threshold in `endgame_zones.py`.

**Literal type alias pattern** (`app/schemas/endgames.py` lines 15-16, 169):
```python
EndgameClass = Literal["rook", "minor_piece", "pawn", "queen", "mixed", "pawnless"]
MaterialBucket = Literal["conversion", "parity", "recovery"]
```
Use the same bare `TypeAlias = Literal[...]` form for `MetricId`, `Zone`, `Trend`, `SampleQuality`, `Window`, `SubsectionId`.

**Frozen dataclass pattern** (stdlib `dataclasses`; no codebase analog exists — introduce fresh):
```python
@dataclass(frozen=True)
class ZoneSpec:
    """Zone boundaries and direction for one metric in the registry."""
    typical_lower: float
    typical_upper: float
    direction: Literal["higher_is_better", "lower_is_better"]
```

**Return type annotation pattern** (`app/services/endgame_service.py::classify_endgame_class`):
All public functions must carry full type annotations per CLAUDE.md §"ty compliance".

---

### `app/schemas/insights.py` (schema, request-response)

**Analog 1:** `app/schemas/normalization.py` (best match for Literal-heavy schema module)

**Full file pattern** (`app/schemas/normalization.py` lines 1-62):
```python
"""Pydantic schema for normalized game data from chess.com and lichess.

Created per D-01: Pydantic models at system boundaries (external API input).
"""

import datetime
from typing import Literal

from pydantic import BaseModel

# Literal types for fields with fixed value sets (per CLAUDE.md)
Platform = Literal["chess.com", "lichess"]
GameResult = Literal["1-0", "0-1", "1/2-1/2"]
Color = Literal["white", "black"]
Termination = Literal["checkmate", "resignation", "timeout", "draw", "abandoned", "unknown"]
TimeControlBucket = Literal["bullet", "blitz", "rapid", "classical"]


class NormalizedGame(BaseModel):
    """Typed representation of a normalized game...

    Uses Literal types for fixed-value fields per CLAUDE.md.
    """

    user_id: int
    platform: Platform
    ...
    # per-game base clock fields (optional, default None)
    base_time_seconds: int | None = None
```
Key takeaways: module-level `Literal` type aliases come first, then `BaseModel` subclasses; optional fields default to `None`; docstring explains the design decision reference.

**Analog 2:** `app/schemas/endgames.py` (lines 1-17, 169, 413-429) for composite response model:
```python
class EndgameOverviewResponse(BaseModel):
    """Composed response for GET /api/endgames/overview.

    Serves the endgame dashboard payloads from a single request so the
    frontend can issue one HTTP call that runs sequentially on one AsyncSession
    (Phase 52). ...
    """

    stats: EndgameStatsResponse
    performance: EndgamePerformanceResponse
    timeline: EndgameTimelineResponse
    score_gap_material: ScoreGapMaterialResponse
    clock_pressure: ClockPressureResponse
    time_pressure_chart: TimePressureChartResponse
    endgame_elo_timeline: EndgameEloTimelineResponse
```
`EndgameTabFindings` follows this same "flat named fields, each a typed Pydantic model" pattern.

**`insights.py` module structure to follow:**
1. Module docstring referencing FIND-01..FIND-05 and phase
2. Stdlib imports
3. Pydantic import
4. Import `Zone`, `Trend`, `SampleQuality`, `Window`, `SubsectionId` re-exported from `endgame_zones`
5. Module-level Literal aliases: `FlagId`, `SectionId`
6. `FilterContext(BaseModel)` — mirrors `get_endgame_overview` parameter surface
7. `SubsectionFinding(BaseModel)` — per-subsection-per-window unit
8. `EndgameTabFindings(BaseModel)` — top-level composite with `findings: list[SubsectionFinding]`, `flags: list[FlagId]`, `findings_hash: str`, `as_of: datetime`

---

### `app/services/insights_service.py` (service, request-response)

**Analog:** `app/services/endgame_service.py::get_endgame_overview` (lines 1895-1965)

**Imports pattern** (`app/services/endgame_service.py` lines 1-60):
```python
"""Endgame service: classification, aggregation, and orchestration for endgame analytics."""

import bisect
import math
import statistics
from collections import defaultdict
from collections.abc import Sequence
from datetime import datetime, time, timedelta
from enum import IntEnum
from typing import Any, Literal, cast

import sentry_sdk
from sqlalchemy.engine import Row
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.query_utils import DEFAULT_ELO_THRESHOLD
from app.repositories.endgame_repository import (
    count_endgame_games,
    ...
)
from app.schemas.endgames import (
    EndgameOverviewResponse,
    ...
)
```
`insights_service.py` imports from `endgame_service` (not repositories directly) and from `app/schemas/insights.py`.

**Async service entry point pattern** (`app/services/endgame_service.py` lines 1895-1916):
```python
async def get_endgame_overview(
    session: AsyncSession,
    user_id: int,
    time_control: list[str] | None,
    platform: list[str] | None,
    rated: bool | None,
    opponent_type: str,
    recency: str | None,
    window: int = 50,
    opponent_strength: Literal["any", "stronger", "similar", "weaker"] = "any",
    elo_threshold: int = DEFAULT_ELO_THRESHOLD,
) -> EndgameOverviewResponse:
    """Compose all five endgame dashboard payloads into a single response.

    Fetches entry_rows and performance rows once, then threads them to both
    the stats/performance builders and _compute_score_gap_material — eliminating
    redundant DB queries that the previous implementation issued separately in
    get_endgame_stats and get_endgame_performance (Phase 53).

    All queries run sequentially on one AsyncSession — no asyncio.gather.
    See endgame_repository.py for AsyncSession concurrency notes.
    """
    cutoff = recency_cutoff(recency)
    ...
```
`compute_findings` follows this exact pattern: `async def`, typed parameters, return type annotation, sequential service calls (never `asyncio.gather`), docstring explaining the layering.

**Sentry error-capture pattern** (`app/services/endgame_service.py`, general pattern):
```python
import sentry_sdk

try:
    ...
except Exception as exc:
    sentry_sdk.set_context("insights", {"user_id": user_id})
    sentry_sdk.capture_exception(exc)
    raise
```
Per CLAUDE.md §"Backend Rules": capture in non-trivial except blocks; pass variables via `set_context`, never embed in message strings.

**Sequential-DB-call pattern** (`app/services/endgame_service.py` lines 1920-1946):
```python
# Fetch entry_rows once — shared by stats, performance, and score_gap_material.
entry_rows = await query_endgame_entry_rows(session, ...)

# Stats: aggregate per-category W/D/L + conversion/recovery from entry_rows
categories = _aggregate_endgame_stats(entry_rows)
total_games = await count_filtered_games(session, ...)
```
`insights_service.py` calls `get_endgame_overview(session, user_id, ..., recency=None)` then `get_endgame_overview(session, user_id, ..., recency="3months")` sequentially — same session, no gather.

**`_compute_weekly_rolling_series` signature** (`app/services/endgame_service.py` lines 1556-1611):
```python
def _compute_weekly_rolling_series(
    rows: list[Row[Any]],
    window: int,
) -> list[dict]:
    """Compute a rolling-window win-rate series sampled once per ISO week...

    Returns:
        list of dicts with keys: date (Monday of the ISO week, YYYY-MM-DD),
        win_rate, game_count. Sorted chronologically by date.
    """
    results_so_far: list[Literal["win", "draw", "loss"]] = []
    per_week_count: dict[tuple[int, int], int] = {}
    data_by_week: dict[tuple[int, int], dict[str, Any]] = {}

    for played_at, result, user_color in rows:
        outcome = derive_user_result(result, user_color)
        results_so_far.append(outcome)
        window_slice = results_so_far[-window:]
        ...
```
Import and call `_compute_weekly_rolling_series` directly for trend computation; do not reimplement.

---

### `scripts/gen_endgame_zones_ts.py` (utility, codegen batch)

**Analog:** `scripts/seed_openings.py` (script structure only — no TS-codegen analog exists in the codebase)

**Script module-level pattern** (`scripts/seed_openings.py` lines 1-36):
```python
"""Idempotent seed script: populate openings table from app/data/openings.tsv.

Usage (local dev):
    uv run python -m scripts.seed_openings

Usage (production):
    ...
"""
import asyncio
import csv
import io
import logging
from pathlib import Path
...

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

TSV_PATH = Path(__file__).resolve().parent.parent / "app" / "data" / "openings.tsv"
```
Follow: module docstring with usage examples, stdlib-only imports (no app imports except registry), `Path(__file__).resolve()` for path resolution, `if __name__ == "__main__": asyncio.run(main())` at the bottom.

**Fresh pattern for TS emission:** No existing Python-to-TypeScript codegen exists in the repo. Design fresh:
- Import `ZONE_REGISTRY`, `BUCKETED_ZONE_REGISTRY`, and threshold constants from `app.services.endgame_zones`
- Build TS source string with explicit type annotations (no `any`)
- Write to `frontend/src/generated/endgameZones.ts` via `Path.write_text()`
- Print success message for CI log visibility
- Add `// AUTO-GENERATED — do not edit by hand. Run scripts/gen_endgame_zones_ts.py` header
- Add `/* eslint-disable */` and `// @ts-nocheck` or explicit types — prefer explicit types to match project style

---

### `frontend/src/generated/endgameZones.ts` (config, generated)

**No analog.** The `frontend/src/generated/` directory does not yet exist. The file will be created by `scripts/gen_endgame_zones_ts.py` and committed. The planner must also update `frontend/knip.json` to ignore this file from dead-export detection until Phase 66 consumers switch in. See `## Shared Patterns — knip.json ignore convention` below.

---

### `tests/services/test_insights_service.py` (test, pure-function unit tests)

**Analog 1:** `tests/test_endgame_service.py` (pure-function class-based test structure)

**Test file header pattern** (`tests/test_endgame_service.py` lines 1-45):
```python
"""Tests for endgame service: classify_endgame_class, _aggregate_endgame_stats, and service entry points.

Tests cover:
- classify_endgame_class: maps material_signature strings to endgame category names
- _aggregate_endgame_stats: aggregates raw per-(game, class) rows into EndgameCategoryStats list
- ...
"""

import datetime
from typing import Any, NamedTuple
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.endgames import EndgameEloTimelinePoint, EndgameWDLSummary
from app.services.endgame_service import (
    CLOCK_PRESSURE_TIMELINE_WINDOW,
    _aggregate_endgame_stats,
    classify_endgame_class,
    get_endgame_overview,
    ...
)


class _FakeRow(NamedTuple):
    """Lightweight stand-in for a SQLAlchemy Row used by endgame service tests."""
    game_id: int
    ...


class TestClassifyEndgameClass:
    """Unit tests for endgame category classification from material_signature."""

    def test_rook_endgame(self):
        """KR vs KR — pure rook endgame, no minor pieces or pawns."""
        assert classify_endgame_class("KR_KR") == "rook"
```
Key takeaways: module docstring lists coverage; class per logical group; per-test docstring explains the case; `NamedTuple` for synthetic row stand-ins; `from unittest.mock import AsyncMock, patch` for async service calls.

**Analog 2:** `tests/test_integration_routers.py` for `seeded_user` fixture usage pattern (lines 1-80):
```python
import httpx
import pytest

from app.main import app
from tests.seed_fixtures import STARTING_POSITION_HASH, SeededUser
# seeded_user fixture is provided by tests.seed_fixtures via conftest.py's
# pytest_plugins registration — do NOT import the fixture name here

_BASE = "http://test"

class TestGlobalStatsRouter:
    @pytest.mark.asyncio
    async def test_totals_match_expected_games(self, seeded_user: SeededUser) -> None:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url=_BASE
        ) as client:
            resp = await client.get("/api/stats/global", headers=seeded_user.auth_headers)
        assert resp.status_code == 200, resp.text
```
For `test_insights_service.py`: the service is pure-Python over `EndgameOverviewResponse` data, so the seeded_user fixture is used if end-to-end DB integration is needed; for unit tests of `assign_zone`/flags/trend, no DB is required — use synthetic Pydantic model instances instead of `seeded_user`.

**`seeded_user` fixture declaration** (`tests/seed_fixtures.py` lines 421-434):
```python
@pytest_asyncio.fixture(scope="module")
async def seeded_user() -> SeededUser:
    """Register one user + commit the deterministic portfolio; return handle."""
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        user_id, email, auth_headers = await _register_and_login(client)
    await _seed_portfolio(user_id)
    return SeededUser(id=user_id, email=email, auth_headers=auth_headers, expected=dict(EXPECTED))
```
Note: `scope="module"` — all tests in a module share one user. Declare `tests/services/` as a new sub-package (`__init__.py`) to keep `scope="module"` isolation correct.

---

### `tests/services/test_endgame_zones.py` (test, pure unit)

**Analog:** `tests/test_endgame_service.py::TestClassifyEndgameClass` (lines 65-122)

```python
class TestClassifyEndgameClass:
    """Unit tests for endgame category classification from material_signature."""

    def test_rook_endgame(self):
        """KR vs KR — pure rook endgame, no minor pieces or pawns."""
        assert classify_endgame_class("KR_KR") == "rook"

    def test_minor_piece_endgame(self):
        """KB vs KN — bishop vs knight, no rook or queen."""
        assert classify_endgame_class("KB_KN") == "minor_piece"
```
`test_endgame_zones.py` follows the same pattern: one class per function under test (`TestAssignZone`, `TestAssignBucketedZone`), one test per direction/edge case (higher_is_better, lower_is_better, boundary, NaN guard).

---

### `tests/services/test_endgame_zones_consistency.py` (test, fresh regex-parse pattern)

**No analog.** No existing test parses another source file with regex. Fresh pattern:
```python
"""Consistency test: Python registry values match inline TS constants.

Regex-parses EndgameScoreGapSection.tsx and EndgameClockPressureSection.tsx
and asserts they equal the registry values. Catches drift until FE consumers
switch to frontend/src/generated/endgameZones.ts in Phase 66.
"""
import re
from pathlib import Path

from app.services.endgame_zones import (
    BUCKETED_ZONE_REGISTRY,
    NEUTRAL_PCT_THRESHOLD,
    NEUTRAL_TIMEOUT_THRESHOLD,
    ZONE_REGISTRY,
)

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent

def _read_ts(rel_path: str) -> str:
    return (_REPO_ROOT / rel_path).read_text(encoding="utf-8")


class TestEndgameZonesConsistency:
    def test_recovery_band_matches_score_gap_section(self) -> None:
        src = _read_ts("frontend/src/components/charts/EndgameScoreGapSection.tsx")
        # Parse FIXED_GAUGE_ZONES.recovery neutral band boundaries
        match = re.search(r"recovery:.*?GAUGE_NEUTRAL.*?from:\s*([\d.]+).*?to:\s*([\d.]+)", src, re.DOTALL)
        assert match, "Could not find FIXED_GAUGE_ZONES.recovery neutral zone in TS source"
        ts_lower, ts_upper = float(match.group(1)), float(match.group(2))
        py_spec = BUCKETED_ZONE_REGISTRY["recovery_save_pct"]["recovery"]
        assert ts_lower == py_spec.typical_lower
        assert ts_upper == py_spec.typical_upper
```
Design the regex patterns around the actual TS constant literals identified in the RESEARCH.md §"Current Frontend Constants" section.

---

### `frontend/src/components/charts/EndgameScoreGapSection.tsx` (single-line edit)

**Self-reference.** Lines 90-94 (current values read 2026-04-20):
```typescript
  recovery: [
    { from: 0, to: 0.30, color: GAUGE_DANGER },
    { from: 0.30, to: 0.40, color: GAUGE_NEUTRAL },
    { from: 0.40, to: 1.0, color: GAUGE_SUCCESS },
  ],
```
D-10 changes `0.30` → `0.25` and `0.40` → `0.35` in the neutral line only. The `GAUGE_DANGER` upper bound and `GAUGE_SUCCESS` lower bound follow the neutral band boundaries by construction.

---

### `.github/workflows/ci.yml` (config, insert step)

**Self-reference.** Current step order (lines 41-55):
```yaml
      - name: Install Python dependencies
        run: uv sync --locked

      - name: Python vulnerability scan (pip-audit)
        run: uv run --with pip-audit pip-audit --strict

      - name: Lint (ruff)
        run: uv run ruff check .

      - name: Type check (ty)
        run: uv run ty check app/ tests/
```
Insert the new "Zone drift check" step after "Install Python dependencies" and before "Python vulnerability scan":
```yaml
      - name: Zone drift check
        run: |
          uv run python scripts/gen_endgame_zones_ts.py
          git diff --exit-code frontend/src/generated/endgameZones.ts
```
This follows the existing CI pattern of `uv run <script>` for Python steps; `--exit-code` causes the step to fail if the committed file differs from what the generator produces.

---

## Shared Patterns

### Named Constants (no magic numbers)
**Source:** `app/services/openings_service.py` lines 39-53 and `app/services/endgame_service.py` lines 15-100 (constant block).
**Apply to:** `app/services/endgame_zones.py` for every threshold exported.
```python
# Minimum weekly data points in window to compute a trend (FIND-04).
TREND_MIN_WEEKLY_POINTS: int = 20

# Minimum slope-to-volatility ratio to emit a directional trend (FIND-04).
TREND_MIN_SLOPE_VOL_RATIO: float = 0.5
```

### Literal Type Aliases
**Source:** `app/schemas/normalization.py` lines 12-16; `app/schemas/endgames.py` lines 15-16, 169.
**Apply to:** All Literal declarations in `app/schemas/insights.py` and `app/services/endgame_zones.py`.
```python
Zone = Literal["weak", "typical", "strong"]
Trend = Literal["improving", "declining", "stable", "n_a"]
SampleQuality = Literal["thin", "adequate", "rich"]
```

### Pydantic v2 BaseModel
**Source:** `app/schemas/endgames.py` throughout; `app/schemas/normalization.py`.
**Apply to:** All models in `app/schemas/insights.py`.
```python
from pydantic import BaseModel

class SubsectionFinding(BaseModel):
    """Per-subsection per-window finding unit.

    value=float('nan') when zero qualifying games exist for the window (thin sample).
    is_headline_eligible=False when trend gate fails or sample is thin.
    dimension carries per-combo or per-bucket identity (e.g. {"bucket": "conversion"}).
    """
    subsection_id: SubsectionId
    window: Window
    metric_id: MetricId
    value: float
    zone: Zone
    trend: Trend
    sample_size: int
    sample_quality: SampleQuality
    is_headline_eligible: bool
    parent_subsection_id: SubsectionId | None = None
    dimension: dict[str, str] | None = None
```

### Async Service Sequential Pattern (no asyncio.gather)
**Source:** `app/services/endgame_service.py::get_endgame_overview` lines 1895-1960.
**Apply to:** `app/services/insights_service.py::compute_findings`.
All `await` calls on the same `AsyncSession` must be sequential. Per CLAUDE.md §"Critical Constraints": never `asyncio.gather` on the same `AsyncSession`.

### Sentry Exception Capture
**Source:** `app/services/endgame_service.py` (general pattern throughout service).
**Apply to:** `app/services/insights_service.py` non-trivial `except` blocks.
```python
import sentry_sdk

except Exception as exc:
    sentry_sdk.set_context("insights", {"user_id": user_id, "filter_context": filter_context.model_dump()})
    sentry_sdk.capture_exception(exc)
    raise
```
Per CLAUDE.md §"Backend Rules": never embed `user_id` in the error message string; pass via `set_context`.

### ty Compliance
**Source:** CLAUDE.md §"ty compliance".
**Apply to:** All new Python files.
- Return type annotation on every function
- `Sequence[X]` not `list[X]` for covariant parameters
- `# ty: ignore[rule-name]` (not `# type: ignore`) with reason when suppressing

### knip.json ignore convention
**Source:** `frontend/knip.json` lines 14-19.
**Apply to:** `frontend/knip.json` — add `frontend/src/generated/endgameZones.ts` to the `"ignore"` array until Phase 66 consumers switch over.
```json
{
  "ignore": [
    "src/components/ui/command.tsx",
    "src/components/ui/popover.tsx",
    "src/components/ui/input-group.tsx",
    "src/generated/endgameZones.ts"
  ]
}
```

### Test Class Structure
**Source:** `tests/test_endgame_service.py` lines 65-125.
**Apply to:** `tests/services/test_insights_service.py`, `tests/services/test_endgame_zones.py`.
```python
class TestAssignZone:
    """Unit tests for assign_zone direction handling."""

    def test_higher_is_better_below_typical_is_weak(self) -> None:
        """Value below typical_lower → weak for higher_is_better metrics."""
        assert assign_zone("endgame_skill", 0.30) == "weak"

    def test_higher_is_better_in_typical_is_typical(self) -> None:
        assert assign_zone("endgame_skill", 0.50) == "typical"
```

---

## No Analog Found

| File | Role | Data Flow | Reason |
|---|---|---|---|
| `frontend/src/generated/endgameZones.ts` | config | — | First generated/committed TS file in the repo; `frontend/src/generated/` directory does not exist yet |
| `tests/services/test_endgame_zones_consistency.py` | test | — | No existing test regex-parses another source file to assert cross-language constant parity |

---

## Metadata

**Analog search scope:** `app/services/`, `app/schemas/`, `tests/`, `scripts/`, `frontend/src/components/charts/`, `.github/workflows/`
**Files scanned:** 18 source files read in full or in targeted ranges
**Pattern extraction date:** 2026-04-20
