---
id: SEED-198
status: promoted
promoted_to: Phase 239
promoted: 2026-10-12
planted: 2026-10-12
planted_during: ad-hoc Library Stats UX review (no phase in flight)
trigger_when: owner picks the Library Stats redesign as a phase; the tactic-IQR plan can start once the blitz full-analysis benchmark sample is done
scope: medium (benchmark §5 extension for tactic IQRs + backend zone wiring + frontend rework of the Stats tab below the timeline; likely 1 phase with 2-3 plans, benchmark/backend first)
---

# SEED-198: Library Stats redesign, you vs. your opponents (gap bars)

Design: `../../sketches/010-library-stats-you-vs-opponents` (round 5, owner-approved direction).
Baseline screenshots (gitignored, local only): `temp/library-stats/`.
Sibling redesign this must stay consistent with: SEED-196 (Endgame Stats, Phase 238, sketch 009).

## Why This Matters

Below the Flaw Stats tiles and the Flaws Timeline (which the owner likes and keeps), the Library Stats tab
shows 15 context-tag bullets in 6 family cards plus 12+ tactic-motif bullets in cards and a "More tactics"
accordion. Every row is the same `MiniBulletChart`: red/green background halves, a blue IQR band, CI
whiskers, a signed delta where negative is good, and a magnifier. It is repetitive and hard to read for
non-statisticians:

- Each row needs four concepts decoded (paired delta, inverted colours, CI whiskers, benchmark band).
- The red/green halves are always fully painted, so a +0.00 row (endgame, p = 0.92) still looks like a verdict.
- Units differ silently: flaw deltas are per 100 moves, tactic deltas per game (+0.02 is unreadable).
- The Severity card repeats the tiles (blunder 5.31 vs tile 5.30); "Flaw rate" is blunders + mistakes;
  Combos overlap Tempo × Opportunity.
