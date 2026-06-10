# Requirements: FlawChess — v1.25 Flaw-Stats Opponent Comparison

**Defined:** 2026-06-09
**Core Value:** Users get position-precise WDL analysis (openings + endgames + time pressure) on top of their actual chess.com / lichess games, with personalized LLM commentary and auto-generated strength/weakness reports. This milestone makes the Library flaw statistics *actionable* by contrasting the user against their actual opponents — flaw rates only reveal a *specific* recurring weakness when compared, not in absolute terms.

**Source:** `.planning/seeds/SEED-040-flaw-stats-opponent-comparison.md` (locked design decisions table). Continues phase numbering at **Phase 113**.

## v1 Requirements

Requirements for this milestone. Each maps to exactly one roadmap phase.

### Opponent-Flaw Materialization (FLAWX)

The data foundation: `game_flaws` currently stores player flaws only. Nearly free to extend — the classifier already evaluates both colors.

- [x] **FLAWX-01**: `game_flaws` records opponent flaws alongside player flaws, distinguished by a new `is_opponent` boolean derived from ply parity + the user's color in that game, so both sides' mistakes/blunders are queryable per game.
  - **AMENDED (113-CONTEXT D-01):** `is_opponent` is **derived at query time** via a single `is_opponent_expr(ply, games.user_color)` repo helper, **not** stored as a column. Both sides' flaws are persisted as rows in existing columns at their own plies; the player/opponent split is a read-time expression. Indexing gave no benefit (50% selective); the helper keeps the fragile parity convention in one tested place.
- [x] **FLAWX-02**: The player-only upsert filter is dropped from the materialization so opponent flaws persist on **every** classify path (import hook, `scripts/reclassify_positions.py`, `scripts/backfill_flaws.py`), preserving the D-10 single-classify-path invariant; no Stockfish/engine cost is added (both colors are already evaluated).
- [ ] **FLAWX-03**: ~~An Alembic migration adds `is_opponent` to `game_flaws` with index support enabling efficient per-side (player vs opponent) and combined per-game filtering.~~
  - **VOIDED (113-CONTEXT D-02/D-03):** No column → no migration, no new index. The premise was false — `is_opponent` is ~50% selective (no useful index) and a `GROUP BY` dimension, not a selective filter. Existing PK `(user_id, game_id, ply)` covers per-game two-sided reads; existing `(user_id, severity)` covers severity scans. **New required scope in its place:** retrofit a player-only gate onto every existing `game_flaws` reader (D-04) so opponent rows don't leak into the current self-only Library UI.
- [x] **FLAWX-04**: `scripts/backfill_flaws.py` repopulates opponent flaws for existing analyzed games (dev users 28 & 44 and the benchmark cohort), idempotent and batched (OOM-safe); prod `game_flaws` continues to ship empty (no prod data migration this milestone).

### Benchmark "Typical" Zone (FLAWBMK)

The lightweight "B" — the IQR of the *delta* across ELO-matched peers, deliberately NOT the heavy 99-breakpoint endgame CDF.

- [x] **FLAWBMK-01**: The benchmark pipeline computes, for each flaw-delta metric, every cohort user's own you−opponent delta over their own games (unified per-100-moves paired-delta for all metric families — see **AMENDED D-01** note in FLAWCMP-01/FLAWCMP-02), replicating the `flaws_service` classification over the cohort's moves.
- [x] **FLAWBMK-02**: The pipeline emits per-(ELO bucket × TC) **Q1/Q3 quartiles** of each delta plus ELO and TC marginals — two quartiles of one derived metric per cell, not a full percentile CDF.
- [x] **FLAWBMK-03**: The established Cohen's-d collapse verdict runs per metric per axis ({ELO, TC}) to decide whether each metric needs cell-specific zones or collapses to a single global zone.
- [x] **FLAWBMK-04**: The `/benchmarks` skill is extended to produce these flaw-delta quartiles, marginals, and collapse verdicts, written to the benchmark report under `reports/`.

### You-vs-Opponent Comparison API (FLAWCMP)

The statistical core: unified per-100-moves paired-delta for all metric families (D-01/D-04 amendment — SEED-040 family split superseded).

