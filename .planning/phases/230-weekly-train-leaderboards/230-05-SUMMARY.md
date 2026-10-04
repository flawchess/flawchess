---
phase: 230-weekly-train-leaderboards
plan: 05
subsystem: ui
tags: [frontend, train, leaderboard, score-screen, release-gate]

requires:
  - phase: 230-weekly-train-leaderboards (plan 02)
    provides: GET /api/train/leaderboard?session_id= with rank_without_session per board
  - phase: 230-weekly-train-leaderboards (plan 03)
    provides: useTrainLeaderboard({ sessionId }) score-screen hook variant, HIDDEN_FROM_OTHERS_LABEL, lib/trainLeaderboard.ts
  - phase: 230-weekly-train-leaderboards (plan 04)
    provides: leaderboard_hidden opt-out and the Privacy disclosure
provides:
  - "rankLineCopy / scoreRankLines / ACCURACY_NOT_ENTERED_LINE: pure score-screen rank-line copy rules (this week, up N, plain rank, guest You'd be, tentative, not-entered, hidden)"
  - "TrainScoreRankLines: compact rank lines under Points: x/y, one session-scoped request per completed session"
  - "TrainScoreScreen sessionId prop wired from Train.tsx (one prop, one element, no new branch)"
  - "CHANGELOG [Unreleased] bullet, final 230-VALIDATION.md, COVERAGE.md"
affects: [train-leaderboard, medals, phase-verification]

actuals:
  tokens: 8000
  tasks: 3
  commits: 4
plan_head_before: 7f21941332191fc5da0fdb228de017b3f1d68091
plan_head_after: 88a6de4c5e5c12566519b3443052def3e2c3462c

tech-stack:
  added: []
  patterns:
    - "All score-screen rank branching lives in the pure lib and the new component; TrainScoreScreen (complexity 13 of 15) gains no conditional"
    - "Single plain-rank path for unchanged and worse ranks: there is no 'down' branch to leak a negative delta (D-18)"
    - "Component test spies on apiClient.get with a real QueryClient; the host screen's suite stubs the component because it has no QueryClientProvider"

key-files:
  created:
    - frontend/src/components/train/TrainScoreRankLines.tsx
    - frontend/src/components/train/__tests__/TrainScoreRankLines.test.tsx
    - .planning/phases/230-weekly-train-leaderboards/COVERAGE.md
  modified:
    - frontend/src/lib/trainLeaderboard.ts
    - frontend/src/lib/__tests__/trainLeaderboard.test.ts
    - frontend/src/components/train/TrainScoreScreen.tsx
    - frontend/src/components/train/__tests__/TrainScoreScreen.test.tsx
    - frontend/src/pages/Train.tsx
    - CHANGELOG.md
    - .planning/phases/230-weekly-train-leaderboards/230-VALIDATION.md

key-decisions:
  - "Guest rule is checked first in rankLineCopy so a guest never sees a delta even when the server sends rank_without_session"
  - "The tentative suffix is gated on kind === 'accuracy', so a stray tentative flag on a Points viewer cannot leak onto the Points line"
  - "scoreRankLines emits the not-entered Accuracy line only when a Points viewer exists; with no Points viewer the list is empty"
  - "No second sign-up CTA: the component renders no buttons, the score bubble's existing guest ask carries it (D-17)"

patterns-established:
  - "Prop pass-through for server state: sessionId flows Train.tsx -> TrainScoreScreen -> TrainScoreRankLines -> hook, with SolveResponse left untouched"

requirements-completed: [D-11, D-12, D-17, D-18, D-19]

