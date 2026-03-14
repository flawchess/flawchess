---
phase: 09-rework-the-games-list-with-game-cards-username-import-and-improved-pagination
verified: 2026-03-14T17:26:35Z
status: passed
score: 15/15 must-haves verified
re_verification:
  previous_status: "passed (incomplete — predated gap-closure plans 09-04 and 09-05)"
  previous_score: 13/13
  gaps_closed:
    - "Game cards show both player usernames with color indicators and ratings"
    - "Dashboard shows unfiltered games list by default on mount instead of placeholder"
    - "Game model stores white_username, black_username, white_rating, black_rating per game"
    - "Analysis endpoint works with target_hash=None (returns all user games)"
  gaps_remaining: []
  regressions: []
---

# Phase 9: Rework the Games List — Verification Report

**Phase Goal:** Transform the games list from a plain HTML table to rich full-width game cards showing
more metadata per game, move chess platform usernames from localStorage to backend user profile storage
with a streamlined import modal, and replace naive pagination with truncated page numbers and a smaller
page size.
**Verified:** 2026-03-14T17:26:35Z
**Status:** passed
**Re-verification:** Yes — previous verification was incomplete (predated gap-closure plans 09-04 and
09-05 execution). This report covers all five plans and both UAT gap-closure cycles.

---

## Goal Achievement

### Observable Truths

| #  | Truth | Status | Evidence |
|----|-------|--------|----------|
| 1  | GameRecord API response includes user_rating, opponent_rating, opening_name, opening_eco, user_color, move_count | VERIFIED | `app/schemas/analysis.py` lines 68–77; `app/services/analysis_service.py` lines 148–162 |
| 2  | GameRecord API response includes white_username, black_username, white_rating, black_rating | VERIFIED | `app/schemas/analysis.py` lines 70–73; `app/services/analysis_service.py` lines 155–158 |
| 3  | GET /users/me/profile returns chess_com_username and lichess_username | VERIFIED | `app/routers/users.py` line 20: `@router.get("/me/profile")` returns `UserProfileResponse` |
| 4  | PUT /users/me/profile updates chess_com_username and/or lichess_username | VERIFIED | `app/routers/users.py` line 33: `@router.put("/me/profile")` calls `user_repository.update_profile` |
| 5  | After an import completes, platform username is auto-saved to user profile | VERIFIED | `app/services/import_service.py` lines 178–185: best-effort `update_platform_username` after commit |
| 6  | move_count is populated for newly imported games | VERIFIED | `app/services/import_service.py` lines 327–338: `move_count = (ply_count + 1) // 2` via `sa_update` |
| 7  | Existing games have move_count backfilled from PGN | VERIFIED | Migration `f009f3b41e8e` lines 35–74: batch loop over all `move_count IS NULL` games |
| 8  | Existing games have white/black username and rating backfilled | VERIFIED | Migration `1c4985e5016a` lines 35–41: SQL UPDATE backfill using user_color + opponent_username logic |
| 9  | Games displayed as full-width cards with colored left border (green/gray/red) | VERIFIED | `GameCard.tsx` lines 15–19: `BORDER_CLASSES` map; `border-l-4` in className at line 52 |
| 10 | Each card shows both players with color indicators, ratings, opening+ECO, time control, date, move count | VERIFIED | `GameCard.tsx` lines 42–103: whiteName/blackName/ratings on line 1; opening/TC/date/moves on line 2 |
| 11 | Pagination uses truncated page numbers with ellipsis | VERIFIED | `GameCardList.tsx` lines 24–55: `getPaginationItems()` with ellipsis markers for totalPages > 7 |
| 12 | Page size is 20 | VERIFIED | `frontend/src/pages/Dashboard.tsx` line 39: `const PAGE_SIZE = 20` |
| 13 | Dashboard shows unfiltered games list by default on mount | VERIFIED | `Dashboard.tsx` line 71: `positionFilterActive` starts `false`; `useGamesQuery` enabled at lines 73–76 |
| 14 | Returning user sees stored usernames and per-platform Sync buttons | VERIFIED | `ImportModal.tsx` lines 169–233: sync view with per-platform rows, Sync buttons, Edit usernames link |
| 15 | localStorage username storage is removed from frontend | VERIFIED | No `localStorage` references in `ImportModal.tsx`, `useImport.ts`, or any import hook |

