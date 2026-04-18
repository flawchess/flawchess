---
phase: 260418-nlh
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - frontend/src/components/charts/EndgameScoreGapSection.tsx
autonomous: true
requirements:
  - QUICK-260418-nlh
must_haves:
  truths:
    - "A fourth gauge labelled 'Endgame Skill' renders in the desktop gauge strip next to Conversion / Parity / Recovery"
    - "The Endgame Skill value equals the simple average of Conversion Win% (W/G), Parity Score% ((W+D/2)/G) and Recovery Save% ((W+D)/G), computed per-bucket with the same formulas as the existing userRate() helper"
    - "Buckets with games === 0 are excluded from the average; if all three buckets have 0 games the Endgame Skill gauge is not rendered (or renders in the opacity-50 disabled state consistent with the existing cards)"
    - "Gauge zones are red <45%, blue 45–55%, green >=55% — matching the parity gauge band for visual consistency"
    - "Mobile stacked layout shows a dedicated Endgame Skill card (gauge only, no WDL/You/Opp/Diff rows) at the bottom of the existing material cards"
    - "The info popover gains a new paragraph explaining the Endgame Skill metric: composite definition, typical ~52% blue-band midpoint, one-number summary usefulness, caveat that it's an aggregate of different rates, and that 0-games buckets are excluded"
    - "No magic numbers — new thresholds/zones reference theme constants (GAUGE_DANGER / GAUGE_NEUTRAL / GAUGE_SUCCESS)"
    - "No changes to the three existing gauges, the desktop table, or the existing mobile cards"
  artifacts:
    - path: "frontend/src/components/charts/EndgameScoreGapSection.tsx"
      provides: "Endgame Skill composite gauge (desktop strip + mobile card) and updated info popover"
      contains: "endgameSkill"
  key_links:
    - from: "EndgameScoreGapSection.tsx"
      to: "EndgameGauge.tsx"
      via: "<EndgameGauge value={...} label='Endgame Skill' zones={ENDGAME_SKILL_ZONES} />"
      pattern: "EndgameGauge.*Endgame Skill"
    - from: "EndgameScoreGapSection.tsx"
      to: "theme.ts"
      via: "import { GAUGE_DANGER, GAUGE_NEUTRAL, GAUGE_SUCCESS, type GaugeZone }"
      pattern: "ENDGAME_SKILL_ZONES"
    - from: "endgameSkill helper"
      to: "data.material_rows"
      via: "filters rows where games > 0, averages per-bucket rates"
      pattern: "endgameSkill\\("
---

<objective>
Add a fourth "Endgame Skill" gauge to `EndgameScoreGapSection.tsx` that summarises the user's endgame performance as the simple average of Conversion Win%, Parity Score% and Recovery Save%. The gauge appears at the end of the desktop gauge strip (preserving existing muscle memory as a summary reading) and as a dedicated bottom card in the mobile stack. The info popover gains a paragraph describing the new metric.

Purpose: Give users a one-number endgame summary that complements the three per-bucket gauges, making it easy to track overall endgame skill over time without reading three numbers.

Output:
- Updated `EndgameScoreGapSection.tsx` with a pure helper `endgameSkill()`, `ENDGAME_SKILL_ZONES` constants, a 4th gauge on desktop (`grid-cols-4`), a bottom "Endgame Skill" card on mobile, and expanded info popover content.
- No backend, type, or `EndgameGauge.tsx` changes.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@CLAUDE.md
@frontend/src/components/charts/EndgameScoreGapSection.tsx
@frontend/src/components/charts/EndgameGauge.tsx
@frontend/src/lib/theme.ts
@frontend/src/types/endgames.ts

<interfaces>
<!-- Key types and patterns extracted up-front so the executor does not need to explore the codebase. -->

From frontend/src/types/endgames.ts:
```typescript
export type MaterialBucket = 'conversion' | 'parity' | 'recovery';

export interface MaterialRow {
  bucket: MaterialBucket;
  label: string;
  games: number;
  win_pct: number;   // 0-100
  draw_pct: number;  // 0-100
  loss_pct: number;  // 0-100
  score: number;     // already 0-1, i.e. (W + D/2)/G
  opponent_score: number | null;
  opponent_games: number;
}

export interface ScoreGapMaterialResponse {
  endgame_score: number;
  non_endgame_score: number;
  score_difference: number;
  material_rows: MaterialRow[];
  // ...
}
```