coverage:
  - id: D1
    description: "The score screen shows 'Points board: #N (up M)' under Points: x/y, from GET /train/leaderboard?session_id=<this session>, with '#N this week' on a first entry and the plain rank when unchanged"
    requirement: "D-11"
    verification:
      - kind: unit
        ref: "frontend/src/components/train/__tests__/TrainScoreRankLines.test.tsx#asks the server for this session and renders \"#N (up M)\""
        status: pass
      - kind: unit
        ref: "frontend/src/components/train/__tests__/TrainScoreScreen.test.tsx#renders the rank lines right under the Points line, carrying the session id"
        status: pass
      - kind: unit
        ref: "frontend/src/lib/__tests__/trainLeaderboard.test.ts#rankLineCopy, public viewers (D-11, D-12)"
        status: pass
    human_judgment: false
  - id: D2
    description: "An Accuracy rank that is unchanged or worse shows the plain rank; no string ever says 'down' (D-18)"
    requirement: "D-18"
    verification:
      - kind: unit
        ref: "frontend/src/lib/__tests__/trainLeaderboard.test.ts#a worse Accuracy rank after the session shows the plain rank and never \"down\" (D-18)"
        status: pass
      - kind: unit
        ref: "frontend/src/components/train/__tests__/TrainScoreRankLines.test.tsx#a worse Accuracy rank shows the plain rank, never a down delta (D-18)"
        status: pass
    human_judgment: false
  - id: D3
    description: "A guest reads 'Points board: You'd be #N' with no delta and no button in the rank lines"
    requirement: "D-17"
    verification:
      - kind: unit
        ref: "frontend/src/components/train/__tests__/TrainScoreRankLines.test.tsx#a guest reads \"You'd be #N\" and the lines hold no button (D-17)"
        status: pass
    human_judgment: false
  - id: D4
    description: "A viewer with Points but no Accuracy entry gets the specific not-on-this-board line, a tentative Accuracy viewer gets '(tentative)', a hidden viewer gets 'Hidden from others', a failed request gets the LoadError sentence"
    requirement: "D-19"
    verification:
      - kind: unit
        ref: "frontend/src/components/train/__tests__/TrainScoreRankLines.test.tsx#a viewer with Points but no Accuracy entry gets the not-entered line (D-19)"
        status: pass
      - kind: unit
        ref: "frontend/src/components/train/__tests__/TrainScoreRankLines.test.tsx#a failed request shows the exact LoadError sentence"
        status: pass
    human_judgment: false
  - id: D5
    description: "The phase passes the full CLAUDE.md pre-merge gate and the serial leaderboard run; CHANGELOG, VALIDATION.md and COVERAGE.md are final"
    verification:
      - kind: other
        ref: "uv run ruff format/check, ty (app + analysis), check_function_size, uv run pytest -n auto -x (5071 passed), frontend lint/build/npm test (4892 passed)/knip, serial leaderboard run (188 passed)"
        status: pass
    human_judgment: false
  - id: D6
    description: "Browser UAT legs 1-7 (landing card at desktop and 375 px, tab persistence, score screen lines, dev-clock week rollover, opt-out across two profiles, guest flow, /privacy line)"
    verification: []
    human_judgment: true
    rationale: "Visual fit at phone width and the multi-account, multi-screen flow are not covered by unit tests; run by the orchestrator after this executor returns (passed 2026-10-04, see Browser UAT)"

duration: 6min
completed: 2026-10-04
status: complete
---

# Phase 230 Plan 05: Score-Screen Rank Lines and Phase Gate Summary

**Score screen shows one server-computed rank line per board under "Points: x/y" (up N, first-of-week, guest hypothetical, tentative, hidden, not-entered), and the phase passes the full pre-merge gate.**

## Performance

- **Duration:** about 6 min
- **Tasks:** 3 (browser UAT leg of Task 3 handed to the orchestrator)
- **Files modified:** 11 (3 created, 8 modified, counting docs)

## Accomplishments

- `rankLineCopy` / `scoreRankLines` in `lib/trainLeaderboard.ts` carry every copy rule from D-11, D-12, D-17, D-18 and D-19, with the "(up N)" rule firing only when `rank_without_session > rank`.
- `TrainScoreRankLines` calls `useTrainLeaderboard({ sessionId })` (one request when the score screen mounts), renders one `p` per line, reserves `min-h-10` so the layout does not jump, and shows `LoadError` on failure.
- `TrainScoreScreen` gained exactly one prop, one destructure and one JSX element; `Train.tsx` passes `trainSession.session.session_id`. No new branch landed in the component at complexity 13 of 15.
- Full pre-merge gate green; CHANGELOG `[Unreleased]` carries the user-facing leaderboard bullet; 230-VALIDATION.md rows are all green with `nyquist_compliant: true` and `wave_0_complete: true`; COVERAGE.md records no external API.

## Task Commits

1. **Task 1 (tracer): rank line end to end** - `0514fdf47` (feat)
2. **Task 2 RED: failing variant tests** - `2e7efaa54` (test)
3. **Task 2 GREEN: guest, tentative, not-entered, hidden, error variants** - `c4ad68e70` (feat)
4. **Task 3: changelog, validation, coverage** - `88a6de4c5` (docs)

## TDD Gate Compliance

