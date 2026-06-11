# Phase 115: You-vs-Opponent Comparison API + Bullet-Grid UI - Context

**Gathered:** 2026-06-11
**Status:** Ready for planning

<domain>
## Phase Boundary

Replace the Library flaw-stats panel's self-only tag-distribution zone with a
**you-vs-opponent comparison surface**: a backend endpoint computing the unified
paired per-game delta (per-100-of-your-own-moves, 114 D-01) for the full
**15-bullet inventory** with a CI per bullet, plus hand-authored benchmark
"typical" zone constants from the §5 report, feeding a family-grouped
`MiniBulletChart` grid with tooltips, a 20-analyzed-game section gate, and
graceful degradation. The trend chart stays comparison-free (FLAWUI-05).

The 15 bullets: Flaw Rate, Mistakes, Blunders (severity) / low-clock, hasty,
unrushed (tempo) / opening, middlegame, endgame (phase) / miss, lucky
(opportunity) / reversed, squandered (impact) / hasty+miss, low-clock+miss
(combos).

**Not in this phase:** tactic-motif bullets (SEED-039, v2), eval-coverage
raising (SEED-012, v2), trend-chart comparison, termination patterns, prod
`game_flaws` backfill (ships empty on prod per milestone scope).
</domain>

<decisions>
## Implementation Decisions

### Grid layout & grouping
- **D-01:** **Family-grouped grid** with subsection headers per family:
  Severity (Flaw Rate, Mistakes, Blunders), Tempo, Phase, Opportunity, Impact,
  Combos. Not a flat 15-row wall; no oversized headline bullet.
- **D-02:** **FlawStatsBand stays; the per-game/per-100 NormToggle is removed.**
  The Band is fixed to **per-100-moves** so the whole panel speaks one unit
  (the bullets are locked per-100 for zone portability). `NormToggle` and the
  `per_game` rendering path are deleted, not hidden.
- **D-03:** **3 bullet columns on desktop, 1 on mobile.** ~5 rows of bullets at
  lg. Accepted trade-off: tighter chart width per bullet — keep labels short
  and let the popover carry the long names.
- **D-04:** **Per-metric axis domains.** Each bullet's `domain` is calibrated to
  its own metric (starting point: §5 pooled p05/p95), hand-set alongside the
  zone constants in the same registry. No shared global scale — a ±0.1pp zone
  must not render as an invisible sliver.

### Zone constants & bands
- **D-05:** **Zone bands = raw §5 pooled Q1/Q3 verbatim.** No editorial
  widening, no minimum band width. Near-degenerate zones (reversed
  [+0.0, +0.0], low-clock+miss [+0.0, +0.0]) render as-is, hairline accepted.
  (Deliberate exception to the usual editorial-judgment rule — user's explicit
  call for this surface.)
- **D-06:** **Pooled global zones for all 15 metrics.** Follow §5's per-metric
  recommendation; no per-ELO refinement for endgame-phase (d=0.28) or blunders
  now — revisit at the next benchmark refresh. Consequence: zones are fully
  filter-independent (no rating/TC lookup at request time).
- **D-07:** **Constants live in a new backend registry** (`flaw_delta_zones.py`
  or similar, mirroring the `endgame_zones.py` shape) and the endpoint **embeds
  each bullet's zone bounds in the response** (FLAWCMP-03). **No TS codegen**,
  no committed frontend constants — the frontend renders what the API sends.
  Per-metric axis domains (D-04) co-locate in the same registry and ship in the
  payload too.
- **D-08:** **Keep the you−opponent sign convention; invert the chart colors.**
  Negative delta = fewer flaws than opponents = good. `MiniBulletChart` gets an
  inverted-color mode (success zone paints LEFT of the neutral band, danger
  RIGHT) so displayed numbers match §5, the zone constants, and the tooltip
  sign-convention line verbatim. Do not negate the metric.

### Sample gates & fallbacks
- **D-09:** **Section gate floor = 20 analyzed games** in the current filter —
  matches the §5 cohort-inclusion basis (≥20 analyzed games/user), so the
  user's delta and the zone rest on comparable sample sizes.
- **D-10:** **Below the floor, the grid zone renders an "analyze more games"
  CTA state**: current analyzed count vs the 20 needed + guidance toward
  getting more games analyzed (lichess server analysis). FlawStatsBand and the
  trend chart above stay live. No greyed-out ghost grid.
- **D-11:** **Zero-event bullets keep their row** with a muted "no events"
  placeholder instead of a chart. The grid never reflows as filters change;
  absence-of-events is visually distinct from "exactly typical" (FLAWCMP-05).
