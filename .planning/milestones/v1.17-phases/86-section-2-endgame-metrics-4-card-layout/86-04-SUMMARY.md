---
phase: 86
plan: 04
subsystem: frontend
tags: [components, endgame-metrics, cards, sig-gating]
requires:
  - 86-02 (backend Skill + per-bucket diff fields wired into ScoreGapMaterialResponse / MaterialRow)
  - 86-03 (shared lib/endgameMetrics.ts helpers + constants)
provides:
  - frontend/src/components/charts/EndgameMetricCard.tsx (Conv/Parity/Recov shared shell)
  - frontend/src/components/charts/EndgameSkillCard.tsx (Skill composite variant, no WDL)
affects:
  - "(no existing files modified — additive only; Plan 05 will mount these in the orchestrator)"
tech-stack:
  patterns:
    - "Props-driven sibling card pattern (Phase 85 EndgameOverallCard precedent)"
    - "Sig-gating triple (isConfident + outside-neutral-band + n-floor) on diff font color only"
    - "Per-card MetricStatPopover with locked D-16 methodology copy"
key-files:
  created:
    - frontend/src/components/charts/EndgameMetricCard.tsx (217 LOC)
    - frontend/src/components/charts/EndgameSkillCard.tsx (195 LOC)
    - frontend/src/components/charts/__tests__/EndgameMetricCard.test.tsx (224 LOC, 7 tests)
    - frontend/src/components/charts/__tests__/EndgameSkillCard.test.tsx (160 LOC, 6 tests)
  modified: []
decisions:
  - "Used `relative` flag on MetricStatPopover for both card variants (D-16 + MetricStatTooltip convention for 0% baselines, mirrors EndgameOverallPerformanceSection score-gap card)."
  - "Sig-gated color test asserts inline `style.color` non-empty for the confident case and empty string for the weak case. Compared via the `normalizeColor` helper from EndgameOverallPerformanceSection.test.tsx (jsdom rewrites oklch `0.50` → `0.5`). Exact-hex match would be brittle; the chosen pattern is robust and verifies the gating contract."
  - "Tests were authored in the TDD RED phase of Tasks 1 and 2 rather than in a separate Task 3 — natural consequence of `tdd=\"true\"` on each task. Plan 04 Task 3's acceptance criteria are still satisfied (both test files exist, ≥4 tests each, lint+tsc clean)."
  - "Empty-state branch on EndgameSkillCard suppresses the popover trigger entirely (matches legacy gauge-only mobile fallback) rather than rendering a muted popover. Simpler + lower visual noise."
metrics:
  completed_date: 2026-05-14
  tasks_completed: 3
  duration_minutes: 6
  test_files_added: 2
  tests_added: 13
  test_files_passing: 34
  tests_passing: 388
---

# Phase 86 Plan 04: Sibling Card Components (EndgameMetricCard + EndgameSkillCard) Summary

Built the two sibling card components for the Phase 86 "Endgame Metrics" 4-card
layout: `EndgameMetricCard` (shared shell for Conversion / Parity / Recovery)
and `EndgameSkillCard` (composite Skill variant with no WDL bar). Both are
props-driven, mirror the Phase 85 sibling-component pattern, and apply the
v1.17 single-bullet doctrine: per-card peer bullet vs 0 with the sig-gating
triple gating only the diff-percent font color.

## What Changed

### Task 1: `EndgameMetricCard.tsx` (new, 217 LOC)

Shared shell for the Conv / Parity / Recov cards. Props:

```ts
{
  bucket: MaterialBucket;
  row: MaterialRow;
  mirror: MaterialRow | undefined;
  sharePct: number;
  metricName: string;
  metricExplanation: ReactNode;
  tileTestId: string;
}
```

Layout follows the Phase 85 sibling-card pattern (`charcoal-texture rounded-md
p-4` tile, `flex flex-col gap-4` body):

1. **Title** — `BUCKET_DISPLAY_LABELS_WITH_METRIC[bucket]` (e.g. "Conversion (Win)").
2. **Gauge row** — `EndgameGauge` with `FIXED_GAUGE_ZONES[bucket]` per SEC2-04;
   `opacity-50` wrapper when `row.games === 0` (D-17).
3. **Games-count row** — Win/Draw/Loss label + Swords icon with
   `Games: {sharePct.toFixed(1)}% ({total})` (D-15), only when `row.games > 0`.
4. **MiniWDLBar** — only when `row.games > 0`.
5. **Peer-bullet row** — when `hasOpponent = oppR !== null && row.opponent_games
   >= MIN_OPPONENT_BASELINE_GAMES`:
   - Text row: `You: X% · Opp: Y% · Diff: ±Zpp` + `MetricStatPopover` trigger.
   - `MiniBulletChart` with `value = userR - oppR`, neutral band ±0.05,
     domain 0.20, CI whiskers from `row.diff_ci_low/high`.
