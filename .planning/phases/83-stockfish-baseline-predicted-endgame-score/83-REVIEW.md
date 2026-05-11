---
phase: 83-stockfish-baseline-predicted-endgame-score
reviewed: 2026-05-11T00:00:00Z
depth: standard
files_reviewed: 21
files_reviewed_list:
  - app/prompts/endgame_insights.md
  - app/schemas/endgames.py
  - app/services/endgame_service.py
  - app/services/endgame_zones.py
  - app/services/eval_utils.py
  - app/services/insights_llm.py
  - app/services/insights_service.py
  - app/services/score_confidence.py
  - frontend/src/components/charts/EndgameStartVsEndSection.tsx
  - frontend/src/components/charts/__tests__/EndgameStartVsEndSection.test.tsx
  - frontend/src/components/popovers/AchievableScorePopover.tsx
  - frontend/src/components/popovers/__tests__/AchievableScorePopover.test.tsx
  - frontend/src/pages/__tests__/Endgames.startVsEnd.test.tsx
  - frontend/src/types/endgames.ts
  - scripts/gen_endgame_zones_ts.py
  - tests/services/test_endgame_zones.py
  - tests/services/test_eval_utils.py
  - tests/services/test_insights_llm.py
  - tests/services/test_insights_service.py
  - tests/services/test_score_confidence.py
  - tests/test_endgame_service.py
findings:
  critical: 1
  warning: 4
  info: 3
  total: 8
status: issues_found
---

# Phase 83: Code Review Report

**Reviewed:** 2026-05-11
**Depth:** standard
**Files Reviewed:** 21
**Status:** issues_found

## Summary

Phase 83 ships the Stockfish-baseline predicted endgame score (`entry_expected_score`) via the Lichess winning-chances sigmoid, plumbed through the backend aggregator, zone registry, LLM payload, and the new 2x2 frontend grid on `EndgameStartVsEndSection`. The pure-math `eval_utils` module, the new Wilson code path (`compute_score_confidence_from_mean`), the aggregator additions in `_get_endgame_performance_from_rows`, and the LLM payload glossary changes are well-covered by tests and consistent with the design.

One **BLOCKER** stands out: the achievable-score bullet on Tile 1 passes the cohort band ([0.45, 0.55]) to `MiniBulletChart` as if it were absolute, but `MiniBulletChart`'s `neutralMin`/`neutralMax` props are documented to be **offsets from `center`**. The component will compute the neutral band as [0.95, 1.05] (clamped off-axis) and render no visible neutral shading on the third bullet. Existing tests assert prop forwarding but do not render the band, so the bug is invisible to the test suite.

Several smaller concerns are flagged below — UI vocabulary table gap for the new metric, an `eval_mate=0` edge case that silently maps to 0.0, and minor cleanup items.

## Critical Issues

### CR-01: Achievable-score MiniBulletChart receives absolute thresholds where offsets are required (broken visible neutral band)

**File:** `frontend/src/components/charts/EndgameStartVsEndSection.tsx:198-217`

**Issue:** The new "Achievable score" row passes:

```tsx
<MiniBulletChart
  value={data.entry_expected_score}
  center={SCORE_BULLET_CENTER}                       // 0.5
  neutralMin={ENTRY_EXPECTED_SCORE_NEUTRAL_MIN}      // 0.45  ← absolute
  neutralMax={ENTRY_EXPECTED_SCORE_NEUTRAL_MAX}      // 0.55  ← absolute
  domain={scoreBulletDomain()}                       // 0.25
  ...
/>
```

But `MiniBulletChart` documents `neutralMin`/`neutralMax` as **offsets from `center`** (see `MiniBulletChart.tsx:32-35` "expressed as an offset from `center`") and computes:

```ts
const absNeutralMin = center + neutralMin;   // 0.5 + 0.45 = 0.95
const absNeutralMax = center + neutralMax;   // 0.5 + 0.55 = 1.05
```

Both bounds get clamped to the axis `[center - domain, center + domain]` = `[0.25, 0.75]`, collapsing the neutral band to a zero-width strip at 0.75. The chart will render no visible neutral shading on this bullet, while Tile 2's `endgame_score` bullet (which correctly passes `neutralMin=-0.05, neutralMax=+0.05`) does render its [0.45, 0.55] band as expected.

