---
id: SEED-040
status: dormant
planted: 2026-06-09
planted_during: v1.24 (Library Page), Phase 111 (Library UI polish) in progress
trigger_when: when scoping a milestone to rework the Library > Stats flaw section into an opponent-comparison surface, or when SEED-038/039 opponent-flaw materialization is being planned
scope: large (milestone)
---

# SEED-040: Flaw-stats opponent comparison rework

Completely rework the **flaw-stats section of the Library > Stats subtab** from a
self-only descriptive panel into a **you-vs-opponent comparison** surface. Today
the panel (`FlawStatsPanel`) shows only the user's own severity rates, a trend
line, and tag distributions — no comparison at all. Flaw statistics only become
*actionable* when contrasted with opponents: that's how a player detects their
*specific* recurring weaknesses rather than their absolute error level.

This is the statistical/UX presentation layer. It is distinct from but depends on
[[SEED-038-flaw-filter-and-game-flaws-materialization]] (the `game_flaws`
materialization) and complements [[SEED-039-tactic-family-cause-of-error-flaw-tags]]
(which *computes* tactic motifs; this *presents* opponent-comparison stats over all
families, tactic motifs included once they exist). Builds on
[[SEED-021-gauges-to-bullet-charts]] (the bullet-chart pattern this reuses).

## The core decision: opponent comparison (A) as backbone, light benchmark (B) as the zone

Two comparison strategies were weighed (the full A-vs-B pro/con framing is in the
exploration that planted this seed):

- **A — your actual opponents** in your actual games. Cheap (materialize opponent
  blunders/mistakes in `game_flaws`), ELO-matched by construction (chess.com /
  lichess pairing). Con: player↔opponent *interaction* (you burn clock → opponent
  thinks on your time → their time-pressure flaws drop).
- **B — benchmark percentiles** vs a representative Lichess sample of ELO peers.
  Powerful (percentile rank), removes the interaction. Con: expensive (CDF per ELO
  cell), recompute on every taxonomy change, and **does not scale to tactic motifs**
  — B-percentiles would need Stockfish PV lines across millions of cohort games per
  motif.

