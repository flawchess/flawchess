# Phase 260: Facepalm as a First-Class Move Quality - Pattern Map

**Mapped:** 2026-11-22
**Files analyzed:** ~22 (from RESEARCH.md "Recommended file touch list", lines 556-574)
**Analogs found:** all files have an in-file or neighbouring analog. No file lacks one.

## File Classification

| File | Role | Data Flow | Closest Analog | Match |
|------|------|-----------|----------------|-------|
| `app/repositories/library_repository.py` | repository | CRUD/filter | own `_facepalm_clause` (350-375) + severity block (712-718) | exact |
| `app/repositories/query_utils.py` | utility | filter | own `cast(Sequence[FlawSeverity], ...)` (414-421) | exact |
| `app/services/library_service.py` | service | request-response | existing `flaw_severity` threading | exact |
| `app/routers/library.py` | router | request-response | `SeverityFilter` Literal (35-38) + `severity: list[SeverityFilter]` params (72, 185, 233, 287, 331, 389) | exact |
| `tests/repositories/test_library_repository.py` | test | DB | `_seed_non_tactic_flaw` (286-316) | exact |
| `frontend/src/types/library.ts` | types | - | existing `FlawSeverity` union | exact |
| `frontend/src/lib/moveStatsCounts.ts` | utility | transform | `severityCountsBySide` (47-61) | exact |
| `frontend/src/lib/__tests__/moveStatsCounts.test.ts` | test | - | own `marker()` factory (5-18) | exact |
| `frontend/src/lib/flawDotColor.ts` (new, optional) | utility | transform | `frontend/src/lib/bestMoveDot.ts` `bestMoveDotSpec` (62-77) | role-match |
| `frontend/src/components/library/MoveStats.tsx` | component | render | `CATEGORY_ORDER` / `CATEGORY_LABELS` / `SEVERITY_CATEGORIES` (44-65) | exact |
| `frontend/src/components/icons/MoveQualityIcon.tsx` | component | render | `SEVERITY_QUALITIES` / `isSeverityQuality` (25-28, 62-66) | exact |
| `frontend/src/components/results/LibraryGameCard.tsx` | component | render | `facepalmPlies` (303-311), `categoryPlies` (432-446), `DESKTOP_BOARD_SIZE` (82) | exact |
| `frontend/src/components/analysis/AnalysisTagsPanel.tsx` | component | render | own `categoryPlies` (176-185), same as LibraryGameCard | exact |
| `frontend/src/components/library/EvalChart.tsx` | component | render | `severityColor` (289-293), dot loop (441-447) | exact |
| `frontend/src/components/filters/FlawFilterControl.tsx` | component | event | `SEVERITY_BUTTONS` (120-133), render (590-605) | exact |
| `frontend/src/components/filters/FacepalmFilter.tsx` | component | - | delete | n/a |
| `frontend/src/components/filters/__tests__/FlawFilterControl.test.tsx` | test | - | FacepalmFilter tests at 8, 528-746 to remove | n/a |
| `frontend/src/lib/theme.ts` | config | - | `SEV_*` / `SEV_*_BG` (66-78), `SEV_FACEPALM` (527) | exact |
| `frontend/src/lib/facepalm.ts` | utility | - | `isFacepalmBlunder` (173-175); range/preset exports (70-160) to delete | exact |
| `useFlawFilterStore.ts`, `useLibrary.ts`, `api/client.ts`, `analytics.ts`, `pages/library/{GamesTab,FlawsTab}.tsx` | hooks/pages | request-response | existing `facepalm` / `facepalmToQueryParams` plumbing (removal) | exact |
| `frontend/src/components/library/SeverityBadge.tsx` | component | render | existing badge (conditional) | exact |

## Pattern Assignments

### `app/routers/library.py` (router)
Analog: `app/routers/library.py:35-38`
```python
# The Games/Flaws filter offers only the mistake/blunder severity tiers
# ...
SeverityFilter = Literal["mistake", "blunder"]
```
Change it to `SeverityFilter = FlawSeverityFilter`, imported from `library_repository`. Leave the `severity: list[SeverityFilter] | None = Query(default=None)` params at 72/185/233/287/331/389 as they are, along with `flaw_severity=list(severity) if severity else None` (133, 220, 274, 318, 376) and `severity=list(severity) if severity else []` (442). Remove the `min_facepalm_pct`/`max_facepalm_pct` Query params (D-13).

