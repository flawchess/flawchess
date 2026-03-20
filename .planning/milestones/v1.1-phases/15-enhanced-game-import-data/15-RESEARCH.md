# Phase 15: Enhanced Game Import Data - Research

**Researched:** 2026-03-18
**Domain:** Chess import pipeline enrichment — clock data, termination, time control, bug fixes
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Clock data storage**
- Store seconds remaining (from PGN `%clk` annotations) as a new column on `game_positions` table
- Store the raw clock value — time spent per move can be derived by consumers
- Use NULL when `%clk` not present (daily games, some older games)
- No UI display of clock data in this phase — store only for future use

**Termination reason**
- Add TWO columns to `games` table:
  - `termination_raw` — platform's original string (e.g. chess.com's "checkmated", lichess's "mate")
  - `termination` — normalized bucket from ~6 categories: checkmate, resignation, timeout, draw, abandoned, unknown
- "Draw" bucket covers: stalemate, repetition, 50-move rule, insufficient material, agreement
- Display normalized termination on game cards (e.g. "Checkmate", "Timeout")

**Time control bucketing fix**
- Fix 180+0 misclassification (currently bucket = bullet because `<= 180s`)
- Claude decides exact boundary adjustment based on chess.com/lichess conventions
- Game cards show both exact time control AND bucket: e.g. "Blitz · 10+5" or "10+5 (Blitz)"
- `time_control_str` already stored — just needs to be included in API response and displayed

**Multi-username import fix**
- Fix `get_latest_for_user_platform()` to filter by `(user_id, platform, username)` not just `(user_id, platform)`
- Each username gets its own sync boundary — importing "bob" after "alice" fetches bob's full history
- Keep games from both usernames — no deletion when switching usernames

**Bug fixes**
- **Data isolation**: User A's games visible when logged in as user B (same browser, different accounts). Likely a caching or user_id filtering issue — investigate and fix.
- **last_login on Google SSO**: last_login updates on email/password login but NOT on Google SSO. Missing hook in the OAuth login flow — needs to be added.

### Claude's Discretion
- Exact time control bucket boundaries (as long as 180+0 = blitz)
- Clock column data type (REAL vs INTEGER seconds)
- Exact game card layout for termination and time control display
- Termination reason mapping table details per platform
- Data isolation bug root cause and fix approach

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope
</user_constraints>

---

## Summary

This phase enriches the existing import pipeline at five distinct touch points: (1) adding a `clock_seconds` column to `game_positions` populated from PGN `%clk` annotations, (2) adding `termination_raw`/`termination` columns to `games` populated from per-platform normalization, (3) fixing the time control bucket boundary so 180+0 = blitz, (4) fixing `get_latest_for_user_platform()` to scope the sync boundary by username, and (5) fixing two bugs — data isolation and Google SSO last_login.

All changes are self-contained within well-understood files. No new libraries are needed. The DB wipe approach (no migration gymnastics) is already the project convention. The primary risk is the data isolation bug root cause, which requires investigation to confirm whether it is a TanStack Query stale-cache issue or a missing `user_id` filter — both are fixable without architectural changes.

**Primary recommendation:** Execute all five work items independently; they share no runtime dependencies and can be planned as parallel tasks.

---

## Standard Stack

### Core (all already present — no new installs)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| python-chess | 1.10.x | PGN parsing, `%clk` extraction via `node.clock()` | Already used throughout |
| SQLAlchemy 2.x async | current | ORM column definitions, bulk inserts | Established project ORM |
| Alembic | current | DB schema migrations | Established project migrator |
| Pydantic v2 | current | Schema field additions | Established project validator |
| FastAPI-Users 15.0.4 | 15.0.4 | `on_after_login` hook (already exists for JWT path) | Established project auth |
| React 19 + TanStack Query | current | Frontend data fetching, cache invalidation | Established frontend stack |
| Tailwind CSS | current | Game card styling | Established frontend styling |

### No New Dependencies Required

All implementation uses existing project libraries. No `npm install` or `uv add` needed.

---

## Architecture Patterns

### %clk Extraction from PGN

python-chess stores clock comments on `GameNode` objects. The correct extraction pattern:

