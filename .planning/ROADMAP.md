# Roadmap: FlawChess

## Milestones

- ✅ **v1.0 Initial Platform** — Phases 1-10 (shipped 2024-03-15)
- ✅ **v1.1 Opening Explorer & UI Restructuring** — Phases 11-16 (shipped 2024-03-20)
- ✅ **v1.2 Mobile & PWA** — Phases 17-19 (shipped 2024-03-21)
- ✅ **v1.3 Project Launch** — Phases 20-23 (shipped 2026-03-22)
- ✅ **v1.4 Improvements** — Phase 24 (shipped 2026-03-22)
- ✅ **v1.5 Game Statistics & Endgame Analysis** — Phases 26-33 (shipped 2026-03-28)
- ✅ **v1.6 UI Polish & Improvements** — Phases 34-39 (shipped 2026-03-30)
- ✅ **v1.7 Consolidation, Tooling & Refactoring** — Phases 40-43 (shipped 2026-04-03)
- ✅ **v1.8 Guest Access** — Phases 44-47 (shipped 2026-04-06)
- ✅ **v1.9 UI/UX Restructuring** — Phases 49-51 (shipped 2026-04-10) — see [milestones/v1.9-ROADMAP.md](milestones/v1.9-ROADMAP.md)
- ✅ **v1.10 Advanced Analytics** — Phases 48, 52-55, 57, 57.1, 59-62 (shipped 2026-04-19) — see [milestones/v1.10-ROADMAP.md](milestones/v1.10-ROADMAP.md)
- ✅ **v1.11 LLM-first Endgame Insights** — Phases 63-68 (shipped 2026-04-24) — see [milestones/v1.11-ROADMAP.md](milestones/v1.11-ROADMAP.md)
- ✅ **v1.12 Benchmark DB Infrastructure & Ingestion Pipeline** — Phase 69 (shipped 2026-04-26) — see [milestones/v1.12-ROADMAP.md](milestones/v1.12-ROADMAP.md)
- ✅ **v1.13 Opening Insights** — Phases 70, 71, 71.1 (shipped 2026-04-27; Phases 72-74 descoped) — see [milestones/v1.13-ROADMAP.md](milestones/v1.13-ROADMAP.md)
- ✅ **v1.14 Score-Based Opening Insights** — Phases 75, 76, 77 (shipped 2026-04-29; INSIGHT-UI-04 descoped) — see [milestones/v1.14-ROADMAP.md](milestones/v1.14-ROADMAP.md)
- ✅ **v1.15 Eval-Based Endgame Classification** — Phases 78, 79 (shipped 2026-05-03; VAL-01 / PHASE-VAL-01 rescinded) — see [milestones/v1.15-ROADMAP.md](milestones/v1.15-ROADMAP.md)
- ✅ **v1.16 Stockfish Eval Analyses** — Phases 80, 80.1, 81, 82, 83 (shipped 2026-05-11) — see [milestones/v1.16-ROADMAP.md](milestones/v1.16-ROADMAP.md)
- ✅ **v1.17 Endgame Stats Card Redesign** — Phases 84-88.4 (shipped 2026-05-19; Phase 89 dropped, 87.3 superseded) — see [milestones/v1.17-ROADMAP.md](milestones/v1.17-ROADMAP.md)
- ✅ **v1.18 Import Pipeline Hardening** — Phases 90, 91, 92 (shipped 2026-05-22; PRs #130, #137, #138 + hotfix #139) — see [milestones/v1.18-ROADMAP.md](milestones/v1.18-ROADMAP.md)
- ✅ **v1.19 Endgame Percentiles** — Phases 93, 94, 94.1, 94.2, 94.3, 94.4 (shipped 2026-05-27; Phase 95 split out before milestone close) — see [milestones/v1.19-ROADMAP.md](milestones/v1.19-ROADMAP.md)
- ✅ **v1.20 Import Pipeline Hardening Follow-Up and Readiness** — Phases 95, 96 (shipped 2026-05-29) — see [milestones/v1.20-ROADMAP.md](milestones/v1.20-ROADMAP.md)
- ✅ **v1.21 Time-Control-Aware Endgame Metrics** — Phases 97, 98, 99, 99.1 (shipped 2026-05-31; PRs #160, #163/#164, #167, #168) — see [milestones/v1.21-ROADMAP.md](milestones/v1.21-ROADMAP.md)
- ✅ **v1.22 Maintenance — Test Isolation & Frontend Major Upgrades** — Phases 100, 101 (shipped 2026-05-31) — see [milestones/v1.22-ROADMAP.md](milestones/v1.22-ROADMAP.md)
- ✅ **v1.23 LLM Endgame-Insights Statistical-Reasoning Rework** — Phases 102, 103 (shipped 2026-06-03) — see [milestones/v1.23-ROADMAP.md](milestones/v1.23-ROADMAP.md)
- ✅ **v1.24 Library Page** — Phases 104–112 (shipped 2026-06-09) — see [milestones/v1.24-ROADMAP.md](milestones/v1.24-ROADMAP.md)
- ✅ **v1.25 Flaw-Stats Opponent Comparison** — Phases 113–115 (incl. 114.1) (shipped 2026-06-12) — see [milestones/v1.25-ROADMAP.md](milestones/v1.25-ROADMAP.md)
- ✅ **v1.26 Full-Game Eval Pipeline** — Phases 116–120 (incl. 117.1, 117.2) (shipped 2026-06-14) — see [milestones/v1.26-ROADMAP.md](milestones/v1.26-ROADMAP.md)
- ✅ **v1.27 Remote Eval Worker Fan-Out & In-App Feedback** — Phases 121–123 (shipped 2026-06-16; releases #199, #202, #203) — see [milestones/v1.27-ROADMAP.md](milestones/v1.27-ROADMAP.md)
- 🔄 **v1.28 Tactic Tagging** — Phases 124–129 (in progress)

## Phases

### Standalone (post-v1.27, milestone TBD)

- [x] **Phase 123.1: Opening-eval dedup cache table (SEED-053)** (INSERTED) — replace the drain's cross-user `DISTINCT ON (full_hash)` self-join with a position-keyed `opening_position_eval` cache table (~1.06M rows / ~80MB, resident); cuts the per-game dedup lookup from ~8.4 s avg to sub-ms, accelerating the ~245k-game tier-3 drain backlog. Drop-in for `_fetch_dedup_evals`, no dedup-semantics change. Also accelerates v1.28 (Phase 125 backfill needs full-eval'd games). (completed 2026-06-17)

### v1.28 Tactic Tagging

- [x] **Phase 124: Schema + Tactic Detector** — Alembic migration for `tactic_motif`/`tactic_piece` columns + the pure-CPU cook-heuristic reimplementation + hand-labeled fixture validation (completed 2026-06-18)
- [x] **Phase 125: Backfill Tactic Motifs** — run `backfill_flaws.py` over ~131k self-eval'd games; lichess-eval-only games stay NULL until full-eval'd via the existing tier-3 idle fleet (completed 2026-06-18)
- [ ] **Phase 126: Comparison Stats + Frontend** — `GET /api/library/tactic-comparison` endpoint + motif chips on flaw cards + MiniBulletChart you-vs-opponent motif grid
- [x] **Phase 127: Detector Hardening & Validation** — return motif depth from all detectors + store `*_tactic_depth`; lichess CC0 puzzle validation harness (precision AND recall); fix deep-scan/loose-pin false positives. De-risks 128/129. (completed 2026-06-19)
- [x] **Phase 128: Missed-Opportunity Tagging** — rename existing tactic cols to `allowed_*`, add `missed_*` set; second detector pass on the `flaw_ply` PV (SEED-054); backend filter + schema; mover-relative columns, `is_opponent_expr` narration (no `tactic_pov` column) (completed 2026-06-19)
- [x] **Phase 128.1: Add tactic motifs for lichess-theme coverage** (INSERTED) — close lichess `puzzleTheme.xml` gaps: split `discovered-check` out of discovered-attack, new `trapped-piece` detector, trivial `en-passant` + `promotion`/`under-promotion` tags; new precision floors baselined on TRAIN (SEED-058) (completed 2026-06-20)
- [x] **Phase 129: Tactic Filter UI** — composed motif × pov (missed/allowed) × depth-slider filter + display across flaw surfaces, desktop + mobile (completed 2026-06-20)

## Phase Details

### Phase 123.1: Opening-eval dedup cache table (SEED-053) (INSERTED)

**Goal**: The full-eval drain's opening-region eval/best_move dedup lookup is served by a position-keyed cache table instead of the cross-user self-join — sub-millisecond per lookup, no change to dedup semantics
**Depends on**: Nothing (standalone infra; pure drop-in for `_fetch_dedup_evals`)
**Requirements**: SEED-053 (no formal REQ IDs — infra optimization)
**Success Criteria** (what must be TRUE):

  1. A new Alembic migration adds `opening_position_eval(full_hash BIGINT PK, eval_cp SmallInteger, eval_mate SmallInteger, best_move VARCHAR(5))`; the dev DB migrates cleanly; a standalone idempotent backfill script populates it from existing our-engine opening evals (`DISTINCT ON (full_hash)` where `ply <= DEDUP_MAX_PLY` and the `has_engine_full_evals` predicate)
  2. The drain's opening-region write path upserts only freshly-computed engine misses into the cache (`INSERT … ON CONFLICT (full_hash) DO NOTHING`, batched in the existing write transaction); a freshly drained opening position appears in the cache
  3. `_fetch_dedup_evals` reads from `opening_position_eval` (`full_hash = ANY(:hashes)`) instead of the self-join, preserving every existing read-side guard (`ply <= DEDUP_MAX_PLY`, not flaw-adjacent, not terminal); a regression test asserts identical dedup results to the legacy self-join for the same fixture
  4. eval/flaw/pv output is unchanged (no behavioral diff in the drain); the lookup's measured time drops from seconds to low-ms on prod-like data
  5. The cache is seeded from prod our-engine data only; benchmark-DB seeding and a materialized view are explicitly rejected (provenance / no best_move-pv / refresh cost) and documented (per SEED-053 + 123.1-CONTEXT)

**Plans**: 2 plans

### Phase 124: Schema + Tactic Detector

**Goal**: The system can detect and store a tactic motif for any flawed move that has a stored refutation PV
**Depends on**: Nothing (first phase of this milestone — builds on v1.27 infrastructure)
**Requirements**: TACSCH-01, TACSCH-02, TACDET-01, TACDET-02, TACDET-03, TACDET-04
**Success Criteria** (what must be TRUE):

  1. A new Alembic migration adds nullable `tactic_motif` (SmallInteger enum) and `tactic_piece` (SmallInteger) columns to `game_flaws`; the dev DB migrates cleanly
  2. Given a stored `game_positions.pv` at `flaw_ply + 1`, the detector returns at most one motif name from the implemented MVP set (finalized during phase discussion) with a fixed priority order when multiple motifs fire
  3. The detector leaves `tactic_motif = NULL` when confidence is low rather than guessing; a hand-labeled per-motif fixture set passes with precision-first accuracy
  4. Motif detection runs inside `classify_game_flaws` (eval-drain flow-through) and `backfill_flaws.py` (recompute path) for both the player's and the opponent's flaws, with no new engine invocation

**Plans**: 4 plans

Plans:
**Wave 1**

- [x] 124-01-PLAN.md — Schema foundation: Alembic migration (3 nullable cols) + ORM columns + TacticMotifInt/Literal/dicts encoding shell + FlawRecord/flaw_record_to_row plumbing

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 124-02-PLAN.md — Detector module: PV parser + Core 8 + named-mate + tier-3 detectors + D-07 priority dispatcher (tactic_piece D-12, confidence D-11)

**Wave 3** *(blocked on Wave 2 completion)*

- [x] 124-03-PLAN.md — Hand-labeled fixtures from own prod flaws + precision harness enforcing D-10 bars (Core ≥90%, tier-3/named-mate ≥95%)

**Wave 4** *(blocked on Wave 3 completion)*

- [x] 124-04-PLAN.md — Wire detect_tactic_motif into _build_flaw_record for both colors (flows to classify + backfill, no new engine call)

### Phase 125: Backfill Tactic Motifs

**Goal**: All existing self-eval'd game flaws carry their tactic motif and piece tags; coverage is honest and verifiable
**Depends on**: Phase 124 (schema + validated detector)
**Requirements**: TACSCH-03
**Success Criteria** (what must be TRUE):

  1. Running `backfill_flaws.py` over the ~131k self-eval'd games (`full_evals_completed_at IS NOT NULL`) populates `tactic_motif` and `tactic_piece` for every flaw row where the detector fires (NULL rows reflect genuine low-confidence, not skipped positions)
  2. Lichess-eval-only flaws (~13.6k games with no `full_evals_completed_at`) keep `tactic_motif = NULL` — no bespoke job type, no separate backfill; coverage fills in via the existing tier-3 idle fleet
  3. Backfill is idempotent: re-running it produces the same result without duplicating or corrupting existing rows

**Plans**: 3 plans

- [x] 125-01-PLAN.md — Wave 0: extend test_backfill_flaws.py to assert tactic columns + build read-only coverage_report_tactic_motifs.py (D-04)
- [x] 125-02-PLAN.md — run dev backfill (D-02), prove honest coverage (SC#1/D-04), idempotency (SC#3/D-05), D-06 blast-radius
- [x] 125-03-PLAN.md — deferred prod runbook (D-01, documentation only)

**Note**: ROADMAP SC#1 (prod ~131k) is met-on-dev / prod-pending — Phase 125 completes on dev; prod execution is deferred (D-01).

### Phase 126: Comparison Stats + Frontend

**Goal**: Players can see which tactic motifs they allow more or less than their opponents, with significance gating and mobile parity
**Depends on**: Phase 125 (populated `tactic_motif` rows)
**Requirements**: TACCMP-01, TACCMP-02, TACCMP-03, TACUI-01, TACUI-02, TACUI-03
**Success Criteria** (what must be TRUE):

  1. `GET /api/library/tactic-comparison` returns per-motif rates (normalized per game or per 100 blunders) for player vs opponents, with significance verdict via the project's existing Wilson-based chess-score utility, honoring all game filters (time control, platform, rated, opponent type, recency, color) and severity
  2. Each flaw card in the Library shows its `allowed` motif as a family-colored chip with a definition popover, consistent with the shipped flaw-tag chip pattern
  3. The you-vs-opponent motif comparison surface (MiniBulletChart grid: measure + CI + benchmark zone where available, per-motif tooltips) renders on the Library page with a section-level sample gate below which the comparison is withheld
  4. All chips, comparison bullets, and interactive elements render correctly on mobile at 375px with `data-testid` and ARIA labels matching the project's browser-automation rules

**Plans**: 3 plans
**Wave 1**

- [x] 126-01-PLAN.md — Backend: `/tactic-comparison` endpoint + service/repo + `tactic_families` filter on `apply_game_filters()` + confidence-gated `tactic_motif`/`tactic_confidence` on flaw rows (wave 1)

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 126-02-PLAN.md — Frontend chip + filter: TAC_* theme constants, family taxonomy meta, `TacticMotifChip` on both flaw surfaces, beta-gated motif filter in FilterPanel (wave 2)

**Wave 3** *(blocked on Wave 2 completion)*

- [x] 126-03-PLAN.md — Frontend grid: `getTacticComparison` API + `useTacticComparison` hook + `TacticComparisonGrid` on the Library page (wave 3)

**UI hint**: yes

### Phase 127: Detector Hardening & Validation

**Goal**: Tactic tags are trustworthy — false positives are measured against independent ground truth and the worst offenders are fixed, and every tag carries the depth at which the motif occurs
**Depends on**: Phase 124 (detector + schema). Independent of Phase 126.
**Requirements**: (to be assigned during discuss-phase)
**Success Criteria** (what must be TRUE):

  1. Every detector returns the ply at which the motif fires; a new nullable `*_tactic_depth` SmallInteger is stored on `game_flaws` (populated on next drain/backfill; NULL on pre-existing rows is honest)
  2. A read-only validation harness scores the detector against the lichess CC0 puzzle database (FEN + solution Moves + Themes), reporting **precision AND recall** per motif, mapping our motifs to lichess theme names and explicitly listing motifs with no lichess equivalent (unvalidated, same status as today's query-suppressed set)
  3. The deep-scan / loose-pin false positives are fixed: `detect_fork` and `detect_pin` no longer attribute an incidental motif buried in a non-forcing continuation to the flaw (e.g. depth-bounded or relevance-gated), validated by the harness precision delta
  4. No vendoring or porting of AGPL `cook.py` — only the CC0 puzzle *data* is used; this is recorded in the test/harness docstring
  5. The self-labeled fixture circularity is documented and superseded: the precision/recall numbers in CI come from the independent puzzle set, not detector-bucketed fixtures

**Plans**: 4 plans
**Wave 1**

- [x] 127-01-PLAN.md — 4-tuple detector contract + depth + relevance gate + min-depth dispatch + tactic_depth column/migration (Wave 1)
- [x] 127-02-PLAN.md — harness infra: selector + committed CC0 fixture + motif→theme map + excluded tagger dir + pyproject ignore + CI step (Wave 1)

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 127-03-PLAN.md — measure precision/recall + depth-vs-Rating correlation, set floors from measured numbers, suppress sub-floor tier-3, supersede circular fixtures (Wave 2)

**Wave 3** *(blocked on Wave 2 completion)*

- [x] 127-04-PLAN.md — dev re-backfill validation (tactic_depth populated, fork/pin FP drop) + deferred prod runbook (Wave 3)

### Phase 128: Missed-Opportunity Tagging

**Goal**: A flaw can carry both the tactic the flaw-maker *missed* (the line they should have played) and the tactic they *allowed* (the refutation), distinguished without a perspective column
**Depends on**: Phase 127 (hardened detector + depth). SEED-054 `flaw_ply` PV coverage.
**Requirements**: (to be assigned during discuss-phase)
**Success Criteria** (what must be TRUE):

  1. The existing tactic columns are renamed to `allowed_tactic_motif`/`allowed_tactic_piece`/`allowed_tactic_confidence` (data preserved) and `allowed_tactic_depth` is added; a new `missed_tactic_*` set is added (motif/piece/confidence/depth)
  2. The detector runs a second pass on the `flaw_ply` PV with `pov = the mover`, populating `missed_*`; a flaw may have neither, one, or both column sets filled
  3. No `tactic_pov` column exists — orientation is the column source and user-perspective is derived via `is_opponent_expr(ply, user_color)`; narration follows the column-set × is_opponent matrix
  4. The inline-columns-vs-child-table decision is made and recorded during discuss-phase (lean inline, per the design note)
  5. Backend filtering and the comparison/flaw schemas expose both orientations; backfill is idempotent and gated on SEED-054 PV availability (lichess-only coverage fills in over time)

**Plans**: 4 plans

Plans:
**Wave 1**

- [x] 128-01-PLAN.md — Storage contract: rename tactic_* → allowed_tactic_* + add missed_tactic_* (data-preserving Alembic rename+add) + FlawRecord/write-path mapping (D-01, D-02, D-06)

**Wave 2** *(blocked on Wave 1)*

- [x] 128-02-PLAN.md — Detector second pass: orientation-parametrized _detect_tactic_for_flaw, missed pass on flaw_ply PV (pov=mover), both 4-tuples in _build_flaw_record (D-03, D-04, D-05, D-06)
- [x] 128-03-PLAN.md — Orientation-aware filter + schema contract: orientation enum at both filter sites (default allowed), full tactic_* → allowed_* rename ripple, both column sets on flaw/comparison schemas (D-07, D-08, D-09, D-10)

**Wave 3** *(blocked on Wave 2)*

- [x] 128-04-PLAN.md — Dev backfill (missed_* + allowed_tactic_depth fill, honest coverage, idempotency) + deferred folded 127/128 prod runbook (D-11, D-12, D-13)

### Phase 128.1: Add tactic motifs for lichess-theme coverage (discovered-check, trapped-piece, en-passant, promotion) (INSERTED)

**Goal:** Close lichess `puzzleTheme.xml` coverage gaps in `detect_tactic_motif` by adding four deterministically-detectable motifs — split `discovered-check` out of `discovered-attack` (near-free, logic already exists), a new `trapped-piece` detector (escape-square enumeration), and trivial `en-passant` + `promotion`/`under-promotion` tags. Each motif follows the 5-step recipe (Literal + IntEnum, detector, `motif_theme_map.py` entry, dispatch placement, precision floor baselined from a fresh TRAIN harness run; never lower an existing floor). Product call needed on whether to surface promotion/under-promotion as chips (move-type vs true motif).
**Requirements**: TBD (assign during discuss-phase)
**Depends on:** Phase 128
**Source:** SEED-058
**Plans:** 2/2 plans complete

Plans:

- [x] 128.1-01-PLAN.md — discovered-check (split from discovered-attack) + trapped-piece: two Tier-2 real-geometry motifs (ints 25-26), detectors, theme-map, dispatch ranks
- [x] 128.1-02-PLAN.md — en-passant/promotion/under-promotion move-type trio (ints 27-29) at a new lowest tier + MOVE_TYPE_MOTIFS frozenset, then the full 5-motif fresh-TRAIN precision-floor baseline

### Phase 129: Tactic Filter UI

**Goal**: Players can filter and read tactics along three axes — which motif, missed vs allowed, and difficulty (depth) — on both desktop and mobile
**Depends on**: Phase 128 (missed/allowed columns), Phase 127 (depth)
**Requirements**: TACUI-04, TACUI-05, TACUI-06, TACUI-07, TACUI-08
**Success Criteria** (what must be TRUE):

  1. A depth (difficulty) slider filters flaws by `*_tactic_depth`; always-on, default = Intermediate (Beginner/Advanced presets + custom slider); API param in half-moves (1:1 with the column), "moves deep" labels in the frontend (D-03)
  2. An Either/Missed/Allowed orientation toggle switches the tactic view, **defaulting to Either** (amended 2026-06-20 per D-07 — reverses the original "defaulting to missed"; the user directed Either as the neutral default); narration is the chip label + shared `TagLegend`
  3. The motif × orientation × depth filter composes cleanly with the existing Library filters; the tactic-comparison grid shows two bullets per family (Missed/Allowed), ranked top-6 by Missed with a "More Tactics" accordion, independent of the Flaws-tab filters
  4. All controls and chips render correctly on mobile at 375px with `data-testid` and ARIA labels per the browser-automation rules

**Plans**: 5 plans (3 original + 2 gap-closure for UAT G-01)
**Wave 1**

- [x] 129-01-PLAN.md — Backend: depth filter param + 3-value orientation ("either" OR-across-columns) at both filter sites + mate exemption; dual-orientation tactic-comparison endpoint ranked top-6 by Missed (TACUI-04, TACUI-05)

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 129-02-PLAN.md — Frontend filters: tacticDepth lib + TacticDepthFilter control + Either/Missed/Allowed toggle + store/query threading + orientation-prefixed dual chips, desktop + mobile (TACUI-06, TACUI-07)

**Wave 3** *(blocked on Wave 2 completion)*

- [x] 129-03-PLAN.md — Frontend grid: two-bullet family cards + top-6-by-Missed + "More Tactics" accordion (TACUI-08)

**Gap closure (UAT G-01 — "More Tactics" accordion unreachable: 6 families always = all families, overflow always empty; fix via tactic-family taxonomy redesign to 10 families)**

- [x] 129-04-PLAN.md — Backend taxonomy: rewrite `FAMILY_TO_MOTIF_INTS` to the authoritative 10 families (split pin_skewer→skewer/pin/x_ray, discovery→double_check/discovered_attack, add discovered_check/trapped_piece, drop combinations); update consumers + tests; no migration (TACUI-05, TACUI-08)
- [x] 129-05-PLAN.md — Frontend taxonomy hub: mirror the 10 backend keys in `tacticComparisonMeta.ts` + `theme.ts` per-family tokens + filter chips + motif defs + tests + `tsc -b`; accordion now renders 4 overflow families, closing G-01 (TACUI-05, TACUI-06, TACUI-07, TACUI-08)

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1-10. v1.0 phases | 36/36 | Complete | 2024-03-15 |
| 11-16. v1.1 phases | 14/14 | Complete | 2024-03-18 |
| 17-19. v1.2 phases | 5/5 | Complete | 2024-03-21 |
| 20-23. v1.3 phases | 10/10 | Complete | 2026-03-22 |
| 24. Web Analytics | 2/2 | Complete | 2026-03-22 |
| 26-33. v1.5 phases | 18/19 | Complete (28-03 deferred) | 2026-03-28 |
| 34-39. v1.6 phases | 11/11 | Complete | 2026-03-30 |
| 40-43. v1.7 phases | 11/11 | Complete | 2026-04-03 |
| 44-47. v1.8 phases | N/A | Complete | 2026-04-06 |
| 49-51. v1.9 phases | 7/7 | Complete | 2026-04-10 |
| 48, 52-62. v1.10 phases | 28/28 | Complete | 2026-04-19 |
| 63-68. v1.11 phases | 23/23 | Complete (Phase 67 descoped) | 2026-04-24 |
| 69. Benchmark DB Infra & Ingestion | 6/6 | Complete (follow-on phases → SEED-006) | 2026-04-26 |
| 70-71.1. v1.13 phases | 14/14 | Complete (Phases 72/73/74 descoped) | 2026-04-27 |
| 75-77. v1.14 phases | 16/16 | Complete (INSIGHT-UI-04 descoped) | 2026-04-29 |
| 78-79. v1.15 phases | 10/10 | Complete (VAL-01 / PHASE-VAL-01 rescinded) | 2026-05-03 |
| 80-83. v1.16 phases | 24/24 | Complete | 2026-05-11 |
| 84-88.4. v1.17 phases | ~54/~54 | Complete (89 dropped, 87.3 superseded) | 2026-05-19 |
| 90-92. v1.18 phases | 17/17 | Complete | 2026-05-22 |
| 93. Global Percentile Benchmark Artifact | 2/2 | Complete | 2026-05-22 |
| 94. Backend & Frontend Percentile Annotations | 3/3 | Complete | 2026-05-23 |
| 95-96. v1.20 phases | 5/5 | Complete | 2026-05-29 |
| 97-99.1. v1.21 phases | 15/15 | Complete (99.1 INSERTED) | 2026-05-31 |
| 100-101. v1.22 phases | 3/3 | Complete | 2026-05-31 |
| 102-103. v1.23 phases | 3/3 | Complete (103 unplanned follow-on) | 2026-06-03 |
| 104-112. v1.24 phases | 37/37 | Complete (111 shipped direct, no plan artifacts) | 2026-06-09 |
| 113. Opponent-Flaw Materialization | 3/3 | Complete | 2026-06-10 |
| 114. Benchmark Flaw-Delta Zone Computation | 1/1 | Complete | 2026-06-10 |
| 114.1. Replace move_count with exact ply_count (INSERTED) | 2/2 | Complete | 2026-06-10 |
| 115. You-vs-Opponent Comparison API + Bullet-Grid UI | 2/2 | Complete | 2026-06-11 |
| 116. All-Ply Engine Core | 3/3 | Complete (deployed #190) | 2026-06-14 |
| 117. Priority Queue + Flaw Integration | 3/3 | Complete (deployed #190) | 2026-06-14 |
| 117.1. Flaw-Eval Convention Fix (INSERTED, SEED-044) | 2/2 | Complete (deployed #190) | 2026-06-14 |
| 117.2. Wipe Eval-Only Engine Residue (INSERTED, SEED-044) | 1/1 | Complete (deployed #191) | 2026-06-14 |
| 118. Demand UX + Auto-Enqueue | 3/3 | Complete (verified; not yet deployed) | 2026-06-14 |
| 119. Eval-drain coverage (SEED-045, SEED-046) | 3/3 | Complete | 2026-06-14 |
| 120. Headless remote trusted-operator eval worker | 4/4 | Complete | 2026-06-14 |
| 121. Remote-worker tier-1 claiming (SEED-048) | 1/1 | Complete (release #199) | 2026-06-15 |
| 122. In-app feedback button (SEED-049) | 2/2 | Complete (release #202; UAT 5/5) | 2026-06-15 |
| 123. Remote-worker entry-ply fresh-import drain (SEED-051) | 3/3 | Complete (release #203; UAT 2/2) | 2026-06-16 |
| 123.1. Opening-eval dedup cache table (SEED-053) (INSERTED) | 2/2 | Complete | 2026-06-17 |
| 124. Schema + Tactic Detector | 4/4 | Complete    | 2026-06-18 |
| 125. Backfill Tactic Motifs | 3/3 | Complete    | 2026-06-18 |
| 126. Comparison Stats + Frontend | 3/3 | Complete   | 2026-06-18 |
| 127. Detector Hardening & Validation | 4/4 | Complete    | 2026-06-19 |
| 128. Missed-Opportunity Tagging | 4/4 | Complete    | 2026-06-19 |
| 129. Tactic Filter UI | 5/5 | Complete    | 2026-06-20 |

## Backlog

### Phase 999.1: Password Reset (BACKLOG)

**Goal:** Users can recover account access when they forget their password — request reset link, receive email, set new password
**Requirements:** TBD
**Plans:** 5/5 plans complete

Plans:

- [ ] TBD (promote with /gsd:review-backlog when ready)

### Phase 999.4: Position-Based Most Played Openings via game_positions (BACKLOG)

**Goal:** Redesign "Most Played Openings" to count how many games *passed through* each opening position (via `game_positions` Zobrist hash matching) instead of counting final opening name classifications from chess.com/lichess. Currently "1. e4" shows ~75 games (only games *classified* as "King's Pawn Game") while obscure specific lines rank higher. Position-based counting would show all ~2000+ games that played 1. e4, consistent with FlawChess's core Zobrist hash architecture. Requires JOIN from `openings` reference table to `game_positions` on FEN or precomputed hash, then `COUNT(DISTINCT game_id)`.
**Requirements:** TBD
**Plans:** 0 plans

Plans:

- [ ] TBD (promote with /gsd:review-backlog when ready)

### Phase 999.5: Hybrid Stockfish Eval for Conversion/Recovery (BACKLOG)

**Goal:** Use Stockfish eval (`eval_cp`) as the advantage/disadvantage signal for conversion/recovery classification when available, falling back to material imbalance + 4-ply persistence for games without eval. Stockfish eval is the gold standard (no persistence filter needed since eval handles transient trades natively). Currently only ~15% of Lichess games have eval data and chess.com has 0%, but this improves automatically as more games get server-analyzed. Validated in `docs/endgame-conversion-recovery-analysis.md`: persistence closes 50-70% of the gap to Stockfish for pawn/mixed endgames, but a hybrid approach would eliminate the remaining 5-8pp offset for eval-available games.
**Requirements:** TBD
**Plans:** 0 plans

Plans:

- [ ] TBD (promote with /gsd:review-backlog when ready)

### Phase 999.6: Opening Risk & Drawishness (BACKLOG)

**Goal:** Risk and drawishness metrics per position in the move explorer.
**Requirements:** TBD
**Plans:** 0 plans
**Context:** Moved from v1.10 Advanced Analytics — v1.10 is an endgame-focused milestone and opening risk metrics are a better fit for the upcoming Opening Insights milestone (discovering weaknesses in most-played opening lines). Re-evaluate scope at that time.

Plans:

- [ ] TBD (promote with /gsd-review-backlog when ready)

*Phase 999.7 (LLM Endgame-Insights Statistical-Reasoning Rework) promoted to active Phase 102 (v1.23) on 2026-06-01 via `/gsd-explore`; shipped 2026-06-03.*

*Phase 103 (Endgame report LLM prompt refinements) shipped 2026-06-03 as an unplanned follow-on under v1.23 — see the collapsed v1.23 block above and [milestones/v1.23-ROADMAP.md](milestones/v1.23-ROADMAP.md).*

### Phase 130: Tactic tag improvements and fixes

**Goal:** [To be planned]
**Requirements**: TBD
**Depends on:** Phase 129
**Plans:** 0 plans

Plans:

- [ ] TBD (run /gsd-plan-phase 130 to break down)

---

<details>
<summary>✅ v1.27 Remote Eval Worker Fan-Out & In-App Feedback (Phases 121–123) — SHIPPED 2026-06-16</summary>

Three independent seeds grouped at close per the standalone-then-regroup pattern (cf. v1.20); each phase shipped to prod standalone (releases #199, #202, #203) and soaked before grouping. Two phases extend the v1.26 remote-eval-worker contract (SEED-048 / Phase 120) so off-box compute helps beyond the idle tier-3 backlog; the third adds an in-app feedback channel.

- [x] Phase 121: Remote-worker tier-1 claiming (SEED-048) (1/1 plan) — remote workers can claim tier-1 single-game "analyze" jobs (server-busy overflow, FCFS), opaque job-token threaded lease→submit with `status='leased'` stamp guard, idle_sleep 5s→1s — completed 2026-06-15 (release #199)
- [x] Phase 122: In-app feedback button (SEED-049) (2/2 plans) — `feedback` table + thin POST /api/feedback, Sentry signal tagged with ELO bucket/platform, floating auto-hiding button (yields to overlays, iOS safe-area) + modal (required text + optional 3-point sentiment) — completed 2026-06-15 (release #202); UAT 5/5 pass
- [x] Phase 123: Remote-worker entry-ply fresh-import drain (SEED-051) (3/3 plans) — three-rung worker ladder (tier-1 > entry-ply > tier-3), batched depth-15 entry-lease/entry-submit endpoints, one nullable `games` lease column + SKIP-LOCKED LIFO claim, D-5 backlog-depth gate, CR-01 zero-target livelock fix — completed 2026-06-16 (release #203); UAT 2/2 pass, verified on a real 5,132-game first import

See [milestones/v1.27-ROADMAP.md](milestones/v1.27-ROADMAP.md) for full details.

</details>

<details>
<summary>✅ v1.26 Full-Game Eval Pipeline (Phases 116–120, incl. 117.1, 117.2) — SHIPPED 2026-06-14</summary>

Turned eval coverage from "endgame-entry plies only" into a full-game background analysis pipeline: every move evaluated by Stockfish at Lichess-parity strength (1M nodes/move), drained by a tiered priority queue (explicit > recent windows > idle backlog), results flowing automatically into the Library's flaw surfaces. Server-first v1 of SEED-012. Two correctness phases (117.1, 117.2) were inserted from SEED-044 for a pre/post-move eval off-by-one; Phase 119 (SEED-045/046) hardened drain coverage; Phase 120 (SEED-048) added an off-box headless eval worker.

- [x] Phase 116: All-Ply Engine Core (3/3 plans) — 1M-node all-ply drain + ply≤20 dedup + completion marker + memory bounds — completed 2026-06-14 (deployed #190)
- [x] Phase 117: Priority Queue + Flaw Integration (3/3 plans) — SKIP-LOCKED tiered queue + lease/report + tier-1 fan-out + best_move/PV + flaw flow-through + guest exclusion — completed 2026-06-14 (deployed #190)
- [x] Phase 117.1: Flaw-Eval Convention Fix (INSERTED, SEED-044) (2/2 plans) — post-move convention everywhere + dedup one-ply-shift + clean-slate re-eval — completed 2026-06-14 (deployed #190)
- [x] Phase 117.2: Wipe Eval-Only Engine Residue (INSERTED, SEED-044) (1/1 data migration) — NULLed 3,497 eval-only-residue engine games; lichess untouched — completed 2026-06-14 (deployed #191)
- [x] Phase 118: Demand UX + Auto-Enqueue (3/3 plans) — on-demand analyze affordances + coverage badges + in-flight status + guest promotion — completed 2026-06-14
- [x] Phase 119: Eval-drain coverage (SEED-045, SEED-046) (3/3 plans) — bounded-retry hole-filling + recency-weighted tier-3 lottery + lichess-leak fix + honest pulsing badge — completed 2026-06-14
- [x] Phase 120: Headless remote trusted-operator eval worker (SEED-048) (4/4 plans) — operator-token lease/submit endpoints + headless CLI worker + SF-version gate — completed 2026-06-14

See [milestones/v1.26-ROADMAP.md](milestones/v1.26-ROADMAP.md) for full details.

</details>

<details>
<summary>✅ v1.25 Flaw-Stats Opponent Comparison (Phases 113–115, incl. 114.1) — SHIPPED 2026-06-12</summary>

Reworked the Library flaw-stats surface from a self-only descriptive panel into an actionable you-vs-opponent comparison, in four phases: opponent-flaw materialization with a query-time player/opponent split (113), the benchmark §5 flaw-delta delta-IQR zones with Cohen's-d collapse verdicts (114), an inserted `move_count`→exact `ply_count` swap for an exact per-game denominator (114.1, SEED-041 §9), and the comparison surface — a unified per-100-moves paired-delta endpoint feeding a uniform 15-bullet `MiniBulletChart` grid (115). The SEED-040 count-rate/proportion family split was superseded by one unified estimator (FLAWCMP-02 voided); the `is_opponent` column was voided in favour of a query-time helper (FLAWX-03 voided). Deferred to v2: tactic-motif families (SEED-039) and coverage raising (SEED-012).

- [x] Phase 113: Opponent-Flaw Materialization (3/3 plans) — both-mover `game_flaws` + query-time `is_opponent_expr` split, reader gating, dev/benchmark backfill — completed 2026-06-10
- [x] Phase 114: Benchmark Flaw-Delta Zone Computation (1/1 plan) — §5 chapter, 15-metric Q1/Q3 + ELO/TC marginals + Cohen's-d verdicts — completed 2026-06-10
- [x] Phase 114.1: Replace `move_count` with exact `ply_count` (INSERTED, SEED-041 §9) (2/2 plans) — single migration + import-path + all readers; frontend cards + chapter5 §5 follow-on — completed 2026-06-10
- [x] Phase 115: You-vs-Opponent Comparison API + Bullet-Grid UI (2/2 plans) — unified per-100-moves paired-delta endpoint + family-grouped 15-bullet grid, tooltips, sample gate — completed 2026-06-11

See [milestones/v1.25-ROADMAP.md](milestones/v1.25-ROADMAP.md) for full details.

</details>

<details>
<summary>✅ v1.24 Library Page (Phases 104–112) — SHIPPED 2026-06-09</summary>

SEED-036's analysis half, built in nine phases: the Library shell + Import/Overview migration (104), the on-the-fly mistake-detection kernel (105), the Games-surface backend (106), the Games subtab UI (107), the Flaws subtab + `game_flaws` materialization + cross-tab Flaw filter (108), per-card expected-score eval charts (109), the flaw-tag taxonomy overhaul (110), a filter-UX polish pass (111), and the Flaws-card rework + single-game modal (112). The deferred SEED-036 surfaces (Analysis detail viewer, best-move endpoint) stay specified in `.planning/seeds/SEED-036-library-page-milestone.md`.

- [x] Phase 104: Library Page Shell + Import & Overview Subtab Migration (2/2 plans) — completed 2026-06-05
- [x] Phase 105: Mistake-Detection + Classification + Tagging Service on-the-fly (2/2 plans) — completed 2026-06-05
- [x] Phase 106: Games-Surface Backend — Mistake Filter, Per-Game Counts & Stats Aggregates (3/3 plans) — completed 2026-06-05
- [x] Phase 107: Games Subtab Frontend — Card Archive, Filters & Flaw-Stats Panel (7/7 plans) — completed 2026-06-06
- [x] Phase 108: Flaws Subtab — game_flaws Materialization, Per-Flaw Endpoint, Cross-Tab Flaw Filter & Miniboard List (8/8 plans) — completed 2026-06-06
- [x] Phase 109: Per-Card Expected-Score Eval Chart (Games subtab) (4/4 plans) — completed 2026-06-07
- [x] Phase 110: Flaw-Tag Taxonomy Overhaul — Rename, Impact-Family Rebuild, Tooltip Restore & Active-Filter Highlight (7/7 plans) — completed 2026-06-08
- [x] Phase 111: Library UI Polish — staged Apply-only filter model (shipped via direct commits; no plan artifacts) — completed 2026-06-09
- [x] Phase 112: Flaws Subtab Card Rework — 2-up Card grid + View-game modal (4/4 plans) — completed 2026-06-09

See [milestones/v1.24-ROADMAP.md](milestones/v1.24-ROADMAP.md) for full details.

</details>

*Earlier milestones below. v1.23 (Phases 102, 103) shipped 2026-06-03 — archived to [milestones/v1.23-ROADMAP.md](milestones/v1.23-ROADMAP.md); see the collapsed block. v1.22 (Phases 100, 101) shipped 2026-05-31 — archived to [milestones/v1.22-ROADMAP.md](milestones/v1.22-ROADMAP.md). v1.21 (Phases 97, 98, 99, 99.1) shipped 2026-05-31 — archived to [milestones/v1.21-ROADMAP.md](milestones/v1.21-ROADMAP.md).*

<details>
<summary>✅ v1.23 LLM Endgame-Insights Statistical-Reasoning Rework (Phases 102, 103) — SHIPPED 2026-06-03</summary>

- [x] Phase 102: Endgame LLM Statistical-Reasoning Rework (3/3 plans) — cohort-framed percentile annotations + time-pressure narration (Score Gap by Remaining Time / Clock Gap / Net Flag Rate) wired into the endgame-insights payload, prompt taught to reason over the v1.17–v1.21 metric set under the zone gate (p-values + CI bounds OUT), relaxed overview cap, vocabulary audit vs concepts accordion + tooltip popovers, `endgame_v35` → `endgame_v43`; HUMAN-UAT (LLM-07) signed off across short-history / sparse-section / full-history prod users — completed 2026-06-02 (LLM-01..07)
- [x] Phase 103: Endgame report LLM prompt refinements (unplanned follow-on) — three GM-feedback recommendation-quality fixes (decision-speed time-trouble advice, no fabricated mechanism, no named theoretical positions at any Elo), GM Noël Studer study link in the Recommendations card, prompt condensed ~35%, `endgame_v44` — completed 2026-06-03

See [milestones/v1.23-ROADMAP.md](milestones/v1.23-ROADMAP.md) for full details.

</details>

<details>
<summary>✅ v1.22 Maintenance — Test Isolation & Frontend Major Upgrades (Phases 100, 101) — SHIPPED 2026-05-31</summary>

- [x] Phase 100: Isolated Test DB Per Run (2/2 plans) — per-run/per-xdist-worker DB cloned from a migrated template; TRUNCATE retired; `pytest -n auto` green at 18.56s vs 40.29s serial (2.2x); concurrent-run isolation verified (SEED-031) — completed 2026-05-31
- [x] Phase 101: Frontend Major Dependency Upgrades (1/1 plan) — 11 frontend deps to latest major across 6 bisectable atomic clusters (lucide → Vite 8 → jsdom 29 → eslint 10 → TypeScript 6 → recharts 3); recharts 3 visual UAT (one regression fixed); peer-compat clean (SEED-032) — completed 2026-05-31

See [milestones/v1.22-ROADMAP.md](milestones/v1.22-ROADMAP.md) for full details.

</details>

<details>
<summary>✅ v1.21 Time-Control-Aware Endgame Metrics (Phases 97, 98, 99, 99.1) — SHIPPED 2026-05-31</summary>

- [x] Phase 97: Endgame Metrics by Time Control (4/4 plans, PR #160) — completed 2026-05-29
- [x] Phase 98: Per-TC Collapsible Endgame Type Cards (2/2 plans, PR #163; release #164) — completed 2026-05-30
- [x] Phase 99: Percentile Badges for Conversion, Parity, and Recovery (5/5 plans, PR #167) — completed 2026-05-30
- [x] Phase 99.1: Move Cohort CDF Out of Source into a DB Table (4/4 plans, PR #168; INSERTED) — completed 2026-05-31

See [milestones/v1.21-ROADMAP.md](milestones/v1.21-ROADMAP.md) for full details.

</details>

<details>
<summary>✅ v1.20 Import Pipeline Hardening Follow-Up and Readiness (Phases 95-96) — SHIPPED 2026-05-29</summary>

- [x] Phase 95: asyncpg COPY for `bulk_insert_positions` (2/2 plans, PRs #148/#149) — completed 2026-05-27
- [x] Phase 96: Import Readiness Gate (3/3 plans, PR #151) — completed 2026-05-28

See [milestones/v1.20-ROADMAP.md](milestones/v1.20-ROADMAP.md) for full details.

</details>

<details>
<summary>✅ v1.18 Import Pipeline Hardening (Phases 90-92) — SHIPPED 2026-05-22</summary>

- [x] Phase 90: Import Pipeline Memory Leak Fix + Resilience (3/3 plans, PR #130) — completed 2026-05-20
- [x] Phase 91: Two-lane import — defer Stockfish eval to in-process cold drain (8/8 plans, PR #137) — completed 2026-05-21
- [x] Phase 92: Custom date range filter (from/to dates replace closed Recency union) (6/6 plans, PR #138) — completed 2026-05-22

</details>

<details>
<summary>✅ v1.17 Endgame Stats Card Redesign (Phases 84-88.4) — SHIPPED 2026-05-19</summary>

- [x] Phase 84: Data plumbing — mirror-rate audit (1/1 plan, PR #95) — completed 2026-05-13
- [x] Phase 85: Section 1 — Games with vs without Endgame / 3-card composite (5/5 plans) — shipped 2026-05-14
- [x] Phase 85.1: Hypothesis tests + 95% CIs for Endgame Score Differences (4/4 plans; INSERTED) — shipped 2026-05-14
- [x] Phase 86: Section 2 — Endgame Metrics 4-card layout (5/5 plans) — shipped 2026-05-14
- [x] Phase 87: Section 3 — Per-type Endgame Type Breakdown cards (3/3 plans) — shipped 2026-05-15
- [x] Phase 87.1: Per-span ΔES metric for endgame types (4/4 plans, PR #97; INSERTED) — completed 2026-05-15
- [x] Phase 87.2: Section 2 — eval-based ΔES Score Gap bullets (4/4 plans, PR #98; INSERTED) — completed 2026-05-16
- [~] Phase 87.3: Endgame Skill v2 — Conv+Parity percentile composite (INSERTED) — **superseded** by Phase 87.4 (PR #102)
- [x] Phase 87.4: Drop Endgame Skill — Conversion ELO timeline (3/3 plans, PR #104; INSERTED) — completed 2026-05-16
- [x] Phase 87.5: Rebuild Endgame ELO on Endgame Score Gap (3/3 plans, PR #105; INSERTED) — completed 2026-05-17
- [x] Phase 87.6: Endgame ELO via logistic stretch around Actual ELO (3/3 plans, PR #106; INSERTED) — completed 2026-05-18
- [x] Phase 88: Time Pressure stats rework with hypothesis tests + CIs (15/15 plans, PR #107; INSERTED) — completed 2026-05-18
- [x] Phase 88.3: Endgame Stats viz refinements — inactivity-gap annotations + Overall Performance card (4/4 plans, PR #108; INSERTED) — completed 2026-05-18
- [x] Phase 88.4: Time Pressure card layout refactor (3/3 plans, PR #109; INSERTED) — completed 2026-05-19
- [→] Phase 89: Polish — popovers, gating decisions, automation rules, 375px parity — **dropped from scope** 2026-05-19 (not needed)

See [milestones/v1.17-ROADMAP.md](milestones/v1.17-ROADMAP.md) for full details.

</details>

<details>
<summary>✅ v1.16 Stockfish Eval Analyses (Phases 80, 80.1, 81, 82, 83) — SHIPPED 2026-05-11</summary>

- [x] Phase 80: Opening stats: middlegame-entry eval and clock-diff columns (6/6 plans) — completed 2026-05-05 (PR #80)
- [x] Phase 80.1: Include transpositions in Move Explorer and Opening Insights stats (4/4 plans) — completed 2026-05-07 (PR #82)
- [x] Phase 81: Endgame Start vs End — twin-tile section above the WDL table (5/5 plans) — completed 2026-05-09 (PR #85)
- [x] Phase 82: LLM prompt awareness of Endgame Start vs End metrics (4/4 plans) — completed 2026-05-10 (PR #86)
- [x] Phase 83: Stockfish-baseline predicted endgame score (5/5 plans) — completed 2026-05-11 (PR #88)

See [milestones/v1.16-ROADMAP.md](milestones/v1.16-ROADMAP.md) for full details.

</details>

<details>
<summary>✅ v1.0 Initial Platform (Phases 1-10) — SHIPPED 2024-03-15</summary>

- [x] Phase 1: Data Foundation (2/2 plans) — completed 2024-03-11
- [x] Phase 2: Import Pipeline (4/4 plans) — completed 2024-03-12
- [x] Phase 3: Analysis API (2/2 plans) — completed 2024-03-12
- [x] Phase 4: Frontend and Auth (3/3 plans) — completed 2024-03-12
- [x] Phase 5: Position Bookmarks (5/5 plans) — completed 2024-03-13
- [x] Phase 6: Browser Automation Optimization (2/2 plans) — completed 2024-03-13
- [x] Phase 7: Game Statistics and Charts (3/3 plans) — completed 2024-03-14
- [x] Phase 8: Games and Bookmark Tab Rework (3/3 plans) — completed 2024-03-14
- [x] Phase 9: Game Cards, Username Import, Pagination (8/8 plans) — completed 2024-03-15
- [x] Phase 10: Auto-Generate Position Bookmarks (4/4 plans) — completed 2024-03-15

</details>

<details>
<summary>✅ v1.1 Opening Explorer & UI Restructuring (Phases 11-16) — SHIPPED 2024-03-20</summary>

- [x] Phase 11: Schema and Import Pipeline (1/1 plan) — completed 2024-03-16
- [x] Phase 12: Backend Next-Moves Endpoint (2/2 plans) — completed 2024-03-16
- [x] Phase 13: Frontend Move Explorer Component (2/2 plans) — completed 2024-03-16
- [x] Phase 14: UI Restructuring (3/3 plans) — completed 2024-03-17
- [x] Phase 15: Enhanced Game Import Data (3/3 plans) — completed 2024-03-18
- [x] Phase 16: Game Card UI Improvements (3/3 plans) — completed 2024-03-18

</details>

<details>
<summary>✅ v1.2 Mobile & PWA (Phases 17-19) — SHIPPED 2024-03-21</summary>

- [x] Phase 17: PWA Foundation + Dev Workflow (1/1 plan) — completed 2024-03-20
- [x] Phase 18: Mobile Navigation (1/1 plan) — completed 2024-03-20
- [x] Phase 19: Mobile UX Polish + Install Prompt (3/3 plans) — completed 2024-03-21

</details>

<details>
<summary>✅ v1.3 Project Launch (Phases 20-23) — SHIPPED 2026-03-22</summary>

- [x] Phase 20: Rename & Branding (2/2 plans) — completed 2026-03-21
- [x] Phase 21: Docker & Deployment (2/2 plans) — completed 2026-03-21
- [x] Phase 22: CI/CD & Monitoring (2/2 plans) — completed 2026-03-21
- [x] Phase 23: Launch Readiness (4/4 plans) — completed 2026-03-22

</details>

<details>
<summary>✅ v1.4 Improvements (Phase 24) — SHIPPED 2026-03-22</summary>

- [x] Phase 24: Web Analytics (2/2 plans) — completed 2026-03-22

</details>

<details>
<summary>✅ v1.5 Game Statistics & Endgame Analysis (Phases 26-33) — SHIPPED 2026-03-28</summary>

- [x] Phase 26: Position Classifier & Schema (2/2 plans) — completed 2026-03-23
- [x] Phase 27: Import Wiring & Backfill (2/2 plans) — completed 2026-03-24
- [x] Phase 27.1: Optimize game_positions columns (via quick tasks) — completed 2026-03-26
- [x] Phase 28: Engine Analysis Import (2/3 plans, 28-03 deferred) — completed 2026-03-25
- [x] Phase 28.1: Import lichess analysis metrics (1/1 plan) — completed 2026-03-26
- [x] Phase 29: Endgame Analytics (3/3 plans) — completed 2026-03-26
- [x] Phase 31: Endgame classification redesign (2/2 plans) — completed 2026-03-26
- [x] Phase 32: Endgame Performance Charts (3/3 plans) — completed 2026-03-27
- [x] Phase 33: Homepage, README & SEO Update (3/3 plans) — completed 2026-03-28

</details>

<details>
<summary>✅ v1.6 UI Polish & Improvements (Phases 34-39) — SHIPPED 2026-03-30</summary>

- [x] Phase 34: Theme Improvements (2/2 plans) — completed 2026-03-28
- [x] Phase 35: WDL Chart Refactoring (2/2 plans) — completed 2026-03-28
- [x] Phase 36: Most Played Openings (1/1 plan) — completed 2026-03-28
- [x] Phase 37: Openings Reference Table & Redesign (3/3 plans) — completed 2026-03-28
- [x] Phase 38: Opening Statistics & Bookmark Rework (2/2 plans) — completed 2026-03-29
- [x] Phase 39: Mobile Opening Explorer Sidebars (1/1 plan) — completed 2026-03-30

</details>

<details>
<summary>✅ v1.7 Consolidation, Tooling & Refactoring (Phases 40-43) — SHIPPED 2026-04-03</summary>

- [x] Phase 40: Static Type Checking (2/2 plans) — completed 2026-04-01
- [x] Phase 41: Code Quality & Dead Code (4/4 plans) — completed 2026-04-02
- [x] Phase 41.1: Import Speed Optimization (2/2 plans) — completed 2026-04-03
- [x] Phase 42: Backend Optimization (2/2 plans) — completed 2026-04-03
- [x] Phase 43: Frontend Cleanup (1/1 plan) — completed 2026-04-03

</details>

<details>
<summary>✅ v1.8 Guest Access (Phases 44-47) — SHIPPED 2026-04-06</summary>

- [x] Phase 44: Guest Session Foundation — completed 2026-04-06
- [x] Phase 45: Guest Frontend — completed 2026-04-06
- [x] Phase 46: Email/Password Promotion — completed 2026-04-06
- [x] Phase 47: Google SSO Promotion — completed 2026-04-06

</details>

<details>
<summary>✅ v1.9 UI/UX Restructuring (Phases 49-51) — SHIPPED 2026-04-10</summary>

- [x] Phase 49: Openings Desktop Sidebar (1/1 plan) — completed 2026-04-09
- [x] Phase 50: Mobile Layout Restructuring (2/2 plans) — completed 2026-04-10
- [x] Phase 51: Stats Subtab, Homepage & Global Stats (4/4 plans) — completed 2026-04-10

See [milestones/v1.9-ROADMAP.md](milestones/v1.9-ROADMAP.md) for full details.

</details>

<details>
<summary>✅ v1.10 Advanced Analytics (Phases 48, 52-55, 57, 57.1, 59-62) — SHIPPED 2026-04-19</summary>

- [x] Phase 48: Conversion & Recovery Persistence Filter (2/2 plans) — completed 2026-04-07
- [x] Phase 52: Endgame Tab Performance (3/3 plans) — completed 2026-04-11
- [x] Phase 53: Endgame Score Gap & Material Breakdown (2/2 plans) — completed 2026-04-12
- [x] Phase 54: Time Pressure — Clock Stats Table (2/2 plans) — completed 2026-04-12
- [x] Phase 55: Time Pressure — Performance Chart (2/2 plans) — completed 2026-04-12
- [~] Phase 56: Endgame ELO Backend + Breakdown Table — cancelled, subsumed by Phase 57
- [x] Phase 57: Endgame ELO Timeline Chart (2/2 plans) — completed 2026-04-18
- [x] Phase 57.1: Endgame ELO Timeline Anchor Change + Volume Bars (2/2 plans, INSERTED) — completed 2026-04-18
- [→] Phase 58: Opening Risk & Drawishness — moved to backlog as Phase 999.6
- [x] Phase 59: Fix Endgame Conv/Parity/Recov per-game stats (3/3 plans) — completed 2026-04-13
- [x] Phase 60: Opponent-based Baseline for Endgame Conv/Recov (2/2 plans) — completed 2026-04-14
- [x] Phase 61: Test Suite Hardening & DB Reset (3/3 plans) — completed 2026-04-16
- [x] Phase 62: Admin User Impersonation (5/5 plans) — completed 2026-04-17

See [milestones/v1.10-ROADMAP.md](milestones/v1.10-ROADMAP.md) for full details.

</details>

<details>
<summary>✅ v1.11 LLM-first Endgame Insights (Phases 63-68) — SHIPPED 2026-04-24</summary>

- [x] Phase 63: Findings Pipeline & Zone Wiring (5/5 plans) — completed 2026-04-20
- [x] Phase 64: `llm_logs` Table & Async Repo (3/3 plans) — completed 2026-04-20
- [x] Phase 65: LLM Endpoint with pydantic-ai Agent (6/6 plans) — completed 2026-04-21
- [x] Phase 66: Frontend EndgameInsightsBlock & Beta Flag (5/5 plans) — completed 2026-04-22
- [~] Phase 67: Validation & Beta Rollout — descoped, replaced by public rollout for all users (commit c91478e)
- [x] Phase 68: Endgame Score Timeline (dual-line + shaded gap) (4/4 plans) — completed 2026-04-24

See [milestones/v1.11-ROADMAP.md](milestones/v1.11-ROADMAP.md) for full details.

</details>

<details>
<summary>✅ v1.12 Benchmark DB Infrastructure & Ingestion Pipeline (Phase 69) — SHIPPED 2026-04-26</summary>

- [x] Phase 69: Benchmark DB Infrastructure & Ingestion Pipeline (6/6 plans) — completed 2026-04-26 via PR #65 — INFRA-01..03, INGEST-01..06

See [milestones/v1.12-ROADMAP.md](milestones/v1.12-ROADMAP.md) for full details.

</details>

<details>
<summary>✅ v1.13 Opening Insights (Phases 70, 71, 71.1) — SHIPPED 2026-04-27</summary>

- [x] Phase 70: Backend opening insights service (5/5 plans) — completed 2026-04-26 via PR #66 — INSIGHT-CORE-01..09
- [x] Phase 71: Frontend Stats subtab — `OpeningInsightsBlock` (6/6 plans) — completed 2026-04-27 via PR #67 — INSIGHT-STATS-01..06
- [x] Phase 71.1: Openings subnav layout refactor — match Endgames pattern (3/3 plans, INSERTED) — completed 2026-04-27 via PR #68
- [~] Phase 72: Frontend Moves subtab — inline weakness/strength bullets — descoped 2026-04-27 (covered by MoveExplorer row tint via `getArrowColor`)
- [~] Phase 73: Meta-recommendation aggregate finding (stretch) — descoped 2026-04-27 (per-finding cards in Phase 71 already deliver actionable signal)
- [~] Phase 74: Bookmark-card weakness badge (stretch) — descoped 2026-04-27 (alert-fatigue concern with existing nav notification dots)

See [milestones/v1.13-ROADMAP.md](milestones/v1.13-ROADMAP.md) for full details.

</details>

<details>
<summary>✅ v1.14 Score-Based Opening Insights (Phases 75, 76, 77) — SHIPPED 2026-04-29</summary>

- [x] Phase 75: Backend — score metric and confidence annotation (4/4 plans) — completed 2026-04-28 (PR #69)
- [x] Phase 76: Frontend — score-based coloring, confidence badges, label reframe (8/8 plans) — completed 2026-04-28 (PR #70; inline confidence-mute hotfix PR #71)
- [x] Phase 77: Troll-opening watermark on Insights findings (4/4 plans) — completed 2026-04-28 (PR #72)

See [milestones/v1.14-ROADMAP.md](milestones/v1.14-ROADMAP.md) for full details.

</details>

<details>
<summary>✅ v1.15 Eval-Based Endgame Classification (Phases 78, 79) — SHIPPED 2026-05-03</summary>

- [x] Phase 78: Stockfish-Eval Cutover for Endgame Classification (6/6 plans) — completed 2026-05-03 (PR #78) — ENG-01..03, FILL-01..04, IMP-01..02, REFAC-01..05, VAL-02 (VAL-01 rescinded)
- [x] Phase 79: Position-phase classifier and middlegame eval (4/4 plans) — completed 2026-05-03 (PR #78) — CLASS-01..02, SCHEMA-01..02, PHASE-IMP-01..02, PHASE-FILL-01..03, PHASE-VAL-02..03, PHASE-INV-01 (PHASE-VAL-01 rescinded)

See [milestones/v1.15-ROADMAP.md](milestones/v1.15-ROADMAP.md) for full details.

</details>
