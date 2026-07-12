---
phase: 167-backend-store-on-finish
verified: 2026-07-11T20:00:00Z
status: passed
score: 12/12 must-haves verified
behavior_unverified: 0
overrides_applied: 0
---

# Phase 167: Backend Store-on-Finish Verification Report

**Phase Goal:** A finished bot game is persisted as a first-class `platform='flawchess'` Library game through the shared normalization/persistence path, carrying clocks, full bot settings, and a converted player rating.
**Verified:** 2026-07-11
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (ROADMAP SC1-SC5 + landmine checks)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| SC1 | POST `/bots/games` → `normalize_flawchess_game` → `_flush_batch` creates exactly one `platform='flawchess'` games row; drain-eligible; appears in Library games list | ✓ VERIFIED | `app/routers/bots.py` → `store_bot_game_service.store_bot_game` → `normalize_flawchess_game` (app/services/normalization.py:515) → `_flush_batch` (import_service). `tests/routers/test_bots.py::test_store_bot_game_creates_flawchess_game` asserts 200/created:true, exactly one `games` row (`len(rows)==1`), `evals_completed_at IS NULL`, and the game_id appears in `GET /api/library/games?platform=flawchess`. Passed live. |
| SC2 | Endpoint rejects a bot PGN missing per-move `[%clk]` with 422; stored bot games carry both-color clocks | ✓ VERIFIED | `normalize_flawchess_game` gates on `white_has_clock and black_has_clock` (normalization.py:577-582), returns `None`; router maps `None` → `HTTPException(422)` (bots.py:37-38). `tests/routers/test_bots.py::test_store_bot_game_missing_clock_returns_422` and `::test_store_bot_game_unparseable_pgn_returns_422` both pass; `tests/services/test_normalization.py::TestNormalizeFlawchessGame` covers white-only/black-only clock omission. |
| SC3 | `bot_game_settings` records nominal ELO + play_style_blend + tc_preset + rating_source; player-color rating column = converted rating; opponent-color = bot nominal ELO | ✓ VERIFIED | `app/models/bot_game_settings.py` has all 4 columns + CHECK constraint; migration `a07ccca76092` applied (`alembic heads` = head). `store_bot_game_service.py` derives `player_rating`/`rating_source` from `user_rating_anchors_repository.fetch_anchors_for_user` and places them per D-08 in `normalize_flawchess_game` (lines 617-629: player-color column = player_rating, opponent-color = bot_elo). `tests/services/test_store_bot_game_service.py::TestRatingDerivation` (lichess-only, no-anchor→NULL, blended) all pass and assert both the `games` row rating columns and the `bot_game_settings` row fields directly. |
| SC4 | Re-submitting the same `game_uuid` returns success (200) without a second games row or a second bot_game_settings row (idempotent on `uq_games_user_platform_game_id`) | ✓ VERIFIED | `uq_games_user_platform_game_id` constraint exists in `app/models/game.py:49`. `store_bot_game` uses `_flush_batch`'s ON CONFLICT DO NOTHING dedup (`inserted_count == 1` → `created`), guards the `BotGameSettings` insert with `if created:` (store_bot_game_service.py:115-126). `tests/services/test_store_bot_game_service.py::TestIdempotency::test_duplicate_game_uuid_returns_existing_id` asserts exactly 1 `games` row AND exactly 1 `bot_game_settings` row after a duplicate submit, `created=False` on the second call, same `game_id`. `tests/routers/test_bots.py::test_store_bot_game_idempotent_resubmit` confirms at the HTTP layer. Both pass. |
| SC5 | Flawchess excluded from default analytics (`apply_game_filters` platform=None) but present on Library; guest path works via `current_active_user` | ✓ VERIFIED | `DEFAULT_EXCLUDED_PLATFORMS = ("flawchess",)` + `apply_game_filters` else-branch `Game.platform.notin_(...)` (query_utils.py:30, 195-203). `get_library_games` substitutes `["chess.com","lichess","flawchess"]` when `platform is None` (library_service.py:704). `tests/repositories/test_query_utils.py::test_bot_opponent_type_excludes_flawchess_but_keeps_imported_bot_game` specifically uses `opponent_type='bot'` (not the default 'human' view) to avoid the false-positive test trap flagged in RESEARCH Pitfall 1 — passes. Guest path: `bots.py` router uses `Depends(current_active_user)` which covers guest `User` rows (`is_guest=True`) identically to registered users — no special-casing, matching D-13. |