### `app/repositories/library_repository.py` (repository)
- New `FlawSeverityFilter = Literal["facepalm","blunder","mistake"]` plus a values tuple. The Literal shape is the router one above.
- `_severity_clause` should copy the style of `_facepalm_clause` (350-375): a docstring citing the D-ids, an early `return None` when nothing is selected, and the caller-bound `score` parameter defaulting to `facepalm_expr(FACEPALM_LIBRARY_LAMBDA)`. Collect the branches in a `list[ColumnElement[bool]]` and keep `score.isnot(None)` / float thresholds (`score >= X / _FACEPALM_PCT_SCALE`). RESEARCH.md 594-640 has the full draft.
- It replaces `library_repository.py:712-718`:
```python
if severity:
    clauses.append(GameFlaw.severity.in_([_SEVERITY_INT[s] for s in severity]))
```
- Builder signature (647-657): `severity: Sequence[FlawSeverityFilter]`. Drop `min_facepalm_pct`/`max_facepalm_pct` but keep `facepalm_score`. Delete `facepalm_range_active` (340-347) and `_facepalm_clause`, plus the call at 764-766. Keep the `_SEVERITY_INT["blunder"]` lookup style (no f-strings, per the header at line 11).

### `app/repositories/query_utils.py` (utility)
Analog at 414-421:
```python
if flaw_severity or flaw_tags or tactic_active or facepalm_active:
    severities = cast(Sequence[FlawSeverity], flaw_severity or [])
```
Change the cast target to `FlawSeverityFilter` and drop `facepalm_active`. The param at 185 is `Sequence[str]` and can stay, or be narrowed.

### `app/services/library_service.py` (service)
Change `get_library_flaws` severity param and `_DEFAULT_SEVERITY` to `FlawSeverityFilter`, and drop the range pass-through. This mirrors the router/repo threading.

### `tests/repositories/test_library_repository.py` (test)
Analog `_seed_non_tactic_flaw` at 286-316:
```python
async def _seed_non_tactic_flaw(session, *, user_id, game_id, ply, severity: int = 2,
                                facepalm_target: float | None = None) -> None:
    ...
    **facepalm_fact_columns(facepalm_target, lam=FACEPALM_LIBRARY_LAMBDA),
```
New tag tests should seed blunders above and below the cut, plus an unscored one (`facepalm_target=None`), and then assert that facepalm, blunder, blunder+facepalm and mistake each select the right rows. Add finally-cleanup per the eval-lottery isolation memory.

### `frontend/src/lib/moveStatsCounts.ts` (utility, transform)
Analog at 19 and 47-61:
```ts
export type MoveStatCategory = 'gem' | 'great' | 'best' | 'good' | 'inaccuracy' | 'mistake' | 'blunder';
...
for (const m of markers) {
  const side = moverColorAtPly(m.ply);
  out[side][m.severity]++;
}
```
Add `flawMoveCategory()` (RESEARCH.md 580-591), have `emptySeverityCounts()` (28-30) include `facepalm: 0`, and change the loop to `out[side][flawMoveCategory(m)]++`. Import `isFacepalmBlunder` from `@/lib/facepalm` (173-175).

### `frontend/src/lib/__tests__/moveStatsCounts.test.ts` (test)
Reuse the `marker(overrides)` factory at lines 5-18 and add `facepalm_score` to the overrides. Cover the facepalm and blunder split at the `FACEPALM_HIGH_CUTOFF` boundary, and the null case.

### `frontend/src/lib/flawDotColor.ts` (new) or inline in `EvalChart.tsx`
Analog `bestMoveDot.ts:62-77`: a pure exported function of `(point, highlightedPlies?, userColor?)` that returns a spec or null and uses only theme constants. Unit-test it the same way `EvalChart.test.tsx` covers `bestMoveDotSpec`. Current colour switch at `EvalChart.tsx:289-293`:
```ts
function severityColor(sev: FlawSeverity): string {
  if (sev === 'blunder') return SEV_BLUNDER;
  if (sev === 'mistake') return SEV_MISTAKE;
  return SEV_INACCURACY;
}
```
Make it `(marker) => category === 'facepalm' ? SEV_FACEPALM : ...` via `flawMoveCategory`. Call site at 444: `const color = severityColor(marker.severity);`. The tooltip should use the same classifier.

### `frontend/src/components/library/MoveStats.tsx` (component)
Analog at 44-65. Add `'facepalm'` to `CATEGORY_ORDER` after `'blunder'` (per CONTEXT row order), add `facepalm: 'Facepalm'` to `CATEGORY_LABELS` plus the popover copy entry (around 102), and move the "7 rows" comment and count constant to 8. `SEVERITY_CATEGORIES` gets the facepalm member, or switches to the FlawMoveCategory list. `countFor` (210) reads the extended counts.

