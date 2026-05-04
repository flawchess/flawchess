# Handoff — Phase 80 column tweaks (paused 2026-05-03)

Branch: `gsd/phase-80-opening-stats-middlegame-entry-eval-and-clock-diff-columns`
Status: working tree dirty, no commits this session.

## User request (verbatim)

Feedback on the current Phase 80 implementation (Openings → Stats page):

1. **Remove the MG Clock column and the corresponding DB query code.**
2. **Rename these columns**: MG Eval → '' (merge tooltip with column MG Entry); MG Entry → Eval.
3. **Remove the MG conf. column** and display the confidence when hovering over (or tapping on mobile) the bullet chart in the Eval column instead.

Interpretation:
- Current desktop columns: `Name | Games | WDL | MG eval (text) | MG entry (bullet) | MG conf. | MG clock`
- New desktop columns: `Name | Games | WDL | (no header — text "+2.1") | Eval (bullet, with tooltip)`
- The "Eval" column header carries the merged tooltip (the existing `MG_EVAL_HEADER_TOOLTIP` already covers both).
- Confidence info that was in the MG conf. pill now opens on hover/tap of the bullet chart. Mobile must support tap (the existing `Tooltip` component suppresses touch — needs a popover-style wrapper instead).

## Done

### Backend
- `app/schemas/stats.py` — removed `avg_clock_diff_pct`, `avg_clock_diff_seconds`, `clock_diff_n` from both `OpeningWDL` and `BookmarkPhaseEntryItem`.
- `app/repositories/stats_repository.py`:
  - Dropped `clock_diff_sum`, `base_time_sum`, `clock_diff_n` from `OpeningPhaseEntryMetrics` dataclass.
  - Removed `aliased` import (no longer needed) and `base_time_seconds` column from dedup CTE.
  - Removed `clock_seconds` from `phase_entry_subq`, removed `gp_opp` alias + outerjoin, removed `clock_diff_expr`, removed `has_user_and_opp_clock` predicate, removed the three clock-diff aggregation columns and the matching row decoders.
  - Updated docstring to drop clock-diff references.
- `app/services/stats_service.py` — removed the clock-diff finalizer block and locals (`avg_clock_diff_pct/seconds/clock_diff_n`) inside `get_most_played_openings.rows_to_openings`.

## Still TODO (in order)

### Backend (finish first — fixes will currently break ty/pytest)

1. **`app/services/stats_service.py`** — the `OpeningWDL(...)` constructor call still passes the removed fields. Strip these three lines from the constructor (around line ~452):
   ```python
   avg_clock_diff_pct=avg_clock_diff_pct,
   avg_clock_diff_seconds=avg_clock_diff_seconds,
   clock_diff_n=clock_diff_n,
   ```
2. **`app/services/stats_service.py`** — `_phase80_item_from_metrics` (around lines ~494-499) still computes the clock-diff fields onto `BookmarkPhaseEntryItem`. Drop the entire `if pe.clock_diff_n > 0 and pe.base_time_sum > 0:` block.

### Frontend

3. **`frontend/src/types/stats.ts`** — drop `avg_clock_diff_pct`, `avg_clock_diff_seconds`, `clock_diff_n` from both `OpeningWDL` (lines 56-58) and the bookmark phase-entry item (lines 82-84).

4. **`frontend/src/components/stats/MostPlayedOpeningsTable.tsx`**:
   - Drop `CLOCK_DIFF_HEADER_TOOLTIP` export and the `formatSignedPct1` / `formatSignedSeconds` imports.
   - Change desktop grid from 7 cols → 5 cols. Current template:
     ```
     sm:grid-cols-[minmax(0,1fr)_auto_minmax(120px,200px)_auto_minmax(100px,160px)_auto_minmax(80px,120px)]
     ```
     New:
     ```
     sm:grid-cols-[minmax(0,1fr)_auto_minmax(120px,200px)_auto_minmax(100px,160px)]
     ```
   - Header row: drop the MG eval `InfoPopover` (header text becomes empty `<span>`), rename "MG entry" → "Eval" (keep the InfoPopover with `MG_EVAL_HEADER_TOOLTIP`), delete the "MG conf." and "MG clock" header cells.
   - Row body: delete column 6 (ConfidencePill) and column 7 (clockDiffContent). Wrap column 5's `<MiniBulletChart>` in a hover+tap popover that renders `<ConfidenceTooltipContent ... evalMeanPawns={o.avg_eval_pawns} />`.
   - Mobile section (lines 202-237 with `sm:hidden`) is dead code (the desktop wrapper uses `hidden lg:block`). Either delete the mobile block entirely or apply the same trim. Recommend deleting since `MobileMostPlayedRows` in Openings.tsx is the live mobile renderer.

