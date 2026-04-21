# Phase 65: LLM Endpoint with pydantic-ai Agent - Pattern Map

**Mapped:** 2026-04-21
**Files analyzed:** 13 (5 new + 8 modified)
**Analogs found:** 12 / 13

## File Classification

| New/Modified File | Kind | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|------|-----------|----------------|---------------|
| `app/services/insights_llm.py` | NEW | service (orchestration) | request-response + external-API + DB read/write | `app/services/endgame_service.py` (module-level async service, sentry, `AsyncSession`) + `app/services/insights_service.py` (sequential awaits, sentry context) | role-match (no pydantic-ai analog) |
| `app/services/insights_prompts/endgame_v1.md` | NEW | static text asset (prompt) | file-I/O (read once at import) | no analog (no other loaded-text files in repo) | none — follow RESEARCH.md §6 |
| `app/routers/insights.py` | NEW | router (HTTP) | request-response | `app/routers/endgames.py` | exact |
| `tests/services/test_insights_llm.py` | NEW | unit+integration tests | test fixture + monkeypatch | `tests/services/test_insights_service.py` | role-match |
| `tests/test_insights_router.py` | NEW | integration tests | httpx AsyncClient | `tests/test_endgames_router.py` | exact |
| `tests/test_llm_log_repository_reads.py` | NEW | repo tests | `fresh_test_user` + direct DB | `tests/test_llm_log_repository.py` | exact |
| `tests/services/test_insights_service_series.py` | NEW | unit tests | synthetic Pydantic data | `tests/services/test_insights_service.py` | exact |
| `app/services/insights_service.py` | MOD | service | CRUD (add resampling) | self (existing per-subsection builder pattern) | self-consistent |
| `app/schemas/insights.py` | MOD | schema | transform | self (existing `SubsectionFinding`/`FilterContext`) | self-consistent |
| `app/repositories/llm_log_repository.py` | MOD | repository (reads) | DB read | self (`get_latest_log_by_hash`) | self-consistent |
| `app/main.py` | MOD | app wiring | lifespan | self (`cleanup_orphaned_jobs`) | self-consistent |
| `app/core/config.py` | MOD | config | env vars | self (`SENTRY_DSN`/`SECRET_KEY` pattern) | self-consistent |
| `tests/conftest.py` | MOD | test fixtures | env-var-before-import | self (lines 1-13) | self-consistent |

**Test layout note:** CONTEXT.md D-41 proposes `tests/routers/...`, `tests/repositories/...` sub-directories. Those sub-directories DO NOT exist in the codebase — flat `tests/*.py` is the rule for router and repository tests (see `tests/test_endgames_router.py`, `tests/test_llm_log_repository.py`). Only `tests/services/` exists as a sub-directory. The table above normalizes the paths to match the actual layout. Planner should confirm this with the user (CONTEXT.md may be idealizing) or leave a note for the executor; either way, `tests/test_insights_router.py` and `tests/test_llm_log_repository_reads.py` at the flat root match conventions best.

---

## Pattern Assignments

### `app/services/insights_llm.py` (service, orchestration)

**Primary analog:** `app/services/endgame_service.py` (module-level async orchestration service with `AsyncSession` arg)
**Secondary analog:** `app/services/insights_service.py` (sequential awaits + sentry context pattern)

#### Module-docstring + import pattern

From `app/services/insights_service.py:1-47`:

```python
"""Endgame findings service: transforms `EndgameOverviewResponse` composites into
deterministic findings for the LLM prompt assembly in Phase 65.

Scope (Phase 63):
- `compute_findings(filter_context, session, user_id)` is the sole public entry
  point. ...
Critical invariants:
- Two sequential awaits of `get_endgame_overview`, never concurrent gather
  ...
- Non-trivial except blocks call `sentry_sdk.set_context` with structured
  data, not variable-in-message strings (CLAUDE.md §Sentry).
"""

import datetime
import hashlib
import json
import math
import statistics

import sentry_sdk
from sqlalchemy.ext.asyncio import AsyncSession
```

Phase 65 mirrors: header docstring (scope + critical invariants), stdlib-first imports, `sentry_sdk`, `AsyncSession`.

#### Module-level constants (pattern for `INSIGHTS_MISSES_PER_HOUR`, `_PROMPT_VERSION`, `_OUTPUT_RETRIES`, `_SYSTEM_PROMPT`)

