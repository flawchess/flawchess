---
phase: 87-section-3-per-type-endgame-type-breakdown-cards
reviewed: 2026-05-14T00:00:00Z
depth: standard
files_reviewed: 11
files_reviewed_list:
  - app/schemas/endgames.py
  - app/services/endgame_service.py
  - tests/test_endgame_service.py
  - frontend/src/types/endgames.ts
  - frontend/src/components/charts/EndgameTypeCard.tsx
  - frontend/src/components/charts/__tests__/EndgameTypeCard.test.tsx
  - frontend/src/lib/endgameMetrics.ts
  - frontend/src/components/charts/EndgameTypeBreakdownSection.tsx
  - frontend/src/components/charts/__tests__/EndgameTypeBreakdownSection.test.tsx
  - frontend/src/pages/Endgames.tsx
  - frontend/src/pages/__tests__/Endgames.overallPerformance.test.tsx
findings:
  critical: 1
  warning: 6
  info: 4
  total: 11
status: fixed
---

# Phase 87: Code Review Report

**Reviewed:** 2026-05-14
**Depth:** standard
**Files Reviewed:** 11
**Status:** issues_found

## Summary

Phase 87 replaces the legacy WDL + ConvRecov endgame charts with a 5-card per-type breakdown section. Backend adds 10 new per-class peer-diff fields to `ConversionRecoveryStats`; frontend mirrors the schema and renders gauges + WDL + peer-bullets + Games deep-link per card. Test coverage on both layers is solid for the layout, sparse states, and sig-gating triple.

The dominant issue is a math/wiring inconsistency on the Conversion peer-diff test (Critical). The displayed metric on the card and bullet position is a **win-rate** difference, but the p-value and 95% CI fed into the same bullet are computed on a **chess-score** difference (treating draws as half-wins). With non-zero draws this produces a CI bar that does not enclose the displayed value, and a significance verdict on a different statistic than the user sees. Several smaller issues around type assertions, magic numbers, the sharePct denominator choice, mobile/A11y patterns, and a misleading "defensive dead branch" follow.

## Critical Issues

### CR-01: Conv peer-diff test statistic does not match the displayed metric

**File:** `app/services/endgame_service.py:401-410` (and mirrored in `frontend/src/components/charts/EndgameTypeCard.tsx:99-141, 357-387`)

**Issue:** The Conversion peer-diff p-value and 95% CI are computed by feeding raw W/D/L counts (including draws) into `compute_score_difference_test`, which calculates a chess-score statistic `(W + 0.5·D) / N` per side. The frontend, however, displays and renders the bullet position from a pure **win-rate** diff:

- `userConv = category.conversion.conversion_pct / 100` is `wins/games` (line 99).
- `oppConv = category.conversion.opp_conversion_pct` is `recovery_losses/recovery_games` (a pure opponent-win-rate, set in `endgame_service.py:422-426`).
- `convDiff = userConv - oppConv` (pure win-rate diff) is passed both as the bullet's `value` and into the gap label.

But `conv_diff_ci_low/high/p_value` come from `compute_score_difference_test(conversion_wins, conversion_draws, conversion_losses, …, recovery_losses, recovery_draws, recovery_wins, …)`. When `conversion_draws > 0` or `recovery_draws > 0`, the helper's per-side score is `(W + 0.5·D)/N`, not `W/N`. The CI midpoint and significance verdict then describe a different quantity than the displayed diff.

Worked counter-example demonstrating divergence:
- Conv bucket: W=10, D=0, L=10 (n=20) → user win-rate 0.5, chess-score 0.5
- Recov bucket: W=0, D=10, L=10 (n=20) → opp Conv via mirror = recovery_losses/n = 10/20 = 0.5 → frontend `convDiff = 0`
- Helper input opp side: `(eg_w=10, eg_d=10, eg_l=0, eg_n=20)` → score = (10+5)/20 = 0.75 → CI midpoint diff = 0.5 − 0.75 = **−0.25**

So the bullet would draw the value dot at 0 and the CI bar centered at −0.25 — a visible mismatch and a significance claim on a statistic the user can't see. The Recov call (lines 411-420) is consistent because it sets `eg_d = 0` and folds draws into wins via the saves-as-W mapping, collapsing chess-score to save-rate. The Conv call does not apply the analogous coercion.

The locked plan (CONTEXT D-01) acknowledges chess-score is what the helper computes and argues "the helper's diff-of-rates output applies directly when we feed it the flipped W/D/L counts" — that reasoning only holds when the user and mirror buckets have D=0, which the production data won't guarantee. The two unit tests that fix exact numeric expectations (`test_per_class_conv_diff_mirror_flip_correctness`) both set draws=0, hiding the divergence. The range-only assertions in `test_conversion_recovery_stats_carries_per_class_diff_fields` (lines 575-580) do not catch it either.

