# Phase 61: Test Suite Hardening & DB Reset — Context

**Gathered:** 2026-04-16
**Status:** Ready for execution
**Mode:** Direct (user approved scope inline; no separate discuss pass)

<domain>
## Phase Boundary

Two related quality-of-life improvements for the pytest suite:

1. **Test DB reset at session start.** Today `tests/conftest.py` runs `alembic upgrade head` against `flawchess_test` but never wipes data. HTTP-path tests (those using `httpx.AsyncClient(transport=ASGITransport(app=app))`) commit via the session-scoped `override_get_async_session` fixture, so `users`, `oauth_account`, `position_bookmarks`, `games`, and `game_positions` accumulate indefinitely across local and CI runs. We add a session-scoped TRUNCATE that wipes everything except `alembic_version` (and `openings` if populated) before the first test runs. Data from the just-finished run is preserved for inspection; the next run starts clean.

2. **Meaningful aggregation sanity tests.** The audit in the session preceding this phase identified gaps: no end-to-end verification that WDL counts are correct from the user's perspective when they play black, no verification that material tallies move in the right direction on capture, no rolling-window boundary coverage, no platform×time-control intersection coverage, no recency-cutoff boundary test, no position-dedup within-game test, no endgame-class-transition test, and no router-level "seed N games → assert response.json has these exact numbers" test. This phase closes those gaps.

In scope:
- `tests/conftest.py` — truncate fixture
- `tests/seed_fixtures.py` (new) — shared realistic `seeded_user` fixture with committed data, reusable by router integration tests
- `tests/test_aggregation_sanity.py` (new) — unit-level aggregation tests using `db_session` rollback isolation
- `tests/test_integration_routers.py` (new) — router-level integration tests (register → seed for that user_id → call API → assert numbers)

Out of scope:
- Frontend test harness changes
- CI config changes (truncate runs per pytest session; CI uses ephemeral Postgres container so truncate is a no-op there but still correct)
- Rewriting existing tests — we only ADD new tests and ONE conftest fixture; existing tests are not touched
- Any production-code change. If a test discovers a real bug, flag it in the PR description rather than fixing it in this phase.
</domain>

<decisions>
## Implementation Decisions

### 1. Truncate vs schema drop/recreate → TRUNCATE

Use `TRUNCATE TABLE <all_public_tables_except_excluded> RESTART IDENTITY CASCADE` at session start, not `DROP SCHEMA` + re-run Alembic.

**Why:** TRUNCATE is one order of magnitude faster, doesn't rebuild indexes, and preserves the schema we just verified with `alembic upgrade head` immediately prior. Schema drop/recreate would work but adds ~1-2s to every local pytest startup for no benefit — the schema is already correct.

**Implementation:** Discover tables via `SELECT tablename FROM pg_tables WHERE schemaname='public'`, exclude `{'alembic_version', 'openings'}`. Runs ONCE per pytest session, right after `alembic upgrade head` and before `test_engine` yields. Uses the sync engine because TRUNCATE in a single transaction doesn't need async.

### 2. Truncate exclusions → alembic_version + openings

- `alembic_version` is managed by Alembic; truncating it breaks migration tracking.
- `openings` is a reference table populated by `scripts/seed_openings.py`. Today `flawchess_test` probably has zero rows here (nothing in the test setup seeds it), so truncate is effectively a no-op. But IF a future contributor seeds it (e.g. to test opening classification paths end-to-end), we don't want TRUNCATE to wipe that reference data silently. Exclude it defensively.

All other tables (users, games, game_positions, position_bookmarks, import_jobs, oauth_account, guest_sessions, etc.) are truncated.

### 3. Shared seeded_user fixture → module-scoped, committed, HTTP-registered