From `app/services/endgame_service.py:165-174, 817-842`:

```python
_MATERIAL_ADVANTAGE_THRESHOLD = 100
_MIN_OPPONENT_SAMPLE = 10
SCORE_GAP_TIMELINE_WINDOW = 100
...
MIN_GAMES_FOR_CLOCK_STATS = 10
NUM_BUCKETS = 10
BUCKET_WIDTH_PCT = 10  # each bucket spans 10 percentage points
```

And from `app/repositories/llm_log_repository.py:33-35`:

```python
_COST_UNKNOWN_PREFIX = "cost_unknown:"  # kept stable + LIKE-queryable
_ERROR_JOIN_SEP = "; "
_MODEL_SEP = ":"
```

**Apply:** module-level UPPER_SNAKE for public constants, `_LEADING_UNDERSCORE` for internal. Attach a one-line inline comment stating semantics when the name is non-obvious.

#### Sequential-await + Sentry `set_context` on exception (load-bearing invariant)

From `app/services/insights_service.py:110-136`:

```python
try:
    all_time_resp = await get_endgame_overview(
        session=session,
        user_id=user_id,
        ...
    )
    last_3mo_resp = await get_endgame_overview(
        session=session,
        ...
    )
except Exception as exc:
    # CLAUDE.md §Sentry: pass variable data via set_context; never embed
    # user_id or filter_context values in the error message (grouping).
    sentry_sdk.set_context("insights", {"user_id": user_id, "filter_context": filter_context.model_dump()})
    sentry_sdk.capture_exception(exc)
    raise
```

**Apply:** `generate_insights` and `_run_agent` follow the same try/except shape. Re-raise after `set_context`+`capture_exception`; never swallow. Call site in `generate_insights` passes `findings_hash` and `model` in the `insights` context dict.

#### Custom exception classes (for router mapping)

No direct analog of custom request-exception classes in `app/services/`. Closest: `import_service` raises stdlib `RuntimeError`/`ValueError` and lets the router-level handler map them. Phase 65's three domain exceptions (`InsightsRateLimitExceeded`, `InsightsProviderError`, `InsightsValidationFailure`) are new. Follow RESEARCH.md §7 snippet verbatim:

```python
class InsightsRateLimitExceeded(Exception):
    def __init__(self, retry_after_seconds: int) -> None:
        self.retry_after_seconds = retry_after_seconds

class InsightsProviderError(Exception):
    def __init__(self, error_marker: str) -> None:
        self.error_marker = error_marker

class InsightsValidationFailure(Exception):
    """Structured-output validation exhausted output_retries."""
```

#### Agent singleton + lazy construction (LLM-02)

No analog exists — pydantic-ai is new to the codebase. Follow RESEARCH.md §6 exactly:

```python
@functools.lru_cache(maxsize=1)
def get_insights_agent() -> Agent[None, EndgameInsightsReport]:
    model = settings.PYDANTIC_AI_MODEL_INSIGHTS
    return Agent(
        model,
        output_type=EndgameInsightsReport,
        system_prompt=_SYSTEM_PROMPT,
        output_retries=_OUTPUT_RETRIES,
    )
```

**Key RESEARCH.md findings to preserve:** `output_type=` not `result_type=`; `output_retries=2`; `_SYSTEM_PROMPT` loaded at module import via `(_PROMPTS_DIR / "endgame_v1.md").read_text(encoding="utf-8")`.

---

### `app/routers/insights.py` (router, request-response)

**Analog:** `app/routers/endgames.py` (exact match for prefix/tags + session/auth dep pattern)

#### Imports + router instantiation (lines 1-24 of endgames.py)

```python
"""Endgames router: HTTP endpoints for endgame analytics.

Endpoints (all mounted under /api/endgames):
- GET /overview: all four endgame dashboard payloads in a single request
- GET /games: paginated game list filtered by endgame class
"""

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.models.user import User
from app.schemas.endgames import (
    EndgameClass,
    EndgameGamesResponse,
    EndgameOverviewResponse,
)
from app.repositories.query_utils import DEFAULT_ELO_THRESHOLD
from app.services import endgame_service
from app.users import current_active_user

router = APIRouter(prefix="/endgames", tags=["endgames"])
```

