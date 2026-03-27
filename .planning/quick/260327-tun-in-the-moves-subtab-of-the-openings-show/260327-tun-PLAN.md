---
phase: quick
plan: 260327-tun
type: execute
wave: 1
depends_on: []
files_modified:
  - frontend/src/components/move-explorer/MoveExplorer.tsx
autonomous: true
must_haves:
  truths:
    - "Moves with fewer than 10 games appear visually muted (reduced opacity)"
    - "Moves with 10+ games render at full opacity as before"
  artifacts:
    - path: "frontend/src/components/move-explorer/MoveExplorer.tsx"
      provides: "Muted styling for low-game-count moves"
  key_links:
    - from: "frontend/src/components/move-explorer/MoveExplorer.tsx"
      to: "frontend/src/lib/theme.ts"
      via: "imports MIN_GAMES_FOR_RELIABLE_STATS and UNRELIABLE_OPACITY"
      pattern: "MIN_GAMES_FOR_RELIABLE_STATS|UNRELIABLE_OPACITY"
---

<objective>
Mute move rows in the MoveExplorer (Moves subtab of Openings page) when their game count is below the MIN_GAMES_FOR_RELIABLE_STATS threshold (10 games).

Purpose: Visually signal to users that moves with very few games have unreliable WDL statistics, without hiding them entirely.
Output: Updated MoveExplorer.tsx with opacity-based muting for low-sample-size moves.
</objective>

<execution_context>
@.planning/quick/260327-tun-in-the-moves-subtab-of-the-openings-show/260327-tun-PLAN.md
</execution_context>

<context>
@frontend/src/components/move-explorer/MoveExplorer.tsx
@frontend/src/lib/theme.ts
@frontend/src/types/api.ts

<interfaces>
From frontend/src/lib/theme.ts:
```typescript
export const MIN_GAMES_FOR_RELIABLE_STATS = 10;
export const UNRELIABLE_OPACITY = 0.5;
```

From frontend/src/types/api.ts:
```typescript
export interface NextMoveEntry {
  move_san: string;
  game_count: number;
  wins: number;
  draws: number;
  losses: number;
  win_pct: number;
  draw_pct: number;
  loss_pct: number;
  transposition_count: number;
}
```
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Mute low-game-count move rows in MoveExplorer</name>
  <files>frontend/src/components/move-explorer/MoveExplorer.tsx</files>
  <action>
    1. Import MIN_GAMES_FOR_RELIABLE_STATS and UNRELIABLE_OPACITY from '@/lib/theme' (add to existing import).

    2. In the MoveRow component, compute whether the row is below threshold:
       ```typescript
       const isBelowThreshold = entry.game_count < MIN_GAMES_FOR_RELIABLE_STATS;
       ```

    3. Apply reduced opacity to the entire `<tr>` element when below threshold. Add an inline `style` with `opacity: UNRELIABLE_OPACITY` when `isBelowThreshold` is true. This mutes the move name, game count, AND the WDL bar together as a unit.

    4. Do NOT hide the rows or disable click interaction — moves should still be playable, just visually dimmed.

    5. Do NOT change the popover behavior — low-game-count rows should still show WDL tooltip on hover.
  </action>
  <verify>
    <automated>cd /home/aimfeld/Projects/Python/flawchess/frontend && npx tsc --noEmit 2>&1 | head -20</automated>
  </verify>
  <done>Move rows with game_count < 10 render at 50% opacity; rows with >= 10 games render at full opacity. All rows remain interactive.</done>
</task>

</tasks>

<verification>
- TypeScript compiles without errors
- Visual: On the Openings page Moves subtab, moves with fewer than 10 games appear dimmed
- Dimmed rows are still clickable and show WDL popover on hover
</verification>

<success_criteria>
Low-sample-size moves are visually distinguishable from reliable moves via reduced opacity, using existing theme constants.
</success_criteria>
