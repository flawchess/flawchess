---
phase: 81-endgame-start-vs-end-twin-tile-section-above-the-wdl-table
plan: 03
subsystem: frontend
tags: [endgames, twin-tile, mini-bullet, sig-test, react-component]
requires:
  - 81-01 (backend EndgamePerformanceResponse fields)
  - 81-02 (frontend types + endgameEntryEvalZones module)
provides:
  - EndgameStartVsEndSection component (the single new artifact of Phase 81)
affects:
  - frontend/src/components/charts/EndgameStartVsEndSection.tsx (NEW)
  - frontend/src/components/charts/__tests__/EndgameStartVsEndSection.test.tsx (NEW)
tech-stack:
  added: []
  patterns:
    - Inline-value-row + popover + MiniBulletChart (mirrored from ExplorerTab)
    - Three-state zone color gated on isConfident + colored-zone check (Pattern A)
    - Tile container: charcoal-texture rounded-md p-4 (Pattern D)
    - n < 10 sparse placeholder per tile (D-06)
key-files:
  created:
    - frontend/src/components/charts/EndgameStartVsEndSection.tsx
    - frontend/src/components/charts/__tests__/EndgameStartVsEndSection.test.tsx
  modified: []
decisions:
  - "Reused wilsonBounds from scoreConfidence.ts rather than re-implementing inline — keeps the score CI computation in one place"
  - "deriveLevel(p, n) thresholds mirror computeScoreConfidence.ts exactly (n>=10 gate, p<0.01 high, p<0.05 medium) so confidence buckets stay consistent across the app"
  - "color='white' on BulletConfidencePopover for endgame stats — the popover's union is 'white' | 'black' only; endgame is color-agnostic, 'white' is a benign default for the per-color baseline tick"
  - "Tile 1 first in DOM (D-17) achieves mobile chronological order via natural document order; no flex-order tricks needed for the 1-col → 2-col responsive switch"
  - "Sparse placeholder uses 'Not enough data yet' (project's existing phrasing on EndgameConvRecovChart is 'Not enough data for…' — matched the leading 'Not enough data' prefix so the section reads consistently)"
metrics:
  duration_minutes: 8
  completed: 2026-05-09
---

# Phase 81 Plan 03: EndgameStartVsEndSection Twin-Tile Component Summary

Built the single new component of Phase 81: a twin-tile "Endgame Start vs End" section composing the existing `MiniBulletChart`, `BulletConfidencePopover`, and `ScoreConfidencePopover` to render Tile 1 (avg eval at endgame entry vs 0) and Tile 2 (endgame score vs 50%) with three-state sig-test color logic and per-tile `n < 10` placeholders.

## What Was Built

- **`frontend/src/components/charts/EndgameStartVsEndSection.tsx`** (NEW)
  - `<section data-testid="endgame-start-vs-end-section">` wrapping a `grid grid-cols-1 lg:grid-cols-2 gap-4` with two `charcoal-texture rounded-md p-4` tiles.
  - Tile 1 (`tile-entry-eval`, "Where you start"): label + signed pawns value + `BulletConfidencePopover` (testid `entry-eval-popover-trigger`) + `MiniBulletChart` with the Plan 02 D-15 constants (`ENDGAME_ENTRY_EVAL_CENTER=0`, neutral band ±0.75, domain ±2.0).
  - Tile 2 (`tile-endgame-score`, "What you do with it"): label + score % value + `ScoreConfidencePopover` (testid `endgame-score-popover-trigger`) + `MiniBulletChart` with the existing Openings score-bullet constants (`SCORE_BULLET_CENTER=0.5`, neutral band ±0.05, domain 0.25 — D-16).
  - Tile 1 first in DOM ordering for D-17 chronological mobile stacking.
  - `deriveLevel(p, n)` helper inlined to bucket the raw backend p-values into `'low' | 'medium' | 'high'` using the same thresholds `scoreConfidence.computeScoreConfidence` uses (n>=10 gate, p<0.01 high, p<0.05 medium).
  - Color-gating logic mirrors ExplorerTab's `showZoneFontColor`: paint the value span's `style.color` only when `isConfident(level) && zoneHex !== ZONE_NEUTRAL`.
  - `wilsonBounds(score, total)` from `scoreConfidence.ts` provides the Tile 2 whisker bounds, then `clampScoreCi` clamps to `[0, 1]` for the chart.
  - `data.endgame_score_p_value ?? 1` coerces nullable backend p-value to the popover's non-nullable `pValue` prop (mirrors `BulletConfidencePopover`'s internal `pValue ?? 1` coercion for symmetry).
  - When `n < MIN_GAMES_FOR_RELIABLE_STATS`, the value-row + chart pair is replaced with `<p className="text-sm text-muted-foreground py-4">Not enough data yet</p>` on that tile only (D-06: keeps layout stable when only one tile is sparse).

- **`frontend/src/components/charts/__tests__/EndgameStartVsEndSection.test.tsx`** (NEW)
  - 14 RED-then-GREEN component tests covering all `<must_haves>` truths.
  - Spies on `MiniBulletChart` via `vi.mock` to assert prop forwarding (Tile 1 D-15 constants + Tile 2 score-bullet constants).
  - `normalizeColor` helper handles jsdom's cosmetic `0.50` → `0.5` rewrite of oklch trailing zeros so the assertions read the actual semantic value, not the textual representation.
  - Covers DOM order (Tile 1 first), color zones (sig+positive → green, sig+negative → red, sig+neutral-band → no color, not-sig → no color), `n<10` placeholder per tile, popover-trigger data-testids.