**Apply verbatim:** `router = APIRouter(prefix="/insights", tags=["insights"])`. Decorators use relative paths (`@router.post("/endgame", ...)`), NEVER `@router.post("/insights/endgame")` (CLAUDE.md §Router Convention).

#### Route body with Annotated dep injection + Query params (lines 27-61)

```python
@router.get("/overview", response_model=EndgameOverviewResponse)
async def get_endgame_overview(
    session: Annotated[AsyncSession, Depends(get_async_session)],
    user: Annotated[User, Depends(current_active_user)],
    time_control: list[str] | None = Query(default=None),
    platform: list[str] | None = Query(default=None),
    recency: str | None = Query(default=None),
    rated: bool | None = Query(default=None),
    opponent_type: str = Query(default="human"),
    window: int = Query(default=50, ge=5, le=200),
    opponent_strength: Literal["any", "stronger", "similar", "weaker"] = Query(default="any"),
    elo_threshold: int = Query(default=DEFAULT_ELO_THRESHOLD),
) -> EndgameOverviewResponse:
    """Return all four endgame dashboard payloads in a single response."""
    return await endgame_service.get_endgame_overview(
        session,
        user_id=user.id,
        time_control=time_control,
        ...
    )
```

**Apply:** `POST /endgame` route copies the filter-Query-param surface (D-31 matches `/endgames/overview`), constructs `FilterContext(**params)`, and calls `insights_llm.generate_insights(filter_context, user.id, session)`. Router body = zero business logic (D-33).

#### Exception → HTTPException mapping

