---
phase: quick-9
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - app/services/stats_service.py
  - frontend/src/components/stats/RatingChart.tsx
autonomous: true
must_haves:
  truths:
    - "Global Stats page loads without 500 error and displays WDL data"
    - "Rating chart Y-axis adapts to data range with round-100 boundaries"
  artifacts:
    - path: "app/services/stats_service.py"
      provides: "Fixed outcome-to-key mapping in _aggregate_wdl"
      contains: "OUTCOME_KEY_MAP"
    - path: "frontend/src/components/stats/RatingChart.tsx"
      provides: "Adaptive YAxis domain with round-100 boundaries"
      contains: "domain"
  key_links: []
---

<objective>
Fix two phase 7 bugs: Global Stats 500 error caused by KeyError in _aggregate_wdl(), and Rating chart Y-axis starting at 0 instead of adapting to data range.

Purpose: Make the Global Stats and Rating pages functional and visually useful.
Output: Two fixed files, both bugs resolved.
</objective>

<execution_context>
@/home/aimfeld/.claude/get-shit-done/workflows/execute-plan.md
@/home/aimfeld/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@app/services/stats_service.py
@frontend/src/components/stats/RatingChart.tsx
@app/services/analysis_service.py (for derive_user_result return values)
</context>

<tasks>

<task type="auto">
  <name>Task 1: Fix _aggregate_wdl KeyError for "losss"</name>
  <files>app/services/stats_service.py</files>
  <action>
In `_aggregate_wdl()`, replace line 84's string concatenation `outcome + "s"` with a mapping dict lookup.

Add a module-level constant before the function:
```python
_OUTCOME_KEY_MAP = {"win": "wins", "draw": "draws", "loss": "losses"}
```

Replace line 84:
```python
counts[label_key][outcome + "s"] += 1
```
with:
```python
counts[label_key][_OUTCOME_KEY_MAP[outcome]] += 1
```

This properly maps "loss" -> "losses" instead of producing "losss".
  </action>
  <verify>
    <automated>cd /home/aimfeld/Projects/Python/chessalytics && uv run python -c "
from app.services.stats_service import _OUTCOME_KEY_MAP
assert _OUTCOME_KEY_MAP == {'win': 'wins', 'draw': 'draws', 'loss': 'losses'}
print('Mapping dict OK')
"</automated>
  </verify>
  <done>_aggregate_wdl uses mapping dict; "loss" correctly maps to "losses" key; no KeyError on Global Stats page.</done>
</task>

<task type="auto">
  <name>Task 2: Add adaptive Y-axis domain to RatingChart</name>
  <files>frontend/src/components/stats/RatingChart.tsx</files>
  <action>
Compute adaptive Y-axis domain from visible (non-hidden) chart data with round-100 boundaries.

Add a `useMemo` hook that:
1. Filters `data` to only include time controls NOT in `hiddenKeys`
2. Finds min and max rating from the filtered data points
3. Floors min to nearest 100 (e.g., 843 -> 800): `Math.floor(min / 100) * 100`
4. Ceils max to nearest 100 (e.g., 1847 -> 1900): `Math.ceil(max / 100) * 100`
5. Returns `[flooredMin, ceiledMax]` as the domain
6. Falls back to `['auto', 'auto']` if no visible data

Update `<YAxis />` on line 78 to use the computed domain:
```tsx
<YAxis domain={yDomain} />
```

The domain must react to legend toggle (hiddenKeys changes) so it recalculates when time controls are shown/hidden.
  </action>
  <verify>
    <automated>cd /home/aimfeld/Projects/Python/chessalytics/frontend && npx tsc --noEmit 2>&1 | head -20</automated>
  </verify>
  <done>YAxis domain adapts to visible data range with round-100 boundaries. Toggling legend items recalculates the domain. No TypeScript errors.</done>
</task>

</tasks>

<verification>
- Backend: `GET /stats/global` returns 200 with WDL data (no 500 error)
- Frontend: Rating chart Y-axis shows adaptive range (e.g., 800-1200) instead of starting from 0
- TypeScript compiles without errors
</verification>

<success_criteria>
- Global Stats page loads and displays WDL breakdown without errors
- Rating chart Y-axis uses round-100 boundaries adapted to data range
- Both fixes are minimal and targeted with no side effects
</success_criteria>

<output>
After completion, create `.planning/quick/9-some-fixes-for-phase-7/9-SUMMARY.md`
</output>
