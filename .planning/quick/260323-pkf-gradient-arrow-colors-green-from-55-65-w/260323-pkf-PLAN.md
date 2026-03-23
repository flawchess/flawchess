---
phase: quick
plan: 260323-pkf
type: execute
wave: 1
depends_on: []
files_modified:
  - frontend/src/lib/arrowColor.ts
  - frontend/src/pages/Openings.tsx
autonomous: true
must_haves:
  truths:
    - "Arrow at 55% win rate is grey (gradient start)"
    - "Arrow at 65%+ win rate is full green"
    - "Arrow at 60% win rate is halfway between grey and green"
    - "Arrow at 45% win rate (55% loss) is grey (red gradient start)"
    - "Arrow at 35% win rate (65% loss) is full red"
    - "Hover variants follow same gradient with boosted lightness"
    - "Moves with fewer than 10 games remain grey regardless of win rate"
    - "Popover text describes gradient behavior instead of hard thresholds"
  artifacts:
    - path: "frontend/src/lib/arrowColor.ts"
      provides: "Gradient arrow color function"
    - path: "frontend/src/pages/Openings.tsx"
      provides: "Updated popover descriptions (desktop + mobile)"
  key_links:
    - from: "frontend/src/lib/arrowColor.ts"
      to: "frontend/src/pages/Openings.tsx"
      via: "getArrowColor import"
      pattern: "getArrowColor"
---

<objective>
Replace hard-threshold arrow coloring with gradual color transitions. Arrows should smoothly
transition from grey to green as win rate goes from 55% to 65%, and from grey to red as loss
rate goes from 55% to 65%. Update popover descriptions to match.

Purpose: More nuanced visual feedback — moves with 58% win rate should look different from 52%.
Output: Updated arrowColor.ts with gradient logic, updated Openings.tsx popover text.
</objective>

<execution_context>
@.planning/quick/260323-pkf-gradient-arrow-colors-green-from-55-65-w/260323-pkf-PLAN.md
</execution_context>

<context>
@frontend/src/lib/arrowColor.ts
@frontend/src/pages/Openings.tsx
@frontend/src/pages/Dashboard.tsx (also uses getArrowColor — no changes needed, just verify signature stays the same)
</context>

<interfaces>
<!-- Existing callers pass (winPct, lossPct, gameCount, isHovered) — signature must not change -->

From frontend/src/lib/arrowColor.ts:
```typescript
export function getArrowColor(winPct: number, lossPct: number, gameCount: number, isHovered: boolean): string;
```

Callers in Dashboard.tsx:88 and Openings.tsx:123:
```typescript
color: getArrowColor(entry.win_pct, entry.loss_pct, entry.game_count, isHovered),
```
</interfaces>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Implement gradient arrow color logic</name>
  <files>frontend/src/lib/arrowColor.ts, frontend/src/lib/arrowColor.test.ts</files>
  <behavior>
    - gameCount < 10 -> grey (unchanged)
    - winPct <= 55 and lossPct <= 55 -> grey (neutral zone)
    - winPct = 55 -> grey (gradient start, t=0)
    - winPct = 60 -> halfway between grey and green (t=0.5)
    - winPct >= 65 -> full green (t=1)
    - lossPct = 55 -> grey (gradient start, t=0)
    - lossPct = 60 -> halfway between grey and red (t=0.5)
    - lossPct >= 65 -> full red (t=1)
    - If both winPct > 55 and lossPct > 55 (rare edge case with high draw rate), prioritize whichever is higher
    - Hover variants: same gradient but with boosted lightness (0.6 for green/red ends, 0.9 for grey end)
    - Function signature unchanged: getArrowColor(winPct, lossPct, gameCount, isHovered): string
  </behavior>
  <action>
    Replace the discrete threshold logic in `getArrowColor` with oklch interpolation.

    The gradient approach:
    1. Keep `MIN_GAMES_FOR_COLOR = 10` guard — returns grey if below.
    2. Define gradient range constants: `GRADIENT_START = 55` (grey end), `GRADIENT_END = 65` (full color end).
    3. Compute `t` values for win and loss: `t = clamp((pct - GRADIENT_START) / (GRADIENT_END - GRADIENT_START), 0, 1)`.
    4. If both t_win > 0 and t_loss > 0, use whichever has higher t.
    5. Interpolate oklch components between grey and green/red based on t.
       - For green: lightness from 0.75 to 0.45, chroma from 0.01 to 0.16, hue from 260 to 145.
       - For red: lightness from 0.75 to 0.45, chroma from 0.01 to 0.17, hue from 260 to 25.
       - For hover: lightness endpoints shift to 0.9 (grey end) and 0.6 (color end).
    6. Return interpolated `oklch(L C H)` string.

    Remove the exported color constants (GREEN, GREY, RED, GREEN_HOVER, etc.) since they are only used in ChessBoard.tsx for the color sort order. Update the sort order in ChessBoard.tsx if needed — actually check first whether ChessBoard.tsx uses these constants. If it does, keep them exported or refactor the sort.

    Wait — checking: ChessBoard.tsx imports `GREEN, GREEN_HOVER, RED, RED_HOVER, GREY, GREY_HOVER` for arrow color sort order (green first, red second, grey last). With gradient colors, the sort must change to use the computed t values instead. However, ChessBoard only receives `BoardArrow[]` with a `color` string — it doesn't have access to t values.

    Two options:
    (a) Keep the named constants for the sort and classify gradient colors into buckets based on hue.
    (b) Add a `sortOrder` field to BoardArrow.

    Use option (a) — parse the hue from the oklch string in the sort comparator. Arrows with hue near 145 (green) sort first, hue near 25 (red) sort second, hue near 260 (grey) sort last. This avoids changing the BoardArrow interface.

    Actually simpler: the sort in ChessBoard.tsx uses a colorOrder map with exact string matches. Replace that with a function that extracts lightness and chroma from the oklch string to determine sort priority. Lower lightness + higher chroma = more saturated = sort first. Or just sort by chroma descending (more colorful arrows drawn first, grey last).

    Write a helper `arrowSortKey(color: string): number` that returns 0 for green-ish, 1 for red-ish, 2 for grey-ish based on parsed oklch hue and chroma. Export it from arrowColor.ts for use in ChessBoard.tsx.
  </action>
  <verify>
    <automated>cd /home/aimfeld/Projects/Python/flawchess/frontend && npx vitest run src/lib/arrowColor.test.ts</automated>
  </verify>
  <done>
    getArrowColor returns gradient oklch colors that smoothly transition from grey (at 55%) to full green/red (at 65%+). All test cases pass. Function signature unchanged. ChessBoard sort still works with gradient colors.
  </done>
