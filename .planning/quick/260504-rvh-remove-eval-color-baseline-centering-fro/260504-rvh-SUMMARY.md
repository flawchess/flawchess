---
phase: 260504-rvh
plan: 01
type: execute
wave: 1
status: complete
completed_at: 2026-05-04
duration_minutes: ~25
tags:
  - frontend
  - backend
  - opening-stats
  - eval-confidence
  - mg-entry
  - bullet-chart
  - tooltip
dependency_graph:
  requires:
    - quick task 260504-my2 (introduced the per-color baseline centering being removed)
  provides:
    - MG-entry eval z-test runs against H0: mean == 0 cp regardless of color
    - bullet chart anchored on 0 cp with optional reference tick at the per-color baseline
    - simpler frontend zone helper (evalZoneColor takes only `value`)
  affects:
    - stats API contract (eval_baseline_pawns_white/_black semantics shift from "chart center" to "tick position")
    - any future UI that consumes MostPlayedOpeningsResponse must treat baselines as display annotation, not test reference
tech-stack:
  added: []
  patterns:
    - "Visual baselines decoupled from statistical H0 (display tick != test reference)"
key-files:
  created: []
  modified:
    - app/services/eval_confidence.py
    - app/services/opening_insights_constants.py
    - app/services/stats_service.py
    - app/schemas/stats.py
    - tests/services/test_eval_confidence.py
    - frontend/src/lib/openingStatsZones.ts
    - frontend/src/lib/__tests__/openingStatsZones.test.ts
    - frontend/src/components/charts/MiniBulletChart.tsx
    - frontend/src/components/charts/__tests__/MiniBulletChart.test.tsx
    - frontend/src/components/insights/EvalConfidenceTooltip.tsx
    - frontend/src/components/insights/BulletConfidencePopover.tsx
    - frontend/src/components/stats/MostPlayedOpeningsTable.tsx
    - frontend/src/components/stats/__tests__/MostPlayedOpeningsTable.test.tsx
    - frontend/src/pages/Openings.tsx
decisions:
  - "Keep `baseline_cp: float = 0.0` parameter on compute_eval_confidence_bucket for arithmetic generality (no production caller passes a non-zero value)"
  - "Drop the `centerPawns` prop from EvalConfidenceTooltip / BulletConfidencePopover entirely (no fallback to 0)"
  - "Render reference tick as a thin dashed line via inline `border-dashed` style rather than a new tailwind class, keeps diff minimal"
  - "Drop the unused `user_color` parameter from rows_to_openings closure now that baseline is decoupled (no caller depended on the parameter externally)"
metrics:
  total_commits: 2
  total_files_changed: 14
  total_insertions: 240
  total_deletions: 242
---

# Quick Task 260504-rvh: Remove Eval Color Baseline Centering Summary

**One-liner:** Decoupled the MG-entry bullet chart's visual center (now 0 cp) from the per-color engine baseline, which becomes a small dashed reference tick; the backend z-test now answers "is the mean different from 0 cp?" regardless of cell color.

## Goal

Roll back the per-color baseline centering introduced by quick task 260504-my2: zones, chart center, and z-test H0 should all anchor on 0 cp (engine-balanced). The per-color engine asymmetry (white +0.315 / black -0.189 pawns from the 2026-05-04 Lichess benchmark) still matters as a "what's typical for your color" annotation, so it's surfaced as a tick on the bullet chart instead of disappearing entirely.

## Implementation

### Task 1: Backend (commit 16ea9ca)

- `eval_confidence.py`: Module + function docstrings rewritten to drop EVAL_BASELINE_CP_* / Stockfish-asymmetry framing. The `baseline_cp: float = 0.0` parameter is retained for arithmetic generality, but the docstring explicitly notes no production caller passes a non-zero value.
- `opening_insights_constants.py`: Removed `EVAL_BASELINE_CP_WHITE` / `_BLACK` (centipawn H0 references). Replaced with `EVAL_BASELINE_PAWNS_WHITE = 0.315` / `_BLACK = -0.189` (display-only tick positions).
- `stats_service.py`: Dropped `_baseline_cp_for_color` helper. Both `compute_eval_confidence_bucket` call sites (`rows_to_openings` and `_phase80_item_from_metrics`) now omit `baseline_cp`. Response builder uses the new pawn constants directly. Dropped the now-unused `user_color` parameter from the inner `rows_to_openings` closure and from `_phase80_item_from_metrics`.
- `app/schemas/stats.py`: Comment on `eval_baseline_pawns_white/_black` updated to reflect the new "tick-mark position" semantics.
- `tests/services/test_eval_confidence.py`: Dropped the four baseline_cp-dependent tests. Added `test_baseline_cp_default_equals_explicit_zero` (locks the parameter default) and `test_mean_at_white_engine_baseline_reads_significant` (locks the intended semantic shift: a mean equal to the white engine baseline now reports "high" / p < 0.001 instead of being neutralized).

### Task 2: Frontend (commit e1e55bb)