From frontend/src/lib/theme.ts:
```typescript
export const GAUGE_DANGER: string;   // red
export const GAUGE_NEUTRAL: string;  // blue
export const GAUGE_SUCCESS: string;  // green
export interface GaugeZone { from: number; to: number; color: string; }
```

From frontend/src/components/charts/EndgameGauge.tsx:
```typescript
interface EndgameGaugeProps {
  value: number;        // 0..maxValue (we pass userR * 100)
  maxValue?: number;    // default 100
  label: string;        // used in aria-label and an inner testId
  zones?: GaugeZone[];  // default DEFAULT_GAUGE_ZONES
}
```

Existing per-bucket rate helper (userRate) in EndgameScoreGapSection.tsx (lines 129-133):
```typescript
function userRate(row: MaterialRow): number {
  if (row.bucket === 'conversion') return row.win_pct / 100;
  if (row.bucket === 'recovery') return (row.win_pct + row.draw_pct) / 100;
  return row.score; // parity
}
```

Existing desktop gauge strip (lines 227-252) uses `grid-cols-3` — must become `grid-cols-4`.
Existing mobile stack (lines 365-472) maps over material_rows; new Skill card is appended after that map as a sibling block.
Existing info popover (lines 171-214) is a `<div className="space-y-2">` with `<p>` and a `<ul>` — new paragraph goes inside the same div.
</interfaces>
</context>

<tasks>