```python
# Source: python-chess docs — GameNode.clock() method
# hashes_for_game() already iterates moves via game.mainline()
# Use node.clock() to get seconds remaining as float | None
for node in game.mainline():
    clock_seconds = node.clock()  # returns float seconds or None if no %clk annotation
    move = node.move
    move_san = board.san(move)
    # ... compute hashes, then board.push(move)
```

Key detail: `node.clock()` reads the `%clk` comment on the node AFTER the move (i.e., the clock value for the side that just moved). It returns `None` when no annotation is present. The current `hashes_for_game()` uses `enumerate(game.mainline_moves())` — this must be refactored to iterate `game.mainline()` (nodes) instead, to access the clock comment.

**Return type change for `hashes_for_game()`:** Currently returns `list[tuple[int, int, int, int, str | None]]`. After the change it must include clock: `list[tuple[int, int, int, int, str | None, float | None]]`. All callers (`_flush_batch` in `import_service.py`) must be updated.

**Clock column data type:** Use `REAL` (PostgreSQL float4). Clock values from `%clk` are floats (e.g., `3.5` for 3.5 seconds remaining). `INTEGER` would lose sub-second precision. `REAL` is more appropriate than `DOUBLE PRECISION` (float8) since clock precision beyond one decimal place is not meaningful.

### Termination Extraction

**chess.com** — termination is in `game["white"]["result"]` and `game["black"]["result"]`. The loser's result string reveals the termination cause. The winner always has `"win"`. Extract from the loser's result:

| chess.com result string | Normalized bucket |
|------------------------|-------------------|
| `checkmated` | `checkmate` |
| `resigned` | `resignation` |
| `timeout` | `timeout` |
| `timevsinsufficient` | `draw` |
| `agreed`, `stalemate`, `insufficient`, `repetition`, `50move` | `draw` |
| `abandoned` | `abandoned` |
| `win` | N/A (winner — look at other player) |
| anything else | `unknown` |

**Implementation note:** For chess.com draws, both players have the same draw result string. Extract termination from the non-`"win"` result of either player. When one player has `"win"`, the other's result is the termination cause.

**lichess** — termination is in `game["status"]` field. Map:

| lichess status | Normalized bucket |
|---------------|-------------------|
| `mate` | `checkmate` |
| `resign` | `resignation` |
| `outoftime` | `timeout` |
| `timeout` (no moves made) | `abandoned` |
| `draw`, `stalemate`, `threefoldRepetition`, `fiftyMoves`, `unknownFinish` | `draw` |
| `aborted` | `abandoned` |
| `cheat` | `unknown` |
| anything else | `unknown` |

**lichess also provides `termination` field** in game JSON but it's a human-readable string and less reliable for programmatic mapping than `status`. Use `status`.

### Time Control Boundary Fix

The bug: `<= 180` makes 180+0 bullet. Chess.com and lichess both classify 180+0 as blitz.

**Fix:** Change the bullet/blitz boundary from `<= 180` to `< 180`. This means:
- `< 180s` → bullet (so 179+0 = bullet)
- `180s to 600s` → blitz (so 180+0 = blitz)
- `180+2` = 260s → blitz (already correct, still blitz)

This matches both chess.com and lichess conventions where 3|0 (3 minutes) is classified as blitz.

**Existing test `test_bullet_boundary` asserts `180+0 -> bullet`** — this test must be UPDATED to assert `180+0 -> blitz` (it will fail after the fix; the fix makes it correct).

### Multi-Username Sync Fix

Current `get_latest_for_user_platform()` query:
```python
.where(
    ImportJob.user_id == user_id,
    ImportJob.platform == platform,
    ImportJob.status == "completed",
)
```

Fixed version adds `ImportJob.username == username`:
```python
.where(
    ImportJob.user_id == user_id,
    ImportJob.platform == platform,
    ImportJob.username == username,
    ImportJob.status == "completed",
)
```

**Caller in `import_service.py`** must pass `job.username` to the query. Currently `run_import()` calls `get_latest_for_user_platform(session, job.user_id, job.platform)` — add `job.username` as third argument.

### Data Isolation Bug

The bug: "User A's games visible when logged in as user B (same browser, different accounts)."

**Root cause candidates (in order of probability):**

1. **TanStack Query stale cache** — Query keys include user identity. If `user_id` or a user-specific key is not part of the query key, cached data from user A's session persists when user B logs in in the same browser. This is the most likely cause since the backend clearly filters by `user_id` in all queries.

