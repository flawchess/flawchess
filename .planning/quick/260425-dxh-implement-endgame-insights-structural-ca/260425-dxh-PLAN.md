---
phase: 260425-dxh
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - app/repositories/import_job_repository.py
  - app/repositories/llm_log_repository.py
  - app/services/insights_llm.py
  - tests/services/test_insights_llm.py
autonomous: true
requirements:
  - QUICK-260425-dxh
must_haves:
  truths:
    - "Calling generate_insights twice in a row with no new imports returns cache_hit on the second call without invoking compute_findings."
    - "A completed import_jobs row with games_imported > 0 and completed_at after the cached row's created_at invalidates the cache."
    - "A completed import_jobs row with games_imported = 0 (no-op resync) does NOT invalidate the cache."
    - "A cached log row older than INSIGHTS_CACHE_MAX_AGE_DAYS (30 days) is treated as a miss even when no qualifying imports occurred."
    - "User A's cached log is never returned to user B (the new lookup filters by user_id)."
    - "compute_findings runs only on the cache-miss path; cache hits skip it entirely."
    - "findings_hash is still populated on cache-miss writes for diagnostics, but is no longer used as a lookup key."
    - "Backend passes uv run ruff check ., uv run ruff format --check ., uv run ty check app/ tests/, and uv run pytest with zero errors."
  artifacts:
    - path: "app/repositories/import_job_repository.py"
      provides: "get_latest_completed_import_with_games_at(session, user_id) -> datetime|None"
    - path: "app/repositories/llm_log_repository.py"
      provides: "get_latest_successful_log_for_user(session, user_id, prompt_version, model, opponent_strength, max_age) -> LlmLog|None"
    - path: "app/services/insights_llm.py"
      provides: "Module constant INSIGHTS_CACHE_MAX_AGE_DAYS=30; rewritten generate_insights with cache-first control flow"
      contains: "INSIGHTS_CACHE_MAX_AGE_DAYS"
    - path: "tests/services/test_insights_llm.py"
      provides: "Tests for cache-hit, import-invalidation, no-op-import non-invalidation, TTL expiry, cross-user isolation, and cache-hit-skips-compute_findings"
  key_links:
    - from: "app/services/insights_llm.py:generate_insights"
      to: "app/repositories/llm_log_repository.py:get_latest_successful_log_for_user"
      via: "Tier-1 lookup BEFORE compute_findings"
      pattern: "get_latest_successful_log_for_user"
    - from: "app/services/insights_llm.py:generate_insights"
      to: "app/repositories/import_job_repository.py:get_latest_completed_import_with_games_at"
      via: "Cache freshness check; row invalid iff max_completed_at > log.created_at"
      pattern: "get_latest_completed_import_with_games_at"
---

<objective>
Replace the unstable `findings_hash`-based tier-1 cache for endgame insights with a structural cache keyed on `(user_id, prompt_version, model, opponent_strength)`, validated against the user's most recent completed import that brought in new games and a 30-day TTL. Move the cache lookup to run BEFORE `compute_findings` so cache hits skip the heavy DB pipeline.

Purpose: today's cache misses on every call (sliding 3-month window + stale_months markers in `EndgameTabFindings` perturb the hash daily even with frozen game corpora), forcing fresh LLM calls even when the user did nothing. After this change, repeat opens of the Endgame tab without new imports serve from cache and skip `compute_findings`.

Output: two new repository helpers, a rewritten `generate_insights`, an `INSIGHTS_CACHE_MAX_AGE_DAYS = 30` module constant, and updated/added tests covering the new validity rules.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
</execution_context>

<context>
@./CLAUDE.md
@app/services/insights_llm.py
@app/repositories/llm_log_repository.py
@app/repositories/import_job_repository.py
@app/models/llm_log.py
@app/models/import_job.py
@app/schemas/llm_log.py
@tests/services/test_insights_llm.py

<interfaces>
Existing types/exports the executor will use directly.