The router integration tests need a user that:
- Has a real JWT (so `/api/auth/jwt/login` works)
- Has `user_id` known to test code (so we can insert games for that exact ID)
- Has committed game data (so it's visible to API requests going through `override_get_async_session`)

Approach: one `seeded_user` fixture at **module scope** in `tests/seed_fixtures.py`:
1. Register via `POST /api/auth/register` with a uuid-prefixed email. Parse `response.json()["id"]` — fastapi-users `BaseUser[int]` schema exposes `id` as int.
2. Login via `/api/auth/jwt/login`, capture bearer token.
3. Open a fresh `AsyncSession` via `app.core.database.async_session_maker` (which is patched to the test DB by `override_get_async_session`'s session-scoped setup — confirmed in conftest.py:69) and seed a deterministic portfolio (see Plan 61-01 for exact counts).
4. Commit.
5. Yield `SeededUser(id=..., email=..., auth_headers={"Authorization": f"Bearer {token}"}, expected=<dict of expected aggregates>)`.

Module scope avoids re-seeding per test (expensive — ~15 inserts per user) but keeps isolation between router test modules. The data persists for the whole suite thanks to the session-start truncate.

**Alternative considered — function-scoped db_session seeding:** would require the HTTP path to see rolled-back data, which it cannot. Rejected.

**Alternative considered — seed at session scope:** module-scoped is safer because test modules can add supplementary data without colliding with sibling modules.

### 4. Unit-level aggregation tests → db_session rollback, user_id 700-series

For aggregation sanity tests that exercise service/repo code directly (not via HTTP), use the existing `db_session` transaction-rollback fixture. Each test picks a unique user_id in the 700-series (no current test module uses these) and the FK helper `ensure_test_user`. This matches the convention already established by `test_stats_service.py` (800-series), `test_openings_time_series.py` (900-series), `test_stats_repository.py` (99999).

### 5. Router integration tests → assert exact numbers, not just shape

New file `tests/test_integration_routers.py` verifies:
- `GET /api/stats/global` — seeded portfolio returns the expected WDL counts per time control AND per color (including black perspective flip)
- `GET /api/endgames/overview` — seeded portfolio returns the expected endgame_wdl counts and the Conv/Even/Recov material_rows sum equals endgame total (Phase 59 invariant, but at the router layer)
- `POST /api/openings/next-moves` — seeded portfolio with several games passing through the starting position returns the expected per-move WDL totals

Each test asserts exact integers. If seeding drifts out of sync with expectations the test fails loudly, which is the goal — "known seed → known numbers."

### 6. Material tally tests → use position_classifier directly, not DB

`app/services/position_classifier.py` exposes pure functions (`_compute_material_count`, `_compute_material_signature`, `_compute_material_imbalance`). These are the source of truth for the values stored in `GamePosition`. Testing them directly with `python-chess` board instances (e.g. starting position, after `1. e4`, after `1. e4 e5 2. exd5`) is much simpler and more targeted than seeding games and reading back material columns. Material tally tests land in a new `tests/test_material_tally.py` file so the existing `test_position_classifier.py` structure isn't disrupted.

### Folded todos

None — this phase originates from a live audit conversation, not a backlog item.
</decisions>

<code_context>
## Existing Code Insights

- **`tests/conftest.py:21-44`** — `test_engine` fixture runs `alembic upgrade head` at session start. That's where the truncate call goes, **after** migrations but **before** `yield engine`. Uses the sync engine via `engine.sync_engine` (already available for the teardown dispose).
- **`tests/conftest.py:47-83`** — `override_get_async_session` is session-scoped autouse and patches `app.core.database.async_session_maker` to the test DB. HTTP-path tests commit through this maker. For the `seeded_user` fixture, we import `async_session_maker` from `app.core.database` AFTER conftest patches it, so our seeding lands in `flawchess_test`.
- **`tests/conftest.py:101-109`** — `ensure_test_user(session, user_id)` creates a minimal User row with FK-valid id. Used when seeding games for IDs that aren't HTTP-registered.
- **Game model (`app/models/game.py`)** — NOT-NULL columns are `user_id`, `platform`, `platform_game_id`, `pgn`, `result`, `user_color`, `rated`. Everything else is nullable. `played_at` has NO server default but is widely read — always set it explicitly. `time_control_bucket` is a Postgres ENUM (`bullet|blitz|rapid|classical`). `result` is a Postgres ENUM (`1-0|0-1|1/2-1/2`). `user_color` is `white|black`. Unique constraint on `(user_id, platform, platform_game_id)`.
- **GamePosition model (`app/models/game_position.py`)** — NOT-NULL columns are `game_id`, `user_id` (denormalized for query perf), `ply`, `full_hash`, `white_hash`, `black_hash`. All analytics columns (`material_count`, `material_signature`, `material_imbalance`, `endgame_class`, `piece_count`, `clock_seconds`, `eval_cp`, etc.) are nullable.
- **`user_material_imbalance_after` is computed, not stored.** The repository `app/repositories/endgame_repository.py:239` derives it via window function. For seeding, we just need consecutive plies with `material_imbalance` set; the service reads `imbalance_after` as the imbalance at ply+4.
- **Router prefixes (`app/main.py:71-77`)** — everything mounts under `/api`. So the paths are `/api/stats/global`, `/api/endgames/overview`, `/api/openings/next-moves` (POST).
- **`ENDGAME_PLY_THRESHOLD`** (app/repositories/endgame_repository.py) — a span must have ≥ this many consecutive plies of the same `endgame_class` to qualify. The existing `test_endgames_router.py:96` seeds `range(30, 30 + ENDGAME_PLY_THRESHOLD)`. Same pattern applies here.
- **fastapi-users register response** exposes `id: int` directly (`BaseUser[int]` in `app/routers/auth.py:42`). `response.json()["id"]` is the authoritative source for the registered user's id.
- **`derive_user_result(result, user_color)`** in `app/services/openings_service.py` is the canonical WDL-perspective conversion. When we assert from the user's perspective (especially when user plays black), expected numbers must be built with this function in mind.
- **`apply_game_filters`** in `app/repositories/query_utils.py` centralizes filter logic. Testing intersection correctness is as simple as seeding games that straddle filter boundaries and asserting the filtered query returns exactly what we expect.
</code_context>

<specifics>
## Specific Ideas

- **Truncate implementation sketch:**
  ```python
  from sqlalchemy import text

  _TRUNCATE_EXCLUDE = frozenset({"alembic_version", "openings"})

  def _truncate_all_tables(sync_engine) -> None:
      with sync_engine.begin() as conn:
          rows = conn.execute(text(
              "SELECT tablename FROM pg_tables WHERE schemaname = 'public'"
          ))
          tables = [r[0] for r in rows if r[0] not in _TRUNCATE_EXCLUDE]
          if tables:
              conn.execute(text(
                  f'TRUNCATE TABLE {", ".join(tables)} RESTART IDENTITY CASCADE'
              ))
  ```
  Called from inside `test_engine` between `alembic_command.upgrade` and `create_async_engine`.

- **Seeded portfolio composition** (deterministic, ~15 games):
  - 3 chess.com blitz as white: 2W 1D 0L
  - 2 chess.com blitz as black: 1W (0-1) 0D 1L (1-0)
  - 2 chess.com rapid as white: 0W 0D 2L (both 0-1, user loses)
  - 2 lichess blitz as white: 2W 0D 0L
  - 2 lichess bullet as black: 0W 2D 0L
  - 2 lichess classical as white: 1W 0D 1L
  - 2 lichess rapid as white, 1 rated + 1 unrated
  - Opening positions: several games share the starting Zobrist hash so `/next-moves` has real material
  - Endgame spans: at least 3 games get ENDGAME_PLY_THRESHOLD+ consecutive plies with `endgame_class=1` (rook), plus 1 game with two class transitions (rook→pawn)
  - Total: 15 games; expected WDL from user's perspective: wins=6, draws=3, losses=6 — but verify by computing deterministically in the fixture rather than hand-counting.

- **Filter intersection test fixture**:
  - Seed 4 games: (chess.com, blitz), (chess.com, rapid), (lichess, blitz), (lichess, rapid). Assert the filter `platform=["chess.com"] AND time_control=["blitz"]` returns exactly 1 game, not 3 (union) or 0.

- **Recency boundary test**:
  - Seed one game at `played_at == cutoff_dt` (to the microsecond). Assert whether `apply_game_filters` includes or excludes it — then document the actual behavior in the test's docstring. If the behavior is inclusive, call it `test_recency_cutoff_inclusive_at_boundary`. This is a behavioral-pinning test, not a correctness assertion.

- **Position dedup test**:
  - Seed one game with 3 GamePosition rows all sharing the same `full_hash` at plies 0, 2, 4 (impossible in real chess but valid for testing the dedup logic). Call the openings analyze service with that hash. Assert total==1, not 3.

- **Endgame transition test**:
  - Seed one game with 6+ plies of `endgame_class=1` then 6+ plies of `endgame_class=3`. Call the endgame overview service. Assert per-type breakdown shows BOTH rook AND pawn classes with 1 game each; total is still 1 distinct game_id via `endgame_wdl.total`.

- **WDL-from-black-perspective test**:
  - Seed 3 games with `user_color="black"`: (result="0-1" → user wins), (result="1-0" → user loses), (result="1/2-1/2" → draw). Call `get_global_stats`. Assert the black bucket has wins=1, losses=1, draws=1.

- **Material tally tests** (no DB):
  ```python
  import chess
  from app.services.position_classifier import _compute_material_count, _compute_material_imbalance

  def test_starting_position_material():
      board = chess.Board()
      assert _compute_material_count(board) == 7800  # both sides full
      assert _compute_material_imbalance(board) == 0

  def test_after_white_captures_central_pawn():
      board = chess.Board()
      board.push_san("e4")
      board.push_san("d5")
      board.push_san("exd5")  # white captures black pawn
      assert _compute_material_imbalance(board) == 100  # +1 pawn = +100cp for white
      assert _compute_material_count(board) == 7700
  ```
  These catch a regression in the material constants or sign conventions.
</specifics>

<deferred>
## Deferred Ideas

- **ECO / opening_name double-match test** — needs the `openings` reference table to be populated in the test DB. Out of scope until we decide whether tests should seed reference data. Flag in final summary.
- **Rolling window edge cases** beyond what Plan 61-02 covers — e.g. timeline behavior under a 1-game window, or a window larger than total games. Add if cheap during execution, otherwise log as follow-up.
- **Opponent-type and opponent-strength filter intersection** — Phase 60 reworks some of this; we stick to platform × time_control for now.
</deferred>

<canonical_refs>
## Canonical References

- `tests/conftest.py` — edit target for Plan 61-01 Task 1 (truncate)
- `tests/seed_fixtures.py` — new file for Plan 61-01 Task 2 (seeded_user module fixture)
- `tests/test_aggregation_sanity.py` — new file for Plan 61-02
- `tests/test_integration_routers.py` — new file for Plan 61-03
- `tests/test_material_tally.py` — new file for Plan 61-02 (material tests)
- `app/core/database.py` — `async_session_maker` used by seed fixture
- `app/main.py:71-77` — router mount prefixes (all `/api`)
- `app/routers/auth.py:42` — register router exposes `id: int`
- `app/services/stats_service.py` — `get_global_stats`, `_rows_to_wdl_categories`
- `app/services/endgame_service.py` — `get_endgame_overview`, `_compute_score_gap_material`
- `app/services/openings_service.py` — `derive_user_result`, `get_next_moves`
- `app/services/position_classifier.py` — material helpers
- `app/repositories/query_utils.py` — `apply_game_filters`
- `app/repositories/endgame_repository.py` — `ENDGAME_PLY_THRESHOLD`, entry-row query
- `tests/test_endgames_router.py:54-113` — `_seed_game_with_endgame` pattern to mirror
- `tests/test_stats_service.py:63-119` — `_seed_game` pattern to mirror
- Phase 59 `59-01-PLAN.md` — reference format for plan structure, invariant assertions style
</canonical_refs>
