---
phase: quick
plan: 260326-qhw
type: execute
wave: 1
depends_on: []
files_modified:
  - app/schemas/endgames.py
  - app/services/endgame_service.py
  - frontend/src/types/endgames.ts
  - frontend/src/components/charts/EndgameWDLChart.tsx
  - tests/test_endgame_service.py
autonomous: true
requirements: []
---

<objective>
Fix endgame conversion/recovery sub-bars to show full W/D/L breakdown (3 segments) instead of the current 2-segment bars.

Purpose: Currently conversion bars lump draws into losses, and recovery bars lump wins into draws. Both should show green/grey/red segments like the main WDL bars.
Output: Backend returns granular W/D/L counts for both conversion and recovery; frontend renders 3-segment mini-bars.
</objective>

<context>
@app/schemas/endgames.py
@app/services/endgame_service.py
@frontend/src/types/endgames.ts
@frontend/src/components/charts/EndgameWDLChart.tsx
@tests/test_endgame_service.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add granular W/D/L fields to backend schema and service</name>
  <files>app/schemas/endgames.py, app/services/endgame_service.py, tests/test_endgame_service.py</files>
  <action>
**app/schemas/endgames.py — ConversionRecoveryStats:**
Add new fields (keep existing fields for backward compat):
- `conversion_draws: int` — draws when up material
- `conversion_losses: int` — losses when up material (= conversion_games - conversion_wins - conversion_draws)
- `recovery_wins: int` — wins when down material
- `recovery_draws: int` — draws when down material

**app/services/endgame_service.py — _aggregate_endgame_stats():**

1. Change `conv` accumulator from `{"games": 0, "wins": 0}` to `{"games": 0, "wins": 0, "draws": 0}`.
   In the loop, when `user_material_imbalance > 0` and `outcome == "draw"`, increment `conv[endgame_class]["draws"]`.

2. Change `recov` accumulator from `{"games": 0, "saves": 0}` to `{"games": 0, "wins": 0, "draws": 0}`.
   In the loop, when `user_material_imbalance < 0`:
   - If `outcome == "win"`: increment `recov["wins"]`
   - If `outcome == "draw"`: increment `recov["draws"]`
   Remove the combined "saves" increment — compute `recovery_saves = wins + draws` when building the schema object (to keep `recovery_saves` field working).

3. When constructing `ConversionRecoveryStats`, pass the new fields:
   - `conversion_draws=conv_data["draws"]`
   - `conversion_losses=conversion_games - conversion_wins - conv_data["draws"]`
   - `recovery_wins=recov_data["wins"]`
   - `recovery_draws=recov_data["draws"]`
   - `recovery_saves=recov_data["wins"] + recov_data["draws"]` (derived, keeps existing field correct)

**tests/test_endgame_service.py:**
Update `test_conversion_pct_per_category` — add a draw row (e.g. game_id=4, rook, up, draw "1/2-1/2") and assert:
- `conversion_draws == 1`
- `conversion_losses == 1` (the existing lost game)
- `conversion_wins == 1` (the existing won game)
- `conversion_games == 3`

Update `test_recovery_pct_per_category` — verify `recovery_wins` and `recovery_draws` are split correctly from the existing test rows (game 1 is "1-0" white down = win, game 2 is "1/2-1/2" = draw, game 3 is "0-1" white down = loss):
- `recovery_wins == 1`
- `recovery_draws == 1`
- `recovery_saves == 2` (still correct)
  </action>
  <verify>
    <automated>cd /home/aimfeld/Projects/Python/flawchess && uv run pytest tests/test_endgame_service.py -x -v</automated>
  </verify>
  <done>ConversionRecoveryStats schema has conversion_draws, conversion_losses, recovery_wins, recovery_draws fields. Service populates them correctly. All endgame service tests pass.</done>
</task>

<task type="auto">
  <name>Task 2: Update frontend types and render 3-segment conversion/recovery bars</name>
  <files>frontend/src/types/endgames.ts, frontend/src/components/charts/EndgameWDLChart.tsx</files>
  <action>
**frontend/src/types/endgames.ts — ConversionRecoveryStats:**
Add fields mirroring backend:
- `conversion_draws: number`
- `conversion_losses: number`
- `recovery_wins: number`
- `recovery_draws: number`

**frontend/src/components/charts/EndgameWDLChart.tsx:**

1. Update the `CategoryData` interface to include the new fields: `conversion_draws`, `conversion_losses`, `recovery_wins`, `recovery_draws`.

2. Update the data mapping in `EndgameWDLChart` to pass the new fields from `cat.conversion.*`.

3. In `EndgameCategoryRow`, replace the 2-segment bar calculations:

**Conversion bar** (currently `convWinPct`/`convLossPct` — 2 segments):
```typescript
const convWinPct = cat.conversion_games > 0 ? (cat.conversion_wins / cat.conversion_games) * 100 : 0;
const convDrawPct = cat.conversion_games > 0 ? (cat.conversion_draws / cat.conversion_games) * 100 : 0;
const convLossPct = cat.conversion_games > 0 ? (cat.conversion_losses / cat.conversion_games) * 100 : 0;
```

**Recovery bar** (currently `recvSavePct`/`recvLossPct` — 2 segments):
```typescript
const recvWinPct = cat.recovery_games > 0 ? (cat.recovery_wins / cat.recovery_games) * 100 : 0;
const recvDrawPct = cat.recovery_games > 0 ? (cat.recovery_draws / cat.recovery_games) * 100 : 0;
const recvLosses = cat.recovery_games - cat.recovery_wins - cat.recovery_draws;
const recvLossPct = cat.recovery_games > 0 ? (recvLosses / cat.recovery_games) * 100 : 0;
```

4. Update the conversion bar JSX to render 3 segments:
```tsx
{convWinPct > 0 && <div style={{ width: `${convWinPct}%`, backgroundColor: WDL_WIN }} />}
{convDrawPct > 0 && <div style={{ width: `${convDrawPct}%`, backgroundColor: WDL_DRAW }} />}
{convLossPct > 0 && <div style={{ width: `${convLossPct}%`, backgroundColor: WDL_LOSS }} />}
```

5. Update the recovery bar JSX to render 3 segments:
```tsx
{recvWinPct > 0 && <div style={{ width: `${recvWinPct}%`, backgroundColor: WDL_WIN }} />}
{recvDrawPct > 0 && <div style={{ width: `${recvDrawPct}%`, backgroundColor: WDL_DRAW }} />}
{recvLossPct > 0 && <div style={{ width: `${recvLossPct}%`, backgroundColor: WDL_LOSS }} />}
```
  </action>
  <verify>
    <automated>cd /home/aimfeld/Projects/Python/flawchess/frontend && npm run build</automated>
  </verify>
  <done>Conversion and recovery mini-bars show 3 segments (green/grey/red) matching the main WDL bar style. TypeScript compiles without errors.</done>
</task>

</tasks>

<verification>
- `uv run pytest tests/test_endgame_service.py -x -v` — all tests pass
- `cd frontend && npm run build` — no TS errors
- Visual: open endgame stats, expand "More" on a category with conversion/recovery data, confirm bars show 3 colored segments
</verification>

<success_criteria>
- Conversion bars show Win (green) / Draw (grey) / Loss (red) segments
- Recovery bars show Win (green) / Draw (grey) / Loss (red) segments
- Percentage labels remain unchanged (conversion = win rate, recovery = save rate)
- All backend tests pass with the new granular fields
</success_criteria>

<output>
After completion, create `.planning/quick/260326-qhw-fix-endgame-conversion-recovery-wdl-bars/260326-qhw-SUMMARY.md`
</output>