**Fix:** Use the same saves-as-W coercion pattern for Conv (collapse draws into the loss bucket so the helper's chess-score reduces to a Bernoulli win-rate):

```python
# Conv peer-diff via win-rate-as-W mapping (mirrors the Recov saves-as-W mapping).
# Coerce (W, D, L) → (W, 0, D+L) so the helper's (W + 0.5·D)/N collapses to W'/N',
# i.e. the win-rate. Opponent side: their wins in the user's recovery bucket are
# user losses there, so map opp → (recovery_losses, 0, recovery_wins + recovery_draws).
conv_p, conv_ci_low, conv_ci_high = compute_score_difference_test(
    conversion_wins,
    0,
    conversion_draws + conversion_losses,
    conversion_games,
    recovery_losses,
    0,
    recovery_wins + recovery_draws,
    recovery_games,
)
```

Add a unit test with draws > 0 on both buckets that asserts `0.5 * (conv_diff_ci_low + conv_diff_ci_high) == pytest.approx(userConv - oppConv, abs=0.005)`. The mirror identity should still hold; only the per-side score formula changes.

## Warnings

### WR-01: `total_games` is the wrong denominator for "Games: X%" on each card

**File:** `frontend/src/pages/Endgames.tsx:593`, `frontend/src/components/charts/EndgameTypeBreakdownSection.tsx:52-53`

**Issue:** `EndgameTypeBreakdownSection` is mounted with `totalGames={statsData.total_games}` — per `EndgameStatsResponse.total_games` ("Total games matching current filters (not just endgame games)") this is all filtered games, not the endgame subset. For a user with 1000 filtered games where 200 reached an endgame, a class with 80 endgame games renders as "Games: 8.0% (80)" rather than "40.0% (80)", which is far less informative for a section titled "Endgame Type Breakdown". The plan locks `cat.total / totalGames * 100` but does not lock which `totalGames` to pass; passing `endgame_games` would put the share denominator on the same population as the chart.

**Fix:** Pass `statsData.endgame_games` instead, and update the orchestrator's prop comment to clarify the denominator is "games that reached an endgame phase". If the team specifically wants share-of-all-games, label it as such ("of your games" vs "of your endgames") so users can interpret the percentage. Update the EndgameTypeBreakdownSection test fixture's `totalGames=500` so it matches the new semantic.

### WR-02: `as number` casts on already-narrowed nullable fields

**File:** `frontend/src/components/charts/EndgameTypeCard.tsx:111-112, 344, 354, 385, 420, 430, 461`

**Issue:** After `hasConvOpponent` (lines 104-106) narrows `oppConv !== null`, the code still uses `oppConv as number` six times. With `noUncheckedIndexedAccess` enabled and `oppConv: number | null`, the cast loses the narrowing benefit and lets stale code creep in if the guard ever changes. The cast also bypasses TS's flow analysis — if a future refactor flips the guard to `>= MIN` without the `!== null` check, the cast still compiles and crashes at runtime when `oppConv` is null.

**Fix:** Narrow once into local non-null aliases, then drop the casts:

```tsx
if (hasConvOpponent) {
  const oppConvValue: number = oppConv;  // narrowed by the guard above
  // …use oppConvValue everywhere instead of `oppConv as number`
}
```

Or pull the rendered Conv/Recov rows into small sub-components that receive `oppConv: number` non-null. Either pattern enforces the invariant at the type level.

### WR-03: `as Exclude<EndgameClass, 'pawnless'>` hides a real runtime path

**File:** `frontend/src/components/charts/EndgameTypeCard.tsx:162-164`

**Issue:** The InfoPopover content uses

```tsx
{ENDGAME_TYPE_DESCRIPTIONS[
  category.endgame_class as Exclude<EndgameClass, 'pawnless'>
] ?? ''}
```

`ENDGAME_TYPE_DESCRIPTIONS` is typed `Record<Exclude<EndgameClass, 'pawnless'>, string>` so the cast is purely to silence the indexer. If the orchestrator's `HIDDEN_ENDGAME_CLASSES` filter is bypassed (someone mounts `EndgameTypeCard` directly with a pawnless category, or someone adds a new class without updating both maps), the cast lies about the type and the lookup silently returns the `?? ''` fallback — an empty popover with no warning. The card claims (line 145-148 comment) that pawnless can't reach this point, but the runtime guard is missing.

**Fix:** Either widen the map to include all `EndgameClass` keys (drop the `Exclude<…>` from the type), or replace the cast with an explicit guard that surfaces unexpected classes during dev:

```tsx
const desc =
  category.endgame_class !== 'pawnless'
    ? ENDGAME_TYPE_DESCRIPTIONS[category.endgame_class]
    : '';
```

The TS narrowing handles the type without an unchecked assertion.

### WR-04: Empty-class `!bands` branch is documented as unreachable but kept as a divergent shell

**File:** `frontend/src/components/charts/EndgameTypeCard.tsx:147-149, 178`

**Issue:** The comment claims "the defensive `!bands` branch below should never trigger in production" because `PER_CLASS_GAUGE_ZONES` contains all 6 keys. The type system already guarantees this: `EndgameClass` and `EndgameClassKey` are isomorphic unions over the same six string literals (verified against `frontend/src/generated/endgameZones.ts:67-76`). So `bands` cannot be `undefined`, and `noUncheckedIndexedAccess` does not change that because the lookup uses a key drawn from the same literal union. The `!bands` short-circuit is dead code that conflates "no data" (`total === 0`) with "unknown class" (impossible by construction), and the comment instructs the reader to ignore one of the merged cases.

**Fix:** Drop the `!bands` check and the conditional empty-class shell merger. Keep `if (!hasGames) { /* empty shell */ }` and assert `bands` non-null with a non-null assertion (or destructure directly). If unknown-class robustness is wanted in case the type drifts in the future, log via Sentry rather than rendering a silent neutral gauge.

### WR-05: Missing `aria-label` on the WDL bar + missing landmark for the breakdown section

**File:** `frontend/src/components/charts/EndgameTypeCard.tsx:308-316`, `frontend/src/components/charts/EndgameTypeBreakdownSection.tsx:44`

**Issue:** Per CLAUDE.md's Browser Automation Rules (3) icon-only and chartlike elements should be labeled. The `MiniWDLBar` mount in the card has only `data-testid={`${tileTestId}-wdl`}`; there is no `aria-label` describing the per-class WDL distribution, so screen readers and automation tooling get nothing semantic. Similarly, `<section data-testid="endgame-type-breakdown-section">` has no `aria-label` / `aria-labelledby` despite being a top-level layout container (CLAUDE.md rule 4). The section heading lives in the parent (`Endgames.tsx:538`), so there is no in-section labelled landmark.

**Fix:** Add `aria-label={`${category.label} endgame win/draw/loss distribution`}` to the WDL bar wrapper, and `aria-labelledby` (or an explicit `aria-label`) on the section element. If the wrapping h2 lives in `Endgames.tsx`, give it an `id="endgame-type-breakdown-heading"` and reference it from the section's `aria-labelledby`.

### WR-06: Card lacks per-card `aria-label` despite being an interactive composite

**File:** `frontend/src/components/charts/EndgameTypeCard.tsx:262`

**Issue:** Each card root is `<div className="charcoal-texture rounded-md p-4" data-testid={tileTestId}>` with no `role`/`aria-label`. The card contains an interactive Games link, two popovers, and a bullet — assistive tech encounters a generic group with no name. The Games link's `aria-label` is the only labeling artifact in the card, and it only describes itself.

**Fix:** Add `role="group"` and `aria-label={`${category.label} endgame breakdown`}` to the card root. This is a recurring pattern in Phase 86's `EndgameMetricCard` — verify against that file and align.

## Info

### IN-01: `formatDiffPct` can disagree with the bullet `value` numerically

**File:** `frontend/src/lib/endgameMetrics.ts:55-58`; consumed in `EndgameTypeCard.tsx:354, 385, 430, 461`

**Issue:** `formatDiffPct(userR, oppR) = Math.round(userR*100) - Math.round(oppR*100)`. The bullet's `value={convDiff}` uses `userConv - oppConv` (a single round). So "Gap: +5%" can sit next to a bullet centered at +4.6% (rendered ~+5%) or +5.4% — the numeric Gap label and the bullet's pixel position can disagree by 1pp. The comment in `endgameMetrics.ts:50-54` documents this rationale, but the user-visible side effect is two different "+5%" / "+4%" reads on the same row.

**Fix:** Either round once at the display step (`Math.round((userR - oppR) * 100)`) so the bullet's value and the label match exactly, or pass the rounded integer diff into both the bullet and the label so the helper is the single source of truth. The current implementation guarantees "Gap = round(You) − round(Opp)" but breaks "Gap == round(bulletValue * 100)".

### IN-02: Magic number for gauge `size={130}` duplicated

**File:** `frontend/src/components/charts/EndgameTypeCard.tsx:205, 219, 283, 297`

**Issue:** `size={130}` is hard-coded four times in this file (twice in the empty shell, twice in the rendered card). Per CLAUDE.md "no magic numbers" guideline, extract to a named constant.

**Fix:**

```ts
const PER_TYPE_GAUGE_SIZE = 130;
```

at module scope and reference it at all four sites. Co-locate in `endgameMetrics.ts` only if another card needs it; otherwise keep it private to this file.

### IN-03: Description map for `pawnless` quietly dropped from public knowledge

**File:** `frontend/src/lib/endgameMetrics.ts:140-146`

**Issue:** `ENDGAME_TYPE_DESCRIPTIONS` excludes `pawnless` via `Exclude<EndgameClass, 'pawnless'>`, but `ENDGAME_CLASS_TO_SLUG` (lines 160-167) and `HIDDEN_ENDGAME_CLASSES` (line 175) all retain the entry. If the team ever re-enables pawnless (the comment in `endgameMetrics.ts:172-174` says classification stays in the DB so re-enabling is "without a reimport"), they will hit a missing description and a quiet fallback to `''` (see WR-03). The Phase 87 legacy lift (CONTEXT mentions `EndgameWDLChart.tsx:30-37`) included a pawnless description but it was dropped during the lift.

**Fix:** Re-add the pawnless description (`"Endgames with no pawns on the board, only kings and pieces."`) and widen the map type to `Record<EndgameClass, string>`. Cost is one extra entry; benefit is re-enable-safety + no type-cast at the call site. This also resolves WR-03 cleanly.

### IN-04: `EndgameTypeCard.test.tsx` "no inline color" assertion is fragile

**File:** `frontend/src/components/charts/__tests__/EndgameTypeCard.test.tsx:296`

**Issue:** `expect(diffSpan.style.color).toBe('')` asserts the inline `style.color` is the empty string. The implementation sets `convDiffStyle` to `undefined` when not paint-eligible (line 126-128), and React drops `style={undefined}`. This works today but is fragile — if the implementation switches to `style={{}}` (an empty object) the assertion fails despite no semantic change. The "is colored" branch on line 280 uses `toBeTruthy()` for symmetry; the "is not colored" branch should mirror that.

**Fix:** Use a stronger negative assertion: `expect(diffSpan.style.color).toBeFalsy()` or assert against the absence of the style attribute: `expect(diffSpan.getAttribute('style')).not.toMatch(/color:/)`.

---

## Fix Log

Post-review redesign on 2026-05-14: user reviewing the new section identified
that the Conv and Recov peer-bullets on each card always render the same
magnitude because they are computed from the same mirrored per-class WDL data
(mirror identity). Both bullets were replaced with a SINGLE chess-score
bullet per card using the exact pattern from the "Games with Endgame" card
(`EndgameOverallCard`). Conv and Recov gauges at the top of each card are
kept. The fix carries through to the backend (the 10 added Phase 87 schema
fields are reverted; a new `score_p_value` field is added to drive the
single bullet's sig-gating).

- **CR-01** — `d536b026` + `dec56649`. Obsoleted by design change. The Conv/Recov
  peer-bullets are removed entirely; the new per-card bullet is a chess-score
  bullet tested against 50% (Wilson score test), so the displayed metric and
  the test statistic are the same value by construction.
- **WR-01** — `31e082d1`. `Endgames.tsx` now passes `statsData.endgame_games`
  (not `total_games`) to `EndgameTypeBreakdownSection`. Each card's
  "Games: X%" reads as a share of the user's endgames.
- **WR-02** — `dec56649`. The `as number` casts on `oppConv`/`oppRecov` were
  on the now-removed Conv/Recov bullet rows. Removed with the bullets.
- **WR-03** — `dec56649`. The `as Exclude<EndgameClass, 'pawnless'>` cast in
  the title `InfoPopover` is gone; the new code uses an explicit
  `category.endgame_class !== 'pawnless'` guard.
- **WR-04** — `dec56649`. The dead `!bands` branch is dropped. The
  empty-class path is now solely `!hasGames`; the type system already
  guarantees bands presence for the 5 non-pawnless classes.
- **WR-05** — `31e082d1`. `EndgameTypeBreakdownSection` carries
  `aria-labelledby="endgame-type-breakdown-heading"`; the parent h2 in
  `Endgames.tsx` carries that id. The per-card `MiniWDLBar` mount picks up
  `aria-label="${label} win/draw/loss distribution"` (in `dec56649`).
- **WR-06** — `dec56649`. The card root now carries `role="group"` and
  `aria-label="${category.label} endgame breakdown"`.
- **IN-02** — `dec56649`. Hard-coded `size={130}` extracted to
  `const PER_TYPE_GAUGE_SIZE = 130` at module scope.

**Still open** (cleanup follow-ups):
- IN-01 — `formatDiffPct` rounding mismatch. Moot for the per-type card now
  (no diff label), but the helper still exists for callers outside Phase 87.
- IN-03 — `pawnless` description map. Not addressed; pawnless remains hidden.
- IN-04 — fragile `style.color === ''` assertion. The rewritten
  `EndgameTypeCard.test.tsx` uses `.toBeFalsy()` / `.toBeTruthy()` already
  (`65e0e2ba`), so the original concern is no longer present in the new test
  file, but other tests with the same pattern were not audited.

---

_Reviewed: 2026-05-14_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
_Fix log appended: 2026-05-14_
