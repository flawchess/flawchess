---
phase: 260425-lii
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - app/services/chesscom_client.py
  - tests/test_chesscom_client.py
autonomous: true
requirements:
  - QUICK-260425-LII-01
must_haves:
  truths:
    - "A 404 on /games/archives with body containing 'not found' raises ValueError matching 'chess.com user .* not found'."
    - "A 404 on /games/archives with an ambiguous body (e.g. 'internal error') triggers a follow-up call to /pub/player/{username}."
    - "If the player endpoint returns 200 on the ambiguous-404 path, a ValueError is raised with a user-actionable message about archives being temporarily unavailable, NOT 'user not found'."
    - "If the player endpoint returns 404 on the ambiguous-404 path, the original 'not found' ValueError is raised (fallback)."
    - "If the player endpoint returns 5xx on the ambiguous-404 path, a generic 'request failed' ValueError is raised so last_synced_at is preserved (consistent with f69842b)."
    - "All existing chess.com client tests still pass; no regression in unrelated 404/410/403/500/429 archive-fetch behavior."
    - "uv run ty check app/ tests/ passes with zero errors."
    - "uv run ruff check . passes; ruff format produces no diff."
  artifacts:
    - path: "app/services/chesscom_client.py"
      provides: "Body-aware 404 handling on the archives endpoint plus a player-endpoint existence probe."
      contains: "_classify_archives_404"
    - path: "app/services/chesscom_client.py"
      provides: "User-existence check helper hitting /pub/player/{username}."
      contains: "_user_exists_on_chesscom"
    - path: "tests/test_chesscom_client.py"
      provides: "Coverage for the three new 404-classification branches."
      contains: "internal error"
  key_links:
    - from: "app/services/chesscom_client.py:fetch_chesscom_games"
      to: "_classify_archives_404"
      via: "function call on archives 404 branch"
      pattern: "_classify_archives_404\\("
    - from: "_classify_archives_404"
      to: "_user_exists_on_chesscom"
      via: "follow-up player endpoint probe on ambiguous body"
      pattern: "_user_exists_on_chesscom\\("

---

<objective>
Fix the misleading "chess.com user 'X' not found" error during import. The chess.com `/games/archives` endpoint returns HTTP 404 in two semantically distinct situations (user truly missing vs. archives unavailable for a real user), and the current code at `app/services/chesscom_client.py:122-123` conflates them. Real users with no public archives or transient chess.com errors get told their username doesn't exist, which sends them on a fruitless typo hunt.

Purpose: Give users accurate, actionable diagnostics when chess.com import fails — distinguish "fix your username" from "chess.com is unavailable / no games yet, try again later".

Output:
- `app/services/chesscom_client.py` with body-aware 404 handling and a player-endpoint existence probe.
- `tests/test_chesscom_client.py` extended with three new branches (genuine 404, ambiguous 404 + player 200, ambiguous 404 + player 404 fallback).
- Zero net new dependencies, no schema changes, no migrations.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@./CLAUDE.md
@app/services/chesscom_client.py
@tests/test_chesscom_client.py

<interfaces>
<!-- Current 404 handling site (the bug). Extracted from app/services/chesscom_client.py. -->

```python
# app/services/chesscom_client.py:99-127 (relevant excerpt)
api_username = username.lower()  # already lowercased — case-sensitivity is NOT the bug
archives_url = f"{BASE_URL}/{api_username}/games/archives"
# ... retry loop on transient network errors ...

if archives_resp.status_code == 404:
    raise ValueError(f"chess.com user '{username}' not found")  # <-- conflates two cases
if archives_resp.status_code != 200:
    raise ValueError(
        f"chess.com request failed (status {archives_resp.status_code}) for user '{username}'"
    )
```

```python
# app/services/chesscom_client.py:23 — base URL constant
BASE_URL = "https://api.chess.com/pub/player"
# Player-existence probe URL: f"{BASE_URL}/{api_username}"
# Archives URL: f"{BASE_URL}/{api_username}/games/archives"
```

