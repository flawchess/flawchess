---
phase: 85-section-1-games-with-vs-without-endgame-cards
plan: 04
subsystem: ui
tags: [react, endgames, refactor, knip, integration]

# Dependency graph
requires:
  - phase: 85
    plan: 01
    provides: "non_endgame_score_p_value on EndgamePerformanceResponse so the new section's two card-level sig gates share identical Wilson semantics"
  - phase: 85
    plan: 02
    provides: "EndgameScoreOverTimeChart extracted into its own file; legacy section file reduced to the section function + SCORE_GAP_DOMAIN, ready for deletion"
  - phase: 85
    plan: 03
    provides: "EndgameGamesWithWithoutSection component (+ tests) waiting to be mounted"
provides:
  - "Endgames page Section 1 swapped from the legacy WDL table to the new twin-tile cards layout"
  - "Legacy EndgamePerformanceSection.tsx deleted entirely (the section function was its only export after Plan 02)"
  - "Test file renamed: EndgamePerformanceSection.test.tsx → EndgameScoreOverTimeChart.test.tsx (the deferred-rename from Plan 02)"
  - "Endgames.startVsEnd page test updated to assert against the new section's testids (endgame-games-with-without-section, tile-games-without-endgame, tile-games-with-endgame) and to populate the new non_endgame_score_p_value fixture field"
affects: [endgames, section-1, phase-86]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Per-card tile shells live inside EndgameGamesWithWithoutSection; the page mount drops its outer charcoal-texture wrapper to avoid visual double-nesting"
    - "scoreGapData is the gating condition for mounting Section 1 (the new component takes it as a non-optional prop per D-10)"

key-files:
  created:
    - .planning/milestones/v1.17-phases/85-section-1-games-with-vs-without-endgame-cards/deferred-items.md
  modified:
    - frontend/src/pages/Endgames.tsx
    - frontend/src/pages/__tests__/Endgames.startVsEnd.test.tsx
  deleted:
    - frontend/src/components/charts/EndgamePerformanceSection.tsx
  renamed:
    - "frontend/src/components/charts/__tests__/EndgamePerformanceSection.test.tsx → EndgameScoreOverTimeChart.test.tsx"

key-decisions:
  - "Delete the legacy section file entirely. After Plan 02's chart extract its only remaining export was EndgamePerformanceSection itself; SCORE_GAP_DOMAIN was already re-declared locally inside EndgameGamesWithWithoutSection.tsx (Plan 03), so nothing outside the deleted function consumed any symbol from the file."
  - "Rename the chart test file. Every test inside EndgamePerformanceSection.test.tsx targets EndgameScoreOverTimeChart (Plan 02 left the rename for this plan)."
  - "Gate the Section 1 mount on scoreGapData being defined. The new component requires scoreGap as a non-optional prop while the existing scope around the chart already conditions on scoreGapData; gating mirrors the sibling chart block and satisfies TypeScript narrowing without a type-cast."
  - "Defer the repo-wide ruff format gate. uv run ruff format --check . reports 93 files would be reformatted, all untouched by this phase. Logged to deferred-items.md per the SCOPE BOUNDARY rule."

patterns-established:
  - "Plan-04-style cleanup: when a wave-3 mount swap leaves a legacy file with no live consumers, delete the file in the same plan rather than leaving an orphan for a future chore."

requirements-completed: [SEC1-01, SEC1-07]

# Metrics
duration: 7min
completed: 2026-05-13
---

# Phase 85 Plan 04: Mount EndgameGamesWithWithoutSection + delete legacy section Summary

**Endgames page now renders the new "Games with vs without Endgame" twin-tile cards instead of the legacy WDL table; the legacy EndgamePerformanceSection.tsx file is deleted and the chart test file is renamed to match the surviving component.**

## Performance

- **Duration:** ~7 min
- **Started:** 2026-05-13T17:18:00Z
- **Completed:** 2026-05-13T17:24:30Z
- **Tasks:** 2 auto + 1 checkpoint (deferred to orchestrator for human UAT)
- **Files modified:** 2 (Endgames.tsx, Endgames.startVsEnd.test.tsx)
- **Files deleted:** 1 (EndgamePerformanceSection.tsx)
- **Files renamed:** 1 (test file rename)

