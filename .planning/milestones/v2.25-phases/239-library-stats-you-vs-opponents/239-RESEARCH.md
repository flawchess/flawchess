# Phase 239: Library Stats You-vs-Opponents Redesign - Research

**Researched:** 2026-10-12
**Domain:** Benchmark §5 extension (SQL / per-user distributions), backend per-TC payloads (FastAPI + SQLAlchemy async), frontend gap-bar rework (React 19 + TanStack Query)
**Confidence:** HIGH for code facts and file locations (read this session); MEDIUM for the statistical consequences of the new benchmark basis (derived, not yet measured)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### Carried forward from SEED-198 (locked 2026-10-12, do not re-ask)
- **D-00a:** Gap bar is the one visual: 0 tick in the middle, grey benchmark IQR of the gap drawn where it is (may be off-centre), one dot red/blue/green, better always to the right, linear inside the band and saturating outside (`1 - e^-x`, x in band widths). No red/green halves, no CI whiskers.
- **D-00b:** The gap reads as words ("1.7 fewer", "0.42 more", "same"); typical gaps print white, only better/worse are green/red; the dot stays blue for typical.
- **D-00c:** Only the gap is on the page (tiles keep their "Opponents x.xx" line). A lucide Search icon opens a `RankedMetricPopover`-shell popover: definition + "Fewer is better", You/Opponents, typical gap range + verdict, basis, then greyed counts / 95% CI / p-value below a separator.
- **D-00d:** "flaws" / "blunders" / "mistakes", never "events".
- **D-00e:** Tiles: Blunders and Mistakes only (Inaccuracies tile, Severity card and "Flaw rate" retire).
- **D-00f:** Context tags: combos (hasty miss, low-clock miss) removed; four cards Clock | Game phase, Opponent errors | Lost advantages, tag names unchanged, one-line hint per tag.
- **D-00g:** "What stands out" card above the context cards: top 3 strengths / top 3 weaknesses ranked by distance outside the band in band widths, each with hint, coloured gap and Search popover, then one "Typical: …" line.
- **D-00h:** Tactic motifs: three tables in `TACTIC_GROUPS` order, Motif (+ "N of your flaws") | Missed | Allowed, full-size gap bars per 100 games, fixed column widths, phones stack Missed/Allowed under the motif, zero-count motifs listed under the table. "More tactics" accordion and the top-6 ranking (Phase 129 D-14) retire.
- **D-00i:** Advanced table collapsed by default with chevron and the `ShellyQuote` `EXPAND_HINT` "Click or tap for details" hint, hidden once open.
- **D-00j:** Card header bands throughout; Fredoka only for the h2 section titles.
- **D-00k:** Unchanged: Flaws Timeline visuals (it follows the selected TC), ELO Ratings, Results Breakdown, analyzed-coverage badge.

#### Filters and the TC switch
- **D-01:** The sidebar filter panel **stays** on the Library Stats tab (unlike Phase 238 D-01/D-02: there is no ranked sample here, so recency, platform, color and opponent-strength filters stay meaningful). All gap metrics are computed over the filtered analyzed games of the selected TC.
- **D-02:** The TC switch **narrows within the filter**: it offers only TCs allowed by the time-control filter that have ≥1 analyzed game in the current filters; zero-analyzed TCs are omitted. One synced switch across Flaw Stats, You vs. your opponents, and Tactic motifs. ELO Ratings and Results Breakdown keep reading the sidebar filters exactly as today (not the switch).
- **D-03:** A TC with ≥1 but fewer than 20 analyzed games (`FLAW_COMPARISON_GATE` / `TACTIC_COMPARISON_GATE`) stays in the switch; tiles still show the rates, and each gap-bar section shows a slot like "Not enough analyzed games yet (12 of 20)" instead of bars (Phase 238 D-09 shape).
- **D-04:** Default TC on load = TC with the most analyzed games in the current filters, ties to the faster TC, preferring an above-gate TC when one exists.
- **D-05:** The selected TC is remembered in `localStorage` with a key **separate from** the Endgame Stats page (Endgame counts ranked games, Library counts analyzed games). try/catch, renders fine without it; falls back to D-04 when the stored TC is not offered under the current filters.

