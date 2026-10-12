---
phase: quick-261012-qiz
plan: 01
quick_id: 261012-qiz
mode: quick
type: execute
wave: 1
depends_on: []
files_modified:
  - app/repositories/llm_log_repository.py
  - app/services/insights_llm.py
  - app/routers/insights.py
  - app/repositories/import_job_repository.py
  - tests/services/test_insights_llm.py
  - tests/test_insights_router.py
  - frontend/src/components/endgames/useEndgameInsightsState.ts
  - frontend/src/components/endgames/useEndgameInsightsState.test.tsx
  - frontend/src/App.tsx
  - CHANGELOG.md
autonomous: true
requirements: ["QUICK-261012-qiz"]

estimate:
  tokens: 85000
  raw_tokens: 85000
  tasks: 3
  confidence: low

must_haves:
  truths:
    - "Two concurrent POST /api/insights/endgame requests for the same user produce exactly ONE LLM call: the second waits on a per-user Postgres advisory xact lock and then returns the first request's report with status cache_hit"
    - "A cached report younger than INSIGHTS_REGEN_COOLDOWN (24h) is served by BOTH POST /api/insights/endgame (cache_hit, no compute_findings, no LLM call) and GET /api/insights/endgame/cached (200) even when a completed import with games_imported > 0 landed after it"
    - "A cached report older than 24h is still invalidated by a later import with games_imported > 0 (POST regenerates as fresh, GET /cached returns 404); a no-op import (games_imported = 0) never invalidates; the 30-day INSIGHTS_CACHE_MAX_AGE still applies"
    - "The POST service path and the GET /cached router path share ONE validity helper in app/services/insights_llm.py, so the two rules cannot drift"
    - "The Endgame Stats tab never auto-fires a Generate request while another Generate request is already in flight (anyGenerating guard)"
    - "Comments/docstrings that describe the cache validity rule mention the 24h cooldown, and CHANGELOG.md [Unreleased] carries user-facing bullets for both changes"
  artifacts:
    - path: "app/repositories/llm_log_repository.py"
      provides: "acquire_insights_generation_lock(session, user_id) issuing the two-int pg_advisory_xact_lock with a named namespace constant"
      contains: "pg_advisory_xact_lock"
    - path: "app/services/insights_llm.py"
      provides: "INSIGHTS_REGEN_COOLDOWN constant, get_cached_insights_response shared helper, lock call at the top of generate_insights"
      contains: "INSIGHTS_REGEN_COOLDOWN"
    - path: "app/routers/insights.py"
      provides: "GET /insights/endgame/cached delegating to insights_llm.get_cached_insights_response"
      contains: "get_cached_insights_response"
    - path: "tests/services/test_insights_llm.py"
      provides: "concurrency dedup test + service-path cooldown tests"
      contains: "TestConcurrentGenerateDedup"
    - path: "tests/test_insights_router.py"
      provides: "router-path cooldown tests (200 within 24h, 404 beyond)"
    - path: "frontend/src/components/endgames/useEndgameInsightsState.ts"
      provides: "anyGenerating early return in the auto-generate effect"
  key_links:
    - from: "app/services/insights_llm.py::generate_insights"
      to: "app/repositories/llm_log_repository.py::acquire_insights_generation_lock"
      via: "first awaited statement on the caller session, BEFORE the cache lookup"
      pattern: "acquire_insights_generation_lock"
    - from: "app/routers/insights.py::get_cached_endgame_insights"
      to: "app/services/insights_llm.py::get_cached_insights_response"
      via: "single shared validity helper (lookup + cooldown + import check + strip overview)"
      pattern: "get_cached_insights_response"
    - from: "app/core/database.py::get_async_session"
      to: "advisory xact lock release"
      via: "session.commit() after yield (normal path) or session close/rollback (exception path) ends the transaction and releases the xact lock"
      pattern: "await session.commit"
---

<objective>
Stop duplicate endgame-insights LLM generations and cap regeneration at once per day.

