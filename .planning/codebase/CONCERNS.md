# Codebase Concerns

**Analysis Date:** 2026-05-30

> Scope: full repo. Backend `app/` (FastAPI / Python 3.13), frontend `frontend/src/`
> (React 19 / TS / Vite). This codebase is unusually disciplined for its age:
> almost zero `TODO`/`FIXME`/`HACK` markers (3 total, all benign doc references to a
> literal `"(p = X.XXX)"` string), no stray `.bak`/`.orig` files in source trees
> (one archived `.bak` under `.planning/`), broad-except blocks are paired with
> `sentry_sdk.capture_exception`, settings are centralized in a typed
> `pydantic-settings` object (`app/core/config.py`), and rate limiting exists on the
> guest-creation and insights endpoints. The concerns below are therefore mostly
> *structural* (oversized files, in-memory state, operational fragility) rather than rot.

## Tech Debt

**In-memory import-job registry (single-process assumption baked in):**
- Issue: The authoritative live import-job state is an in-memory dict in `import_service.py` (`JobState` dataclass, `JobStatus` enum). `app/schemas/imports.py:62` and `app/routers/imports.py:150` both explicitly note "In-memory only — orphaned DB jobs after server restart are not [reflected]". The DB `import_jobs` row is a shadow copy reconciled by the reaper, not the source of truth for live progress.
- Files: `app/services/import_service.py` (registry + `JobState`), `app/routers/imports.py:119-150`, `app/schemas/imports.py:62`
- Impact: Hard ceiling of one backend process. A second uvicorn worker / horizontal scale would split the registry; users could see a job "disappear" after a restart even though DB rows persist. Status endpoints derive from the in-memory registry, so post-restart progress reads can mislead.
- Fix approach: Promote the DB `import_jobs` row to source of truth for status/progress and treat the in-memory dict as a cache, or move job state to a shared store (Redis / Postgres advisory locks) before any multi-worker deploy.

**Oversized, multi-concern service files breaching documented function/file limits:**
- Issue: CLAUDE.md sets soft/hard logic-LOC limits (100/200) and explicitly calls out "pipeline orchestrators (insights, import, normalization)" and large page components as split targets. Several files are far past any reasonable file budget and concentrate many concerns.
- Files (LOC):
  - `app/services/endgame_service.py` (3462) — the single largest hand-written backend module by a wide margin; prime refactor candidate.
  - `app/services/insights_llm.py` (2188) — also carries a ~9 KB single-line `_PROMPT_VERSION` comment (v14→v35 changelog crammed into one string literal at line 68); see "Fragile Areas".
  - `app/services/insights_service.py` (1355), `app/services/canonical_slice_sql.py` (1115), `app/services/opening_insights_service.py` (997), `app/repositories/endgame_repository.py` (949), `app/services/import_service.py` (929).
  - Frontend: `frontend/src/pages/Openings.tsx` (1232), `frontend/src/pages/Endgames.tsx` (965), `frontend/src/App.tsx` (634), `frontend/src/pages/Home.tsx` (627).
- Impact: High cognitive load, merge-conflict magnets, hard to test in isolation. `endgame_service.py` and the two big page components are where new work is riskiest.
- Fix approach: Apply the CLAUDE.md split recipe — one function per pipeline stage for the services; extract `useXyzData` hooks + sibling desktop/mobile renderers for the pages. Treat these as their own GSD refactor phases (not opportunistic in-task), per the "refactor on sight / but flag if out of scope" rule.