- Tactic rows have `has_zone = false` everywhere, so there is no typical band at all.
- The best content (the plain sentence "You have 1.70 fewer hasty flaws per 100 moves than your opponents.
  You: 0.71, opponents: 2.41") is hidden in the hover popover.

## Locked decisions (owner, 2026-10-12, sketch rounds 1-5)

1. **Gap bar is the one visual** for every you-vs-opponent metric (tiles, context tags, tactics). The middle
   tick is always 0 ("same as your opponents"); the grey band is the benchmark IQR of the gap, drawn where
   it actually is (may be off-centre); one dot coloured red (worse than typical) / blue (typical) / green
   (better). **Better is always to the right**, matching the endgame `PercentileBar`, even though every
   metric here is a flaw rate where lower is better. Linear inside the band, saturating outside
   (`1 - e^-x`, x in band widths) so large gaps approach the edge without clipping. No red/green halves,
   no CI whiskers.
2. **The gap reads as words** ("1.7 fewer", "0.42 more", "same"). Typical gaps print white; only
   better/worse gaps are green/red. The dot stays blue for typical.
3. **Only the gap is on the page.** No "you vs. opponents" rates in the context rows, the "What stands out"
   items or the tactic tables. A lucide **Search** icon to the right of every gap opens the popover (the
   `RankedMetricPopover` shell: light bubble, text-xs): definition + "Fewer is better", **You: x. Opponents: y.**,
   the typical gap range and verdict, the basis ("your N analyzed <tc> games in the current filters"),
   then a grey italic footer below a separator with flaw counts, 95% CI and p-value.
4. **Wording:** "flaws" / "blunders" / "mistakes", never "events".
5. **Tiles:** Blunders and Mistakes only (the Inaccuracies tile is removed). Each keeps its big number,
   gets an "Opponents x.xx" line and a gap bar. The Severity card and its "Flaw rate" row retire.
6. **Context tags:** combos (hasty miss, low-clock miss) are removed. Four cards with header bands:
   Clock (low-clock, hasty, unrushed) | Game phase (opening, middlegame, endgame), Opponent errors (miss,
   lucky) | Lost advantages (reversed, squandered). Tag names stay (they match the Games-tab chips), each
   with a one-line plain-language hint under the label.
7. **"What stands out" card** above the context cards: top 3 strengths and top 3 weaknesses ranked by
   distance outside the band (in band widths, so rare tags compete fairly), each with hint, coloured gap and
   Search popover; then one line "Typical: …".
8. **Tactic motifs: three tables** following the filter panel's `TACTIC_GROUPS` and family order:
   Piece Attacks · Checkmate, Checks & Discoveries · Advanced. Columns Motif (+ "N of your flaws") | Missed |
   Allowed, each cell a full-size gap bar; units **per 100 games**; fixed column widths so the tables line
   up; phones stack Missed/Allowed under the motif. Motifs with no flaws on either side are listed under
   the table, not as rows. The "More tactics" accordion retires.
9. **Advanced collapsed by default**, with header chevron and the endgame page's "Click or tap for details"
   hint (`ShellyQuote` `EXPAND_HINT` styling), hidden once open.
10. **Low-sample cells** (fewer than 40 flaws, you + opponents, in that cell) are faded and get no red/green
    verdict; the popover says "Too few flaws to call it".
11. **Synced time-control switch** in every section (Flaw Stats, You vs. your opponents, Tactic motifs), like
    the endgame page (`TcSwitch` / `useEndgameStatsTc` pattern). Card header bands throughout; Fredoka only
    for the h2 section titles.
12. Unchanged: the Flaws Timeline (it follows the selected TC), ELO Ratings, Results Breakdown, the
    analyzed-coverage badge.

## Work implied (for discuss/plan)

**Benchmark: tactic-motif IQRs (blocks the tactic bands).** `TacticBullet.has_zone` is false because the old
benchmark DB had only Lichess-provided evals for some games, no full analyses. Representative benchmark
samples are now being fully analyzed (classical and rapid done, blitz about half on 2026-10-12). Extend the
`/benchmarks` skill §5 (`../../../scripts/benchmarks/chapter5.py`, `.claude/skills/benchmarks/SKILL.md` §5) with
per-family Missed and Allowed paired-delta zones (you − opponent, per 100 games), same methodology as the
15 flaw-delta zones (equal-footing filter, per-(user, elo, tc) values, Cohen's-d collapse verdict per axis),
plus a viability table (share of users with non-zero counts; rare families like en passant or x-ray may be
unviable and should get `has_zone = false`). Basis must be the fully analyzed sample only.

**Backend.**
- A tactic zone registry next to `../../../app/services/flaw_delta_zones.py`, wired into `get_tactic_comparison`
  (`app/services/library_service.py`, sets `zone_lo` / `zone_hi` / `has_zone`).
- `get_tactic_comparison` still ranks top-6 families (D-14) for the old grid; the new tables want every
  family in `TACTIC_GROUPS` order, so the ranking can go.
- Drop the combo tags (and `flaw_rate`) from the flaw-comparison payload, or just stop rendering them;
  `../../../app/repositories/library_repository.py` and `chapter5.py` still compute `hasty_miss` / `low_clock_miss`.
- Per-TC requests: the switch implies one TC per request (or one request returning all TCs, like the
  endgame ranked payload). Today's flaw-delta zones are pooled (one zone per metric), which is fine.

**Frontend.** A `GapBar` component (sibling of `PercentileBar`) + a gap popover (sibling of
`RankedMetricPopover`); tiles rework in `FlawStatsBand.tsx`; `FlawComparisonGrid.tsx` → four cards +
"What stands out"; `TacticComparisonGrid.tsx` → three group tables with the collapsible Advanced card;
TC switch per section in `pages/GlobalStats.tsx`. `MiniBulletChart` and `FlawBulletPopover` likely lose
their last Library usage (check Openings before deleting). Update `FLAW_COMPARISON_FAMILIES` /
`flawComparisonMeta.ts` (combos, Severity) and tests.

## Open questions for discuss-phase

- **TC switch vs. the sidebar time-control filter** on this tab (same question SEED-196 raised): hide the
  filter here, or let it limit which TCs the switch offers? What about the Flaws Timeline, which today
  pools TCs?
- Default TC on load (most-played analyzed TC?) and a TC below the analyzed-games gate (20): hide it from
  the switch or show the gate CTA in each section?
- Tactic zones per TC × Elo or pooled? Let the collapse verdict decide, as for the 15 flaw-delta zones.
- Ship the tactic tables before the IQRs exist (band-less bars, verdict-neutral) or wait for the benchmark
  plan? The sketch used made-up bands.
- Should tactics feed "What stands out" once their zones are real?
- Low-sample threshold: 40 flaws per cell was a sketch choice; calibrate against the CI width.

## Breadcrumbs

- `../../../frontend/src/pages/GlobalStats.tsx` (Stats tab), `frontend/src/components/library/FlawStatsPanel.tsx`,
  `FlawStatsBand.tsx`, `FlawComparisonGrid.tsx`, `TacticComparisonGrid.tsx`,
  `frontend/src/components/popovers/FlawBulletPopover.tsx`, `frontend/src/components/charts/MiniBulletChart.tsx`
- `../../../frontend/src/lib/flawComparisonMeta.ts`, `frontend/src/lib/tacticComparisonMeta.ts` (`TACTIC_GROUPS`),
  `frontend/src/lib/tagDefinitions.ts`
- Endgame patterns to reuse: `../../../frontend/src/components/endgames/stats/PercentileBar.tsx`,
  `RankedMetricPopover.tsx`, `RankedMetricRow.tsx`, `TcSwitch.tsx`, `frontend/src/hooks/useEndgameStatsTc.ts`,
  `frontend/src/components/insights/ShellyQuote.tsx` (`EXPAND_HINT`)
- Backend: `../../../app/routers/library.py` (`/flaw-comparison`, `/tactic-comparison`), `app/services/library_service.py`,
  `app/services/flaw_delta_zones.py`, `app/schemas/library.py`, `app/repositories/library_repository.py`
- Benchmarks: `../../../.claude/skills/benchmarks/SKILL.md` §5, `scripts/benchmarks/chapter5.py`
- Sibling seed: `SEED-196-endgame-stats-percentile-first-redesign.md`
