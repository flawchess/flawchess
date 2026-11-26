---
phase: 257-facepalm-rate-library-stats
reviewed: 2026-11-20T00:00:00Z
depth: standard
files_reviewed: 24
files_reviewed_list:
  - app/repositories/library_repository.py
  - app/schemas/library.py
  - app/services/blunder_check_rules.py
  - app/services/facepalm_score.py
  - app/services/library_service.py
  - frontend/src/components/analysis/FacepalmMoveChip.tsx
  - frontend/src/components/analysis/VariationTree.tsx
  - frontend/src/components/library/EvalChart.tsx
  - frontend/src/components/library/FacepalmBadgePopover.tsx
  - frontend/src/components/library/FacepalmChip.tsx
  - frontend/src/components/library/FacepalmExplanation.tsx
  - frontend/src/components/library/FacepalmShareChart.tsx
  - frontend/src/components/library/FlawCard.tsx
  - frontend/src/components/library/stats/ContextTagCards.tsx
  - frontend/src/components/library/stats/FacepalmCard.tsx
  - frontend/src/components/library/stats/GapPopover.tsx
  - frontend/src/components/library/stats/LibraryStatsSections.tsx
  - frontend/src/hooks/analysis/useAnalysisGemMarkers.ts
  - frontend/src/lib/facepalm.ts
  - frontend/src/lib/flawComparisonMeta.ts
  - frontend/src/lib/gapBar.ts
  - frontend/src/lib/theme.ts
  - frontend/src/types/library.ts
  - CHANGELOG.md
findings:
  critical: 0
  warning: 1
  info: 5
  total: 6
  necessity: 0
status: issues_found
---

# Phase 257: Code Review Report

**Reviewed:** 2026-11-20
**Depth:** standard
**Files Reviewed:** 24 source files (plus the listed backend and frontend tests, read as secondary)
**Status:** issues_found

## Summary

No blockers. I attacked the areas named in the brief and the implementation held up.

- **SQL/Python twin of the type.** `facepalm_type_sql` and `facepalm_type` read the same `_loss_sql`/`material_loss` and `_missed_sql`/`material_missed` pairs, and both apply `loss > 0 and loss >= missed`. The NULL branch, the tie rule and the no-material rule agree. `tests/services/test_facepalm_score.py` runs parity over every model shape and every aggregate input, including a tie row and a no-material row. It also checks the stored-fact path and that the type ignores the fitted coefficients.
- **User scoping.** `fetch_facepalm_share_counts` filters `GameFlaw.user_id` and `Game.user_id`, and takes its game set from `_filtered_games_base`. `fetch_facepalm_comparison` filters `GameFlaw.user_id`, and its game ids come from the user-scoped anchor via `.in_(select(...).correlate(None))`. `fetch_page_facepalm_scores` keeps `GameFlaw.user_id` plus `player_only_gate`. No route accepts a user id, so there is no IDOR path. Tests exist for both new aggregate queries.
- **D-06 (opponent scores stay aggregate-only).** Opponent scores enter only as `COUNT ... FILTER` columns in `fetch_facepalm_comparison`. The share counts, the chip queries and `query_flaws` stay on `player_only_gate`. The drill and the tag filters are untouched.
- **Paired-rate math.** The facepalm rows reuse `_paired_series`. Both sides are divided by the user's move count, and the anchor is shared with `fetch_flaw_comparison`. The share is pooled sum over sum, and `scored_counts` and `facepalm_counts` stay index-aligned with the rate lists. The `moves <= 0` skip happens before the appends.
- **Null handling and the 70% cut.** `_window_share` returns null below the floor, and the frontend treats a null share as a gap. `FACEPALM_STATS_MIN` (0.7) equals `70 / _FACEPALM_PCT_SCALE`, which is the High preset bound, and a test pins this.
- **Frontend types.** Under `noUncheckedIndexedAccess`, every `Record<FacepalmType, ...>` lookup is keyed by the literal union, so none can be undefined. Every surface requires score and type together (D-09).
- **Tooling.** `tsc -p tsconfig.app.json --noEmit`, `eslint` on the touched frontend paths, `npm run knip`, `ruff check app tests`, `ty check` and `check_function_size.py --fail-over-depth 4` are all clean.

The remaining findings are one copy-accuracy concern and a few small quality issues.

## Warnings

### WR-01: The "missed win" type and its copy claim material was won for rows with no such evidence

**File:** `app/services/facepalm_score.py:660` (type rule), `frontend/src/lib/facepalm.ts:414` (sentence), `frontend/src/lib/flawComparisonMeta.ts:470-475` (row hint and definition)
**Issue:** D-02 makes "missed win" the `else` branch. A row gets it when `loss <= 0`, or when `loss > 0` but `loss < missed`. Rows with no material in either line, or whose best line is unknown (`_missed_sql` returns 0.0 for an unknown best line, D-18), therefore get `missed_win`.

