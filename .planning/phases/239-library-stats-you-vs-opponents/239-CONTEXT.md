# Phase 239: Library Stats You-vs-Opponents Redesign - Context

**Gathered:** 2026-10-12
**Status:** Ready for planning

<domain>
## Phase Boundary

Make the Library Stats tab (below the Flaw Stats tiles and the Flaws Timeline) readable for
non-statisticians. Every you-vs-opponent metric (Blunders/Mistakes tiles, 10 context tags, tactic motifs)
becomes one zero-centred gap bar with the gap in words, a Search-icon popover carries the rates and
statistics, and each section gets a synced TC switch. The tactic tables get real benchmark typical ranges
from an extended `/benchmarks` §5, which also recomputes the flaw-delta zones on the fully analyzed sample.

SEED-198 locked decisions 1-12 and sketch 010 round 5 are the design. This discussion resolved the open
questions from ROADMAP.md: filters vs TC switch, default TC and below-gate TCs, tactic zone sequencing and
granularity, the zone basis, the low-sample threshold, and whether tactics feed "What stands out". No new
capabilities beyond SEED-198.

</domain>

<decisions>
## Implementation Decisions

### Carried forward from SEED-198 (locked 2026-10-12, do not re-ask)
- **D-00a:** Gap bar is the one visual: 0 tick in the middle, grey benchmark IQR of the gap drawn where it is (may be off-centre), one dot red/blue/green, better always to the right, linear inside the band and saturating outside (`1 - e^-x`, x in band widths). No red/green halves, no CI whiskers.
  - **Owner override, 2026-10-13 (UAT, D-14/D-15):** direction flipped: lower values (fewer flaws = better) on the LEFT, following the number line. The grey band is now symmetric around 0 (D-15), so it is always centred.
- **D-00b:** The gap reads as words ("1.7 fewer", "0.42 more", "same"); typical gaps print white, only better/worse are green/red; the dot stays blue for typical.
- **D-00c:** Only the gap is on the page (tiles keep their "Opponents x.xx" line). A lucide Search icon opens a `RankedMetricPopover`-shell popover: definition + "Fewer is better", You/Opponents, typical gap range + verdict, basis, then greyed counts / 95% CI / p-value below a separator.
- **D-00d:** "flaws" / "blunders" / "mistakes", never "events".
- **D-00e:** Tiles: Blunders and Mistakes only (Inaccuracies tile, Severity card and "Flaw rate" retire).
- **D-00f:** Context tags: combos (hasty miss, low-clock miss) removed; four cards Clock | Game phase, Opponent errors | Lost advantages, tag names unchanged, one-line hint per tag.
- **D-00g:** "What stands out" card above the context cards: top 3 strengths / top 3 weaknesses ranked by distance outside the band in band widths, each with hint, coloured gap and Search popover, then one "Typical: …" line.
  - **Owner override, 2026-10-13 (UAT):** the "What stands out" card was dropped. The You vs. your opponents section shows only the four context-tag cards; `WhatStandsOut` and its ranking helpers (`pickStandouts`, `standoutDistance`) were deleted.
- **D-00h:** Tactic motifs: three tables in `TACTIC_GROUPS` order, Motif (+ "N of your flaws") | Missed | Allowed, full-size gap bars per 100 games, fixed column widths, phones stack Missed/Allowed under the motif, zero-count motifs listed under the table. "More tactics" accordion and the top-6 ranking (Phase 129 D-14) retire.
- **D-00i:** Advanced table collapsed by default with chevron and the `ShellyQuote` `EXPAND_HINT` "Click or tap for details" hint, hidden once open.
- **D-00j:** Card header bands throughout; Fredoka only for the h2 section titles.
- **D-00k:** Unchanged: Flaws Timeline visuals (it follows the selected TC), ELO Ratings, Results Breakdown, analyzed-coverage badge.
  - **Owner override, 2026-10-13 (UAT):** ELO Ratings and Results Breakdown did change. The ELO charts gained grey daily game-count bars (like the Endgame ELO Timeline; `/stats/rating-history` now returns `game_count` per day and TC), and the Results Breakdown rows lost their transparent relative game-count bars.

