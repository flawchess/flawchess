---
task: 260616-ey1
status: complete
commits:
  - 80d0f467 feat(260616-ey1): open QUEUE-08 guest gate for tier-1 eval only
  - 2a286cc1 feat(260616-ey1): show Analyze button to guests; update coverage CTA
  - 3b04fe1b test(260616-ey1): flip guest tier-1 assertions; add guest router test
  - cfa0f2dd chore(260616-ey1): CHANGELOG + update NoAnalysisState test for guest analyze
gate:
  ruff_format: pass (246 files already formatted)
  ruff_check: pass (all checks passed)
  ty: pass (zero errors)
  pytest: pass (2707 passed, 10 skipped, 3 warnings)
  frontend_lint: pass (ESLint clean)
  frontend_tests: pass (951 passed across 84 files)
  knip: pass (no dead exports)
deviations: none
---

# Summary: 260616-ey1 — Allow guests to analyze a single game

## What was done

Opened the QUEUE-08 guest gate for tier-1 (explicit, on-demand) Stockfish eval only. Guests can
now click "Analyze" on a game card to enqueue it for engine analysis, while automatic tier-3
background analysis of all games remains a signup benefit.

### Task 1: Backend (3 files)

- **app/routers/imports.py** `enqueue_tier1`: removed the `if user.is_guest: return skipped_guest`
  early-return so guests pass through to `enqueue_tier1_game`. IDOR ownership guard unchanged.
- **app/services/eval_queue_service.py** `enqueue_tier1_game`: changed guard from
  `if is_guest is None or is_guest:` to `if is_guest is None:` — only a missing user row returns
  False; guests can enqueue.
- **app/services/eval_queue_service.py** `_claim_queued_job`: changed `AND u.is_guest = false`
  to `AND (u.is_guest = false OR ej.tier = 1)` so workers drain guest tier-1 jobs.
- **app/services/eval_queue_service.py** `_claim_tier3_derived`: both `u.is_guest = false`
  filters left **unchanged**; added inline comments marking them intentionally preserved.
- **app/routers/admin.py** `admin_enqueue_tier1`: simplified status logic — no more is_guest
  lookup or `skipped_guest` branch (enqueue_tier1_game no longer returns False for guests).

### Task 2: Frontend (4 files)

- **NoAnalysisState.tsx**: removed `isGuest` prop, guest sign-up CTA branch, and now-unused
  `useNavigate` / `react-router-dom` imports.
- **LibraryGameCard.tsx**: removed `isGuest={isGuest}` from both NoAnalysisState call sites
  (desktop + mobile); removed unused `useUserProfile` import and `isGuest` constant.
- **EvalCoverageBadge.tsx**: updated button text from "Sign up to analyze" to
  "Sign up to analyze all games"; updated comment to reflect guests can now do one game at a time.
- **analysisCoverageCopy.tsx**: tightened popover copy to convey that signup unlocks automatic
  background analysis of all games (no per-game clicking).

### Task 3: Tests (2 files)

- **tests/services/test_eval_queue.py** `TestGuestExclusion.test_guest_exclusion`: flipped tier-1
  assertion from False→True; added eval_jobs row existence check; added `_claim_queued_job` drain
  check confirming the `OR ej.tier = 1` path works. Tier-3 exclusion check and
  `test_tier3_guest_excluded_from_lottery` remain unchanged and still pass.
- **tests/routers/test_imports_tier1_enqueue.py**: updated file docstring; added `_create_guest`
  helper and `guest_client` fixture; added `test_tier1_guest` asserting 200 "enqueued" for guest's
  own game and 404 for another user's game (IDOR guard).

### Task 4: CHANGELOG + test file cleanup

- **CHANGELOG.md**: added bullet under `[Unreleased] ### Changed`.
- **NoAnalysisState.test.tsx**: removed 2 obsolete guest sign-up CTA tests; dropped `isGuest`
  prop from all remaining render calls. All 951 frontend tests pass.

## Gate results

| Gate | Result |
|------|--------|
| `ruff format --check` | PASS — 246 files already formatted |
| `ruff check` | PASS — all checks passed |
| `ty check` | PASS — zero errors |
| `pytest -n auto -x` | PASS — 2707 passed, 10 skipped, 3 warnings |
| `npm run lint` | PASS — ESLint clean |
| `npm test -- --run` | PASS — 951 passed across 84 files |
| `npm run knip` | PASS — no dead exports |

## Security

- T-ey1-01 (IDOR): IDOR guard unchanged — guest POSTing to another user's game still 404s.
- T-ey1-02 (tier-3 bulk drain): both `_claim_tier3_derived` guest filters preserved with comments.
- T-ey1-03 (DoS via spam): idempotent ON CONFLICT DO NOTHING on the active-job partial unique
  index caps a guest to one active job per game (existing behavior, unchanged).