- **D-12:** **`low-clock+miss` ships** (58% cohort viability) using the same
  fallback machinery — zero-event placeholder + the CI speaking for itself.
  FLAWCMP-04's plan-time CI-width check against materialized dev data
  (users 28/44) confirms; only a catastrophic result there reopens the
  drop question.

### Filter interactions
- **D-13:** **Under a non-default severity filter (e.g. blunders-only), zones
  stay visible with a tooltip caveat** noting the zone was computed on the
  M+B basis. No zone-hiding degradation for severity; the FLAWUI-04 zoneless
  path remains reserved for genuinely zoneless metrics (future tactic motifs).
- **D-14:** **FLAWUI-03 requirement text stays unamended; the tooltip copy is
  written future-proof** — generic wording along the lines of "filters move
  your point estimate; the typical zone may not follow your filters" that
  survives a future per-ELO zone refinement without copy changes. No
  REQUIREMENTS.md amendment for this.
- **D-15:** **Tooltips follow the endgame metrics style**:
  `frontend/src/components/popovers/MetricStatPopover.tsx` (HelpCircle-trigger
  popover, text-xs allowed per CLAUDE.md exception), with metric-specific
  paragraphs added where needed — definition + sign convention per bullet
  (FLAWUI-02), tempo-interaction caveat on clock-conditioned tags,
  squandered/lucky exposure caveat (114 D-03), severity-basis caveat (D-13),
  filter line (D-14).
- **D-16:** **No special handling for the opponent-gap filter.** No extra
  disclosure about ELO-matched zone basis vs gap-filtered deltas; the generic
  zone wording (D-14) covers it implicitly.

### Claude's Discretion
- **CI method:** bootstrap vs normal/t approximation over per-game deltas —
  planner/executor choice; default to the normal/t approximation (deterministic,
  cheap, adequate at N≥20) unless research finds a concrete reason to bootstrap.
- **Endpoint shape:** extend `GET /api/library/flaw-stats` vs a sibling
  endpoint — planner's call (consider payload size and the existing TanStack
  query key structure).
