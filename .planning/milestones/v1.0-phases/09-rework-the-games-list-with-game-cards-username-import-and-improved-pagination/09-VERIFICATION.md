---
phase: 09-rework-the-games-list-with-game-cards-username-import-and-improved-pagination
verified: 2026-03-14T21:00:00Z
status: human_needed
score: 17/17 must-haves verified
re_verification:
  previous_status: gaps_found
  previous_score: 15/17
  gaps_closed:
    - "test_auth.py::TestUserIsolation::test_user_isolation_analysis passes — black_username replaces removed opponent_username"
    - "All auth-related tests pass with dev bypass neutralized by conftest.py session fixture"
  gaps_remaining: []
  regressions: []
human_verification:
  - test: "Visual card layout in browser"
    expected: "Each game card has colored left border (green=win, gray=draw, red=loss); W/D/L badge; white circle + white username (muted) vs black circle + black username (muted) with opponent name bolded; second line shows opening+ECO, time control, date, move count"
    why_human: "Tailwind CSS rendering and visual hierarchy require browser inspection to confirm bolding and border colors are perceptible"
  - test: "Import modal Add button end-to-end"
    expected: "After importing from chess.com only, open Import modal. chess.com row shows Sync button with stored username. lichess row shows Add button. Clicking Add expands inline input. Entering a username and clicking Import starts the lichess import and closes the modal."
    why_human: "Requires a live import cycle to confirm profile auto-save, modal state reset on close, and addingPlatform state transitions work end-to-end"
---

# Phase 9: Rework the Games List — Verification Report (Fourth Pass)

**Phase Goal:** Transform the games list from a plain HTML table to rich full-width game cards showing more metadata per game, move chess platform usernames from localStorage to backend user profile storage with a streamlined import modal, and replace naive pagination with truncated page numbers and a smaller page size.
**Verified:** 2026-03-14T21:00:00Z
**Status:** human_needed
**Re-verification:** Yes — fourth pass after gap-closure plan 09-08 (test regression fixes).

---

## What Changed Since Previous Verification

Plan 09-08 fixed the two gaps identified in the third-pass verification:

1. `tests/conftest.py` — added `disable_dev_auth_bypass` session-scoped autouse fixture using `dependency_overrides[_dev_bypass_user] = _jwt_current_active_user`. This neutralizes the dev auth bypass for all tests regardless of `ENVIRONMENT` setting.
2. `tests/test_auth.py` line 202 — replaced `opponent_username="opponent"` with `black_username="opponent"` (correct because `user_color="white"` on line 201 means the opponent plays black).