2. **Backend `user_id` filter missing** — Less likely; the analysis repository consistently applies `user_id` filters. But worth verifying in any endpoints that might serve data without authentication.

**Investigation approach:** Check TanStack Query key definitions in the frontend hooks. If query keys don't include user ID, stale cache from the previous session will be returned until TTL expires or cache is invalidated. The fix is to include `user_id` or `email` in query keys, or call `queryClient.clear()` on logout.

**Frontend auth flow investigation:**
- On logout: does `queryClient.clear()` or `queryClient.invalidateQueries()` get called?
- On login: are query keys user-scoped?

### Google SSO last_login Fix

The existing `on_after_login()` hook in `UserManager` already handles email/password login. The Google OAuth flow bypasses this hook because it goes through `oauth_callback()` instead of the standard login path.

Current `google_callback()` in `routers/auth.py`:
```python
user = await user_manager.oauth_callback(...)
# ... then generates JWT and redirects
# Missing: no last_login update here
```

**Fix:** After `user_manager.oauth_callback()` returns the user, update `last_login` directly:

```python
# After oauth_callback returns user:
async with async_session_maker() as session:
    await session.execute(
        sa_update(User).where(User.id == user.id).values(last_login=func.now())
    )
    await session.commit()
```

Alternatively, override `on_after_login` in `UserManager` — but FastAPI-Users may not call it during OAuth. The direct update in the callback is the safest approach.

### API Schema Changes (GameRecord)

Add to `GameRecord` Pydantic schema:
- `termination: str | None` — normalized bucket ("checkmate", "resignation", etc.)
- `time_control_str: str | None` — already stored in DB, just not exposed

Add to `Game` model assembly in `analysis_service.py`:
```python
GameRecord(
    ...
    termination=g.termination,
    time_control_str=g.time_control_str,
)
```

Corresponding TypeScript `GameRecord` interface in `frontend/src/types/api.ts` must gain the same two fields.

### GameCard Display

Extend line 2 of `GameCard.tsx`:
```tsx
{/* Show: "Blitz · 10+5" when both bucket and str present */}
{game.time_control_bucket && (
  <span className="capitalize">
    {game.time_control_bucket}
    {game.time_control_str ? ` · ${game.time_control_str}` : ''}
  </span>
)}
{game.termination && (
  <span className="capitalize">{game.termination}</span>
)}
```

Display priority: termination as a small badge or plain text alongside W/D/L; exact time control appended to bucket label.

### Bulk Insert Chunk Size

`bulk_insert_positions` currently chunks at 4000 rows (7 columns each = 28,000 params). Adding `clock_seconds` makes it 8 columns per row: 32,767 / 8 ≈ 4,095 max rows. Update chunk size to `4000` remains safe (4000 × 8 = 32,000 < 32,767). No change needed — but document this calculation explicitly in the function's comment.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| %clk annotation parsing | Manual regex on PGN comment text | `node.clock()` from python-chess | Already handles format variations, returns None when absent |
| Bulk insert chunking logic | Custom chunk calculator | Update existing `bulk_insert_positions` chunk_size constant | Already handles asyncpg 32,767 param limit |
| OAuth token handling | Custom JWT generation in OAuth flow | Already implemented via `strategy.write_token(user)` | Consistent with existing flow |

---

## Common Pitfalls

### Pitfall 1: hashes_for_game() iteration refactor breaks move_san semantics

**What goes wrong:** Current code uses `enumerate(game.mainline_moves())` which gives `Move` objects. Switching to `game.mainline()` gives `ChildNode` objects. The SAN must still be computed from `board.san(node.move)` BEFORE `board.push(node.move)`.

**How to avoid:** In the refactored loop, call `board.san(node.move)` and `node.clock()` before `board.push(node.move)`. The clock annotation is on the node representing the position AFTER the move — so `node.clock()` gives the time remaining for the side that just moved.

**Warning signs:** If move_san values are shifted by one ply in test assertions, the order of SAN vs push is wrong.

### Pitfall 2: asyncpg param limit after adding clock_seconds column

**What goes wrong:** `bulk_insert_positions` chunks at 4000 rows × 7 cols = 28,000 params. After adding `clock_seconds`, it's 4000 × 8 = 32,000. This is still under 32,767, but the comment must be updated to document the new calculation and the chunk_size should be reviewed.