- [ ] **FLAWCMP-01**: ~~For **count-rate families** (Flaw Rate = M+B/100 moves, tempo `low-clock`/`hasty`/`unrushed`, phase `opening`/`middlegame`/`endgame`), the endpoint returns the mean **paired per-game delta** `(your_count − opp_count) / your_moves_in_game × 100` with a confidence interval (bootstrap or normal approx over the per-game deltas), the game as the pairing unit.~~
  - **AMENDED (114-CONTEXT D-01/D-04):** The endpoint uses the **unified per-100-moves paired-delta for ALL 15 metrics** (Flaw Rate, all tempo/phase/opportunity/impact tags, and both combos). There is no count-rate vs proportion family split. CI method: bootstrap or normal approx over per-game deltas for every bullet. SEED-040's "Denominator (count-rate families)" and "Statistical method detail → proportion families" rows are superseded.
- [ ] ~~**FLAWCMP-02**: For **proportion families** (`miss`, `lucky`, `reversed`, `squandered`), the endpoint returns the you−opponent **Wilson difference-of-proportions** with its CI, using the project's existing chess-score util (no parallel significance test invented).~~
  - **VOIDED (114-CONTEXT D-04):** The count-rate/proportion family split is superseded by the unified paired per-game delta estimator (D-01). Phase 115's endpoint uses the same per-100-moves estimator for all 15 metrics. Wilson difference-of-proportions is not implemented. SEED-040 "Proportion CI method" row is superseded.
