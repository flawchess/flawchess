---
phase: 260508-f9o
plan: 01
type: quick
status: complete
completed: 2026-05-08
requirements:
  - QUICK-260508-F9O-01
key-files:
  modified:
    - app/schemas/openings.py
    - app/services/openings_service.py
    - frontend/src/types/api.ts
    - frontend/src/pages/Openings.tsx
    - tests/test_openings_service.py
    - frontend/src/pages/__tests__/Openings.statsBoard.test.tsx
commits:
  - 25a7c31b
  - c0b6d6dc
---

# Quick Task 260508-f9o: Eval Bullet Row in Moves "Results played as" Card

One-liner: Added a third MG-entry eval bullet chart row under the Openings → Moves "Results played as" card, matching the chart-left / indicator-right layout used by `OpeningStatsCard` and `OpeningFindingCard`, with backend `/openings/positions` plumbing the eval fields by reusing the existing `query_opening_phase_entry_metrics_batch` + `compute_eval_confidence_bucket` helpers.

## What Changed

### Backend (commit `25a7c31b`)

`app/schemas/openings.py`:
- Extended `WDLStats` with optional `avg_eval_pawns`, `eval_ci_low_pawns`, `eval_ci_high_pawns`, `eval_n` (default 0), `eval_p_value`, `eval_confidence` (default `"low"`). Mirrors the `OpeningWDL` shape used by Stats and Insights cards.
- Extended `OpeningsResponse` with `eval_baseline_pawns: float`. Resolved server-side from `request.color` (BLACK when `"black"`, else WHITE).

`app/services/openings_service.py`:
- `analyze()` now calls `query_opening_phase_entry_metrics_batch(hashes=[request.target_hash], hash_column=request.match_side, …)` when `target_hash is not None`. The helper accepts the `Literal["full","white","black"]` value directly, so `match_side` flows through unchanged.
- The MG-entry finalizer block (`compute_eval_confidence_bucket(pe.eval_sum_mg, pe.eval_sumsq_mg, pe.eval_n_mg)` → pawns + CI + confidence) is copied verbatim from `stats_service.py:405-420`. When `pe is None` or `eval_n_mg == 0`, the eval fields stay at their schema defaults.
- Per-color baseline resolved via the constants imported from `app.services.opening_insights_constants` (the same module `stats_service.py` imports them from). `color is None` falls back to white, matching the existing convention.

`tests/test_openings_service.py`:
- New `TestAnalyzeEvalFields` class with 4 specs covering: position with MG eval populates 12-game mean ≈ 0.31 pawns + CI bounds straddling the mean; position with `eval_cp=None` returns defaults (`eval_n=0`, `avg_eval_pawns=None`); `target_hash=None` skips the fetch and returns defaults; `color=None` falls back to the white baseline (+0.25). New helper `_seed_game_with_mg_eval` seeds the opening anchor row + a `phase=1` MG-entry row in one call.

### Frontend (commit `c0b6d6dc`)

`frontend/src/types/api.ts`:
- `WDLStats` mirrors the backend fields. The MG-entry fields are optional in TypeScript (`eval_n` and `eval_confidence` are required because the backend always sets them; the others default to `null`).
- `OpeningsResponse.eval_baseline_pawns: number` added.

`frontend/src/pages/Openings.tsx`:
- Replaced the 2-column `grid grid-cols-[auto_minmax(0,1fr)]` inside `wdl-moves-position` with a single 1-column container that holds (a) a flex header (`positionResultsLabel` + games link) and (b) a `grid grid-cols-[minmax(0,1fr)_auto] gap-x-2 gap-y-2 items-center` block with three rows (WDL / Score / Eval).
- Each row puts the chart in the 1fr column and the indicator (label + value + popover) in the auto column. All three chart bars share the same flexible 1fr column, so they render at identical width on every viewport.
- New eval row is structurally identical to the eval row in `OpeningStatsCard` / `OpeningFindingCard`: signed pawns (`formatSignedEvalPawns`) + `Cpu` icon + `BulletConfidencePopover`, with the existing `showEvalZoneFont` confidence-and-zone gate. When `hasMgEval` is false (no eval data), both the chart and indicator render an em-dash placeholder.
- Imports added: `Cpu` (lucide-react), `BulletConfidencePopover`, `formatSignedEvalPawns`, `EVAL_BULLET_DOMAIN_PAWNS`, `EVAL_NEUTRAL_MIN_PAWNS`, `EVAL_NEUTRAL_MAX_PAWNS`, `evalZoneColor`. `EVAL_BASELINE_PAWNS_WHITE` / `_BLACK` were already imported.
- Backend-provided `gamesData.eval_baseline_pawns` preferred over the local constant fallback (handles stale-cache safety).