**Score:** 15/15 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `app/schemas/users.py` | UserProfileResponse and UserProfileUpdate schemas | VERIFIED | Both classes; correct nullable fields |
| `app/routers/users.py` | GET/PUT /users/me/profile endpoints | VERIFIED | Router prefix `/users`; both endpoints wired to user_repository |
| `app/repositories/user_repository.py` | get_profile, update_profile, update_platform_username | VERIFIED | All three async functions implemented with correct SQLAlchemy |
| `app/models/game.py` | move_count, white_username, black_username, white_rating, black_rating columns | VERIFIED | Lines 42–45 (white/black) and line 57 (move_count) |
| `app/models/user.py` | chess_com_username, lichess_username columns | VERIFIED | Lines 18–19 with String(100) nullable |
| `app/core/config.py` | ENVIRONMENT setting | VERIFIED | Line 14: `ENVIRONMENT: str = "production"` |
| `app/users.py` | Dev-mode auth bypass | VERIFIED | Lines 83–106: `_dev_bypass_user` + conditional `current_active_user` |
| `app/services/normalization.py` | white_username, black_username, white_rating, black_rating in both normalizers | VERIFIED | chess.com lines 175–178; lichess lines 286–289 |
| `alembic/versions/f009f3b41e8e_...py` | Migration: move_count + username columns with PGN backfill | VERIFIED | 3 columns added; batch backfill loop present |
| `alembic/versions/1c4985e5016a_...py` | Migration: white/black username/rating columns with SQL backfill | VERIFIED | 4 columns added; backfill SQL UPDATE in lines 35–41 |
| `tests/test_users_router.py` | Tests for profile GET/PUT endpoints | VERIFIED | 4 tests; all pass (4 passed, 4 warnings in 0.51s) |
| `frontend/src/components/results/GameCard.tsx` | Card with left border and both-player display (min 40 lines) | VERIFIED | 106 lines; substantive rendering of all required fields |
| `frontend/src/components/results/GameCardList.tsx` | Card list with truncated pagination (min 60 lines) | VERIFIED | 154 lines; `getPaginationItems()` + scroll-to-top |
| `frontend/src/types/users.ts` | UserProfile type with chess_com_username, lichess_username | VERIFIED | Both fields as `string | null` |
| `frontend/src/types/api.ts` | GameRecord with new fields; optional target_hash in AnalysisRequest | VERIFIED | Line 31 (`target_hash?`), lines 67–70 (white/black player fields) |
| `frontend/src/hooks/useUserProfile.ts` | useUserProfile query + useUpdateUserProfile mutation | VERIFIED | 28 lines; staleTime 300_000; direct query data update on mutation |
| `frontend/src/hooks/useAnalysis.ts` | useGamesQuery hook for auto-fetch on mount | VERIFIED | Lines 18–33: useQuery with no target_hash; enabled param forwarded from Dashboard |
| `frontend/src/components/import/ImportModal.tsx` | Redesigned two-mode import modal (min 80 lines) | VERIFIED | 238 lines; sync view and input view fully implemented |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `app/services/import_service.py` | `app/repositories/user_repository.py` | `update_platform_username` after import | WIRED | Line 180: `await user_repository.update_platform_username(session, job.user_id, job.platform, job.username)` |
| `app/services/analysis_service.py` | `app/schemas/analysis.py` | GameRecord construction with all new fields | WIRED | Lines 148–162: all 10 new fields populated from `g.*` |
| `app/main.py` | `app/routers/users.py` | `include_router` registration | WIRED | Line 24: `app.include_router(users_router)` |
| `app/services/normalization.py` | `app/models/game.py` | white/black username+rating in normalized dicts | WIRED | Both normalizers include all 4 new fields in their return dicts |
| `app/repositories/analysis_repository.py` | `app/schemas/analysis.py` | target_hash=None skips position join | WIRED | Line 45: `if target_hash is not None and hash_column is not None` branch |
| `frontend/src/pages/Dashboard.tsx` | `frontend/src/hooks/useAnalysis.ts` | `useGamesQuery` auto-fetches on mount | WIRED | Line 18: import; lines 73–76: `useGamesQuery({ offset, limit, enabled: !positionFilterActive })` |
| `frontend/src/pages/Dashboard.tsx` | `frontend/src/components/results/GameCardList.tsx` | Renders default games list | WIRED | Line 30: import; lines 463–474: `<GameCardList .../>` for default games path |
| `frontend/src/components/import/ImportModal.tsx` | `frontend/src/hooks/useUserProfile.ts` | `useUserProfile` to determine sync vs input mode | WIRED | Lines 12–13: import; line 49: `isFirstTime` derived from profile data |
| `frontend/src/hooks/useUserProfile.ts` | `/users/me/profile` | API call via apiClient | WIRED | Line 9: `apiClient.get<UserProfile>('/users/me/profile')`; line 21: `apiClient.put` |
| `frontend/vite.config.ts` | `http://localhost:8000` | `/users` proxy entry | WIRED | Line 28: `'/users': 'http://localhost:8000'` |

