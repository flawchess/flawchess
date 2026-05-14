---
type: quick
description: Tighten Achievable Score Gap neutral band to ±5pp via a dedicated ACHIEVABLE_SCORE_GAP_* registry entry, keeping Endgame Score Gap at ±10pp.
files_modified:
  - app/services/endgame_zones.py
  - scripts/gen_endgame_zones_ts.py
  - frontend/src/generated/endgameZones.ts
  - frontend/src/components/charts/EndgameOverallScoreGapRow.tsx
  - frontend/src/components/charts/EndgameOverallPerformanceSection.tsx
autonomous: true
---

<objective>
Tighten the Achievable Score Gap (3.1.5) neutral band from ±10pp to ±5pp by introducing a dedicated `achievable_score_gap` entry in `ZONE_REGISTRY` and a separate `ACHIEVABLE_SCORE_GAP_NEUTRAL_MIN/MAX` TS export, so the gauge actually paints red/green for cohorts whose median sits inside the old ±10pp band (notably the 2400-cohort at +3.5pp). The Endgame Score Gap (3.1.6) row MUST keep its current ±10pp band — both rows currently share `SCORE_GAP_NEUTRAL_MIN/MAX` and a naive constant tweak would wrongly tighten 3.1.6 too.

**Justification (from reports/benchmarks-latest.md §3.1.5):** pooled benchmark IQR for `achievable_score_gap` is `[−3.9pp, +4.6pp]`, so ±5pp is a clean rounded fit. The collapse verdict notes a strong ELO ramp (d=0.62 keep-separate); single global ±5pp is a defensible interim, with per-ELO stratification deferred. §3.1.6 (Endgame Score Gap) is "collapse OK at ±10pp", so it must stay separate. The report explicitly offers two options ("tighten to ±5pp" OR "split into a dedicated `ACHIEVABLE_SCORE_GAP_*` module so 3.1.6 keeps ±10pp"); this plan implements the split, which lets us deliver both intents in one change.

Purpose: align gauge color thresholds with pooled benchmark IQR for 3.1.5 without regressing 3.1.6.
Output: one new `ZoneSpec` registry entry, two new TS-emitted constants, updated `ScoreGapRow` props + caller wiring.
</objective>

<context>
@app/services/endgame_zones.py
@scripts/gen_endgame_zones_ts.py
@frontend/src/generated/endgameZones.ts
@frontend/src/components/charts/EndgameOverallPerformanceSection.tsx
@frontend/src/components/charts/EndgameOverallScoreGapRow.tsx

<interfaces>
Current behaviour (lines from `EndgameOverallPerformanceSection.tsx`):
- `gapZoneColor(value)` (lines 47–51) reads module-level `SCORE_GAP_NEUTRAL_MIN/MAX` and is called for BOTH `achievableGapColor` (line 80) and `gapColor` (line 69).
- Both `<ScoreGapRow>` instances (lines 159–193 Achievable, 194–230 Endgame) plus both `<MetricStatPopover>` `neutralLower/neutralUpper` props (lines 179–180 and 215–216) reference the same shared constants.
- `ScoreGapRow` itself (`EndgameOverallScoreGapRow.tsx` lines 15–18, 71–72) imports `SCORE_GAP_NEUTRAL_MIN/MAX` and forwards them to `MiniBulletChart` as `neutralMin`/`neutralMax`. It does NOT currently accept these as props.

Required interface change: extend `ScoreGapRow` props to accept `neutralMin: number` and `neutralMax: number` (required, not optional — both call sites pass them after the refactor; making them optional with a default would re-introduce the shared-constant trap). The two consumers then pass the correct constants per row.

