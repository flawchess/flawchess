# Phase 114: Benchmark Flaw-Delta Zone Computation - Context

**Gathered:** 2026-06-10
**Status:** Ready for planning

<domain>
## Phase Boundary

Extend the `/benchmarks` pipeline with a **new chapter** that computes a lightweight
per-(ELO bucket × TC) "typical" zone for every flaw-delta metric. For each cohort user,
compute their own **you−opponent delta** for each metric over their own games, then emit
**Q1/Q3 quartiles** per cell plus ELO and TC marginals, with the established **Cohen's-d
collapse verdict** per metric per axis. This is the *light* "B" — two quartiles of one
derived metric per cell — deliberately **NOT** the heavy 99-breakpoint endgame CDF.

The numbers come from the deterministic generator (`scripts/gen_benchmarks.py` +
`scripts/benchmarks/` modules) against the **benchmark DB**, where Phase 113 already
materialized **both sides'** flaws in `game_flaws`. The `/benchmarks` SKILL.md narrates
the new chapter's artifact into the report under `reports/benchmark/`.

**This phase is benchmark-computation only.** It produces the report (raw quartiles +
marginals + verdicts + viability diagnostics). The you-vs-opponent comparison endpoint and
the bullet-grid UI are Phase 115; the final editorial zone constants are hand-authored in
Phase 115 from this report.
</domain>

<decisions>
## Implementation Decisions

### Unified estimator — one denominator policy for all 13 metrics (amends SEED-040, voids FLAWCMP-02)
- **D-01:** **All 13 flaw-delta metrics use the same estimator: a paired per-game delta on a
  per-100-of-your-own-moves basis.** Per game: `(your_tag_count − opp_tag_count) /
  your_moves_in_game × 100`. Per-cohort-user delta = the **mean of those paired per-game
  deltas across the user's analyzed games**. Then take **Q1/Q3 across cohort users** per
  (ELO×TC) cell. The **game is the independence unit**; the denominator (your moves) is
  **dense** (present in every game), so there is no per-game `0/0` and no pooling step.
  - This applies uniformly to **Flaw Rate, tempo (low-clock / hasty / unrushed), phase
    (opening / middlegame / endgame), opportunity (miss / lucky), impact (reversed /
    squandered), and the two combos** — there is **no count-rate vs proportion split**.
  - **Drops SEED-040's family split** (count-rate per-100-moves vs proportion-over-
    opportunities). **No opportunity denominators, no Wilson difference-of-proportions.**