Bug (prod llm_logs 2026-10-11/12): users 1242, 1277, 1282, 1287 each got two fresh reports 20-60s apart with an identical findings_hash and no import in between. A second POST (page reload or remount) arrived while the first request was still inside compute_findings + the LLM call, before its llm_logs row existed, so both missed the cache and both paid for an LLM call.

Fix (1): a per-user Postgres advisory xact lock at the top of generate_insights serializes same-user generations; the waiter re-runs the cache lookup after the first request's row is committed and returns it as cache_hit. A cheap frontend guard also stops the auto-generate effect from firing while a Generate is already in flight.

Fix (2): a plain 24h regeneration cooldown. A cached row stays valid when it is younger than INSIGHTS_REGEN_COOLDOWN even if an import with new games landed after it. Older rows keep the existing import-invalidation rule. The rule lives in ONE helper shared by the POST service path and the GET /cached router path.

Purpose: stop paying twice for the same report, and stop regenerating on every small import.
Output: lock helper + shared validity helper + cooldown constant (backend), router delegating to the helper, frontend in-flight guard, updated comments, tests proving both behaviors, CHANGELOG bullets.
</objective>

<execution_context>
@~/.claude/gsd-core/workflows/execute-plan.md
@~/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@CLAUDE.md
@app/services/insights_llm.py
@app/routers/insights.py
@app/repositories/llm_log_repository.py
@app/core/database.py
@frontend/src/components/endgames/useEndgameInsightsState.ts

<interfaces>
<!-- Extracted by the planner so the executor does not have to re-explore. -->

app/services/insights_llm.py (current state):
- Line ~101: INSIGHTS_CACHE_MAX_AGE_DAYS = 30 and INSIGHTS_CACHE_MAX_AGE = datetime.timedelta(days=...). Module already imports datetime, sentry_sdk, AsyncSession, settings, get_latest_completed_import_with_games_at, create_llm_log, get_latest_successful_log_for_user, EndgameInsightsReport, EndgameInsightsResponse.
- INSIGHTS_CACHE_OPPONENT_STRENGTH: Literal["any"] = "any"; _PROMPT_VERSION = "endgame_v49".
- _maybe_strip_overview(report) -> EndgameInsightsReport.
- _run_agent(user_prompt: str, user_id: int, findings_hash: str) -> tuple[EndgameInsightsReport | None, int, int, int | None, int, str | None]  (report, in_tokens, out_tokens, thinking_tokens, latency_ms, error_marker).
- generate_insights(user_id: int, session: AsyncSession) -> EndgameInsightsResponse at line ~2657: Tier-1 lookup via get_latest_successful_log_for_user(session, user_id=..., prompt_version=_PROMPT_VERSION, model=settings.PYDANTIC_AI_MODEL_INSIGHTS, opponent_strength=INSIGHTS_CACHE_OPPONENT_STRENGTH, max_age=INSIGHTS_CACHE_MAX_AGE); then get_latest_completed_import_with_games_at(session, user_id); valid iff last_import_at is None or last_import_at <= cached.created_at; then compute_findings -> _assemble_user_prompt -> _run_agent -> create_llm_log (OWN session, commits independently) -> raise or return status="fresh".

app/routers/insights.py GET /endgame/cached (line ~90-127) DUPLICATES that Tier-1 logic inline and imports settings, get_latest_completed_import_with_games_at, get_latest_successful_log_for_user, EndgameInsightsReport, INSIGHTS_CACHE_MAX_AGE, INSIGHTS_CACHE_OPPONENT_STRENGTH for it.

app/core/database.py get_async_session (VERIFIED by planner): `async with async_session_maker() as session: yield session; await session.commit()`. Normal path: the commit after yield ends the transaction and releases any pg_advisory_xact_lock. Exception path: the commit is skipped, the `async with` exit closes the session, and the pooled connection is reset with a rollback, which also releases the xact lock. No idle_in_transaction / lock timeouts are configured anywhere in the repo. Engine has no isolation_level override, so Postgres default READ COMMITTED applies: each statement after lock acquisition gets a fresh snapshot and sees rows committed by the lock holder.