The UI states this as fact. The popover says "Missed win: the best move won material that was not taken." The row hint says "Facepalm blunders that passed up a material win." The "Missed wins" count in the stats card includes those rows too.

For a no-material or unknown-best-line row, the sentence has no support. The mirror case, "Allowed loss", is safe because it requires `loss > 0`. The rule is owner-locked, but the shipped wording over-claims relative to it. The prod share of such rows has not been measured. Seed line 107 raises coverage for the share, not for the type.

**Fix:** Measure, on prod or the benchmark DB, how many scored blunders at or above 0.7 are typed `missed_win` with `missed = 0` (no gain and no known best line). If the share is not negligible, either:
- soften the sentence to what the rule guarantees, for example `missed_win: 'the move did not lose material.'`, or
- keep the owner's wording and add a fallback sentence for the `missed = 0` case.

At minimum, record the measured share in the phase UAT so the owner confirms the wording against real data.

## Info

### IN-01: Doc comments left orphaned by insertion (three sites)

**File:** `frontend/src/lib/facepalm.ts:399-404`, `frontend/src/components/library/EvalChart.tsx:533-535`, `frontend/src/types/library.ts:570-577`
**Issue:** New declarations were inserted between an existing JSDoc and the item it documented.
- `facepalm.ts`: the "257 D-08: teal for a missed win ..." block now sits above the `/** 257 D-10: short type name ... */` block. It documents nothing, and `FACEPALM_TYPE_STYLE` has no doc.
- `EvalChart.tsx`: `/** Inline glyph matching the chart's flaw dot ... */` now sits directly above the `FacepalmTooltipLine` doc, so `MarkerGlyph` lost its doc.
- `types/library.ts`: `/** Analysis state of a game ... */` is separated from `AnalysisState` by the new `FacepalmType`.

A similar stale line is in `FacepalmChip.tsx:4-5`, which still says the chip is "Colored ... like the context TagChip". The chip is no longer neutral.
**Fix:** Move each comment back above its own declaration, and move the D-08 tint comment above `FACEPALM_TYPE_STYLE`.

### IN-02: The share chart's percent axis can show uneven, rounded tick labels

**File:** `frontend/src/components/library/FacepalmShareChart.tsx:36-46, 136-144`
**Issue:** The y domain is in share units, such as `[0.2, 0.3]`, and ticks are formatted with `Math.round(share * 100)`. Recharts' nice ticks over a 0.1-wide domain step by 0.025, so labels like 22.5 and 27.5 render as "23%" and "28%". That gives unevenly spaced, misleading labels. Wider domains are fine.
**Fix:** Plot percent values (multiply the data by 100 in a `useMemo`), or pass a `tickCount` or explicit `ticks` on whole-percent steps.

### IN-03: The share card duplicates the empty state when the timeline is empty

**File:** `frontend/src/components/library/stats/LibraryStatsSections.tsx:79-92`, `frontend/src/components/library/FacepalmShareChart.tsx:119-125`
**Issue:** When the selected TC has no trend points, `FlawTrendChart` shows "Not enough games to show a trend" and `FacepalmShareChart` renders a second card with "Not enough scored blunders to show a trend". The user gets two empty cards stacked.
**Fix:** In `FlawTimeline`, render the share chart only when `points.length >= 2`, or let the share card say nothing when the timeline above already shows its own fallback.

### IN-04: `FacepalmRow` and `ContextTagRow` are near-duplicates, and the chart ticks use a raw 12px font

**File:** `frontend/src/components/library/stats/FacepalmCard.tsx:44-72` against `ContextTagCards.tsx:31-56`; `FacepalmShareChart.tsx:135,140`
**Issue:**
- Both rows build the same `GapRow` plus `GapPopover`. They differ only in the meta table, `omitDirection` and `rangeNote`. This is quality debt, not a defect.
- `tick={{ fontSize: 12 }}` is below the `text-sm` floor in `frontend/CLAUDE.md`. It copies `FlawTrendChart`, which already does this. If the project keeps chart ticks at 12, the rule needs a charts exception. If not, both charts need a fix.

**Fix:** Optional. Extract a shared row helper parameterised by meta and popover props. Decide the chart tick size once, in a shared constant.

### IN-05: A shipped comment records an unfinished prod probe

**File:** `app/services/library_service.py:1117-1122`
**Issue:** The `FACEPALM_SHARE_MIN_SCORED` comment ends with "The prod probe is still pending (plan 07)". The 257-07 summary lists the probe as a human follow-up. Once merged, the comment stays and goes stale. The floor was also changed from the 20 in CONTEXT to 50, based on benchmark data only.
**Fix:** After the probe, replace the sentence with the measured result, or drop it from the code and keep it in the phase notes.

---

_Reviewed: 2026-11-20_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