Codegen script anchor: `scripts/gen_endgame_zones_ts.py` lines 35–43 already pulls `_SCORE_GAP_SPEC = ZONE_REGISTRY["score_gap"]` and emits `SCORE_GAP_NEUTRAL_MIN/MAX` on lines 116–117. Mirror this pattern: add `_ACHIEVABLE_SCORE_GAP_SPEC = ZONE_REGISTRY["achievable_score_gap"]` near line 43 and emit `ACHIEVABLE_SCORE_GAP_NEUTRAL_MIN` / `ACHIEVABLE_SCORE_GAP_NEUTRAL_MAX` adjacent to the existing `SCORE_GAP_NEUTRAL_*` lines (around line 117). The constant-naming convention is mandatory (`*_NEUTRAL_MIN`/`*_NEUTRAL_MAX`, not `*_TYPICAL_LOWER`/`*_TYPICAL_UPPER`) to match the existing FE consumers' pattern.
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add achievable_score_gap registry entry + codegen the new TS constants</name>
  <files>app/services/endgame_zones.py, scripts/gen_endgame_zones_ts.py, frontend/src/generated/endgameZones.ts</files>
  <action>
1. In `app/services/endgame_zones.py`:
   - Extend the `MetricId` Literal alias to include `"achievable_score_gap"` (insert alphabetically near `"score_gap"`, with a brief comment: `# 260514 split-out — dedicated band so 3.1.5 can tighten without affecting 3.1.6`).
   - Add a new entry to `ZONE_REGISTRY` immediately AFTER the existing `"score_gap"` entry (keep the two cohort-aware gap metrics colocated): `"achievable_score_gap": ZoneSpec(typical_lower=-0.05, typical_upper=0.05, direction="higher_is_better")`. Include a docstring-style comment citing `reports/benchmarks-latest.md §3.1.5` and noting pooled IQR `[-3.9pp, +4.6pp]` rounded to ±5pp, plus a "per-ELO stratification deferred (d=0.62)" note so the next benchmark cycle has the context.