app/models/llm_log.py: created_at is DateTime(timezone=True) (Base.type_annotation_map) with server_default=func.now(), i.e. set by the DB server clock.

Existing advisory-lock precedent: app/services/eval_apply.py uses the single-bigint form with _GAME_WRITE_LOCK_NAMESPACE (0x464C4157) packed into the high 32 bits; tests/conftest.py uses bigint key 7_777_777_777. The two-int4 form lives in a separate key space (pg_locks.objsubid 2 vs 1), so a two-int namespace cannot collide with either. users.id is a plain int autoincrement PK (int4).

Test fixtures (tests/conftest.py): fresh_test_user (committed User, deleted on teardown, llm_logs + import_jobs cascade on user delete), test_engine (per-run DB engine), fake_insights_agent (TestModel factory). The module-level async_session_maker in app.repositories.llm_log_repository is patched to the test DB (create_llm_log writes there).
GOTCHA: in tests settings.PYDANTIC_AI_MODEL_INSIGHTS is "test", which genai-prices does not know, so every row create_llm_log writes gets error="cost_unknown:test" and is NOT cache-eligible (the lookup filters error IS NULL). Any test that needs a generate_insights-written row to serve as a cache hit must monkeypatch app.repositories.llm_log_repository._compute_cost to return Decimal("0").

Existing tests to know:
- tests/services/test_insights_llm.py: helpers _sample_report, _make_log_row(user_id, *, created_at=..., response_json=..., error=..., model="test"), _seed, _fake_compute_findings. Class TestStructuralCacheInvalidation (~line 2764): test_import_with_new_games_invalidates_cache (row 2h old, import 1h old -> asserts fresh; BREAKS under the cooldown), test_no_op_import_does_not_invalidate (row 2h old; would pass trivially via cooldown), test_ttl_expiry_misses, test_other_users_log_not_returned, test_cache_hit_skips_compute_findings.
- tests/test_insights_router.py: helpers _make_row, _seed, fixture authed_user_with_session. TestFilterFree.test_cache_lookup_uses_constant_opponent_strength spies app.services.insights_llm.get_latest_successful_log_for_user and asserts len(lookups) == 1 for one POST. TestCachedEndpoint.test_cache_lookup_uses_constant_opponent_strength spies app.routers.insights.get_latest_successful_log_for_user (BREAKS once the router stops importing that name). TestCachedEndpoint.test_invalidated_by_recent_import (row 2h old, import 1h old -> asserts 404; BREAKS under the cooldown).

frontend/src/components/endgames/useEndgameInsightsState.ts: `anyGenerating = useEndgameInsightsGenerating()` is already computed; the auto-generate useEffect early-returns on `!autoGenerate || !cacheIsEmpty || hasActiveImport`, then checks the module-level autoGeneratedForFetch marker. Its test file mocks useEndgameInsightsGenerating as a constant `() => false` inside vi.mock with vi.hoisted state objects.
</interfaces>
</context>

<tasks>

<task type="tracer" tdd="true">
  <name>Task 1: Per-user advisory lock dedups concurrent generate_insights (tracer: lock -> service -> real-DB concurrency test)</name>
  <files>app/repositories/llm_log_repository.py, app/services/insights_llm.py, tests/services/test_insights_llm.py</files>
  <behavior>
    - Two concurrent generate_insights calls for the same fresh_test_user, each on its OWN AsyncSession from async_sessionmaker(test_engine, expire_on_commit=False), with _run_agent replaced by an async fake that increments a counter, awaits asyncio.sleep(0.3) and returns (report, 100, 50, None, 300, None): the fake is called exactly once, and the two response statuses sorted are ["cache_hit", "fresh"].
    - Without the lock (RED) the same test sees the fake called twice and both statuses "fresh".
  </behavior>
  <action>
