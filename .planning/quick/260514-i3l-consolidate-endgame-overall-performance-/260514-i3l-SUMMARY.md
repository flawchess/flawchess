---
phase: 260514-i3l
plan: 01
type: quick
tags: [frontend, tooltip, refactor, endgames]
status: complete
commits:
  - 95e08dfa  # feat(endgames): add MetricStatTooltip + MetricStatPopover shared components
  - 5919c62b  # refactor(endgames): consolidate Overall Performance tooltips into MetricStatPopover
files_added:
  - frontend/src/components/popovers/MetricStatTooltip.tsx
  - frontend/src/components/popovers/MetricStatPopover.tsx
  - frontend/src/components/popovers/__tests__/MetricStatTooltip.test.tsx
files_modified:
  - frontend/src/components/charts/EndgameOverallCard.tsx
  - frontend/src/components/charts/EndgameOverallEntryCard.tsx
  - frontend/src/components/charts/EndgameOverallPerformanceSection.tsx
files_deleted:
  - frontend/src/components/popovers/ScoreGapPopover.tsx
---

# Quick task 260514-i3l: Endgame Overall Performance tooltip consolidation

Consolidated the 6 tooltips in the FlawChess Endgames page "Endgame Overall
Performance" section into one shared `<MetricStatTooltip>` body + a
`<MetricStatPopover>` Radix shell with uniform 4-paragraph anatomy and a
vocabulary switch (score-based for 5/6 metrics, eval-based for Endgame Entry
Eval).

## What changed

**Components added (1 popover body + 1 popover shell + 1 test file):**

- `MetricStatTooltip.tsx` — pure-markup tooltip body. Props:
  `{ name, explanation, value, baseline, unit, gameCount, level, pValue,
  vocabulary, neutralLower, neutralUpper, baselineLabel, methodology,
  lastPlayedAt? }`. Vocabulary switch (`score` → strength/weakness/difference;
  `eval` → advantage/disadvantage/deviation). Unit switch (`percent` →
  baseline-relative line; `pawns` → signed pawns, no baseline-distance text).
  Sign convention: signed only for gap metrics (baseline=0) and pawns;
  unsigned for score-vs-50%. Imports `ConfidenceLevel` from
  `@/lib/scoreConfidence`.

- `MetricStatPopover.tsx` — Radix popover shell mirroring the existing
  ScoreGapPopover / AchievableScorePopover / BulletConfidencePopover
  hover pattern (100ms open delay, Portal + Content `side="top"
  sideOffset={4}`, identical animation class soup, `text-xs`). Wraps
  `<MetricStatTooltip>`. Adds `testId`, `ariaLabel`, optional
  `triggerClassName`.

- `MetricStatTooltip.test.tsx` — 21 tests covering:
  - 4 headline shapes per vocabulary (score: strength/weakness/difference/
    inconclusive; eval: advantage/disadvantage/deviation/inconclusive).
  - Percent value-line: unsigned for baseline=0.5, signed for baseline=0,
    "at the X% baseline." when diff rounds to 0.0%.
  - Pawns value-line: signed pawns, no baseline-distance text.
  - pValue=null branch: no `p = ` segment, no `null`/`NaN` leak.
  - lastPlayedAt branch: present/null/undefined.
  - Bold name + explanation paragraph.
  - **D-10 forbidden-framing contract** (Achievable Score body): contains
    `2300+` and `Lichess`; does not contain `underperformance` /
    `fall short` / `below your potential`. Ported from
    `AchievableScorePopover.test.tsx`.

**Call sites migrated (6 tooltips, 3 files):**

| File                                   | Tooltip                  | Vocabulary | Baseline | Neutral band                                    | testId                              |
| -------------------------------------- | ------------------------ | ---------- | -------- | ----------------------------------------------- | ----------------------------------- |
| `EndgameOverallCard.tsx`               | Non-Endgame Score        | score      | 0.5      | 0.45 / 0.55                                     | `score-info-no`                     |
| `EndgameOverallCard.tsx`               | Endgame Score            | score      | 0.5      | 0.45 / 0.55                                     | `score-info-yes`                    |
| `EndgameOverallEntryCard.tsx`          | Endgame Entry Eval       | eval       | 0 pawns  | ENDGAME_ENTRY_EVAL_NEUTRAL_*_PAWNS (±0.75)      | `entry-eval-popover-trigger`        |
| `EndgameOverallEntryCard.tsx`          | Achievable Score         | score      | 0.5      | 0.45 / 0.55                                     | `popover-trigger-achievable-score`  |
| `EndgameOverallPerformanceSection.tsx` | Achievable Score Gap     | score      | 0        | SCORE_GAP_NEUTRAL_MIN / _MAX (±0.10)            | `achievable-score-gap-info`         |
| `EndgameOverallPerformanceSection.tsx` | Endgame Score Gap        | score      | 0        | SCORE_GAP_NEUTRAL_MIN / _MAX (±0.10)            | `endgame-score-gap-info`            |