Full test suite result: **249 passed, 0 failed** (confirmed by live run).

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|---------|
| 1 | GameRecord API response includes white_username, black_username, white_rating, black_rating, user_color, move_count, opening_name, opening_eco; no redundant fields | VERIFIED | `app/schemas/analysis.py` lines 58–74: clean schema; grep confirms no opponent_username/user_rating/opponent_rating |
| 2 | GET /users/me/profile returns chess_com_username and lichess_username | VERIFIED | `app/routers/users.py`: @router.get("/me/profile") returns UserProfileResponse |
| 3 | PUT /users/me/profile updates chess_com_username and/or lichess_username | VERIFIED | `app/routers/users.py`: @router.put("/me/profile") calls user_repository.update_profile |
| 4 | After import, platform username auto-saved to user profile | VERIFIED | `app/services/import_service.py` lines 178–185: best-effort update_platform_username after commit |
| 5 | move_count populated for newly imported games | VERIFIED | `app/services/import_service.py` lines 327–338: move_count via sa_update |
| 6 | Existing games have white/black username and rating backfilled | VERIFIED | Migration 1c4985e5016a: SQL UPDATE backfill |
| 7 | Games displayed as full-width cards with colored left border | VERIFIED | `GameCard.tsx` lines 15–19: BORDER_CLASSES map; border-l-4 in className at lines 52–53 |
| 8 | White player always on left (muted) with white circle; black player on right (muted) with black circle; opponent name bolded | VERIFIED | `GameCard.tsx` lines 68, 74: !isUserWhite bolds white span (opponent when user is black); isUserWhite bolds black span (opponent when user is white) |
| 9 | Card shows opening+ECO, time control, date, move count on second line | VERIFIED | `GameCard.tsx` lines 96–103: second row renders all four fields |
| 10 | Pagination uses truncated page numbers with ellipsis | VERIFIED | `GameCardList.tsx` lines 24–55: getPaginationItems() with ellipsis markers for totalPages > 7 |
| 11 | Page size is 20 | VERIFIED | `frontend/src/pages/Dashboard.tsx` line 39: PAGE_SIZE = 20 |
| 12 | Dashboard shows unfiltered games list by default on mount | VERIFIED | `Dashboard.tsx`: positionFilterActive starts false; useGamesQuery enabled for default path |
| 13 | Returning user sees stored usernames with per-platform Sync buttons | VERIFIED | `ImportModal.tsx` lines 202–210: Sync button for configured platform |
| 14 | Sync view shows Add button for unconfigured platform | VERIFIED | `ImportModal.tsx` lines 241–250: Add button branch when platform username is null |
| 15 | Clicking Add shows inline input + Import/Cancel buttons | VERIFIED | `ImportModal.tsx` lines 212–240: inline input with onKeyDown Enter support and Import/Cancel buttons |
| 16 | test_auth.py::TestUserIsolation::test_user_isolation_analysis passes | VERIFIED | `tests/test_auth.py` line 202: uses `black_username="opponent"` — live run confirms PASSED |
| 17 | All auth assertion tests pass in test environment | VERIFIED | `tests/conftest.py` lines 9–22: disable_dev_auth_bypass fixture with dependency_overrides — live run: 249 passed, 0 failed |

**Score:** 17/17 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `app/models/game.py` | white_username, black_username, white_rating, black_rating, move_count; no redundant columns | VERIFIED | Lines 42–52; opponent_username/opponent_rating/user_rating absent (confirmed by grep) |
| `app/schemas/analysis.py` | GameRecord with new fields only; no redundant fields | VERIFIED | Lines 58–74: clean schema (confirmed by grep) |
| `app/repositories/stats_repository.py` | Derives user_rating via CASE WHEN | VERIFIED | Lines 25–28: case(user_color == 'white', white_rating, else_=black_rating).label("user_rating") |
| `alembic/versions/697d7b8842d2_drop_redundant_user_relative_columns.py` | Drops opponent_username, opponent_rating, user_rating | VERIFIED | Lines 24–26: op.drop_column for all three; downgrade with add_column present |
| `frontend/src/components/results/GameCard.tsx` | Opponent bolded, white on left, black on right | VERIFIED | 106 lines; bolding logic correct at lines 68 and 74 |
| `frontend/src/components/import/ImportModal.tsx` | Sync view with Add button for unconfigured platforms | VERIFIED | 340 lines; addingPlatform state; handleAdd handler; per-platform ternary branching |
| `frontend/src/types/api.ts` | GameRecord without redundant fields | VERIFIED | Lines 53–68: only white/black player fields; confirmed by grep |
| `tests/conftest.py` | Session-scoped autouse fixture overriding ENVIRONMENT to production for test suite | VERIFIED | Lines 9–22: disable_dev_auth_bypass uses dependency_overrides[_dev_bypass_user] = _jwt_current_active_user |
| `tests/test_auth.py` | No reference to removed opponent_username column | VERIFIED | Line 202: black_username="opponent"; grep confirms no opponent_username remaining |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `app/repositories/stats_repository.py` | `app/models/game.py` | CASE WHEN user_color='white' THEN white_rating ELSE black_rating | WIRED | Lines 25–28: case() expression with correct column references |
| `app/services/analysis_service.py` | `app/schemas/analysis.py` | GameRecord construction without redundant fields | WIRED | Schema has no opponent_username/user_rating/opponent_rating; confirmed by grep |
| `frontend/src/components/import/ImportModal.tsx` | `useImportTrigger` | handleAdd calls trigger.mutateAsync({ platform, username: trimmed }) | WIRED | Lines 72–84: handleAdd passes correct args to trigger |
| `frontend/src/components/results/GameCard.tsx` | `frontend/src/types/api.ts` | GameRecord type; white_username/black_username used for player display | WIRED | Lines 42–45: whiteName/blackName derived from white_username/black_username |
| `tests/conftest.py` | `app/users.py` | FastAPI dependency_overrides[_dev_bypass_user] = _jwt_current_active_user | WIRED | conftest.py line 20: override registered on app instance; 249/249 tests pass |