**45 `# ty: ignore` suppressions concentrated in ORM / FastAPI-Users boundaries:**
- Issue: 45 backend `ty: ignore` / `type: ignore` comments. Most are legitimate and documented (SQLAlchemy `ColumnElement`-vs-`bool`, FastAPI-Users generics, forward refs). A few are looser: `import_service.py:826,829` use `# type: ignore[union-attr]` justified only as "dict fallback for test mocks" — production code shaped around test doubles.
- Files: `app/services/guest_service.py` (4), `app/services/endgame_service.py` (5+), `app/services/import_service.py` (5), `app/services/insights_llm.py` (3), `app/routers/auth.py` (2), `app/repositories/endgame_repository.py` (2), `app/services/admin_service.py` (2), `app/models/*.py`.
- Impact: Each suppression is a spot where the type checker is blind. The test-mock-driven ignores (`import_service.py:826,829`) are the only ones that hint at a design smell rather than tooling limits.
- Fix approach: Leave the SQLAlchemy / FastAPI-Users ones (tooling beta limitation). For the test-mock ignores, narrow the production type with a real Pydantic model and adapt the mocks instead.

## Known Bugs

No open bug markers found in source (`grep TODO/FIXME/HACK/XXX` returns 3 benign doc hits). The historical production incidents documented in CLAUDE.md (FLAWCHESS-3Q OOM family) are all marked fixed / mitigated; the residual risk is captured under Performance and Fragile Areas below rather than as live bugs.

## Security Considerations

**Default `SECRET_KEY` signs JWTs if the env var is unset:**
- Risk: `app/core/config.py:17` defaults `SECRET_KEY = "change-me-in-production"`, and `app/users.py:61,71` use `settings.SECRET_KEY` as the JWT signing secret. If the prod `.env` ever omits `SECRET_KEY`, the app starts with a publicly-known signing key, allowing forged auth tokens. There is no fail-fast guard rejecting the placeholder value in a production environment.
- Files: `app/core/config.py:17`, `app/users.py:61,71`
- Current mitigation: Prod `.env` is expected to set it; 1Password sync. But nothing enforces it.
- Recommendations: Fail startup when `ENVIRONMENT != "development"` and `SECRET_KEY == "change-me-in-production"` (or is empty). Same guard would catch an empty `GOOGLE_OAUTH_CLIENT_SECRET` in prod.

**Import-trigger endpoint has no per-IP / per-request rate limiting:**
- Risk: Rate limiting exists for guest-account creation (`app/core/ip_rate_limiter.py`, 5 req/hour/IP, applied in `auth.py:232`) and for insights (`InsightsRateLimitExceeded` in `routers/insights.py`), but the import-start endpoint (`POST /` in `app/routers/imports.py`) has no limiter (`grep limiter` → 0 hits in that file). Imports are the most expensive operation (game fetch + Zobrist + eval drain) and the documented OOM history shows Postgres is the scarce resource.
- Files: `app/routers/imports.py`, `app/services/import_service.py`
- Current mitigation: Per-user active-job dedupe (`get_active_job` checks `status in (PENDING, IN_PROGRESS)`), the `game_repository.py:134-141` active-import gate, `IMPORT_TIMEOUT_SECONDS = 3h` cap, and per-platform `asyncio.Semaphore` throttles on *outbound* API calls (`app/core/rate_limiters.py`, 3 concurrent each). These bound per-user concurrency and external fetch rate, but not inbound request rate or guest fan-out across many guest accounts.
- Recommendations: Add a per-user / per-IP limiter on the import-start endpoint; consider a global concurrent-import cap and a guest game-count quota (none found in `guest_service.py`).

**All rate limiters are in-process (reset on restart, do not span workers):**
- Risk: `ip_rate_limiter.py` self-documents "In-process limiter — resets on server restart. Acceptable for single-process Uvicorn deployment. For multi-process or distributed deployments, replace with a Redis-backed solution." The import semaphores (`rate_limiters.py`) and insights limiter are likewise per-process.
- Files: `app/core/ip_rate_limiter.py`, `app/core/rate_limiters.py`, `app/routers/insights.py`
- Impact: A restart resets all guest-creation / insights counters; a multi-worker deploy would multiply every limit by the worker count.
- Recommendations: Move to a shared store before scaling out (couples directly to the single-process scaling limit below).