## Accomplishments
- New Section 1 mount: `<EndgameGamesWithWithoutSection data={perfData} scoreGap={scoreGapData} />` lives where the legacy `<EndgamePerformanceSection>` used to sit, gated by `scoreGapData` so the non-optional `scoreGap` prop is satisfied.
- Legacy `EndgamePerformanceSection.tsx` removed entirely (file deletion).
- Test rename completed: `EndgamePerformanceSection.test.tsx` → `EndgameScoreOverTimeChart.test.tsx` (all tests inside target the extracted chart).
- Page-level test (`Endgames.startVsEnd.test.tsx`) updated to assert against the new section + tile testids and to populate the new `non_endgame_score_p_value` fixture field.
- Verification gates that ran green: frontend `lint`, `tsc --noEmit`, `vitest run` (363 tests / 31 files), `knip`, `build`; backend `ruff check`, `ty check`, `pytest -x` (1402 passed, 6 skipped).

## Task Commits

1. **Task 1: Mount EndgameGamesWithWithoutSection in Endgames.tsx and remove legacy import** — `00dce512` (feat)
2. **Task 2: Delete the legacy EndgamePerformanceSection function and rename the chart test file** — `ec39fae6` (refactor)
3. **Task 3 (checkpoint:human-verify)**: deferred to the orchestrator. The "work without stopping" directive in the orchestrator prompt and the `autonomous: false` instruction combined to: execute end-to-end, surface only genuine ambiguities. The human UAT steps in the plan are reproduced verbatim in this summary's "Outstanding" section.

**Plan metadata:** `9a5ecde5` (docs: deferred-items.md). The orchestrator owns the STATE.md / ROADMAP.md final-commit.

## Files Created/Modified
- `frontend/src/pages/Endgames.tsx` — replaced the `EndgamePerformanceSection` import + JSX mount with `EndgameGamesWithWithoutSection`; gated on `scoreGapData`; dropped the outer charcoal-texture wrapper (the new section provides its own per-card tile shells).
- `frontend/src/pages/__tests__/Endgames.startVsEnd.test.tsx` — updated to assert against `endgame-games-with-without-section`, `tile-games-without-endgame`, `tile-games-with-endgame`, plus the surviving `score-gap-difference` and `endgame-score-timeline-chart` testids. Added `non_endgame_score_p_value: 0.001` to `buildPerf()` so the type matches.
- `frontend/src/components/charts/EndgamePerformanceSection.tsx` — **deleted** (entire file).
- `frontend/src/components/charts/__tests__/EndgamePerformanceSection.test.tsx` → `EndgameScoreOverTimeChart.test.tsx` — **renamed** (no content changes; all tests already targeted the chart after Plan 02).
- `.planning/milestones/v1.17-phases/85-section-1-games-with-vs-without-endgame-cards/deferred-items.md` — created to log the pre-existing ruff format drift.

## Decisions Made
- Deleted the legacy file entirely rather than trimming. The file's only remaining export was the function being replaced; `SCORE_GAP_DOMAIN` was already re-declared locally in Plan 03.
- Renamed (not deleted) the chart test file. Plan 02 deferred the rename; deleting would have lost ten coverage cases for `EndgameScoreOverTimeChart`.
- Logged ruff format drift instead of reformatting 93 unrelated files (per SCOPE BOUNDARY).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Added missing `non_endgame_score_p_value` to test fixture**
- **Found during:** Task 1 verification (`npx tsc --noEmit` after the page test was updated)
- **Issue:** Plan 01 added `non_endgame_score_p_value: number | null` to `EndgamePerformanceResponse`, but the page-level test fixture `buildPerf()` in `Endgames.startVsEnd.test.tsx` was never updated; the new section consumes this field, so the test would have failed TypeScript narrowing once the new section was mounted.
- **Fix:** Added `non_endgame_score_p_value: 0.001` next to the existing `endgame_score_p_value` in the fixture.
- **Files modified:** `frontend/src/pages/__tests__/Endgames.startVsEnd.test.tsx`
- **Verification:** `npx tsc --noEmit` exits 0; `npm test -- --run` exits 0 with 363 tests.
- **Committed in:** `ec39fae6` (Task 2 commit — grouped with the test rename since both target the same file)

