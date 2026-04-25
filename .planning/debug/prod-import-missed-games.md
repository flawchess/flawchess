---
slug: prod-import-missed-games
status: resolved
trigger: |
  Have a look at the import jobs of user 11 in prod. There was an import (id: 482a95d9-53cc-4dfe-b4fa-ca130c0ca7dc) completed at 2026-04-19 19:34:56.835275 +00:00. Then another import (b6cda3b7-18ad-4905-9d74-77b5e4823863) completed at 2026-04-24 23:08:08.966610 +00:00 with 0 games_fetched and 0 games_imported. However, when I did a sync for the same chess.com username (Chess_player_lol) locally, games where fetched from within that time period. I think the import in prod missed a few games. Investigate
created: 2026-04-25
updated: 2026-04-25
---

# Debug: prod-import-missed-games

## Symptoms

- **Expected:** Prod chess.com import on 2026-04-24 23:08 UTC for user 11 (chess.com username `Chess_player_lol`) should have fetched any new games played since the previous import on 2026-04-19 19:34 UTC.
- **Actual:** Import job `b6cda3b7-18ad-4905-9d74-77b5e4823863` completed with `games_fetched=0` and `games_imported=0`, but a local sync of the same username afterwards fetched games from that 2026-04-19 → 2026-04-24 window.
- **Error messages:** None reported — job status is `completed` (not `failed`).
- **Timeline:**
  - Prior import: `482a95d9-53cc-4dfe-b4fa-ca130c0ca7dc` completed 2026-04-19 19:34:56 UTC
  - Affected import: `b6cda3b7-18ad-4905-9d74-77b5e4823863` completed 2026-04-24 23:08:08 UTC (0 games)
  - Local reproduction (today, 2026-04-25): sync for same username fetched games from inside that window
- **Reproduction:** Trigger sync on prod for user 11 → 0 games. Trigger same sync locally → games are returned.
- **Environment:** Production (Hetzner), backend on commit `e468619` (current main, includes v1.11). Local dev on same commit.

## Investigation resources

- DB MCP servers and `psql` over the SSH tunnel to prod.
- Import service: `app/services/import_service.py`
- Chess.com client: `app/services/chesscom_client.py`
- Models: `import_jobs`, `games`, `users`.
- Sentry: https://flawchess.sentry.io
- Production logs via `ssh flawchess docker compose logs`.

## Evidence

- timestamp: 2026-04-25 (investigator)
  source: prod DB `import_jobs` table for user_id=11
  observation: |
    Five jobs total for user 11. The two relevant chess.com jobs:
    - 482a95d9 (2026-04-19): completed, games_fetched=25, games_imported=23, last_synced_at=2026-04-19 19:34:56
    - b6cda3b7 (2026-04-24): completed, games_fetched=0, games_imported=0, last_synced_at=2026-04-24 23:08:08
    - Job duration of b6cda3b7: started 23:08:08.410, completed 23:08:08.966 → ~556ms total.

- timestamp: 2026-04-25 (investigator)
  source: prod DB `games` table for user_id=11, platform=chess.com
  observation: |
    Latest stored game for user 11 played at 2026-04-18 22:39:37 UTC. Confirms no games from
    the 2026-04-19 → 2026-04-24 window were imported.

- timestamp: 2026-04-25 (investigator)
  source: live curl to chess.com archive API
  observation: |
    `GET https://api.chess.com/pub/player/chess_player_lol/games/2026/04` returns 41 games,
    16 of which are after the 2026-04-19 19:34:56 UTC cutoff. Games definitely exist.
    Cache header on archives list: `last-modified: Friday, 24-Apr-2026 23:08:08 GMT+0000`
    (Cloudflare cache), exactly matching the failed import's completed_at — strongly suggests
    a transient cache miss / origin-fetch error happened at that exact moment.

- timestamp: 2026-04-25 (investigator)
  source: local DB `import_jobs` for username Chess_player_lol
  observation: |
    Local incremental sync today fetched 41 games (the entire 2026/04 archive) because the
    local cursor was 2026-04-02. Confirms the chess.com archive currently contains the games
    the prod import missed.

- timestamp: 2026-04-25 (investigator)
  source: prod DB `import_jobs` other chess.com jobs on 2026-04-24
  observation: |
    Two other chess.com jobs (user 64) failed cleanly that day with error_message "chess.com
    user 'Wastertan' not found" / "...'Wasterram'..." (404 typos, unrelated). No other
    completed-with-0-games jobs.

