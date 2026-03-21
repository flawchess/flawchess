---
phase: 20-rename-branding
plan: 01
subsystem: infra
tags: [branding, rename, pwa, config]

# Dependency graph
requires:
  - phase: 19-mobile-ux-polish-install-prompt
    provides: InstallPromptBanner component with "Install Chessalytics" text (now updated)
provides:
  - All source, config, test, and planning files use "FlawChess"/"flawchess" exclusively
  - PWA manifest name and short_name set to "FlawChess"
  - Browser tab title reads "FlawChess"
  - apple-touch-icon.png placeholder at frontend/public/icons/
affects: [21-docker-deployment, 22-cicd-monitoring, 23-launch-readiness]

# Tech tracking
tech-stack:
  added: []
  patterns: []

key-files:
  created:
    - frontend/public/icons/apple-touch-icon.png
  modified:
    - pyproject.toml
    - app/main.py
    - app/core/config.py
    - app/services/chesscom_client.py
    - app/services/zobrist.py
    - app/routers/auth.py
    - frontend/index.html
    - frontend/vite.config.ts
    - frontend/src/App.tsx
    - frontend/src/pages/Auth.tsx
    - frontend/src/components/install/InstallPromptBanner.tsx
    - frontend/src/lib/zobrist.ts
    - tests/conftest.py
    - tests/test_chesscom_client.py
    - .env.example
    - CLAUDE.md
    - README.md
    - .planning/PROJECT.md
    - .planning/STATE.md
    - .planning/MILESTONES.md

key-decisions:
  - "CSRF cookie renamed from chessalytics_oauth_csrf to flawchess_oauth_csrf — breaks in-flight OAuth sessions but acceptable for pre-production rename"
  - "apple-touch-icon.png is a copy of icon-192.png as placeholder — user will provide final 180x180 PNG asset"

patterns-established: []

requirements-completed: [BRAND-01, BRAND-02, BRAND-03]

# Metrics
duration: 10min
completed: 2026-03-21
---

# Phase 20 Plan 01: Rename & Branding Summary

**Full codebase renamed from Chessalytics to FlawChess across 20 files — PWA manifest, browser title, app header, User-Agent, DB defaults, all updated; apple-touch-icon.png placeholder added; 313 tests pass**

## Performance

- **Duration:** ~10 min
- **Started:** 2026-03-21T14:06:27Z
- **Completed:** 2026-03-21T14:11:04Z
- **Tasks:** 2
- **Files modified:** 21 (20 renamed + 1 created)

## Accomplishments

- Renamed all source, config, test, and active planning files from Chessalytics to FlawChess
- Updated PWA manifest name/short_name to "FlawChess" and browser tab title
- Created apple-touch-icon.png placeholder (copy of icon-192.png) at correct path
- All 313 backend tests pass; frontend builds successfully

## Task Commits

1. **Task 1: Rename all backend, frontend, config, and doc files** - `0917337` (feat)
2. **Task 2: Create apple-touch-icon placeholder and verify tests pass** - `922dc15` (feat)

## Files Created/Modified

- `frontend/public/icons/apple-touch-icon.png` - iOS home screen icon placeholder (copy of icon-192.png)
- `pyproject.toml` - `name = "flawchess"`
- `app/main.py` - `title="FlawChess"`
- `app/core/config.py` - DATABASE_URL defaults use `flawchess`/`flawchess_test`
- `app/services/chesscom_client.py` - `USER_AGENT = "FlawChess/1.0 (github.com/flawchess/flawchess)"`
- `app/services/zobrist.py` - Module docstring updated
- `app/routers/auth.py` - CSRF cookie renamed to `flawchess_oauth_csrf`
- `frontend/index.html` - Title and apple-touch-icon href updated
- `frontend/vite.config.ts` - PWA manifest name/short_name updated
- `frontend/src/App.tsx` - Both NavHeader and MobileHeader brand text updated
- `frontend/src/pages/Auth.tsx` - h1 heading updated
- `frontend/src/components/install/InstallPromptBanner.tsx` - DrawerTitle updated
- `frontend/src/lib/zobrist.ts` - File comment updated
- `tests/conftest.py` - DB name comments updated
- `tests/test_chesscom_client.py` - User-Agent assertion updated
- `.env.example` - DATABASE_URL defaults updated
- `CLAUDE.md` - Project section heading updated
- `README.md` - H1 heading updated
- `.planning/PROJECT.md` - Heading and description updated
- `.planning/STATE.md` - "formerly Chessalytics" removed from heading
- `.planning/MILESTONES.md` - Heading updated

## Decisions Made

- CSRF cookie renamed from `chessalytics_oauth_csrf` to `flawchess_oauth_csrf` — this was not in the explicit plan file list but was found during grep verification. Renamed since it's a branding string and pre-production.
- `apple-touch-icon.png` is a copy of `icon-192.png` (192x192) as a placeholder — the user will provide the final 180x180 PNG asset.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Updated CSRF cookie name in app/routers/auth.py**

- **Found during:** Task 1 (grep verification pass)
- **Issue:** `_CSRF_COOKIE = "chessalytics_oauth_csrf"` in `app/routers/auth.py` was not in the plan's file list but contained a "chessalytics" string
- **Fix:** Renamed to `"flawchess_oauth_csrf"` — consistent with rebrand, acceptable pre-production
- **Files modified:** `app/routers/auth.py`
- **Verification:** Tests still pass (no test asserts on cookie name string), grep shows no remaining occurrences
- **Committed in:** `0917337` (Task 1 commit)

**2. [Rule 2 - Missing Critical] Updated README.md**

- **Found during:** Task 1 (grep verification pass)
- **Issue:** `README.md` was not in the plan's file list but contained `# Chessalytics` heading
- **Fix:** Renamed heading to `# FlawChess`
- **Files modified:** `README.md`
- **Verification:** grep shows no remaining occurrences
- **Committed in:** `0917337` (Task 1 commit)

---

**Total deviations:** 2 auto-fixed (both Rule 2 - files found during grep verification not in the explicit plan list)
**Impact on plan:** Both fixes necessary for the "no chessalytics in tracked files" success criterion. No scope creep.

## Issues Encountered

None — grep exclusions worked as expected for `.planning/milestones/`, `.planning/quick/`, `.planning/research/`, and `.claude/settings.local.json` (filesystem path references). `.env` was intentionally left unmodified per plan instructions.

## User Setup Required

The local `.env` file still contains `chessalytics` database names. User should update manually:
```
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/flawchess
TEST_DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/flawchess_test
```
This requires renaming the PostgreSQL database or creating a new one, and re-running `uv run alembic upgrade head`.

## Next Phase Readiness

- All branding is "FlawChess" in source — ready for Phase 20 Plan 02 (GitHub repo transfer)
- apple-touch-icon.png placeholder in place — user should replace with final 180x180 design asset before launch
- No external services affected by this rename yet (Sentry/Plausible created in Phase 22/23)

## Self-Check: PASSED

- FOUND: `frontend/public/icons/apple-touch-icon.png`
- FOUND: `20-01-SUMMARY.md`
- FOUND: commit `0917337`
- FOUND: commit `922dc15`

---
*Phase: 20-rename-branding*
*Completed: 2026-03-21*
