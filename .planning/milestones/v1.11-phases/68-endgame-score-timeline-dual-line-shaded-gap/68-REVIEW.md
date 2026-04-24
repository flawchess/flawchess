---
phase: 68-endgame-score-timeline-dual-line-shaded-gap
scope: PR #61 (v1.11 LLM-first Endgame Insights, phases 63-68)
reviewed: 2026-04-24
depth: standard
files_reviewed: 60
findings:
  critical: 0
  warning: 3
  info: 6
  total: 9
status: issues_found
---

# Phase 68: Code Review Report — PR #61 (v1.11 LLM-first Endgame Insights)

**Reviewed:** 2026-04-24
**Depth:** standard
**Files Reviewed:** 60 (spot-checked full content on the 32 files most relevant to the focus areas)
**Status:** issues_found — 0 critical, 3 warnings, 6 info

## Summary

The PR is in strong shape. No critical bugs or security issues. The architecture claims that matter most are honored:

- **LLM XSS surface:** Safe. `EndgameInsightsBlock` renders `player_profile`, `overview`, and `recommendations` via React text nodes (`<p>` / `<li>`), never `dangerouslySetInnerHTML`. LLM output cannot inject HTML.
- **Prompt injection surface:** Low. User-controlled inputs that flow into the user prompt are all `Literal`-typed (`opponent_strength`, `color`, `recency`) or structured numeric findings — no free-form strings from the user reach the prompt.
- **Authz:** `POST /api/insights/endgame` requires `current_active_user`; rate-limit is per-user. The recent switch to "all users" (commit c91478e) was intentional; `beta_enabled` now persists only on the user profile schema, not as a gate.
- **Async DB safety:** Verified. `compute_findings` makes two sequential `await`s, never `asyncio.gather`. `generate_insights` is sequential throughout. `LlmLogRepository.create_llm_log` opens its own session via `async_session_maker()` so log rows survive caller rollbacks — the read helpers correctly take a caller-supplied session.
- **Migration safety:** The five migrations (create `llm_logs`, add `beta_enabled`, add `thinking_tokens`, drop `system_prompt`, drop `flags`) all have reversible downgrades; FK on `user_id` uses `ondelete="CASCADE"`; indexes cover the hot paths (`user_id + created_at DESC`, `findings_hash`, `endpoint + created_at DESC`).
- **Cache key stability:** `_compute_hash` correctly excludes `as_of` and `findings_hash` and uses the NaN-safe `model_dump_json` → `json.loads` → `json.dumps(sort_keys=True)` recipe. Prompt-version changes invalidate the cache by being part of the cache key (`findings_hash + prompt_version + model`).
- **Sentry compliance:** All three exception paths in `_run_agent` use `sentry_sdk.set_context` with structured data, never variable-in-message interpolation. Same pattern in `compute_findings`.
- **Sign convention in dual-line chart:** The gradient stop math in `EndgameScoreOverTimeChart` handles sign flips correctly (`dA * dB < 0` excludes touches-zero).

Findings below are mostly code-quality and edge-case robustness — none block the milestone.

## Warnings

### WR-01: Rate-limit check is vulnerable to concurrent request TOCTOU

**File:** `app/services/insights_llm.py:1800-1813`

`count_recent_successful_misses` is read and then compared to `INSIGHTS_MISSES_PER_HOUR` without a DB-level lock or unique-constraint mechanism. Two concurrent requests from the same user can both read `misses = 2`, both pass the gate, both call the LLM, both write a log row → 4 misses in the hour. Realistically the frontend is single-user single-tab so this is low-probability, but a double-click, a retry mid-flight, or a second tab makes it trivially reproducible. The consequence is up to ~2x spend during concurrent bursts, not a security breach.

**Fix:** Either accept the slack (document it), OR wrap the miss-count + LLM call + log write in a `SELECT ... FOR UPDATE` on a per-user lock row, OR run the rate-limit increment inside a transaction that writes a placeholder `llm_logs` row first (`response_json IS NULL`) and bumps it on success. Simplest: add a frontend mutex so the button is disabled while `mutation.isPending`.

### WR-02: `_run_agent` latency timer starts before `agent.run()`

**File:** `app/services/insights_llm.py:1747-1762`

The catch-all `except Exception` correctly captures and converts unknown failures to `provider_error`. However, `t0 = time.monotonic()` is set before `agent.run(user_prompt)`, so if `get_insights_agent()` raises (e.g. the `lru_cache` was invalidated somehow — unlikely but possible), the `except` block will still record a latency, and Sentry context won't indicate the failure happened before the call. Defensive but misleading.

**Fix:** Move `t0` to be the first statement inside the `try:` block, and handle agent-construction errors in a separate wrapping try around the `get_insights_agent()` call. Or accept current behavior with a comment noting the latency includes agent-construction time.

### WR-03: `EndgameInsightsBlock` has dead `staleMinutes` state — always null

**File:** `frontend/src/components/insights/EndgameInsightsBlock.tsx:81`