---

### Requirements Coverage

| Requirement | Source Plans | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| GAMES-01 | 09-01, 09-02, 09-04, 09-05, 09-06 | Games displayed as full-width cards; opponent bolded; white player on left with correct circles | SATISFIED | GameCard.tsx with correct bolding (lines 68, 74) and border-l-4 result color |
| GAMES-02 | 09-01 | Game model has move_count; backfilled; populated at import | SATISFIED | app/models/game.py line 52; migration f009f3b41e8e; import service |
| GAMES-03 | 09-01, 09-03, 09-07 | Platform usernames on backend; auto-saved on import; modal sync/input/add views | SATISFIED | app/models/user.py; update_platform_username; ImportModal.tsx three views |
| GAMES-04 | 09-01, 09-04, 09-06 | GameRecord API expanded with white/black player data; redundant fields removed | SATISFIED | app/schemas/analysis.py lines 58–74: clean final schema |
| GAMES-05 | 09-02, 09-05 | Truncated pagination; page size 20; default games list on mount | SATISFIED | getPaginationItems() in GameCardList.tsx; PAGE_SIZE=20; useGamesQuery wired |

All GAMES-* requirement IDs accounted for across plans 09-01 through 09-08. No REQUIREMENTS.md requirement IDs (IMP-*, ANL-*, etc.) are claimed by or orphaned in this phase.

---

### Anti-Patterns Found

None. All previously identified blockers (test_auth.py opponent_username reference, auth bypass in tests) resolved by plan 09-08. No new anti-patterns detected.

---

### Human Verification Required

#### 1. Card visual layout in browser

**Test:** Open the Dashboard with imported games.
**Expected:** Each card has colored left border (green=win, gray=draw, red=loss); W/D/L badge; white circle + white username vs black circle + black username with opponent name bolded (user's own name is muted); second line shows opening+ECO, time control, date, move count.
**Why human:** Tailwind CSS rendering and visual hierarchy require browser inspection to confirm the bolding is perceptible and border colors render correctly.

#### 2. Import modal Add button end-to-end

**Test:** Import from chess.com. After import completes, re-open Import modal.
**Expected:** chess.com row shows Sync button with stored username. lichess row shows Add button. Clicking Add expands inline input. Entering a username and clicking Import starts the lichess import and closes the modal.
**Why human:** Requires a live import cycle to confirm profile auto-save, modal state reset on close, and addingPlatform state transitions work end-to-end.

---

### Test Suite Results

- **Backend:** 249 passing, 0 failing (confirmed by live run during this verification)
- **All 8 previously failing tests now pass:**
  - `tests/test_auth.py`: 0 failures (TypeError fixed + auth bypass neutralized)
  - `tests/test_users_router.py`: 0 failures (auth bypass neutralized)
  - `tests/test_stats_router.py`: 0 failures (auth bypass neutralized)
- **Frontend build:** Confirmed clean in 09-06/09-07 summaries; no frontend changes in 09-08

---

### Gaps Summary

No gaps remain. All 17 truths are verified. The two outstanding items (visual layout, import modal end-to-end) require human browser testing and cannot be resolved programmatically.

---

_Verified: 2026-03-14T21:00:00Z_
_Verifier: Claude (gsd-verifier)_