From app/models/llm_log.py:
```python
class LlmLog(Base):
    id: Mapped[int]
    user_id: Mapped[int]                            # FK users.id (Integer, NOT BigInteger)
    created_at: Mapped[datetime.datetime]           # server_default=now()
    endpoint: Mapped[str]                           # "insights.endgame"
    model: Mapped[str]
    prompt_version: Mapped[str]
    findings_hash: Mapped[str]                      # kept; no longer the lookup key
    filter_context: Mapped[dict]                    # JSONB; {"opponent_strength": "..."}
    response_json: Mapped[dict | None]              # cache hit requires NOT NULL
    error: Mapped[str | None]                       # cache hit requires NULL
    cache_hit: Mapped[bool]
    # Index: ix_llm_logs_user_id_created_at (user_id, created_at DESC) — covers new lookup.
```

From app/models/import_job.py:
```python
class ImportJob(Base):
    id: Mapped[str]
    user_id: Mapped[int]                            # FK users.id, indexed
    status: Mapped[str]                             # "pending"|"in_progress"|"completed"|"failed"
    games_imported: Mapped[int]                     # 0 for no-op resyncs
    completed_at: Mapped[datetime.datetime | None]  # set atomically with status="completed"
```

From app/schemas/llm_log.py:
```python
LlmLogEndpoint = Literal["insights.endgame"]

class LlmLogFilterContext(BaseModel):
    opponent_strength: Literal["any", "stronger", "similar", "weaker"]
```

From app/services/insights_llm.py (existing surface that stays):
```python
INSIGHTS_MISSES_PER_HOUR = 3
_PROMPT_VERSION = "endgame_v15"
_RATE_LIMIT_WINDOW = datetime.timedelta(hours=1)
_ENDPOINT: LlmLogEndpoint = "insights.endgame"

# Stays unchanged; just runs less often:
async def compute_findings(filter_context, session, user_id) -> EndgameTabFindings: ...

# Stays for existing rate-limit / tier-2 paths:
count_recent_successful_misses, get_latest_report_for_user, get_oldest_recent_miss_timestamp, create_llm_log
```

From app/repositories/llm_log_repository.py (existing helper to mirror style):
```python
async def get_latest_log_by_hash(session, findings_hash, prompt_version, model) -> LlmLog | None
# DEPRECATE from production hot path — but DO NOT delete; tests + future analytics may use it.
```
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add structural cache helpers + rewrite generate_insights cache flow</name>
  <files>
    app/repositories/import_job_repository.py,
    app/repositories/llm_log_repository.py,
    app/services/insights_llm.py
  </files>
  <action>
**1a. `app/repositories/import_job_repository.py`** — add new helper at module bottom:

```python
async def get_latest_completed_import_with_games_at(
    session: AsyncSession, user_id: int
) -> datetime | None:
    """Return MAX(completed_at) for the user's completed imports that fetched
    new games (games_imported > 0), or None if none exist.

    Used as the cache-invalidation timestamp for the structural insights cache:
    a cached LLM log row is invalid iff its created_at < this timestamp.
    No-op resyncs (games_imported = 0) are intentionally excluded so daily
    syncs that fetch zero games do NOT bust the cache.
    """
    result = await session.execute(
        select(func.max(ImportJob.completed_at)).where(
            ImportJob.user_id == user_id,
            ImportJob.status == "completed",
            ImportJob.games_imported > 0,
        )
    )
    return result.scalar_one_or_none()
```

You'll need to add `from sqlalchemy import func` to the existing `from sqlalchemy import select, update` import (combine: `from sqlalchemy import func, select, update`).

**1b. `app/repositories/llm_log_repository.py`** — add a new helper alongside (NOT replacing) `get_latest_log_by_hash`. Place it after `get_latest_log_by_hash` (around line 163, before `count_recent_successful_misses`):