2. In `scripts/gen_endgame_zones_ts.py`:
   - After the existing `_SCORE_GAP_SPEC = ZONE_REGISTRY["score_gap"]` line, add `_ACHIEVABLE_SCORE_GAP_SPEC = ZONE_REGISTRY["achievable_score_gap"]`.
   - In `_render()`, immediately after the two `SCORE_GAP_NEUTRAL_*` export lines, emit two new exports: `ACHIEVABLE_SCORE_GAP_NEUTRAL_MIN` and `ACHIEVABLE_SCORE_GAP_NEUTRAL_MAX`, sourced from `_ACHIEVABLE_SCORE_GAP_SPEC.typical_lower` / `typical_upper`. Preserve trailing-zero formatting consistent with the existing line (Python's default float repr will emit `-0.05` / `0.05` — fine, matches existing `-0.1` / `0.1`).
3. Regenerate the TS mirror: run `uv run python scripts/gen_endgame_zones_ts.py`. Verify the generated file now contains both `SCORE_GAP_NEUTRAL_MIN/MAX = -0.1 / 0.1` (unchanged) and `ACHIEVABLE_SCORE_GAP_NEUTRAL_MIN/MAX = -0.05 / 0.05` (new). Do NOT hand-edit `frontend/src/generated/endgameZones.ts`.
  </action>
  <verify>
    <automated>uv run ty check app/ tests/ &amp;&amp; uv run pytest tests/ -x -q &amp;&amp; uv run python scripts/gen_endgame_zones_ts.py &amp;&amp; git diff --exit-code frontend/src/generated/endgameZones.ts || (echo "Re-run codegen; commit the regenerated TS file" &amp;&amp; false)</automated>
  </verify>
  <done>
- `ZONE_REGISTRY["achievable_score_gap"]` exists with `typical_lower=-0.05`, `typical_upper=0.05`, `direction="higher_is_better"`.
- `MetricId` includes `"achievable_score_gap"`.
- `ty` passes with zero errors.
- All existing backend tests still pass (no test currently asserts on the new metric_id, so this is a non-breaking addition).
- Regenerated `frontend/src/generated/endgameZones.ts` exports both `SCORE_GAP_NEUTRAL_*` (unchanged at ±0.1) and new `ACHIEVABLE_SCORE_GAP_NEUTRAL_*` at ±0.05.
- `git diff --exit-code` on the generated file shows no drift after re-running the codegen script.
  </done>
</task>

<task type="auto">
  <name>Task 2: Wire the new band into ScoreGapRow + EndgameOverallPerformanceSection</name>
  <files>frontend/src/components/charts/EndgameOverallScoreGapRow.tsx, frontend/src/components/charts/EndgameOverallPerformanceSection.tsx</files>
  <action>
1. **`EndgameOverallScoreGapRow.tsx`** — make the neutral band caller-controlled:
   - Remove the imports of `SCORE_GAP_NEUTRAL_MAX` and `SCORE_GAP_NEUTRAL_MIN` from `@/generated/endgameZones` (the row no longer owns the band choice).
   - Add two required props to `ScoreGapRowProps`: `neutralMin: number` and `neutralMax: number`. Include a JSDoc comment on each clarifying they're signed score-gap units in [−1, +1].
   - Forward them to `<MiniBulletChart>` as `neutralMin={neutralMin}` / `neutralMax={neutralMax}` (replacing the current hard-coded imports on lines 71–72).
   - Update the file-level docstring (lines 2–10) to remove the line that says both rows "share … the neutral band from `SCORE_GAP_NEUTRAL_MIN/MAX`" — they no longer do.

2. **`EndgameOverallPerformanceSection.tsx`** — wire each row to its own band:
   - Update the import from `@/generated/endgameZones` to pull in `ACHIEVABLE_SCORE_GAP_NEUTRAL_MAX`, `ACHIEVABLE_SCORE_GAP_NEUTRAL_MIN`, `SCORE_GAP_NEUTRAL_MAX`, `SCORE_GAP_NEUTRAL_MIN` (alphabetical, matches existing eslint-import order).
   - Replace `gapZoneColor(value: number)` (lines 47–51) with a parameterized helper:
     ```
     function gapZoneColor(value: number, neutralMin: number, neutralMax: number): string
     ```
     keeping the same `< neutralMin → ZONE_DANGER`, `>= neutralMax → ZONE_SUCCESS`, else `ZONE_NEUTRAL` logic. (Preferred over duplicating into `achievableGapZoneColor` — one helper, two call sites, no duplicate logic to keep in sync.) Update the function's doc comment to mention both rows feed it with their own band.
   - Update the two call sites:
     - Line 69 (`gapColor`): `gapZoneColor(scoreGap.score_difference, SCORE_GAP_NEUTRAL_MIN, SCORE_GAP_NEUTRAL_MAX)` — Endgame Score Gap stays at ±10pp.
     - Line 80 (`achievableGapColor`): `gapZoneColor(achievableGapValue, ACHIEVABLE_SCORE_GAP_NEUTRAL_MIN, ACHIEVABLE_SCORE_GAP_NEUTRAL_MAX)` — Achievable Score Gap moves to ±5pp.
   - Pass `neutralMin`/`neutralMax` to BOTH `<ScoreGapRow>` instances (now-required props):
     - Achievable row (lines 159–193): `neutralMin={ACHIEVABLE_SCORE_GAP_NEUTRAL_MIN} neutralMax={ACHIEVABLE_SCORE_GAP_NEUTRAL_MAX}`.
     - Endgame Score Gap row (lines 194–230): `neutralMin={SCORE_GAP_NEUTRAL_MIN} neutralMax={SCORE_GAP_NEUTRAL_MAX}`.
   - Update the two `<MetricStatPopover>` `neutralLower`/`neutralUpper` props to match each row's new band (Achievable popover lines 179–180 → use the new `ACHIEVABLE_*` constants; Endgame popover lines 215–216 → leave on `SCORE_GAP_*`). The popover quotes the band textually, so this matters for the tooltip narrative consistency.
   - Add a one-line code comment above the new `gapZoneColor` definition referencing the split rationale: `// 260514: Achievable (±5pp) and Endgame (±10pp) Score Gaps now use distinct bands — see reports/benchmarks-latest.md §3.1.5.`

3. **Tests** — run the frontend test suite. Existing fixtures in `frontend/src/components/charts/__tests__/EndgameOverallPerformanceSection.test.tsx` use achievable values `0.07`, `0.04`, `-0.15` and assert on rendered text (`+7%`, `+4%`, `-15%`) and CI whisker data attributes — none assert on inline `color`/`resultColor` for the Achievable row. Color assertions exist only for `score-value-yes` (the Card 3 Endgame Score, unrelated to this change). If any test fails, investigate and fix in this task before declaring done; do not add `// @ts-ignore` or `expect.any`.
  </action>
  <verify>
    <automated>cd frontend &amp;&amp; npm run build &amp;&amp; npm test -- --run</automated>
  </verify>
  <done>
- `ScoreGapRow` accepts `neutralMin`/`neutralMax` as required props; no longer imports from `@/generated/endgameZones`.
- `gapZoneColor` is parameterized and called twice with different bands.
- Achievable Score Gap row renders red below −5pp, green at/above +5pp, blue inside `[−5pp, +5pp]`.
- Endgame Score Gap row STILL renders red below −10pp, green at/above +10pp, blue inside `[−10pp, +10pp]` (regression-free).
- Both `MetricStatPopover` instances forward the correct per-row `neutralLower`/`neutralUpper` so tooltip narration matches the visible band.
- `npm run build` passes (TypeScript strict + `noUncheckedIndexedAccess`); `npm test -- --run` passes; knip stays clean (no dead exports introduced).
  </done>
</task>

</tasks>

<verification>
Run the full CI-equivalent locally before commit:
```
uv run ruff check . && uv run ruff format --check .
uv run ty check app/ tests/
uv run pytest -x -q
uv run python scripts/gen_endgame_zones_ts.py && git diff --exit-code frontend/src/generated/endgameZones.ts
cd frontend && npm run lint && npm run knip && npm run build && npm test -- --run
```
All commands must pass. Manual smoke (optional, not blocking): load the Endgames page locally with a benchmark user whose Achievable Score Gap lands in `[5pp, 10pp)` — under the old shared band that user saw "typical blue"; under the new split they should see "strong green" on the Achievable row while the Endgame row colors are unchanged.
</verification>

<success_criteria>
- Achievable Score Gap gauge paints red/green at the tightened ±5pp threshold; the 2400-cohort median (+3.5pp) still reads as "typical" but +5pp users now correctly read "above neutral", and the 800-cohort lower tail (−7pp p25) reads as "danger" (the original recommendation's intent).
- Endgame Score Gap gauge behavior is byte-identical to before: same ±10pp band, same color rules, same tooltip text.
- Single source of truth preserved: thresholds live only in `app/services/endgame_zones.py`; TS mirror is regenerated, never hand-edited; CI drift gate (`git diff --exit-code` on the generated file) is satisfied.
- No magic numbers: all four boundaries (±0.05, ±0.10) reach the UI through named imports from `@/generated/endgameZones`.
</success_criteria>

<output>
After completion, the next sensible commit is a single squash with message along the lines of:
```
feat(endgames): tighten Achievable Score Gap neutral band to ±5pp

Split the shared SCORE_GAP_NEUTRAL_* constant into per-row bands:
Achievable Score Gap moves to ±5pp (pooled benchmark IQR [-3.9pp, +4.6pp],
reports/benchmarks-latest.md §3.1.5); Endgame Score Gap stays at ±10pp
(§3.1.6 verdict: collapse OK at current band).
```
No CHANGELOG entry required for a `/gsd-quick` calibration tweak (per project CHANGELOG rules — "Skip this for /gsd-quick / /gsd-fast tasks that don't meaningfully change behavior"); however, this is a user-visible color-threshold change, so a one-line `### Changed` entry under `[Unreleased]` is defensible. Defer to the user at commit time.
</output>