- `openingStatsZones.ts`: `evalZoneColor` signature simplified to `(value: number) => string`; thresholds compare value directly to ±0.30. `buildMgEvalHeaderTooltip()` rewritten without em-dashes, drops the `evalBaselinePawns` parameter (callers no longer interpolate the active baseline). `EVAL_BASELINE_PAWNS_WHITE` / `_BLACK` retained as fallback tick positions for sections without a per-API baseline.
- `MiniBulletChart.tsx`: New optional `tickPawns?: number` prop. When provided AND inside the visible axis, renders a thin dashed reference line at that absolute position (distinct from the solid 0 cp center). `data-testid="mini-bullet-tick"` for testability. Backwards-compatible.
- `EvalConfidenceTooltip.tsx`: Dropped `centerPawns` prop and the "Centered (vs X baseline): ..." line. Tooltip now shows raw mean and CI in pawns plus the standard p-value / verdict / N row. Footer changed from "vs baseline" to "vs 0 cp".
- `BulletConfidencePopover.tsx`: Dropped `centerPawns` prop and its plumbing.
- `MostPlayedOpeningsTable.tsx`: `MiniBulletChart` callsite passes `tickPawns={evalBaselinePawns}` instead of `center={evalBaselinePawns}`. `BulletConfidencePopover` callsite drops `centerPawns`. `evalZoneColor` calls drop the second argument. `buildMgEvalHeaderTooltip()` called without arg.
- `Openings.tsx` (mobile section, lines ~185–223): Same edits applied to the mobile MG-line markup per CLAUDE.md "Always apply changes to mobile too" rule.
- Tests: `openingStatsZones.test.ts` drops the `baseline-centered` describe block, adds a `zero-centered (260504-rvh)` block with success/danger/neutral cases plus two cases asserting how the white +0.315 and black -0.189 baselines now classify under the zero-anchored rule (white reads as success, black as neutral). `MiniBulletChart.test.tsx` adds a `tickPawns prop (260504-rvh)` describe with five cases (omitted, expected positions for white and black baselines, axis-overshoot suppression). `MostPlayedOpeningsTable.test.tsx`: zone tests rewritten around the zero anchor; tooltip-text tests rewritten to match the new copy.

## Verification

All gates green:

- `uv run ruff check .`: clean
- `uv run ruff format --check` (on the 5 changed backend files): clean
- `uv run ty check app/ tests/`: zero errors
- `uv run pytest -x`: 1236 passed, 6 skipped
- `cd frontend && npm run lint`: clean
- `cd frontend && npm test -- --run`: 275 passed
- `cd frontend && npm run knip`: clean
- `cd frontend && npm run build`: success

Cross-stack search confirms zero residual references:

- `grep -rn "EVAL_BASELINE_CP\|_baseline_cp_for_color" app tests` → no hits in production code; only the intentional default-equivalence test references `baseline_cp=0.0` in test_eval_confidence.py
- `grep -rn "centerPawns" frontend/src` → no hits
- `evalBaselinePawns` only flows into `tickPawns` (MostPlayedOpeningsTable.tsx:97, Openings.tsx:197); the variable name persists because it matches the API field name

## API Contract

`MostPlayedOpeningsResponse.eval_baseline_pawns_white` / `_black` are unchanged in shape and still emit +0.315 / -0.189 pawns by default. The semantic shift (chart center → tick position) is purely on the frontend rendering side.

## Deviations from Plan

None for the most part. One minor tightening:

- **Inner closure cleanup:** the plan said to leave the `rows_to_openings` closure signature alone, but with `_baseline_cp_for_color` gone the `user_color` parameter is unused. Dropped it from both `rows_to_openings` and `_phase80_item_from_metrics` for consistency with ty's unused-parameter detection. The two callers (white and black sections of `get_most_played_openings`, and the bookmark service) update accordingly. Net effect is one fewer noisy parameter — the visual color signaling now lives entirely on the frontend.

A pre-existing unrelated formatter drift was discovered in the working tree (running `uv run ruff format .` would have reformatted ~91 unrelated files like alembic migrations and routers). I reverted those reformat-only changes to keep the diff focused on this task. This is out-of-scope tech debt that any future ruff format pass on `main` would surface.

## Authentication Gates

None.

## Self-Check

- Files exist:
  - `app/services/eval_confidence.py`: FOUND
  - `app/services/opening_insights_constants.py`: FOUND
  - `app/services/stats_service.py`: FOUND
  - `app/schemas/stats.py`: FOUND
  - `tests/services/test_eval_confidence.py`: FOUND
  - `frontend/src/lib/openingStatsZones.ts`: FOUND
  - `frontend/src/lib/__tests__/openingStatsZones.test.ts`: FOUND
  - `frontend/src/components/charts/MiniBulletChart.tsx`: FOUND
  - `frontend/src/components/charts/__tests__/MiniBulletChart.test.tsx`: FOUND
  - `frontend/src/components/insights/EvalConfidenceTooltip.tsx`: FOUND
  - `frontend/src/components/insights/BulletConfidencePopover.tsx`: FOUND
  - `frontend/src/components/stats/MostPlayedOpeningsTable.tsx`: FOUND
  - `frontend/src/components/stats/__tests__/MostPlayedOpeningsTable.test.tsx`: FOUND
  - `frontend/src/pages/Openings.tsx`: FOUND
- Commits exist:
  - `16ea9ca`: FOUND (Task 1 backend)
  - `e1e55bb`: FOUND (Task 2 frontend)

## Self-Check: PASSED
