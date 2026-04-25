---
phase: 260425-lwz
plan: "01"
type: tdd
wave: 1
depends_on: []
files_modified:
  - app/services/chesscom_client.py
  - tests/test_chesscom_client.py
autonomous: true
requirements: [LWZ-01]
must_haves:
  truths:
    - "When chess.com archives-list returns ambiguous 404 and player endpoint returns 200, fetch_chesscom_games no longer raises 'couldn't return games' — it enumerates monthly archive URLs from the player's joined date to today and fetches them sequentially"
    - "If the player JSON includes a 'joined' Unix timestamp (seconds), enumeration starts at that month (UTC)"
    - "If 'joined' is missing, enumeration starts at the chess.com earliest plausible archive (2007-01)"
    - "If since_timestamp is provided, enumeration starts at max(joined_month, since_timestamp_month) so incremental sync remains correct"
    - "Per-month 404/410 responses skip cleanly (existing _fetch_archive_with_retries behavior); transient 5xx/429 retry; persistent failures still raise RuntimeError"
    - "All-empty fallback (every synthesized URL 404s) yields zero games as a normal success rather than raising"
    - "When fallback fires, a logger.info line and a Sentry info-level capture_message are emitted with tags source=import platform=chess.com so we can monitor frequency"
  artifacts:
    - path: "app/services/chesscom_client.py"
      provides: "Month-enumeration fallback in fetch_chesscom_games + new _fetch_chesscom_player_joined helper + _CHESSCOM_EARLIEST_ARCHIVE_YEAR_MONTH constant"
      contains: "_fetch_chesscom_player_joined"
    - path: "tests/test_chesscom_client.py"
      provides: "Tests covering fallback enumeration, since_timestamp truncation, missing joined, per-month 404 skip, full integration mirroring wasterram"
      contains: "test_archives_404_with_player_200_falls_back_to_month_enumeration"
  key_links:
    - from: "fetch_chesscom_games (ambiguous 404 + exists=True branch)"
      to: "_fetch_chesscom_player_joined → month enumeration → existing archive_urls loop"
      via: "synthesized {BASE_URL}/{api_username}/games/YYYY/MM URLs appended to archive_urls"
      pattern: "f\"{BASE_URL}/{api_username}/games/"
    - from: "fallback site"
      to: "Sentry + logger"
      via: "logger.info(...) and sentry_sdk.capture_message(level='info', tags={source, platform})"
      pattern: "capture_message.*chess.com archives-list 404"
---

<objective>
Replace the "couldn't return games right now" raise in `fetch_chesscom_games`'s ambiguous-404 + player-200 branch with a month-enumeration fallback, so users like `wasterram` (whose archives-list endpoint is silently broken on chess.com's side while their monthly archives still work) can complete imports normally.

Purpose: Close a live recovery gap left by quick task 260425-lii. The previous fix correctly distinguished "user truly absent" from "real user, archives unavailable", but treated the latter as terminal. Live verification shows the underlying monthly archives ARE reachable for these accounts; only the index endpoint is broken. We can recover by enumerating months client-side.

Output:
- New private helper `_fetch_chesscom_player_joined(client, api_username) -> datetime | None` that returns the player's `joined` timestamp converted to UTC datetime (or None if missing/unreachable).
- New module constant `_CHESSCOM_EARLIEST_ARCHIVE_YEAR_MONTH = (2007, 1)` (chess.com launched May 2007 — January is a conservative floor).
- Modified ambiguous-404 + exists=True branch: instead of raising, fetch joined date, enumerate months from `max(joined_month, since_timestamp_month)` to current month UTC, build `{BASE_URL}/{api_username}/games/YYYY/MM` URLs, set `archive_urls` to the synthesized list, fall through to the existing per-archive loop.
- Inline comment at the fallback site referencing the bug it works around (per CLAUDE.md "comment bug fixes").
- Sentry info-level `capture_message` and `logger.info` so we can monitor how often this code path fires in production.
- Tests covering: enumeration correctness, since_timestamp truncation, missing-joined fallback, per-month 404 skip, integration scenario mirroring wasterram (archives-list 404 ambiguous, player 200 with joined, two monthly archives 200 with games).
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@./CLAUDE.md
@./app/services/chesscom_client.py
@./tests/test_chesscom_client.py
@./.planning/quick/260425-lii-fix-misleading-chess-com-user-not-found-/260425-lii-PLAN.md
@./.planning/quick/260425-lii-fix-misleading-chess-com-user-not-found-/260425-lii-SUMMARY.md