**How to avoid:** Update the chunk_size comment in `bulk_insert_positions` to reflect 8 columns. Consider setting chunk_size to 3500 for a wider safety margin.

### Pitfall 3: test_bullet_boundary expects the old (wrong) behavior

**What goes wrong:** `test_normalization.py::TestParseTimeControl::test_bullet_boundary` explicitly asserts `parse_time_control("180+0") -> ("bullet", 180)`. After the fix this assertion is wrong. If not updated, the test will fail and block CI.

**How to avoid:** Update this test case to assert `bucket == "blitz"` when fixing `parse_time_control()`.

### Pitfall 4: Termination extraction for chess.com draws — both players have same string

**What goes wrong:** For draws, both players have `result = "agreed"` (or "stalemate", etc.). The naive approach of "look at the loser's result" fails because neither player is the loser.

**How to avoid:** Extract termination after result determination. If result is draw (`1/2-1/2`), use either player's result string (they're the same category). If result is decisive, extract from the losing player's result string (the one without "win").

### Pitfall 5: Data isolation — query cache not invalidated on logout/re-login

**What goes wrong:** TanStack Query caches responses by query key. If keys are not user-scoped and cache is not cleared on logout, user B's session may see user A's cached game data.

**How to avoid:** Add `queryClient.clear()` (or at minimum `queryClient.removeQueries()`) to the logout handler. Alternatively, include user ID in all query keys. Verify this is the root cause before implementing.

---

## Code Examples

### %clk extraction — refactored hashes_for_game()

```python
# Source: python-chess docs — GameNode.clock() returns float | None
def hashes_for_game(pgn_text: str) -> list[tuple[int, int, int, int, str | None, float | None]]:
    """Returns (ply, white_hash, black_hash, full_hash, move_san, clock_seconds)."""
    try:
        game = chess.pgn.read_game(io.StringIO(pgn_text))
    except Exception:
        return []

    if game is None:
        return []

    moves = list(game.mainline())
    if not moves:
        return []

    results = []
    board = game.board()

    for ply, node in enumerate(moves):
        move_san: str = board.san(node.move)  # BEFORE push
        clock_seconds: float | None = node.clock()  # seconds remaining after this move
        wh, bh, fh = compute_hashes(board)
        results.append((ply, wh, bh, fh, move_san, clock_seconds))
        board.push(node.move)

    # Final position: no move, no clock
    wh, bh, fh = compute_hashes(board)
    results.append((len(moves), wh, bh, fh, None, None))

    return results
```

### Termination normalization — chess.com

```python
# In normalize_chesscom_game():
def _chesscom_termination(white_result: str, black_result: str, result: str) -> tuple[str | None, str | None]:
    """Return (termination_raw, termination) for chess.com game."""
    if result == "1/2-1/2":
        raw = white_result  # both are same draw string
    elif result == "1-0":
        raw = black_result  # loser's result string describes termination
    else:  # 0-1
        raw = white_result

    _MAP = {
        "checkmated": "checkmate",
        "resigned": "resignation",
        "timeout": "timeout",
        "timevsinsufficient": "draw",
        "agreed": "draw",
        "stalemate": "draw",
        "insufficient": "draw",
        "repetition": "draw",
        "50move": "draw",
        "abandoned": "abandoned",
    }
    return raw, _MAP.get(raw, "unknown")
```

### Termination normalization — lichess

```python
# In normalize_lichess_game():
_LICHESS_STATUS_MAP = {
    "mate": "checkmate",
    "resign": "resignation",
    "outoftime": "timeout",
    "draw": "draw",
    "stalemate": "draw",
    "threefoldRepetition": "draw",
    "fiftyMoves": "draw",
    "unknownFinish": "draw",
    "aborted": "abandoned",
    "timeout": "abandoned",  # game aborted before first move
    "cheat": "unknown",
    "noStart": "abandoned",
}

status = game.get("status", "unknown")
termination_raw = status
termination = _LICHESS_STATUS_MAP.get(status, "unknown")
```

### get_latest_for_user_platform() fix