#### Benchmark zones (tactic IQRs + flaw-delta refresh)
- **D-06:** Extend `/benchmarks` §5 (`scripts/benchmarks/chapter5.py`, `.claude/skills/benchmarks/SKILL.md` §5) with per-family Missed and Allowed paired-delta zones (you − opponent, per 100 games) plus a viability table, same methodology as the flaw-delta zones (equal-footing filter, per-(user, elo, tc) values, ≥30-contributor cell floor, Cohen's-d collapse verdict per axis). Unviable families (e.g. x-ray, en passant) get `has_zone = false`.
- **D-07:** **One basis for all zones:** the same §5 run recomputes the existing flaw-delta zones (blunder, mistake, and the 10 surviving context tags) on the **fully analyzed benchmark sample**, replacing the old Lichess-eval-only basis in `app/services/flaw_delta_zones.py`. Combos and `flaw_rate` drop from the registry. Some bands users see today will move. — **Reversibility:** reversible — registry constants, re-run §5 to change.
- **D-08:** **Don't wait for blitz.** Compute zones now from the finished classical + rapid full-analysis samples. **Blitz and bullet use the rapid zones as a stopgap** (for both tactic and flaw-delta zones) until their full-analysis samples exist; refresh later by re-running §5. The half-finished blitz sample is not used.
- **D-09:** The stopgap is **silent** in the UI (popover copy minimalism). The TC mapping is documented in the zone registry module and in the benchmark report.
- **D-10:** Granularity: let the collapse verdict decide per axis (TC: classical vs rapid only for now; Elo), with thin cells falling back to marginal/global zones, as for the existing flaw-delta zones. The registry may hold per-TC and/or per-Elo zones when they don't collapse.
- **D-11:** A tactic zone registry next to `flaw_delta_zones.py`, wired into `get_tactic_comparison` (`zone_lo` / `zone_hi` / `has_zone`). `has_zone = false` renders band-less: no grey band, blue dot, no verdict, popover without a typical range line.

#### Low sample and "What stands out"
- **D-12:** Low-sample fade = a named constant of **40 flaws (you + opponents) per cell**, applied to tactic cells **and** context-tag rows: faded, no red/green verdict (dot neutral), popover says "Too few flaws to call it". The planner sanity-checks 40 against the CI width on the owner's dev blitz/rapid data and adjusts the constant only if clearly off.
- **D-13:** "What stands out" ranks **context tags only** (not tactics, not the Blunders/Mistakes tiles). Faded (low-sample) rows never qualify.

### Claude's Discretion
- Plan split (likely: benchmark §5 + zone registries, backend payload, frontend rework).
- Payload shape: one TC per request vs one response with all offered TCs (endgame ranked-payload style); per-TC analyzed counts needed for D-02/D-03/D-04 either way.
- API cleanup: drop combo tags, `flaw_rate` and the top-6 tactic ranking from the payloads and repositories vs stop rendering; prefer removing dead backend paths (`library_repository.py` and `chapter5.py` combo computation) when nothing else consumes them.
- Which Elo the zone lookup uses if the Elo axis does not collapse (e.g. the user's current rating in the selected TC).
- Copy for the gate slot, "Typical: …" line, and the "What stands out" empty case (fewer than 3 strengths/weaknesses, or none).
- Where the TC-switch state lives (small store vs hook like `useEndgameStatsTc`), as long as D-05 persistence holds.

### Deferred Ideas (OUT OF SCOPE)
- Refresh all zones with blitz (and bullet) once their full-analysis benchmark samples finish (re-run §5; replaces the D-08 stopgap).
- Tactics in "What stands out" (rejected for now, D-13).

#### Reviewed Todos (not folded)
- `172-deferred-review-findings.md`, `2026-03-11-bitboard-storage-for-partial-position-queries.md`, `2026-08-29-variation-tree-nested-button.md`: keyword-only matches, unrelated to this phase.
</user_constraints>

<phase_requirements>
## Phase Requirements (coverage contract = CONTEXT decisions)

| ID | Description | Research Support |
|----|-------------|------------------|
| D-00a | Zero-centred gap bar, saturating outside band | §Pattern 5 (sketch `pos()` math verbatim + zero-width guards) |
| D-00b | Gap in words, colour rules | §Pattern 5 (`gapWords`, `fmt` verbatim), §Pattern 7 |
| D-00c | Search-icon popover on `RankedMetricPopover` shell | §Pattern 6 (extract shared shell), §Code Examples |
| D-00d | "flaws" wording | §Pitfall 9 (copy review) |
| D-00e | Blunders/Mistakes tiles only | §Pattern 4 (tiles read the per-TC `blunder`/`mistake` bullets), §Dead-code inventory |
| D-00f | Combos removed, four cards, hints | §Dead-code inventory, §Pattern 7 (hint copy, interpolate thresholds) |
| D-00g | "What stands out" ranking | §Pattern 8 |
| D-00h | Three tactic tables, per 100 games | §Pattern 4 (per-100-games unit moves to backend), §Pattern 9 |
| D-00i | Advanced collapsed + EXPAND_HINT | §Pattern 9, §Pitfall 10 (`text-xs` vs floor rule) |
| D-00j | Card header bands, Fredoka h2 | §Pattern 9 (`font-brand`, `AccordionTrigger band`) |
| D-00k | Timeline follows selected TC | §Pattern 4 (`trend_by_tc` on `/flaw-stats`) |
| D-01 | Sidebar filters stay | §Pattern 4 (filters still flow through `apply_game_filters`) |
| D-02 | TC switch within filter, ≥1 analyzed | §Pattern 4 (`tcs[]` only lists TCs with analyzed_n ≥ 1 within the TC filter) |
| D-03 | Below-gate slot per section | §Pattern 4 (bullets computed for every listed TC; `below_gate` per TC) |
| D-04 | Default TC rule | §Pattern 10 (`pickDefaultTc` generalisation) |
| D-05 | Separate localStorage key | §Pattern 10 (`library_stats_tc`, store factory) |
| D-06 | Tactic Missed/Allowed zones in §5 | §Pattern 1, §Pattern 2 |
| D-07 | Flaw-delta zones recomputed on full-analysis sample | §Pattern 1 (base CTE on `benchmark_selection`), §Pitfall 1 (bands widen) |
| D-08 | Classical + rapid only; blitz/bullet → rapid | §Pattern 1 (`FULL_ANALYSIS_TRANCHES`), §Pattern 3 (`ZONE_TC_FOR`) |
| D-09 | Silent stopgap, documented in registry + report | §Pattern 3, §Benchmark run logistics |
| D-10 | Collapse verdict decides granularity | §Pattern 3, §Pitfall 4 (marginal floor not enforced today) |
| D-11 | Tactic registry wired into `get_tactic_comparison` | §Pattern 3, §Pattern 4 |
| D-12 | 40-flaw fade constant + sanity check | §D-12 sanity check (formula + exact SQL), §Pattern 4 (`low_sample` from backend) |
| D-13 | What stands out = context tags only, faded excluded | §Pattern 8 |
</phase_requirements>

## Summary

The phase has three separable parts with a clean dependency order: (1) a §5 benchmark extension that switches the zone basis to the Phase 212 full-analysis lane and adds 38 tactic metrics (19 families x Missed/Allowed), (2) backend registries plus per-TC payloads, (3) the frontend rework. Everything the redesign needs already exists in some form: the paired per-game delta estimator, the Wald-z mean CI and p-value helpers, the Phase 238 TC store/switch/popover shell, and the sketch's exact gap-bar math. No new packages.

The "fully analyzed benchmark sample" is concretely the `benchmark_selection` table (Phase 212): a capped (100 games/user/TC), md5-seeded random, equal-footing draw per TC tranche, where both arms (lichess-analyzed and never-analyzed) were re-evaluated by our engine. "Finished" means every selected game has `full_evals_completed_at`, `full_pv_completed_at`, `best_moves_completed_at` and `blobs_completed_at` set. Live status on 2026-10-12: classical and rapid are 99.9% done, blitz 74.1%, bullet 0 (verified via `scripts/benchmark_lane.py status --all-tranches`). Today's §5 does **not** use this sample at all: it reads `g.evals_completed_at IS NOT NULL` over the whole cohort (1.22M games), which is the broad, differently-selected basis D-07 replaces.

The most important non-obvious finding: tactic motifs depend on PV blobs (a motif is suppressed to NULL while its blob is pending, `flaws_service.py` `blobs_pending`), so the benchmark base must require `blobs_completed_at IS NOT NULL`. The second: the lane caps users at 100 games per TC, so per-user means are much noisier than on the old basis. Benchmark IQRs of per-user deltas include that sampling noise, so the flaw-delta bands will widen and the rare tactic bands may be mostly noise. This does not reopen D-07, but the owner should see a noise diagnostic next to each zone before the registry values are locked (Open Question 1).

**Primary recommendation:** Three plans in sequence: Plan 01 = §5 extension on `benchmark_selection` (classical + rapid), report splice, diff-gate refresh, and both zone registries authored from the run. Plan 02 = backend per-TC payloads for all three endpoints in one response each (all offered TCs, no refetch on switch), combos/flaw_rate/top-6 removed, tactic rates in per-100-games, `low_sample` computed server-side. Plan 03 = frontend (GapBar, shared popover shell, generalised TC store/switch, tiles, What stands out, four context cards, three tactic tables).

## Project Constraints (from CLAUDE.md)

- No magic numbers: `LOW_SAMPLE_MIN_FLAWS = 40`, `PER_100_GAMES = 100`, gap-bar geometry constants, top-N = 3, storage key all named. [CITED: ./CLAUDE.md "Coding Guidelines"]
- `Literal[...]` for fixed sets in schemas and service/repo params (TC, metric keys, family keys, orientation); `Sequence[str]` for params accepting Literal lists. [CITED: ./CLAUDE.md]
- `uv run ty check app/ tests/ scripts/` zero errors; explicit return types; `# ty: ignore[rule]` only where unfixable. [CITED: ./CLAUDE.md]
- Nesting depth ≤ 4 (gated by `scripts/check_function_size.py app/ --fail-over-depth 4` and eslint `max-depth`). [CITED: ./CLAUDE.md]
- `apply_game_filters()` is the single filter implementation; never duplicate filter logic. [CITED: ./CLAUDE.md]
- Router prefix convention `APIRouter(prefix="/library")` with relative paths (already in place). [VERIFIED: app/routers/library.py:35 `router = APIRouter(prefix="/library", tags=["library"])`]
- Sentry: `capture_exception` in non-trivial except blocks in services/routers; no variables in messages; context via `set_context`. Existing comparison functions follow this pattern (keep it). [CITED: ./CLAUDE.md]
- Never `asyncio.gather` on one `AsyncSession`; run the per-TC queries sequentially. [CITED: ./CLAUDE.md]
- API responses never expose internal hashes (not relevant here). [CITED: ./CLAUDE.md]
- Pre-merge gate (ruff format/check, ty x2, function-size gate, `pytest -n auto -x`, frontend lint/build/test/knip) before squash-merge. [CITED: ./CLAUDE.md]
- CHANGELOG `## [Unreleased]` bullets when the phase merges. [CITED: ./CLAUDE.md]
- Frontend: theme colours from `theme.ts`; `text-sm` floor except hover/tap popover bodies; `data-testid` on every interactive element; `isError` branch on every query chain; knip in CI; run `npm run build` (tsc -b) before integrating shared-type changes; every new user-facing feature ships its `trackFeature` event registered in `analytics.ts`; popovers use `useTrackedPopoverOpen`; never interpolate free values into popover testIds. [CITED: frontend/CLAUDE.md]
- Benchmarks are the source of truth for "typical" copy; popover copy minimalism (WHAT + sign convention); no flame icons. [CITED: user memory feedback_benchmark_source_of_truth, feedback_popover_copy_minimalism, feedback_no_flame_icons]
- Plans must not gate on `bin/reset_db.sh`. [CITED: user memory feedback_no_dev_db_reset_in_plans]

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Benchmark zones (flaw + tactic IQR, collapse verdicts) | Offline script (`scripts/benchmarks/chapter5.py`) against benchmark DB | Report (`reports/benchmark/benchmarks-latest.md`) | Population statistics are computed offline; no endpoint (D-09 of Phase 114 precedent) |
| Zone registries | API / Backend (`app/services/*_zones.py`) | — | Backend-owned per Phase 115 D-07; endpoint embeds `zone_lo/zone_hi/has_zone`; no TS codegen |
| Per-TC analyzed counts, gate, gap stats (mean, CI, p, low_sample) | API / Backend (`library_service`) | Database (repository aggregation) | Statistics and thresholds belong with the data; one constant for 40 flaws |
| Filter application | Database / repository (`apply_game_filters`) | — | Single filter implementation |
| TC selection, default rule, persistence | Browser / Client (module store + localStorage) | — | UI state, no server round-trip on switch |
| Gap-bar geometry, gap words, verdict colour, What-stands-out ranking | Browser / Client | — | Pure presentation of server numbers |
| Flaws Timeline per TC | API / Backend (`/flaw-stats` `trend_by_tc`) | Browser picks the series | Trend computed server-side; client selects |

## Standard Stack

No new libraries. Everything is in-repo. [VERIFIED: codebase read]

### Core (existing, reuse)
| Asset | Location | Purpose |
|-------|----------|---------|
| D-01 paired-delta estimator | `scripts/benchmarks/chapter5.py` `_per_user_cte()` | Per-game (player − opp), per-user mean, ≥20 floor |
| Distribution + Cohen's d | `scripts/benchmarks/distribution.py` (`agg_select`, `GROUPING_SETS`, `split_grouping_sets`, `verdict`) | Pooled + ELO/TC marginals + verdict |
| Mean CI / p-value | `app/services/library_service.py` `_compute_mean_ci` (1496-1516), `_two_sided_p` (1519-1536) | Wald-z on per-game deltas, stdlib only |
| Per-game fetches | `app/repositories/library_repository.py` `fetch_flaw_comparison` (2014), `fetch_tactic_comparison` (2300), `count_filtered_and_analyzed` (1880) | LEFT JOIN anchor so clean games count as 0 |
| TC store + switch | `frontend/src/hooks/useEndgameStatsTc.ts`, `components/endgames/stats/TcSwitch.tsx` | Synced selection, localStorage, pinned default |
| Popover shell | `components/endgames/stats/RankedMetricPopover.tsx` | Search trigger, 100 ms hover-open, Portal, `text-xs` body, `useTrackedPopoverOpen` |
| Bar look | `components/endgames/stats/PercentileBar.tsx` + theme `PERCENTILE_TRACK`, `PERCENTILE_TYPICAL_BAND`, `PERCENTILE_MEDIAN_TICK` | Track, band, tick, dot styling |
| Dot colours | `rankedMetrics.ts` `percentileBandColor`: `ZONE_DANGER` / `GAUGE_NEUTRAL` / `ZONE_SUCCESS` | Same red/blue/green as Endgame |
| Collapsible card | `components/ui/accordion.tsx` `AccordionTrigger band` + `group/accordion-trigger`; `EndgameStatsTab.tsx` `SectionInsightSlot` precedent | Advanced tactics card |

**Installation:** none.

## Package Legitimacy Audit

This phase installs no external packages (backend or frontend). No `npm install` / `uv add` steps.

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| (none) | — | — | — | — | — | — |

**Packages removed due to [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

## Architecture Patterns

### System Architecture Diagram

```
 OFFLINE (Plan 01)                                   ONLINE (Plans 02/03)
 ─────────────────                                   ────────────────────
 benchmark DB :5433                                  Browser: Library > Stats tab
   benchmark_selection (classical, rapid; armed)       │ useFilterStore (sidebar filters, unchanged)
     JOIN games (full_evals+pv+blobs done)             ▼
     JOIN selected_users (equal footing, TC anchor)   3 parallel queries, all filters, NO tc narrowing
     LEFT JOIN game_flaws                              ├─ GET /library/flaw-stats      → trend_by_tc[]
        │                                              ├─ GET /library/flaw-comparison → tcs[{tc, analyzed_n, below_gate, bullets[12]}]
        ▼                                              └─ GET /library/tactic-comparison → tcs[{tc, analyzed_n, below_gate, bullets[38]}]
   per-game Δ: flaws /user_moves, tactics /game          │
   per-(user, elo, tc) mean, ≥20 games                    ▼
        │                                              useLibraryStatsTc(tcs from flaw-comparison)
        ▼                                                default = D-04, stored = localStorage 'library_stats_tc'
   GROUPING SETS → pooled / ELO / TC quartiles            │ selectedTc (client-only, switch never refetches)
   Cohen's d per axis + viability (+ noise diag)          ▼
        │                                              ┌───────────────┬──────────────────────┬───────────────────┐
        ▼                                              │ Flaw Stats    │ You vs. opponents     │ Tactic motifs     │
   benchmarks-latest.md §5 (narrated)                  │ tiles (B, M)  │ What stands out (D-13)│ 3 tables          │
        │ owner reads verdicts                          │ + Timeline    │ 4 context cards       │ Advanced collapsed│
        ▼                                              └───────────────┴──────────────────────┴───────────────────┘
   app/services/flaw_delta_zones.py   ──────────────►  backend per bullet: zone_lo/zone_hi/has_zone
   app/services/tactic_delta_zones.py (new)             (blitz/bullet → rapid zone, silent)
                                                       backend per bullet: low_sample (you+opp flaws < 40)
```

### Recommended file structure (new/changed)

```
scripts/benchmarks/chapter5.py            # full-analysis base CTE, 12 flaw + 38 tactic metrics, viability, noise diag
.claude/skills/benchmarks/SKILL.md        # §5 rewritten: basis, metric list, tactic estimator, stopgap mapping
tests/scripts/benchmarks/test_chapter5_diff.py   # EXPECTED_* regenerated on the new basis (on-demand gate)
app/services/flaw_delta_zones.py          # 12 metrics, per zone-TC bands, ZONE_TC_FOR mapping (D-08/D-09)
app/services/tactic_delta_zones.py        # NEW: (family, orientation) → per zone-TC band or None (has_zone=false)
app/schemas/library.py                    # FlawComparisonTc / TacticComparisonTc / FlawTrendTc, Literal keys
app/repositories/library_repository.py    # per-TC counts, TC column on anchors, combo + flaw_rate columns removed
app/services/library_service.py           # per-TC bucketing, ×100 tactic unit, low_sample, top-6 removed
frontend/src/lib/gapBar.ts                # NEW: pure gapPosition / gapVerdict / gapWords / formatters
frontend/src/components/library/stats/    # NEW dir: GapBar, GapPopover, GapRow, FlawTiles, WhatStandsOut,
                                          #   ContextTagCards, TacticTables, LibraryTcSwitch wiring
frontend/src/components/ui/metric-info-popover.tsx (or endgames/stats/) # shared Search-popover shell
frontend/src/hooks/tcSelectionStore.ts    # NEW: store factory; useEndgameStatsTc + useLibraryStatsTc wrap it
```

### Pattern 1: Full-analysis base for §5 (D-07, D-08)

**What:** Replace `base_games` in `_per_user_cte()` and `_compute_viability()` (today `g.evals_completed_at IS NOT NULL`) with a join through `benchmark_selection`.

Today's base [VERIFIED: scripts/benchmarks/chapter5.py:231-239]:
```
"base_games AS MATERIALIZED (\n"
"  SELECT g.id AS game_id, g.user_id, g.user_color,\n"
f"         ({sql.USER_ELO_AT_GAME_SQL}) AS ueag,\n"
"         su.tc_bucket AS tc\n"
"  FROM games g\n"
"  JOIN selected_users su ON su.user_id = g.user_id\n"
f"  WHERE {sql.BASE_GAME_FILTER}\n"
"    AND g.evals_completed_at IS NOT NULL\n"
```

`benchmark_selection` columns [VERIFIED: app/models/benchmark_selection.py:105-126]: `__tablename__ = "benchmark_selection"`, `CheckConstraint("tc_tranche IN ('bullet','blitz','rapid','classical')", ...)`, `game_id ... ForeignKey("games.id", ondelete="CASCADE")`, `tc_tranche: Mapped[str] = mapped_column(String(20), nullable=False)`, `lichess_arm: Mapped[bool]`, `armed: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"), default=False)`.

Lane tunables [VERIFIED: scripts/benchmark_lane.py:85-90]: `GAMES_PER_USER_PER_TC_CAP = 100`, `EQUAL_FOOTING_MAX_RATING_GAP = 100`, `SELECTION_SEED = "212-benchmark-lane"`, `TC_TRANCHES = ("classical", "rapid", "blitz", "bullet")`.

Recommended base (values not quoted above are proposals):
```python
# Phase 239 D-08: only tranches whose full-analysis lane has finished. Blitz/bullet
# zones fall back to rapid in the app registry (ZONE_TC_FOR), never computed here.
FULL_ANALYSIS_TRANCHES: tuple[sql.TcBucket, ...] = ("classical", "rapid")  # [ASSUMED name]

def _base_games_cte() -> str:
    tranches = ", ".join(f"'{t}'" for t in FULL_ANALYSIS_TRANCHES)
    return (
        "base_games AS MATERIALIZED (\n"
        "  SELECT g.id AS game_id, g.user_id, g.user_color,\n"
        f"         ({sql.USER_ELO_AT_GAME_SQL}) AS ueag,\n"
        "         su.tc_bucket AS tc\n"
        "  FROM benchmark_selection bs\n"
        "  JOIN games g ON g.id = bs.game_id\n"
        "  JOIN selected_users su ON su.user_id = g.user_id\n"
        f"  WHERE bs.armed AND bs.tc_tranche IN ({tranches})\n"
        f"    AND {sql.BASE_GAME_FILTER}\n"          # TC anchor keeps one su row per game
        "    AND g.full_evals_completed_at IS NOT NULL\n"
        "    AND g.full_pv_completed_at IS NOT NULL\n"
        "    AND g.blobs_completed_at IS NOT NULL\n"  # tactic motifs are final only once blobs exist
        ")"
    )
```
Use it in **both** `_per_user_cte()` and `_compute_viability()` (today they duplicate the base; one helper removes the drift risk).

**Why each predicate:**
- `bs.tc_tranche IN ('classical','rapid')`: D-08, the half-finished blitz tranche must not leak in. Verified live progress 2026-10-12: classical 99.9%, rapid 99.9%, blitz 74.1%, bullet 0 selected. [VERIFIED: `uv run python scripts/benchmark_lane.py status --all-tranches --db benchmark`, output: "status classical ... percent complete (best_moves_done / selected): 99.9%", "status rapid ... 99.9%", "status blitz ... 74.1%", "status bullet: ... selected=0"]
- `bs.armed`: unarmed rows are invisible to claim lanes, so they cannot be analyzed. [VERIFIED: app/models/benchmark_selection.py:73-76 docstring "an unarmed row is invisible to all five claim lanes"]
- `blobs_completed_at IS NOT NULL`: a detected motif is suppressed to NULL while its blob is pending (`blobs_pending=True` path) and self-heals at the tier-4 retag. Without this predicate, games mid-pipeline contribute false zero tactic counts. [VERIFIED: app/services/flaws_service.py:730-738 docstring "When True AND a motif was detected AND pv_blob is None AND pre_flaw_eval_cp is not None, the motif cannot yet be gate-checked, so it is suppressed to NULL"]; `blobs_completed_at` semantics [VERIFIED: app/models/game.py:270-280 "stamped `now()` when every flaw ply's blob is written, cleared back to NULL when a reclassification ... inserts a fresh NULL-blob ply"].
- Do **not** use `lichess_evals_at` as a provenance filter: on lane games it stays set for the lichess arm even though the stored evals are now ours (homogenized). [CITED: .claude/skills/benchmarks/SKILL.md §5 "Mixed eval provenance" — "`games.lichess_evals_at` no longer implies the stored `eval_cp` came from lichess"]

### Pattern 2: Tactic metrics in §5 (D-06)

**What:** 19 families x {missed, allowed} = 38 metrics, estimator per game = `player_count − opp_count` (count per game, NOT divided by moves), per-user mean over ≥20 games, rendered x100 as "per 100 games".

Count predicate must equal the app's comparison predicate exactly: motif column of that orientation in the family's ints AND confidence ≥ 70.
- Family map [VERIFIED: app/repositories/library_repository.py:119-215, keys verbatim]: `"fork"`, `"skewer"`, `"pin"`, `"x_ray"`, `"double_check"`, `"discovered_check"`, `"discovered_attack"`, `"trapped_piece"`, `"hanging"`, `"mate"`, `"deflection"`, `"intermezzo"`, `"interference"`, `"capturing_defender"`, `"attraction"`, `"sacrifice"`, `"en_passant"`, `"under_promotion"`, `"promotion"` (19 keys; `"mate"` = `BACK_RANK_MATE, MATE, SMOTHERED_MATE, ANASTASIA_MATE, HOOK_MATE, ARABIAN_MATE, BODEN_MATE, DOUBLE_BISHOP_MATE, DOVETAIL_MATE`).
- Int values [VERIFIED: app/services/tactic_detector.py:104-134]: `FORK = 1`, `HANGING_PIECE = 2`, `PIN = 3`, `SKEWER = 4`, `DOUBLE_CHECK = 5`, `DISCOVERED_ATTACK = 6`, `BACK_RANK_MATE = 7`, `MATE = 8`, `DEFLECTION = 9`, `ATTRACTION = 10`, `INTERMEZZO = 11`, `X_RAY = 12`, `INTERFERENCE = 13`, `CAPTURING_DEFENDER = 16`, `SACRIFICE = 17`, `SMOTHERED_MATE = 18` … `DOVETAIL_MATE = 24`, `DISCOVERED_CHECK = 25`, `TRAPPED_PIECE = 26`, `EN_PASSANT = 27`, `PROMOTION = 28`, `UNDER_PROMOTION = 29`.
- Confidence gate [VERIFIED: app/repositories/library_repository.py:68 `_TACTIC_CHIP_CONFIDENCE_MIN: int = 70`; app/services/library_service.py:1715 `MIN_TACTIC_CHIP_CONFIDENCE: int = _TACTIC_CHIP_CONFIDENCE_MIN`].
- The app's join gate [VERIFIED: app/repositories/library_repository.py:2400-2406]: `.outerjoin(GameFlaw, (GameFlaw.game_id == anchor_subq.c.game_id) & (GameFlaw.user_id == user_id) & motif_col.isnot(None) & (conf_col >= tactic_confidence_min))`.

**Import, don't copy:** in `chapter5.py` import `FAMILY_TO_MOTIF_INTS` from `app.repositories.library_repository` and `MIN_TACTIC_CHIP_CONFIDENCE` from `app.services.library_service`, so a future family remap re-groups the benchmark automatically. Scripts already import `app.*` (`scripts/gen_benchmarks.py:71 from app.core.config import db_url_for_target`). [VERIFIED: grep scripts/gen_benchmarks.py]. Iterate the dict in Python to build `COUNT(*) FILTER (...)` columns; column names are `p_{family}_{orient}` / `o_{family}_{orient}` (all identifiers from a closed set, no user input).

Two-orientation columns can live in one per-game CTE if the LEFT JOIN to `game_flaws` is unconditional (as for the flaw metrics) and the motif/confidence predicate moves into each `FILTER`. That gives one scan for 12 flaw + 38 tactic metrics (100 count columns), cheaper than two scans. [ASSUMED: performance; the old 15-metric scan took ~86 s on 1.2M games, the new base is ~146k games]

**Unit:** the existing `render.Unit` is `Literal["cp", "score", "pp", "pp3"]` with `"pp"` scale 100 [VERIFIED: scripts/benchmarks/render.py:72-75]. Add a new unit (e.g. `"per100g"`, scale 100, suffix " /100 games") rather than mislabelling tactic numbers as "pp".

**Report shape:** 38 full per-metric sections would bloat the report. Render tactics as one compact table (family, orientation, n, Q1, median, Q3, classical Q1/Q3, rapid Q1/Q3, TC d + verdict, ELO d + verdict, pct_nonzero, degenerate-IQR flag). Keep full sections for the 12 flaw metrics.

**Viability rule for `has_zone=false` (D-06):** recommend `has_zone = false` when the pooled IQR is degenerate (`p25 == p75`, typically both 0) OR `pct_nonzero < 50%` (SKILL.md already flags < 50% as a viability concern). A zero-width band at 0 would paint any non-zero gap as "worse/better than typical", which is wrong. [ASSUMED: thresholds; owner confirms from the viability table]

### Pattern 3: Zone registries (D-07..D-11)

Current registry [VERIFIED: app/services/flaw_delta_zones.py:38-60] is pooled-only with a `domain` field, e.g. `"blunder": FlawDeltaZoneSpec(zone_lo=-0.31, zone_hi=+0.25, domain=1.4)`, and includes `"flaw_rate"`, `"hasty_miss"`, `"low_clock_miss"` (to drop).

Recommended shape (uniform per zone-TC lookup; a collapsed TC axis is just identical values):
```python
TimeControlBucket = Literal["bullet", "blitz", "rapid", "classical"]   # app/schemas/normalization.py:19
ZoneTc = Literal["rapid", "classical"]
FlawDeltaMetric = Literal["blunder", "mistake", "low_clock", "hasty", "unrushed",
                          "opening", "middlegame", "endgame_phase", "miss", "lucky",
                          "reversed", "squandered"]

@dataclass(frozen=True)
class ZoneBand:
    zone_lo: float
    zone_hi: float

# D-08/D-09 stopgap: blitz and bullet have no finished full-analysis sample, so they
# read the rapid zones. Silent in the UI; documented here and in benchmarks-latest.md §5.
ZONE_TC_FOR: Mapping[TimeControlBucket, ZoneTc] = {
    "bullet": "rapid", "blitz": "rapid", "rapid": "rapid", "classical": "classical",
}
FLAW_DELTA_ZONES: Mapping[FlawDeltaMetric, Mapping[ZoneTc, ZoneBand]] = {...}

def flaw_delta_zone(metric: FlawDeltaMetric, tc: TimeControlBucket) -> ZoneBand: ...
```
`TimeControlBucket` already exists as `Literal["bullet", "blitz", "rapid", "classical"]` [VERIFIED: app/schemas/normalization.py:19]; import it rather than redefining.

Tactic registry (`app/services/tactic_delta_zones.py`): `Mapping[tuple[TacticFamily, TacticOrientationSide], Mapping[ZoneTc, ZoneBand] | None]` where `None` = unviable (`has_zone=False`). Units: per 100 games.

- Drop `domain`: the gap bar derives its scale from the band (D-00a), so `domain` loses its only consumer when `MiniBulletChart` leaves the Library.
- Elo axis: the 2026-08-18 verdicts for all 15 flaw metrics were collapse/review on ELO (max |d| 0.27). [CITED: reports/benchmark/benchmarks-latest.md header "Mostly-collapse verdicts (max d = 0.27)"] If the new run keeps ELO at collapse/review, ship no Elo keying (YAGNI). If any metric gets "keep separate" (≥ 0.5) on ELO, key that metric by Elo bucket and look up the user's Elo from `user_rating_anchors.anchor_rating` for the selected TC (Lichess-equivalent, already converts chess.com; filter-independent). Raw game ratings would mix chess.com and Lichess scales against a Lichess-only benchmark. Fall back to the TC/global band when the user has no anchor row. [VERIFIED: app/models/user_rating_anchors.py:96-111 `__tablename__ = "user_rating_anchors"`, `anchor_rating: Mapped[int]`]
- Registry values are hand-authored from the narrated report (Phase 115 precedent, no generator) and rounded to the existing 0.01 grid for flaw metrics. [VERIFIED: app/services/flaw_delta_zones.py:24-26 docstring "The 0.01 rounding grid keeps a visible neutral band on the rare tags"]

### Pattern 4: Per-TC payloads, all offered TCs in one response (D-02, D-03, D-04, D-00k)

**Recommendation: one response per endpoint containing every offered TC.** Reasoning:
1. Today's default request already scans every filtered analyzed game pooled across TCs (`fetch_flaw_comparison` with `time_control=None`), so bucketing the same rows by `Game.time_control_bucket` costs about the same as today. One-TC-per-request makes each request cheaper but adds a refetch and spinner on every switch click, and the counts for D-02/D-04 would need an extra request anyway.
2. The switch becomes purely client-side, like Phase 238 (`EndgameStatsRankedResponse.tcs: list[RankedTcStats]`). [VERIFIED: grep app/schemas/endgames.py:557 `tcs: list[RankedTcStats]`]
3. All three queries fire in parallel on load; no request depends on the selected TC (a TC-param `/flaw-stats` call would wait for the counts first).

Proposed schemas (names are proposals; `TimeControlBucket` import is verified):
```python
class FlawBullet(BaseModel):
    tag: FlawDeltaMetric               # was str
    delta: float | None; ci_low: float | None; ci_high: float | None
    player_rate: float | None; opp_rate: float | None; p_value: float | None
    player_events: int; opp_events: int
    zone_lo: float; zone_hi: float; has_zone: bool
    low_sample: bool                   # player_events + opp_events < LOW_SAMPLE_MIN_FLAWS (D-12)
    # `domain` dropped

class FlawComparisonTc(BaseModel):
    tc: TimeControlBucket
    analyzed_n: int
    below_gate: bool                   # analyzed_n < FLAW_COMPARISON_GATE
    bullets: list[FlawBullet]          # 12, ALWAYS computed (tiles need rates below gate, D-03)

class FlawComparisonResponse(BaseModel):
    tcs: list[FlawComparisonTc]        # fast→slow, only TCs with analyzed_n >= 1 (D-02)
    analyzed_gate: int

class TacticBullet(BaseModel):         # rates/delta/CI now PER 100 GAMES
    family: TacticFamily; orientation: Literal["missed", "allowed"]
    you_rate, opp_rate, delta, ci_low, ci_high, p_value, you_events, opp_events,
    zone_lo, zone_hi, has_zone, low_sample

class TacticComparisonTc(BaseModel):
    tc: TimeControlBucket; analyzed_n: int; below_gate: bool
    bullets: list[TacticBullet]        # 38, fixed FAMILY_TO_MOTIF_INTS order, missed then allowed

class FlawTrendTc(BaseModel):
    tc: TimeControlBucket
    points: list[FlawTrendPoint]
# FlawStatsResponse gains trend_by_tc: list[FlawTrendTc]
```

Implementation notes:
- **Counts by TC:** new repo function (e.g. `count_analyzed_by_tc`) = `_filtered_games_base(...)` ∩ `_analyzed_game_ids_subquery(user_id)` joined back to `Game` and grouped by `Game.time_control_bucket`. Drop NULL buckets: `time_control_bucket` is nullable [VERIFIED: app/models/game.py:155-157 `time_control_bucket: Mapped[str | None] = mapped_column(time_control_bucket_enum)`]. The time-control sidebar filter is already applied by `apply_game_filters`, so "allowed by the filter" (D-02) falls out for free.
- **Per-game rows:** add `Game.time_control_bucket.label("tc")` to the anchor subqueries in `fetch_flaw_comparison` and `fetch_tactic_comparison`, include it in `group_by`, then bucket rows in Python and run the existing `_compute_bullets` / `_compute_tactic_bullets` per bucket.
- **Gate:** compute bullets for every listed TC (≥ 1 analyzed game) and set `below_gate` per TC. The old early return skipped the per-game query only when the pooled count was < 20; the cost of computing below-gate TCs is negligible.
- **Tactic unit:** multiply per-game counts by `PER_100_GAMES = 100` before `_compute_mean_ci`/`_two_sided_p` (CI and mean scale linearly; p-value is scale-invariant). The current code is per game [VERIFIED: app/services/library_service.py:1752-1754 "Per-game rate: events per game (not per 100 moves — D-04 per-game normalization)."].
- **`low_sample`:** a backend constant `LOW_SAMPLE_MIN_FLAWS: int = 40` in `library_service.py`, applied per bullet. One source of truth, pytest-testable, and the frontend's "What stands out" filter just reads the boolean.
- **Tiles:** read `player_rate` / `opp_rate` / `delta` / zone from the selected TC's `blunder` and `mistake` bullets. These equal the flaw-stats macro per-100 rates by construction. [VERIFIED: app/schemas/library.py:279-284 "This matches the you-vs-opponent bullet's player_rate for mistake/blunder exactly (same per-game-then-mean aggregation ...)"]
- **Flaws Timeline:** add `Game.time_control_bucket` to `fetch_flaw_trend_rows` and build one `_compute_flaw_trend` series per TC (`trend_by_tc`). No extra query.
- **`/flaw-stats` consumers:** `FlawsTab.tsx` uses `useLibraryFlawStats(UNFILTERED_PROBE_FILTERS, NO_FLAW_FILTER)` only for `analyzed_n`; keep `analyzed_n`/`total_n` top-level. [VERIFIED: grep frontend/src/pages/library/FlawsTab.tsx:233-238]
- **Ordering:** emit TCs in `bullet, blitz, rapid, classical` order (same as `TC_ORDER` in `useEndgameStatsTc.ts:25`).

### Pattern 5: Gap-bar math (D-00a, D-00b)

Source of truth: the owner-approved sketch. [VERIFIED: .planning/sketches/010-library-stats-you-vs-opponents/index.html:223-226, 362-380]
```js
const BAND_HALF_POS = 25;     // the wider side of the band reaches 25% from the centre
const EDGE_POS = 3;           // outermost dot position (% from either edge)
const OUTER_SPAN = 50 - BAND_HALF_POS - EDGE_POS;
const MIN_FLAWS = 40;         // fade a row / column below this many flaws (you + opponents)
const verdict = (d, lo, hi) => d < lo ? 'hi' : d > hi ? 'lo' : 'md';   // lower = better for every flaw metric
const fmt = v => Math.abs(v) >= 10 ? v.toFixed(0) : Math.abs(v) >= 1 ? v.toFixed(1) : v.toFixed(2);
const gapWords = d => Math.abs(d) < 0.005 ? 'same' : `${fmt(Math.abs(d))} ${d < 0 ? 'fewer' : 'more'}`;
function pos(d, lo, hi) {
  const s = Math.max(Math.abs(lo), Math.abs(hi));
  const a = Math.abs(d);
  let off;
  if (a <= s) off = BAND_HALF_POS * a / s;
  else off = BAND_HALF_POS + OUTER_SPAN * (1 - Math.exp(-(a - s) / (hi - lo)));
  return d < 0 ? 50 + off : 50 - off;
}
```
Band drawn from `pos(hi)` (left) to `pos(lo)` (right). Port into `frontend/src/lib/gapBar.ts` as typed pure functions with named constants, plus:
- **Guards the sketch lacks:** `hi - lo === 0` (division by zero in the saturating branch) and `s === 0` (division by zero inside the band). With `has_zone=false` there is no band at all: use a fixed reference scale for the dot position (e.g. the selected TC's `|you_rate| + |opp_rate|` or a named default), no verdict. [ASSUMED: band-less scale choice, planner picks]
- `MIN_FLAWS` here is the frontend copy of the backend constant; prefer the backend `low_sample` boolean so the constant lives once.
- `has_zone=false` or `low_sample`: verdict forced to typical (blue dot, white gap words), row faded.

### Pattern 6: Shared Search-popover shell (D-00c)

`RankedMetricPopover` couples the shell (trigger, 100 ms hover-open, Portal, `side="top"`, `sideOffset={4}`, `text-xs` body, `useTrackedPopoverOpen(testId)`) to ranked-metric content. [VERIFIED: frontend/src/components/endgames/stats/RankedMetricPopover.tsx:118-183] Extract the shell into a generic component (children = body) and make both `RankedMetricPopover` and the new gap popover use it. Do not copy-paste the hover/timer logic a third time (`TacticComparisonGrid` already has its own copy that goes away).

Popover testIds should carry a `tc` segment so analytics collapses TCs: e.g. `gap-popover-hasty-tc-blitz`; `popoverTargetFromTestId` strips TC segments that follow a `tc`/`card` segment. [VERIFIED: frontend/CLAUDE.md "per-TC segments after `tc`/`card`" + grep frontend/src/lib/analytics.ts:565-579]

### Pattern 7: Hint copy (D-00f)

One-line hints from the sketch (`index.html:319-332`) are the starting point, but two hard-code thresholds ("15+ points", "under 5% of your time left"). Build them from `@/generated/flawThresholds` like `TAG_DEFINITIONS` does (`tagDefinitions.ts` imports `TIME_PRESSURE_CLOCK_FRACTION` etc.), keep popover definitions on `TAG_DEFINITIONS`. [VERIFIED: frontend/src/lib/tagDefinitions.ts:17-26 imports from '@/generated/flawThresholds']

### Pattern 8: "What stands out" (D-00g, D-13)

Sketch algorithm [VERIFIED: index.html `renderHighlights`, read via sed this session; not quoted as discrete values]: over the 10 context tags only, verdict per tag; distance = `(lo - d)/(hi - lo)` below band, `(d - hi)/(hi - lo)` above band, 0 inside; top 3 per side by distance desc; then "Typical: a, b, c." listing typical tags. Add for D-13: skip `low_sample` rows and `has_zone=false` rows; guard `hi - lo === 0`. Empty-case copy is discretion (sketch: "Nothing outside the typical range."). Sign mapping: `d < lo` = fewer flaws = strength.

### Pattern 9: Tactic tables + collapsible Advanced (D-00h, D-00i, D-00j)

- Group membership/order from `TACTIC_COMPARISON_FAMILIES[].group` filtered by `TACTIC_GROUPS` order [VERIFIED: frontend/src/lib/tacticComparisonMeta.ts:227-231 `{ key: 'piece_attacks', label: 'Piece Attacks' }`, `{ key: 'discoveries', label: 'Checkmate, Checks & Discoveries' }`, `{ key: 'advanced', label: 'Advanced' }`].
- Row hidden (listed under the table) when you+opp events are 0 in **both** orientations; a cell with 0 events in one orientation shows a muted "no flaws" placeholder (sketch `tacCell`).
- "N of your flaws" = missed `you_events` + allowed `you_events` (sketch `tacRow`: `DATA[tc].tac[f].m[3] + DATA[tc].tac[f].a[3]`). [ASSUMED: interpretation confirmed only by the sketch code]
- Advanced: `Accordion type="single" collapsible` + `AccordionTrigger band` + the hint span using `group-aria-expanded/accordion-trigger:hidden`, like `EndgameStatsTab.tsx` `SectionInsightSlot`. `EXPAND_HINT` is module-private in `ShellyQuote.tsx` [VERIFIED: ShellyQuote.tsx:7 `const EXPAND_HINT = 'Click or tap for details';`]: export it (or extract a tiny `ExpandHint` component) instead of duplicating the string.
- Accordion open is an open-state panel: track with `useTrackedOpen` (frontend/CLAUDE.md).
- h2 section titles use `font-brand` (Fredoka) like Phase 238 (`MetricsSection.tsx:34` `className="font-brand text-lg font-semibold text-foreground"`). [VERIFIED: read this session]

### Pattern 10: Generalised TC store + switch (D-02, D-04, D-05)

`useEndgameStatsTc` is a module-level store tied to `RankedTcStats` and one storage key [VERIFIED: frontend/src/hooks/useEndgameStatsTc.ts:22 `export const ENDGAME_STATS_TC_STORAGE_KEY = 'endgame_stats_tc';`, :25 `const TC_ORDER: readonly TimeControlBucket[] = ['bullet', 'blitz', 'rapid', 'classical'];`]. `TcSwitch` calls `useEndgameStatsTc` internally and tracks `{ target: 'endgame-stats-tc', value: tc }` [VERIFIED: frontend/src/lib/analytics.ts:449, 486].

Recommended: a store factory `createTcSelectionStore({ storageKey, pickDefault })` holding the module state (chosen, pinned default, listeners) and returning a hook `(tcs) => [selected, set]`. `useEndgameStatsTc` becomes a thin wrapper (keeps `useEndgameStatsTc.test.ts` green); a new `useLibraryStatsTc` uses key `'library_stats_tc'` [ASSUMED name] and a D-04 picker (prefer `analyzed_n >= analyzed_gate`, max `analyzed_n`, ties to the faster TC). Make `TcSwitch` presentational (`tcs: readonly TimeControlBucket[]`, `selected`, `onSelect`, `sectionId`) so the Library sections pass their own hook result and register a new option-change target (e.g. `'library-stats-tc'`, add to `OPTION_TARGETS` and `OptionChangeProps`). Keep the pinned-default behaviour (Phase 238 FE-IN-05: an import refetch must not flip the TC without user action).

### Anti-Patterns to Avoid
- **Copying family→int lists into `chapter5.py` or SQL.** Import `FAMILY_TO_MOTIF_INTS`; the frontend `TACTIC_COMPARISON_FAMILIES[].motifs` already mirrors it by contract.
- **Using `lichess_evals_at` to define the benchmark basis.** Homogenized lichess-arm games keep it set (SKILL.md §5).
- **Reading TC from `bs.tc_tranche` without the cohort TC anchor.** Keep `sql.BASE_GAME_FILTER` (contains `g.time_control_bucket::text = su.tc_bucket`) so a user selected in two TCs does not duplicate games.
- **Significance-gated colour.** The old grids tinted only when the CI excluded zero (`isFlawDeltaSignificant`). The new rule is band position plus the 40-flaw fade (D-00a, D-12); do not carry the significance gate over silently.
- **Frontend re-sorting tactic families by rate.** Order is fixed by `TACTIC_GROUPS` + family array order (D-00h).
- **Refetching on TC switch.** The selected TC is client state only.

## Dead-code inventory (what retires, every consumer)

| Item | Location | Consumers found | Action |
|------|----------|-----------------|--------|
| `flaw_rate`, `hasty_miss`, `low_clock_miss` metrics | `chapter5.py:58-75` (`_FLAW_DELTA_METRICS`), predicates `:183-199` and `:362-378`, labels `:482-498`, `Chapter5Values` fields | `tests/scripts/benchmarks/test_chapter5_diff.py` | Remove; regenerate gate |
| same, registry | `app/services/flaw_delta_zones.py:40, 58-59` | `library_service._compute_bullets` (iterates registry), `tests/services/test_flaw_comparison.py` (`_EXPECTED_TAGS`, `test_registry_has_15_metrics`, `test_combos`) | Remove; update tests |
| same, SQL columns | `library_repository.fetch_flaw_comparison` `:2085-2097` (flaw_rate), `:2258-2288` (combos) | `_compute_bullets` via `getattr(row, f"player_{tag}")` | Remove columns |
| `FlawDeltaZoneSpec.domain`, `FlawBullet.domain` | `flaw_delta_zones.py`, `schemas/library.py:388` | `FlawComparisonGrid.tsx` (`domain={bullet.domain}`), `types/library.ts` | Remove with the grid rewrite |
| Top-6 ranking (D-14) | `library_service.py:1801-1815` (`_sort_key`), `:1924-1958` | `test_tactic_comparison_service.py` (`test_family_mapping_produces_overflow`, `test_tactic_comparison_produces_overflow`, `test_significant_gap_first`), `TacticComparisonResponse` docstring, `TacticComparisonGrid.tsx` (`MAX_MAIN_GRID_FAMILIES`, "More tactics" accordion) | Remove; replace with fixed-order tests |
| `FlawBulletPopover.tsx` | `components/popovers/` | Only `FlawComparisonGrid.tsx`; `SeverityGlyphIcon.tsx` mentions it in a comment only | Delete (SeverityGlyphIcon stays, used by VariationTree etc.) |
| `MiniBulletChart` | `components/charts/` | Openings: `PositionResultsPanel.tsx`, `OpeningStatsCard.tsx`, `OpeningFindingCard.tsx` | **Keep.** Its `invertColors` prop loses its only callers (Library grids); leave it (knip does not flag props) |
| Combo/Severity families, `flaw_rate` meta | `flawComparisonMeta.ts:66-106, 123-129, 218-232`; theme `FAM_COMBO`, `FAM_COMBO_BG` (only used here); `FAM_SEVERITY*` (only used by `FLAW_FAMILY_COLORS`) | knip will flag | Remove; keep `FlawIcon` type (used by `FlawFilterControl.tsx`) |
| `isFlawDeltaSignificant`, `flawDeltaZoneColor`, `flawConfidenceLevel`, `formatPValue` (flawComparisonMeta) | `flawComparisonMeta.ts:242-276` | Grid + FlawBulletPopover only (RankedMetricPopover imports its own `formatPValue` from `rankedMetrics.ts`) | Remove or reuse `rankedMetrics.formatPValue` |
| `isTacticDeltaSignificant`, `tacticDeltaZoneColor`, `TACTIC_BULLET_DOMAIN`, `TacticBulletPopover` | `tacticComparisonMeta.ts:598-612`, `TacticComparisonGrid.tsx` | Grid only | Remove |
| Inaccuracies tile, `rates`/`per_severity_counts` on flaw-stats | `FlawStatsBand.tsx`, `get_flaw_stats` | `FlawStatsBand.tsx`, `FlawStatsPanel.tsx`; `tag_distribution` already has **no** frontend consumer | Recommended: drop `rates`, `per_severity_counts`, `tag_distribution` and their two queries (`fetch_stats_aggregates`, `fetch_stats_per_game_rates`) once tiles read the comparison bullets. Discretion; at minimum stop rendering |
| Insights / LLM payloads | `app/services/insights_*.py` | **None** read flaw/tactic comparison (grep found no match) | No action |

[VERIFIED: grep over app/, scripts/, tests/, frontend/src this session]

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| CI / p-value of the gap | New stats util, Poisson rate diff, Wilson | `_compute_mean_ci` + `_two_sided_p` (paired per-game Wald-z) | Established method for these exact bullets; zone and CI share the per-game paired basis |
| Collapse verdict | Hand Cohen's d | `distribution.verdict` / `stats.max_abs_d` | Verdict thresholds and sparse-cell rule are codified |
| Filter application | Per-endpoint WHERE clauses | `_filtered_games_base` → `apply_game_filters` | Single filter implementation (CLAUDE.md) |
| Family → motif ints | Literal lists in SQL/scripts | `FAMILY_TO_MOTIF_INTS` | Cross-stack contract, re-groups automatically |
| TC persistence | New ad-hoc localStorage code | Factory from `useEndgameStatsTc` (validation, try/catch, pinned default) | T-238-07 validation + FE-IN-05 pin already solved |
| Popover open tracking | Manual `trackFeature('popover-open')` | `useTrackedPopoverOpen(testId)` | Registry-typed, TC-segment collapsing |

## Common Pitfalls

### Pitfall 1: The 100-game cap widens every band (D-07 consequence)
**What goes wrong:** Benchmark zones are IQRs of per-user mean deltas. Var(per-user mean) = between-user variance + within-user noise / n_games. The lane caps each user at 100 games per TC, then splits them across game-time Elo buckets (floor 20), so per-user means are much noisier than on the old cohort-wide basis. Rough Poisson estimate for blunders (≈1 blunder per side per ~40-move game): noise-only per-user SD ≈ 0.35 per 100 moves at 100 games, i.e. a noise-only IQR ≈ 0.48, close to today's whole blunder band width (0.56 = −0.31..+0.25). For rare tactic families (≈5 per 100 games per side) the noise-only IQR at 100 games is ≈ 4 per 100 games, likely larger than any real between-user spread. [ASSUMED: back-of-envelope Poisson model; verify against the run]
**Why it happens:** D-07 trades basis size for homogeneity.
**How to avoid:** Add a "noise-only IQR" diagnostic per metric in the §5 output, `1.349 * sqrt(mean over users of (var of per-game deltas / n_games))`, next to the observed IQR, so the owner sees what share of each band is sampling noise before the registry is locked. Do not silently "fix" it (method-of-moments shrinkage would be a methodology change, owner call).
**Warning signs:** Most of the owner's own rows land "typical"; tactic bands several times wider than the owner's rates.

### Pitfall 2: Tactic motifs NULL while blobs are pending
**What goes wrong:** Games in the lane without blobs contribute 0 tactics for both sides, pulling bands toward 0.
**How to avoid:** `g.blobs_completed_at IS NOT NULL` in the base (Pattern 1). (App side: users' games with pending blobs are equally affected on both sides of the paired delta, so the gap is unbiased in expectation; rates are slightly low. Out of scope.)

### Pitfall 3: Diff gate vs narration
**What goes wrong:** `test_chapter5_diff.py` pins `compute()` numbers only; the narrated report prose, headline "Top-axis collapse summary" and "Recommended thresholds summary" rows for §5 are not gated. [CITED: user memory project_diff_gate_not_narration]
**How to avoid:** After the run, update every §5 section, both summary tables (drop flaw_rate/combo rows, add tactic rows), and the report header bullet about §5's basis. The §1 note that "§5's flaw-delta zones are built on `evals_completed_at`" also becomes stale (reports/benchmark/benchmarks-latest.md:170-171).

### Pitfall 4: The ≥30 cell floor is documented, not enforced
**What goes wrong:** `_CELL_CONTRIBUTOR_FLOOR = 30` is only interpolated into report text; `compute()` emits pooled/ELO/TC marginals with whatever `n` they have and no per-cell grid. [VERIFIED: scripts/benchmarks/chapter5.py:50 `_CELL_CONTRIBUTOR_FLOOR: int = 30` and its only uses are in `render()` at :475] On the smaller lane sample some marginal levels (e.g. 2400 in rapid) may be thin.
**How to avoid:** Either null Q1/Q3 for marginal levels with `n < 30` in `compute()` or make the registry author fall back to pooled for those levels; state which in SKILL.md. Emit a TC x ELO cell grid only if a metric keeps both axes separate (D-10).

### Pitfall 5: Benchmark DB is live
**What goes wrong:** The blitz tranche is still draining on the benchmark DB (74.1%), so the DB changes during the run; ~55 classical + ~86 rapid never-analyzed games are still incomplete and could finish later, moving the diff gate by a hair.
**How to avoid:** Run §5 once, record the snapshot timestamp in the report header, regenerate EXPECTED_* from that same run. Do not run another heavy benchmark scan concurrently. [CITED: SKILL.md Workflow step 1 "Never run two heavy benchmark-DB scans concurrently"] If sharding is ever needed, shard by `md5(id) % k`, not rank windows. [CITED: user memory project_benchmark_db_not_static]

### Pitfall 6: Tactic units silently change
**What goes wrong:** `TacticBullet` rates go from per game to per 100 games; any test or copy that assumed per-game breaks quietly (e.g. `TACTIC_BULLET_DOMAIN = 0.2`).
**How to avoid:** Multiply in one place in the service, update docstrings/schema comments, assert the unit in a test (a 1-vs-0 game yields `you_rate == 100.0` for that game).

### Pitfall 7: Below-gate TCs still need bullets
**What goes wrong:** Keeping the current early return (`bullets=[]` when below gate) breaks D-03's "tiles still show the rates".
**How to avoid:** Compute bullets for every listed TC; only the gap-bar sections switch to the slot.

### Pitfall 8: NULL time_control_bucket games drop out of the comparisons
**What goes wrong:** Pooled comparisons today include games with no TC bucket (possible for pasted PGNs); per-TC payloads cannot place them.
**How to avoid:** Exclude NULL buckets explicitly in the counts and per-game rows so counts and bullets stay on one basis. Mention in a code comment.

### Pitfall 9: Copy drift ("events", raw signs)
**What goes wrong:** Existing copy says "No events in current filter", "events/game"; the sketch's typical range prints signed raw deltas ("−0.31 to +0.25") while the page speaks in "fewer/more" with better on the right.
**How to avoid:** Grep new components for "event"; render the typical range in gap words ("0.31 fewer to 0.25 more") [ASSUMED: copy choice, discretion].

### Pitfall 10: `text-xs` hint outside a popover
**What goes wrong:** `ShellyQuote`'s hint uses `text-xs` [VERIFIED: ShellyQuote.tsx:48 `className="text-xs font-normal text-muted-foreground group-aria-expanded/accordion-trigger:hidden"`], but frontend/CLAUDE.md sets a `text-sm` floor except popover bodies.
**How to avoid:** D-00i asks for the ShellyQuote styling, which the owner accepted in 238 UAT. Reuse the exact styling via the shared hint (one place to change). Flag to the owner if a reviewer objects.

### Pitfall 11: `user_moves` parity inconsistency (pre-existing, do not touch)
`fetch_flaw_comparison` and `chapter5` use `FLOOR(ply_count/2)` for white, while the trend helper `_user_moves_from_ply_count` uses ceil for white. [VERIFIED: library_repository.py:2063-2066; library_service.py:1167-1169] App and benchmark agree with each other, which is what matters for the zones. Out of scope; flag only.

### Pitfall 12: knip / tsc
Deleting the grids leaves dead exports (theme `FAM_COMBO*`, meta helpers). Run `npm run knip` and `npm run build` (tsc -b) before integrating; `npm test`/lint do not type-check. [CITED: frontend/CLAUDE.md; user memory feedback_frontend_run_tsc_build]

## Code Examples

### Existing CI / p-value helpers to reuse (per-game paired deltas)
```python
# Source: app/services/library_service.py:1496-1536 (read this session)
def _compute_mean_ci(values: list[float], z: float = 1.96) -> tuple[float, float, float]:
    ...  # (0,0,0) empty; (m,m,m) n==1; mean ± z*sqrt(var/n)
def _two_sided_p(values: list[float]) -> float | None:
    ...  # None n<2; se==0 → 0.0 or 1.0; erfc(|mean/se| / sqrt(2))
```

### Gates (unchanged values)
```python
# Source: app/services/library_service.py:1493, 1710 (read this session)
FLAW_COMPARISON_GATE: int = 20
TACTIC_COMPARISON_GATE: int = 20
```

### Tactic bullet in per-100-games (proposal)
```python
PER_100_GAMES: float = 100.0      # Phase 239 D-00h: tactic gaps read per 100 games
LOW_SAMPLE_MIN_FLAWS: int = 40     # D-12: you + opponents flaws per cell

you_rate = float(you_count) * PER_100_GAMES
opp_rate = float(opp_count) * PER_100_GAMES
deltas_by_fam[fam].append(you_rate - opp_rate)
...
low_sample = (y_total + o_total) < LOW_SAMPLE_MIN_FLAWS
```

## D-12 sanity check (40 flaws vs CI width)

**Closed form** (Poisson counts, sides roughly equal, small per-game counts): the paired per-game CI half-width in event units is ≈ 1.96·√N, where N = you + opponent flaws in the cell, independent of the game count. Relative to one side's count (N/2) that is **≈ 3.92/√N**: N = 40 → ±62%, N = 100 → ±39%, N = 400 → ±20%. So at 40 flaws only roughly 2:1 splits (e.g. 27 vs 13) clear p < 0.05. [ASSUMED: derived; verify empirically below]

**Decision rule** (proposal for the planner): compare CI half-width to band width (`zone_hi − zone_lo`) for cells with N in [30, 60] once the new zones exist. If the typical CI half-width at N ≈ 40 exceeds about 1.5 band widths, raise the constant; if it is under about 0.5 band widths, lower it; otherwise keep 40. [ASSUMED: thresholds, owner confirms]

**Exact queries for the orchestrator/executor (dev DB; project MCP `flawchess-db` or psql inside `flawchess-dev-db-1`).** Values used: ply parity "even ply = white mover" [VERIFIED: app/repositories/query_utils.py:78-80 docstring "even ply → white mover → is_opponent iff user_color == 'black'"]; confidence 70; family ints from `FAMILY_TO_MOTIF_INTS` / `TacticMotifInt` quoted in Pattern 2.

```sql
-- 0) Owner's dev user id (largest analyzed set)
SELECT g.user_id, count(*) AS analyzed
FROM games g WHERE g.full_evals_completed_at IS NOT NULL
GROUP BY g.user_id ORDER BY analyzed DESC LIMIT 5;

-- 1) Tactic cells: per (tc, family, orientation) totals and CI half-width, per 100 games
WITH g AS (
  SELECT id, user_color, time_control_bucket::text AS tc
  FROM games
  WHERE user_id = :uid AND full_evals_completed_at IS NOT NULL
    AND ply_count > 0 AND NOT is_computer_game AND time_control_bucket IS NOT NULL
),
fam(family, ints) AS (VALUES
  ('fork', ARRAY[1]), ('skewer', ARRAY[4]), ('pin', ARRAY[3]), ('x_ray', ARRAY[12]),
  ('double_check', ARRAY[5]), ('discovered_check', ARRAY[25]), ('discovered_attack', ARRAY[6]),
  ('trapped_piece', ARRAY[26]), ('hanging', ARRAY[2]),
  ('mate', ARRAY[7,8,18,19,20,21,22,23,24]),
  ('deflection', ARRAY[9]), ('intermezzo', ARRAY[11]), ('interference', ARRAY[13]),
  ('capturing_defender', ARRAY[16]), ('attraction', ARRAY[10]), ('sacrifice', ARRAY[17]),
  ('en_passant', ARRAY[27]), ('under_promotion', ARRAY[29]), ('promotion', ARRAY[28])
),
orient(o) AS (VALUES ('missed'), ('allowed')),
per_game AS (
  SELECT g.id, g.tc, fam.family, orient.o,
    count(f.ply) FILTER (WHERE (f.ply % 2 = 0) = (g.user_color = 'white')) AS you_n,
    count(f.ply) FILTER (WHERE (f.ply % 2 = 0) <> (g.user_color = 'white')) AS opp_n
  FROM g CROSS JOIN fam CROSS JOIN orient
  LEFT JOIN game_flaws f
    ON f.game_id = g.id AND f.user_id = :uid
   AND CASE WHEN orient.o = 'missed'
            THEN f.missed_tactic_motif = ANY(fam.ints) AND f.missed_tactic_confidence >= 70
            ELSE f.allowed_tactic_motif = ANY(fam.ints) AND f.allowed_tactic_confidence >= 70 END
  GROUP BY g.id, g.tc, fam.family, orient.o
)
SELECT tc, family, o AS orientation, count(*) AS n_games,
       sum(you_n) AS you_flaws, sum(opp_n) AS opp_flaws, sum(you_n + opp_n) AS total_flaws,
       round(100.0 * avg(you_n - opp_n), 3) AS gap_per_100g,
       round(100.0 * 1.96 * stddev_samp(you_n - opp_n) / sqrt(count(*)), 3) AS ci_half_per_100g
FROM per_game
GROUP BY tc, family, o
ORDER BY tc, total_flaws;

-- 2) Context tags (per 100 moves): same shape, one predicate per tag
WITH g AS (
  SELECT id, user_color, time_control_bucket::text AS tc,
         CASE WHEN user_color = 'white' THEN floor(ply_count / 2.0) ELSE ceil(ply_count / 2.0) END AS um
  FROM games
  WHERE user_id = :uid AND full_evals_completed_at IS NOT NULL
    AND ply_count > 1 AND NOT is_computer_game AND time_control_bucket IS NOT NULL
),
per_game AS (
  SELECT g.id, g.tc, g.um,
    count(f.ply) FILTER (WHERE (f.ply % 2 = 0) = (g.user_color = 'white') AND f.tempo = 0)  AS p_low_clock,
    count(f.ply) FILTER (WHERE (f.ply % 2 = 0) <> (g.user_color = 'white') AND f.tempo = 0) AS o_low_clock,
    count(f.ply) FILTER (WHERE (f.ply % 2 = 0) = (g.user_color = 'white') AND f.is_reversed)  AS p_reversed,
    count(f.ply) FILTER (WHERE (f.ply % 2 = 0) <> (g.user_color = 'white') AND f.is_reversed) AS o_reversed
    -- add hasty (tempo=1), unrushed (tempo=2), opening/middlegame/endgame (phase=0/1/2),
    -- miss (is_miss), lucky (is_lucky), squandered (is_squandered) in the same pattern
  FROM g LEFT JOIN game_flaws f ON f.game_id = g.id AND f.user_id = :uid
  GROUP BY g.id, g.tc, g.um
)
SELECT tc, count(*) AS n_games,
  sum(p_low_clock + o_low_clock) AS low_clock_total,
  round(1.96 * stddev_samp((p_low_clock - o_low_clock) * 100.0 / um) / sqrt(count(*)), 3) AS low_clock_ci_half,
  sum(p_reversed + o_reversed) AS reversed_total,
  round(1.96 * stddev_samp((p_reversed - o_reversed) * 100.0 / um) / sqrt(count(*)), 3) AS reversed_ci_half
FROM per_game GROUP BY tc;
```
Tag predicates: `tempo` 0/1/2 = low-clock/hasty/unrushed, `phase` 0/1/2 = opening/middlegame/endgame, booleans `is_miss`, `is_lucky`, `is_reversed`, `is_squandered`. [VERIFIED: scripts/benchmarks/chapter5.py:183-199 tag_predicates, e.g. `"low_clock": "gf.tempo = 0"`, `"reversed": "gf.is_reversed = TRUE"`]

Simpler alternative that reuses the exact app code: a scratch script in `temp/` calling `library_service.get_tactic_comparison(..., time_control=["rapid"])` against the dev DB and printing `you_events + opp_events` vs `ci_high − ci_low`. Either is fine; run after Plan 01 so the band widths exist.

## Benchmark run logistics

1. `bin/benchmark_db.sh start` (container `flawchess-benchmark-db-1` was up and healthy on 2026-10-12). [VERIFIED: `docker ps` output "flawchess-benchmark-db-1 Up 3 days (healthy)"]
2. Confirm tranche state: `uv run python scripts/benchmark_lane.py status --all-tranches --db benchmark` (read-only counts; `create_all(checkfirst=True)` is a no-op on existing tables).
3. Fast path, §5 only (~1-2 min on the old 1.2M-game basis; the lane basis is ~146k games): build a benchmark session as in `tests/scripts/benchmarks/conftest.py` (`gen_benchmarks._db_url("benchmark")`, `SET TRANSACTION READ ONLY`) and `await chapter5.build(session)`; or simply run the diff gate. Do **not** run the 33-min full `gen_benchmarks.py`. [CITED: user memory project_benchmark_chapter5_refresh_fast_path]
4. Regenerate `EXPECTED_*` and `EXPECTED_VERDICTS` in `tests/scripts/benchmarks/test_chapter5_diff.py` from that run (drop flaw_rate/combos, add at least pooled + verdict expectations for the tactic metrics). Gate runs only with an explicit path: `uv run pytest tests/scripts/benchmarks/test_chapter5_diff.py -q` (excluded from normal runs by `--ignore` in pyproject). [CITED: SKILL.md Workflow "QA the artifact"]
5. Narrate into `reports/benchmark/benchmarks-latest.md` as a **subchapter subset** (splice §5 in place, keep §1-§4, rebuild both summary tables, add a header bullet with the §5 snapshot date and basis change, document the blitz/bullet → rapid mapping per D-09). [CITED: SKILL.md "Re-running" → subchapter subset]. Note: this is a subset splice, not a fresh snapshot, so no rotation; the header must say §5 has a newer snapshot date than §1-§4.
6. Update SKILL.md §5 (basis, 12 + 38 metrics, tactic estimator and unit, viability/`has_zone` rule, noise diagnostic, stopgap mapping, the frontmatter description's "15 you−opponent paired-delta metrics").
7. Author both registries from the narrated verdicts.

Executor caution: long DB-heavy work inside a gsd-executor subagent has died mid-run before; commit before the run and do not background it. [CITED: user memory project_executor_sse_timeout_long_plans, project_executor_backgrounded_runs_die]

## Runtime State Inventory

Not a rename phase. Runtime state touched: a new localStorage key (`library_stats_tc`, new, nothing to migrate); benchmark report and registry constants (in git). Stored data: none migrated (game_flaws untouched). Live service config: none. OS-registered state: none. Secrets/env vars: none. Build artifacts: none.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| §5 basis `evals_completed_at` over the whole cohort (1,223,105 games) | `benchmark_selection` full-analysis lane, classical + rapid | This phase (D-07) | Bands move, likely wider (Pitfall 1) |
| Pooled single zone per flaw metric | Per zone-TC lookup with blitz/bullet → rapid | This phase (D-08/D-10) | Registry API changes |
| Tactic bullets `has_zone=False`, per game | Real zones, per 100 games | This phase (D-06/D-11) | New registry module |
| Colour only when CI excludes 0 | Colour by band position, faded below 40 flaws | This phase (D-00a/D-12) | Verdict logic changes |

[VERIFIED: reports/benchmark/benchmarks-latest.md:1229 "**Cohort basis**: 1,223,105 analyzed games across 4,649 user×(ELO,TC) cells"]

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Noise-only IQR estimates (blunder ≈ 0.48/100 moves, rare tactics ≈ 4/100 games) | Pitfall 1 | Bands may be narrower than feared; diagnostic resolves it |
| A2 | `has_zone=false` rule: degenerate IQR or pct_nonzero < 50% | Pattern 2 | Too strict/lenient zone coverage; owner picks from the viability table |
| A3 | One merged per-game scan for flaw + tactic metrics is fast enough | Pattern 2 | Slower §5 run; split into two scans if needed |
| A4 | Names `FULL_ANALYSIS_TRANCHES`, `ZoneTc`, `ZONE_TC_FOR`, `library_stats_tc`, `library-stats-tc`, `LOW_SAMPLE_MIN_FLAWS`, `PER_100_GAMES`, schema class names | Patterns 1-4, 10 | Cosmetic |
| A5 | "N of your flaws" = missed + allowed you_events | Pattern 9 | Wrong number under the motif name |
| A6 | Typical range rendered in gap words, not signed raw deltas | Pitfall 9 | Copy preference only |
| A7 | D-12 closed form 3.92/√N and the 0.5x/1.5x band-width decision rule | D-12 section | Constant kept/changed on a weak rule; owner confirms |
| A8 | Band-less (`has_zone=false`) dot scale | Pattern 5 | Dot position looks arbitrary for unviable families |
| A9 | Tiles below the gate show rates (you + opponents) but replace their gap bar with the slot | Pitfall 7 | D-03 wording "each gap-bar section" could also mean tiles keep their bar; confirm in plan |

## Open Questions

1. **Accept noise-inflated bands, or add a correction?**
   - What we know: the lane gives ≤100 games per user per TC; band = IQR of noisy per-user means.
   - Unclear: how much of each band is noise until the run.
   - Recommendation: Plan 01 emits a noise-only IQR column; the owner decides at the registry step (keep, or a later methodology seed). Do not block the phase on it.
2. **Elo keying.** Only needed if a metric's ELO verdict is "keep separate" on the new basis. Recommendation: plan the `user_rating_anchors` lookup as a conditional task gated on the §5 verdicts.
3. **Slim `/flaw-stats`.** Dropping `rates`/`per_severity_counts`/`tag_distribution` removes two queries; it is cleanup within the discretion clause. Recommendation: do it in Plan 02 if tests stay small; otherwise defer with a note.
4. **Tiles low-sample fade.** D-12 names tactic cells and context-tag rows only. Recommendation: no fade on tiles (blunders/mistakes are never rare at ≥20 games).

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Benchmark DB (Docker, :5433) | Plan 01 §5 run, diff gate | ✓ | container `flawchess-benchmark-db-1` healthy | — |
| Dev DB (Docker) | Backend tests, D-12 check | ✓ | `flawchess-dev-db-1` healthy | — |
| uv | Backend, scripts | ✓ | 0.10.9 | — |
| Node | Frontend | ✓ | v24.19.0 | — |
| Project DB MCP (`flawchess-db`) | D-12 SQL | orchestrator only (subagents lack project MCP) | — | psql inside the dev container, or a `temp/` script via the service layer |

**Missing dependencies with no fallback:** none.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (+ pytest-asyncio, xdist) backend; vitest frontend |
| Config file | `pyproject.toml` (benchmark gates `--ignore`d by default); `frontend/vite.config.ts` test block |
| Quick run command | `uv run pytest tests/services/test_flaw_comparison.py tests/services/test_tactic_comparison_service.py -x` |
| Full suite command | `uv run pytest -n auto -x` and `( cd frontend && npm run lint && npm run build && npm test -- --run && npm run knip )` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| D-06/D-07/D-08 | §5 base uses `benchmark_selection`, classical+rapid, completion predicates; 12 flaw + 38 tactic metric keys; no combos/flaw_rate | unit (SQL string) | `uv run pytest tests/scripts/test_chapter5_sql.py -x` | ❌ Wave 0 (string assertions on `_base_games_cte()` / metric list, no DB; outside `tests/scripts/benchmarks/` so the normal suite runs it) |
| D-06/D-07 | Numbers reproduce the narrated report | integration (benchmark DB, on demand) | `uv run pytest tests/scripts/benchmarks/test_chapter5_diff.py -q` | ✅ (EXPECTED_* to regenerate) |
| D-08/D-09/D-10 | `ZONE_TC_FOR` maps blitz/bullet → rapid; registry has exactly 12 flaw metrics; lookup per TC | unit | `uv run pytest tests/services/test_flaw_delta_zones.py -x` | ❌ Wave 0 |
| D-11/D-06 | Tactic registry covers all 19 families x 2; `None` → `has_zone=False` | unit | `uv run pytest tests/services/test_tactic_delta_zones.py -x` | ❌ Wave 0 |
| D-02/D-03 | `tcs[]` lists only TCs with ≥1 analyzed game inside the TC filter; below-gate TC still has bullets | integration (dev DB clone) | `uv run pytest tests/services/test_flaw_comparison.py -x` | ✅ (rewrite) |
| D-00e/D-00f | 12 bullets (blunder, mistake, 10 tags), no combos/flaw_rate | integration | same file | ✅ (rewrite `_EXPECTED_TAGS`, drop `test_combos`) |
| D-00h | Tactic bullets per 100 games, fixed order, all 19 families, no top-6 | integration | `uv run pytest tests/services/test_tactic_comparison_service.py -x` | ✅ (replace overflow/top-6 tests) |
| D-11 | `get_tactic_comparison` sets zone_lo/zone_hi/has_zone from registry per TC | integration | same file | ✅ (new test) |
| D-12 | `low_sample` true below 40 you+opp flaws, false at 40 | unit/integration | same two files | ❌ new tests |
| D-00k | `trend_by_tc` per TC; `analyzed_n` kept for FlawsTab | integration | `uv run pytest tests/services/test_library_service.py -x -k flaw_stats` | ✅ (extend) |
| API | Router shapes, 422 on bad params | integration | `uv run pytest tests/test_library_router.py -x -k "comparison or flaw_stats"` | ✅ (update) |
| D-00a/D-00b | `gapPosition` (centre, band edges, saturation, both zero-width guards), `gapWords`, verdict | unit | `cd frontend && npm test -- --run src/lib/__tests__/gapBar.test.ts` | ❌ Wave 0 |
| D-00a/D-11/D-12 | GapBar renders band/no band, blue dot when faded/zoneless | component | `npm test -- --run src/components/library/stats/__tests__/GapBar.test.tsx` | ❌ Wave 0 |
| D-00c | Gap popover sections, "Too few flaws to call it", no range line when zoneless, footer CI/p | component | `npm test -- --run src/components/library/stats/__tests__/GapPopover.test.tsx` | ❌ Wave 0 |
| D-02/D-04/D-05 | Default TC rule, separate key, stored TC ignored when not offered, pinned default | hook | `npm test -- --run src/hooks/__tests__/useLibraryStatsTc.test.ts` + existing `useEndgameStatsTc.test.ts` | ❌ / ✅ |
| D-00g/D-13 | Top 3 per side by band-width distance; faded/zoneless excluded; Typical line; empty copy | component | `npm test -- --run src/components/library/stats/__tests__/WhatStandsOut.test.tsx` | ❌ Wave 0 |
| D-00f | Four cards, tag order, hints | component | `npm test -- --run src/components/library/__tests__/FlawComparisonGrid.test.tsx` | ✅ (rewrite) |
| D-00h/D-00i | Three tables in TACTIC_GROUPS order, zero-count motifs listed under table, Advanced collapsed with hint | component | `npm test -- --run src/components/library/__tests__/TacticComparisonGrid.test.tsx` | ✅ (rewrite) |
| D-03 | Gate slot "(12 of 20)" per section | component | in the two grid tests | ✅ (rewrite) |
| UI | Desktop + mobile look, switch sync across sections | manual UAT (browser) | Claude-in-Chrome on dev build | manual |

### Sampling Rate
- **Per task commit:** the matching row's command.
- **Per wave merge:** backend `uv run pytest -n auto -x`; frontend `npm test -- --run && npm run build && npm run knip`.
- **Phase gate:** full pre-merge gate from CLAUDE.md, plus `uv run pytest tests/scripts/benchmarks/test_chapter5_diff.py -q` once after Plan 01.

### Wave 0 Gaps
- [ ] `tests/scripts/test_chapter5_sql.py` (DB-free). `pyproject.toml:93` has `addopts = "--ignore=tests/scripts/benchmarks --ignore=tests/scripts/tagger"`, so a test placed under `tests/scripts/benchmarks/` would never run in the normal suite.
- [ ] `tests/services/test_flaw_delta_zones.py`, `tests/services/test_tactic_delta_zones.py`
- [ ] `frontend/src/lib/__tests__/gapBar.test.ts`
- [ ] `frontend/src/components/library/stats/__tests__/{GapBar,GapPopover,WhatStandsOut}.test.tsx`
- [ ] `frontend/src/hooks/__tests__/useLibraryStatsTc.test.ts`
- Prove new tests by reverting the fix once (mutation check), not by symbol presence. [CITED: user memory feedback_mutation_test_gap_closures]

## Security Domain

### Applicable ASVS Categories
| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no (unchanged) | FastAPI-Users `current_active_user` |
| V3 Session Management | no | — |
| V4 Access Control | yes | `user_id` only from `current_active_user`, never a request param (existing IDOR guard on all three endpoints) |
| V5 Input Validation | yes | FastAPI/Pydantic Query types; `Literal` for any new param; frontend validates the stored TC before use (T-238-07 pattern) |
| V6 Cryptography | no | — |

### Known Threat Patterns
| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| IDOR on per-TC payloads | Information disclosure | Keep `user_id=user.id` from the auth dependency; repository scopes every subquery by `user_id` |
| Tampered localStorage TC | Tampering | Validate against the `TimeControlBucket` union and the offered list; try/catch around storage |
| SQL built from strings in chapter5 | Tampering | Identifiers only from closed in-code sets (`FAMILY_TO_MOTIF_INTS` keys, literal tranches); benchmark scripts run read-only (`SET TRANSACTION READ ONLY`) |

## Sources

### Primary (HIGH confidence, read this session)
- `scripts/benchmarks/chapter5.py`, `distribution.py`, `sql.py`, `render.py`; `scripts/benchmark_lane.py`; `scripts/gen_benchmarks.py`
- `app/models/benchmark_selection.py`, `app/models/game.py`, `app/models/game_flaw.py`, `app/models/user_rating_anchors.py`
- `app/services/flaw_delta_zones.py`, `library_service.py`, `flaws_service.py`, `tactic_detector.py`; `app/repositories/library_repository.py`, `query_utils.py`; `app/schemas/library.py`, `normalization.py`; `app/routers/library.py`
- Frontend: `pages/GlobalStats.tsx`, `components/library/*`, `lib/flawComparisonMeta.ts`, `lib/tacticComparisonMeta.ts`, `lib/tagDefinitions.ts`, `lib/analytics.ts`, `components/endgames/stats/*`, `hooks/useEndgameStatsTc.ts`, `hooks/useLibrary.ts`, `components/insights/ShellyQuote.tsx`, `components/endgames/EndgameStatsTab.tsx`, `components/ui/accordion.tsx`
- `.claude/skills/benchmarks/SKILL.md` (Workflow, §1 analysis share, §5), `reports/benchmark/benchmarks-latest.md` (header, §5, §5.16), `reports/benchmark-lane/*.md`
- `.planning/seeds/SEED-198-*.md`, `.planning/sketches/010-*/{index.html,README.md}`, `.planning/notes/eval-completion-columns.md`, `.planning/phases/238-*/238-CONTEXT.md`
- Live command: `scripts/benchmark_lane.py status --all-tranches --db benchmark` (2026-10-12)

### Secondary / Tertiary
- None. No web research was needed: the phase uses only in-repo code and no external packages.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH (no new dependencies; all reused assets read)
- Architecture: HIGH (payload/registry/store designs follow verified in-repo precedents)
- Pitfalls: HIGH for code facts (blobs, floor not enforced, NULL TC); MEDIUM for the band-widening magnitude (derived, not measured)

**Research date:** 2026-10-12
**Valid until:** 2026-11-11 (benchmark lane state changes as blitz finishes; re-check tranche status before Plan 01)