`frontend/src/pages/__tests__/Openings.statsBoard.test.tsx`:
- Three new describe blocks covering the eval row's sub-trees: `BulletConfidencePopover` trigger renders with `eval-bullet-popover-trigger` testid + default aria-label; `MiniBulletChart` with `EVAL_BULLET_DOMAIN_PAWNS` + `tickPawns` renders the bar + CI whisker; the `hasMgEval` gate returns `true` only when `eval_n > 0` AND `avg_eval_pawns` is a real number.

## Reused Helpers (No Duplicated Logic)

- `query_opening_phase_entry_metrics_batch` (`app/repositories/stats_repository.py`) — same SQL helper Phase 80 already uses for Stats + Insights. The optional `hash_column` parameter accepts the request's `match_side` directly.
- `compute_eval_confidence_bucket` (`app/services/eval_confidence.py`) — single source of truth for the eval z-test confidence bucket and CI.
- `EVAL_BASELINE_PAWNS_WHITE` / `_BLACK` (`app/services/opening_insights_constants.py`) — same module `stats_service.py` imports them from.
- The MG-entry finalizer block in `stats_service.py:405-420` was copied verbatim into `openings_service.analyze`. No paraphrasing or alternative derivation.
- Frontend layout, gates, and constants (`EVAL_BULLET_DOMAIN_PAWNS`, `EVAL_NEUTRAL_*_PAWNS`, `evalZoneColor`, `formatSignedEvalPawns`, `isConfident`, `ZONE_NEUTRAL`, `BulletConfidencePopover`) are all the same ones `OpeningStatsCard` / `OpeningFindingCard` use.

## Verification

Backend:
- `uv run ruff check app/ tests/` — all checks passed
- `uv run ty check app/ tests/` — all checks passed
- `uv run pytest tests/test_openings_service.py tests/test_stats_repository.py tests/services/test_stats_service_phase_entry.py tests/test_openings_repository.py` — 96 passed
- `uv run pytest -k openings -x` — 112 passed, 1151 deselected

Frontend:
- `npm run lint` — clean
- `npm run knip` — clean
- `npm run build` — built in ~5s, no errors
- `npm test -- --run` — 24 files, 289 tests passed (was 283 pre-task; +6 new specs in 4 describe blocks)

## Deviations from Plan

None of substance. Two minor adjustments documented below; both were reasoned in-line and are noted here for traceability.

1. The plan suggested adding `# Phase 80 plumbing` to the schema comment. I dropped that label and used the quick-task ID instead so the comment stays consistent with the surrounding `260504-ttq` / `260507-aw5` references in the same `WDLStats` block.
2. Tests were added as `TestAnalyzeEvalFields` in `tests/test_openings_service.py` (the file the plan suggested) using a local `_seed_game_with_mg_eval` helper rather than reusing `tests/services/test_stats_service_phase_entry.py::_seed_game_with_phases`. Reason: the existing helper requires an opening anchor from `openings_dedup` (matched by `ply_count`) and uses a separate `_create_test_users` fixture wired to a different user-id pool. Mirroring that wiring would have required cross-module imports. The local helper is small (50 LOC) and its assertions cover the new behavior precisely.

## Self-Check

Files exist:
- `.planning/quick/260508-f9o-in-the-openings-moves-tab-section-result/260508-f9o-PLAN.md` ✓
- `.planning/quick/260508-f9o-in-the-openings-moves-tab-section-result/260508-f9o-SUMMARY.md` ✓ (this file)
- `app/schemas/openings.py` ✓
- `app/services/openings_service.py` ✓
- `frontend/src/types/api.ts` ✓
- `frontend/src/pages/Openings.tsx` ✓
- `tests/test_openings_service.py` ✓
- `frontend/src/pages/__tests__/Openings.statsBoard.test.tsx` ✓

Commits exist:
- `25a7c31b feat(260508-f9o): plumb MG-entry eval into /openings/positions` ✓
- `c0b6d6dc feat(260508-f9o): three-row chart layout for Moves "Results played as" card` ✓

## Self-Check: PASSED
