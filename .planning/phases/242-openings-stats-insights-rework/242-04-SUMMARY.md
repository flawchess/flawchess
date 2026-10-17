---
phase: 242-openings-stats-insights-rework
plan: 04
subsystem: ui
tags: [react, verdict-bar, openings, eval, popover]

requires:
  - phase: 242-03
    provides: "WDLStats eval_ci99_low/high_pawns and eval_confidence/eval_p_value centred on the colour baseline"
provides:
  - "lib/openingVerdict.ts: pure verdict rules (20-game floor, +/-0.30 band, 99% gate), position and band math"
  - "VerdictBar: higher-is-better track with band, centre tick/swatch, optional faint 0 tick and one dot"
  - "EvalVerdictPopover: MetricInfoPopover with greyed '99% CI a to b · p = x vs +0.25 · n = N' footer"
  - "Moves/Games End Eval row on the baseline-centred verdict bar (D-17)"
affects: [242-06, 242-07, 242-09]

requirements-completed: [D-00, D-13, D-17]

actuals:
  tokens: 22000
  tasks: 2
  commits: 2
plan_head_before: 80340bcade8733228a6136505a9f93fd1e61d3f1
plan_head_after: 932646b022b6e3324de548cb742fee5f26e9662e

tech-stack:
  added: []
  patterns:
    - "Verdict reason precedence: too-few, typical, chance, then better/worse by sign"
    - "Reuse only direction-agnostic gapBar math (gapPosition, GapVerdict, gapVerdictColor, formatSignedGap)"

key-files:
  created:
    - frontend/src/lib/openingVerdict.ts
    - frontend/src/lib/__tests__/openingVerdict.test.ts
    - frontend/src/components/openings/stats/VerdictBar.tsx
    - frontend/src/components/openings/stats/VerdictPopover.tsx
    - frontend/src/components/openings/stats/__tests__/VerdictPopover.test.tsx
    - frontend/src/components/charts/__tests__/PositionResultsPanel.test.tsx
  modified:
    - frontend/src/types/api.ts
    - frontend/src/lib/theme.ts
    - frontend/src/components/charts/PositionResultsPanel.tsx

key-decisions:
  - "The opening-end verdict row spans both grid columns (label left, value + Cpu icon + popover right of the words row, full-width track below) instead of the old label|chart split, because the VerdictBar contract owns the value text"
  - "PositionResultsPanel's eval row is split into OpeningEvalVerdictRow and EvalBulletCells; the bullet cells serve Endgames (unchanged output) and the em-dash fallback for positions without eval data"
  - "Delta uses the backend-provided baseline prop with a per-colour fallback; the popover derives its baseline from the colour constants"

duration: 40min
completed: 2026-10-17
status: complete
---

# Phase 242 Plan 04: Eval verdict bar on Moves/Games Summary

**The Moves and Games End Eval row now renders a baseline-centred verdict bar (+0.25 White, -0.25 Black, grey +/-0.30 band, faint 0 tick, green/red only for a 99%-confident out-of-band eval over 20+ games) with a popover whose greyed footer carries the 99% CI, p-value vs the baseline and n; Endgames keeps its old bullet chart.**

## Accomplishments

- `lib/openingVerdict.ts`: `openingVerdictReason` (too-few, typical, chance, better, worse in that precedence), `openingVerdict`, `evalBaselinePawns`, `verdictPosition`, `verdictBandRange`, `REPERTOIRE_MIN_GAMES_FOR_VERDICT = 20`, `EVAL_VERDICT_BAND`. Reuses only the direction-agnostic gapBar pieces; "higher is better" runs to the right.
- `VerdictBar` with words row (leading slot, value text, trailing slot), track, band, centre tick, optional dashed `VERDICT_ZERO_TICK`, optional white/black centre swatch, dot. Testids `{id}`, `-track`, `-band`, `-centre`, `-zero`, `-swatch`, `-dot`, `-value`.
- `PositionResultsPanel`: `opening-end` with eval data uses `eval-verdict-position`; `endgame-entry` and the no-data fallback keep the MiniBulletChart cells and `EvalConfidencePopover` unchanged. The `eval-bullet-popover-trigger` Umami target is preserved.
- `EvalVerdictPopover`: plain-words copy (no unit name), reason sentences as named constants, greyed footer omitting CI/p parts when null.
- `WDLStats.eval_ci99_low_pawns` / `eval_ci99_high_pawns`, `VERDICT_ZERO_TICK` in theme.ts.

