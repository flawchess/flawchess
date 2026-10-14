# Quick Task 261014-pb9: Library Stats 3x3 tempo x game-phase flaw gap heatmap - Context

**Gathered:** 2026-10-14
**Status:** Ready for planning

<domain>
## Task Boundary

On the Library Stats tab, in the "You vs. your opponents" section, add a 3x3 heatmap crossing
the three tempo tags (low clock, hasty, unrushed) with the three game-phase tags (opening,
middlegame, endgame). Each cell shows the paired you-minus-opponent gap in flaws per 100 of
the user's moves for flaws carrying BOTH tags, for the selected time control. Visually
consistent with the existing context-tag cards and gap bars.

</domain>

<decisions>
## Implementation Decisions

### Placement
- New full-width Card below the four context-tag cards (`ContextTagCards`) inside
  `VsOpponentsSection` (`frontend/src/components/library/stats/LibraryStatsSections.tsx`).
- Same `Card` / `CardHeader` (title + `<small>` subtitle) / `CardBody` styling as `ContextTagCard`.
- Clock and Game phase cards stay unchanged (they are the marginals, with benchmark bands).
- Below-gate / no-data handling follows the section: the section's existing gate slot already
  replaces everything below the gate, so the heatmap only renders when `ContextTagCards` does.

### Data
- Backend: extend the existing flaw-comparison aggregation
  (`app/repositories/library_repository.py`, the COUNT(GameFlaw.ply) FILTER query) with
  18 more columns: player_/opp_ x {tempo} x {phase}, each filter = side AND tempo == X AND phase == Y.
- Compute each cell with the same paired per-game rate / delta / 99% CI / p-value / significant
  machinery as the existing bullets (`_paired_gap_test`, `_build_flaw_bullet` pattern in
  `app/services/library_service.py`). Same denominator: per 100 of the user's moves, both sides.
- Add the 9 cells to the `/api/library/flaw-comparison` response per TC (new field on
  `FlawComparisonTc`, e.g. `tempo_phase_cells`, each carrying `tempo` + `phase` Literals plus the
  FlawBullet stat fields). Do NOT add them to the 12 `bullets` / `FLAW_DELTA_METRICS` (that list
  drives benchmark zones). Mirror the type in `frontend/src/types/library.ts`.
- No benchmark zones for crossed cells: `has_zone = false`, zone_lo/zone_hi = 0.
- Flaws with NULL tempo (no clock data) simply don't appear in any cell; no special copy needed
  beyond what the popover basis already says.

### Color encoding
- Diverging green (fewer flaws than opponents, `ZONE_SUCCESS`) / red (more, `ZONE_DANGER`) from
  `lib/theme.ts`. Opacity/intensity scaled by |gap| relative to the max |gap| among the 9 cells
  of the selected TC (with a sensible floor so the strongest significant cell is clearly saturated
  and weak ones still visibly tinted).
- Non-significant cells (99% CI covers 0) and null-delta cells render neutral (charcoal / the
  card's neutral cell background), matching GapBar's "colour only when significant" rule for
  zoneless cells (D-16). Text must stay readable on every fill.

### Cell content
- Each cell shows the signed gap in words exactly like the bars (`gapWords` from
  `lib/gapBar.ts`, e.g. "1.2 fewer" / "same"); null delta shows the same empty copy the bars use.
- Tap/hover opens the existing `GapPopover` (you rate, opponent rate, CI, basis), with a label
  like "Hasty, middlegame" and a definition combining both tag hints.
- Adapt API cells to the existing `GapCell` view model (reuse/extend `flawBulletToGapCell`).

### Layout
- Plain 3x3, no marginal totals row/column.
- Row/column headers use the existing tag labels from `FLAW_GAP_META` (low_clock/hasty/unrushed,
  opening/middlegame/endgame_phase).

### Claude's Discretion
- Axis orientation (suggested: columns = tempo in Clock-card order low clock, hasty, unrushed;
  rows = phase in game order opening, middlegame, endgame). Must fit phone width (16px gutter, no
  horizontal scroll), e.g. compact header labels on mobile.
- Card title/subtitle copy (e.g. "Clock x game phase" / "where and how fast the flaw happened").
  Keep copy minimal; no jargon. Em-dashes sparingly.
- Optional better/worse legend line consistent with the cards' axis caption.
- data-testids for card, cells (`tempo-phase-cell-{tempo}-{phase}`), popovers; follow
  frontend/CLAUDE.md testid rules.

</decisions>

<specifics>
## Specific Ideas

- Follow frontend/CLAUDE.md (theme constants, testids, no magic numbers, max-depth gate).
- Backend tests: extend the flaw-comparison repository/service tests to cover a crossed cell
  (player vs opponent count for a tempo+phase combo, and that NULL-tempo flaws are excluded).
- Frontend tests: component test for the heatmap (renders 9 cells, neutral fill for a
  non-significant cell, coloured fill for a significant one, popover trigger present).
- CHANGELOG `## [Unreleased]` user-facing bullet.
- Run `npm run build` (tsc -b) since shared API types change.

</specifics>

<canonical_refs>
## Canonical References

- `frontend/src/components/library/stats/ContextTagCards.tsx`, `GapBar.tsx`, `GapPopover.tsx`
- `frontend/src/lib/gapBar.ts`, `frontend/src/lib/flawComparisonMeta.ts`, `frontend/src/lib/theme.ts`
- `app/repositories/library_repository.py` (flaw comparison query ~L1870-2080)
- `app/services/library_service.py` (`_paired_gap_test`, `_build_flaw_bullet`, `_compute_bullets`, `get_flaw_comparison`)
- `app/schemas/library.py` (`FlawBullet`, `FlawComparisonTc`)

</canonical_refs>
</content>
</invoke>