**Score:** 5/5 roadmap SCs verified, 0 present-but-behavior-unverified.

### Landmine Checks

| Landmine | Status | Evidence |
|----------|--------|----------|
| `_flush_batch` game-id lookup helper exists and is used | ✓ VERIFIED | `app/repositories/game_repository.py::get_game_id_by_platform_game_id` (lines 70-95) added; called from `store_bot_game_service.py:107-109` immediately after `_flush_batch`. |
| `_build_card`/`normalize_to_lichess_blitz` has a `"flawchess"` guard preventing rating double-conversion | ✓ VERIFIED | `library_service.py:539` (`is_flawchess = game.platform == "flawchess"`) guards both `normalize_to_lichess_blitz` call sites (lines 542-560), passing the raw rating through when `is_flawchess`. `tests/services/test_library_service.py::test_flawchess_rapid_card_has_identity_normalized_rating` proves identity for a non-blitz bucket. |
| `Platform` Literal extended everywhere ty needs | ✓ VERIFIED | `app/schemas/normalization.py` Platform Literal includes `"flawchess"`; `uv run ty check app/ tests/` reports zero errors (ran live, "All checks passed!"). Unrelated inline `Literal["chess.com","lichess"]` filter types in insights.py/imports.py/opening_insights.py/openings.py/endgames.py deliberately left untouched per RESEARCH Pitfall 4 (confirmed by grep — no flawchess added there, and this is correct: adding it would make bot games user-selectable on analytics filters, violating STORE-07). |

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `app/schemas/bots.py` | StoreBotGameRequest/Response, no server-owned fields | ✓ VERIFIED | Exists; UUID validator, bot_elo bounds (600-2600), play_style_blend bounds (0-1), pgn max_length; no rating/platform/user_id/username/is_computer_game field (grep confirmed). |
| `app/models/bot_game_settings.py` | BotGameSettings model, FK CASCADE, CHECK constraint | ✓ VERIFIED | game_id PK/FK ondelete=CASCADE; CheckConstraint `ck_bot_game_settings_rating_source`; TEXT (not native ENUM). |
| Alembic migration | Creates bot_game_settings table | ✓ VERIFIED | `a07ccca76092` head revision; `alembic heads` confirms; contains ForeignKeyConstraint ondelete=CASCADE + CheckConstraint; no ENUM. |
| `app/services/normalization.py::normalize_flawchess_game` | PGN-only normalizer | ✓ VERIFIED | Present, single-parse, [%clk]/result/termination gating, D-08 rating placement, FLAWCHESS_BOT_USERNAME constant. |
| `app/repositories/game_repository.py::get_game_id_by_platform_game_id` | id-lookup helper | ✓ VERIFIED | Present, scoped by (user_id, platform, platform_game_id). |
| `app/services/store_bot_game_service.py::store_bot_game` | orchestration service | ✓ VERIFIED | Present; rating derivation, normalize, _flush_batch, id lookup, settings insert, single commit, Sentry on unexpected exceptions. |
| `app/routers/bots.py` + `app/main.py` registration | POST /bots/games | ✓ VERIFIED | Router registered (`app.include_router(bots_router, prefix="/api")`, main.py:181); thin, no business logic; 422 mapping; `current_active_user` dependency. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `bots.py` router | `store_bot_game_service.store_bot_game` | direct call, `user.id` from JWT | WIRED | Confirmed — `user.id` never sourced from request body. |
| `store_bot_game` | `normalize_flawchess_game` | direct call | WIRED | One PGN parse, results flow into NormalizedGame. |
| `normalize_flawchess_game` output | `_flush_batch` | 1-item batch list | WIRED | `await _flush_batch(session, [normalized], user_id)`. |
| `_flush_batch` result | `get_game_id_by_platform_game_id` | post-insert lookup | WIRED | Serves both newly-inserted and idempotent-duplicate paths (verified via tests). |
| `apply_game_filters` | `get_library_games` | opt-in seam | WIRED | `library_platform` local variable substitutes explicit list including flawchess when platform is None. |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| STORE-01 | 167-02, 167-03 | Stored via shared path, appears in Library | ✓ SATISFIED | test_bots.py::test_store_bot_game_creates_flawchess_game |
| STORE-02 | 167-03 | [%clk] gate, 422 on missing | ✓ SATISFIED | test_bots.py 422 tests, test_normalization.py TestNormalizeFlawchessGame |
| STORE-03 | 167-01, 167-03 | Converted rating + bot ELO + rating_source | ✓ SATISFIED | test_store_bot_game_service.py::TestRatingDerivation |
| STORE-04 | 167-01, 167-03 | Full bot settings recorded | ✓ SATISFIED | BotGameSettings row asserted with nominal_elo/play_style_blend/tc_preset in TestRatingDerivation::test_lichess_only_anchor |
| STORE-05 | 167-01, 167-03 | Idempotent on UUID | ✓ SATISFIED | TestIdempotency + test_bots.py::test_store_bot_game_idempotent_resubmit |
| STORE-06 | 167-03 | Analyzable exactly like imported; guest caveat (existing exclusion) | ✓ SATISFIED | evals_completed_at IS NULL assertion in test_bots.py; guest exclusion is the pre-existing eval_queue_service.py is_guest filter (unmodified, confirmed present) |
| STORE-07 | 167-02 | Excluded from default analytics, present on Library/Bots | ✓ SATISFIED | test_query_utils.py::TestApplyGameFiltersFlawchessExclusion (3 tests, including the opponent_type='bot' non-trivial case) |