</task>

<task type="auto">
  <name>Task 2: Update ChessBoard arrow sort and Openings popover text</name>
  <files>frontend/src/components/board/ChessBoard.tsx, frontend/src/pages/Openings.tsx</files>
  <action>
    **ChessBoard.tsx:**
    Update the arrow sort logic (around line 93-108) to use `arrowSortKey` from arrowColor.ts instead of the hardcoded colorOrder map. Import the new helper. The sort should still draw more colorful (green/red) arrows before grey ones, and within each color group, thicker arrows first.

    **Openings.tsx — two popover locations (desktop line ~261 and mobile line ~569):**
    Replace the current text describing hard thresholds with gradient description. Update BOTH the desktop and mobile popover (per CLAUDE.md: "always check mobile variants").

    Current text (at both locations):
    "The arrows on the board show the next moves from your games that match the current filter settings. Thicker arrows mean the move occurred more frequently. Colors indicate your results: green for high win rate (60%+), red for high loss rate (60%+), and grey otherwise. Moves with fewer than 10 games are always grey."

    New text (at both locations):
    "The arrows on the board show the next moves from your games that match the current filter settings. Thicker arrows mean the move occurred more frequently. Arrow colors gradually shift from grey to green as your win rate increases from 55% to 65%+, and from grey to red as your loss rate increases from 55% to 65%+. Moves with fewer than 10 games are always grey."
  </action>
  <verify>
    <automated>cd /home/aimfeld/Projects/Python/flawchess/frontend && npx tsc --noEmit && npm run build</automated>
  </verify>
  <done>
    ChessBoard sorts gradient arrows correctly (colorful first, grey last). Both desktop and mobile popovers describe the new gradient behavior. Build succeeds with no type errors.
  </done>
</task>

</tasks>

<verification>
1. `cd frontend && npx vitest run src/lib/arrowColor.test.ts` — unit tests pass
2. `cd frontend && npm run build` — no type errors, clean build
3. `cd frontend && npm run lint` — no lint errors
</verification>

<success_criteria>
- Arrow colors smoothly transition from grey to green (55% to 65% win rate) and grey to red (55% to 65% loss rate)
- Moves with < 10 games remain grey
- getArrowColor signature unchanged — Dashboard.tsx and Openings.tsx callers work without modification
- ChessBoard arrow sort handles gradient colors correctly
- Both desktop and mobile popovers describe the gradient behavior
- All tests pass, build succeeds, lint clean
</success_criteria>

<output>
After completion, create `.planning/quick/260323-pkf-gradient-arrow-colors-green-from-55-65-w/260323-pkf-SUMMARY.md`
</output>