No in-repo analog for custom-exception→HTTP mapping at the router layer (most services let exceptions propagate to FastAPI's default handler). Follow RESEARCH.md §7 snippet. Uses `HTTPException(status_code=..., detail=InsightsErrorResponse(...).model_dump())`.

---

### `app/services/insights_service.py` (MOD — extend with resampling + `series` field)

**Self-analog:** existing per-subsection builder functions (e.g., `_finding_score_gap_timeline`, `_finding_overall` at lines 194-260).

#### Existing per-subsection builder shape to extend (lines 224-260)

```python
def _finding_score_gap_timeline(
    response: EndgameOverviewResponse,
    window: Window,
) -> SubsectionFinding:
    """score_gap_timeline -> trend over score_gap_material.timeline series."""
    timeline: list[ScoreGapTimelinePoint] = response.score_gap_material.timeline
    if not timeline:
        return _empty_finding("score_gap_timeline", window, "score_gap")

    series = [p.score_difference for p in timeline]
    trend, weekly_points = _compute_trend(series)
    last_value = series[-1]
    sample_size = len(series)
    quality = sample_quality("score_gap_timeline", sample_size)
    is_headline = trend != "n_a"
    return SubsectionFinding(
        subsection_id="score_gap_timeline",
        ...
    )
```

**Apply:** add a new `series=_weekly_points_to_time_points(weekly, window)` kwarg to the four timeline builders (`_finding_score_gap_timeline`, `_finding_clock_diff_timeline`, `_findings_endgame_elo_timeline`, `_findings_type_win_rate_timeline`). Non-timeline builders leave `series=None` (default from schema).

#### Resampling helper placement

Add `_weekly_points_to_time_points(weekly, window)` and `_series_for_endgame_elo_combo(combo, window, min_games_floor)` near the top of `insights_service.py`, alongside existing stdlib helpers. Follow RESEARCH.md §5 code verbatim; use `statistics.mean` + `collections.defaultdict`; weighted-by-n mean (recommended). Place new threshold `_ENDGAME_ELO_COMBO_MIN_GAMES = 10` at module scope (matches `_MIN_OPPONENT_SAMPLE = 10` pattern in `endgame_service.py:170`).

---

### `app/schemas/insights.py` (MOD — add new envelope + report schemas)

**Self-analog:** existing `SubsectionFinding`, `FilterContext`, `EndgameTabFindings` (lines 92-186).

#### Pydantic v2 + Literal field convention (lines 69-84)

```python
FlagId = Literal[
    "baseline_lift_mutes_score_gap",
    "clock_entry_advantage",
    "no_clock_entry_advantage",
    "notable_endgame_elo_divergence",
]

SectionId = Literal[
    "overall",
    "metrics_elo",
    "time_pressure",
    "type_breakdown",
]
```

**Apply to new envelope:**

```python
InsightsStatus = Literal["fresh", "cache_hit", "stale_rate_limited"]
InsightsError = Literal["rate_limit_exceeded", "provider_error", "validation_failure", "config_error"]
```

Module-level type aliases above the classes that use them.

#### BaseModel + Field + declaration-order rule (lines 133-165)

```python
class SubsectionFinding(BaseModel):
    """Finding for one subsection x one time window.

    ... Field declaration order is load-bearing for ``findings_hash`` stability ...
    """

    subsection_id: SubsectionId
    parent_subsection_id: SubsectionId | None = None
    window: Window
    metric: MetricId
    value: float
    zone: Zone
    trend: Trend
    weekly_points_in_window: int
    sample_size: int
    sample_quality: SampleQuality
    is_headline_eligible: bool
    dimension: dict[str, str] | None = None
```

**Apply:** add `series: list[TimePoint] | None = None` as the last field on `SubsectionFinding` (declaration order = hash invariant; appending is safe, reordering is not).

#### `model_validator` pattern (for `EndgameInsightsReport.unique_section_ids`)

No existing `model_validator` in `insights.py`. Pydantic v2 syntax per RESEARCH.md §pydantic-ai API + CONTEXT.md §Specifics:

```python
from pydantic import BaseModel, Field, model_validator
from typing import Self

class EndgameInsightsReport(BaseModel):
    overview: str
    sections: list[SectionInsight] = Field(..., min_length=1, max_length=4)
    model_used: str
    prompt_version: str

    @model_validator(mode="after")
    def unique_section_ids(self) -> Self:
        ids = [s.section_id for s in self.sections]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate section_id")
        return self
```

**Apply:** add `SectionInsight`, `EndgameInsightsReport`, `EndgameInsightsResponse`, `InsightsErrorResponse`, `TimePoint` schemas. Extend `__all__` (lines 46-58) with the new names. `FilterContext` (already defined) is reused for `EndgameInsightsResponse.stale_filters`.

---

### `app/repositories/llm_log_repository.py` (MOD — add 2 read helpers)

**Self-analog:** existing `get_latest_log_by_hash` (lines 118-155).

```python
async def get_latest_log_by_hash(
    session: AsyncSession,
    findings_hash: str,
    prompt_version: str,
    model: str,
) -> LlmLog | None:
    """Phase 65 cache-lookup stub. Returns most recent successful log for the key.

    UNLIKE create_llm_log, this read helper takes a caller-supplied session —
    Phase 65's cache-lookup path already has one, and reads don't have the
    durability-across-rollback motivation that writes do.

    "Successful" means response_json IS NOT NULL and error IS NULL — a row
    written with error set (e.g., provider error, cost_unknown) is NOT a
    cache hit.
    """
    result = await session.execute(
        select(LlmLog)
        .where(
            LlmLog.findings_hash == findings_hash,
            LlmLog.prompt_version == prompt_version,
            LlmLog.model == model,
            LlmLog.response_json.is_not(None),
            LlmLog.error.is_(None),
        )
        .order_by(LlmLog.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()
```

**Apply to `count_recent_successful_misses` and `get_latest_report_for_user`:**

- Same `async def` + `AsyncSession` param + caller-supplied session.
- Same `select(...).where(LlmLog.col.is_not(None), LlmLog.col.is_(None))` idiom for NULL checks.
- Same docstring header ("UNLIKE create_llm_log, this read helper ...").
- `.execute()` then `.scalar_one()` (for count) or `.scalar_one_or_none()` (for report lookup).

Use RESEARCH.md §4 SQL snippets verbatim.

---

### `app/main.py` (MOD — add lifespan Agent validation call)

**Self-analog:** existing `lifespan` (lines 42-45).

```python
@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    await cleanup_orphaned_jobs()
    yield
```

**Apply (RESEARCH.md §6):**

```python
@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    # D-22: validate insights agent FIRST — startup failure is a deploy-blocker.
    get_insights_agent()  # raises UserError / ValueError on misconfig
    await cleanup_orphaned_jobs()
    yield
```

Add import `from app.services.insights_llm import get_insights_agent` next to the existing `from app.services.import_service import cleanup_orphaned_jobs` (line 17). Register the new router: add `from app.routers.insights import router as insights_router` and `app.include_router(insights_router, prefix="/api")` alongside the existing `include_router` calls (lines 72-79).

---

### `app/core/config.py` (MOD — add 2 env vars)

**Self-analog:** existing `SENTRY_DSN` / `SECRET_KEY` pattern.

```python
class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://..."
    ...
    SECRET_KEY: str = "change-me-in-production"
    ...
    SENTRY_DSN: str = ""  # Empty string = Sentry disabled (dev default)
    SENTRY_TRACES_SAMPLE_RATE: float = 0.0  # 0.0 = no traces (dev default)

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
```

**Apply:**

```python
    PYDANTIC_AI_MODEL_INSIGHTS: str = ""  # Empty = unconfigured, lifespan raises
    INSIGHTS_HIDE_OVERVIEW: bool = False
```

Inline comments per existing convention. No `Literal` — pydantic-ai accepts arbitrary model strings at runtime.

---

### `tests/conftest.py` (MOD — add env var + import-order)

**Self-analog:** lines 1-13 (env-var-before-import pattern).

```python
import asyncio
import os
import uuid

# Disable Sentry before any app imports — must precede app.core.config which
# reads SENTRY_DSN from env/.env. ...
os.environ["SENTRY_DSN"] = ""

# Use a full-length (32-byte) SECRET_KEY for tests ...
os.environ["SECRET_KEY"] = "test-secret-key-32-bytes-exactly-ok-for-hs256-tests"

import chess
import pytest
...
```

**Apply:** add `os.environ["PYDANTIC_AI_MODEL_INSIGHTS"] = "test"` between lines 13 and 15, with inline comment ("Pydantic-AI's `test` provider prefix passes startup validation; individual tests override with TestModel/FunctionModel.").

#### `fake_insights_agent` fixture — new fixture, no existing analog for pydantic-ai

Follow D-38 + RESEARCH.md §2 (TestModel). Use `monkeypatch.setattr("app.services.insights_llm.get_insights_agent", lambda: fake_agent)`. Place in `tests/conftest.py` next to `starting_board` / `empty_board` (~line 148), or in a new `tests/services/conftest.py` if preferred.

Fixture pattern borrowed from `override_get_async_session` autouse (lines 103-144):

```python
@pytest.fixture
def fake_insights_agent(monkeypatch):
    from pydantic_ai import Agent
    from pydantic_ai.models.test import TestModel
    from app.schemas.insights import EndgameInsightsReport
    import app.services.insights_llm as insights_llm

    def _make(report: EndgameInsightsReport):
        agent = Agent(
            TestModel(custom_output_args=report.model_dump()),
            output_type=EndgameInsightsReport,
        )
        insights_llm.get_insights_agent.cache_clear()
        monkeypatch.setattr(insights_llm, "get_insights_agent", lambda: agent)
        return agent

    return _make
```

---

### `tests/services/test_insights_llm.py` (NEW)

**Analog:** `tests/services/test_insights_service.py` (same sub-directory, same `TestComputeX` class layout, same synthetic-data approach).

#### Test-class organization (lines 65-160 of the analog)

```python
"""Tests for app/services/insights_service.py — Phase 63 Plan 05.

Coverage by requirement:
- FIND-01 (layering): TestComputeFindingsLayering asserts ...
- FIND-03 (flags): TestComputeFlags exercises ...
...
"""

from __future__ import annotations

import inspect
import math
from unittest.mock import AsyncMock, patch

import pytest

import app.services.insights_service as insights_module
from app.schemas.insights import (
    EndgameTabFindings,
    FilterContext,
    ...
)
from app.services.insights_service import (
    _compute_flags,
    _compute_hash,
    _compute_trend,
    _empty_finding,
    compute_findings,
)


class TestComputeTrend:
    """Unit tests for _compute_trend: count gate + slope/volatility gate."""

    def test_count_fail_returns_n_a(self) -> None: ...
    def test_both_pass_improving(self) -> None: ...
```

**Apply:** one `TestX` class per concern (TestAgentWiring, TestPromptAssembly, TestStartupValidation, TestSoftFailTiering, TestRateLimitBoundary). Use `AsyncMock`/`patch` on `get_latest_log_by_hash`, `count_recent_successful_misses`, `create_llm_log` for most tests; use `fake_insights_agent` fixture for the agent.

---

### `tests/test_insights_router.py` (NEW — flat root, not `tests/routers/`)

**Analog:** `tests/test_endgames_router.py` (exact pattern match).

#### Auth + httpx AsyncClient fixture (lines 30-46)

```python
@pytest_asyncio.fixture(scope="module")
async def auth_headers() -> dict[str, str]:
    """Register a fresh user once per module and return auth headers."""
    email = f"endgames_router_test_{uuid.uuid4().hex[:8]}@example.com"
    password = "testpassword123"

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        await client.post("/api/auth/register", json={"email": email, "password": password})
        login_resp = await client.post(
            "/api/auth/jwt/login",
            data={"username": email, "password": password},
        )
        token = login_resp.json()["access_token"]

    return {"Authorization": f"Bearer {token}"}
```

**Apply:** identical fixture name prefix rename (`insights_router_test_...@example.com`). Use `fake_insights_agent` fixture (new, from conftest) to stub the Agent for happy-path / rate-limit / cache-hit tests.

---

### `tests/test_llm_log_repository_reads.py` (NEW — flat root, mirrors `test_llm_log_repository.py`)

**Analog:** `tests/test_llm_log_repository.py` (exact pattern match — same `_build_payload` helper, same `fresh_test_user` dependency).

#### Payload-builder + fresh_test_user pattern (lines 32-80)

```python
def _build_payload(user_id: int, **overrides: Any) -> LlmLogCreate:
    """Build a minimal-valid LlmLogCreate, letting callers override one field."""
    defaults: dict[str, Any] = dict(
        user_id=user_id,
        endpoint="insights.endgame",
        model="anthropic:claude-haiku-4-5-20251001",
        prompt_version="endgame_v1",
        findings_hash="a" * 64,
        ...
    )
    defaults.update(overrides)
    return LlmLogCreate(**defaults)


@pytest.mark.asyncio
async def test_create_llm_log_inserts_and_returns_row(fresh_test_user: User) -> None:
    """Happy path: known model → cost computed, error None, row persisted."""
    data = _build_payload(fresh_test_user.id)
    row = await create_llm_log(data)
    ...
```

**Apply verbatim:** reuse `_build_payload`. Tests:
- `test_count_recent_successful_misses_counts_only_successful_misses` — seed one success, one `error="..."`, one `cache_hit=True`, one outside window; assert count=1.
- `test_count_recent_successful_misses_empty_returns_zero`.
- `test_get_latest_report_for_user_returns_most_recent`.
- `test_get_latest_report_for_user_filters_by_prompt_version_and_model`.
- `test_get_latest_report_for_user_skips_error_rows`.

Need direct DB reads via fresh session (pattern from `fresh_test_user` + `async_sessionmaker(test_engine, expire_on_commit=False)`; see `tests/test_llm_log_repository.py:22-28`).

---

### `tests/services/test_insights_service_series.py` (NEW)

**Analog:** `tests/services/test_insights_service.py` (same dir, same class-based layout, same `_make_finding` helper idea for synthetic Pydantic).

**Apply:** `TestResampleMonthly`, `TestResampleWeeklyPassthrough`, `TestEndgameEloGapOnly`, `TestSparseCombo`, `TestTypeWinRateMonthly` classes. No DB access — pure function tests over synthetic weekly-tuple input.

---

### `app/services/insights_prompts/endgame_v1.md` (NEW — static asset)

**Analog:** none. No other repo-loaded text files exist (`openings.tsv` is binary data, different category).

**Apply (from CONTEXT.md D-29 + D-30 + SEED-003):** markdown file, UTF-8. Contains:
1. Agent role + output contract.
2. Metric glossary (D-30; ~80-150 lines).
3. Section-gating rules (D-19: "include a section only when sample_size > 0 AND sample_quality != 'thin'").
4. Cross-section flag interpretations.
5. Overview-paragraph constraints (≤150 words; always populate — INS-06).

Loaded via `(Path(__file__).parent / "insights_prompts" / "endgame_v1.md").read_text(encoding="utf-8")` (RESEARCH.md §6).

---

### `pyproject.toml` (MOD — add pydantic-ai-slim)

**Self-analog:** existing deps list. Single-line addition per RESEARCH.md §8:

```toml
"pydantic-ai-slim[anthropic,google]>=1.85,<2.0",
```

---

### `.env.example` (MOD — document 2 new env vars)

**Self-analog:** existing `.env.example` entries (read it to confirm layout). RESEARCH.md §3 provides the final copy:

```bash
# LLM insights (Phase 65+)
# Supports any pydantic-ai model string; requires matching provider API key set.
PYDANTIC_AI_MODEL_INSIGHTS=anthropic:claude-haiku-4-5-20251001
ANTHROPIC_API_KEY=sk-ant-...
# Set INSIGHTS_HIDE_OVERVIEW=true to strip report.overview before returning to client
# (full overview is still captured in llm_logs.response_json for offline analysis).
INSIGHTS_HIDE_OVERVIEW=false
```

---

## Shared Patterns

### Sentry capture with `set_context`

**Source:** `app/services/insights_service.py:131-136` + CLAUDE.md §Sentry.
**Apply to:** every non-trivial `except` in `insights_llm.generate_insights` and `_run_agent`.

```python
except Exception as exc:
    sentry_sdk.set_context("insights", {"user_id": ..., "findings_hash": ..., "model": ..., "endpoint": "insights.endgame"})
    sentry_sdk.capture_exception(exc)
    raise
```

**NEVER** embed variables in exception messages — they fragment Sentry grouping. Error markers on `llm_logs.error` column use stable enum-like prefixes only (`"provider_error"`, `"validation_failure_after_retries"`).

### Repository reads: caller-supplied session

**Source:** `app/repositories/llm_log_repository.py:118-155` (`get_latest_log_by_hash`).
**Apply to:** `count_recent_successful_misses`, `get_latest_report_for_user`.

```python
async def xxx(
    session: AsyncSession,
    user_id: int,
    ...
) -> T | None:
    """UNLIKE create_llm_log, this read helper takes a caller-supplied session —
    [caller's path] already has one, and reads don't have the
    durability-across-rollback motivation that writes do.
    """
    result = await session.execute(select(LlmLog).where(...).order_by(...).limit(...))
    return result.scalar_one_or_none()
```

### Pydantic v2: `BaseModel` + `Literal` + `Field` + declaration-order

**Source:** `app/schemas/insights.py:69-186`.
**Apply to:** every new schema in Phase 65. No `Enum`; use `Literal[...]`. No `BaseModel.Config` (use `model_config = ...` on v2). Field declaration order is load-bearing for `findings_hash` — append, never reorder, in `SubsectionFinding`.

### Test fixture: env-var-before-import

**Source:** `tests/conftest.py:1-13`.
**Apply to:** `tests/conftest.py` extension. Place `os.environ["PYDANTIC_AI_MODEL_INSIGHTS"] = "test"` at the TOP of the file, before any `from app.main import ...` or `from app.services.insights_llm import ...`. Pydantic-AI's `test` provider prefix passes `get_insights_agent()` startup validation; individual tests then override via monkeypatch.

### Router convention

**Source:** `app/routers/endgames.py:24` + CLAUDE.md §Router Convention.
**Apply to:** `app/routers/insights.py`.

```python
router = APIRouter(prefix="/insights", tags=["insights"])

@router.post("/endgame", response_model=EndgameInsightsResponse)  # relative path only
async def get_endgame_insights(...): ...
```

Never `@router.post("/insights/endgame", ...)`. `main.py` does `include_router(..., prefix="/api")`, yielding final path `/api/insights/endgame`.

### FastAPI dependency pattern

**Source:** `app/routers/endgames.py:28-29`.
**Apply to:** every new route.

```python
session: Annotated[AsyncSession, Depends(get_async_session)],
user: Annotated[User, Depends(current_active_user)],
```

Imports: `from app.core.database import get_async_session`; `from app.users import current_active_user`; `from app.models.user import User`.

### ty compliance (CLAUDE.md)

Explicit return type annotations on every new function. Use `Sequence[T]` (not `list[T]`) for parameters accepting `list[Literal[...]]`. No bare `str` for Literal-field parameters. Use `# ty: ignore[rule-name]` with a rule name + reason when unavoidable (should not be needed in Phase 65).

---

## No Analog Found

| File | Reason |
|------|--------|
| `app/services/insights_prompts/endgame_v1.md` | No existing loaded text assets in repo. Pure new convention; follow D-27/D-30 + RESEARCH.md §6. |

All other files have at least a self-analog or a close role+data-flow match.

---

## Metadata

**Analog search scope:** `app/services/`, `app/routers/`, `app/repositories/`, `app/schemas/`, `app/models/`, `app/core/`, `tests/`, `tests/services/`.
**Files scanned:** 16.
**Pattern extraction date:** 2026-04-21.