```python
# Test file uses unittest.mock (AsyncMock + MagicMock) — NOT respx as the
# pre-drafted plan suggests. Stay consistent with the existing pattern.
# tests/test_chesscom_client.py:51-57
def _make_response(json_data: dict, status_code: int = 200) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data
    resp.raise_for_status = MagicMock()
    return resp
```

```text
chess.com 404 response bodies (verified live, 2026-04-25):
  Genuine missing user:    {"message": "User \"X\" not found."}
  Real user, no archives:  {"message": "An internal error has occurred. Please contact ..."}
                           (e.g. wasterram — exists at chess.com/member/wasterram)
The /pub/player/{username} endpoint returns 200 for real users, 404 for fake.
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Body-aware 404 handling with player-endpoint tiebreaker</name>
  <files>
    app/services/chesscom_client.py
    tests/test_chesscom_client.py
  </files>
  <behavior>
    Tests to add to `TestFetchChesscomGames` in `tests/test_chesscom_client.py`,
    written BEFORE the implementation change (RED → GREEN). Use the existing
    `_make_response` / `AsyncMock` pattern — do not introduce respx.

    1. `test_404_with_user_not_found_body_raises_not_found_error`
       - archives 404 with body `{"message": "User \"unknown\" not found."}`
       - expect ValueError matching `chess.com user 'unknown' not found`
       - the player endpoint MUST NOT be called (assert call_count == 1 on archives only)

    2. `test_404_with_internal_error_body_and_player_200_raises_archives_unavailable`
       - archives 404 with body `{"message": "An internal error has occurred. Please contact ..."}`
       - player endpoint (`/pub/player/wasterram`) returns 200 with a player JSON dict
       - expect ValueError matching something like
         `chess.com couldn't return games for 'wasterram' right now` (no public archives or temporary chess.com error)
       - assert mock_client.get was called twice (archives, then player)

    3. `test_404_with_internal_error_body_and_player_404_falls_back_to_not_found`
       - archives 404 with `{"message": "An internal error has occurred..."}`
       - player endpoint returns 404
       - expect ValueError matching `chess.com user 'ghostuser' not found`

    4. `test_404_with_internal_error_body_and_player_500_raises_request_failed`
       - archives 404 with `{"message": "An internal error has occurred..."}`
       - player endpoint returns 500
       - expect ValueError matching `chess.com request failed` so the import is
         marked failed and `last_synced_at` is preserved (consistent with f69842b).

    5. The existing `test_404_raises_value_error` (which currently mocks an
       empty-body 404) MUST be updated to reflect the new behavior:
       empty body / unparseable JSON falls into the ambiguous branch, so the
       test must additionally mock the player endpoint (e.g. as 404) to assert
       the fallback "not found" message. This keeps the test meaningful instead
       of brittle to internal branch changes.
  </behavior>
  <action>
    Step 1 — RED: Add the four new tests above to `tests/test_chesscom_client.py`
    in `TestFetchChesscomGames`, and update the existing `test_404_raises_value_error`
    so its mock supplies a player-endpoint response (404) for the fallback path.
    Run `uv run pytest tests/test_chesscom_client.py -x` and confirm the new
    tests fail (and the updated existing test fails) — this proves they exercise
    real behavior.

    Step 2 — GREEN: Edit `app/services/chesscom_client.py`:

    (a) Add two private helpers above `fetch_chesscom_games`:

        async def _user_exists_on_chesscom(
            client: httpx.AsyncClient, api_username: str
        ) -> bool | None:
            """Probe /pub/player/{username} to disambiguate a 404 on /games/archives.

            Returns:
                True  — player endpoint returned 200, user exists.
                False — player endpoint returned 404, user truly absent.
                None  — player endpoint returned anything else (5xx / network);
                        caller should treat as 'request failed' so the import is
                        marked failed and last_synced_at is preserved (f69842b).
            """
            url = f"{BASE_URL}/{api_username}"
            try:
                resp = await client.get(url, headers=_HEADERS)
            except _RETRYABLE_EXCEPTIONS:
                # Network-level error on the probe — surface as 'unknown'.
                return None
            if resp.status_code == 200:
                return True
            if resp.status_code == 404:
                return False
            return None

        Implementation note: do NOT add Sentry capture here. These ValueErrors
        are user-input/expected-condition failures (per CLAUDE.md "skip
        trivial/expected exceptions"). The top-level run_import handler still
        captures truly unexpected failures via the existing mechanism.

    (b) Add a small constant near the top of the module, beneath the existing
        `_RATE_LIMIT_BACKOFF_SECONDS`:

            # Substring (case-insensitive) we expect in the chess.com 404 body
            # when the user truly does not exist. Anything else on a 404 is
            # treated as ambiguous and probed via the player endpoint.
            _CHESSCOM_NOT_FOUND_MARKER = "not found"

        (Avoids a magic string, satisfies CLAUDE.md "no magic numbers/strings".)

    (c) Replace the existing block at lines 122-123:

            if archives_resp.status_code == 404:
                raise ValueError(f"chess.com user '{username}' not found")

        with the following body-aware branch (preserve the existing `if
        archives_resp.status_code != 200` line untouched immediately after):

            if archives_resp.status_code == 404:
                # chess.com returns 404 on /games/archives in TWO distinct cases:
                #   1. User truly absent — body: {"message": "User \"X\" not found."}
                #   2. Real user, archives unavailable (no public archives, or
                #      transient chess.com error) — body: {"message":
                #      "An internal error has occurred..."}
                # Pre-2026-04-25 this branch conflated both as "user not found",
                # which sent users with valid accounts on a typo hunt. We now
                # parse the body and, on ambiguity, probe /pub/player/{username}
                # to disambiguate. See `.planning/quick/260425-lii-*`.
                try:
                    body = archives_resp.json()
                    message = str(body.get("message", "")) if isinstance(body, dict) else ""
                except ValueError:
                    message = ""

                if _CHESSCOM_NOT_FOUND_MARKER in message.lower():
                    raise ValueError(f"chess.com user '{username}' not found")

                # Ambiguous body — confirm existence via the player endpoint.
                exists = await _user_exists_on_chesscom(client, api_username)
                if exists is True:
                    raise ValueError(
                        f"chess.com couldn't return games for '{username}' right now "
                        "(no public archives or temporary chess.com error). "
                        "Try again in a few minutes."
                    )
                if exists is False:
                    raise ValueError(f"chess.com user '{username}' not found")
                # exists is None — player endpoint also failed; treat as transient.
                raise ValueError(
                    f"chess.com request failed (status 404, player endpoint unreachable) "
                    f"for user '{username}'"
                )

    (d) Update the docstring of `fetch_chesscom_games` Raises section to reflect
        the new ValueError variants (genuine not-found, archives-unavailable,
        request-failed). Keep wording terse.

    Step 3 — Verify GREEN: re-run `uv run pytest tests/test_chesscom_client.py -x`.
    All five 404-related tests must pass plus all pre-existing tests in the file.

    Step 4 — Polish: run `uv run ty check app/ tests/` and `uv run ruff check . && uv run ruff format .`.
    Address any reported issues. Add explicit return type annotations on the new
    helper if ty complains (`-> bool | None`).

    Constraints / scope guards:
    - Do NOT modify `lichess_client.py` (its 404 handling is already clean).
    - Do NOT modify the frontend or DB schema.
    - Do NOT change the lowercasing on line 99.
    - Do NOT add Sentry `capture_exception` for these ValueErrors — they are
      user-input/expected-condition failures per CLAUDE.md.
    - Keep the helper functions module-private (leading underscore).
    - No new third-party dependencies.
  </action>
  <verify>
    <automated>uv run pytest tests/test_chesscom_client.py -x && uv run ty check app/ tests/ && uv run ruff check . && uv run ruff format --check .</automated>
  </verify>
  <done>
    - All five 404-branch tests pass (3 new + 1 new fallback + the updated existing test).
    - All other tests in `tests/test_chesscom_client.py` still pass.
    - `uv run ty check app/ tests/` reports zero errors.
    - `uv run ruff check .` clean; `ruff format --check .` produces no diff.
    - `app/services/chesscom_client.py` contains `_user_exists_on_chesscom` and the
      `_CHESSCOM_NOT_FOUND_MARKER` constant, plus a comment at the modified 404
      site explaining the bug fix (per CLAUDE.md "comment bug fixes").
    - The conflated `raise ValueError(f"chess.com user '{username}' not found")`
      at the old line 122-123 is gone (replaced by the body-aware branch).
  </done>
</task>

<task type="checkpoint:human-verify" gate="blocking">
  <what-built>
    Body-aware 404 handling in chess.com import. Genuine missing usernames still
    raise "user not found"; real users with archives temporarily unavailable
    (e.g. `wasterram`) now raise an actionable "couldn't return games right now"
    message instead of a misleading "user not found".
  </what-built>
  <how-to-verify>
    Run the local dev stack (backend + frontend) and exercise three import flows
    against the LIVE chess.com API (this catches any wire-format drift the unit
    tests can't):

    1. Start dev DB if not running:
       `docker compose -f docker-compose.dev.yml -p flawchess-dev up -d`
    2. Start backend: `uv run uvicorn app.main:app --reload`
    3. Start frontend in a second terminal: `cd frontend && npm run dev`
    4. Log in as a test user.
    5. From the Import page, attempt to import as chess.com username `wasterram`.
       Expected: error toast/message contains "couldn't return games" or
       "no public archives or temporary chess.com error" — NOT "user not found".
    6. Attempt to import as `zzzznotarealuser12345`.
       Expected: error message clearly says "chess.com user '...' not found".
    7. Attempt to import as your own real, archive-having chess.com username.
       Expected: import proceeds normally; games are fetched.
    8. Sentry sanity: open https://flawchess.sentry.io and confirm no new
       exception issues were captured for steps 5 or 6 (these are expected
       user-input failures and must NOT spam Sentry).

    Type "approved" if all four behaviors match. If any diverges, paste the
    actual error message and the username you used.
  </how-to-verify>
  <resume-signal>Type "approved" or describe issues</resume-signal>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| flawchess backend → chess.com public API | Untrusted external response; bodies may change shape, status codes may be ambiguous. We already treat the response defensively (status-code branching, retry on transient codes); this change tightens body-text interpretation. |
| User → import endpoint | Username comes from authenticated user input; already validated/lowercased upstream. No new injection surface. |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-260425-lii-01 | Tampering | chess.com 404 body parsing | mitigate | Wrap `archives_resp.json()` in try/except ValueError so a malformed/non-JSON 404 body does not crash; fall through to the player-endpoint probe. |
| T-260425-lii-02 | Information disclosure | New ValueError messages | accept | Messages contain only the username the user supplied (already known to them) and a generic chess.com hint. No internal paths or secrets surfaced. |
| T-260425-lii-03 | Denial of service | Extra player-endpoint call on 404 path | accept | Only fires on the ambiguous-404 path (rare); shares the same client + headers + retry posture; chess.com rate-limit (429) on the probe falls through to "request failed" which fails the import safely. No amplification vector. |
| T-260425-lii-04 | Spoofing | Trusting `_user_exists_on_chesscom` result | accept | Worst case is mislabeling an existence response under a network partition; we already return `None` (= "request failed") in that case, which preserves `last_synced_at` and surfaces a generic error. No security impact. |

</threat_model>

<verification>
- All four checks in the Task 1 `<verify>` automated block pass.
- Pre-existing chess.com client tests in `tests/test_chesscom_client.py` (15+ cases covering 410/403/500/429/incremental sync/etc.) still pass with no modification.
- Manual smoke test (Task 2 checkpoint) confirms live behavior against chess.com API matches expectations.
</verification>

<success_criteria>
- A user importing as `wasterram` (or any real user with no public archives) sees an actionable "archives temporarily unavailable" message instead of "user not found".
- A user importing a genuinely fake username still sees "user not found".
- chess.com 5xx / network errors during the player-endpoint probe degrade gracefully to "request failed" (last_synced_at preserved).
- Zero new Sentry issues for the expected ValueError variants.
- ty + ruff + pytest all green.
</success_criteria>

<output>
After completion, create `.planning/quick/260425-lii-fix-misleading-chess-com-user-not-found-/260425-lii-01-SUMMARY.md` summarizing the change, the two new helpers, the test cases added, and any deviations from this plan.
</output>