## Tasks & Commits

| Task | Name                                            | Commit   |
| ---- | ----------------------------------------------- | -------- |
| 1    | Wave 0 — write component tests (RED)            | a7862eda |
| 2    | Create EndgameStartVsEndSection.tsx component   | 8a2909b8 |

## Verification

- `cd frontend && npm test -- --run src/components/charts/__tests__/EndgameStartVsEndSection.test.tsx` — 14/14 passed
- `cd frontend && npm test -- --run` — 331/331 passed (full FE suite, no regressions; up from 317 in Plan 02 — +14 new tests)
- `cd frontend && npm run lint` — 0 errors (3 pre-existing unused-eslint-disable warnings in `coverage/` only)
- `cd frontend && npx tsc --noEmit` — 0 errors (strict, `noUncheckedIndexedAccess` enabled)
- `cd frontend && npm run knip` — 0 issues
- `grep -c 'data-testid="endgame-start-vs-end-section"' frontend/src/components/charts/EndgameStartVsEndSection.tsx` → 1
- `grep -c 'data-testid="tile-entry-eval"' frontend/src/components/charts/EndgameStartVsEndSection.tsx` → 1
- `grep -c 'data-testid="tile-endgame-score"' frontend/src/components/charts/EndgameStartVsEndSection.tsx` → 1
- `grep -c '"overall"' frontend/src/components/charts/EndgameStartVsEndSection.tsx` → 0 (no leftover from any earlier draft)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] jsdom oklch color normalization in tests**
- **Found during:** Task 2 (running tests for the first time after writing the component)
- **Issue:** jsdom's CSSStyleDeclaration normalizes `oklch(0.50 ...)` → `oklch(0.5 ...)` when reading `element.style.color` back. Direct `expect(valueSpan.style.color).toBe(ZONE_SUCCESS)` failed because `ZONE_SUCCESS = 'oklch(0.50 0.14 145)'` and jsdom returned `'oklch(0.5 0.14 145)'`.
- **Fix:** Added a `normalizeColor` helper to the test file that strips trailing zeros from decimals in any numeric token, then compare both sides through it. Preserves the contract — both sides must encode the same color — without weakening it to a regex match.
- **Files modified:** `frontend/src/components/charts/__tests__/EndgameStartVsEndSection.test.tsx`
- **Commit:** 8a2909b8 (folded into Task 2's commit since the helper was added before any test could go green)

### Plan-deviation notes (no functional change)

- The plan's draft `wilsonBounds` snippet was inline in the action block. I imported the existing `wilsonBounds` from `@/lib/scoreConfidence` instead — the plan explicitly told me to "check `frontend/src/lib/` first to avoid duplicating an existing helper", and one is already there. No code drift; matches the plan's intent.
- Plan asked the executor to grep for the canonical "Not enough data" phrasing in the codebase. The closest match is `EndgameConvRecovChart.tsx`'s `"Not enough data for conversion/recovery analysis"`. I used `"Not enough data yet"` (the plan's fallback) since the conv/recov phrasing is bucket-specific and doesn't transfer cleanly. The leading `Not enough data` prefix matches both surfaces, so the test's `/Not enough data/i` regex is consistent with the rest of the page.

## TDD Gate Compliance

Per-task TDD cycle followed:
- Task 1 → `test(81-03)` commit (RED — vitest reports `Failed to resolve import "../EndgameStartVsEndSection"`)
- Task 2 → `feat(81-03)` commit (GREEN — 14/14 tests pass after the component lands and the color-normalization test util is added)
- No REFACTOR commit needed (component is small enough to land clean in one cycle).

## Known Stubs

None. The component is fully wired — Plan 04 is the only remaining gap (page integration in `Endgames.tsx`), which is a separate plan in this phase. No data sources are mocked or stubbed in production code.

## Self-Check: PASSED

- `frontend/src/components/charts/EndgameStartVsEndSection.tsx` — FOUND
- `frontend/src/components/charts/__tests__/EndgameStartVsEndSection.test.tsx` — FOUND
- Commit `a7862eda` — FOUND on branch
- Commit `8a2909b8` — FOUND on branch
- All `<must_haves>` truths verified by passing tests + grep on the component file
- All acceptance criteria (`grep -c` checks) verified:
  - `data-testid="endgame-start-vs-end-section"` count = 1 (>= 1)
  - `data-testid="tile-entry-eval"` count = 1 (>= 1)
  - `data-testid="tile-endgame-score"` count = 1 (>= 1)
  - `MiniBulletChart|BulletConfidencePopover|ScoreConfidencePopover` count = 11 (>= 5; includes JSDoc, imports, renders, ariaLabel refs)
  - `ENDGAME_ENTRY_EVAL_DOMAIN_PAWNS|ENDGAME_ENTRY_EVAL_NEUTRAL` count = 6 (>= 3)
  - `SCORE_BULLET_CENTER|SCORE_BULLET_NEUTRAL` count = 6 (>= 3)
  - `isConfident|MIN_GAMES_FOR_RELIABLE_STATS` count = 7 (>= 2)
  - `color="white"` count = 1 (>= 1)
  - `"overall"` count = 0 (must be 0)