### `frontend/src/components/icons/MoveQualityIcon.tsx`
`MoveQuality` must accept `'facepalm'`. Follow the `SEVERITY_QUALITIES`/`isSeverityQuality` branch (25-28, 63-64) with the existing "???" glyph used by the card corner badge and `SEV_FACEPALM`.

### `LibraryGameCard.tsx` / `AnalysisTagsPanel.tsx` (component)
Current code, the same in both files (`LibraryGameCard.tsx:443-444`, `AnalysisTagsPanel.tsx:184-185`):
```ts
for (const fm of game.flaw_markers ?? []) {
  push(fm.severity, moverColorAtPly(fm.ply), fm.ply);
}
```
Change it to `push(flawMoveCategory(fm), ...)`. Rewrite `facepalmPlies` (LibraryGameCard 303-311, `fm.severity === 'blunder' && isFacepalmBlunder(fm.facepalm_score)`) as `flawMoveCategory(fm) === 'facepalm'`. `DESKTOP_BOARD_SIZE = 225` (82) is derived from the table height, so recompute it for 8 rows.

### `frontend/src/components/filters/FlawFilterControl.tsx` (component, event)
Analog at 120-133:
```ts
interface SeverityButtonConfig { sev: 'blunder' | 'mistake'; label: string; icon: FlawIcon; color: string; bg: string; }
const SEVERITY_BUTTONS: SeverityButtonConfig[] = [
  { sev: 'blunder', label: 'Blunders', icon: BlunderIcon, color: SEV_BLUNDER, bg: SEV_BLUNDER_BG },
  { sev: 'mistake', label: 'Mistakes', icon: MistakeIcon, color: SEV_MISTAKE, bg: SEV_MISTAKE_BG },
];
```
Make `sev: FlawSeverityFilter`. Add `{ sev: 'facepalm', label: 'Facepalm', icon: <??? icon>, color: SEV_FACEPALM, bg: SEV_FACEPALM_BG }` first and use the singular labels 'Blunder'/'Mistake'. Testids come for free via `filter-flaw-severity-${sev}` (240). Also update the prop type at 59 (`severity: ('blunder'|'mistake')[]`) and the toggle handler (509-516, which already tracks `trackFeature('filter-change', {target:'severity', value: sev})`). Delete the import at 49/54, the props at 84-90 and the render at 607-612 (`FacepalmFilter`).

### `frontend/src/lib/theme.ts` (config)
Analog at 66-78 and 527:
```ts
export const SEV_BLUNDER = 'oklch(0.58 0.19 25)';
export const SEV_BLUNDER_BG = 'oklch(0.58 0.19 25 / 0.14)';
export const SEV_BLUNDER_BORDER = 'oklch(0.58 0.19 25 / 0.30)';
...
export const FACEPALM_BAND_SWATCH = 'oklch(0.42 0.17 25)';
export const SEV_FACEPALM = FACEPALM_BAND_SWATCH;
```
Add `SEV_FACEPALM_BG = 'oklch(0.42 0.17 25 / 0.14)'` (and `_BORDER` / 0.30 if needed) next to `SEV_FACEPALM`, using the same alpha convention.

### `frontend/src/lib/facepalm.ts`
Keep `isFacepalmBlunder` (173-175), `toFacepalmPct`, `FACEPALM_HIGH_CUTOFF` and the copy constants. Delete the range/preset machinery (`FacepalmPreset`, `PRESET_*`, `DEFAULT_FACEPALM_VALUE`, `derivePreset`, `presetToRange`, `sliderToRange`, `isFacepalmNarrowed`, `formatFacepalmSummary`, `facepalmToQueryParams`, 70-160) once its callers are gone. Run `npm run knip` to confirm nothing is left.

## Shared Patterns
- **One classifier:** every frontend surface uses `flawMoveCategory` (moveStatsCounts.ts). There should be no inline `severity === 'blunder' && isFacepalmBlunder(...)` anywhere else. Library Stats and timeline keep the Lichess meaning (D-07).
- **Literal mirroring:** the backend `FlawSeverityFilter` is mirrored in `frontend/src/types/library.ts`, with a comment pointing at each side (as `library_repository.py:97` already does for facepalm constants).
- **One bound score expression:** pass `facepalm_score` into the clause so the chip and the filter cannot disagree (`library_repository.py:357-359` docstring).
- **Theme constants only:** colours come from `theme.ts`, never literals (EvalChart 288 comment).

## No Analog Found
None.

## Metadata
Search scope: app/routers, app/repositories, app/services, tests/repositories, frontend/src/{lib,components,hooks,pages,types}. All paths are in the tracked worktree.
