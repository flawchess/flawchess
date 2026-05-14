---
phase: 87
type: fix
status: complete
title: Replace per-type Conv+Recov peer bullets with a single Score bullet
completed: 2026-05-14
commits:
  - d536b026 refactor(87): drop redundant Conv/Recov peer-diff fields
  - 2e57f211 feat(87): add per-class score_p_value for type-card score bullet sig-gating
  - dec56649 refactor(87): replace per-card Conv+Recov bullets with single Score bullet
  - 65e0e2ba test(87): cover redesigned EndgameTypeCard with single Score bullet
  - 31e082d1 fix(87): use endgame_games denominator and section landmark
  - 60eee922 docs(87): mark code review findings as fixed
key_files:
  created:
    - .planning/milestones/v1.17-phases/87-section-3-per-type-endgame-type-breakdown-cards/87-FIX-SUMMARY.md
  modified:
    - app/schemas/endgames.py
    - app/services/endgame_service.py
    - tests/test_endgame_service.py
    - frontend/src/types/endgames.ts
    - frontend/src/components/charts/EndgameTypeCard.tsx
    - frontend/src/components/charts/__tests__/EndgameTypeCard.test.tsx
    - frontend/src/components/charts/EndgameTypeBreakdownSection.tsx
    - frontend/src/pages/Endgames.tsx
    - .planning/milestones/v1.17-phases/87-section-3-per-type-endgame-type-breakdown-cards/87-REVIEW.md
  deleted: []
---

# Phase 87 Fix: Per-Type Card Peer Signal Redesign

## Problem

Code review of the freshly-built `EndgameTypeCard` surfaced a deeper issue
than any individual finding: the Conversion and Recovery peer-bullet rows on
each card are mathematically redundant. Both are derived from the same
per-class WDL totals via the same-game mirror identity:

- `oppConv = recovery_losses / recovery_games` (mirror-flip W↔L on the
  recovery bucket)
- `oppRecov = (conversion_losses + conversion_draws) / conversion_games`
  (saves-as-W on the conversion bucket)

The user-facing Conv and Recov gap labels therefore move in lockstep — they
can never tell different stories. The CI bars wrap p-values computed on
distinct statistics (compounding REVIEW CR-01's chess-score vs win-rate
mismatch on the Conv side), but the bullets carry the same magnitude. Two
rows, one signal, no extra information for the user.

## Decision

Replace BOTH the Conv and Recov peer-bullet rows with a SINGLE chess-score
bullet using the exact pattern from the "Games with Endgame" card
(`EndgameCard` in `EndgameOverallCard.tsx`). The two per-class gauges
(Conversion, Recovery) at the top of each card are kept — they continue to
show the per-bucket headline rates against fixed per-class typical bands.

The single bullet plots the per-class chess score `(W + 0.5*D) / N` against
the 50% baseline, with Wilson 95% whiskers and a Wilson score-test p-value
gating the inline color (sig-gating triple: `n >= MIN_GAMES_FOR_RELIABLE_STATS
AND isConfident(level) AND outside neutral band`).

## Backend Changes

- **`app/schemas/endgames.py`** — Drop the 10 Phase 87 fields added to
  `ConversionRecoveryStats` (`opp_conversion_pct`, `opp_recovery_pct`,
  `opp_conversion_games`, `opp_recovery_games`, `conv_diff_p_value`,
  `conv_diff_ci_low`, `conv_diff_ci_high`, `recov_diff_p_value`,
  `recov_diff_ci_low`, `recov_diff_ci_high`). Add `score_p_value: float | None`
  to `EndgameCategoryStats` for the new bullet.
- **`app/services/endgame_service.py`** — Remove both
  `compute_score_difference_test` calls per class. Populate `score_p_value`
  via `compute_confidence_bucket(wins, draws, losses, total)` with the
  standard `PVALUE_RELIABILITY_MIN_N=10` wire-format gate.
- **`tests/test_endgame_service.py`** — Drop the 4 `TestPerClassPeerDiff`
  tests (and the `cast_or_zero` helper). Add 2 new `TestPerClassScorePValue`
  tests covering the strong-signal and below-gate cases.

## Frontend Changes

- **`frontend/src/types/endgames.ts`** — Mirror the schema cleanup
  (10 fields out, `score_p_value` in).