**Decision: A is the universal backbone for all families (including future tactic
motifs); B is folded in as a *lightweight* "typical" zone, not full percentiles.**
The deciding factor is the cost trajectory: A scales to the SEED-039 tactic taxonomy
almost for free (PV search bounded by the user's own games), B does not.

### Why this dissolves the A/B tension (the bullet-chart synthesis)

Per flaw tag, **one bullet chart** (the [[SEED-021-gauges-to-bullet-charts]] /
endgame "Clock Gap" pattern):

- **Measure** = the *frequency difference* (you − opponents) for that tag, computed
  within your own game set (pure A).
- **Error bar** = a real **confidence interval** on that difference, from your N
  games. This hypothesis-testing angle is the deliberate differentiator from
  descriptive-stats-only platforms.
- **Blue "typical" zone** = the **benchmark IQR of that same delta** across
  ELO-matched peers. This is a *much lighter* B than the 11-metric endgame CDF: two
  quartiles (Q1/Q3) of one derived metric per cell, **not** 99 breakpoints. It
  answers "is my you-vs-opponent gap unusual for my rating?" without the
  percentile-recompute tax.

The benchmark zone is computed on the **delta** (the A-style materialized stat),
which is what keeps B cheap. Chart **degrades gracefully**: measure + CI always
render; the blue zone renders only when the cohort stat exists for that metric.

## Locked design decisions (from the planting exploration)

| Decision | Choice | Rationale |
|---|---|---|
| Headline comparison | **A (opponent rates) backbone**, light B zone integrated | Only option that survives the tactic-motif roadmap without a benchmark-recompute explosion |
| Expression | **Rate per exposure** (difference in frequency) | Intuitive magnitude; same-game → directly comparable |
| Denominator (count-rate families) | **Per 100 of your own moves** (toggle removed) | Within-game length confound is absent (shared game), but game length rises with ELO → per-100 keeps the *benchmark zone* portable across ELO cells |
| Flaw base | **Mistakes + Blunders combined** | Bigger N (crucial for combos/rare tags); existing severity filter can still narrow to blunders-only |
| Severity family | **Single "Flaw Rate" bullet** (M+B / 100 moves) | Branded term "Flaw" = mistakes+blunders; M-vs-B split not shown directly; definition in metric tooltip |
| Count-rate CI method | **Paired per-game difference** | Same game set → pairing removes game-level variance, tighter CI, partially controls the interaction; bootstrap/normal CI |
| Proportion CI method | **Wilson difference-of-proportions** (existing chess-score util) | `miss`/`lucky`/`reversed`/`squandered` are proportions (denominator = opportunities faced / flaws), not per-move rates |
| Tempo interaction confound | **Show + caveat tooltip** | Clock-conditioned tags read high partly from the interaction; honest tooltip, uniform grid (matches project tooltip-disclosure pattern) |
| Thin samples | **Let the CI speak + section gate** | Section-level "analyze more games" floor; above it every bullet renders with its CI (wide bar = inconclusive); per-bullet blank only on literally zero events |
| Trend chart | **No comparison** | ELO-peer matching irons out the *level*; the signal is in *composition* (the bullets), not the trend delta |
| Termination (timeout/resign) | **Out of scope here; cross-link to Time Management** | "Blunder less but flag more" needs game-result/termination data (already `net_flag_rate`), not `game_flaws` — keep the flaw section about in-game error patterns |

## v1 bullet inventory (~13 bullets)

Each = you−opponent delta, per 100 of your own moves over the M+B base, with CI +
benchmark blue zone:

- **Flaw Rate** (combined M+B / 100 moves) — the headline
- **Tempo:** `low-clock`, `hasty`, `unrushed` (the last = blundering with time in
  hand → pure calculation/positional weakness, no clock excuse)
- **Phase:** `opening`, `middlegame`, `endgame`
- **Opportunity:** `miss`, `lucky` — Wilson proportions (not per-100)
- **Impact:** `reversed`, `squandered` — Wilson proportions
- **Combos (curated, NOT an auto cross-tab):** `hasty + miss`, `low-clock + miss`

**Combo curation principle:** a combo earns a slot only when the intersection says
something neither parent does. `endgame+blunder` is dominated by standalone
`endgame` (M+B base); `low-clock+blunder` by standalone `low-clock` — both rejected.
The kept combos answer "do I miss tactics *because* I'm rushed?":

- `hasty + miss` — **flagship, least confounded**: moved fast *despite having time*,
  and let opponents off the hook more than they let me. A behavioral/skill tell, not
  clock fed to the opponent.
- `low-clock + miss` — high-value but carries the tempo interaction caveat.

**`miss` is a v1 proxy for "missed tactic."** Pre-SEED-039, `is_miss` = "failed to
punish an error the opponent handed you." It upgrades cleanly to literal
`hasty + missed-fork` once tactic motifs land, via the adjacency join SEED-039
already designed (missed-X = opponent `allowed-X` adjacent to your `is_miss`).

## Statistical method detail

- **Count-rate families** (Flaw Rate, tempo, phase, future tactic motifs): per game,
  take `(your tag count − opponent tag count) / your_moves_in_game * 100`; the metric
  is the mean of those paired per-game deltas; CI via bootstrap or normal approx. The
  game is the pairing unit — same complexity, length, TC, date, exact rating match.
- **Proportion families** (opportunity, impact): difference-of-proportions with the
  project's established **Wilson** chess-score util. Do not invent a parallel test.
- **Benchmark blue zone:** for each cohort user compute their own per-metric delta,
  then take Q1/Q3 across users per (ELO bucket × TC) cell. Run the established
  `/benchmarks` **Cohen's-d collapse verdict** per metric per axis to decide whether
  each metric needs cell-specific zones or collapses to a global zone.

## Upstream: impact-tag threshold recalibration (2026-06-09)

The `reversed`/`squandered` thresholds were recalibrated to round-eval anchors specifically
to give *this* comparison a usable signal (see [[flaw-tag-definitions]] §Impact). The impact
family is the sparsest, and this seed consumes it as a **Wilson difference-of-proportions**
with a per-(ELO×TC) IQR blue zone — both the CI width on a user's own proportion and the
zone's non-degeneracy depend on event density. With the original cutoffs most cohort users
in a cell had ~0–2 squandered events, which would collapse the delta IQR and leave every
squandered bullet "inconclusive."

Benchmark-DB measurement (2026-06-09, replicating `flaws_service` over the cohort's own
moves): the recalibration **~3× the squandered rate** (per-user share with ≥10 instances
**34% → 68%**) and left `reversed` roughly flat (**+21%**, already healthy at ~51% of users
≥10). New cutoffs: `reversed` 68/32 (≈ ±2.0), `squandered` 75/59 (≈ +3.0/+1.0). The
`squandered` *entry* is the load-bearing lever.

**Coupling to resolve at plan time (phase 2):** impact tags are *proportions*, so the
**denominator** matters as much as the entry cutoff. If the denominator is "winning positions
reached" (squander opportunities), loosening the entry from +4.7 to +3.0 also *enlarges* the
denominator, so the observed *rate* moves less than the 3× raw-count change implies. The
raw-count density gain is unambiguous and is what rescues the Wilson CI; the rate effect and
the per-cell IQR-zone stability check must be measured against the **final denominator
definition** during the benchmark backfill. Calibrate threshold + denominator together, not
in isolation. (Threshold implementation itself is a self-contained `/gsd-quick`: 4 constants
+ the exact-value tests in `tests/services/test_flaws_service.py` + the tooltip copy.)

## Cost & feasibility

- **Eval-only families are computable now.** Tempo/phase/opportunity/impact need no
  PV; the benchmark cohort already has the eval coverage where analyzed (see
  `reports/benchmark/benchmark-eval-coverage-2026-05-25.md`: 11–62% per cell).
- **Tactic motifs defer the benchmark zone**, not the comparison. Cohort-wide
  Stockfish PVs are the expensive part; until then a tactic bullet shows
  CI-vs-your-opponents with no blue zone (graceful degradation).
- **OOM history (FLAWCHESS-3Q):** opponent-flaw materialization itself is nearly free
  (the classifier already evaluates both colors — drop the player-only filter, add
  `is_opponent`). The engine cost is only the future tactic PV search; keep it off the
  import hot path per SEED-039.

## Eval-coverage prerequisite — the gating bottleneck (Q-007, 2026-06-09)

Q-007's prod probe surfaced the real constraint on this entire feature: **flaw
classification requires full per-ply eval, and most prod games don't have it.**

Prod analyzed-game distribution (103 of 126 users have games; "analyzed" = full eval
present, via the `white_blunders IS NOT NULL` summary proxy) is **strongly bimodal**:

| Metric | Value |
|---|---|
| Median analyzed games/user | **6** |
| p75 | 511 |
| p90 | 1,062 |
| max | 5,133 |
| Avg % of a user's games analyzed | 12.2% |
| Users ≥20 / ≥50 / ≥100 / ≥200 analyzed | 51 / 48 / 41 / 37 |

Two populations: a bottom half with almost nothing (median 6), and a top ~37–51 users
with hundreds-to-thousands; almost no middle.

**Root cause: chess.com exposes no Stockfish evals via its API for any game.** lichess
provides per-ply evals only when the user had server analysis on (or broadcast/study).
So flaw-classifiable games ≈ a minority of lichess games; chess.com-only users have ~0.
This gates **both** halves of the comparison at once — player and opponent flaws are
classified from the *same* full-game eval, so the bottleneck is per-game, and any fix
serves the whole feature.

**Consequences for SEED-040:**
- The section gate is load-bearing. At scale the comparison is meaningful only for the
  ~37–51 heavy-analysis users until coverage rises. Frame as an engaged-analysis
  feature; the empty state must drive "get more games analyzed."
- The combos stay the open risk (rare intersections need many analyzed games) — Q-007
  halves 1b/2, deferred to post-materialization.

**Raising coverage is an upstream dependency, NOT part of SEED-040.** Two paths:

1. **Client-side bulk analysis (`stockfish.wasm`)** — [[SEED-012-client-side-stockfish-tactics]],
   "the enabler." Opt-in, batched, position-keyed storage with cross-user dedup. No
   server CPU, but requires the user to run it.
2. **Server-side idle-time analysis with a priority queue (NEW idea, 2026-06-09)** — run
   Stockfish on the prod server when nothing more important is running, draining a
   priority queue ordered by: **active users** (recent `last_activity`), **more recent
   games**, **longer time controls** first. Centralized and trustworthy (no fake-eval
   concern), and works for ALL users with no client action.
   - **Tension:** reopens SEED-012's locked non-goal #1 ("do not fall back to a
     server-side queue"), set when the box was 4-vCPU. Box is now CPX42 (8 vCPU / 16 GB),
     so revisiting is legitimate. Recorded as a SEED-012 amendment, not folded silently.
   - **Headroom is generous — Stockfish was NOT the OOM cause.** The FLAWCHESS-3Q / 2026-03
     OOM-kills were **import memory pressure** (oversized/concurrent imports, batch size,
     SQLAlchemy connection-pool exhaustion vs host RAM); the 2026-05-21 incident had no
     Stockfish at all. So ~6 of 8 cores can run analysis **constantly**, not one timid
     niced worker. The real requirement is **fast preemption**: yield cores immediately
     when higher-priority work arrives — uvicorn request handling, Postgres load, and
     above all the import-time eval pass (never compete with an active import). Keep the
     total memory footprint bounded so a concurrent import + the analysis workers + Postgres
     coexist within RAM (the actual OOM lesson), but core count is not the constraint.
   - **Priority refinements:** prefer longer-TC games that *lack* lichess evals (bullet
     is low-value and rarely analyzed); recent + active-user games first matches where the
     comparison actually gets viewed. Reuse SEED-012's position-keyed schema so server and
     client work share the same dedup'd store.

Both paths are eval-pipeline concerns owned by SEED-012; SEED-040 just consumes the
coverage they produce and works today for the ~37 heavy-analysis users regardless.

## Recommended milestone phase breakdown (recommendation only — NOT roadmapped)

Per the no-unrequested-phase-planning rule, this is a suggestion to consider when the
milestone is actually scoped; no ROADMAP entries were written.

1. **Opponent-flaw materialization** (foundation; shared with SEED-038/039). Add
   `is_opponent` to `game_flaws`, drop the player-only upsert filter, reclassify/backfill.
   `is_opponent` is derivable from ply parity + player color, so it's a query-convenience
   denormalization.
2. **Benchmark backfill + `/benchmarks` extension.** Run the existing backfill over the
   benchmark DB; extend `/benchmarks` to emit ELO×TC quartiles + ELO/TC marginals for
   each flaw-delta metric; run the collapse verdict per metric.
3. **API + UI.** New/extended flaw-stats endpoint returning per-tag deltas + CIs +
   zone bounds; the bullet-chart grid frontend (replaces the current tag-distribution
   zone; keeps the trend chart comparison-free).

## Open questions deferred to plan time

- **Filter × blue-zone interaction:** the TC filter shifts which (ELO, TC) zone you're
  compared against; platform/color/opponent-type/recency are user-local and move only
  your point estimate, not the zone (the percentile-chip-disclosure precedent). Needs a
  tooltip line.
- **Trend chart metric:** keep blunders/game or switch to Flaw Rate (M+B/100) for
  headline consistency.
- **Section-gate floor value N:** Q-007 (above) shows the prod distribution is bimodal;
  a ~20-analyzed-game floor admits ~half of active users. Final N + the combo CI-width
  check await opponent-flaw materialization (Q-007 halves 1b/2).

## Breadcrumbs

- `frontend/src/pages/library/` — `StatsTab.tsx` → `GlobalStatsPage` → `FlawStatsPanel.tsx`
  (current zones: `FlawStatsBand`, `FlawTrendChart`, `FlawTagDistribution`).
- `app/routers/library.py` (`GET /api/library/flaw-stats`),
  `app/services/library_service.py` (`get_flaw_stats`),
  `app/schemas/library.py` (`FlawStatsResponse`).
- `app/models/game_flaw.py` — `GameFlaw` (M+B-only; no `is_opponent` yet).
- `app/repositories/game_flaws_repository.py` — the player-only filter to drop.
- `app/services/flaws_service.py` — `_run_all_moves_pass` (classifies both colors already).
- `app/services/global_percentile_cdf.py` — endgame CDF infra (the *heavy* B this seed
  deliberately does NOT replicate; the light delta-IQR zone is the alternative).
- `/benchmarks` skill + `reports/benchmarks-latest.md` — the collapse-verdict framework.
- `.planning/notes/flaw-tag-definitions.md`, `.planning/notes/flaw-tag-naming.md` — taxonomy.

## Notes

Captured 2026-06-09 from a `/gsd-explore` session. Forward-looking seed only — no
roadmap phase was created (per project convention + the no-unrequested-planning rule).
The user framed this as milestone-sized with opponent-flaw materialization as phase 1.
Enrich or promote when the milestone is scoped.