- [ ] **FLAWCMP-03**: The flaw-stats endpoint returns the full 15-bullet inventory (expanded from ~13 to include `mistake` and `blunder` severity split) — per-tag delta + CI + (when available) benchmark zone bounds — honoring all existing game filters (platform, color, time control, rated, opponent type, recency) and the severity filter, which can still narrow the M+B base to blunders-only.
- [ ] **FLAWCMP-04**: The curated combo bullets `hasty + miss` (flagship, least confounded) and `low-clock + miss` are included in the inventory; their CI-width adequacy is validated at plan time against the materialized opponent-flaw data (combo viability is the milestone's known thin-sample risk).
- [ ] **FLAWCMP-05**: A section-level sample gate returns an "analyze more games" state below a floor N (value set at plan time against the bimodal prod distribution); above the floor every bullet returns its measure + CI (a wide bar reads as inconclusive), and a bullet returns a blank/no-zone state only on literally zero events for that tag.

### Bullet-Grid Presentation (FLAWUI)

Replaces the current self-only tag-distribution zone with the comparison surface. Reuses the SEED-021 bullet-chart component.

- [ ] **FLAWUI-01**: The flaw-stats panel's current tag-distribution zone is replaced by a uniform grid of ~13 bullet charts (reusing the `MiniBulletChart` / endgame "Clock Gap" pattern), one per tag: measure (you−opponent delta), CI error bar, and the benchmark "typical" blue zone.
- [ ] **FLAWUI-02**: Each bullet discloses its metric definition, sign convention, and — for clock-conditioned tags — the tempo-interaction caveat (clock-conditioned tags read high partly because burning your clock feeds the opponent thinking time), via the project's tooltip-popover pattern in a uniform grid.
- [ ] **FLAWUI-03**: A tooltip line discloses the filter×zone interaction: the TC filter changes which (ELO×TC) zone you are compared against, while user-local filters (platform / color / opponent type / recency) move only your point estimate, not the zone (the percentile-chip-disclosure precedent).
- [ ] **FLAWUI-04**: A bullet degrades gracefully — measure + CI always render when events exist; the blue zone renders only when the cohort stat exists for that metric (future tactic-motif bullets render zoneless without breaking the grid).
- [ ] **FLAWUI-05**: The flaw trend chart remains comparison-free (no opponent delta) — ELO-peer matching already irons out the absolute level; the signal lives in the bullets' *composition*, not a trend delta.
- [ ] **FLAWUI-06**: The bullet grid works on mobile (responsive layout) and follows browser-automation conventions (`data-testid`, ARIA labels, semantic HTML) on all new interactive elements and containers, with desktop + mobile parity.

## v2 Requirements

Deferred to future release. Tracked but not in this roadmap.

### Tactic-Motif Comparison (FLAWTAC — SEED-039)

- **FLAWTAC-01**: The you-vs-opponent comparison extends to tactic-motif families (missed forks/pins/skewers) once SEED-039 computes them; the A-style comparison backbone already accommodates them (CI vs opponents), zoneless until cohort PVs exist.
- **FLAWTAC-02**: `miss` upgrades from the v1 proxy ("failed to punish an error") to literal `missed-X` via the SEED-039 adjacency join (opponent `allowed-X` adjacent to your `is_miss`).
- **FLAWTAC-03**: The benchmark blue zone is computed for tactic-motif deltas (requires cohort-wide Stockfish PV lines — the expensive deferred part).

### Eval-Coverage Enablement (FLAWCOV — SEED-012)

- **FLAWCOV-01**: Analyzed-game coverage is raised (client-side `stockfish.wasm` and/or server-side idle-time priority-queue analysis) so the comparison serves all users, not just the ~37–51 heavy-analysis users it ships for. Owned by SEED-012; the gating upstream dependency for this feature's reach.

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Full benchmark **percentile CDF** on flaw deltas (the "heavy B") | Deliberately replaced by the light per-(ELO×TC) delta-IQR zone; the CDF cost trajectory does not survive the SEED-039 tactic-motif roadmap (would need Stockfish PVs across millions of cohort games per motif). |
| **Trend-chart** opponent comparison | ELO-peer matching already controls the absolute level; the actionable signal is in the bullets' composition, not a trend delta. |
| **Termination** patterns ("blunder less but flag more", timeout/resign) | Needs game-result/termination data (already `net_flag_rate`), not `game_flaws`; belongs to the Time Management surface, cross-linked, not duplicated here. |
| Direct **M-vs-B split** display | Single branded "Flaw Rate" bullet (M+B combined) for bigger N on rare tags; the existing severity filter still narrows to blunders-only. |
| **Per-100 vs per-game denominator toggle** | Removed — fixed at per-100 of your own moves (keeps the benchmark zone portable across ELO cells as game length rises with rating). |
| **Eval-coverage raising** (raising % of analyzed games) | Owned by SEED-012 (v2/FLAWCOV above); this milestone consumes existing coverage and ships working for engaged-analysis users. |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| FLAWX-01 | Phase 113 | Complete |
| FLAWX-02 | Phase 113 | Complete |
| FLAWX-03 | Phase 113 | Pending |
| FLAWX-04 | Phase 113 | Complete |
| FLAWBMK-01 | Phase 114 | Complete |
| FLAWBMK-02 | Phase 114 | Complete |
| FLAWBMK-03 | Phase 114 | Complete |
| FLAWBMK-04 | Phase 114 | Complete |
| FLAWCMP-01 | Phase 115 | Pending (amended D-01/D-04: unified estimator for all 15 metrics) |
| FLAWCMP-02 | Phase 115 | **VOIDED** (D-04: Wilson proportion method superseded by unified paired-delta) |
| FLAWCMP-03 | Phase 115 | Pending |
| FLAWCMP-04 | Phase 115 | Pending |
| FLAWCMP-05 | Phase 115 | Pending |
| FLAWUI-01 | Phase 115 | Pending |
| FLAWUI-02 | Phase 115 | Pending |
| FLAWUI-03 | Phase 115 | Pending |
| FLAWUI-04 | Phase 115 | Pending |
| FLAWUI-05 | Phase 115 | Pending |
| FLAWUI-06 | Phase 115 | Pending |
| FLAWTAC-01 | Deferred (v2 — SEED-039) | Deferred |
| FLAWTAC-02 | Deferred (v2 — SEED-039) | Deferred |
| FLAWTAC-03 | Deferred (v2 — SEED-039) | Deferred |
| FLAWCOV-01 | Deferred (v2 — SEED-012) | Deferred |

**Coverage:**

- v1 requirements: 19 total (1 voided: FLAWCMP-02)
- Mapped to phases: 19 ✓ (18 active + 1 voided)
- Unmapped: 0 ✓
- v2 (deferred, not in this roadmap): 4 — FLAWTAC-01/02/03 (SEED-039), FLAWCOV-01 (SEED-012); tracked in the table for completeness, owned by their seeds

---
*Requirements defined: 2026-06-09 (milestone v1.25 open, sourced from SEED-040)*
*Last updated: 2026-06-10 after roadmap creation (Phases 113–115 assigned)*
*Amended: 2026-06-10 (Phase 114 D-04 fan-out: FLAWCMP-02 voided, FLAWCMP-01 amended to unified estimator, FLAWBMK-01 updated)*