RED first. In tests/services/test_insights_llm.py add a new class TestConcurrentGenerateDedup with one async test (pytest.mark.asyncio) using fresh_test_user, test_engine and monkeypatch. Monkeypatch app.services.insights_llm.compute_findings with the existing _fake_compute_findings lambda pattern used elsewhere in the file, monkeypatch app.services.insights_llm._run_agent with the counting/sleeping async fake described in behavior (signature user_prompt, user_id, findings_hash), and monkeypatch app.repositories.llm_log_repository._compute_cost to return Decimal("0") so the row the first call writes has error None and is cache-eligible (document in the test docstring why: model "test" is unknown to genai-prices and would otherwise stamp cost_unknown:test, which the cache lookup rejects). Define an inner coroutine that opens its own session via the session maker, awaits generate_insights(fresh_test_user.id, session), awaits session.commit() (mirrors get_async_session, ends the transaction so the xact lock releases), and returns the response. Run two of them with asyncio.gather (separate sessions, so this does NOT violate the CLAUDE.md one-session gather rule; say so in a one-line comment). Assert the counter equals 1 and the sorted statuses equal ["cache_hit", "fresh"]. Add `import asyncio` to the module imports. Run the test and confirm it FAILS (counter 2) before implementing.

GREEN. In app/repositories/llm_log_repository.py add a module constant INSIGHTS_GENERATION_LOCK_NAMESPACE: int = 0x494E5347 (ASCII "INSG"; fits signed int4) with a comment explaining it is the classid half of the two-int4 advisory-lock form, keyed per user, and that the two-int4 key space is separate from the single-bigint keys used by eval_apply._GAME_WRITE_LOCK_NAMESPACE and the tests/conftest.py template lock, so it cannot collide. Add async def acquire_insights_generation_lock(session: AsyncSession, user_id: int) -> None that executes sqlalchemy text "SELECT pg_advisory_xact_lock(:namespace, :user_id)" with those two bound params (import text from sqlalchemy next to select). Docstring: transaction-scoped, released when the caller's transaction ends (commit or rollback), blocks until the lock is free. Keeping the SQL in the repository honors the CLAUDE.md "no SQL in services" rule. Mention the helper in the module docstring's list of surfaces.