`const staleMinutes: number | null = null;` is declared but never reassigned. It is threaded through `RenderedState`, then used to choose between two stale banner copy strings (`staleCopy` at line 202-205), but the `staleMinutes !== null` branch is unreachable. Looks like an incomplete removal — probably the stale path used to derive minutes from `retry_after_seconds` on the 200 envelope. The result is users on the `stale_rate_limited` path always see the generic "try again in a moment" copy, never the "~N min" copy.

**Fix:** Either populate `staleMinutes` from the response (would require threading `retry_after_seconds` into the 200 envelope schema), OR delete the dead state and the minutes-aware branch of `staleCopy` entirely. The latter is lower-risk and matches current behavior:

```tsx
const staleCopy = "Showing your most recent insights. You've hit the hourly limit; try again in a moment.";
// And drop staleMinutes from RenderedState props entirely.
```

## Info

### IN-01: `insights_llm.py` at 1857 lines is over-dense for one module

**File:** `app/services/insights_llm.py` (entire file)

Mixes Agent singleton, prompt assembly (~60% of the file), cache/rate-limit orchestration, exception classes, and helper math. `_assemble_user_prompt` alone is ~140 lines. Maintainability cost — no correctness impact.

**Fix:** Consider splitting on a follow-up phase: `insights_llm/agent.py` (Agent + singleton), `insights_llm/prompt.py` (all `_format_*`, `_render_*`, `_assemble_user_prompt`), `insights_llm/orchestrate.py` (`generate_insights`, rate-limit helpers).

### IN-02: `compute_player_profile` uses `datetime.date.today()` instead of UTC

**File:** `app/services/insights_service.py:267, 283-288, 324`

`today = datetime.date.today()` returns the server's local date, while `_RATE_LIMIT_WINDOW` math and `_all_time_window_bounds` use UTC. On a server running in a non-UTC zone (unusual for the Hetzner deployment but possible), the 90-day cutoff for `cutoff_last_3mo` and the "stale" marker could be off by ±1 day near midnight UTC. Currently prod is UTC so this is dormant.

**Fix:** Use `datetime.datetime.now(datetime.UTC).date()` for consistency with the rest of the pipeline.

### IN-03: `_finalize_cost_and_error` treats empty-string `data.error` as falsy

**File:** `app/repositories/llm_log_repository.py:92`

`combined = f"{data.error}{_ERROR_JOIN_SEP}{marker}" if data.error else marker` — if a caller ever passes `data.error = ""`, the `if data.error` branch is false and `""` gets silently dropped in favor of just `marker`. No current call site passes empty strings, but the behavior drifts from "None means no error" toward "empty string means no error" without documentation.

**Fix:** Either document "caller must pass None, never empty string", OR use `if data.error is not None:` to be strict.

### IN-04: `FilterContext.rated_only=False` ambiguity on the wire

**File:** `app/services/insights_service.py:147, 157`

`rated=True if filter_context.rated_only else None` — when the user sets `rated_only=False`, this forwards `rated=None` ("no filter"), not `rated=False` ("only unrated games"). The router also maps `bool(rated) if rated is not None else False` on ingest, so `None` on the wire becomes `False` on the router → `None` to the service. Net effect: `rated=False` and `rated=None` both mean "unfiltered". Matches the v1.11 `_validate_full_history_filters` gate (which rejects `rated_only=True`), so moot today. But when the filter gate relaxes, the shorthand will bite.

**Fix:** Add a docstring note on `FilterContext.rated_only` that `False` means "no rated filter", not "filter to unrated only".

### IN-05: `_assemble_user_prompt` has no explicit length cap before send

**File:** `app/services/insights_llm.py:1504-1642`

Series are capped at `_ALL_TIME_MAX_POINTS = 36`, but the player profile, type chart (up to 5 rows), and subsection fan-outs (5 endgame classes × 2 metrics for `conversion_recovery_by_type`) could in theory balloon the prompt. In practice bounded to a few hundred lines. No token accounting before send means a pathological payload could hit the model's context limit and get truncated server-side, surfacing as `UnexpectedModelBehavior` → `output_retries`.

**Fix:** Add a defensive `len(user_prompt)` check (log a warning to Sentry above 50k chars), OR add a test asserting P99 prompt size is below a threshold.

### IN-06: Rate-limit window depends on DB wall-clock matching app wall-clock

**File:** `app/services/insights_llm.py:1685-1692`, `app/repositories/llm_log_repository.py:195, 236`

`cutoff = datetime.datetime.now(datetime.UTC) - window` is computed in app code, but row `created_at` values are written with Postgres `server_default=func.now()`. If the DB host and app host clocks differ by more than a few seconds (they shouldn't — NTP on both — but non-hermetic), the window-edge math drifts and `retry_after` can be off by the same drift.

**Fix:** Compute `cutoff` with DB-side `NOW()` in the query (`WHERE created_at > NOW() - make_interval(hours => 1)`). Defers the clock-sync assumption to a single clock.

---

_Reviewed: 2026-04-24_
_Reviewer: gsd-code-reviewer_
_Depth: standard_