---

### Requirements Coverage

The requirement IDs GAMES-01 through GAMES-05 are phase-internal IDs defined in plan frontmatter. They do
not appear in `REQUIREMENTS.md` (which uses IMP-*, ANL-*, FLT-*, RES-*, AUTH-*, INFRA-* namespacing). All
GAMES-* IDs are fully accounted for across the five plans. No requirement IDs from REQUIREMENTS.md are
claimed by or orphaned in this phase — the phase extends the platform beyond the v1 requirement set.

| Requirement | Source Plans | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| GAMES-01 | 09-01, 09-02, 09-04, 09-05 | Games displayed as full-width cards with colored left border and all metadata | SATISFIED | `GameCard.tsx` with `border-l-4` result color; both-player display verified in code |
| GAMES-02 | 09-01 | Game model has move_count; backfilled from PGN; populated at import | SATISFIED | `app/models/game.py` line 57; migration `f009f3b41e8e` backfill; import service lines 327–338 |
| GAMES-03 | 09-01, 09-03 | Platform usernames on backend; auto-saved on import; modal sync/input views | SATISFIED | `app/models/user.py` lines 18–19; `update_platform_username`; `ImportModal.tsx` two-mode UI |
| GAMES-04 | 09-01, 09-04 | GameRecord API response expanded with new fields including both-player data | SATISFIED | `app/schemas/analysis.py` lines 58–77: all 10 new fields present |
| GAMES-05 | 09-02, 09-05 | Truncated pagination; page size 20; default games list on mount | SATISFIED | `getPaginationItems()` in `GameCardList.tsx`; `PAGE_SIZE=20`; `useGamesQuery` wired to Dashboard |

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `alembic/versions/7eb7ce83cdb9_...py` | 11 | Unused `sqlalchemy` import (ruff F401, auto-fixable) | Info | Pre-existing from earlier phase |
| `app/models/game.py` | 66 | Ruff F821 forward ref `GamePosition` (suppressed with `# type: ignore`) | Info | Pre-existing; correct suppression |
| `app/models/game_position.py` | 28 | Ruff F821 forward ref `Game` | Info | Pre-existing |
| `tests/test_bookmark_repository.py` | 19 | Unused import `PositionBookmarkReorderRequest` (ruff F401) | Info | Pre-existing |
| `frontend/src/components/filters/FilterPanel.tsx` | 22 | ESLint `react-refresh/only-export-components` | Info | Pre-existing from earlier phase |
| `frontend/src/components/ui/badge.tsx` | 49 | ESLint `react-refresh/only-export-components` | Info | Pre-existing shadcn/ui generated code |
| `frontend/src/components/ui/button.tsx` | 67 | ESLint `react-refresh/only-export-components` | Info | Pre-existing shadcn/ui generated code |
| `frontend/src/components/ui/tabs.tsx` | 90 | ESLint `react-refresh/only-export-components` | Info | Pre-existing shadcn/ui generated code |
| `frontend/src/components/ui/toggle.tsx` | 44 | ESLint `react-refresh/only-export-components` | Info | Pre-existing shadcn/ui generated code |