```python
async def get_latest_successful_log_for_user(
    session: AsyncSession,
    user_id: int,
    prompt_version: str,
    model: str,
    opponent_strength: str,
    max_age: datetime.timedelta,
) -> LlmLog | None:
    """Phase 65 structural-cache lookup (replaces get_latest_log_by_hash on the hot path).

    Returns the most recent successful log row for this user under the current
    (prompt_version, model, opponent_strength) tuple, provided it is younger
    than max_age. The caller is responsible for the additional "no qualifying
    import since created_at" check (see app/services/insights_llm.py).

    "Successful" means response_json IS NOT NULL AND error IS NULL — same rule
    as get_latest_log_by_hash. cost_unknown / provider-error rows do NOT hit.

    Index coverage: ix_llm_logs_user_id_created_at (user_id eq + created_at
    DESC ordering + range on created_at). Remaining filters are cheap on the
    small per-user-per-window slice.

    Args:
        session: caller-supplied AsyncSession (read path).
        user_id: authenticated user (mandatory; this fixes the cross-user
            collision latent in get_latest_log_by_hash).
        prompt_version: current era key (e.g. "endgame_v15").
        model: pydantic-ai provider:model string.
        opponent_strength: matched against filter_context->>'opponent_strength'
            via the JSONB text-extraction operator.
        max_age: TTL for the structural cache (e.g. timedelta(days=30)).

    Returns:
        Most recent matching LlmLog, or None.
    """
    cutoff = datetime.datetime.now(datetime.UTC) - max_age
    result = await session.execute(
        select(LlmLog)
        .where(
            LlmLog.user_id == user_id,
            LlmLog.prompt_version == prompt_version,
            LlmLog.model == model,
            LlmLog.filter_context["opponent_strength"].astext == opponent_strength,
            LlmLog.created_at >= cutoff,
            LlmLog.response_json.is_not(None),
            LlmLog.error.is_(None),
        )
        .order_by(LlmLog.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()
```

Notes:
- Use `LlmLog.filter_context["opponent_strength"].astext == opponent_strength` (SQLAlchemy 2.x JSONB text-extraction). This is the `->>'opponent_strength'` PostgreSQL operator. It works because `filter_context` is `Mapped[dict]` backed by JSONB.
- DO NOT delete `get_latest_log_by_hash` — keep it for tests/analytics.

**1c. `app/services/insights_llm.py`** — three edits:

(i) Add module constant near the top of the constants block (after `_PROMPT_VERSION` around line 60), per CLAUDE.md no-magic-numbers rule:

```python
# Structural cache TTL safety net (260425-dxh): bounds the sliding 3-month
# window narrative drift on cache hits. Lower to 14 if users complain about
# stale narratives.
INSIGHTS_CACHE_MAX_AGE_DAYS = 30
INSIGHTS_CACHE_MAX_AGE = datetime.timedelta(days=INSIGHTS_CACHE_MAX_AGE_DAYS)
```

(ii) Update the imports block. In `from app.repositories.llm_log_repository import (...)`:
- ADD `get_latest_successful_log_for_user`
- REMOVE `get_latest_log_by_hash` (no longer called from this module). The helper itself stays in the repo.

Add a new import line:
```python
from app.repositories.import_job_repository import get_latest_completed_import_with_games_at
```

(iii) Rewrite `generate_insights` (currently lines 1775-1860) so the cache lookup runs BEFORE `compute_findings`. Preserve the existing rate-limit, tier-2 soft-fail, fresh-call, and log-write logic. Updated structure:

```python
async def generate_insights(
    filter_context: FilterContext,
    user_id: int,
    session: AsyncSession,
) -> EndgameInsightsResponse:
    """Tier-1 structural cache -> rate-limit -> tier-2 soft-fail -> fresh LLM call.

    Cache key (260425-dxh): (user_id, prompt_version, model, opponent_strength).
    Validity rule: row.created_at >= MAX(import_jobs.completed_at WHERE
    games_imported > 0) for this user, AND row younger than
    INSIGHTS_CACHE_MAX_AGE. Reordered so compute_findings only runs on miss.

    Returns EndgameInsightsResponse with status in {fresh, cache_hit,
    stale_rate_limited}. Raises InsightsRateLimitExceeded (router -> 429),
    InsightsProviderError (router -> 502), or InsightsValidationFailure
    (router -> 502) on the respective failure paths.
    """
    model = settings.PYDANTIC_AI_MODEL_INSIGHTS

    # Tier-1 STRUCTURAL cache lookup (260425-dxh): cheap query on
    # (user_id, prompt_version, model, opponent_strength) + freshness checks.
    # Runs BEFORE compute_findings so cache hits skip the heavy DB pipeline.
    # Bug-fix note: the previous findings_hash-based lookup was unstable across
    # days because EndgameTabFindings includes time-relative fields (sliding
    # 3-month window stats and stale_months markers), so the hash drifted even
    # with a frozen game corpus. The hash also wasn't user-scoped — a latent
    # cross-user collision risk that the new helper closes by filtering on
    # user_id directly.
    cached = await get_latest_successful_log_for_user(
        session,
        user_id=user_id,
        prompt_version=_PROMPT_VERSION,
        model=model,
        opponent_strength=filter_context.opponent_strength,
        max_age=INSIGHTS_CACHE_MAX_AGE,
    )
    if cached is not None:
        last_import_at = await get_latest_completed_import_with_games_at(session, user_id)
        # Cache row valid only if no qualifying import has happened since it
        # was written. games_imported=0 imports were intentionally excluded
        # in the helper, so no-op resyncs do not invalidate the cache.
        if last_import_at is None or last_import_at <= cached.created_at:
            report = EndgameInsightsReport.model_validate(cached.response_json)
            return EndgameInsightsResponse(
                report=_maybe_strip_overview(report),
                status="cache_hit",
            )

    # Cache miss path: now we pay for compute_findings.
    findings = await compute_findings(filter_context, session, user_id)

    # Rate-limit check (CONTEXT.md D-09, D-10). Unchanged.
    misses = await count_recent_successful_misses(session, user_id, _RATE_LIMIT_WINDOW)
    if misses >= INSIGHTS_MISSES_PER_HOUR:
        fallback = await get_latest_report_for_user(session, user_id, _PROMPT_VERSION, model)
        if fallback is not None:
            stale_report = EndgameInsightsReport.model_validate(fallback.response_json)
            stale = _maybe_stale_filters(fallback, filter_context)
            return EndgameInsightsResponse(
                report=_maybe_strip_overview(stale_report),
                status="stale_rate_limited",
                stale_filters=stale,
            )
        retry_after = await _compute_retry_after(session, user_id)
        raise InsightsRateLimitExceeded(retry_after_seconds=retry_after)

    # Fresh call. (Unchanged from prior implementation.)
    user_prompt = _assemble_user_prompt(findings)
    report, in_tokens, out_tokens, thinking_tokens, latency_ms, marker = await _run_agent(
        user_prompt, user_id, findings.findings_hash
    )
    if report is not None:
        report = report.model_copy(
            update={
                "model_used": model,
                "prompt_version": _PROMPT_VERSION,
            }
        )
    await create_llm_log(
        LlmLogCreate(
            user_id=user_id,
            endpoint=_ENDPOINT,
            model=model,
            prompt_version=_PROMPT_VERSION,
            findings_hash=findings.findings_hash,  # kept for diagnostics, no longer the cache key
            filter_context=LlmLogFilterContext(opponent_strength=filter_context.opponent_strength),
            user_prompt=user_prompt,
            response_json=report.model_dump() if report is not None else None,
            input_tokens=in_tokens,
            output_tokens=out_tokens,
            thinking_tokens=thinking_tokens,
            latency_ms=latency_ms,
            cache_hit=False,
            error=marker,
        )
    )
    if marker == "validation_failure_after_retries":
        raise InsightsValidationFailure(marker)
    if marker is not None or report is None:
        raise InsightsProviderError(marker or "provider_error")
    return EndgameInsightsResponse(
        report=_maybe_strip_overview(report),
        status="fresh",
    )
```