**2. [Rule 3 - Out-of-scope] Logged repo-wide ruff format drift**
- **Found during:** Task 2 verification (`uv run ruff format --check .`)
- **Issue:** 93 untouched files (e.g. `tests/test_users_router.py`, `tests/test_stats_service.py`) would be reformatted. None belong to phase 85; the drift reproduces against `main` at `/home/aimfeld/Projects/Python/flawchess`. Plan 04's acceptance list included `ruff format --check .` as a gate.
- **Fix:** Did NOT auto-reformat. Per SCOPE BOUNDARY (only auto-fix issues directly caused by this plan), logged the gap to `deferred-items.md` and recommended a follow-up `/gsd-quick` chore PR.
- **Files modified:** `.planning/milestones/v1.17-phases/85-section-1-games-with-vs-without-endgame-cards/deferred-items.md` (new)
- **Verification:** `uv run ruff check .` exits 0; `uv run ty check app/ tests/` exits 0; `uv run pytest -x` exits 0 (1402 passed, 6 skipped).
- **Committed in:** `9a5ecde5`

---

**Total deviations:** 2 (1 bug auto-fix, 1 out-of-scope log)
**Impact on plan:** The bug fix was necessary for type safety after Plan 01 widened the schema. The format-drift log surfaces an inherited issue without expanding scope.

## Issues Encountered
- `npm ci` was needed at the start; the worktree was spawned without `node_modules`. Ran once and continued.
- The deletion test for `EndgamePerformanceSection.test.tsx` was tempted by the plan ("delete the section test file"), but reading the file showed all ten cases target `EndgameScoreOverTimeChart` — the plan's escape hatch ("if any test inside actually tested EndgameScoreOverTimeChart … move them") applied verbatim, so the test was renamed instead of deleted.

## User Setup Required
None.

## Outstanding (deferred to orchestrator)

**Task 3 — checkpoint:human-verify (visual UAT).** Steps (verbatim from the plan):
1. Start the dev environment: `bin/run_local.sh` (or `docker compose -f docker-compose.dev.yml -p flawchess-dev up -d` + `uv run uvicorn app.main:app --reload` + `cd frontend && npm run dev`).
2. Visit `http://localhost:5173/endgames` — log in or use guest mode with imported games.
3. Above the "Endgame Start vs End" twin-tile section, confirm:
   - A section h3 `Games with vs without Endgame` with an info icon to its right (hover, legacy two-paragraph popover renders).
   - A sub-tagline `Do you perform better or worse when games reach an endgame?`
   - Two cards on a wide viewport: LEFT = `Games without Endgame`, RIGHT = `Games with Endgame`. Resize to ≤ 1024px width, cards stack vertically with `Games without Endgame` on top.
   - Each card shows a WDL bar + a `Score: NN%` row with the bullet to its right. Hover the score's info icon, popover explains the 0.50 natural anchor.
   - Below the two cards, a full-width tile titled `Score Gap (Yes − No)` with a signed `+N%` or `-N%` label and a bullet anchored at 0.
4. Sig gating spot-check: pick a card where the WDL is clearly lopsided (e.g., score 70%+ over many games). The score percentage should be tinted green (or red if below the band). Pick a card where score is near 50% (or n < 10), value should be the default text color, not zone-tinted.
5. Em-dash audit: skim the section header popover and the per-card score popover, confirm at most one em-dash per paragraph (CLAUDE.md style rule).
6. Confirm the legacy table is gone (no `Endgame | Games | Win/Draw/Loss | Score | Score Gap` table headers anywhere on the page).

## Next Phase Readiness
- Section 1 is now live in the codebase; once the orchestrator's human UAT signs off, the phase is mergeable.
- Pre-existing repo-wide ruff format drift is a chore-PR candidate. Suggested command: `uv run ruff format .` repo-wide followed by a single `chore: ruff format` commit.

## Self-Check: PASSED

- `grep -c "EndgameGamesWithWithoutSection" frontend/src/pages/Endgames.tsx` → 2 (import + mount)
- `grep -c "EndgamePerformanceSection" frontend/src/pages/Endgames.tsx` → 0
- `[ ! -f frontend/src/components/charts/EndgamePerformanceSection.tsx ]` → true (file deleted)
- `[ -f frontend/src/components/charts/__tests__/EndgameScoreOverTimeChart.test.tsx ]` → true
- `git log --oneline | grep -E "00dce512|ec39fae6|9a5ecde5"` → all three commits present
- Frontend gate (`lint`, `tsc --noEmit`, `vitest run`, `knip`, `build`) all exit 0
- Backend gate (`ruff check`, `ty check`, `pytest -x`) all exit 0; `ruff format --check .` drift documented in deferred-items.md

---
*Phase: 85-section-1-games-with-vs-without-endgame-cards*
*Completed: 2026-05-13*