- Exact family header copy, bullet label text, CTA copy, popover prose
  (within the D-15 structure and the project's popover-copy-minimalism rule).
- SQL aggregation strategy for the per-game paired deltas (single game_flaws
  scan with `is_opponent_expr` split + `games.ply_count` denominator per
  Phase 114.1's fast path is the obvious shape).
- What happens to `FlawTagDistribution.tsx` and its tests (deleted with the
  zone it implements, unless something still consumes it).
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Design source (locked, with amendments)
- `.planning/seeds/SEED-040-flaw-stats-opponent-comparison.md` — milestone
  design, bullet inventory, combo curation, statistical method (as amended by
  114 D-01/D-04: unified estimator, Wilson voided).
- `.planning/REQUIREMENTS.md` §FLAWCMP + §FLAWUI — the 11 requirements this
  phase delivers; FLAWCMP-01 amended, FLAWCMP-02 voided.
- `.planning/phases/114-benchmark-flaw-delta-zone-computation/114-CONTEXT.md`
  — D-01 unified estimator definition (the exact per-game formula), D-03
  exposure-caveat disclosure, D-10 hand-authored-zones mandate.

### The zone data (input to the hand-authored constants)
- `reports/benchmark/benchmarks-latest.md` **§5 Flaw-Delta Zones** (§5.1–§5.16)
  — pooled Q1/Q3 per metric, p05/p95 (for D-04 axis domains), collapse
  verdicts (all → pooled global), viability diagnostics (§5.16) for the
  FLAWCMP-04 combo check. Note the 2026-06-11 mate-ladder basis paragraph —
  these are the current numbers.

### Zone-registry precedent
- `app/services/endgame_zones.py` — the registry shape to mirror for
  `flaw_delta_zones.py` (but NO TS codegen this time, per D-07 the API carries
  the bounds).

### Existing endpoint + panel (the surfaces being extended/replaced)
- `app/services/library_service.py` §"Stats panel (LIBG-09)" —
  `get_flaw_stats`, the filter kwargs plumbing, `_analyzed_game_ids_subquery`,
  the W2 per-100 denominator precedent.
- `app/repositories/library_repository.py` — `fetch_stats_aggregates` (the
  COUNT(*) FILTER single-scan pattern to extend with the opponent split),
  `fetch_total_user_moves`.
- `app/repositories/query_utils.py` — `is_opponent_expr(ply, games.user_color)`
  (113 D-01), the single source of the player/opponent parity convention.
- `app/schemas/library.py` — `FlawStatsResponse` and friends.
- `frontend/src/components/library/FlawStatsPanel.tsx` — panel shell;
  `NormToggle` is removed here (D-02); `FlawTagDistribution` is the replaced
  zone; `FlawStatsBand` switches to fixed per-100.
- `frontend/src/components/charts/MiniBulletChart.tsx` — already supports CI
  whiskers (`ciLow`/`ciHigh`), asymmetric zones, per-instance `domain`; needs
  the inverted-color mode (D-08).
- `frontend/src/components/popovers/MetricStatPopover.tsx` — the tooltip
  pattern to follow (D-15).

### Tag semantics + denominator
- `.planning/notes/flaw-tag-definitions.md` — tag definitions incl. the
  2026-06-09 impact recalibration; source for popover definition paragraphs.
- `games.ply_count` (Phase 114.1) — per-game user-move denominator:
  FLOOR(ply_count/2) for white, CEIL(ply_count/2) for black; no
  game_positions scan (the §5 generator already uses this fast path).
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`MiniBulletChart`** — near-complete fit: CI whiskers, asymmetric
  `(neutralMin, neutralMax)` zones, per-instance `domain`, `center`. Only gap:
  the inverted-color mode (D-08) — success currently hard-paints right.
- **`is_opponent_expr`** — the read-time player/opponent split over
  `game_flaws`; the delta numerators are two `COUNT(*) FILTER` branches on it.
- **`fetch_stats_aggregates`** — the single-scan COUNT FILTER pattern; the
  comparison needs a per-game GROUP BY variant (per-game paired deltas, then
  mean + CI in Python).
- **`games.ply_count`** (114.1) — exact per-game user-move denominator with no
  `game_positions` access; same formula §5 used, keeping user deltas and
  benchmark zones on an identical basis.
- **`MetricStatPopover`** — the endgame tooltip pattern (D-15).
- **Existing filter plumbing** — `get_flaw_stats`'s filter kwargs +
  `apply_game_filters` already cover every filter FLAWCMP-03 requires.

### Established Patterns
- **LoadError / loading skeleton / empty-state ternary chain** in
  `FlawStatsPanel` — extend, don't reinvent, for the new grid zone states
  (loading / error / below-floor CTA / normal).
- **`data-testid` + ARIA conventions** (FLAWUI-06) — kebab-case,
  component-prefixed; every bullet row, popover trigger, and the grid container
  need them; desktop + mobile parity.
- **Zone-constant registries as plain Python modules** with typed entries
  (`endgame_zones.py`) — same shape for flaw-delta zones, minus codegen.

### Integration Points
- `FlawStatsPanel` Zone 3: `FlawTagDistribution` is replaced by the new bullet
  grid component; Zones 1–2 (Band minus toggle, trend) remain.
- `GET /api/library/flaw-stats` (or sibling): response grows the per-bullet
  comparison block (delta, ci_low, ci_high, zone bounds, axis domain,
  event counts for the zero-event state, analyzed_n for the gate).
- `useLibraryFlawStats` hook in the Stats tab (`GlobalStats`) — query key /
  fetch path if the endpoint shape changes.
</code_context>

<specifics>
## Specific Ideas

- Tooltips: "follow the tooltip style used in endgame metrics, add specific
  metric paragraphs if needed" (user's words) — i.e. `MetricStatPopover`
  structure, not a new disclosure framework.
- The user consistently chose the *simpler, data-faithful* option over
  editorial smoothing this session: raw Q1/Q3 verbatim, pooled global zones,
  no opponent-gap special-casing, keep-zones-with-caveat over zone-hiding.
  Planner should not reintroduce editorial machinery the user declined.
- Density preference: 3-col desktop grid accepted despite the chart-width
  trade-off — keep bullet rows compact.
</specifics>

<deferred>
## Deferred Ideas

- **Per-ELO zone refinement for endgame-phase / blunders** — revisit at the
  next benchmark refresh (D-06); §5 flags both, Cohen's d ≤ 0.28 today.
- **Tactic-motif bullets** (SEED-039) — the D-11/D-13 degradation paths are
  designed to absorb them zoneless later; nothing else in this phase.
- **Eval-coverage raising** (SEED-012 / FLAWCOV-01) — upstream dependency for
  feature reach; the D-10 CTA state is this phase's only touchpoint.

### Reviewed Todos (not folded)
All 10 `todo.match-phase` hits were generic keyword matches on the long-range
backlog (bitboard storage, phase-70 amendments, benchmark rebuild/skill-v2
ideas, old prod-backfill tasks, popover-copy tweak, tailwind label) — none
phase-115-scoped; none folded.
</deferred>

---

*Phase: 115-you-vs-opponent-comparison-api-bullet-grid-ui*
*Context gathered: 2026-06-11*