Important constraints/preservation:
- Sequential awaits on `session` only. Never `asyncio.gather` on this session (CLAUDE.md).
- Keep all existing Sentry context patterns and `_run_agent` invocation untouched.
- Keep `findings_hash` populated on the LlmLogCreate write (it's still useful for analytics / "did the LLM input actually change").
- DO NOT remove `get_latest_log_by_hash` from `app/repositories/llm_log_repository.py` — only stop importing it here.
- DO NOT touch `compute_findings` or `_compute_hash` in `app/services/insights_service.py`.
- Add explicit return type annotations on the new helpers (CLAUDE.md ty compliance).
- Run `uv run ruff format .` after editing so formatting matches.
  </action>
  <verify>
    <automated>uv run ruff check . && uv run ruff format --check . && uv run ty check app/ tests/</automated>
  </verify>
  <done>
- `get_latest_completed_import_with_games_at` exists in `app/repositories/import_job_repository.py` and returns `datetime | None`.
- `get_latest_successful_log_for_user` exists in `app/repositories/llm_log_repository.py` alongside `get_latest_log_by_hash` (the old helper is NOT deleted).
- `INSIGHTS_CACHE_MAX_AGE_DAYS = 30` and `INSIGHTS_CACHE_MAX_AGE` are module constants in `app/services/insights_llm.py`.
- `generate_insights` performs the structural cache lookup BEFORE calling `compute_findings`; on cache hit it returns without touching `compute_findings`.
- `get_latest_log_by_hash` is no longer imported in `app/services/insights_llm.py`.
- `findings_hash` is still passed to `LlmLogCreate` on the cache-miss write.
- `uv run ruff check .`, `uv run ruff format --check .`, and `uv run ty check app/ tests/` all pass with zero errors.
  </done>
</task>

<task type="auto">
  <name>Task 2: Update insights LLM tests for the structural cache contract</name>
  <files>tests/services/test_insights_llm.py</files>
  <action>
Update `tests/services/test_insights_llm.py` to reflect the new cache contract. The existing `TestCacheBehavior` class (around line 1855) seeds rows by `findings_hash` — that key no longer matters, but the tests still need to seed `filter_context={"opponent_strength": "any"}` (already correct in `_make_log_row`) and now also need fresh `created_at` plus optionally an import_jobs row.

**2a. Adjust `_make_log_row` if needed.** It already sets `filter_context={"opponent_strength": "any"}` and accepts `created_at` — no signature change required. Verify the existing helper is sufficient.

**2b. Update existing cache tests in `TestCacheBehavior`** so they remain meaningful:

- `test_second_call_cache_hits` — already seeds a row with `error=None`, `model="test"`, opponent_strength via filter_context. The new lookup will find it (no qualifying import_jobs row exists for fresh_test_user). Add a docstring note that the cache key is now structural. Replace the comment block referencing `get_latest_log_by_hash` with one that names `get_latest_successful_log_for_user`.

- `test_prompt_version_bump_misses` — still valid (prompt_version is still part of the key).

- `test_model_swap_misses` — still valid (model is still part of the key).

**2c. Add a new test class `TestStructuralCacheInvalidation` after `TestCacheBehavior`** with these tests. Each follows the existing seeding/monkeypatch pattern:

```python
class TestStructuralCacheInvalidation:
    """Tests for the 260425-dxh structural cache:
    (user_id, prompt_version, model, opponent_strength) + import freshness + 30d TTL.
    """

    @pytest.mark.asyncio
    async def test_import_with_new_games_invalidates_cache(
        self,
        fake_insights_agent: Any,
        fresh_test_user: User,
        test_engine: AsyncEngine,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """A completed import with games_imported > 0 after the cached row
        was written invalidates the cache: next call must be fresh."""
        from app.models.import_job import ImportJob

        report = _sample_report()
        session_maker = async_sessionmaker(test_engine, expire_on_commit=False)

        old = datetime.datetime.now(datetime.UTC) - datetime.timedelta(hours=2)
        newer = datetime.datetime.now(datetime.UTC) - datetime.timedelta(hours=1)
        async with session_maker() as session:
            await _seed(
                session,
                _make_log_row(
                    fresh_test_user.id,
                    created_at=old,
                    response_json=report.model_dump(),
                ),
            )
            session.add(
                ImportJob(
                    id="job-with-games",
                    user_id=fresh_test_user.id,
                    platform="chess.com",
                    username="dxhuser",
                    status="completed",
                    games_fetched=42,
                    games_imported=42,
                    started_at=newer,
                    completed_at=newer,
                )
            )
            await session.commit()

        fake_insights_agent(report)
        monkeypatch.setattr(
            "app.services.insights_llm.compute_findings",
            lambda fc, sess, uid: _fake_compute_findings(fc, sess, uid),
        )

        async with session_maker() as session:
            r = await generate_insights(_sample_filter_context(), fresh_test_user.id, session)
        assert r.status == "fresh"

    @pytest.mark.asyncio
    async def test_no_op_import_does_not_invalidate(
        self,
        fake_insights_agent: Any,
        fresh_test_user: User,
        test_engine: AsyncEngine,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """A completed import with games_imported = 0 (daily resync that
        fetched nothing new) must NOT invalidate the cache."""
        from app.models.import_job import ImportJob

        report = _sample_report()
        session_maker = async_sessionmaker(test_engine, expire_on_commit=False)

        old = datetime.datetime.now(datetime.UTC) - datetime.timedelta(hours=2)
        newer = datetime.datetime.now(datetime.UTC) - datetime.timedelta(hours=1)
        async with session_maker() as session:
            await _seed(
                session,
                _make_log_row(
                    fresh_test_user.id,
                    created_at=old,
                    response_json=report.model_dump(),
                ),
            )
            session.add(
                ImportJob(
                    id="job-no-games",
                    user_id=fresh_test_user.id,
                    platform="chess.com",
                    username="dxhuser",
                    status="completed",
                    games_fetched=0,
                    games_imported=0,
                    started_at=newer,
                    completed_at=newer,
                )
            )
            await session.commit()

        fake_insights_agent(report)
        monkeypatch.setattr(
            "app.services.insights_llm.compute_findings",
            lambda fc, sess, uid: _fake_compute_findings(fc, sess, uid),
        )

        async with session_maker() as session:
            r = await generate_insights(_sample_filter_context(), fresh_test_user.id, session)
        assert r.status == "cache_hit"

    @pytest.mark.asyncio
    async def test_ttl_expiry_misses(
        self,
        fake_insights_agent: Any,
        fresh_test_user: User,
        test_engine: AsyncEngine,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """A cached row older than INSIGHTS_CACHE_MAX_AGE_DAYS is treated as a miss."""
        from app.services.insights_llm import INSIGHTS_CACHE_MAX_AGE_DAYS

        report = _sample_report()
        session_maker = async_sessionmaker(test_engine, expire_on_commit=False)

        too_old = datetime.datetime.now(datetime.UTC) - datetime.timedelta(
            days=INSIGHTS_CACHE_MAX_AGE_DAYS + 1
        )
        async with session_maker() as session:
            await _seed(
                session,
                _make_log_row(
                    fresh_test_user.id,
                    created_at=too_old,
                    response_json=report.model_dump(),
                ),
            )

        fake_insights_agent(report)
        monkeypatch.setattr(
            "app.services.insights_llm.compute_findings",
            lambda fc, sess, uid: _fake_compute_findings(fc, sess, uid),
        )

        async with session_maker() as session:
            r = await generate_insights(_sample_filter_context(), fresh_test_user.id, session)
        assert r.status == "fresh"

    @pytest.mark.asyncio
    async def test_other_users_log_not_returned(
        self,
        fake_insights_agent: Any,
        fresh_test_user: User,
        test_engine: AsyncEngine,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """A log row owned by a different user must not be served as cache hit
        (regression test for the missing user_id filter on the old hash-based lookup)."""
        # Seed a row owned by a fabricated other user_id. The fresh_test_user
        # call must miss because the lookup now filters by user_id.
        report = _sample_report()
        session_maker = async_sessionmaker(test_engine, expire_on_commit=False)

        other_user_id = fresh_test_user.id + 9999  # well beyond any real seeded user
        async with session_maker() as session:
            # Direct insert bypasses FK if other_user_id doesn't exist; if your
            # test DB enforces FK, create a second user via the same fixture
            # pattern instead. Adjust to whichever matches the conftest setup.
            await _seed(
                session,
                _make_log_row(
                    other_user_id,
                    response_json=report.model_dump(),
                ),
            )

        fake_insights_agent(report)
        monkeypatch.setattr(
            "app.services.insights_llm.compute_findings",
            lambda fc, sess, uid: _fake_compute_findings(fc, sess, uid),
        )

        async with session_maker() as session:
            r = await generate_insights(_sample_filter_context(), fresh_test_user.id, session)
        assert r.status == "fresh"

    @pytest.mark.asyncio
    async def test_cache_hit_skips_compute_findings(
        self,
        fake_insights_agent: Any,
        fresh_test_user: User,
        test_engine: AsyncEngine,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Cache hit must NOT invoke compute_findings (the whole point of the rewrite)."""
        report = _sample_report()
        session_maker = async_sessionmaker(test_engine, expire_on_commit=False)

        async with session_maker() as session:
            await _seed(
                session,
                _make_log_row(
                    fresh_test_user.id,
                    response_json=report.model_dump(),
                ),
            )

        called = {"count": 0}

        async def _raising_compute_findings(fc, sess, uid):
            called["count"] += 1
            raise AssertionError("compute_findings must not be called on cache hit")

        fake_insights_agent(report)
        monkeypatch.setattr(
            "app.services.insights_llm.compute_findings",
            _raising_compute_findings,
        )

        async with session_maker() as session:
            r = await generate_insights(_sample_filter_context(), fresh_test_user.id, session)
        assert r.status == "cache_hit"
        assert called["count"] == 0
```

Notes on the cross-user test:
- If the test DB enforces the FK on `llm_logs.user_id -> users.id` (it does — see `app/models/llm_log.py:50-52`), seeding with a fabricated id will fail. In that case, look at the existing `fresh_test_user` fixture in `tests/conftest.py` (or wherever it's defined) and create a sibling `other_test_user` ad-hoc inside the test using the same pattern, then use `other_test_user.id`. If the conftest exposes a factory like `make_user`, prefer that. The test must end up with two distinct real user rows.
- Run `grep -rn "fresh_test_user" tests/conftest.py tests/services/conftest.py 2>/dev/null` to locate the fixture and adapt accordingly.

**2d. Run the full test file** to confirm nothing else broke:

```bash
uv run pytest tests/services/test_insights_llm.py -x
```

If any other existing test in this file (outside `TestCacheBehavior` / `TestStructuralCacheInvalidation`) relied on the old hash-based hit-by-default behavior with explicit `findings_hash="b" * 64` matching, it should still pass because (a) the test seeds rows with `filter_context={"opponent_strength": "any"}` already, and (b) `_sample_filter_context()` defaults to `opponent_strength="any"`. No additional changes expected, but inspect any failure carefully and adjust the seed `created_at` if a test relied on a row being "fresh enough" for the new TTL.

**2e. Final verification:** run the full backend suite + lint + types.
  </action>
  <verify>
    <automated>uv run ruff check . && uv run ruff format --check . && uv run ty check app/ tests/ && uv run pytest tests/services/test_insights_llm.py -x</automated>
  </verify>
  <done>
- `TestCacheBehavior` tests still pass with the new structural cache.
- `TestStructuralCacheInvalidation` class added with five tests: import-with-new-games invalidates, no-op-import does not invalidate, TTL expiry misses, other user's log is not returned, and cache hit skips `compute_findings`.
- Cross-user test creates a real second user row (FK-compliant) rather than relying on a fabricated id.
- `uv run pytest tests/services/test_insights_llm.py -x` passes with zero failures.
- `uv run ruff check .`, `uv run ruff format --check .`, and `uv run ty check app/ tests/` pass with zero errors.
  </done>
</task>

</tasks>

<verification>
End-to-end backend health gate (run after both tasks complete):

```bash
uv run ruff check .
uv run ruff format --check .
uv run ty check app/ tests/
uv run pytest
```

All four must pass with zero errors before the change is considered done.

Manual sanity check (optional, post-merge on dev):
1. `bin/run_local.sh`, log in, open Endgame Insights tab. First call: fresh LLM run, log row written.
2. Reload the tab. Response status should be `cache_hit`; no new pydantic-ai run in backend logs.
3. Trigger a re-sync that fetches 0 new games (re-import a fully-imported account). Reload tab. Still `cache_hit`.
4. Import some new games (different account or delete a few rows then resync). Reload. Status should flip to `fresh`.
</verification>

<success_criteria>
- `get_latest_successful_log_for_user` and `get_latest_completed_import_with_games_at` exist with the documented signatures and behavior.
- `generate_insights` runs the structural cache lookup BEFORE `compute_findings`; cache hits never invoke `compute_findings`.
- `INSIGHTS_CACHE_MAX_AGE_DAYS = 30` is a named module constant (no magic number).
- `findings_hash` is no longer used as a lookup key but is still populated on cache-miss writes.
- The five new structural-cache invariants (cache hit, new-games invalidation, no-op non-invalidation, TTL expiry, cross-user isolation) are covered by tests.
- `uv run pytest`, `uv run ty check app/ tests/`, `uv run ruff check .`, and `uv run ruff format --check .` all pass with zero errors.
- No DB migration is created (no schema change).
- `get_latest_log_by_hash` is preserved in the repository module (not deleted).
- `compute_findings` and `_compute_hash` in `app/services/insights_service.py` are unchanged.
</success_criteria>

<output>
After both tasks complete, create `.planning/quick/260425-dxh-implement-endgame-insights-structural-ca/260425-dxh-SUMMARY.md` documenting:
- What was changed (helpers added, generate_insights rewrite, constant added).
- What was preserved (findings_hash column, get_latest_log_by_hash repo helper, compute_findings).
- Test coverage added (the five new structural-cache tests).
- Verification results (output of the four commands).
</output>