<task type="auto" tdd="false">
  <name>Task 1: Add Endgame Skill metric (helper + zones + desktop gauge + mobile card + popover copy)</name>
  <files>frontend/src/components/charts/EndgameScoreGapSection.tsx</files>
  <behavior>
    All changes happen in this single file. No other files are touched.

    Computation contract (pure function added near the existing `userRate()`):
    - `endgameSkill(rows: MaterialRow[]): number | null`
    - Filters `rows` to those with `games > 0`.
    - For each remaining row, compute its per-bucket rate with the SAME formulas as `userRate()`:
        conversion → `win_pct / 100`
        recovery   → `(win_pct + draw_pct) / 100`
        parity     → `score`
    - Returns the simple arithmetic mean of those rates (on 0–1 scale).
    - Returns `null` when no rows have `games > 0`.
    - Must not double-count or reuse `userRate()` via .map on a partial record; iterate once over filtered rows.

    Zone contract:
    - New module-level constant `ENDGAME_SKILL_ZONES: GaugeZone[]`:
        `{ from: 0,    to: 0.45, color: GAUGE_DANGER }`
        `{ from: 0.45, to: 0.55, color: GAUGE_NEUTRAL }`
        `{ from: 0.55, to: 1.0,  color: GAUGE_SUCCESS }`
      Values come from imported theme constants — NO literal color strings.
      Include a short comment noting zones mirror the parity gauge band for consistency.

    Desktop strip:
    - Change `grid-cols-3` → `grid-cols-4` on the `lg:grid` gauge strip wrapper (keep `data-testid="endgame-gauge-strip"`).
    - AFTER the existing `.map()` of conversion/parity/recovery gauges, append a 4th `<div>` for Endgame Skill with `data-testid="endgame-gauge-skill"`.
    - Skill gauge is placed LAST (after Recovery) so existing users see the per-bucket gauges in their current order and read Skill as a summary on the right.
    - Compute `const skill = endgameSkill(data.material_rows);`. When `skill === null`, render the same wrapper with `opacity-50` styling and an `EndgameGauge value={0}` (mirrors the existing `row.games === 0 ? 'opacity-50' : undefined` pattern on table rows / cards). When `skill !== null`, render `<EndgameGauge value={skill * 100} label="Endgame Skill" zones={ENDGAME_SKILL_ZONES} />`.
    - Label shown above gauge: text `"Endgame Skill"` in the same `<div className="text-sm mb-1">` style as the other labels. No metric suffix (it's not a Score %).

    Mobile stack:
    - AFTER the existing `.map()` producing `material-card-*` cards (inside the `lg:hidden space-y-3` wrapper, before its closing `</div>`), append a dedicated Endgame Skill card:
        `data-testid="endgame-skill-card"`.
    - Visuals: same rounded-border styling as the existing cards, but card contents are minimal: a header row with the label `"Endgame Skill"` (styled like the existing `text-sm font-medium`), centered gauge below, and nothing else (no WDL bar, no You/Opp/Diff row, no bullet chart).
    - When `skill === null`, apply the `opacity-50` class to the card outer `<div>` (mirroring the existing pattern) and render the gauge with value 0.

    Info popover (existing `<div className="space-y-2">` inside the `InfoPopover`):
    - APPEND (do not replace) a new `<p>` paragraph at the end of the existing content that explains Endgame Skill. Content must convey:
        1. What it is: simple average of Conversion Win%, Parity Score% and Recovery Save%.
        2. Typical value: around 52% based on FlawChess data, which is why the blue band is 45–55% (mirrors the Parity gauge band for consistency).
        3. Why useful: one-number endgame-skill summary that's easy to track over time alongside filters.
        4. Caveat: because the three inputs measure different things (Win% / Score% / Save%), the result is an aggregate, not a true chess score %; colors are comparable to Parity but the number is not.
        5. If a bucket has no games, it's excluded from the average.
      Use `<strong>Endgame Skill</strong>` in the same style as existing bold-term usage in the popover. Keep em-dashes sparse (CLAUDE.md style rule) — prefer commas / periods.

    Constraints (CLAUDE.md):
    - Use theme constants only — no literal color strings, no bare numeric zone boundaries outside the `ENDGAME_SKILL_ZONES` array.
    - `data-testid`s must be `endgame-gauge-skill` (desktop) and `endgame-skill-card` (mobile). These match the naming patterns for the existing buckets.
    - Do NOT touch EndgameGauge.tsx, theme.ts, or endgames.ts — all existing constants and types are sufficient.
    - Do NOT change the three existing gauges, desktop table, or existing mobile cards.
    - `noUncheckedIndexedAccess`: `data.material_rows` is already typed as `MaterialRow[]`, and `endgameSkill()` operates via `.filter` + `.map` + `.reduce` (no index access), so no narrowing is required. If any index access is introduced, narrow via a local variable.
    - Keep the helper `endgameSkill` at module scope alongside `userRate` / `opponentRate` for symmetry.
  </behavior>
  <action>
    Edit `frontend/src/components/charts/EndgameScoreGapSection.tsx` in place:

    1. Add the `ENDGAME_SKILL_ZONES` constant directly after `FIXED_GAUGE_ZONES` (line ~95). Reuse the existing `GAUGE_DANGER / GAUGE_NEUTRAL / GAUGE_SUCCESS` imports (already imported on line 26-28).
    2. Add the `endgameSkill(rows: MaterialRow[]): number | null` pure helper directly after the existing `userRate` function (line ~133). Implement as:
       `const active = rows.filter(r => r.games > 0);`
       `if (active.length === 0) return null;`
       then map each active row to its per-bucket rate (duplicating the `userRate` per-bucket formula inline, or constructing a synthetic rate object — planner note: duplicating the small if/else inline is clearest and avoids an extra helper layer).
       Return `sum / active.length`.
    3. In the desktop gauge strip block (~line 227-252), change `grid-cols-3` to `grid-cols-4`. After the `.map(...)` closing `)` but before the strip's closing `</div>`, append a 4th gauge wrapper:
         - outer `<div>` with `key="skill"`, `className="flex flex-col items-center"` plus `opacity-50` when `skill === null`, and `data-testid="endgame-gauge-skill"`.
         - inner label `<div className="text-sm mb-1">Endgame Skill</div>`.
         - `<EndgameGauge value={(skill ?? 0) * 100} label="Endgame Skill" zones={ENDGAME_SKILL_ZONES} />`.
    4. In the mobile cards block (~line 365-472), after the `.map(...)` closing brace and before the wrapper's closing `</div>`, append the skill card:
         - outer `<div className={'rounded border border-border p-3 space-y-2' + (skill === null ? ' opacity-50' : '')} data-testid="endgame-skill-card">`.
         - header row `<div className="flex items-baseline justify-between"><div className="text-sm font-medium">Endgame Skill</div></div>`.
         - centered gauge `<div className="flex justify-center"><EndgameGauge value={(skill ?? 0) * 100} label="Endgame Skill" zones={ENDGAME_SKILL_ZONES} /></div>`.
         - no WDL bar, no You/Opp/Diff row, no bullet chart.
    5. Compute `const skill = endgameSkill(data.material_rows);` once at the top of the component body (near the existing `totalMaterialGames` computation on line 155) so both desktop and mobile blocks reuse the same value.
    6. Inside the `InfoPopover` children (`<div className="space-y-2">` starting line 171), APPEND a new `<p>` paragraph as the last child explaining the Endgame Skill metric per the behavior contract above. Place it AFTER the existing "Hidden when the opponent sample is smaller than 10 games." paragraph. Do not remove or reorder existing content.
    7. Run the lint/type/test commands below. Fix any ty / TypeScript errors before declaring done.
  </action>
  <verify>
    <automated>cd frontend && npm run lint && npx tsc --noEmit && npm test -- --run EndgameScoreGapSection 2>/dev/null; TEST_EXIT=$?; npm run knip; if [ $TEST_EXIT -ne 0 ] && [ $TEST_EXIT -ne 1 ]; then echo "unexpected test runner exit: $TEST_EXIT"; exit $TEST_EXIT; fi; echo "OK"</automated>
  </verify>
  <done>
    - `npm run lint` passes with zero errors.
    - `npx tsc --noEmit` passes with zero errors (respects `noUncheckedIndexedAccess`).
    - `npm run knip` reports no new unused exports or dependencies.
    - Visual check (human at the end): on a user with non-zero endgame games, the desktop Endgames page shows four gauges in a row (Conversion / Parity / Recovery / Endgame Skill). Skill value equals the arithmetic mean of the three displayed percentages (rounded, ±1pp tolerance from rounding). Zones are red <45 / blue 45-55 / green >=55. Mobile shows three per-bucket cards then a final Endgame Skill card with only the gauge.
    - Info popover now contains a trailing paragraph about Endgame Skill with the bold term, the ~52% typical value, the composite-aggregate caveat, and the 0-games exclusion note.
    - No changes to any file other than `EndgameScoreGapSection.tsx`.
  </done>
</task>

</tasks>

<verification>
1. Lint + type check: `cd frontend && npm run lint && npx tsc --noEmit` must both pass.
2. Dead-code check: `cd frontend && npm run knip` must pass (the new `endgameSkill` helper and `ENDGAME_SKILL_ZONES` constant are module-local, so knip should not flag them).
3. Manual UI check on desktop + mobile viewport:
   - Desktop: four gauges render in a row via `grid-cols-4`, no layout overflow.
   - Mobile: four stacked cards, Endgame Skill last with only the gauge.
   - All four gauges have correct `data-testid`s (`endgame-gauge-conversion`, `endgame-gauge-parity`, `endgame-gauge-recovery`, `endgame-gauge-skill`) and the mobile cards include `endgame-skill-card`.
4. Value sanity: on a user with healthy endgame data, Skill ≈ mean of the other three displayed percents. Zones clearly red/blue/green at the boundary cases.
5. Info popover: open via the (i) icon next to the section heading; new paragraph is visible at the bottom, describes composite metric + ~52% typical + blue band justification + 0-games exclusion.
</verification>

<success_criteria>
- Desktop and mobile both render the new "Endgame Skill" gauge with correct `data-testid`s.
- `endgameSkill()` returns a 0-1 value equal to the simple mean of per-bucket rates over buckets with `games > 0`, or `null` when all are 0.
- Zone boundaries 0.45 / 0.55 are encoded in `ENDGAME_SKILL_ZONES` using `GAUGE_DANGER / GAUGE_NEUTRAL / GAUGE_SUCCESS` — no literal colors.
- Info popover has a new paragraph covering definition, typical value, usefulness, caveat, and 0-games exclusion.
- Lint, type check, and knip all pass. No unrelated files touched.
</success_criteria>

<output>
After completion, create `.planning/quick/260418-nlh-add-endgame-skill-metric-as-simple-avera/260418-nlh-SUMMARY.md` describing:
- The helper + zones added.
- Confirmed 4-gauge desktop / 4-card mobile layout.
- Popover copy added.
- Anything unexpected (e.g. mobile-card styling decisions if the executor chose something different, test file added if any).
</output>