No orphaned requirements — all 7 STORE-01..07 IDs declared across the three plans' frontmatter match REQUIREMENTS.md exactly, and REQUIREMENTS.md's traceability table marks all 7 as "Phase 167 / Complete".

### Anti-Patterns Found

None. Grep for TBD/FIXME/XXX/TODO/HACK/PLACEHOLDER across all phase-modified files returned zero hits. `ruff check` on all phase files passes clean. No stub returns, no hardcoded empty data flowing to output.

### Behavioral Spot-Checks / Test Execution

| Check | Command | Result | Status |
|-------|---------|--------|--------|
| Type check | `uv run ty check app/ tests/` | "All checks passed!" | ✓ PASS |
| Targeted phase tests | `uv run pytest tests/routers/test_bots.py tests/services/test_store_bot_game_service.py tests/services/test_normalization.py tests/schemas/test_bots.py tests/repositories/test_bot_game_settings_repository.py tests/repositories/test_query_utils.py tests/services/test_library_service.py -q` | 85 passed | ✓ PASS |
| Full backend suite | `uv run pytest -n auto -q` | 3240 passed, 18 skipped | ✓ PASS |
| Alembic head | `uv run alembic heads` | `a07ccca76092 (head)` | ✓ PASS |

### Human Verification Required

None. This is a pure backend endpoint with no UI surface in this phase's scope — all behaviors (persistence, idempotency, rating derivation, analytics exclusion, [%clk] gating, guest auth) are covered by executed integration/unit tests against a real Postgres dev DB, not mocked. No behavior-dependent truth was left unexercised.

### Gaps Summary

No gaps. All 5 ROADMAP success criteria, all 3 landmine checks, and all 7 requirement IDs (STORE-01 through STORE-07) are verified against real, passing code and tests — not SUMMARY.md narrative. The one deliberately deferred item (frontend/router `opponent_type` default wiring and the guest-caveat UI) is explicitly out of this phase's scope per 167-CONTEXT.md (Phase 171), correctly documented in code comments (`library_service.py` docstring) and not claimed as done by this phase.

---

_Verified: 2026-07-11_
_Verifier: Claude (gsd-verifier)_