**External-input parsing trust (PGN / platform payloads):**
- Risk: PGNs and NDJSON / archive payloads from chess.com and lichess are parsed and stored. CLAUDE.md mandates per-game try/except and `UnicodeDecodeError` handling; a single malformed game must not abort a whole import.
- Files: `app/services/normalization.py`, `app/services/zobrist.py` (`process_game_pgn`, broad `except Exception` at line 159), `app/services/chesscom_client.py`, `app/services/lichess_client.py`
- Current mitigation: Documented PGN-hardening conventions; `Standard`-variant filtering; per-game exception handling.
- Recommendations: Audit per-game isolation in batch ingestion and bound oversized PGNs.

## Performance Bottlenecks

**Postgres memory under concurrent import (recurring production OOM — FLAWCHESS-3Q):**
- Problem: Documented history of Postgres OOM-kills during game imports (CLAUDE.md). Root causes across recurrences: high fetch throughput fanning out to many concurrent Postgres backends, a per-batch Stockfish eval reserving hash tables, and an over-large SQLAlchemy pool.
- Files: `app/services/import_service.py` (`_BATCH_SIZE = 30`, line 78), `app/core/database.py` (`pool_size=10, max_overflow=10` → 20-conn ceiling per process, lines 18-19), `app/services/engine.py` (`_HASH_MB = 32` line 58, `STOCKFISH_POOL_SIZE` env, default 1).
- Cause: Import is the memory-hot path; the eval pass was the historical OOM driver and has since been moved to the decoupled cold-lane `run_eval_drain()` (`eval_drain.py`, `_DRAIN_BATCH_SIZE = 10`). The bottleneck is now explicitly the Stockfish eval drain, not batch size (per the comment block at `import_service.py:64-78`).
- Improvement path: The mitigations are tuned but inter-dependent and not expressed as a single budget in code. A regression that re-raises `_BATCH_SIZE`, `_HASH_MB`, `STOCKFISH_POOL_SIZE`, or the SQLAlchemy pool in combination can re-trigger OOM (exactly the Phase 41.1 recurrence). Add a guard/test asserting the combined connection + hash-memory budget stays within host caps, and keep the eval pass off the hot lane.

**Giant generated CDF module parsed into the process on every start:**
- Problem: `app/services/global_percentile_cdf.py` is 97,598 lines — the entire repo's backend LOC is dominated by this one generated lookup table (`COHORT_PERCENTILE_CDF`, ~99 percentile breakpoints per (metric, anchor, TC) cell). It is imported transitively via the percentile services into the insights path.
- Files: `app/services/global_percentile_cdf.py` (regenerated by `scripts/gen_global_percentile_cdf.py`)
- Cause: Precomputed percentile CDF embedded as Python source rather than a data asset.
- Improvement path: Import-time parse cost and heap footprint of ~100k lines of literals on every process start. Consider moving the table to a binary / parquet / npz asset loaded lazily, or a DB table, so the module doesn't bloat the Python heap and startup.

## Fragile Areas