### Filters and the TC switch
- **D-01:** The sidebar filter panel **stays** on the Library Stats tab (unlike Phase 238 D-01/D-02: there is no ranked sample here, so recency, platform, color and opponent-strength filters stay meaningful). All gap metrics are computed over the filtered analyzed games of the selected TC.
- **D-02:** The TC switch **narrows within the filter**: it offers only TCs allowed by the time-control filter that have ≥1 analyzed game in the current filters; zero-analyzed TCs are omitted. One synced switch across Flaw Stats, You vs. your opponents, and Tactic motifs. ELO Ratings and Results Breakdown keep reading the sidebar filters exactly as today (not the switch).
- **D-03:** A TC with ≥1 but fewer than 20 analyzed games (`FLAW_COMPARISON_GATE` / `TACTIC_COMPARISON_GATE`) stays in the switch; tiles still show the rates, and each gap-bar section shows a slot like "Not enough analyzed games yet (12 of 20)" instead of bars (Phase 238 D-09 shape).
- **D-04:** Default TC on load = TC with the most analyzed games in the current filters, ties to the faster TC, preferring an above-gate TC when one exists.
- **D-05:** The selected TC is remembered in `localStorage` with a key **separate from** the Endgame Stats page (Endgame counts ranked games, Library counts analyzed games). try/catch, renders fine without it; falls back to D-04 when the stored TC is not offered under the current filters.