The unit test `passes achievable-score W+0.5D constants to MiniBulletChart (D-12 axis parity)` at `EndgameStartVsEndSection.test.tsx:513-540` asserts the props are forwarded as `{ neutralMin: 0.45, neutralMax: 0.55 }`, but the assertion was written against the mocked `MiniBulletChart` and does not exercise the absolute-vs-offset semantics — so the bug is invisible to CI. The other two bullets in the same section happen to work: entry-eval uses `center=0`, so absolute and offset coincide; endgame_score passes the correct `±0.05` offsets via `SCORE_BULLET_NEUTRAL_MIN/MAX`.

Note that the *zone text color* still works (it uses `entryExpectedScoreZoneColor(value)` with absolute thresholds, computed independently from the chart), so the value text colors correctly. Only the visual neutral band on the chart is broken.

**Fix:** Either convert the constants to offsets at the call site or pass already-offset constants. Suggested call-site fix (mirroring Tile 2's pattern):

```tsx
// Pass offsets from SCORE_BULLET_CENTER (0.5) rather than absolute bounds.
neutralMin={ENTRY_EXPECTED_SCORE_NEUTRAL_MIN - SCORE_BULLET_CENTER}  // 0.45 - 0.5 = -0.05
neutralMax={ENTRY_EXPECTED_SCORE_NEUTRAL_MAX - SCORE_BULLET_CENTER}  // 0.55 - 0.5 = +0.05
```

Alternatively, add a derived export to `endgameZones.ts` (e.g. `ENTRY_EXPECTED_SCORE_NEUTRAL_OFFSET_MIN/MAX = lower/upper - 0.5`) and update the prop forwarding test to assert the offset values. The corresponding tests at `EndgameStartVsEndSection.test.tsx:537-540` must be updated to assert `{ neutralMin: -0.05, neutralMax: 0.05 }` (after the fix the achievable bullet will share the same offsets as Tile 2's endgame-score bullet — disambiguating the two `mock.calls` entries will need a different discriminator, e.g. `value` or the `ariaLabel`).

Add a render-level assertion (e.g. inspect the rendered neutral band width with `MiniBulletChart` un-mocked, or snapshot the inline `style` of the band element) so a future regression is caught.

## Warnings

### WR-01: `eval_mate=0` silently maps to 0.0 for both colors

**File:** `app/services/eval_utils.py:69-97`

**Issue:** `eval_mate_to_expected_score(0, "white")` falls through both `if eval_mate > 0` and `if eval_mate < 0` branches and returns `0.0`. The docstring explicitly says "Positive (e.g. +5) means white has a forced mate; negative (e.g. -5) means black has one. The magnitude (distance to mate) is irrelevant" — but it makes no statement about `eval_mate=0`. Stockfish typically does not emit mate=0, but the column is a free `int`; a corrupt/edge backfill row would silently bias the cohort mean toward 0 for either color.

**Fix:** Either explicitly reject `eval_mate=0` with an assertion / `ValueError`, or document it (e.g. "Stockfish never emits eval_mate=0; this branch returns 0.0 by convention but should never be reached in practice"). A defensive `assert eval_mate != 0` would make the contract explicit and surface bad backfill rows early.

### WR-02: AchievableScorePopover leaks a pending `setTimeout` on unmount

**File:** `frontend/src/components/popovers/AchievableScorePopover.tsx:27-37`

**Issue:** `handleMouseEnter` schedules `setTimeout(() => setOpen(true), 100)` and stores the handle on `hoverTimeout.current`. There is no `useEffect` cleanup that clears the timeout on unmount, so if the component unmounts within the 100ms hover delay (e.g. filter change in the parent re-renders), the timer fires `setOpen(true)` on an unmounted instance — React will log a console warning and the open state is wasted. Same pattern exists on the older `ScoreConfidencePopover` so this isn't a regression, but the new copy carries the same defect.

**Fix:** Add a cleanup effect.

```tsx
React.useEffect(() => {
  return () => {
    if (hoverTimeout.current) clearTimeout(hoverTimeout.current);
  };
}, []);
```

### WR-03: UI vocabulary table in `endgame_insights.md` does not list `entry_expected_score`

**File:** `app/prompts/endgame_insights.md:78-90`

**Issue:** The "UI vocabulary — match what the user sees" table maps every metric data field to its narration label (e.g. `score_pct → "Score"`, `endgame_skill → "Endgame Skill"`). `entry_expected_score` is missing — the LLM has to fall back to the metric glossary entry near line 355 to learn it should narrate this metric as "Achievable score". Other tiles' metrics are duplicated in both places; the new metric is only in the glossary.

**Fix:** Add a row to the vocabulary table.

```
| `entry_expected_score`        | "Achievable score"                  | "Achievable score of 58%" |
```

This keeps both surfaces in sync and matches the convention already followed for `entry_eval_pawns`.

### WR-04: Test asserts prop forwarding without rendering the chart, hiding CR-01

**File:** `frontend/src/components/charts/__tests__/EndgameStartVsEndSection.test.tsx:513-540` and `:336-356`

**Issue:** `MiniBulletChart` is mocked to a stub div, so every test only asserts the props the component pushes through, not what the chart renders. The achievable-score test (`passes achievable-score W+0.5D constants to MiniBulletChart`) asserts `{ neutralMin: 0.45, neutralMax: 0.55 }` — which is *what the component sends*, not *what is correct* given the prop contract documented on `MiniBulletChart`. CR-01 is a direct consequence: the test is happy, the user sees a broken band.

**Fix:** Add at least one test per tile that renders the real `MiniBulletChart` (un-mocked) and asserts the inline `style.left`/`style.width` of the neutral band element, or the absolute pixel span of the rendered neutral zone. This both catches CR-01 and pins the offset-vs-absolute contract so future renames cannot silently regress.

## Info

### IN-01: Popover body claims the value comes "via the Lichess winning-chances sigmoid" but mate positions bypass the sigmoid

**File:** `frontend/src/components/popovers/AchievableScorePopover.tsx:73-79`

**Issue:** The body copy reads "via the Lichess winning-chances sigmoid", but the actual aggregator (per `eval_utils.eval_mate_to_expected_score` and `endgame_service.py:1745-1751`) bypasses the sigmoid for mate positions and maps them directly to 0/1. For a user with many forced-mate endings, the "sigmoid" framing is a small white lie. The metric glossary in the LLM prompt (`endgame_insights.md:355`) correctly distinguishes the two paths; the popover does not.

**Fix:** Either tighten the popover copy (e.g. "via the Lichess winning-chances curve; forced mates count as 1 or 0") or accept the simplification as user-facing copy. The lint test at `AchievableScorePopover.test.tsx:60-67` pins the "2300+" and "Lichess" wording, so a copy tweak should also update the assertions.

### IN-02: `hoverTimeout.current` is not reset to `null` after `clearTimeout`

**File:** `frontend/src/components/popovers/AchievableScorePopover.tsx:34-37`

**Issue:** After `clearTimeout(hoverTimeout.current)`, the ref still holds the (now-invalid) timer handle. The popover never reads the handle for anything other than `clearTimeout`, so this is harmless today, but if a future edit checks `hoverTimeout.current != null` as a "timer is armed" signal, it will mis-read a stale handle as armed.

**Fix:**

```tsx
const handleMouseLeave = () => {
  if (hoverTimeout.current) {
    clearTimeout(hoverTimeout.current);
    hoverTimeout.current = null;
  }
  setOpen(false);
};
```

### IN-03: `EVAL_CLIP_MAX_CP` lives in `endgame_service.py` next to `EVAL_ADVANTAGE_THRESHOLD`, not in `endgame_zones.py`

**File:** `app/services/endgame_service.py:176-181`

**Issue:** The Phase 83 prompt and the LLM glossary both describe the clip as a *cohort definition* shared with the sigmoid math (and the prompt explicitly cites the [0.45, 0.55] cohort band, which lives in `endgame_zones.py`). Keeping the clip threshold in `endgame_service.py` while putting the related zone band in `endgame_zones.py` splits one logical knob across two modules. Not a bug — just a minor cohesion smell. If the clip moves (or a future per-ELO clip is introduced) the registry would be the natural home.

**Fix:** Optionally relocate `EVAL_CLIP_MAX_CP` to `endgame_zones.py` alongside the new `entry_expected_score` `ZoneSpec` (it's already a Phase 83 D-07 constant). Re-export from `endgame_service.py` for back-compat with the single caller, or update the import directly. Defer until next refactor pass.

---

_Reviewed: 2026-05-11_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