<interfaces>
<!-- Existing helpers / constants in app/services/chesscom_client.py to reuse — do NOT re-derive or duplicate. -->

```python
# Module-level (already present)
BASE_URL = "https://api.chess.com/pub/player"
_HEADERS = {"User-Agent": USER_AGENT}
_RETRYABLE_EXCEPTIONS = (httpx.TimeoutException, httpx.RemoteProtocolError, httpx.ReadError)
_CHESSCOM_NOT_FOUND_MARKER = "not found"

# Existing helper (returns bool | None) — keep signature, do NOT modify
async def _user_exists_on_chesscom(client: httpx.AsyncClient, api_username: str) -> bool | None: ...

# Existing helper for incremental sync skipping — reuse
def _archive_before_timestamp(archive_url: str, since: datetime) -> bool: ...

# Existing per-archive fetcher with retry/skip/raise behavior — fallback URLs feed into this unchanged
async def _fetch_archive_with_retries(client, archive_url) -> httpx.Response | None: ...
```

<!-- Test helpers (already in tests/test_chesscom_client.py) -->
```python
def _make_response(json_data: dict, status_code: int = 200) -> MagicMock: ...
def _make_game(uuid="game-uuid-1", rules="chess", username="testuser", ...): ...
```
Tests use `unittest.mock.AsyncMock` with `side_effect=[...]` to script sequential responses. Always `patch("app.services.chesscom_client.asyncio.sleep", new=AsyncMock())` to avoid real sleeping during retry/pace loops.
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: TDD — fallback to month enumeration on ambiguous 404 + player-exists</name>
  <files>tests/test_chesscom_client.py, app/services/chesscom_client.py</files>

  <behavior>
    Tests to add (RED first, before any implementation):

    1. `test_archives_404_ambiguous_with_player_200_enumerates_months_from_joined`
       - Archives endpoint: 404 with `{"message": "An internal error has occurred."}`
       - Player endpoint: 200 with `{"username": "wasterram", "joined": <unix_seconds_for_2026_03_22>}`
       - Two synthesized monthly archives: 2026/03 → 200 with one game, 2026/04 → 200 with one game
       - Freeze "now" to 2026-04-25 UTC by patching `datetime` in `app.services.chesscom_client` (or by passing a `datetime.now()`-equivalent monkeypatch). Assert exactly 2 games yielded, exactly 4 GET calls (archives, player, 2026/03, 2026/04), and the archive URLs called include `/games/2026/03` and `/games/2026/04` and DO NOT include `/games/2026/02` (joined was March).
       - Use `patch("app.services.chesscom_client.asyncio.sleep", new=AsyncMock())`.

    2. `test_fallback_enumeration_truncates_to_since_timestamp`
       - Same archives-404 + player-200 setup but `joined` = 2024-01-01 UTC.
       - `since_timestamp = datetime(2026, 3, 1, tzinfo=timezone.utc)`.
       - "Now" frozen at 2026-04-25 UTC.
       - Expect enumeration to start at 2026/03 (not 2024/01) — 2 archive fetches (03 and 04), not 28+. Assert call_count and the actual URLs.

    3. `test_fallback_enumeration_uses_earliest_when_joined_missing`
       - Player 200 returns `{"username": "x"}` (no `joined` field).
       - "Now" frozen at 2007-03-15 UTC (a tight window so test stays fast — 3 months: 2007/01, 2007/02, 2007/03).
       - Each of those 3 months returns 404 (skipped by existing `_fetch_archive_with_retries` behavior).
       - Assert 0 games yielded, no exception raised, exactly 5 GET calls (archives, player, 3 months).

    4. `test_fallback_per_month_404_skips_and_continues`
       - Already partially covered by #1 if we change one of the months to 404. Variant: 2026/03 → 404, 2026/04 → 200 with one game. Assert 1 game yielded.

    5. `test_fallback_emits_sentry_info_capture_message`
       - Mirror case #1 minimally. Patch `app.services.chesscom_client.sentry_sdk.capture_message` with a `MagicMock`.
       - Assert it was called at least once with `level="info"` and `tags` dict containing `source="import"` and `platform="chess.com"`, AND the message string contains the substring "archives-list 404" (so the existing per-archive `capture_message` calls don't false-positive).

    All five tests must FAIL before implementation (commit RED). After GREEN, all 25+5 = 30 tests in the file must pass.

    Implementation behavior (after RED is committed):

    a. Add module constant: `_CHESSCOM_EARLIEST_ARCHIVE_YEAR_MONTH: tuple[int, int] = (2007, 1)` with a comment "chess.com launched May 2007; use January as a conservative floor for accounts with no `joined` field."

    b. Add helper `_fetch_chesscom_player_joined(client, api_username) -> datetime | None`:
       - GET `{BASE_URL}/{api_username}` with `_HEADERS`.
       - Wrap in `try/except _RETRYABLE_EXCEPTIONS: return None`.
       - If `resp.status_code != 200`: return None.
       - Parse JSON; if `joined` is present and is an int: `return datetime.fromtimestamp(int(joined), tz=timezone.utc)`. Otherwise return None. Tolerate `ValueError`/`TypeError` from JSON parse and return None.
       - Return type `datetime | None`. Docstring states unit (seconds, not ms) and behavior on failure.

    c. Modify the ambiguous-404 + `exists is True` branch in `fetch_chesscom_games`:
       - Remove the `raise ValueError("chess.com couldn't return games for ...")`.
       - Add inline comment block: `# Workaround: chess.com's /games/archives endpoint silently 404s for some real accounts (e.g. user 'wasterram' confirmed 2026-04-25) while individual /games/YYYY/MM endpoints still work. Enumerate months from joined date and let the existing per-archive loop handle each one. Tracks frequency via Sentry info-level capture_message.`
       - Call `joined_at = await _fetch_chesscom_player_joined(client, api_username)`.
       - Compute `start_year, start_month`:
         - If `joined_at` is None: use `_CHESSCOM_EARLIEST_ARCHIVE_YEAR_MONTH`.
         - Else: `(joined_at.year, joined_at.month)`.
       - If `since_timestamp` is provided: bump `(start_year, start_month)` to `max((start_year, start_month), (since_timestamp.year, since_timestamp.month))` (tuple comparison handles year+month ordering).
       - Compute `now = datetime.now(timezone.utc)`; iterate `(year, month)` from start to `(now.year, now.month)` inclusive, constructing URLs `f"{BASE_URL}/{api_username}/games/{year:04d}/{month:02d}"`.
       - Set `archive_urls = synthesized_list` and let existing loop run.
       - Emit:
         ```python
         logger.info(
             "chess.com archives-list 404 for %s, falling back to month enumeration (%d months)",
             username, len(archive_urls),
         )
         sentry_sdk.capture_message(
             "chess.com archives-list 404 — falling back to month enumeration",
             level="info",
             tags={"source": "import", "platform": "chess.com"},
         )
         ```
       - For testability of the "now" boundary: prefer `datetime.now(timezone.utc)` directly. Tests patch via `patch("app.services.chesscom_client.datetime")` with a `MagicMock` whose `.now.return_value` is the frozen time, and pass through `fromtimestamp` to the real datetime. (Alternative: extract a small `_current_year_month()` helper and patch that instead — choose whichever yields a cleaner test patch. Document the choice in the SUMMARY.)

    d. Refactor structure: factor the enumeration into a private helper `_enumerate_archive_urls(api_username, start_ym, end_ym) -> list[str]` if it makes the test for "URLs called" easier to write — optional but recommended for unit-level coverage of the date math separately from network mocks.
  </behavior>

  <action>
    RED phase:
    - Add the 5 tests listed above to `tests/test_chesscom_client.py` inside `TestFetchChesscomGames` (and possibly a new `TestFetchChesscomPlayerJoined` class for unit-testing the helper directly with 200/200-no-joined/404/timeout/non-int-joined cases).
    - Run `uv run pytest tests/test_chesscom_client.py -x` and confirm the new tests fail.
    - Commit RED: `test(260425-lwz): add failing tests for archives-list 404 month-enumeration fallback`.

    GREEN phase:
    - Add `_CHESSCOM_EARLIEST_ARCHIVE_YEAR_MONTH` constant.
    - Implement `_fetch_chesscom_player_joined` helper.
    - Replace the ambiguous-404 + `exists is True` raise with the enumeration fallback per the behavior section above. Include the bug-fix comment per CLAUDE.md.
    - Add `logger.info` + `sentry_sdk.capture_message(level="info", ...)` at the fallback site.
    - Run `uv run pytest tests/test_chesscom_client.py -x`, `uv run ty check app/ tests/`, `uv run ruff check . && uv run ruff format .`. All must pass.
    - Commit GREEN: `feat(260425-lwz): fall back to month enumeration when chess.com archives-list 404s for real users`.

    REFACTOR phase (only if needed):
    - If the GREEN code is hard to follow, extract `_enumerate_archive_urls` helper and/or `_resolve_enumeration_start` helper. Re-run tests and lint. Commit `refactor(260425-lwz): ...` only if changes were made.

    Constraints reminder:
    - No magic numbers — all literals (2007, 1, etc.) named.
    - Inline comment at the fallback site explaining the chess.com bug being worked around (per CLAUDE.md).
    - `_user_exists_on_chesscom` signature unchanged — add a new helper rather than overloading it.
    - Do NOT add `sentry_sdk.capture_exception` for ValueError paths (per CLAUDE.md "skip trivial/expected exceptions") — info-level `capture_message` is the only Sentry call added here.
    - Do NOT use `asyncio.gather`. Sequential month fetches only — the existing 0.15s pacing in `_fetch_archive_with_retries` is the rate-limit budget.
    - lichess client untouched.
    - Update the `fetch_chesscom_games` docstring `Raises:` section: remove the "couldn't return games right now" bullet, since that branch no longer raises. Mention the fallback in the function docstring summary.
  </action>

  <verify>
    <automated>uv run pytest tests/test_chesscom_client.py -x &amp;&amp; uv run ty check app/ tests/ &amp;&amp; uv run ruff check . &amp;&amp; uv run ruff format --check app/services/chesscom_client.py tests/test_chesscom_client.py</automated>
  </verify>

  <done>
    - All 5 new tests pass; all pre-existing tests in `tests/test_chesscom_client.py` still pass.
    - `_fetch_chesscom_player_joined` and `_CHESSCOM_EARLIEST_ARCHIVE_YEAR_MONTH` exist in `app/services/chesscom_client.py`.
    - The ambiguous-404 + player-200 branch no longer raises ValueError; instead it logs, emits Sentry info, and feeds synthesized URLs into the existing archive loop.
    - `uv run ty check app/ tests/` reports zero errors.
    - `uv run ruff check .` clean; ruff format reports both files already formatted.
    - At least two commits in git log: RED test commit and GREEN implementation commit (REFACTOR commit optional).
    - Updated `fetch_chesscom_games` docstring `Raises:` section reflects new behavior.
    - Inline comment at fallback site references the chess.com bug and live-confirmed account `wasterram` (per CLAUDE.md "comment bug fixes").
  </done>
</task>

</tasks>

<verification>
- `uv run pytest tests/test_chesscom_client.py` — all tests pass (existing 25 + new 5 = 30).
- `uv run pytest` — full suite passes (no regressions in import_service or normalization tests).
- `uv run ty check app/ tests/` — zero errors.
- `uv run ruff check .` — clean.
- `uv run ruff format --check .` — clean.
- Manual sanity grep: `grep -n "couldn't return games" app/services/chesscom_client.py` returns nothing (the old raise is fully removed).
- Manual sanity grep: `grep -n "archives-list 404" app/services/chesscom_client.py` returns the new log/Sentry call sites.
</verification>

<success_criteria>
1. A user whose chess.com `/games/archives` endpoint returns ambiguous 404 (like `wasterram`) but whose `/pub/player/{username}` returns 200 will complete an import successfully — yielding however many games their monthly archives contain (possibly 0) — instead of seeing "couldn't return games right now, try again later".
2. Genuine missing users (404 with "not found" body, OR ambiguous 404 + player 404) still raise the user-facing "user not found" ValueError. No regression to the 260425-lii behavior.
3. Transient network/server failures (ambiguous 404 + player 5xx/network error) still raise "request failed" ValueError so `last_synced_at` is preserved. No regression.
4. Incremental sync (`since_timestamp` provided) does not re-fetch months that ended before `since_timestamp`.
5. Sentry receives an info-level `capture_message` whenever the fallback fires, tagged `source=import platform=chess.com`, so we can monitor production frequency.
6. No new dependencies. lichess client untouched. No changes to import_service, schemas, or routers.
</success_criteria>

<output>
After completion, create `.planning/quick/260425-lwz-fallback-to-month-enumeration-when-chess/260425-lwz-SUMMARY.md` per the standard summary template, including:
- Root cause recap (archives-list silently broken for some real chess.com accounts).
- The before/after of the ambiguous-404 + player-200 branch.
- Decision on how "now" is patched in tests (direct `datetime` patch vs `_current_year_month` helper).
- Whether `_enumerate_archive_urls` helper was extracted in REFACTOR.
- Confirmation that lichess client and import_service were untouched.
</output>