- **`frontend/src/components/charts/EndgameTypeCard.tsx`** — Full rewrite of
  the bottom of the card. Top of the card (title + InfoPopover + n-chip +
  gauges + WDL bar + Games deep-link) is preserved. Bottom section becomes a
  single Score row matching `EndgameOverallCard.tsx:113-160` exactly:
  `score = (wins + 0.5*draws) / total`, `[ciLow, ciHigh] = wilsonBounds(...)`,
  `level = deriveLevel(score_p_value, total)`, `MetricStatPopover` with the
  Wilson methodology block, `MiniBulletChart` anchored on
  `SCORE_BULLET_CENTER=0.5`. New testids on the card root:
  `${tileTestId}-score-row`, `-score-value`, `-score-info`, `-score-bullet`.
- **`frontend/src/components/charts/__tests__/EndgameTypeCard.test.tsx`** —
  Rewritten. 10 tests covering full render, deep-link target + click,
  description popover, empty/sparse shells, score sig-gating (confident +
  colored zone vs null p-value vs neutral-zone score), and the
  `SHOW_WDL_BAR_IN_TYPE_CARDS=false` fallback.
- **`frontend/src/components/charts/EndgameTypeBreakdownSection.tsx`** — Add
  `aria-labelledby="endgame-type-breakdown-heading"` on the `<section>` so
  screen readers and automation tools land on a named landmark. Update prop
  docstring to clarify the `totalGames` denominator semantics.
- **`frontend/src/pages/Endgames.tsx`** — Pass `statsData.endgame_games`
  (not `total_games`) to `EndgameTypeBreakdownSection` so each card's
  "Games: X%" is the share of the user's endgames (REVIEW WR-01). Add
  `id="endgame-type-breakdown-heading"` on the wrapping h2. Update the h2
  InfoPopover explainer to describe the new per-type Score bullet instead of
  the now-removed Conv/Recov peer bullets.

## REVIEW.md Findings Folded In

- **CR-01** (Conv peer-diff test ≠ displayed metric) — Obsoleted by design
  change. No peer bullets, no test/displayed-metric mismatch.
- **WR-01** (wrong sharePct denominator) — Now uses `endgame_games`.
- **WR-02** (`as number` casts) — Removed with the bullets.
- **WR-03** (`as Exclude<EndgameClass, 'pawnless'>` cast) — Replaced with an
  explicit `category.endgame_class !== 'pawnless'` guard.
- **WR-04** (dead `!bands` branch) — Dropped.
- **WR-05** (missing aria-label / landmark) — `aria-labelledby` on the
  section + `aria-label` on the `MiniWDLBar` wrapper.
- **WR-06** (no `role="group"` on card root) — Added.
- **IN-02** (`size={130}` magic number) — Extracted to `PER_TYPE_GAUGE_SIZE`.

Still open: IN-01 (`formatDiffPct` rounding mismatch — irrelevant for the
per-type card now, but the helper remains for other call sites), IN-03
(`pawnless` description map), IN-04 (audit other tests using the same
`style.color === ''` pattern).

## Verification

```bash
$ uv run ruff check .
All checks passed!

$ uv run ty check app/ tests/
All checks passed!

$ uv run pytest tests/test_endgame_service.py tests/services/test_score_confidence.py -q
353 passed in 0.32s

$ cd frontend && npx tsc --noEmit
(clean, exit 0)

$ cd frontend && npm run lint
(clean, exit 0)

$ cd frontend && npm run knip
(clean, exit 0)

$ cd frontend && npx vitest run \
    src/components/charts/__tests__/EndgameTypeCard.test.tsx \
    src/components/charts/__tests__/EndgameTypeBreakdownSection.test.tsx \
    src/pages/__tests__/Endgames.overallPerformance.test.tsx
Test Files  3 passed (3)
      Tests  22 passed (22)
```

## Notes for the Next Reviewer

- The Phase 84 `opponent_conversion_pct` / `opponent_recovery_pct` /
  `opponent_conversion_games` / `opponent_recovery_games` fields on
  `ConversionRecoveryStats` are preserved — they still back the legacy
  `EndgameConvRecovChart` component until that file is deleted in a separate
  cleanup pass.
- `compute_score_difference_test` is still imported in
  `app/services/endgame_service.py` (used by `_compute_score_gap_material`
  for the Section 1 / Section 2 surface). The per-class call sites are gone.
- The frontend `formatDiffPct` helper is now unused inside
  `EndgameTypeCard.tsx` but still exported from `lib/endgameMetrics.ts` for
  callers elsewhere; knip is clean.