No blockers or warnings introduced by phase 9. All listed issues are pre-existing from earlier phases.

---

### Human Verification Required

#### 1. Card visual layout in browser

**Test:** Open the Dashboard, run an analysis query returning 5+ games.
**Expected:** Each card has a clear colored left border (green for win, gray for draw, red for loss); result
badge, both player names with circle indicators (white circle = white player, black circle = black player),
ratings in parentheses, opening+ECO, time control, date, move count, and platform link are all visible.
**Why human:** Visual hierarchy and Tailwind CSS rendering require browser inspection.

#### 2. Default games list on mount

**Test:** Log in as a user who has already imported games. Navigate to the Dashboard without clicking Filter.
**Expected:** The right column immediately shows game cards (not the "Play moves on the board" placeholder).
A count like "247 games imported" is visible above the card list.
**Why human:** Requires a real user session with imported games; cannot confirm API call fires in a static check.

#### 3. Truncated pagination with large result sets

**Test:** With 50+ games imported, navigate to page 5 of the default games list.
**Expected:** Pagination shows: `< 1 ... 3 4 5 6 7 ... N >` — first page, window around current page, last
page, ellipsis in gaps.
**Why human:** Requires actual data with many pages to exercise the ellipsis logic in practice.

#### 4. Position filter switches view and board reset returns to default

**Test:** Play moves on the board and click Filter. Then click the board reset button.
**Expected:** After Filter: WDL bar appears and game list shows position-matched games only. After reset:
WDL bar disappears and the default unfiltered game list reappears.
**Why human:** Requires interactive UI flow with live board state changes.

#### 5. Import modal sync view after first import

**Test:** Log in as a new user, open Import modal, enter a chess.com username and start import. Wait for
completion toast. Re-open Import modal.
**Expected:** Modal now shows the sync view with the stored chess.com username and a "Sync" button — no
input fields.
**Why human:** Requires a live import cycle to confirm auto-save and profile query invalidation work end-to-end.

---

### Test Suite Results

- **Backend:** 249 tests pass (`uv run pytest tests/ -q — 249 passed, 25 warnings in 2.77s`)
- **Frontend build:** Clean (`npm run build — built in 3.15s`; no errors; only pre-existing chunk size warning)
- **Frontend lint:** 5 pre-existing ESLint errors in shadcn/ui generated files and FilterPanel; 0 new errors from phase 9
- **Backend lint:** 6 ruff findings, all pre-existing from earlier phases; none in phase 9 files

---

### Phase Execution Summary

This phase required five plans executed in two waves with a UAT cycle between them:

- **Wave 1 (Plans 09-01, 09-02):** Backend model expansion (move_count, username columns), profile endpoint, schema enrichment, GameCard and GameCardList frontend components, truncated pagination, import modal redesign, and page size change.
- **UAT cycle:** User testing found two major issues: (1) game cards showed only opponent name rather than both players, and (2) dashboard showed a placeholder instead of a default games list.
- **Gap-closure Wave 1 (Plan 09-04):** Backend — added white_username, black_username, white_rating, black_rating columns to Game model; updated normalization; made target_hash optional in analysis endpoint; added dev auth bypass.
- **Gap-closure Wave 2 (Plans 09-03, 09-05):** Frontend — redesigned GameCard to show both players on one line; added useGamesQuery hook; wired Dashboard to show default games list on mount; import modal redesign finalized.

All gaps are resolved. The phase goal is fully achieved.

---

_Verified: 2026-03-14T17:26:35Z_
_Verifier: Claude (gsd-verifier)_
