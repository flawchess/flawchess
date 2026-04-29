# Project Retrospective

*A living document updated after each milestone. Lessons feed forward into future planning.*

## Milestone: v1.14 — Score-Based Opening Insights

**Shipped:** 2026-04-29
**Phases:** 3 (75, 76, 77) | **Plans:** 16 | **Delivered via:** PRs #69, #70, #71 (inline confidence-mute hotfix), #72, #73 (quick task)
**Stats:** 123 files changed, +18,701 / -787 lines over 2 days (2026-04-28 → 2026-04-29)
**Source:** SEED-007 (Option A only — Wilson on score, 0.50 pivot, no user-baseline) + SEED-008 (label reframe). Both seeds folded into v1.14 and closed.

### What Was Built
- Score `(W + 0.5·D)/N` is the canonical metric across `opening_insights_service.py`, `openings_repository.py`, `arrowColor.ts`, and the `NextMoveEntry` / `OpeningInsightFinding` API payloads. `loss_rate` / `win_rate` removed cleanly. Effect-size gate against a 0.50 pivot with strict `≤`/`≥` boundaries — minor at 0.45/0.55, major at 0.40/0.60. Pivot stays at 0.50 (no user-baseline shrinkage; matchmaking + opponent-strength filter already center the baseline) (Phase 75)
- Trinomial Wald 95% confidence interval per finding using the actual variance of the chess result distribution `X ∈ {0, 0.5, 1}` — variance `(W + 0.25·D)/N − score²` rather than the binomial-Wilson approximation that over-states uncertainty when draws are common (standard formula in BayesElo / Ordo). Pure-Python `math` only, no scipy. Half-width buckets `≤ 0.10 → high`, `≤ 0.20 → medium`, else `low`. Pivoted from Wilson per Phase 75 D-05. `MIN_GAMES_PER_CANDIDATE` dropped 20 → 10 — confidence badge replaces hard-floor gate (Phase 75)
- `OpeningInsightFinding` payload extended with `confidence: "low" | "medium" | "high"` (the half-width bucket, user-facing badge) and `p_value: float` (two-sided Z-test of observed score vs 0.50, tooltip-grade). `severity` retained so the frontend renders effect size + precision + significance per finding. `NextMoveEntry` extended with the same three fields for moves-list parity (Phase 75 + 76-02)
- `arrowColor.ts` migrated to score (effect-size only — no confidence cue on arrows). Move Explorer moves-list row tint by score with extended mute rule `(game_count < 10 OR confidence === 'low')`. New Conf column with sort key `(confidence DESC, |score - 0.50| DESC)`. Single shared `compute_confidence_bucket` module with CI structural assertion that there's only one implementation (Phase 76)
- `OpeningFindingCard` renders score-based prose with level-specific confidence indicator and directional p-value tooltip; `UNRELIABLE_OPACITY` mute when `n_games < 10` OR `confidence === 'low'`. Four `InfoPopover` triggers added to `OpeningInsightsBlock` section headers. Mobile parity at 375px (Phase 76)
- INSIGHT-UI-04 (soften titles per SEED-008) descoped 2026-04-28 per Phase 76 D-04 — severity word never appeared as user-facing text; confidence badge + sort calibration deliver SEED-008's intent without rewriting "Weakness/Strength" titles
- Inline hotfix between Phase 76 and 77 (PR #71): force grey arrow + skip row tint when `confidence === 'low'`. Strengthens the at-a-glance board read; low-confidence findings still surface in the table with the badge but don't visually claim authority on the board
- Phase 77 troll-opening watermark — frontend-only matching via a side-only FEN piece-placement key (no backend schema, no Zobrist hash, no API contract change). `troll-face.svg` renders as 30%-opacity bottom-right watermark on `OpeningFindingCard` (mobile + desktop) and a small inline icon next to qualifying SAN rows in `MoveExplorer` (desktop only via `hidden sm:inline-block`). Curation is offline via a Node/TS script that emits per-ply candidates (both colors) for human pruning. Decorative `<img>` idiom keeps the asset cacheable and out of the accessibility tree (Phase 77)
- CI consistency test `test_opening_insights_arrow_consistency` rewritten to enforce score-based threshold lock-step between backend classification and `arrowColor.ts`
- Inline quick tasks during the milestone window: 260428-doc-framing-refresh, 260428-oxr (replaced Wald half-width buckets with p-value thresholds), 260428-tgg (sort by Wald CI bound), 260428-v9i (switched ranking from Wald to Wilson score interval bound), 260429-gmj (after-move arrow on insight finding mini board, PR #73)

### What Worked
- **Tightly-scoped milestone with one conceptual move.** v1.14 had a clear single thesis ("effect size decides what shows up, confidence annotates how sure we are") and shipped it in 2 days across 3 phases / 16 plans. The conceptual pivot was articulated in the design note before any code was written; every phase plan referenced it. Compact milestones with a clear thesis ship faster than ambitious milestones with mixed themes.
- **Decision IDs (D-XX) carried through context → plan → SUMMARY.** Phase 75 D-05 (trinomial Wald over Wilson) and D-09 (`p_value` alongside `confidence`) were debated at discuss-phase, recorded in `75-CONTEXT.md`, cited as the rationale for REQUIREMENTS amendments in Plan 75-04, and referenced in the Phase 75 SUMMARY. The chain from "why" to "what shipped" is unbroken and grep-able. Phase 76 D-03/D-04/D-17 followed the same chain.
- **Pivot during the milestone (Wilson → Wald, ranking iterations).** Originally specified Wilson half-width buckets per SEED-007 Option A; mid-Phase-75 discussion revealed Wilson over-states uncertainty when draws are common. Pivoted to trinomial Wald in `75-CONTEXT.md` D-05, with REQUIREMENTS amendment in Plan 75-04. The four post-Phase-76 quick tasks (260428-oxr/tgg/v9i + 260429-gmj) iterated on confidence buckets, sort key, and visual polish based on first-look-at-real-data feedback. Treating the metric as soft and iterable through the milestone window produced a calibrated end state that pre-locked metric specs would have over-constrained.
- **Frontend-only Phase 77 matching as a deliberate scope reduction.** Original troll-watermark design note specified backend Zobrist + TSV + frozenset — same shape as `seed_openings.py`. Switched to frontend-only matching via side-only FEN piece-placement keys at `77-CONTEXT.md` time after recognizing the small read-only nature of the curated set. Eliminated a migration, a backend service touch, an API contract change, and a CI parity test. Pure savings; no ergonomic loss.
- **CI structural assertions on shared helpers.** Both v1.14 phases shipped CI tests that catch *structural* violations beyond functional ones — `test_opening_insights_arrow_consistency` enforces backend/frontend threshold lock-step; the structural assertion on `compute_confidence_bucket` ensures only one implementation exists. Cheap to write; prevents the most common refactoring-induced drift class.
- **Inline mid-milestone hotfix (PR #71) was the right reach.** After Phase 76 shipped, the live UI showed low-confidence colored arrows still claiming visual authority on the board. Fixed inline via PR #71 (force grey + skip row tint) before opening Phase 77. Don't open a new phase for a polish-grade fix that's clearly load-bearing; don't queue for next milestone either; ship inline.
- **Phase 77 added off-roadmap-scope under v1.14, not as a hyphenated milestone.** Frontend-only follow-on with no v1.15 dependency; cheaper to ship under v1.14 than open v1.14.1.

### What Was Inefficient
- **Discuss-phase confidence-bucket math went through three pivots before settling.** Wilson (SEED-007) → Wald with half-width buckets (Phase 75 D-05) → p-value thresholds (post-Phase-76 quick task 260428-oxr) → Wilson score-interval bound for ranking only (260428-v9i). Each pivot required follow-on REQUIREMENTS/code adjustments. A 30-minute first-pass smoke against real user data during discuss-phase — sample 100 user-color pairs, compute candidate Wald/Wilson/p-value buckets, eyeball the rank order — would have surfaced the right calibration earlier. Lesson: when the milestone hinges on one statistical decision, smoke real data before locking the spec.
- **Phase 75 → 76 → 77 ran sequential when 75 + 76 had natural overlap.** Phase 75 (4 plans) and Phase 76 (8 plans) had natural overlap potential — frontend types, arrowColor.ts, helper module are pure additions atop the new constants module. Phase 76's first 3 plans are pure frontend type-shape catch-up that could have started in parallel with Phase 75. A two-track lane would have shaved a half day off the critical path.
- **No discuss-phase for Phase 77; design notes were rewritten mid-context.** Phase 77 jumped straight from "design notes in `notes/troll-openings-design.md`" to plans, then revised in `77-CONTEXT.md` ("backend Zobrist/TSV/frozenset approach is OUTDATED"). The original design note remains in tree as a misleading sibling. Future readers will hit the stale design note first.
- **133 quick-task entries without status frontmatter still showing as "open" in audits.** Carried forward from v1.10/v1.11/v1.12/v1.13 closes with the same disclaimer. Growing roughly +10/milestone. At some point this needs a one-shot script to backfill status frontmatter on the historical archive, or the audit's heuristic needs a bypass for entries with merged commits.

### Patterns Established
- **Effect size + confidence as separate UI cues.** Pioneered in v1.14: severity (effect size, color intensity) and confidence (precision, badge text + opacity mute) surfaced as orthogonal dimensions on the same finding. The user reads both at once. Reusable framing for any future ranked-discovery surface (LLM-narrated openings, endgame anomalies, rating-anomaly signals).
- **Trinomial Wald variance on chess scores, not binomial Wilson.** Future statistical work on FlawChess should default to trinomial Wald — chess is a 3-outcome game; the binomial approximation distorts the math when draws are non-trivial. `compute_confidence_bucket` is the canonical implementation.
- **Frontend-only matching for small read-only curated sets.** Phase 77 troll-opening matching established the pattern: side-only FEN piece-placement key, static data module, lookup once per render. Skips backend schema / API contract / migration / CI parity test. Use when the curated set is small (≤ 1000 entries), read-only, and doesn't need user-specific gating.
- **Decorative `<img>` watermark idiom.** Decorative `<img>` over CSS background — keeps the asset cacheable and lets browser handle scaling; `alt=""` + `aria-hidden="true"` + `pointer-events-none` keeps it out of the accessibility tree and doesn't block underlying interactivity.
- **CI structural assertion on shared helpers.** Beyond functional tests, assert *that there's only one implementation* of a cross-cutting helper. Cheap to write; prevents drift across refactors.
- **Mid-milestone hotfix PR.** When live-UI feedback reveals a polish-grade fix that's clearly load-bearing and not worth a new phase, ship inline. Pattern matches v1.13's quick-task hotfix loop.

### Key Lessons
1. **Smoke real data before locking statistical specs.** v1.14's three confidence-bucket pivots cost real REQUIREMENTS/code rewrites. A 30-min smoke on production-shape data during discuss-phase would have surfaced the right calibration first try.
2. **Compact milestones with one thesis ship faster than ambitious mixed-theme ones.** v1.14 (3 phases / 16 plans / 2 days, one conceptual move) compares favorably to v1.13's mixed scope.
3. **CI structural assertions complement functional tests.** Both Phase 75 and Phase 76 shipped CI tests that catch refactoring-induced *shape* violations, not just behavior bugs.
4. **Iteration via inline hotfixes / quick tasks is a feature.** PR #71 + four post-Phase-76 quick tasks iterated on the metric/sort/visual until the milestone felt right. Don't fight the iterative loop; structure for it.
5. **Off-roadmap-scope additions belong under the current milestone, not a hyphenated one.** Phase 77 folded into v1.14 directly rather than spawning v1.14.1.
6. **Stale design notes in tree are a future-reader trap.** Phase 77's pivot from backend to frontend matching left an outdated `notes/troll-openings-design.md` as a sibling. Either delete superseded design notes at decision time or annotate them with `> SUPERSEDED by <link>`.

### Cost Observations
- Sessions: ~7 conversations across the milestone window (discuss × 3 + plan × 3 + execute × 3 + verify × 3 + close × 1, with overlaps)
- Notable: Phase 76 ran an 8-plan parallel execute waveplan; Phase 77 ran a 4-plan / 2-wave execute. Parallel execution cut wall-clock by ~50% vs sequential.
- Sentry: zero new prod errors attributable to v1.14 changes through 2026-04-29 close. Score migration was clean.

---

## Milestone: v1.13 — Opening Insights

**Shipped:** 2026-04-27
**Phases:** 3 executed (70, 71, 71.1); Phases 72-74 descoped | **Plans:** 14 | **Delivered via:** PRs #66, #67, #68 (squash merges)
**Stats:** 106 files changed, +19,246 / -561 lines over 2 days (2026-04-26 → 2026-04-27)

### What Was Built
- Backend `opening_insights_service` with `POST /api/insights/openings` — single SQL transition aggregation per (user, color) over `game_positions` for entry plies in [3, 16]. LAG-window CTE on the new `ix_gp_user_game_ply (user_id, game_id, ply) INCLUDE (full_hash, move_san) WHERE ply BETWEEN 1 AND 17` partial composite covering index streams transitions as Index Only Scan with Heap Fetches: 0. `array_agg` window over rows BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING passes `entry_san_sequence` straight to the service — no extra roundtrip for FEN replay (Phase 70)
- Two-pass attribution: direct `query_openings_by_hashes` lookup on entry hashes; pass 2 batched query for parent-prefix hashes computed via `_compute_prefix_hashes()` with `ctypes.c_int64` signed-int64 conversion to match python-chess polyglot hashes (BLOCKER-2). Findings without direct or parent-lineage match are dropped, never surfaced as `<unnamed line>` placeholders. Sentry tag `openings.attribution.unmatched_dropped` captures drops for diagnosis (Phase 70)
- Strict `>` 0.55 win/loss boundary mirroring `frontend/src/lib/arrowColor.ts`; severity tier major (≥ 0.60) / minor in `(0.55, 0.60)`; CI test `test_opening_insights_arrow_consistency` enforces backend/frontend lock-step. `MIN_GAMES_PER_CANDIDATE = 20` evidence floor enforced at SQL HAVING level (Phase 70)
- Frontend `OpeningInsightsBlock` on Openings → Stats subtab with severity-accented `OpeningFindingCard` (DARK_RED / LIGHT_RED / DARK_GREEN / LIGHT_GREEN border, mirroring arrow colors), four-state rendering (loading skeleton, error, empty, populated), shared `LazyMiniBoard` thumbnail extracted from `GameCard` into `frontend/src/components/board/LazyMiniBoard.tsx` (Phase 71)
- Deep-link wiring — clicking a finding's Moves link replays `entry_san_sequence` through `chess.loadMoves()`, flips the board if `finding.color === 'black'`, applies the matching color filter with `matchSide: 'both'`, navigates to Move Explorer with the candidate row carrying a sticky severity tint + one-shot pulse from quick-task 260427-j41 (Phase 71)
- Openings page subnav layout refactor mid-milestone — desktop subnav lifted above `SidebarLayout` (mirrors Endgames pattern, `<Tabs>` wraps `<SidebarLayout>` so `TabsContent` context survives); mobile gains a sticky 4-tab subnav with filter button, board becomes non-sticky on Moves+Games and hidden on Stats+Insights, chevron-fold collapsible removed entirely; subtab switching resets scroll on both viewports (Phase 71.1)
- Pre-v1.13 quick task PRE-01 — dropped the parity filter from `query_top_openings_sql_wdl`, surfacing 1599 of 3301 white-defined ECO openings in the black top-10. Off-color rows now prefixed with `vs.` for clarity. Without this fix, the Phase 70 scan input would have been wrong from the start

### What Worked
- **Reuse-first phase planning.** Phase 70 plan structure was anchored on existing primitives (`apply_game_filters`, `query_top_openings_sql_wdl`, `game_positions` Zobrist hashes) and the v1.11 in-tab insights placement idiom. No new schema migrations on the analytics tables (only the new partial covering index). Made Phase 70 compact (5 plans) with low integration risk.
- **TDD with Wave 0 stubbed test scaffolding.** Phase 70 Plan 01 wrote failing tests against not-yet-existing services/routers using `pytest.importorskip` so the suite stayed collectable through Wave 1. Plans 02-05 each turned a wave green. The arrow-consistency CI test caught a frontend/backend threshold drift before merge.
- **Single SQL aggregation per (user, color), HAVING-side filtering.** Originally specified per-position recursion (D-15 redesign); collapsed to one transition CTE per color with HAVING enforcing both evidence floor and threshold at SQL level. No Python-side post-filter, no separate scan input. Latency stays under budget for typical users without precompute.
- **Mid-milestone Phase 71.1 insertion.** Frontend layout debt surfaced during Phase 71 UAT (Openings subnav diverged from Endgames subnav shape). Inserted Phase 71.1 to fix it in-milestone rather than carry the divergence into v1.14. Three plans, ~10 minutes wall-clock per plan, delivered in a half day. Cheaper than living with the inconsistency.
- **Mid-milestone scope-down on Phases 72/73/74.** After Phases 70+71+71.1 shipped (2026-04-27), spent time looking at the live UI: Move Explorer row tint already conveys the signal at the displayed position; per-finding cards already deliver per-opening actionable signal at finer granularity than an aggregate; bookmark-badge density risked alert fatigue. Descoping three planned phases on the day they would have started was the right call — a hypothetical "next milestone" planner who couldn't see the live UI couldn't have made it.
- **Quick-task hotfix loop kept v1.13 polished.** Six quick tasks landed during the milestone (PRE-01 + 260427-g4a..j41) — IllegalMoveError fix, whole-card-link → explicit-link split, candidate-move highlight, mobile link-placement adjustment, etc. Each was a sharp, atomic commit; the milestone shipped with no rough edges that real users would have hit immediately.

### What Was Inefficient
- **The v1.11 LLM stack went unused.** v1.13 deliberately kept LLM out of scope (templated/rule-based v1) but the `llm_logs` table, pydantic-ai Agent, and prompt-versioning machinery from v1.11 sat idle. Deferred is the right call (we don't yet know which findings are worth narrating), but the v1.11 retrospective's lesson — that LLM stack is a force multiplier — could have been weighed harder. Revisit in v1.13.x or v1.14 once real-user feedback identifies which findings are worth narrating.
- **`MIN_GAMES_PER_CANDIDATE` raised from n=10 (spec) to n=20 (D-15 redesign).** The original SEED-005 spec said n=10; live scanning at n=10 produced too many noisy "weakness" classifications on small samples (one bad week of blitz tilts a 0.55 loss-rate). The redesign to n=20 happened at Plan 70-04 / 70-05 time, requiring REQUIREMENTS / ROADMAP / CHANGELOG amendments (D-15/D-16/D-17). A small smoke at n=10 during discuss-phase would have surfaced the noise floor and saved the late amendments.
- **Whole-card touch target on `OpeningFindingCard` reverted twice.** Plan 71-04 specified the whole card as a single `<a href>` (D-22). Quick-task 260427-h3u then split this into explicit "Moves" + "Games" links because the whole-card target obscured which subtab opened. Live UX testing surfaced what the plan didn't anticipate. Pattern to watch: card-shaped UI with multiple potential destinations should default to explicit links from the start.
- **129 quick-task entries surfaced as "open" in pre-close audit.** Same as v1.12 — most are historical archive without status frontmatter. Audit tooling consistently misclassifies these. Should fix the audit query rather than re-acknowledge the same noise every milestone.

### Patterns Established
- **LAG-window transition CTE for chess-position scans.** When walking ply-ordered position sequences for a per-game property, use `func.lag(...).over(partition_by=game_id, order_by=ply)` plus a partial composite covering index aligned with the partition+order keys. Yields Index Only Scan with Heap Fetches: 0 at modest index size (~9% of table size with the right partial predicate).
- **`array_agg` window for trailing context.** When the consumer needs the prefix sequence (e.g., `entry_san_sequence` to replay the line), use `array_agg(...).over(partition_by=game_id, order_by=ply, rows=BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING)` so the prefix lives on the same row as the entry. Eliminates a second roundtrip and a service-layer assembly.
- **Two-pass attribution with drop-on-miss.** When mapping computed structural keys (Zobrist hashes here) to a canonical reference, do (a) direct lookup and (b) batched parent-prefix lookup; drop entries that match neither. Don't surface `<unnamed line>` placeholders — they pollute the UX and grow over time.
- **Strict `>` boundary lock-step with frontend, enforced by CI.** When backend classification thresholds need to match a frontend visual (arrow color, badge color), pin the constants and add a CI test asserting they're equal. Prevents the most common drift class.
- **First migration in the project to use `postgresql_concurrently=True` + `autocommit_block`.** Required for index creation on a write-heavy table (`game_positions`) without locking out import. Captured rationale inline so future autogenerate doesn't reorder the partition columns "for symmetry" with sibling indexes. Reuse for any future write-table indexes.
- **Severity tier as a visual axis.** Two-level tier (major / minor) maps cleanly to dark / light variants of the same hue family. Composes with semantic colors (red weakness / green strength) into a 4-cell color palette. Reuse for any classification UI with severity gradients.

### Key Lessons
- **Verify n-floor with a smoke before locking it in spec.** SEED-005 said n=10; live data said n=20. A 5-minute `psql` query against dev DB during discuss-phase would have surfaced the noise floor and avoided the late spec amendments. Pattern: any classification threshold that hinges on noise floor needs at least one sample-driven sanity check before the spec is final.
- **Look at the live UI before locking the rest of the milestone scope.** v1.13 originally had Phases 72-74 planned. After Phases 70+71+71.1 shipped, the live UI made it obvious that 72 (inline bullets) was redundant with the existing row tint; 73 (aggregate) was duplicative of per-finding cards at finer granularity; 74 (bookmark badge) risked alert fatigue. None of these were visible from the spec — they only became visible after Phase 71 was on screen. Pattern: **after a frontend phase ships, audit the rest of the milestone against the live UI before starting the next phase.**
- **Quick-task loop is part of the milestone, not separate.** Six quick tasks shipped during v1.13. Treating quick tasks as first-class milestone work (with proper commit messages, CHANGELOG entries, and STATE.md tracking) kept the milestone polished. Don't relegate quick tasks to a separate "polish phase" — fold them in continuously.
- **Whole-card link defaults are wrong when the card has multiple destinations.** Future card components with deep-linking should default to explicit child links unless there's exactly one navigation target.

### Cost Observations
- v1.13 spanned 2 days of focused work (2026-04-26 → 2026-04-27) — same wall-clock as v1.12.
- Sessions: ~6 main sessions (3 plan-execute, 1 discuss-phase, 1 quick-task batch, 1 milestone close).
- Notable: 14 plans across 3 phases delivered in 2 days — the most plans-per-day of any milestone since v1.0. Driven by reuse-heavy phase shape (Phase 70 stands almost entirely on existing primitives) and TDD-with-Wave-0-scaffolding compressing the integration cycle.
- Notable: mid-milestone scope-down on Phases 72/73/74 saved an estimated 1-2 days of follow-up work that would have been thrown away once the live UI was inspected.

---

## Milestone: v1.12 — Benchmark DB Infrastructure & Ingestion Pipeline

**Shipped:** 2026-04-26
**Phases:** 1 executed (69) | **Plans:** 6 (5 fully executed + 1 with descoped sub-tasks) | **Delivered via:** PR #65 (squash merge)
**Stats:** 98 files changed, +13,440 / -1,740 lines, 51 commits over 2 days

### What Was Built
- Isolated `flawchess-benchmark` PostgreSQL 18 instance on port 5433, deployed via `docker-compose.benchmark.yml` with read-only MCP role and `bin/benchmark_db.sh` lifecycle script. Same canonical Alembic chain as dev/prod/test (no schema fork) — Lichess `[%eval` annotations populate the existing `game_positions.eval_cp` / `eval_mate` columns (Phase 69-01)
- Third read-only MCP server `flawchess-benchmark-db` registered and documented in `CLAUDE.md` Database Access section (Phase 69-03)
- Eval-presence pre-filter via streaming `zgrep` over the Lichess monthly PGN dump — the ~85% of dump games without `[%eval` headers never reach python-chess; selection scan walltime drops by an order of magnitude (Phase 69-04)
- Stratified subsampling at the player-opportunity level on (rating_bucket × time_control). 5 rating buckets × 4 TCs, separate `WhiteElo` / `BlackElo` per side; 90M games scanned, 491k qualifying (K=10 eval-bearing-game floor), 8,628 distinct players persisted across 20 cells (17/20 cells hit the 500-user cap) (Phase 69-04)
- Resumable per-user checkpoint orchestrator with idempotent inserts via the existing `(platform, platform_game_id)` unique constraint, SIGINT + SIGKILL safety, in-flight users picked up first on resume (Phase 69-05)
- Smoke-test ingest at `--per-cell 3` ran end-to-end against the live Lichess API. 60 terminal rows: 56 completed, 3 over_20k_games skips, 1 unexplained failure (deferred to SEED-006); 274,143 games and 19.4M positions imported in 3h 6min (Phase 69-06)
- Verification report at `reports/benchmark-db-phase69-verification-2026-04-26.md` covering all four Dimension-8 evidence sections plus storage budget projection (~205 GB at full `--per-cell 100` ingest, flagged for SEED-006 disk sizing) (Phase 69-06)

### What Worked
- **Mid-milestone scope-down was the right call.** Originally Phases 69-73; the realization (2026-04-26, 2 days before close) that the full benchmark ingest is days of wall-clock ops work, not a milestone gate, freed up v1.13 work and let v1.12 ship on a clean pipeline-correctness criterion. Treating ops work as a milestone gate was actively blocking unrelated planning.
- **Smoke-vs-spec catches design slips that discuss-phase can't.** The `eval_depth` + `eval_source_version` columns looked correct in plan 69-02 + decision context (D-12 etc.) — both assumed the Lichess API surfaces depth metadata. The smoke output proved otherwise immediately. Hot-patching the columns out (one Alembic migration, 5 source files) was lighter than running a corrective phase.
- **Player-opportunity bucketing on separate `WhiteElo`/`BlackElo`.** Each side independently classified into its own rating cell, never aggregated by a game-level rating field. Caught early in `/gsd-discuss-phase` (D-10/D-11), saved a structural rework downstream.
- **Per-user checkpoint table over byte-offset checkpoint.** Idempotent inserts on `(platform, platform_game_id)` made resumability trivial; SIGKILL during a batch leaves the user as `pending` and the resume logic picks it up first. Zero application-layer dedup needed.
- **`zgrep` eval pre-filter as the first stage.** Most of the Lichess dump (~85% of games) lacks `[%eval` headers entirely; pre-filtering at the text layer before python-chess sees the game cut selection-scan time from "overnight" to "morning coffee."
- **Phase 69 not split into 69 + 69.1.** Infrastructure (INFRA-01..03) and ingestion pipeline (INGEST-01..06) are tightly coupled (eval pre-filter presupposes schema decision; resumability checkpoint lives in the benchmark DB itself). Splitting would have forced a fake handoff.

### What Was Inefficient
- **Two add-then-drop columns inside the same milestone.** `games.eval_depth` and `games.eval_source_version` were added in plan 69-02 (migration `b11018499e4f`) and dropped in `6809b7c79eb3` after the smoke. The discuss-phase context (D-12) assumed Lichess API PGN includes depth like the dump exports do — it doesn't. A 5-minute `curl` against the API during discuss-phase would have prevented both the migration and the hot-patch. Lesson: **verify external API output with a sample before specifying schema**, especially when the source has multiple export channels (dump vs API).
- **Original v1.12 scope was overpacked.** 5 phases bundling infrastructure (1 phase) with applied analytics (4 phases) on a milestone whose hard dependency between halves is "the DB is fully populated" — a multi-day operational step. Should have split into v1.12 (infra + smoke) and a future milestone (analytics) at planning time, not 2 days before close.
- **Storage projection blew past INGEST-05's 50-100 GB target by 2x at modest `--per-cell 100`.** The original storage target was based on a per-endgame-type sample-unit before the 2026-04-25 pivot to per-cell distinct users (D-12). Should have re-derived storage at pivot time.

### Patterns Established
- **Verification-from-smoke.** Pipeline-correctness evidence comes from a small smoke run (e.g., `--per-cell 3`) rather than blocking on a full operational run. Document evidence in a per-phase verification report under `reports/`. Use this whenever the "real" run is operationally heavy and the smoke captures the same correctness invariants.
- **Hot-patch-mid-plan over corrective phase.** When a smoke run reveals a small surgical schema issue, hot-patch via Alembic + small source-file edits rather than spawning a corrective phase. Threshold: if the patch fits in <10 files and one migration, hot-patch; otherwise, plan a phase.
- **Streaming text pre-filter before structural parsing.** When ingesting from large external dumps with mixed-quality content, layer a streaming text filter (`zgrep`, ripgrep, etc.) before the heavy parser to drop unqualified rows early.
- **Ops tables via `create_all()` against the secondary engine.** When a benchmark/ops DB needs auxiliary tables that have no place in the canonical analytical schema (here: `benchmark_selected_users`, `benchmark_ingest_checkpoints`), create them via `Base.metadata.create_all()` against the secondary engine on first invocation. Don't pollute the canonical Alembic chain.
- **Same Alembic chain across dev/prod/test/benchmark.** Resist the temptation to fork the schema for the benchmark DB — keep one canonical chain and let the analytical columns serve both prod analysis and benchmark analysis.

### Key Lessons
- **Verify external API output with a sample before specifying schema.** Documentation about "depth available in PGN" was true for Lichess **dump** exports and false for **API** exports. A 5-minute sampling during discuss-phase would have saved one migration round-trip.
- **Operational steps don't belong in milestone gates.** Multi-day wall-clock work that doesn't change source code (population ingest, large data backfills) should live as ops scripts with their own SOPs, not as a phase a downstream milestone is gated on.
- **Plan smoke + ops as separate artifacts.** A smoke test proves correctness; the full-scale run is a separate operational task. Don't bundle them.

### Cost Observations
- Phase 69 spanned 2 days of focused work (2026-04-24 → 2026-04-26) plus the 3h 6min smoke wall-clock and ~3h discuss-phase context-gathering on 2026-04-25.
- Sessions: ~5 main sessions (4 plan-execute, 1 discuss + 1 close).
- Notable: the scope-down on 2026-04-26 happened mid-milestone via `/gsd-remove-phase` and a roadmap update. Keeping the deferred work in SEED-006 (rather than backlog or out-of-scope) preserved the design rationale for whenever the full ingest does run.

---

## Milestone: v1.11 — LLM-first Endgame Insights

**Shipped:** 2026-04-24
**Phases:** 5 executed (63, 64, 65, 66, 68); Phase 67 descoped | **Plans:** 23 | **Delivered via:** PR #61 (squash merge)

### What Was Built
- First LLM-backed feature in the codebase: `POST /api/insights/endgame` returning a structured `EndgameInsightsReport` (overview + up to 4 Section insights) via a pydantic-ai Agent, cached on findings_hash, rate-limited 3 misses/hr/user, soft-failing to last cached report (Phase 65)
- Deterministic findings pipeline: `compute_findings` transforms `/api/endgames/overview` into per-subsection-per-window `EndgameTabFindings` with zone/trend/sample-quality annotations + three cross-section flags, so the LLM reasons over pre-validated numbers (Phase 63)
- Shared zone registry (`app/services/endgame_zones.py`) as single source of truth; Python→TypeScript codegen script + CI drift guard prevents narrative-vs-chart drift by construction (Phase 63)
- Generic `llm_logs` table (18 cols, BigInteger PK, JSONB, FK CASCADE, 5 indexes including 3 composites with `created_at DESC`) designed up-front for every future LLM feature; async repo with `genai-prices` per-call cost accounting and `cost_unknown:<model>` soft-fallback (Phase 64)
- Frontend `EndgameInsightsBlock` with parent-lifted mutation state (no Context) — `Endgames.tsx` holds one `useEndgameInsights` mutation; the block + 4 `SectionInsightSlot` instances all observe the same state; inline per-section slot placement achieves H2-ride-along suppression for free (Phase 66)
- Dual-line "Endgame vs Non-Endgame Score over Time" chart with colored shaded gap replaces single-line Score Gap chart; prompt simplified (bumped to endgame_v14) since the chart makes gap composition self-evident (Phase 68)

### What Worked
- **Prompt versioning as the cache-invalidation handle** — bumping `_PROMPT_VERSION` (v6→v15 over the milestone) forced fresh generation without explicit cache flush. Iteration was cheap and auditable via git blame on the prompt file.
- **Zone registry + CI drift guard** — Python-side authoritative constants with a codegen'd TS mirror caught divergence at PR time, not at user-report time. Worth the upfront scaffolding.
- **Parent-lifted mutation state in Endgames.tsx** — avoided a Context provider; 4 slot instances observing the same mutation result was simpler than expected and cleanly survived H2-group re-renders.
- **Generic `llm_logs` over feature-specific** — designing the table up-front for every future LLM feature meant Phase 66 UI + later Insights expansion (Openings/Global Stats) require zero schema changes.
- **Pre-merge v1.11 milestone review by gsd-code-reviewer** — caught a critical failing test, a dead codegen pipeline (Phase 66 half-finished switchover), a stale prompt reference, and a stale CHANGELOG entry. Worth doing before every squash.
- **Quick-task loops for UAT feedback** — 260422-tnb, 260423-a4a, 260424-pc6 quick tasks iterated the prompt/schema without spawning new phases. Right tool for small-but-visible refinements.

### What Was Inefficient
- **Phase 67 descope was implicit, not planned** — insights were enabled for all users via commit `c91478e` without updating the roadmap or requirements. Result: VAL-01 and VAL-02 remained formally unchecked with no explicit tech-debt entry until milestone close. The plan-deviation should have been logged as a roadmap update at decision time.
- **Prompt revision churn inside the milestone** — v6→v15 across phases + multiple UAT quick tasks + a final cleanup pass bump (v15) suggests the initial prompt underspecified what the LLM needed to see. A spike might have paid for itself.
- **Two add-then-drop migrations in the same milestone** (`system_prompt`, `flags` columns) — both columns shipped in Phase 64 and were dropped within days. Decision-by-implementation rather than decision-by-design.
- **UAT artifacts are inconsistent** — Phase 68 HUMAN-UAT.md has 5 pending scenarios at close; Phase 66 VERIFICATION.md is `human_needed`. The `/gsd-verify-work` loop wasn't closed before merge.
- **Stale requirement checkboxes** — LOG-02/LOG-04 were implemented in Phase 65 but left unchecked in REQUIREMENTS.md traceability until milestone close. Phase summaries didn't include "requirements-checkbox-updated" in their definition-of-done.
- **Pre-existing ORM/DB column drift** (REAL→Float on 3 columns) surfaces on every Alembic autogenerate and was manually stripped from 3 v1.11 migrations. Deserves a dedicated cleanup migration, not ongoing handraising.

### Patterns Established
- **Prompt-as-file + prompt_version cache key** — all future LLM features should load system prompts from versioned files and include `prompt_version` in the cache key. Never string-literal prompts in `.py`.
- **One generic log table per LLM feature class** — `llm_logs` hosts every Agent call; `endpoint` column distinguishes consumers. New LLM features don't require new tables.
- **Environment-variable-driven model selection** — use `PYDANTIC_AI_MODEL_<FEATURE>` with startup validation (fail-fast on missing/invalid). Swap models for A/B without code changes.
- **Findings-hash cache + soft-fail rate limit** — 3 misses/hr/user with fallback to last cached report is the pattern for any user-triggered LLM endpoint.
- **Python-side registry with codegen'd TS mirror + CI drift guard** — every semantic constant shared between backend and frontend (zone thresholds, metric IDs, enum values) follows this pattern.
- **Parent-lifted mutation state for multi-slot LLM renderers** — when an LLM result feeds multiple visual slots on one page, hold the mutation in the parent and pass the result down as props rather than using Context.

### Key Lessons
- **Plan-deviations deserve an explicit roadmap update at the moment of the decision, not at milestone close.** Phase 67 was skipped in practice weeks before it was documented as skipped.
- **Every new LLM feature must ship with at least one snapshot regression test** — even if it's a single real-user fixture. Phase 67 was the guard that didn't happen; v1.12 should retrofit one.
- **Zone/threshold constants have exactly one authoritative home — enforced by CI.** The v1.11 consolidation pass retired four-way restatement (Python + codegen'd TS + throwaway regex test + 3 inline FE const blocks) down to one codegen'd source.
- **Pre-merge cohesion reviews catch things phase-level review misses** — files shipped but never imported, docstring-vs-code mismatches, CHANGELOG written before the final pivot. Worth running before every milestone squash.

### Cost Observations
- Prompt iteration (v6→v15) dominated API-cost variance; caching on findings_hash + prompt_version meant repeated testing at stable findings cost near-zero.
- Thinking tokens: diagnosed `thinking_tokens=NULL` as a `GEMINI_THINKING_LEVEL=low` config choice (quick task 260423-a4a), not a code bug.

---

## Milestone: v1.10 — Advanced Analytics

**Shipped:** 2026-04-19
**Phases:** 11 (48, 52-55, 57, 57.1, 59-62; Phase 56 cancelled, 58 moved to backlog) | **Plans:** 28 | **Delivered via:** PRs #38, #43, #47, #49, #50, #51, #52

### What Was Built
- Consolidated `/api/endgames/overview` endpoint serving every endgame chart in one round trip; 2-query timeline (GROUP BY game_id+endgame_class with HAVING count(ply)>=6) replaces 8 sequential per-class queries; pg_stat_statements top-offender dropped from 150-500s to sub-second (Phase 52)
- Endgame Score Gap & Material Breakdown: signed endgame-minus-non-endgame score plus 3-row bucket table (Ahead/Equal/Behind → later renamed Conversion/Parity/Recovery) with Good/OK/Bad verdicts calibrated against overall score (Phases 53, 59)
- Opponent-based self-calibrating baseline for Conv/Parity/Recov bullet charts — opponent's rate against the user (respecting all filters) replaces global-average, muted when opponent sample < 10 games (Phase 60)
- Time pressure analytics: per-time-control clock stats table with Games/My-avg/Opp-avg/Clock-diff/Net-timeout columns (Phase 54); two-line user-vs-opponents score chart across 10 time-remaining buckets per TC (Phase 55)
- Endgame ELO Timeline: skill-adjusted rating per (platform, time-control) combo paired with actual rating, asof-join anchor per combo, weekly volume bars for data-weight transparency, info popover framing it as skill-adjusted rather than performance rating (Phases 57 + 57.1)
- Conv/recov persistence filter: material imbalance required at entry AND 4 plies later, threshold 300cp → 100cp for a larger, less noisy dataset (Phase 48)
- Test suite hardening: `flawchess_test` TRUNCATE on session start, deterministic `seeded_user` module-scoped fixture, aggregation sanity tests (WDL perspective when user plays black, material tally direction on captures, rolling-window boundaries, platform × TC filter intersection, recency cutoff, within-game dedup, endgame transitions), router integration tests with exact integer assertions (Phase 61)
- Admin user impersonation: shadcn Command+Popover user search, POST /admin/impersonate, single auth_backend with ClaimAwareJWTStrategy wrapper preserving every `Depends(current_active_user)` call site, impersonation pill in header (desktop + mobile), last_login/last_activity frozen during impersonation, nested impersonation rejected via current_superuser dep (Phase 62)

### What Worked
- Consolidated overview endpoint + deferred desktop filter apply (matching mobile) solved the prod perf crisis cleanly — one response model, one hook, one round trip
- Single-pass `GROUP BY (game_id, endgame_class)` with Python-side dedup was both faster and simpler than UNION ALL — exploits existing `ix_gp_user_endgame_game` index
- Asof-join anchor on user's real rating (via `bisect_right` per combo) fixed the "Actual ELO as rolling mean confuses users" UAT feedback with one backend change — frontend just swapped to the new field
- ClaimAwareJWTStrategy wrapper pattern kept Phase 62 invisible to every existing auth dep — zero changes at call sites, impersonation enabled entirely in the strategy + admin routes
- Splitting Phase 57 (initial chart) from Phase 57.1 (UAT-driven polish) was the right call — clean history, clear rationale for each change, and Phase 57.1 could reference UAT evidence explicitly
- Seeded_user module-scoped fixture → deterministic integer assertions → router integration tests could be written against *known* numbers rather than shape-only — caught two genuine bugs worth follow-up phases
- Mid-milestone rename to Conversion/Parity/Recovery (via quick tasks 260413-pwv + 260415-q75) was done in small text-only passes rather than a big-bang rename commit — kept git history readable

### What Was Inefficient
- Two naming storms on material buckets (ahead/equal/behind → conversion/even/recovery → conversion/parity/recovery) forced three passes across backend schemas, Pydantic literals, frontend copy, and info popovers — should have nailed terminology in the Phase 53 discuss-phase
- Phase 60-02 and all of Phase 61 have no SUMMARY.md files despite being complete — artifact hygiene gap that makes retroactive extraction harder
- Phase 57 inlined `_endgame_skill_from_bucket_rows` in `endgame_service.py` as a port of the frontend `endgameSkill()` with a TODO to dedup when Phase 56's backend `endgame_skill()` landed — Phase 56 was later cancelled, making the TODO orphaned
- Time pressure analytics required three follow-up quick tasks (260414-u88 aggregate TCs, 260414-pv4 fix whole-game rule, 260416-pkx backend aggregation) before settling — the initial plan underspecified the aggregation layer
- Phase 52's `52-03` prod verification plan was deferred (validated informally post-deploy) — missed the discipline of explicit pg_stat_statements before/after capture
- Phase 48 phase directory appears to have been cleaned from .planning/phases before archive — archive built from roadmap content alone, not from phase artifacts

### Patterns Established
- **One consolidated overview endpoint per tab** — for pages with >3 charts sharing the same filter set, consolidate server-side on one AsyncSession rather than fanning out; use one TanStack Query hook on the frontend
- **Deferred filter apply on desktop matching mobile** — for filter sidebars that can push many filter changes, apply on sidebar close, not on every change; avoids query storm and reduces user confusion
- **Weekly volume bars on timeline charts** — every new timeline chart (Endgame ELO, Clock Diff, Score Diff, Win Rate by Endgame Type) now renders a muted bar series showing per-week games; gives users a weight signal at every point
- **Asof-join for per-combo anchors** — when a timeline needs to anchor on a slowly-changing value (user's rating per platform+TC), pre-sort rows by date and `bisect_right` per emitted date instead of a rolling mean
- **ClaimAwareJWTStrategy wrapper** — feature-flag auth variants (impersonation, future: team membership, SSO claims) behind a strategy wrapper around the base JWTStrategy; keeps every existing `Depends(current_active_user)` call site unchanged
- **Seeded portfolio + router integration tests** — for aggregation-heavy endpoints, a module-scoped fixture with a known ~15-game portfolio (black/white/bullet/blitz/rapid/classical/chess.com/lichess/wins/draws/losses) enables "known seed → known numbers" integration tests
- **TRUNCATE on pytest session start** — deterministic DB state, no flaky accumulation, old runs remain inspectable until next session

### Key Lessons
1. **Nail semantic naming in discuss-phase.** Material buckets went through three rename passes mid-milestone (ahead/equal/behind → conversion/even/recovery → conversion/parity/recovery). Each rename touched backend schemas, Pydantic literals, frontend copy, info popovers, and tests. A 15-minute terminology check in the Phase 53 discuss-phase would have saved ~2 hours of rename churn.
2. **Summary hygiene slips when momentum is high.** Phases 60-02 and all of Phase 61 have no SUMMARY.md. Neither blocks shipping, but retroactive archive extraction is harder and post-mortem learnings are thinner. Consider a git hook or pre-PR check that blocks merge without a SUMMARY.md per plan.
3. **UAT catches what the planner misses.** Phase 57's "rolling-mean Actual ELO" shipped reviewer-approved and verifier-passed, yet was visibly wrong to the user on first interaction. The asof-join fix (Phase 57.1) is a clean demonstration of why UAT is worth the extra phase — and why 57.1 as a separate decimal phase beat a late revision to 57.
4. **Consolidate read paths ruthlessly.** The v1.10 perf crisis came from frontend fan-out — 4 parallel requests × 8-per-class queries each. A single response model + single session + single hook fixed it. Every multi-chart page should start with that shape.
5. **Performance measurements need before/after discipline.** Phase 52's success criterion (9) mentioned pg_stat_statements verification but plan 52-03 was deferred and done "informally." For production perf work, capture the metric explicitly before merging — otherwise post-hoc "feels faster" replaces real evidence.
6. **Phase cancellation and backlog promotion are first-class moves.** Retiring Phase 56 (subsumed by 57) and bumping Phase 58 to backlog (999.6) via one small quick task kept v1.10 focused and honest. Don't force scope to match a pre-written roadmap when the work itself tells you the shape has shifted.

### Cost Observations
- 11 phases, 28 plans, 124 commits across ~12 days (2026-04-07 → 2026-04-19)
- 249 files changed, +54835 / -1852 lines (includes generated artifacts, theme screenshots, and planning docs)
- ~20 quick tasks landed on top of phases for iterative polish (mostly styling, renaming, chart tweaks) — quick tasks worked well as "the code is right, the copy/layout needs a pass" vehicles
- Decimal phase (57.1) was the right structure for UAT-driven scope expansion — separate plan files, separate commit, clear rationale
- Phase 62 (5 plans) was the largest; Phases 48, 53-55, 57, 57.1, 60 were each 2 plans — 2-plan is the median unit for a frontend+backend feature on this project

---

## Milestone: v1.9 — UI/UX Restructuring

**Shipped:** 2026-04-10
**Phases:** 3 (49-51) | **Plans:** 7 | **Delivered via:** PRs #40, #41, #42

### What Was Built
- Openings desktop sidebar: collapsible 48px icon strip + 280px on-demand Filters/Bookmarks panel with overlay/push behavior at the 1280px breakpoint, plus a shared SidebarLayout component used by both Openings and Global Stats
- Openings mobile unified control row: Tabs | Color | Bookmark | Filter lifted outside the board collapse grid so controls stay visible when the board is collapsed; 5-item vertical board-action column with 48×48 touch targets; 44px tappable collapse handle; backdrop-blur sticky surface
- Endgames mobile visual alignment: 44px backdrop-blur sticky row with 44px filter button matching the Openings mobile pattern (EGAM-01)
- Global Stats filters wired end-to-end: `opponent_type` + `opponent_strength` through `/stats/global` and `/stats/rating-history` plus the React hooks/API client layer; bot games now excluded by default
- Stats subtab 2-col layout: explicit leftRows/rightRows grid split for Bookmarked Results at the lg breakpoint; new `MobileMostPlayedRows` component for stacked WDLChartRows on mobile
- Homepage 2-column desktop hero: left hero content + right Interactive Opening Explorer preview (heading + screenshot + bullets); pills row removed; Opening Explorer removed from FEATURES list
- Global Stats rename: "Stats" → "Global Stats" across desktop nav, mobile bottom bar, More drawer, mobile page header, plus new page h1 — all driven via existing label-to-testid auto-derivation so testids updated with zero manual edits

### What Worked
- Label-to-testid auto-derivation meant the "Stats" → "Global Stats" rename needed only 3 label string swaps in `App.tsx`; all nav testids, mobile header title, and More drawer entries updated automatically
- Explicit `leftRows`/`rightRows` array split beat CSS `columns-2` for the 2-col Bookmarked Results — deterministic odd-count behavior, no `break-inside` edge cases
- Unified mobile control row lifted outside the board collapse region (D-03) solved the "controls disappear when board collapsed" problem cleanly — one structural change, no prop plumbing
- Shared SidebarLayout component emerged organically from Phase 49 and was immediately reusable for Phase 51-04's Global Stats FilterPanel placement
- Plan 51-01 wiring opponent filters first, Plan 51-04 enabling the UI controls second — kept each plan small and let the end-to-end path come online in two independent commits
- Static 2-col homepage hero (not a carousel) — simpler, no JS state, preserves scroll-free visibility on a 1280px viewport

### What Was Inefficient
- `gsd-tools milestone complete` hard-coded "Phases completed: 4 phases" and copied the full ROADMAP.md verbatim into the v1.9 archive — required manual rewrite of the archive file plus MILESTONES.md entry
- `summary-extract --fields one_liner` returned null or "One-liner:" for 5 of 7 summary files because the summaries use an H2 heading format rather than the YAML field the CLI expects — accomplishments had to be re-extracted by hand
- ROADMAP.md left `[ ] 51-04-PLAN.md` unchecked even after the phase shipped (PR #42 merged) — post-ship state drift between the roadmap checkbox and the actual commit/summary state
- Worktree Plan 51-04 execution started from the wrong HEAD (`45c5b80` instead of `f77dbf3`) and required a `git reset --soft` + `git checkout HEAD -- .` to recover — worktree initialization edge case worth investigating in `gsd-tools`

### Patterns Established
- **Label-driven testid derivation** — keep `NAV_ITEMS[].label` as the single source of truth and derive testids via `label.toLowerCase().replace(/\s+/g, '-')`; renames cost one label edit
- **Unified control row outside collapse region** — when a collapsible section hides controls needed for navigation (like subtabs), lift them into a sibling of the collapse grid rather than inside it
- **Grid-column push/overlay breakpoint** — at 1280px, the Openings sidebar switches from overlay (for ≤1279px) to push (for ≥1280px); this is now the project's reference breakpoint for sidebar-plus-board layouts
- **Shared SidebarLayout component** — any future page that needs a collapsible left strip with Filters should consume SidebarLayout rather than reimplementing
- **Viewport branch at call site, not via prop** — when desktop and mobile need different variants of a component, branch at the page (`hidden md:block` / `md:hidden`) rather than adding a `mobileMode` prop; keeps the desktop component byte-identical and zero-risk

### Key Lessons
1. **CLI milestone archival is a first draft, not a final document.** `gsd-tools milestone complete` creates skeletal archive files and a MILESTONES.md stub, but the accomplishments list, phase count, and archive structure need human cleanup for every milestone — budget 10-15 minutes for the rewrite
2. **Summary extraction depends on file format discipline.** If summaries use H2 `## One-liner` headings instead of YAML frontmatter fields, the extractor returns null. Either standardize on one format or the tooling needs to fall back between both
3. **Post-ship checkbox drift is the norm unless explicitly maintained.** When a PR merges, the ROADMAP plan checkboxes don't auto-update — the next milestone completion pass must reconcile them or add a tooling gate
4. **Mobile-first visual-alignment passes are cheap once a pattern exists.** Phase 50-02 (Endgames visual alignment) was 3 classname swaps + 1 testid — ~10 minutes because Phase 50-01 had already established the `h-11 bg-background/80 backdrop-blur-md` pattern
5. **The "apply to mobile too" CLAUDE.md rule is load-bearing.** Phase 51-04's FilterPanel visibleFilters change updated both the desktop SidebarLayout and the mobile Drawer instances — missing one would have silently diverged the two viewports

### Cost Observations
- 3 phases, 7 plans, ~21-hour execution window end-to-end (2026-04-09 21:42 → 2026-04-10 18:43)
- 57 files changed, +8692 / -1602 lines
- Each phase was delivered in its own PR (#40, #41, #42) with squash merge — clean main history, easy rollback granularity
- Plans stayed small: median 1 plan per phase for 49, 2 for 50, 4 for 51 — the 4-plan split on Phase 51 was the right call because the 4 concerns (opponent filter wiring, stats layout, homepage hero, Global Stats rename) had distinct code surfaces and minimal coupling

---

## Milestone: v1.8 — Guest Access

**Shipped:** 2026-04-06
**Phases:** 4 | **Delivered via:** PR #37

### What Was Built
- Guest session foundation: is_guest User model flag, JWT-based guest sessions with 30-day auto-refresh, IP rate limiting
- Guest frontend: "Use as Guest" buttons on homepage and auth page, persistent guest banner
- Email/password promotion: backend promotion service, register-page promotion flow preserving all imported data
- Google SSO promotion: OAuth promotion route with guest identity preservation across redirect, email collision handling
- Security: CVE-2025-68481 Google OAuth CSRF vulnerability patched with double-submit cookie validation
- UX polish: import page guest guard, auth page logo linking, delete button disabled during active imports

### What Worked
- Guest as first-class User row (is_guest=True) — promotion is a single UPDATE, no FK migration needed
- Bearer transport for guest JWTs — avoided dual-transport complexity entirely
- Register-page promotion instead of separate modal — reused existing form, cleaner UX, less code
- PR-based workflow (feature branch → squash merge) kept main clean during multi-phase development

### What Was Inefficient
- Entire milestone developed outside GSD discuss→plan→execute workflow — no SUMMARY.md, VERIFICATION.md, or PLAN.md files exist for phases 44-47
- GSD state tracking stayed at 0% despite all work being complete — planning artifacts diverged from actual progress
- Quick tasks (UI polish commits between roadmap creation and PR merge) weren't tracked in any GSD artifact

### Patterns Established
- Guest user pattern: is_guest flag on User model, synthetic email (`@guest.local`), promotion via in-place UPDATE
- OAuth CSRF protection: double-submit cookie pattern for all OAuth callbacks
- Import guard: disable destructive actions (delete) while import is running

### Key Lessons
1. When developing outside GSD's formal workflow (e.g., rapid feature branch work), the planning artifacts become stale immediately — either commit to the workflow or accept the tracking gap
2. Guest-as-User-row is much simpler than a separate guest model — promotion is trivial, no FK migration, no special-casing in queries
3. Register-page promotion beats a dedicated modal — reuses existing validation, error handling, and styling

---

## Milestone: v1.3 — Project Launch

**Shipped:** 2026-03-22
**Phases:** 4 | **Plans:** 10

### What Was Built
- Full rebrand from Chessalytics to FlawChess (20 files, PWA manifest, logo, GitHub org transfer)
- Docker Compose production stack: multi-stage Dockerfiles, Caddy auto-TLS, entrypoint with auto-migrations
- Deployed to Hetzner VPS (CX32, 2 vCPUs, 3.7GB RAM) at flawchess.com
- GitHub Actions CI/CD: test + lint + SSH deploy + health check polling
- Sentry error monitoring on both FastAPI backend and React frontend
- Public homepage with feature sections, FAQ, register/login CTA
- SEO fundamentals: meta tags, Open Graph, robots.txt, sitemap.xml
- Privacy policy page at /privacy
- Per-platform rate limiter (asyncio.Semaphore) for chess.com/lichess import protection
- Professional README with screenshots and self-hosting instructions
- 14 quick tasks: lichess import fix, arrow sorting, tooltip→popover, mobile UX, board controls, tab renaming, filter heights, bookmarks, /api prefix, brown theme, new-user routing, README, time control fix, WDL bar fix

### What Worked
- Deployment-first ordering (Phase 21 before 22/23) meant CI/CD and launch readiness could be tested against the live server
- Cloud-init + Docker Compose gave a reproducible single-command server setup
- Caddy as sole internet-facing entry point simplified TLS and routing (no nginx config)
- asyncio.Semaphore for rate limiting avoided adding Redis/Celery infrastructure
- Quick tasks handled all post-launch polish (14 tasks) without disrupting phase work
- Swap file added reactively when PostgreSQL OOM-killed during large import — proactive monitoring would have been better

### What Was Inefficient
- Plan 21-02 (cloud-init cleanup + deploy checkpoint) was never formally executed — deployment happened organically during 21-01 and manual setup. Skipped at milestone completion.
- Some SUMMARY.md files have poor/missing one_liner frontmatter fields — summary-extract continues to return null
- Phase 22 plan checkboxes in ROADMAP.md were never updated to [x] despite being complete — bookkeeping drift from manual execution
- OOM kill on production required emergency swap file and batch size reduction — should have configured swap in cloud-init from the start

### Patterns Established
- `ENVIRONMENT` env var controlling CORS (disabled in production, enabled in dev)
- Backend `expose` only in docker-compose.yml (no `ports`) — Caddy proxies all traffic
- Sentry DSN injected at Docker build time via `ARG`/`ENV` for frontend bundle
- `_BATCH_SIZE = 10` for import to prevent OOM on constrained servers
- asyncio.Semaphore lazy-init pattern to avoid event loop not started error

### Key Lessons
1. Production memory constraints matter — 3.7GB RAM with PostgreSQL + FastAPI + Caddy is tight; swap is essential from day one
2. Human verification checkpoints (deploy steps) don't fit well into automated execution — they should be separate milestone gates, not plans
3. Caddy is excellent for small deployments — auto-TLS, reverse proxy, static file serving in one config
4. Rate limiter design should match the bottleneck — per-platform semaphore is simpler than global queue for chess.com/lichess with different rate limits

---

## Milestone: v1.2 — Mobile & PWA

**Shipped:** 2026-03-21
**Phases:** 3 | **Plans:** 5

### What Was Built
- PWA with service worker, chess-themed icons, Workbox caching (NetworkOnly for API)
- Mobile bottom navigation bar with direct tabs + "More" drawer (vaul-based)
- Click-to-move chessboard on touch devices with sticky board on Openings page
- 44px touch targets on all interactive elements, overflow fixes at 375px
- Android/iOS in-app install prompts (beforeinstallprompt + manual iOS banner)
- Dev workflow: LAN hosting + Cloudflare Tunnel for HTTPS phone testing
- 7 quick tasks: lichess import fix, arrow sorting, tooltip→popover, mobile card layouts, board controls reorder, tab renaming, filter height consistency

### What Worked
- Frontend-only milestone scope (no backend/API changes) kept complexity low and iteration fast
- Pure Tailwind `sm:` breakpoints for mobile/desktop switching — no JS detection needed
- vaul library for drawer component — handled scroll lock, backdrop, iOS momentum out of the box
- Quick tasks handled all polish (tab renaming, button heights, card layouts) without phase overhead
- Duplicating mobile Openings layout (vs trying to make one layout responsive) avoided fighting sticky positioning

### What Was Inefficient
- react-chessboard drag-and-drop caused persistent black screen on mobile — spent multiple iterations trying to fix before disabling drag entirely
- Touch target sizing required understanding CSS specificity interactions between component libraries (shadcn's data-attribute selectors) and custom classes — `min-h-11` vs `h-11` vs `h-11!` depending on component
- summary-extract CLI still returns null for one_liner — SUMMARY.md files lack the expected frontmatter field

### Patterns Established
- `min-h-11 sm:min-h-0` pattern for ToggleGroupItem/SelectTrigger mobile touch targets (min-height overrides component's fixed height)
- `h-11 sm:h-7` for custom buttons to match ToggleGroup/Select heights exactly
- `h-11!` (Tailwind important) when overriding data-attribute-based component styles (e.g., TabsList)
- `h-11 w-11 sm:h-8 sm:w-8` for icon-only buttons (44px mobile, 32px desktop)
- `allowDragging: false` + onSquareClick for mobile chessboard interaction
- `bg-muted/50 hover:bg-muted! border border-border/40` for collapsible trigger styling

### Key Lessons
1. Disable drag-and-drop early on mobile — HTML5 DnD simply doesn't work on iOS Safari, and react-chessboard's touch handling causes rendering bugs
2. CSS specificity matters with component libraries — shadcn uses `data-[size=sm]:h-7` which beats plain `h-7`; use `min-h` to override or Tailwind's `!` modifier
3. Mobile layout duplication is sometimes the right trade-off — fighting CSS to make one responsive layout work everywhere costs more than maintaining two clear layouts
4. Quick tasks are ideal for mobile polish — button heights, tab names, card layouts are all self-contained changes that don't warrant phase planning

---

## Milestone: v1.1 — Opening Explorer & UI Restructuring

**Shipped:** 2026-03-20
**Phases:** 6 | **Plans:** 15

### What Was Built
- Move explorer: next-move W/D/L stats, click-to-navigate, transposition warnings, board arrows
- UI restructuring: tabbed Openings hub, dedicated Import page, shared filter sidebar
- Enhanced import: clock data, termination, time control fix, username-scoped sync
- Game cards: 3-row layout, lucide-react icons, hover/tap minimap, null-safe metadata
- Bug fixes: data isolation, Google SSO last_login, cache clearing

### What Worked
- Phase dependency chain (11→12→13→14→15→16) allowed clean incremental delivery
- Human verification phase (14-03) caught real issues: hooks ordering bug, tab naming, import page redesign
- Quick tasks (19 total) handled polish effectively without disrupting phase work
- DB wipe decision removed migration complexity entirely for v1.1

### What Was Inefficient
- Phase 15 was renumbered mid-milestone (chart consolidation replaced by enhanced import data) — caused confusion in file naming with two "15-*" directories
- GCUI requirements were left at "Planned" status in traceability table despite being complete — bookkeeping drift
- summary-extract CLI returned null for one_liner fields — summaries lacked structured frontmatter fields

### Patterns Established
- Tab content as JSX variables (defined before return, reused in multiple Tabs instances)
- QueryClient singleton pattern for cross-cutting auth/cache concerns
- Username-scoped sync boundaries for multi-username import
- Single TooltipProvider wrapping lists to avoid per-item context overhead

### Key Lessons
1. Phase renumbering creates file system confusion — prefer adding at end (Phase 16) over replacing existing phase numbers
2. Human verification phases catch real bugs that automated tests miss (hooks ordering, UX issues)
3. Quick tasks are effective for UI polish during milestone execution — keeps phase scope clean

---

## Milestone: v1.6 — UI Polish & Improvements

**Shipped:** 2026-03-30
**Phases:** 6 | **Plans:** 11

### What Was Built
- Centralized theme system: CSS variables, brand-brown/charcoal Tailwind utilities, SVG feTurbulence noise texture class
- Charcoal containers with noise texture applied across all pages, brand subtab highlighting
- Shared WDLChartRow component replacing all inconsistent WDL chart implementations (custom bars, Recharts)
- Openings reference table: 3641 entries from TSV dataset, openings_dedup view, SQL-side WDL aggregation
- Most Played Openings redesign: top 10 per color, filter support, dedicated table UI, minimap popover
- Opening Statistics rework: section reordering, default chart data from most-played when no bookmarks, chart-enable toggle
- Bookmark card redesign: bigger minimap (72px), chart-enable toggle in button row, suggestions from most-played data
- Mobile drawer sidebars: Vaul-based right-side drawers for filters and bookmarks, deferred filter apply on close
- 26 quick tasks across the milestone

### What Worked
- Theme-first phase ordering (34→35→36→37→38→39) meant each phase built on the previous — shared components before consuming features
- WDL chart refactoring (Phase 35) paid off immediately — Phases 36-38 could use WDLChartRow without reimplementing
- SQL-side WDL aggregation (func.count.filter) moved counting from Python loops to SQL, measurable performance improvement
- Deferred filter apply pattern on mobile prevents API spam — filters accumulate, single request on sidebar close
- PR-based workflow for phases kept main clean while allowing iterative development

### What Was Inefficient
- Traceability table in REQUIREMENTS.md went stale — ORT-03 was implemented but unchecked, MOB-01-07 showed "Not started" despite completion
- Phase count in MILESTONES.md shows 8 instead of 6 (includes backlog phases in count) — CLI counting is approximate
- No milestone audit was run before completion — requirement drift went undetected until manual check

### Patterns Established
- `charcoal-texture` CSS class for consistent container styling with SVG noise
- WDLChartRow as single source of truth for all WDL visualizations
- Deferred state pattern: local state in sidebar, commit on close
- Openings reference table with precomputed FEN/ply_count for position lookup
- chart-enable toggle with localStorage persistence for user preferences

### Key Lessons
1. Requirement traceability tables need automated updates — manual status tracking drifts as soon as execution begins
2. Theme/component infrastructure phases early in a UI milestone pay compound dividends across subsequent phases
3. Milestone audits should be run proactively, not skipped — catching stale requirements at completion adds unnecessary friction
4. SQL-side aggregation (func.count.filter) is worth the migration cost — Python-side counting doesn't scale

---

## Cross-Milestone Trends

### Process Evolution

| Milestone | Phases | Plans | Key Change |
|-----------|--------|-------|------------|
| v1.0 | 10 | 36 | Established GSD workflow, phase/plan structure |
| v1.1 | 6 | 15 | Added human verification phases, heavy quick task usage |
| v1.2 | 3 | 5 | Frontend-only scope, mobile-first patterns, CSS specificity lessons |
| v1.3 | 4 | 10 | First production deployment, CI/CD, monitoring, launch readiness, 14 quick tasks |
| v1.4 | 1 | 2 | Self-hosted Umami analytics, minimal-scope milestone |
| v1.5 | 9 | 18 | Backend-heavy: position classifier, endgame analytics, engine analysis import |
| v1.6 | 6 | 11 | UI polish: theme system, shared components, openings table, mobile drawers, 26 quick tasks |
| v1.7 | 6 | 11 | Consolidation: ty type checking, knip dead exports, import speed 2x, SQL aggregations |
| v1.8 | 4 | N/A | Guest access via feature branch + PR, outside GSD workflow — no formal plans |
| v1.9 | 3 | 7 | UI/UX restructuring: openings sidebar, mobile layouts, stats subtab |
| v1.10 | 11 | 28 | Advanced endgame analytics: score gap, time pressure, ELO timeline, admin impersonation |
| v1.11 | 5 | 23 | LLM-first endgame insights: pydantic-ai Agent, llm_logs table, dual-line score chart |
| v1.12 | 1 | 6 | Benchmark DB infrastructure & ingestion pipeline; scope-down deferred analysis phases to SEED-006 |
| v1.13 | 3 | 14 | Templated opening insights: SQL transition aggregation, deep-link wiring, subnav refactor |
| v1.14 | 3 | 16 | Score-based opening insights: trinomial Wald confidence, effect size + confidence as orthogonal cues, troll watermark |

### Top Lessons (Verified Across Milestones)

1. DB wipe for schema changes is worth it in early development — migration complexity slows iteration
2. Human verification catches integration issues that unit tests miss
3. Quick tasks are the right tool for UI polish — confirmed across v1.1 (19 tasks), v1.2 (7 tasks), v1.3 (14 tasks), v1.6 (26 tasks)
4. CSS specificity with component libraries requires understanding the full chain — min-h/h/important patterns now documented
5. Production memory constraints need upfront planning — swap file and batch size tuning should be in initial deployment config
6. Human verification checkpoints (manual deploy steps) don't fit automated plan execution — use milestone gates instead
7. Infrastructure-first ordering pays off — theme/shared components early in UI milestones, DB schema early in backend milestones
8. Requirement traceability tables drift under manual maintenance — consider automated status syncing
9. Compact milestones with one conceptual move ship faster than mixed-theme ones (v1.4, v1.12, v1.14 all shipped in 1-3 days)
10. CI structural assertions (single-implementation, threshold lock-step) catch refactoring drift cheaply (v1.13 + v1.14)
11. Iteration via inline hotfixes / quick tasks is a feature — don't fight it, structure for it (v1.13 + v1.14 both used the inline hotfix loop to land calibrated end states that pre-locked specs couldn't have)
12. Smoke real data before locking statistical specs — v1.14's three confidence-bucket pivots cost real REQUIREMENTS rewrites that a 30-min discuss-phase smoke would have prevented