`EndgameOverallCard` is a single component rendered twice (Cards 1 + 3 in
`EndgameOverallPerformanceSection`), so the source has 5 `<MetricStatPopover>`
usages producing 6 runtime tooltips. Two new props (`popoverName`,
`popoverExplanation`) were added to `EndgameCardProps` to parameterise the
per-card prose.

All 6 existing `data-testid` and `aria-label` values were preserved
verbatim (including `Show eval confidence details` from
`BulletConfidencePopover`'s default).

**Component deletion:**

`ScoreGapPopover.tsx` deleted after migration — `knip` confirmed it had no
remaining consumers (its only two call sites were the Achievable Score Gap
and Endgame Score Gap rows in `EndgameOverallPerformanceSection`, both now
on `MetricStatPopover`). The other three legacy popovers
(`ScoreConfidencePopover`, `BulletConfidencePopover`, `AchievableScorePopover`)
stayed: each still has consumers outside the migrated section
(`ExplorerTab`, `OpeningFindingCard`, `OpeningStatsCard`,
`Openings.statsBoard.test.tsx`). `AchievableScorePopover.test.tsx` is kept
intact for the same reason.

## Verification

| Check                                    | Result                                                                                            |
| ---------------------------------------- | ------------------------------------------------------------------------------------------------- |
| `npm test -- --run MetricStatTooltip`    | 21/21 pass.                                                                                       |
| `npm test -- --run` (full suite)         | 373/374 pass. 1 pre-existing failure (see Deviations).                                            |
| `npm run lint`                           | Clean.                                                                                            |
| `npm run knip`                           | Clean (after deleting `ScoreGapPopover.tsx`).                                                     |
| `npm run build`                          | Succeeds (4.51s).                                                                                 |
| 6 testIds appear exactly once in source  | Confirmed via grep.                                                                               |
| `AchievableScorePopover` untouched       | The legacy component file is unchanged; its standalone test still pins the D-10 contract there.   |

## Deviations from the plan

**1. Pre-existing test failure in `AchievableScorePopover.test.tsx` not fixed.**

`AchievableScorePopover.test.tsx › body copy mentions the Lichess formula and
the achieved-score comparison` was failing on `main` before this task. The
test asserts the popover body contains `/Compare.*against your achieved
Endgame score/i` (lowercase "score", with the word "achieved" between
"your" and "Endgame"). The actual `AchievableScorePopover` body renders
`Compare against your Endgame Score.` (capital E + S, no "achieved").

Confirmed pre-existing by stashing my changes and rerunning the test in
isolation against `ee4dce2e` (the worktree base, plus Task 1 commit
`95e08dfa` which touches no `AchievableScorePopover` code): the same single
test fails identically.

Per the executor's scope boundary rule (only auto-fix issues directly caused
by the current task's changes), this is out of scope for the consolidation
quick task. Either the test assertion should be relaxed to
`/Compare.*Endgame [Ss]core/i` or the component prose should be amended to
include "achieved" — both are cosmetic and unrelated to the consolidation.
Flagging for a follow-up quick task.

**2. `ScoreGapPopover.tsx` deletion vs the plan's `must_haves` entry.**

The plan's `must_haves.truths` claims "ScoreGapPopover ... all still exist
(each has at least one consumer outside the migrated section)." This was
incorrect — `ScoreGapPopover` had no consumers outside the migrated section,
and `knip` flagged it after migration. The Task 2 action explicitly
instructs: "If knip reports it as unused, delete the .tsx file AND its
sibling test (if any)." Operational instruction takes precedence, so the
file was deleted. `ScoreGapPopover` had no sibling test, so nothing else
needed removing. The `must_haves` claim about `AchievableScorePopover` did
hold once `AchievableScorePopover.test.tsx` was counted as a consumer
(knip treats live tests as consumers).

## Status

**complete** — both tasks executed atomically with passing checks; one pre-existing
test failure documented and out of scope.