6. **Missing-opponent** — muted `n < 10, baseline unavailable` text replaces
   the peer-bullet row when `opponent_games < MIN_OPPONENT_BASELINE_GAMES`.
7. **Empty state** — when `row.games === 0`: opacity-50 gauge + "Not enough
   data yet" replaces WDL bar / peer-bullet / popover trigger entirely (D-17).

Sig-gating triple on the diff font color: `paintColor = hasOpponent &&
isConfident(deriveLevel(p, n)) && (diff < NEUTRAL_ZONE_MIN || diff >=
NEUTRAL_ZONE_MAX)`. Red below band, green at/above band, neutral CSS-default
when not confident.

`MetricStatPopover` mounted per-card with the orchestrator-provided
`metricName` / `metricExplanation` and the locked D-16 methodology block
(`Score: per-bucket headline rate ... Test: Wald-z ... CI: 95% normal-approx`).

**Commit:** `306911ff`

### Task 2: `EndgameSkillCard.tsx` (new, 195 LOC)

Composite variant. Props:

```ts
{
  skill: number | null;
  oppSkill: number | null;
  totalGames: number;
  pValue: number | null;
  ciLow: number | null;
  ciHigh: number | null;
  tileTestId: string;
}
```

Layout:

1. **Title** — "Endgame Skill".
2. **Gauge** — `EndgameGauge` with `ENDGAME_SKILL_ZONES`; `opacity-50` wrapper
   when `skill === null`.
3. **Games-count row** — Swords icon with `Games: {totalGames.toLocaleString()}`;
   no share % (Skill spans all buckets, share would always be 100%).
4. **No WDL bar** — locked SEC2-03 (single-ply composite has no W/D/L
   definable).
5. **Peer-bullet row** — when `skill !== null && oppSkill !== null &&
   totalGames >= MIN_OPPONENT_BASELINE_GAMES`:
   - Text row: `Your Skill: X% · Opp Skill: Y% · Diff: ±Zpp` + popover trigger.
   - `MiniBulletChart` with `value = skill - oppSkill`, same neutral band /
     domain / barColor as Conv/Parity/Recov, CI whiskers from props.
6. **Empty state** — when `skill === null`: opacity-50 gauge + "Not enough
   data yet" only, no peer-bullet, no popover trigger (matches legacy
   gauge-only mobile fallback at `EndgameScoreGapSection.tsx:512-528`).

Sig-gating triple identical to `EndgameMetricCard` but n-floor is `totalGames`
(per the plan; orchestrator must ensure `pValue` is null when any active opp
component is sparse — that gating happens server-side per D-01).

`MetricStatPopover` mounted with the locked D-16 Skill explanation: "A
composite of your Conversion, Parity, and Recovery rates compared to the same
composite for your opponents in the mirror bucket. One-number summary of
overall endgame proficiency." Same methodology block as `EndgameMetricCard`.

**Commit:** `f52aba3a`

### Task 3: Vitest coverage (RED+GREEN as part of Tasks 1 and 2)

Two test files added during the TDD RED phases of Tasks 1 and 2:

- `__tests__/EndgameMetricCard.test.tsx` (224 LOC, 7 tests):
  1. Structural — container testid + gauge + WDL bar + peer-bullet present
  2. Games-count row shows `Games: {sharePct}% ({total})` with localized total
  3. Title uses `BUCKET_DISPLAY_LABELS_WITH_METRIC[bucket]`
  4. Sig-gated diff color: confident + outside band → `ZONE_SUCCESS` (normalized)
  5. Sig-gated diff color: weak p-value → no inline color
  6. Empty state: `row.games === 0` → "Not enough data yet", no WDL, no bullet
  7. Missing-opponent: `opponent_games < 10` → muted text, no bullet, WDL stays
- `__tests__/EndgameSkillCard.test.tsx` (160 LOC, 6 tests):
  1. Structural — container testid + gauge + games-count + peer-bullet present
  2. NO `MiniWDLBar` rendered (queryByTestId returns null)
  3. Title + Your Skill / Opp Skill labels render
  4. Sig-gated diff color: confident + outside band → `ZONE_SUCCESS`
  5. Sig-gated diff color: weak p-value → no inline color
  6. Empty state: `skill === null` → "Not enough data yet", no bullet, no info trigger

Both files use the same `normalizeColor` helper as
`EndgameOverallPerformanceSection.test.tsx` to handle jsdom's
`oklch(0.50 …)` → `oklch(0.5 …)` rewrite when reading `style.color` back.