**Import-pipeline DB-outage resilience (intricate retry + reaper machinery):**
- Files: `app/services/import_service.py` (`_RETRIABLE_DB_OUTAGE_ERRORS` lines 50-61, `_record_failure_state` retry loop ~303-410, `run_periodic_reaper` line 276, `cleanup_orphaned_jobs` line 141), `app/repositories/import_job_repository.py:179-204` (`fail_orphaned_jobs`), `app/main.py:53-87` (lifespan wiring).
- Why fragile: This is the most heavily commented and most defensively coded area in the repo (multiple UAT-dated comment blocks, 2026-05-16 → 2026-05-20). It encodes hard-won knowledge: the retriable-error tuple must catch raw asyncpg connect-time errors *and* OS-level `ConnectionRefusedError` / `OSError` or jobs strand `in_progress`; the failure-state UPDATE itself can fail during a Postgres restart, so a periodic reaper (5 min, `IMPORT_TIMEOUT_SECONDS` age threshold) is the backstop. The interplay of in-memory status, DB status, retry backoff (2/4/8/16s ≈ 30s), and the reaper is subtle.
- Safe modification: Do not narrow `_RETRIABLE_DB_OUTAGE_ERRORS`, do not remove the reaper, and do not assume the failure-state write succeeds. Re-read the dated comment blocks before touching anything here. Any change should be paired with a simulated Postgres-restart test.
- Test coverage: Backend suite is strong overall (100 test files vs 88 source files), but the OOM / restart scenarios are inherently hard to cover deterministically. Several import-service tests are explicitly `xfail`/pending (`tests/test_import_service.py:2332-2333,1470,1657`; `tests/services/test_eval_drain_stage_b.py` skips with "implementation pending Plans 05/06").

**`_PROMPT_VERSION` mega-comment as de-facto changelog:**
- Files: `app/services/insights_llm.py:68`
- Why fragile: A single string assignment (`_PROMPT_VERSION = "endgame_v35"`) carries a ~9 KB inline comment documenting every prompt revision v14→v35. The version string is a cache key (changing it cache-busts LLM reports), so edits here have product-visible side effects, and the changelog-in-a-comment is unreviewable in normal diffs.
- Safe modification: Bump the version string deliberately (it invalidates cached narration); move the historical changelog out of the source comment into `app/prompts/` docs or `CHANGELOG.md` to make future diffs legible.

**Cross-module use of `eval_drain` internals from the import service:**
- Files: `app/services/import_service.py:33-36` imports `_collect_midgame_eval_targets` and `_collect_endgame_span_eval_targets` (underscore-private) from `eval_drain.py`, flagged "intentional — see SEED-023".
- Why fragile: Private helpers are now part of an implicit cross-module contract. Refactoring `eval_drain.py`'s internals can silently break the import hot lane.
- Safe modification: Promote those two helpers to a public, documented API of `eval_drain` (or a shared `eval_targets` module) so the dependency is explicit.

**React effect-rule suppressions around deep-link / restoration state:**
- Files: `frontend/src/App.tsx:512-515` (`react-hooks/refs`), `frontend/src/pages/openings/useDeepLinkHighlight.ts:35,77` (`react-hooks/set-state-in-effect`), `frontend/src/pages/Endgames.tsx:355` and `frontend/src/pages/Openings.tsx:221` (`react-hooks/exhaustive-deps`).
- Why fragile: These suppress the React-hooks linter for cross-render ref / snapshot logic (token-change restoration guards, pulse-timer sync, deep-link highlight clearing). The comments explain "behavior preserved from original" — i.e. behavior depends on the suppressed pattern. Re-enabling the rule or "fixing" deps can change navigation / highlight behavior.
- Safe modification: Treat each as load-bearing; change only with a test that exercises the deep-link → filter-change → highlight-clear sequence.

## Scaling Limits

**Single backend process:**
- Current capacity: One uvicorn process; in-memory import registry; in-process rate limiters; per-process SQLAlchemy pool of 20 (10 + 10). Prod is a CPX42 (8 vCPU / 16 GB) tuned around this single-process assumption (Postgres `max_connections=30`).
- Limit: Cannot add uvicorn workers or horizontally scale without (a) splitting the in-memory job registry, (b) externalizing the rate limiters, and (c) re-budgeting Postgres `max_connections` — each new process adds up to 20 connections against a 30-connection server cap, so two processes already over-subscribe.
- Scaling path: Externalize job state and limiters (Redis / Postgres), make status DB-sourced, then size `pool_size × workers ≤ max_connections` with headroom.

## Dependencies at Risk