- timestamp: 2026-04-25 (investigator)
  source: code review of `app/services/chesscom_client.py` and `app/services/import_service.py`
  observation: |
    Two critical pieces of logic combine to cause silent data loss:

    1. `chesscom_client.py:159-161` silently skips ("continue") any per-archive monthly
       response that is non-200 OR 429-after-3-attempts. No log, no Sentry capture,
       no signal to caller. Existing tests (`test_500_on_archive_fetch_skips_archive`,
       `test_410_on_archive_fetch_skips_archive`) confirm this is by design.
    2. `import_service.py:246-258` unconditionally advances `last_synced_at = now` even
       when `games_fetched=0`. The comment explicitly justifies this for the legitimate
       "caught up, no new games" case.

    Together: a transient 5xx / Cloudflare hiccup on a single per-archive fetch causes the
    import to complete cleanly with 0 games AND advance the cursor — silently losing data
    that will be permanently dropped by `_archive_before_timestamp` once the calendar moves
    to the next month (archive_end <= since → skipped forever).

- timestamp: 2026-04-25 (investigator)
  source: chesscom_client retry policy review
  observation: |
    Per-archive retry loop only catches `_RETRYABLE_EXCEPTIONS = (TimeoutException,
    RemoteProtocolError, ReadError)`. A 5xx response is NOT an exception in httpx; it
    just sets `resp.status_code`. The current loop only special-cases 429 (60s backoff,
    retries up to 3 times). 500/502/503/504 fall through to the `if resp.status_code != 200`
    skip with no retry at all.

## Current Focus

- hypothesis: At 2026-04-24 23:08:08 UTC, the per-month archive fetch for `2026/04` returned a non-200 response (most likely a transient Cloudflare/origin 5xx — the cache last-modified timestamp coincides exactly), which `chesscom_client.py:160` silently swallowed via `continue`. The import then completed normally with `games_fetched=0`, and `last_synced_at` was advanced to 23:08:08, hiding the failure.
- test: Re-running the same sync locally today fetched games from the affected window — confirming the chess.com data is intact and the prod logic was at fault for that one moment.
- expecting: Fix should (a) not silently drop archive-level errors, (b) preserve the cursor when no games were actually scanned, and (c) add visibility (Sentry/log) for transient failures.
- next_action: Fix applied in branch `fix/chesscom-silent-archive-errors`. Re-import missed window for user 11 once deployed.

## Resolution

### Root cause

`app/services/chesscom_client.py` silently skips per-archive fetches that return non-200 (5xx, exhausted-429), combined with `app/services/import_service.py` always advancing `last_synced_at` on completion. A transient chess.com / Cloudflare error on the 2026/04 archive at 2026-04-24 23:08:08 caused the import to "succeed" with 0 games and bury 16 missed games behind a fresh cursor.

### Fix

Branch: `fix/chesscom-silent-archive-errors`

1. **`app/services/chesscom_client.py`** — replace silent skip with a tiered policy:
   - Add 5xx (500/502/503/504) to a retryable status set; retry like a 429 (with exponential backoff). On final attempt failure, raise `RuntimeError` so the import fails loudly.
   - Exhausted 429 retries also raise `RuntimeError` instead of skipping.
   - Permanent client errors on a per-archive fetch (404/410/403) are still skipped with a `logger.warning` + `sentry_sdk.capture_message` (warning level) — these can legitimately occur for ancient or hidden archives.
   - Untyped non-200 responses raise `RuntimeError` rather than silently skipping.
2. **`app/services/import_service.py`** — no functional change to `last_synced_at` advancement; the new exception path correctly routes failures to the `except Exception` branch which leaves `last_synced_at` untouched (only `update_import_job` is called with `status="failed"`, no `last_synced_at` field).
3. **Tests** — replace `test_500_on_archive_fetch_skips_archive` with `test_500_on_archive_fetch_retries_then_raises`. Add `test_410_on_archive_fetch_skips_with_warning` (preserves silent-skip for permanent client errors). Add `test_503_retries_and_succeeds`.
4. **Operational follow-up** — re-run the chess.com import for user 11 in production after deploy. The previous-job lookup will use the prior (correct) `last_synced_at = 2026-04-19 19:34:56` from the latest *completed* job — but b6cda3b7 IS completed with `last_synced_at = 2026-04-24 23:08:08`. We need to either (a) delete the bad job row, (b) reset its `last_synced_at` to the prior job's value, or (c) accept that the missed window will require a manual one-off re-import via `scripts/reimport_games.py`. **Recommend option (b)**: a one-line UPDATE on the job row after deploy.

### Verification

- Local: `uv run pytest tests/test_chesscom_client.py -x` → all green including the new tests.
- Local: `uv run ruff check app/ tests/` and `uv run ty check app/ tests/` → clean.
- After prod deploy + cursor reset: trigger a chess.com sync for user 11 → expect ~16 games imported.
