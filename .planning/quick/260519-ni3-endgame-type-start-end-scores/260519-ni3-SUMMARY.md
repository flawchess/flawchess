---
phase: quick-260519-ni3
plan: "01"
status: complete
subsystem: endgames
tags: [endgame, score-gap, frontend, backend, tdd]
dependency_graph:
  requires: []
  provides: [type_achievable_score_start_mean, type_achievable_score_end_mean, ScoreGapRow-startSlot-endSlot]
  affects: [EndgameTypeCard, EndgameCategoryStats, ScoreGapRow]
tech_stack:
  added: []
  patterns: [single-source-of-truth helper extraction, slot props for optional UI extension]
key_files:
  created: []
  modified:
    - app/services/endgame_service.py
    - app/schemas/endgames.py
    - tests/test_endgame_service.py
    - frontend/src/types/endgames.ts
    - frontend/src/components/charts/EndgameOverallScoreGapRow.tsx
    - frontend/src/components/charts/EndgameTypeCard.tsx
    - frontend/src/components/charts/__tests__/EndgameTypeCard.test.tsx
    - frontend/src/components/charts/__tests__/EndgameOverallScoreGapRow.test.tsx
decisions:
  - "Extracted _compute_span_scores() returning (es_entry, exit_score) as single source of truth; _compute_span_gap() now delegates to it — no duplication of entry/exit/mate/terminal logic"
  - "Slot props (startSlot/endSlot) default to undefined on ScoreGapRow so 3 other callers render pixel-identical; 3-column layout only activates when slots are present"
  - "Start/End rendered unsigned (Math.round(x*100)%); text-muted-foreground neutral token; no zone color; no separate info popover"
  - "Per-bucket gaps_by_bucket path appends gap only (not start/end); locked by plan decision 4"
metrics:
  duration: "~45 min"
  completed: "2026-05-19T15:12:08Z"
  tasks_completed: 2
  tasks_total: 3
  files_modified: 8
---

# Phase quick-260519-ni3 Plan 01: Start/End Predicted Scores in EndgameTypeCard Summary

**One-liner:** Per-type Start/End expected-score means exposed via `_compute_span_scores` helper, rendered as unsigned whole-percent labels flanking the Score Gap row in EndgameTypeCard.

## Status

**Complete** — Tasks 1 and 2 (backend + frontend code) shipped in commits 3514407f / 82d0968c. The only remaining "Task 3" was a `checkpoint:human-verify` gate, not code work; it was subsequently subsumed by Phase 98, which restored and reworked this exact `EndgameTypeCard` component (per-(class × TC) gauges, `tc` prop) and re-verified it end-to-end with its own UAT. Marked complete at v1.21 milestone close (2026-05-31).

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Backend: expose start/end components + schema + tests | 3514407f | app/services/endgame_service.py, app/schemas/endgames.py, tests/test_endgame_service.py |
| 2 | Frontend: slot props on ScoreGapRow + 3-column label line + tests | 82d0968c | frontend/src/types/endgames.ts, EndgameOverallScoreGapRow.tsx, EndgameTypeCard.tsx, 2 test files |

## What Was Built

### Backend (Task 1)

**`_compute_span_scores()`** — new pure helper returning `(es_entry, exit_score) | None`. Single source of truth for all entry/exit/mate-precedence/terminal-vs-transitory logic. `_compute_span_gap()` is now a thin wrapper: `scores[1] - scores[0]`.

**Call site change** — the loop now calls `_compute_span_scores` once per span; on non-None result it appends to `gaps_by_class`, `starts_by_class`, and `ends_by_class` (new accumulators). `gaps_by_bucket` still receives gap only.

**Per-class builder** — computes `type_start_mean = sum(starts) / n` and `type_end_mean = sum(ends) / n`, both `None` when n == 0 (mirrors `type_gap_mean` None contract).