5. **`frontend/src/pages/Openings.tsx` (`MobileMostPlayedRows`)**:
   - Drop the `clockDiffContent` block and the `MG entry` label/grid cell for clock-diff (lines ~196-208, 237-242).
   - Replace the standalone `ConfidencePill` (lines 228-235) with a hover+tap popover wrapping the `<MiniBulletChart>` (same pattern as #4).
   - Update the mobile grid template; current `grid-cols-[auto_auto_1fr_auto_auto]` (5 tracks for label/text/bullet/conf/clock) should become `grid-cols-[auto_auto_1fr]` (label/text/bullet) — bullet now carries confidence via tooltip.
   - Drop the `formatSignedPct1`, `formatSignedSeconds`, `ConfidencePill` imports if no longer used.
   - In `buildBookmarkRows` (lines ~1098-1124), drop the three clock-diff fields from the synthetic row.

6. **Confidence-on-bullet popover** — the existing `<Tooltip>` (`frontend/src/components/ui/tooltip.tsx`) **deliberately suppresses touch interactions**, so it won't satisfy the "tapping on mobile" requirement. Build a small wrapper that opens on both hover (mouseenter/leave with delay, like InfoPopover) and tap (PopoverTrigger's default click). Suggested location: `frontend/src/components/insights/BulletConfidencePopover.tsx`. Reuse the Radix `Popover` primitive used by `InfoPopover`. Sample skeleton:
   ```tsx
   function BulletConfidencePopover({ children, level, pValue, gameCount, evalMeanPawns, testId }) {
     const [open, setOpen] = useState(false);
     const hoverTimeout = useRef<ReturnType<typeof setTimeout> | null>(null);
     const handleEnter = () => { hoverTimeout.current = setTimeout(() => setOpen(true), 100); };
     const handleLeave = () => { if (hoverTimeout.current) clearTimeout(hoverTimeout.current); setOpen(false); };
     return (
       <PopoverPrimitive.Root open={open} onOpenChange={setOpen}>
         <PopoverPrimitive.Trigger asChild>
           <button
             type="button"
             className="block w-full"
             aria-label="Show eval confidence details"
             data-testid={testId}
             onMouseEnter={handleEnter}
             onMouseLeave={handleLeave}
           >
             {children}
           </button>
         </PopoverPrimitive.Trigger>
         <PopoverPrimitive.Portal>
           <PopoverPrimitive.Content side="top" sideOffset={4}
             onMouseEnter={() => { if (hoverTimeout.current) clearTimeout(hoverTimeout.current); }}
             onMouseLeave={handleLeave}
             className="z-50 max-w-xs rounded-md border-0 outline-none bg-foreground px-3 py-1.5 text-xs text-background">
             <ConfidenceTooltipContent level={level} pValue={pValue ?? 1} score={0.5}
               gameCount={gameCount ?? 0} evalMeanPawns={evalMeanPawns} />
           </PopoverPrimitive.Content>
         </PopoverPrimitive.Portal>
       </PopoverPrimitive.Root>
     );
   }
   ```
   Use this in both desktop (MostPlayedOpeningsTable) and mobile (MobileMostPlayedRows).

7. **Tests** — `frontend/src/components/stats/__tests__/MostPlayedOpeningsTable.test.tsx`:
   - The header tooltips test (line ~240) references `MG_EVAL_HEADER_TOOLTIP`, `CONFIDENCE_HEADER_TOOLTIP`, `CLOCK_DIFF_HEADER_TOOLTIP`. Drop the latter two; assert only the merged Eval tooltip.
   - Tests asserting MG conf testids and MG clock testids/content need to be removed or rewritten.
   - Add a test that the bullet chart cell exposes the confidence popover (e.g. shows `Avg eval:` / `Number of games:` text after a click, since hover is hard to simulate cross-browser).
   - Backend: check `tests/` for any references to `clock_diff_sum`, `base_time_sum`, `clock_diff_n`, `avg_clock_diff_pct`, `avg_clock_diff_seconds` in the stats path (ignore endgame paths — those use the same names but for a different feature).

### Verification

8. Run `uv run ruff check . && uv run ty check app/ tests/ && uv run pytest -q` and on the frontend `npm run lint && npm test && npm run build`.

## Constraints to remember

- The endgame insights system (`app/services/endgame_service.py`, `EndgameClockPressureSection.tsx`, `endgame_zones.py`, etc.) also uses `avg_clock_diff_pct` / `clock_diff_timeline` — **leave those alone**. The user only wants to drop the *MG entry* clock-diff in the Openings → Stats path.
- `MG_EVAL_HEADER_TOOLTIP` (the existing string) is fine for the renamed "Eval" column — no copy change requested.
- Mobile-friendly: the inner `sm:hidden` section of `MostPlayedOpeningsTable.tsx` is currently dead because the parent wrapper is `hidden lg:block`. Either delete or trim — don't leave a half-updated copy.

## Tasks open in this session (recreate as needed)

1. [in_progress] Remove MG Clock column + DB queries — backend mostly done, finish service constructor + bookmark helper.
2. [pending] Rename MG eval/entry headers — Front-end only.
3. [pending] Move confidence to bullet chart hover — needs new popover wrapper.
4. [pending] Update tests for column changes — frontend table test + any backend stats test referencing dropped fields.
5. [pending] Run lint, typecheck, tests.