**`ty` type checker is a beta and a CI gate:**
- Risk: Multiple `# ty: ignore` comments justified as "FastAPI-Users generic typing not resolved by ty beta" / "ty cannot infer ... from a str variable". The build hard-fails on ty (CLAUDE.md). A `ty` upgrade could change which suppressions are needed.
- Impact: A ty version bump may simultaneously remove now-unnecessary ignores (unused-ignore lint error) and surface new ones, breaking CI.
- Migration plan: Pin `ty`; treat upgrades as their own task with a full re-check of all 45 suppressions.

**`pydantic-ai` Agent generics for LLM insights:**
- Risk: `insights_llm.py:318-327` suppresses `invalid-return-type` / `invalid-argument-type` because `pydantic-ai` Agent generic params depend on a runtime model string. The provider / model is configured dynamically via `PYDANTIC_AI_MODEL_INSIGHTS` (`config.py:34`); provider SDK churn (Google thinking config, model names) is a moving target.
- Impact: Prompt / agent construction is the least type-safe area; provider API changes surface at runtime, not compile time. Note `app/main.py` lifespan calls `get_insights_agent()` and aborts startup on an unconfigured model string (good fail-fast), but provider-internal API drift is not caught.
- Migration plan: Wrap agent construction behind a small typed adapter and keep an integration smoke test against the live model.

## Missing Critical Features

**Production-secret fail-fast validation:**
- Problem: `app/core/config.py` is a clean `pydantic-settings` object, but ships permissive defaults (`SECRET_KEY = "change-me-in-production"`, empty OAuth secret, empty `SENTRY_DSN`) with no environment-aware validation that required secrets are actually set in prod.
- Blocks: Safe deploys — a missing `SECRET_KEY` in prod silently falls back to a public signing key (see Security).
- Fix approach: Add a `model_validator` that rejects placeholder / empty secrets when `ENVIRONMENT != "development"`.

**Rate limiting on the expensive import endpoint:** see Security. Guest-creation and insights are limited; import-start is not.

**Single shared place for the OOM tuning budget:**
- Problem: The OOM-relevant knobs are spread across three files (`import_service._BATCH_SIZE`, `engine._HASH_MB` + `STOCKFISH_POOL_SIZE`, `core/database` pool sizes). There is no single budget the way CLAUDE.md narrates it.
- Blocks: A reviewer cannot see at a glance whether a change keeps the combined memory budget within host caps — exactly how the Phase 41.1 OOM regressed.

## Test Coverage Gaps

**Postgres-restart / OOM-recovery paths:**
- What's not tested: The end-to-end Postgres-restart-mid-import recovery (retry classifier → failed-state write failure → reaper backstop) is the most defensively *coded* but inherently hardest to *test* path. Several adjacent tests are `xfail`/skipped pending implementation.
- Files: `app/services/import_service.py` (retry/reaper), `app/repositories/import_job_repository.py:179`, `tests/test_import_service.py:2332-2333`, `tests/services/test_eval_drain_stage_b.py` (4 skips)
- Risk: A regression that strands jobs `in_progress` would only surface in production (it has before — FLAWCHESS-3Q family).
- Priority: High

**Multi-process / registry-split behavior:**
- What's not tested: Behavior when the in-memory registry and DB disagree after a restart (status-endpoint correctness), and in-process rate-limiter behavior under multiple workers.
- Files: `app/routers/imports.py:119-150`, `app/services/import_service.py`, `app/core/ip_rate_limiter.py`
- Risk: Misleading progress / status to users; latent blocker for scaling.
- Priority: Medium

**Oversized service internals (`endgame_service.py`, `insights_service.py`):**
- What's not tested: At 3462 / 1355 LOC these almost certainly contain branch combinations not exercised; the test count is healthy in aggregate but cannot guarantee per-branch coverage at this size.
- Files: `app/services/endgame_service.py`, `app/services/insights_service.py`
- Risk: Edge-case metric / zone computations silently wrong; LLM payload-shape regressions.
- Priority: Medium

---

*Concerns audit: 2026-05-30*