- **D-02 (the deciding analysis):** The only thing an opportunity denominator buys is
  exposure-conditioning, and that justification did not survive scrutiny:
  1. In a **you−opponent paired** design the conditioning is only **partial** — exposure
     cancels asymmetrically (the stronger side makes fewer errors → hands fewer "gifts",
     so the two sides' opportunity counts differ *by skill*).
  2. **ELO-matched pairing already neutralizes most of it** — chess.com/lichess pairing
     makes the cohort user's winning-positions-reached ≈ their opponents' across the matched
     game set, so the exposure confound on the *delta* is **second-order**. This cuts both
     ways: it makes per-100-moves good enough **and** makes the opportunity denominator
     largely unnecessary.
  3. The split's price was steep: two estimators, sparse `0/0` denominators, **thinner IQR
     zones** (zone stability *is* the FLAWBMK-02 deliverable), the impact-threshold
     recalibration tax, mixed UI units, and Wilson/FLAWCMP-02 machinery in 115.
  4. The product is **impact-weighted leak-finding** vs opponents, where per-100-moves is the
     better default — a rare-situation weakness stays near zero instead of screaming off a
     1-of-2 sample.
- **D-03:** **Residual caveat — `squandered` / `lucky` (state-conditional metrics) read
  partly as "how often the situation arose," not pure conversion skill.** Under ELO-matching
  this is second-order; it is disclosed via a **Phase 115 tooltip line**, not corrected with a
  separate denominator. (A plan-time spot-check of the squandered/lucky exposure confound
  against the materialized cohort data is welcome but not gating.)
- **D-04:** **Amendment fan-out — flag for the planner and update REQUIREMENTS.md
  traceability:**
  - **SEED-040** "Locked design decisions" table rows for *Denominator (count-rate families)*,
    *Proportion CI method*, and the *Statistical method detail* split are **amended** to the
    single unified estimator above.
  - **FLAWCMP-02** (Wilson difference-of-proportions for proportion families) is **voided** —
    Phase 115's endpoint uses the unified paired per-game delta for **all** families. The
    CI method becomes bootstrap/normal over per-game deltas for every bullet (a 115 concern;
    114 computes no CI).

### Combo-zone scope — compute uniformly + viability diagnostic
- **D-05:** Phase 114 computes benchmark zones for the **two curated combos**
  (`hasty + miss` flagship, `low-clock + miss`) as **two more metrics in the same pipeline**
  (trivial post-unification: numerator = count of the user's moves carrying **both** tags,
  denominator = your moves, per-100, paired). **Combos are not deferred to zoneless.**
- **D-06:** The generator additionally emits a **per-metric viability diagnostic** — e.g.
  number of cohort users contributing a non-zero delta, number of cells with a non-degenerate
  IQR, median events/user — so **Phase 115 can satisfy FLAWCMP-04** (validate combo CI-width
  adequacy against the materialized data) by **reading** it from the artifact rather than
  re-deriving it. Combos are the rarest numerators, so this diagnostic is load-bearing for them
  and for `low-clock` / `unrushed`.

### Thin-cell handling — suppress, fall back to the marginal
- **D-07:** A cell-specific Q1/Q3 is emitted **only when the cell clears the contributor
  floor**; otherwise the cell's zone is **null**. Phase 115 falls back to the metric's
  **marginal (ELO or TC) or global zone**, which the **Cohen's-d collapse verdict already
  produces**. A thin cell therefore just uses the broader zone — no degenerate narrow band is
  ever shipped. Reuses the existing benchmark **sparse-cell methodology** (the <30-user
  marginal-exclusion pattern).

### Per-user inclusion — uniform min-analyzed-games floor
- **D-08:** Cohort-user inclusion in the Q1/Q3 distribution is gated by a **single uniform
  "min analyzed games per cohort user" floor** applied to **all 13 metrics** (a user below it
  contributes no delta). The uniform floor matches the unified estimator (no per-tag
  opportunity counts to gate on). **Exact N is set at plan time** by measuring the cohort
  distribution. The existing **≥30-contributing-users-per-cell** floor stays on top
  (cell-level stability).

### Zone delivery — report only; editorial constants in Phase 115
- **D-09:** Phase 114's deliverable is the **benchmark report** (FLAWBMK-04): per-cell Q1/Q3 +
  ELO/TC marginals + per-axis Cohen's-d verdicts + combo viability diagnostics — the **raw
  data**. **No new artifact infrastructure** (no committed JSON/Python zone module, no DB
  table). The seed's "lightweight, not the CDF infra" mandate is honored.
- **D-10:** **Phase 115 hand-authors the final zone constants with editorial judgment** from
  this report — the `endgame_zones.py` pattern, per the project's "editorial judgement over IQR
  for zone bands" rule (tighten the band when small effects are meaningful). The report
  presents the IQR; the human sets the shipped band. The generator's gitignored
  `benchmarks-generated.json` intermediate ensures the raw numbers are correct without a new
  committed artifact.

### Claude's Discretion
- Exact placement/numbering of the new benchmark chapter in SKILL.md + the report layout (a new
  top-level chapter, e.g. "§5 Flaw-Delta Zones", mirroring §3's per-metric table shape).
- The concrete `scripts/benchmarks/` module structure, SQL, and the source of the per-game
  **move-count denominator** (see Integration Points — `game_flaws` lacks total moves; the
  generator must join move/ply counts).
- The exact form of the viability-diagnostic columns (D-06).
- Whether to add a chapter-diff gate test under `tests/scripts/benchmarks/` mirroring the
  existing `test_chapter*_diff.py` pattern (recommended for the code/LLM seam, but planner's
  call on scope).
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Design source (locked, with this phase's amendments)
- `.planning/seeds/SEED-040-flaw-stats-opponent-comparison.md` — milestone design + the
  v1 bullet inventory and "Statistical method detail". **Amended by D-01..D-04:** the
  count-rate/proportion family split and the Wilson proportion method are replaced by the
  single unified per-100-moves paired-delta estimator.
- `.planning/REQUIREMENTS.md` §"Benchmark 'Typical' Zone (FLAWBMK)" — FLAWBMK-01..04, and
  §"You-vs-Opponent Comparison API (FLAWCMP)" — note **FLAWCMP-02 is voided** here (D-04).

### Benchmark pipeline (the surface being extended)
- `.claude/skills/benchmarks/SKILL.md` — the generator-driven workflow, collapse-verdict
  methodology (§"Collapse verdict methodology (Cohen's d)"), cell anchoring, equal-footing
  opponent filter, sparse-cell handling, display formatting, and **Report file layout**. The
  new chapter is narrated, not hand-computed.
- `scripts/gen_benchmarks.py` + `scripts/benchmarks/` — the deterministic generator the new
  flaw-delta chapter plugs into; emits `reports/benchmark/benchmarks-generated.{json,md}`.
- `tests/scripts/benchmarks/test_chapter*_diff.py` — the numeric-diff gate pattern (excluded
  from the default `pytest` run; run on demand with an explicit path).
- `reports/benchmark/benchmarks-latest.md` — the report to extend; "Recommended thresholds
  summary" + "Top-axis collapse summary" are the headline deliverables to mirror.

### Flaw classification + opponent derivation (Phase 113 hand-off)
- `app/services/flaws_service.py` — `classify_game_flaws` / `_run_all_moves_pass` (both sides
  classified with per-mover ES); the tag semantics the deltas aggregate.
- `app/repositories/query_utils.py` — **`is_opponent_expr(ply, games.user_color)`** (Phase 113
  D-01) + the `player_only` inverse; the single source of the ply→side parity convention used
  to split player vs opponent rows at read time.
- `.planning/notes/flaw-tag-definitions.md` — flaw-tag definitions incl. the impact
  (`reversed` / `squandered`) thresholds recalibrated 2026-06-09. (The recalibration's
  *denominator-density* rationale is partly moot under D-01, but the raw event-count gain still
  helps zone stability.)
- `.planning/notes/flaw-tag-naming.md` — tag naming.

### Prior-phase context
- `.planning/phases/113-opponent-flaw-materialization/113-CONTEXT.md` — D-01 (derive
  `is_opponent`, no column), D-08 (benchmark cohort `game_flaws` backfilled = this phase's
  input). The benchmark backfill is the **hand-off** that makes 114 readable.

### Zone-delivery precedents (for Phase 115's editorial constants, D-10)
- `app/services/endgame_zones.py` + `scripts/gen_endgame_zones_ts.py` — the hand-authored
  Python zone registry + TS codegen pattern (the model for 115's flaw-delta zone constants).
- `app/services/global_percentile_cdf.py` — the **CDF DB-table** infra deliberately **NOT**
  replicated here (the heavy "B" the seed rejects).
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **The whole `/benchmarks` generator framework** — cell anchoring, ELO/TC bucketing from
  game-time rating, the ≥30-per-cell floor, the equal-footing opponent filter, the Cohen's-d
  collapse-verdict thresholds (<0.2 collapse / 0.2–0.5 review / ≥0.5 keep), and the
  rotate-then-write report layout. The flaw-delta chapter is a **new metric family on this
  rail**, not new infrastructure.
- **`is_opponent_expr` (Phase 113)** — the player/opponent split for computing you−opponent
  deltas straight off the materialized `game_flaws`, no `flaws_service` re-run.
- **Materialized benchmark `game_flaws` (Phase 113 D-08)** — both sides' M+B flaws with full
  subject-relative tags already persisted in the benchmark DB; this phase's direct input.

### Established Patterns
- **Code/LLM seam** — the generator emits numbers; SKILL.md narration applies verdict *words*
  and authors recommendations. The new chapter follows the same seam, ideally with a
  `test_chapter*_diff.py`-style gate.
- **Editorial-judgment zone bands** — final shipped bands are hand-set from the report's IQR,
  not copied raw (D-10).

### Integration Points
- **Move-count denominator** — `game_flaws` stores flaw rows only, not the user's total
  move/ply count per game. The unified per-100-moves estimator (D-01) needs `your_moves_in_game`
  → the generator must join a per-game move/ply count (likely from `game_positions`). **Planner
  to confirm the exact source.**
- **Combo tags on one move** — a `hasty + miss` event is a single move carrying both tags; the
  flaw row's tag set is the join key. Combo numerators are the rarest → the D-06 viability
  diagnostic.
- **Hand-off to Phase 115** — the report's quartiles/marginals/verdicts feed 115's hand-authored
  zone constants (D-10); the unified estimator (D-01) and the voided FLAWCMP-02 (D-04) reshape
  115's endpoint to a single delta+CI method for all bullets.
</code_context>

<specifics>
## Specific Ideas

- The user drove a multi-round challenge to the count-rate/proportion split and converged
  (from both directions) on a **single per-100-of-your-moves paired-delta estimator for all
  metrics**. The deciding insight the user surfaced: *the regime is set by the denominator's
  density, not the numerator's* — and once ELO-matched pairing is taken into account, the
  opportunity denominator's exposure-conditioning is second-order, not worth its complexity
  cost. Claude initially recommended keeping the split and **reversed** under the user's
  reasoning.
- Decision rule that emerged: prefer the **simpler, denser, more zone-stable** estimator unless
  a confound is first-order; disclose the residual (`squandered`/`lucky` exposure) in a tooltip
  rather than correcting it with a parallel method.
</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope. Tactic-motif bullets (SEED-039) remain explicitly
zoneless/out-of-scope until cohort-wide Stockfish PVs exist; eval-coverage raising (SEED-012)
stays an upstream eval-pipeline concern, not part of this phase.
</deferred>

---

*Phase: 114-benchmark-flaw-delta-zone-computation*
*Context gathered: 2026-06-10*