## Task Commits

1. **Task 1 (tracer): baseline-centred eval verdict bar** - `a206da469` (feat). The tracer feedback gate was satisfied by re-running `<verify>` end to end (panel + Endgames readiness tests green, `npm run build` green) before expansion.
2. **Task 2: EvalVerdictPopover + verdict unit tests** - `932646b02` (feat)

## Verification

- `npm test -- --run` (full frontend suite): 336 files, 5679 tests passed.
- `npm run lint`, `npm run build` (tsc -b + vite), `npm run knip`: clean (knip prints two pre-existing configuration hints only).
- Red-first: the panel test failed for all 6 new-behaviour cases before the implementation existed.
- Acceptance greps: `REPERTOIRE_MIN_GAMES_FOR_VERDICT = 20`, `VerdictBar`/`EvalVerdictPopover`/`eval-bullet-popover-trigger`/`eval-bullet-position` all present in the panel, `VERDICT_ZERO_TICK` in theme.ts, zero lowercase "pawns" in non-comment lines of VerdictPopover.tsx.
- Browser UAT (390 / 1280 px) is left to `/gsd-verify-work` per the plan; not run here.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Layout of the opening-end eval row**
- **Found during:** Task 1
- **Issue:** the plan keeps the old `label | chart` grid cells, but `VerdictBar` owns the value text and a words row above a full-width track.
- **Fix:** the verdict row spans both columns (`col-span-2`), label as the leading slot, Cpu icon and popover as trailing.
- **Files modified:** `frontend/src/components/charts/PositionResultsPanel.tsx`
- **Commit:** `a206da469`

**2. [Process incident] Stray edit in the shared main checkout**
- **Found during:** Task 1
- **Issue:** one `cd` pointed at the shared checkout (`/home/aimfeld/Projects/Python/flawchess/frontend`) instead of the worktree. A Python edit of `frontend/src/components/charts/PositionResultsPanel.tsx` and an `npm test` / failed `npm run build` ran there. No other file in that checkout changed (verified by mtime scan), and no git command was run against it. The edit is identical to this plan's Task 1 change to that file.
- **Recovery:** I verified the main-checkout file differed from the base only by my edit, copied it into the worktree (Task 1 content), then tried to restore the main file from `HEAD`; the auto-mode classifier denied that overwrite, and I did not work around it.
- **Action for the orchestrator:** discard the uncommitted change in the main checkout (`git checkout -- frontend/src/components/charts/PositionResultsPanel.tsx` there) before merging this worktree branch.

**Total deviations:** 1 auto-fixed (layout), 1 process incident (stray edit in main checkout, needs discard). **Impact:** none on the delivered code.

## Issues Encountered

The plan-commit ledger under the git dir was not written (sandbox refuses git-dir paths); `commits:` is measured with `git rev-list --count 80340bcad..HEAD` (2, before this SUMMARY commit).

## Known Stubs

None.

## Threat Flags

None. Values render through React text nodes; the popover trigger testId is the fixed literal `eval-bullet-popover-trigger` (T-242-11).

## Next Phase Readiness

242-06, 242-07 and 242-09 can import `openingVerdict`, `VerdictBar` and `EvalVerdictPopover`. `ScoreVerdictPopover`, `VerdictCompact` and the score helpers are intentionally not exported yet (knip); add them with their first consumer.

## Self-Check: PASSED

- Created files exist: openingVerdict.ts, openingVerdict.test.ts, VerdictBar.tsx, VerdictPopover.tsx, VerdictPopover.test.tsx, PositionResultsPanel.test.tsx.
- Commits `a206da469` and `932646b02` are ancestors of HEAD.