**Schema** — `EndgameCategoryStats` gains `type_achievable_score_start_mean: float | None = None` and `type_achievable_score_end_mean: float | None = None`.

**Tests added** (`TestStartEndScoreMeans`, 5 cases):
- `test_new_fields_present_on_schema` — attributes exist on schema
- `test_start_end_null_when_n_zero` — None when all entry evals NULL
- `test_reconciliation_invariant_terminal_spans` — hand-computed 3-span fixture; `end - start == gap` to 1e-9
- `test_reconciliation_invariant_two_classes` — two-class independence + reconciliation
- `test_null_eval_spans_excluded_from_start_end` — mixed cohort; excluded spans not counted
- `test_per_bucket_path_unchanged` — bucket gaps are plain floats

### Frontend (Task 2)

**`EndgameCategoryStats` TS type** — two new `number | null` fields added after gap fields.

**`ScoreGapRow` slot props** — optional `startSlot?: ReactNode` and `endSlot?: ReactNode`. When both are undefined the component renders the original single-line `<span>` layout (pixel-identical for existing callers). When either is present, a flex 3-column row is used: `flex-1` left container, `shrink-0` center group, `flex-1 justify-end` right container.

**`EndgameTypeCard`** — derives `startMean`/`endMean` from category; passes `startSlot`/`endSlot` as ReactNodes only when mean is non-null. Each slot: `<Cpu h-3.5 w-3.5 aria-hidden> Start: {Math.round(x*100)}%` with `text-muted-foreground text-sm`, `data-testid=${tileTestId}-asg-start/end`. Unsigned (no sign prefix). Renders nothing when mean is null or showGapRow is false.

**Tests added:**
- `EndgameTypeCard`: 6 new cases in "Start/End predicted scores" describe block (render, null-hide, n==0-hide, existing asg-value/info unchanged, rounding)
- `EndgameOverallScoreGapRow`: 4 new cases for startSlot/endSlot prop threading

## Automated Gate Results

| Check | Result |
|-------|--------|
| `uv run ruff check .` | PASS |
| `uv run ty check app/ tests/` | PASS (zero errors) |
| `uv run pytest tests/test_endgame_service.py` | PASS (294/294) |
| `npx tsc --noEmit` | PASS |
| `npm run lint` | PASS |
| `npm run knip` | PASS |
| `npm test -- --run EndgameTypeCard EndgameOverallScoreGapRow EndgameMetricCard EndgameOverallPerformanceSection` | PASS (67/67) |

## Deviations from Plan

None during the plan tasks. Two post-checkpoint UAT tweaks (commit `66ede60d`):
(1) the `Cpu` icon now appears only on **Start** (the eval-based entry anchor);
**Score Gap** and **End** drop it to keep the 3-column row uncluttered — note
the Score Gap row's `Cpu` predated this task (Phase 87.1), so this also removes
that pre-existing icon. (2) The center label is shortened from "Score Gap:" to
"Gap:"; the `MetricStatPopover` keeps the full "Score Gap" name + explanation,
and the bullet's screen-reader `ariaLabel` keeps the descriptive
"<type> Score Gap" form. No test asserted the icon or the label text, so no test
changes were needed. Gates re-run green: tsc/lint/knip clean, frontend 586 passed.

## Known Stubs

None. All wiring is live: backend computes and returns start/end means; frontend reads them from the API response type and renders.

## Threat Flags

None. The new schema fields (`type_achievable_score_start_mean`, `type_achievable_score_end_mean`) are descriptive expected-score aggregates (0-1 range), no PII, consistent with existing gap fields (T-ni3-01 accepted). Cohort divergence threat (T-ni3-02) mitigated: starts_by_class/ends_by_class appended under the exact same `span_scores is not None` gate as gaps_by_class; reconciliation test asserts `end - start == gap` per class to 1e-9.

## Self-Check: PASSED

All key files found. Commit hashes verified: 3514407f (backend), 82d0968c (frontend). All automated gates green.