**Commits:** `4fcc6667` (RED for MetricCard), `13033d9f` (RED for SkillCard) —
implementations folded into Tasks 1 and 2 commits.

## Verification

- `cd frontend && npx tsc --noEmit` → exit 0
- `cd frontend && npm run lint` → exit 0
- `cd frontend && npm test -- --run` → 388 tests across 34 files, all passing
- `cd frontend && npm test -- --run EndgameMetricCard EndgameSkillCard` → 13/13
- New components import only from `@/lib/endgameMetrics` (Plan 03 lift),
  existing chart primitives, theme constants, and `EndgameOverallShared` for
  `deriveLevel`. No duplicate constants.
- No `text-xs` usage in either new component or test file (CLAUDE.md rule).
- All interactive elements have `data-testid` (browser-automation rule):
  `tile-*`, `tile-*-you`, `tile-*-opp`, `tile-*-diff`, `tile-*-info`,
  `tile-*-muted`, `tile-*-games-count`. Popover triggers have `aria-label`.

## Deviations from Plan

### Auto-fixed Issues

None — no Rule 1 / Rule 2 / Rule 3 fixes were needed. Plan execution was
straightforward.

### Task structure note (informational, not a deviation)

Plan 04 splits the work into three tasks with `tdd="true"` on each, but Task 3
is the "add tests" step for components built in Tasks 1 and 2. The natural
TDD flow puts the test file authoring in each task's RED phase, so:

- Task 1 (EndgameMetricCard) created its test file in its RED commit
  (`4fcc6667`) and its component in its GREEN commit (`306911ff`).
- Task 2 (EndgameSkillCard) created its test file in its RED commit
  (`13033d9f`) and its component in its GREEN commit (`f52aba3a`).
- Task 3 (tests-only) is therefore satisfied by the artifacts of Tasks 1 and 2.
  No separate commit was needed — the acceptance criteria (≥4 tests per file,
  tsc + lint clean) are already met.

## Notes for Downstream Plans

- **Plan 05 (orchestrator)** mounts these cards into `EndgameMetricsSection`.
  For `EndgameMetricCard`, the orchestrator passes:
  - `metricName="Conversion" / "Parity" / "Recovery"`
  - `metricExplanation` — the locked D-16 strings:
    - Conversion: "Your win rate (only wins count) when you entered the
      endgame with a Stockfish eval ≥ +1.0, compared to your opponents in
      the mirror bucket. Filter-responsive."
    - Parity: "Your chess score (wins + ½ draws) when you entered the
      endgame with an eval between −1.0 and +1.0, compared to your opponents
      in the mirror bucket. Filter-responsive."
    - Recovery: "Your save rate (wins + draws count) when you entered the
      endgame with an eval ≤ −1.0, compared to your opponents in the mirror
      bucket. Filter-responsive."
  - `tileTestId` — `tile-conversion` / `tile-parity` / `tile-recovery` per D-09b.
  - `sharePct` — `(row.games / totalMaterialGames) * 100` (legacy semantics).
- For `EndgameSkillCard`, the orchestrator passes `tileTestId="tile-endgame-skill"`
  and threads `data.skill / data.opp_skill / data.skill_diff_p_value /
  data.skill_diff_ci_low / data.skill_diff_ci_high` from `ScoreGapMaterialResponse`.

- **Sig-color brittleness** flagged for Plan 05 integration check: the
  per-card sig-color tests assert `style.color` is non-empty (after normalizing
  oklch) for confident-and-outside-band, and empty for weak. This catches the
  gating contract but not the precise color choice; Plan 05 should add a
  smoke test that the rendered cards visually match the locked D-14 doctrine
  (red below band, green above band) at the section level.

- **Independence caveat** (D-01 carry-over): the Skill p-value computed in
  Plan 02 treats per-bucket variances as independent, which slightly
  over-estimates precision. Surfaced here for awareness — Plan 05 should NOT
  add UI affordances implying a tighter contract than the helper provides.

## Self-Check: PASSED

- `frontend/src/components/charts/EndgameMetricCard.tsx` — FOUND
- `frontend/src/components/charts/EndgameSkillCard.tsx` — FOUND
- `frontend/src/components/charts/__tests__/EndgameMetricCard.test.tsx` — FOUND
- `frontend/src/components/charts/__tests__/EndgameSkillCard.test.tsx` — FOUND
- Commit `4fcc6667` (RED test for MetricCard) — FOUND in `git log`
- Commit `306911ff` (GREEN MetricCard) — FOUND in `git log`
- Commit `13033d9f` (RED test for SkillCard) — FOUND in `git log`
- Commit `f52aba3a` (GREEN SkillCard) — FOUND in `git log`