```python
# In import_job_repository.py:
async def get_latest_for_user_platform(
    session: AsyncSession,
    user_id: int,
    platform: str,
    username: str,  # NEW PARAMETER
) -> ImportJob | None:
    result = await session.execute(
        select(ImportJob)
        .where(
            ImportJob.user_id == user_id,
            ImportJob.platform == platform,
            ImportJob.username == username,  # NEW FILTER
            ImportJob.status == "completed",
        )
        .order_by(ImportJob.completed_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()
```

### Google SSO last_login fix — in google_callback()

```python
# After oauth_callback() returns user, before generating JWT:
async with async_session_maker() as session:
    await session.execute(
        sa_update(User).where(User.id == user.id).values(last_login=func.now())
    )
    await session.commit()
```

---

## State of the Art

| Old Approach | Current Approach | Impact |
|--------------|-----------------|--------|
| `enumerate(game.mainline_moves())` — gives Move objects only | `game.mainline()` — gives ChildNode objects with `.clock()` access | Enables clock extraction without separate PGN re-parse |
| Sync boundary = latest job for (user_id, platform) | Sync boundary = latest job for (user_id, platform, username) | Each username gets independent history |

---

## Open Questions

1. **Data isolation root cause**
   - What we know: User B sees User A's data when using the same browser.
   - What's unclear: Whether it's TanStack Query stale cache or a missing backend `user_id` filter.
   - Recommendation: During implementation, check frontend logout handler first (add `queryClient.clear()`), then audit any backend endpoints that might lack user_id filtering. The analysis router already applies `user_id` consistently via `_build_base_query`, so the frontend cache is the most likely culprit.

2. **clock_seconds column data type**
   - What we know: `%clk` annotations use float seconds (e.g., `0:03:00.0` = 180.0s), and `node.clock()` returns `float | None`.
   - Recommendation: Use `REAL` (PostgreSQL float4, 4 bytes). Sub-second precision to ~6 decimal places is not needed for any planned use case.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest |
| Config file | `pyproject.toml` (uv-managed) |
| Quick run command | `uv run pytest tests/test_normalization.py tests/test_zobrist.py tests/test_import_service.py -x` |
| Full suite command | `uv run pytest` |

### Phase Requirements → Test Map

| Behavior | Test Type | Automated Command | File Exists? |
|----------|-----------|-------------------|-------------|
| `%clk` extraction from PGN into clock_seconds | unit | `uv run pytest tests/test_zobrist.py -x` | ✅ (extend) |
| Termination mapping — chess.com all result strings | unit | `uv run pytest tests/test_normalization.py -x` | ✅ (extend) |
| Termination mapping — lichess all status strings | unit | `uv run pytest tests/test_normalization.py -x` | ✅ (extend) |
| Time control: 180+0 = blitz (fix boundary) | unit | `uv run pytest tests/test_normalization.py::TestParseTimeControl -x` | ✅ (update existing test) |
| Sync boundary scoped by username | unit | `uv run pytest tests/test_import_service.py -x` | ✅ (extend) |

### Sampling Rate

- **Per task commit:** `uv run pytest tests/test_normalization.py tests/test_zobrist.py tests/test_import_service.py -x`
- **Per wave merge:** `uv run pytest`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

None — existing test infrastructure covers all phase requirements. New test cases must be added to existing files, not new files:
- `tests/test_zobrist.py` — add tests for `hashes_for_game()` clock_seconds tuple field
- `tests/test_normalization.py` — add tests for termination extraction (both platforms), update `test_bullet_boundary`
- `tests/test_import_service.py` — add test for username-scoped sync boundary

---

## Sources

### Primary (HIGH confidence)

- python-chess source inspection and docs: `GameNode.clock()` returns `float | None`, reads `%clk` comment — confirmed by examining existing codebase usage patterns and python-chess API
- Direct codebase reading: all canonical files listed in CONTEXT.md fully read and analyzed

### Secondary (MEDIUM confidence)

- Chess.com/lichess time control conventions (180+0 = blitz): based on widely documented platform behavior and the fact that both platforms label 3|0 as "Blitz" in their UI
- lichess API `status` field values: based on existing normalization patterns and lichess NDJSON game structure already in the codebase

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new libraries; all existing
- Architecture: HIGH — direct code inspection of all touch points
- Pitfalls: HIGH — identified from existing test cases and code structure
- Data isolation root cause: MEDIUM — requires runtime investigation to confirm frontend cache vs backend filter

**Research date:** 2026-03-18
**Valid until:** 2026-04-18 (stable domain)