### Benchmark zones (tactic IQRs + flaw-delta refresh)
- **D-06:** Extend `/benchmarks` §5 (`scripts/benchmarks/chapter5.py`, `.claude/skills/benchmarks/SKILL.md` §5) with per-family Missed and Allowed paired-delta zones (you − opponent, per 100 games) plus a viability table, same methodology as the flaw-delta zones (equal-footing filter, per-(user, elo, tc) values, ≥30-contributor cell floor, Cohen's-d collapse verdict per axis). Unviable families (e.g. x-ray, en passant) get `has_zone = false`.
- **D-07:** **One basis for all zones:** the same §5 run recomputes the existing flaw-delta zones (blunder, mistake, and the 10 surviving context tags) on the **fully analyzed benchmark sample**, replacing the old Lichess-eval-only basis in `app/services/flaw_delta_zones.py`. Combos and `flaw_rate` drop from the registry. Some bands users see today will move. — **Reversibility:** reversible — registry constants, re-run §5 to change.
  - **Owner override, 2026-10-13 (239-06 checkpoint, accept with edits; see `239-ZONE-PROPOSAL.md` `## Accepted`):** D-07's "one basis for all zones" was overridden for the 12 flaw bands. They keep their live values (the older whole-cohort basis, up to ~1000 games per user) because the full-analysis lane's 100-games-per-TC cap makes the proposed widening (1.5x to 3.5x) mostly sampling noise (noise-only IQR 70% to 142% of the observed IQR). The 9 viable tactic bands use the §5 full-analysis-lane basis as measured. `reports/benchmark/benchmarks-latest.md` §5 records the flaw values as the not-adopted proposal.
- **D-08:** **Don't wait for blitz.** Compute zones now from the finished classical + rapid full-analysis samples. **Blitz and bullet use the rapid zones as a stopgap** (for both tactic and flaw-delta zones) until their full-analysis samples exist; refresh later by re-running §5. The half-finished blitz sample is not used.
- **D-09:** The stopgap is **silent** in the UI (popover copy minimalism). The TC mapping is documented in the zone registry module and in the benchmark report.
- **D-10:** Granularity: let the collapse verdict decide per axis (TC: classical vs rapid only for now; Elo), with thin cells falling back to marginal/global zones, as for the existing flaw-delta zones. The registry may hold per-TC and/or per-Elo zones when they don't collapse.
- **D-11:** A tactic zone registry next to `flaw_delta_zones.py`, wired into `get_tactic_comparison` (`zone_lo` / `zone_hi` / `has_zone`). `has_zone = false` renders band-less: no grey band, blue dot, no verdict, popover without a typical range line.

### Low sample and "What stands out"
- **D-12:** Low-sample fade = a named constant of **40 flaws (you + opponents) per cell**, applied to tactic cells **and** context-tag rows: faded, no red/green verdict (dot neutral), popover says "Too few flaws to call it". The planner sanity-checks 40 against the CI width on the owner's dev blitz/rapid data and adjusts the constant only if clearly off.
  - **Owner override, 2026-10-13 (UAT):** replaced by the significance gate (D-14). `LOW_SAMPLE_MIN_FLAWS` and `low_sample` are removed.
- **D-13:** "What stands out" ranks **context tags only** (not tactics, not the Blunders/Mistakes tiles). Faded (low-sample) rows never qualify.
  - **Moot since 2026-10-13 (UAT):** the "What stands out" card was dropped (see D-00g).

### Significance gate and symmetric bands (added 2026-10-13, UAT discussion)
- **D-14:** Red/green verdicts require statistical significance at **99%**, on the Library page (gap bars, tiles' gap) **and** the Endgame Stats page (percentile bars and any other red/green verdict). A cell outside the band / outside the 25-75 percentile range but not significant renders **neutral like typical** (blue dot, white text; endgame: blue dot and neutral ordinal), and the popover says it may be chance. Nulls: **difference metrics test against 0** (99% CI excludes 0 on the verdict's side); the endgame **raw rates** (conversion, parity, recovery rate) test against the **cohort median** (p50 of the cohort CDF at the user's anchor). Displayed CIs switch to 99% so popover and verdict agree. Replaces D-12. Skipped: percentiles for Library stats (benchmark bands are mostly sampling noise, see 239-ZONE-PROPOSAL.md).
- **D-15:** All Library difference bands (12 flaw + 9 viable tactic) become **symmetric around 0: ±IQR/2** of the measured quartiles, rounded up to the 0.01 grid. Rationale: the off-centre quartiles (e.g. low-clock −0.08/+0.03) come from rare, discrete per-user values and cohort selection, not a real typical offset, and the gate tests against 0. — **Reversibility:** registry constants.
- **D-16 (2026-10-13, UAT):** a tactic cell without a typical range (`has_zone = false`, 29 of 38) is judged on significance alone: green/red when its 99% CI on the gap excludes 0, neutral otherwise. Its popover keeps no typical-range line and, when significant, says "There is no typical range for this tactic, but the gap is too large to be chance." Amends D-11's "no verdict".
- **D-17 (2026-10-13, UAT, overrides D-00h's three tables):** the Tactic motifs section shows ONE card, "Most common tactics", with Fork, Pin, Hanging piece and Checkmate (filter-panel order, every row shown even without flaws). They are the four most common families and the only ones with a viable benchmark range on both sides; the other 15 occur under once per 100 games per player (§5 lane, all blobs done), so their gaps were mostly noise. The three group tables, the collapsed Advanced accordion (D-00i for tactics) and the "No flaws yet" list retire. Frontend-only: `/tactic-comparison` still returns all 38 bullets. Owner preference: show less rather than noise.

### Claude's Discretion
- Plan split (likely: benchmark §5 + zone registries, backend payload, frontend rework).
- Payload shape: one TC per request vs one response with all offered TCs (endgame ranked-payload style); per-TC analyzed counts needed for D-02/D-03/D-04 either way.
- API cleanup: drop combo tags, `flaw_rate` and the top-6 tactic ranking from the payloads and repositories vs stop rendering; prefer removing dead backend paths (`library_repository.py` and `chapter5.py` combo computation) when nothing else consumes them.
- Which Elo the zone lookup uses if the Elo axis does not collapse (e.g. the user's current rating in the selected TC).
- Copy for the gate slot, "Typical: …" line, and the "What stands out" empty case (fewer than 3 strengths/weaknesses, or none).
- Where the TC-switch state lives (small store vs hook like `useEndgameStatsTc`), as long as D-05 persistence holds.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Design and locked decisions
- `.planning/seeds/SEED-198-library-stats-you-vs-opponents-redesign.md` — locked decisions 1-12, work implied, breadcrumbs
- `.planning/sketches/010-library-stats-you-vs-opponents/index.html` — owner-approved round 5 layout (tactic IQRs in the sketch are made up)
- `.planning/sketches/010-library-stats-you-vs-opponents/README.md` — round 1-5 decisions, real vs made-up data
- `.planning/ROADMAP.md` §Phase 239 — goal, guardrails, open questions (answered here)
- `.planning/phases/238-endgame-stats-percentile-first/238-CONTEXT.md` — sibling redesign; TC switch / gate-slot / default-TC patterns this phase mirrors (filters decided differently, D-01)
- `.planning/seeds/closed/SEED-196-endgame-stats-percentile-first-redesign.md` — sibling seed

### Benchmarks and zones
- `.claude/skills/benchmarks/SKILL.md` §5 — flaw-delta zone methodology to extend
- `scripts/benchmarks/chapter5.py` — §5 compute (fast refresh path via `chapter5.compute()`, see memory note on §5 refresh)
- `reports/benchmark/benchmarks-latest.md` §5 — current zones, estimator (D-01 unified), cell floor, viability diagnostic
- `app/services/flaw_delta_zones.py` — current pooled zone registry (to be recomputed, combos/flaw_rate dropped)

### Backend
- `app/routers/library.py` — `/flaw-stats`, `/flaw-comparison`, `/tactic-comparison`
- `app/services/library_service.py` — `get_flaw_comparison`, `get_tactic_comparison` (top-6 D-14 ranking to retire), `FLAW_COMPARISON_GATE`, `TACTIC_COMPARISON_GATE`
- `app/schemas/library.py`, `app/repositories/library_repository.py` (combo computation)

### Frontend
- `frontend/src/pages/GlobalStats.tsx` — Stats tab, filter panel wiring
- `frontend/src/components/library/FlawStatsPanel.tsx`, `FlawStatsBand.tsx`, `FlawComparisonGrid.tsx`, `TacticComparisonGrid.tsx`
- `frontend/src/lib/flawComparisonMeta.ts`, `frontend/src/lib/tacticComparisonMeta.ts` (`TACTIC_GROUPS`), `frontend/src/lib/tagDefinitions.ts`
- `frontend/src/components/endgames/stats/PercentileBar.tsx`, `RankedMetricPopover.tsx`, `RankedMetricRow.tsx`, `TcSwitch.tsx`; `frontend/src/hooks/useEndgameStatsTc.ts`; `frontend/src/components/insights/ShellyQuote.tsx` (`EXPAND_HINT`)
- `frontend/CLAUDE.md` — styling, testids, Umami

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `PercentileBar` / `RankedMetricPopover` / `TcSwitch` / `useEndgameStatsTc` (Phase 238): templates for `GapBar`, the gap popover, and the per-page TC switch hook.
- `ShellyQuote` `EXPAND_HINT` styling for the collapsed Advanced table.
- `TACTIC_GROUPS` in `tacticComparisonMeta.ts`: table and row order.

### Established Patterns
- Zone registry is backend-owned (Phase 115 D-07): the endpoint embeds `zone_lo` / `zone_hi`; no TS codegen for these.
- Existing sign convention: negative delta = fewer flaws = good. The gap bar flips it visually (better to the right).
- `MiniBulletChart` is still used by Openings (`OpeningStatsCard.tsx`, `PositionResultsPanel.tsx`, `OpeningFindingCard.tsx`, `openingStatsZones.ts`, `scoreBulletConfig.ts`): **do not delete**. `FlawBulletPopover` is used only by the Library grids, `flawComparisonMeta.ts` and `SeverityGlyphIcon.tsx`; delete only after checking the `SeverityGlyphIcon` dependency.
- Benchmarks are the source of truth for "typical" copy.
- Popover copy minimalism (WHAT + sign convention); no flame icons.

### Integration Points
- Shared `useFilterStore` drives the Library queries; the TC switch adds one TC on top of the filtered set (D-02).
- Flaws Timeline today pools TCs; per SEED-198 D-12 it follows the selected TC.
- The benchmark DB must hold the fully analyzed sample marker (researcher: identify how full-analysis games are distinguished from Lichess-eval-only games, see memory `project_eval_completion_columns`).

</code_context>

<specifics>
## Specific Ideas

- Gate slot copy shape: "Not enough analyzed games yet (12 of 20)".
- Low-sample popover line: "Too few flaws to call it".
- Stopgap mapping: blitz → rapid zones, bullet → rapid zones (until their full-analysis samples exist).

</specifics>

<deferred>
## Deferred Ideas

- Refresh all zones with blitz (and bullet) once their full-analysis benchmark samples finish (re-run §5; replaces the D-08 stopgap).
- Tactics in "What stands out" (rejected for now, D-13).

### Reviewed Todos (not folded)
- `172-deferred-review-findings.md`, `2026-03-11-bitboard-storage-for-partial-position-queries.md`, `2026-08-29-variation-tree-nested-button.md`: keyword-only matches, unrelated to this phase.

</deferred>

---

*Phase: 239-library-stats-you-vs-opponents*
*Context gathered: 2026-10-12*