Task 2 followed RED then GREEN with no REFACTOR commit.
- RED (`2e7efaa54`): 11 target assertions failed on behavior (6 in the lib suite, 5 in the component suite: guest, tentative, tentative+up, guest+tentative, not-entered, hidden, error). The D-18 worse-rank test and the plain-rank/qualified cases already held, as the Task 1 single plain-rank path already satisfied them.
- GREEN (`c4ad68e70`): all 63 lib and component tests pass.
- D-18 mutation check: temporarily changing the improvement test from `before > viewer.rank` to `before !== viewer.rank` turned two tests red (lib "a worse Accuracy rank after the session shows the plain rank and never down" and component "a worse Accuracy rank shows the plain rank, never a down delta"), both with `expected 'Accuracy: #5 (up -2)' to be 'Accuracy: #5'`. The original was restored and the suites re-run green (63 passed).

## Pre-merge Gate Transcript

| Step | Result |
|------|--------|
| `uv run ruff format app/ tests/ scripts/ analysis/` | 506 files left unchanged |
| `uv run ruff check . --fix` | All checks passed |
| `uv run ty check app/ tests/ scripts/` | All checks passed |
| `uv run --project analysis --with ty ty check analysis/` | All checks passed |
| `scripts/check_function_size.py app/ --fail-over-depth 4` | OK: 1095 functions scanned, no breaches |
| `uv run pytest -n auto -x -q` | 5071 passed, 19 skipped |
| Serial leaderboard run (test_train_leaderboard router/repo/service, score parity, users router, train router) | 188 passed |
| `npm run lint` / `npm run build` | clean / exit 0 |
| `npm test -- --run` | 4892 passed |
| `npm run knip` | no unused items (one pre-existing configuration hint about .css) |

No gate step modified any file, so no style/chore commit was needed.

## Browser UAT

Run by the orchestrator with claude-in-chrome on 2026-10-04 against the running dev stack (phase branch checked out, migration `c4e7a91d2b58` applied). All 7 legs passed, so no `230-UAT.md` was written. Screenshots are in gitignored `temp/230-uat/`.

| Leg | Result | Evidence |
|-----|--------|----------|
| 1 Landing card at 1280 px and 375 px | PASS | Same-origin iframe probe: order streak card, leaderboard card, stats card; no row or document overflow at either width (rows 294 px / 638 px, scrollWidth = clientWidth); viewer row `bg-muted font-semibold`; name span `truncate`; countdown "ends in 20h 59m" |
| 2 Accuracy tab survives reload | PASS | `flawchess_train_leaderboard_tab=accuracy`, tab still `on` after reload, helper line shown |
| 3 Session then Done | PASS | Real 3-puzzle session: "Points board: #1" (no change, so no "up"), "Accuracy: #1 (tentative)"; after Done the card showed 17 pts / 9 puzzles (was 13 / 6) without reload |
| 4 Dev clock to next Monday | PASS | +1d to Mon Oct 5: "ends in 6d 20h", Accuracy "No accuracy entries yet this week.", Points shows only the other dev user's future-dated solves plus "Solve a puzzle to enter this week's board."; clock reset afterwards |
| 5 Hide me from leaderboards | PASS | Switch on: profile `leaderboard_hidden=true`, own row "Hidden from others"; a guest on the 127.0.0.1 origin saw only user 44; switch off: user 28 back at #1 for the guest. Owner setting restored to off |
| 6 Guest flow | PASS | Guest warm-up session: "Points board: You'd be #3", "Accuracy: You'd be #1 (tentative)", no button inside the rank lines; landing card "You (guest)", "Sign up to claim your spot", "What changes?" and "Sign up free" |
| 7 /privacy | PASS | New leaderboard disclosure line and "Last updated: October 2026" |

Minor observation (not a leg failure): at phone width the " (tentative)" suffix sits inside the truncating name span, so even a short name reads "aimfeld (t…" on the Accuracy board.

## Deviations from Plan

None - plan executed exactly as written. The error branch and the not-entered/hidden rules were deliberately deferred from Task 1 to Task 2 as the plan scoped them.

## Known Stubs

None.

## Threat Flags

None. The only new surface is the existing endpoint called with the caller's own session id (T-230-15, mitigated server-side in Plan 02).

## Issues Encountered

None.

## Self-Check: PASSED

- Created files exist: TrainScoreRankLines.tsx, TrainScoreRankLines.test.tsx, COVERAGE.md.
- Commits found: 0514fdf47, 2e7efaa54, c4ad68e70, 88a6de4c5.
- Acceptance greps: `<TrainScoreRankLines sessionId={sessionId} />` 1, `sessionId={trainSession.session.session_id}` 1, `useTrainLeaderboard({ sessionId })` 1, `(down` 0, `You'd be #` 1, `<Button` 0; the TrainScoreScreen diff adds one import, one prop, one destructure and one element, with no `?`, `&&` or `if (`.