In app/services/insights_llm.py import acquire_insights_generation_lock and call it as the FIRST awaited statement in generate_insights, before the Tier-1 cache lookup. At the call site add a bug-fix comment covering: the prod incident (llm_logs 2026-10-11/12, users 1242, 1277, 1282, 1287 each got two fresh reports 20-60s apart with identical findings_hash and no import between: a second POST from a page reload/remount arrived while the first was still in compute_findings + the LLM call, before its log row existed); how the fix works (the lock serializes same-user generations; create_llm_log commits the row on its OWN session before the first request returns, so when the first request's transaction ends at request teardown, get_async_session's commit after yield, or the close/rollback on the exception path, releases the lock and the waiter's cache lookup, under READ COMMITTED, sees the committed row and returns cache_hit); and the cost (a waiting request holds one pooled connection, which the request already held for the whole LLM call before this change). Do not take the lock in the GET /cached path (read-only, must never block). Update the generate_insights docstring with one sentence about the per-user serialization.

Mutation check (memory rule: prove the fix by reverting it): temporarily comment out the lock call, rerun the new test, confirm it fails with the counter at 2, restore the call, rerun green. Record the RED/revert results in the SUMMARY. Do NOT background the test run.
  </action>
  <verify>
    <automated>uv run pytest tests/services/test_insights_llm.py -k "TestConcurrentGenerateDedup or TestCacheBehavior or TestHappyPath" -x</automated>
  </verify>
  <done>New concurrency test passes with the lock and was observed failing (counter 2) with the lock commented out; acquire_insights_generation_lock exists in app/repositories/llm_log_repository.py and is the first await in generate_insights; the bug-fix comment is at the call site; committed on main (check `git branch --show-current` prints main before committing).</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: 24h regeneration cooldown in one shared validity helper (service + GET /cached router)</name>
  <files>app/services/insights_llm.py, app/routers/insights.py, app/repositories/llm_log_repository.py, tests/services/test_insights_llm.py, tests/test_insights_router.py</files>
  <behavior>
    - Service: cached row 2h old + completed import (games_imported > 0) 1h ago -> generate_insights returns cache_hit and compute_findings is never called (use a raising compute_findings spy like test_cache_hit_skips_compute_findings).
    - Service: cached row 26h old + completed import with games 1h ago -> status "fresh" (this is the existing test_import_with_new_games_invalidates_cache, with its row backdated to 26h).
    - Service: cached row 26h old + no-op import (games_imported = 0) 1h ago -> cache_hit (existing test_no_op_import_does_not_invalidate, row backdated to 26h so it still exercises the games_imported filter instead of passing via the cooldown).
    - Router: GET /api/insights/endgame/cached with row 2h old + import with games 1h ago -> 200 status cache_hit; row 26h old + same import -> 404 (existing test_invalidated_by_recent_import, row backdated to 26h).
    - Router spy: a POST still performs exactly one lookup; the GET /cached spy now patches the service module name and still sees one lookup keyed on opponent_strength "any" and the user's id.
  </behavior>
  <action>
RED first: update and add the tests described in behavior, then run them and confirm the two new within-cooldown tests FAIL (service returns fresh / router returns 404) before implementing.
- tests/services/test_insights_llm.py, class TestStructuralCacheInvalidation: in test_import_with_new_games_invalidates_cache and test_no_op_import_does_not_invalidate change the seeded row's created_at from 2h ago to 26h ago (keep the import at 1h ago) and update their docstrings to say the row is older than the 24h cooldown. Add test_import_within_cooldown_keeps_cache (row 2h ago, ImportJob completed 1h ago with games_fetched/games_imported 42, unique job id, raising compute_findings spy, asserts cache_hit and zero compute calls). Clean up the seeded ImportJob in a try/finally exactly like the existing tests in this class. Use relative offsets from datetime.datetime.now(datetime.UTC) built from the new constant (e.g. INSIGHTS_REGEN_COOLDOWN + timedelta(hours=2) for "older than cooldown") rather than a bare 26 where practical.
- tests/test_insights_router.py, class TestCachedEndpoint: backdate test_invalidated_by_recent_import's cache_written_at to beyond the cooldown and update its docstring. Add test_recent_import_within_cooldown_still_served (row 2h old, import with games_imported 5 completed 1h ago, expects 200 and status cache_hit). Delete the seeded ImportJob rows in a finally block in both tests. In test_cache_lookup_uses_constant_opponent_strength (the GET /cached one) change the monkeypatch target from the router module to "app.services.insights_llm.get_latest_successful_log_for_user", because the router will no longer import that name and monkeypatch.setattr raises on a missing attribute.

GREEN, in app/services/insights_llm.py:
- Next to INSIGHTS_CACHE_MAX_AGE add INSIGHTS_REGEN_COOLDOWN = datetime.timedelta(hours=24) with a comment: a cached report younger than this is served even after an import with new games, so a report is regenerated at most once per day (per user decision for this quick task); the 30-day INSIGHTS_CACHE_MAX_AGE still bounds every row.
- Add a public async def get_cached_insights_response(session: AsyncSession, user_id: int) -> EndgameInsightsResponse | None. It calls the module-level get_latest_successful_log_for_user name (keep calling it through the module global so the existing spies keep working) with the same kwargs generate_insights uses today; returns None if no row. Then: if datetime.datetime.now(datetime.UTC) - cached.created_at < INSIGHTS_REGEN_COOLDOWN the row is valid WITHOUT running the import query; otherwise run get_latest_completed_import_with_games_at and the row is valid iff it is None or <= cached.created_at. Valid -> return EndgameInsightsResponse(report=_maybe_strip_overview(EndgameInsightsReport.model_validate(cached.response_json)), status="cache_hit"); invalid -> None. Docstring states the full validity rule (successful row for (user, prompt_version, model, constant opponent_strength) younger than 30 days AND (younger than 24h OR no import with games since it was written)) and that it is the single rule for both the POST and GET /cached paths. Add a short comment on the "now" choice: real UTC, not the dev_now_utc dependency, because created_at is stamped by the DB server clock (server_default now()) and the repository's 30-day cutoff uses real now too; a shifted dev clock would mis-compare. Keep nesting shallow (early returns).
- In generate_insights replace the inline Tier-1 block (lookup + import check + response build) with ONE call to get_cached_insights_response placed after the lock; return it when not None. Keep the useful parts of the existing explanatory comment (structural key, why findings_hash is no longer the key, runs before compute_findings) and rewrite its validity sentence to the cooldown rule. Update the generate_insights docstring "Validity rule" paragraph accordingly. Update the module docstring's generate_insights bullet if it describes the cache rule.

In app/routers/insights.py: make get_cached_endgame_insights call insights_llm.get_cached_insights_response(session, user.id), raise HTTPException(404, detail="no_cached_report") on None, else return it. Remove the imports that become unused (ruff F401 will list them). Update the function docstring (it shares the validity rule via the helper instead of mirroring it; 200 when a report younger than 24h exists, or an older one with no import with new games since it was written) and the module docstring line for GET /insights/endgame/cached.

In app/repositories/llm_log_repository.py update the get_latest_successful_log_for_user docstring sentence about the caller's additional import check so it points to get_cached_insights_response and mentions the 24h cooldown.

Mutation check: temporarily remove the cooldown short-circuit in get_cached_insights_response, confirm the two within-cooldown tests fail, restore. Record it in the SUMMARY. Do NOT background test runs.
  </action>
  <verify>
    <automated>uv run pytest tests/services/test_insights_llm.py tests/test_insights_router.py tests/test_insights_llm_thinking.py -n auto -x</automated>
  </verify>
  <done>All insights backend tests pass; within-cooldown tests (service + router) were observed failing before the change and when the cooldown short-circuit is reverted; generate_insights and GET /cached both go through get_cached_insights_response; existing import-invalidation coverage is kept (rows backdated beyond 24h, not deleted); `uv run ruff check app/ tests/` and `uv run ty check app/ tests/ scripts/` are clean.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: Frontend in-flight guard, validity-rule comments, CHANGELOG</name>
  <files>frontend/src/components/endgames/useEndgameInsightsState.ts, frontend/src/components/endgames/useEndgameInsightsState.test.tsx, frontend/src/App.tsx, app/repositories/import_job_repository.py, CHANGELOG.md</files>
  <behavior>
    - With useEndgameInsightsGenerating returning true and an empty cache result, rendering useEndgameInsightsState({ autoGenerate: true }) does NOT call mutateAsync.
    - The four existing auto-generate tests stay green.
  </behavior>
  <action>
RED first in frontend/src/components/endgames/useEndgameInsightsState.test.tsx: add a hoisted generatingState object (value false) to the existing vi.hoisted block, make the useEndgameInsightsGenerating mock return generatingState.value, reset it to false in beforeEach, and add a test "does not generate while a Generate request is already in flight" that sets it to true, renders the hook with autoGenerate true and asserts mutateAsync was not called. Run it and confirm it fails.

GREEN in frontend/src/components/endgames/useEndgameInsightsState.ts: add anyGenerating to the auto-generate effect's first early-return condition (before the autoGeneratedForFetch marker is touched, so an in-flight request does not consume the once-per-fetch budget) and to the effect dependency array. Update the hook's header comment: the report is replaced after an import only once it is older than the 24h regeneration cooldown (the server keeps serving a younger report), replacing the "never outlives an import" claim, and mention the effect also stays idle while any Generate is in flight. Mutation check: remove the guard, confirm the new test fails, restore.

frontend/src/App.tsx handleJobDone: rewrite the Phase 238 FE-WR-02 comment above the ['endgame-insights'] invalidation so it says the server answers 404 for a report older than the latest import only once that report is past the 24h regeneration cooldown; the invalidation stays (it is what picks up the new report then). Comment-only change.

app/repositories/import_job_repository.py get_latest_completed_import_with_games_at docstring: say a cached LLM log row is invalidated by this timestamp only once the row is older than the 24h regeneration cooldown (INSIGHTS_REGEN_COOLDOWN in app/services/insights_llm.py). Docstring-only change.

CHANGELOG.md under ## [Unreleased]: add to the existing ### Fixed list a bullet like "Shelly's endgame report is no longer written twice when you reload the Endgames page while it is being generated." and to the existing ### Changed list a bullet like "Shelly's endgame report is refreshed at most once a day: games imported within 24 hours of the last report show up in the next one." Use the existing "Shelly's endgame report" naming; avoid em-dashes (CLAUDE.md).
  </action>
  <verify>
    <automated>( cd frontend && npm run lint && npm test -- --run src/components/endgames ) && ( cd frontend && npm run build )</automated>
  </verify>
  <done>New frontend test passes and was observed failing without the guard; lint, the endgames test folder and the tsc build are green; App.tsx, the hook header and the import_job_repository docstring describe the 24h cooldown; CHANGELOG [Unreleased] has one Fixed and one Changed bullet.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| browser -> POST /api/insights/endgame | authenticated user triggers an LLM call (cost) and now a per-user DB lock |
| browser -> GET /api/insights/endgame/cached | authenticated read of the user's own cached report |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-qiz-01 | Denial of Service | acquire_insights_generation_lock in generate_insights | low | accept | A user firing many concurrent POSTs makes each waiter hold one pooled connection while blocked. Before this change each of those requests held a connection for the full LLM call AND paid for an LLM call, so the lock strictly reduces cost; waiters return fast as cache_hit once the holder commits. Lock is xact-scoped, so it is always released at commit, rollback or connection close. |
| T-qiz-02 | Elevation of Privilege / Tampering | advisory-lock key | low | mitigate | Key is (INSIGHTS_GENERATION_LOCK_NAMESPACE, user.id) where user.id comes from current_active_user, never from request input; the two-int4 key space is disjoint from the bigint keys used by eval_apply and the test template lock, so one user cannot block another user or another subsystem. |
| T-qiz-03 | Information Disclosure | get_cached_insights_response | medium | mitigate | Helper keeps the user_id filter of get_latest_successful_log_for_user; the existing test_other_users_log_not_returned regression test must stay green, and the router passes only the authenticated user's id. |
| T-qiz-04 | Tampering (data freshness) | 24h cooldown | low | accept | A report can lag a fresh import by up to 24h. This is the user's explicit product decision for this task; the 30-day max age still bounds every row. |
| T-qiz-SC | Tampering | npm/pip/cargo installs | low | accept | No package installs in this plan; no new dependencies. |
</threat_model>

<verification>
Run from the repo root, in the foreground (never background a test run):
- uv run ruff format app/ tests/
- uv run ruff check . --fix
- uv run ty check app/ tests/ scripts/
- uv run python scripts/check_function_size.py app/ --fail-over-depth 4
- uv run pytest tests/services/test_insights_llm.py tests/test_insights_router.py tests/test_insights_llm_thinking.py -n auto
- ( cd frontend && npm run lint && npm test -- --run src/components/endgames )
- ( cd frontend && npm run build )
This is a direct commit to main (no squash-merge), so the full pre-merge gate is not required. If ruff format/fix changes files, commit them with a style(...) prefix. Before each commit confirm `git branch --show-current` prints main (the GSD commit helper can recreate a phase branch under the "phase" branching strategy).
</verification>

<success_criteria>
- Concurrent same-user generate_insights calls produce one LLM call and one fresh + one cache_hit response (test proven, and proven to fail without the lock).
- A report younger than 24h survives an import with new games on both the POST and GET /cached paths; an older report is still invalidated; no-op imports never invalidate; the 30-day max age still applies.
- One shared helper (get_cached_insights_response) implements the validity rule for both paths.
- Frontend auto-generate never fires while a Generate is in flight.
- Comments, docstrings and CHANGELOG [Unreleased] reflect the 24h cooldown and the dedup fix.
- ruff, ty, the nesting-depth gate, the insights backend tests and the frontend endgames tests + build are all green.
</success_criteria>

<output>
Create `.planning/quick/261012-qiz-endgame-insights-dedupe-concurrent-llm-g/261012-qiz-SUMMARY.md` when done, including the RED and revert (mutation) observations for each task.
</output>
