# Quick Task 261014-qj8: Benchmark bands for the tempo x phase heatmap cells - Context

**Gathered:** 2026-10-14
**Status:** Ready for planning

<domain>
## Task Boundary

Follow-up to quick task 261014-pb9 (the "Clock by game phase" 3x3 heatmap on Library Stats).
Give the crossed tempo x phase cells benchmark typical-range bands, and colour the heatmap the
way the gap bars are coloured (verdict needs outside-band AND significant), so the heatmap can no
longer contradict the Clock / Game phase rows above it. Today every crossed cell is
`has_zone = false` and tinted by significance only, scaled to the grid's largest significant gap.

</domain>

<decisions>
## Implementation Decisions

### Basis (owner decision 2026-10-13 applies)
- Do NOT use the 239 full-analysis lane (100 games/user/TC cap): the owner rejected it for flaw
  bands as noise-inflated (`.planning/phases/239-library-stats-you-vs-opponents/239-ZONE-PROPOSAL.md`
  `## Accepted`). The live marginal bands come from the pre-239 §5 basis (all eval'd games, no
  cap, pooled over all TCs). The probe re-ran that basis for the crossed cells; it reproduces the
  live marginals within data drift (middlegame/endgame/low-clock match, hasty/unrushed/opening up to
  ~30% wider on the low side). Evidence: `261014-qj8-PROBE.md` in this directory.
- One pooled band per cell, identical for rapid and classical (and blitz/bullet via ZONE_TC_FOR),
  exactly like the marginals. Bands = `symmetric_band(q1, q3)` with the pooled quartiles rounded to
  the 0.01 grid (D-15).

### Bands (pooled quartiles -> symmetric band, per 100 user moves)
| cell | q1 / q3 | band |
|---|---|---|
| low_clock x opening | degenerate (2% nonzero) | NO band (has_zone false) |
| low_clock x middlegame | -0.02 / +0.01 | +-0.02 |
| low_clock x endgame | -0.06 / +0.03 | +-0.05 |
| hasty x opening | -0.15 / +0.07 | +-0.11 |
| hasty x middlegame | -0.17 / +0.09 | +-0.13 |
| hasty x endgame | -0.08 / +0.06 | +-0.07 |
| unrushed x opening | -0.15 / +0.14 | +-0.15 |
| unrushed x middlegame | -0.28 / +0.22 | +-0.25 |
| unrushed x endgame | -0.10 / +0.09 | +-0.10 |
- Viability rule (chapter5): IQR not degenerate AND >=50% of user-cells nonzero. 8 of 9 pass
  (low_clock x middlegame at 68% pooled). Only low_clock x opening has no band.

### Registry
- Add a separate crossed-cell registry in `app/services/flaw_delta_zones.py` (e.g.
  `TEMPO_PHASE_ZONES` keyed (tempo, phase) -> zone TC -> `ZoneBand | None`, plus a lookup
  `tempo_phase_zone(tempo, phase, tc) -> ZoneBand | None`). Do NOT add the cells to
  `FlawDeltaMetric` / `FLAW_DELTA_METRICS` / `FLAW_DELTA_ZONES` (that list drives the 12 bullets
  and the §5 diff gate). Comment the basis and cite the probe file + date in the registry, in the
  style of the existing module docstring.
- Backend cell builder sets `has_zone`, `zone_lo`, `zone_hi` from the lookup (None -> has_zone
  false, zones 0.0).

### Colour (frontend)
- A cell with a band colours exactly like the gap bars: verdict via the existing `effectiveVerdict`
  / `gapVerdictColor` logic in `lib/gapBar.ts` (better/worse only when outside the band AND
  significant; typical or could-be-chance -> neutral). Intensity: scale by how far beyond the band
  the gap is, reusing the GapBar position curve (`gapPosition`, saturating beyond the band) so a
  cell's tint strength matches where its dot would sit on a bar. Neutral cells stay neutral.
- A zoneless cell (low_clock x opening) keeps the current rule (significance-only tint).
- Retire the "relative to the grid's largest significant gap" scaling if nothing else uses it
  (knip must stay clean).
- Popover: a banded cell's GapPopover shows the typical-range sentence like the bars; the zoneless
  cell keeps `zonelessSignificantCopy`.
- Legend line: update copy so "Grey" covers "typical for your level or no clear difference"
  (keep it to one short line, no jargon, em-dashes sparingly).

### Claude's Discretion
- Exact intensity mapping from gapPosition to tint (keep `data-tint` test hooks; add an intensity
  hook if useful for tests).
- Test shape. Required: backend test that the 8 banded cells carry the registry bands and
  low_clock x opening is has_zone false; frontend test that a significant in-band gap renders
  neutral (this is the contradiction being fixed) and an out-of-band significant gap renders
  coloured. Mutation-check the in-band-neutral test (revert the verdict gate, confirm it fails).

</decisions>

<specifics>
## Specific Ideas

- Probe numbers are in `261014-qj8-PROBE.md`; do not re-run the benchmark DB.
- No change to `scripts/benchmarks/chapter5.py`, the §5 report, or its diff gate.
- CHANGELOG: amend the existing [Unreleased] heatmap bullet (from 261014-pb9) rather than adding a
  second one, if it mentions colouring.

</specifics>

<canonical_refs>
## Canonical References

- `.planning/phases/239-library-stats-you-vs-opponents/239-ZONE-PROPOSAL.md` (## Accepted)
- `.planning/quick/261014-pb9-library-stats-3x3-tempo-x-game-phase-fla/261014-pb9-SUMMARY.md`
- `app/services/flaw_delta_zones.py`, `app/services/library_service.py`, `app/schemas/library.py`
- `frontend/src/lib/gapBar.ts`, `frontend/src/components/library/stats/TempoPhaseHeatmap.tsx`,
  `frontend/src/components/library/stats/GapPopover.tsx`, `frontend/src/lib/theme.ts`

</canonical_refs>
