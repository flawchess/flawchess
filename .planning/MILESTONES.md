# Milestones: FlawChess

## v1.12 Benchmark DB Infrastructure & Ingestion Pipeline (Shipped: 2026-04-26)

**Phases completed:** 1 phase (69), 6 plans (5 fully executed + 1 with descoped sub-tasks), delivered via PR #65 (squash merge).
**Stats:** 98 files changed, +13,440 / -1,740 lines, 51 commits over 2 days (2026-04-24 → 2026-04-26)
**Scope-down (2026-04-26):** Originally Phases 69-73. Phases 70-73 (classifier validation at scale, rating-stratified offsets, Parity validation, `/benchmarks` skill upgrade & zone recalibration) moved to SEED-006, gated on the full benchmark ingest. Pipeline correctness is the v1.12 deliverable; populating the DB is ops.

**Key accomplishments:**

- Isolated `flawchess-benchmark` PostgreSQL 18 container on port 5433, deployed via `docker-compose.benchmark.yml` with read-only MCP role `flawchess_benchmark_ro`, lifecycle script `bin/benchmark_db.sh` (start/stop/reset), and Alembic-driven schema parity with dev/prod/test (Phase 69-01)
- Third read-only MCP server `flawchess-benchmark-db` registered and documented in `CLAUDE.md` Database Access section alongside the existing two MCP DB servers (Phase 69-03)
- Eval-presence pre-filter via streaming `zgrep` scan over the Lichess monthly PGN dump, so the ~85% of dump games without `[%eval` headers never reach the python-chess parser, dropping selection-scan walltime by an order of magnitude (Phase 69-04)
- Stratified subsampling at the player-opportunity level on (rating_bucket × time_control). 5 rating buckets × 4 TCs, with separate `WhiteElo` / `BlackElo` bucketing per side (no game-level rating rollup); 90M games scanned, 491k qualifying, 8,628 distinct players persisted across 20 cells, 17/20 hitting the 500-user cap (Phase 69-04)
- Resumable ingest orchestrator with per-user checkpoint table, idempotent inserts via the existing `(platform, platform_game_id)` unique constraint, SIGINT + SIGKILL safe. Pending in-flight users are picked up first on resume; 0 duplicate game rows verified (Phase 69-05)
- Smoke-test ingest at `--per-cell 3` ran end-to-end against the live Lichess `/api/games/user` endpoint. 60 terminal rows: 56 completed, 3 over_20k_games skips, 1 unexplained failure deferred to SEED-006; 274,143 games and 19.4M positions imported in 3h 6min wall-clock (Phase 69-06)
- Pipeline-correctness verification report at `reports/benchmark-db-phase69-verification-2026-04-26.md` covering all four Dimension-8 evidence sections (selection scan, smoke ingest, resumability, eval coverage) plus storage budget projection (~205 GB at full `--per-cell 100` ingest, flagged for SEED-006 disk sizing) (Phase 69-06)
- Hot-patch mid-plan: dropped `games.eval_depth` and `games.eval_source_version` columns (added in plan 69-02 migration `b11018499e4f`, dropped in `6809b7c79eb3`) after the smoke confirmed Lichess's `/api/games/user` endpoint emits bare `[%eval cp]` annotations with no depth field. Both columns were dead weight; reintroduce when an actual second eval source exists. INGEST-06 reduced to "centipawn convention verified", already covered by `tests/test_benchmark_ingest.py::test_centipawn_convention_signed_from_white` running in CI (Phase 69-06)
- Centipawn convention verified, signed from white's POV (`pov.white().score()` / `.mate()`): centipawns vs pawn-units (`[%eval 2.35]` → +235 cp), mate annotations (`[%eval #4]` → mate=4) all asserted via the centipawn-convention test in CI

**Known deferred items:**

- Plan 69-06 sub-tasks 06-05 (`--per-cell 30` interim ingest) and 06-08 (manual cleanup of the 2026-03 Lichess dump file from local disk), descoped per the 2026-04-26 v1.12 scope-down. Full-scale population is operational ops work, not a milestone gate.
- VAL-01 from v1.11 (insights snapshot test), explicitly out of v1.12 scope per REQUIREMENTS.md. Promote via `/gsd-quick` when ready (no dependency on benchmark infra).
- Phases 70-73, moved to SEED-006 (benchmark population zone recalibration). Surface when full benchmark ingest completes.
- Pre-existing ORM/DB column drift (`game_positions.clock_seconds`, `games.white_accuracy`, `games.black_accuracy` REAL→Float), deferred again from v1.11 close. Deserves a dedicated cleanup migration.

---

## v1.11 LLM-first Endgame Insights (Shipped: 2026-04-24)

**Phases completed:** 5 phases (63, 64, 65, 66, 68), 23 plans, delivered via PR #61 (squash merge). Phase 67 (Validation & Beta Rollout) descoped — insights enabled for all users via commit `c91478e` instead of the beta-cohort validation loop. Phase 68 was added mid-milestone after UAT feedback.
**Stats:** 166 files changed, +42,078 / -262 lines, ~190 commits over 5 days (2026-04-20 → 2026-04-24)

**Key accomplishments:**

- LLM-backed Endgame Insights: `POST /api/insights/endgame` returns a structured `EndgameInsightsReport` (overview paragraph + up to 4 Section insights) produced by a pydantic-ai Agent, cached on a findings hash, rate-limited to 3 misses/hr/user, with soft-fail to the last cached report (Phase 65)
- Deterministic findings pipeline: `compute_findings` turns `/api/endgames/overview` into per-subsection-per-window `EndgameTabFindings` with zone/trend/sample-quality annotations and three cross-section flags (baseline-lift mutes score gap, clock-entry advantage/no-advantage) so the LLM reasons over pre-validated numbers (Phase 63)
- Shared zone registry as single source of truth: `app/services/endgame_zones.py` drives both narrative and chart visuals; Python→TypeScript codegen with CI drift guard so frontend gauge constants can never silently diverge (Phase 63)
- Generic `llm_logs` Postgres table (18 columns, BigInteger PK, JSONB for filter_context and response_json, FK CASCADE to users, 5 indexes including 3 composites with `created_at DESC`) designed to host every future LLM feature. Async repository with `genai-prices`-powered per-call cost accounting and `cost_unknown:<model>` soft-fallback (Phase 64)
- Provider-agnostic model selection via `PYDANTIC_AI_MODEL_INSIGHTS` env var; backend refuses to start if env var is missing/invalid. System prompt loaded from `app/prompts/endgame_insights.md` at startup — no string literals in `.py` files (Phase 65)
- Frontend `EndgameInsightsBlock` with parent-lifted mutation state pattern (Endgames.tsx holds one `useEndgameInsights` mutation; EndgameInsightsBlock + 4 SectionInsightSlot instances observe the same state without a context provider). Single retry affordance on any failure path (Phase 66)
- Dual-line "Endgame vs Non-Endgame Score over Time" chart replaces the single-line Score Gap chart — both absolute Score series rendered with a colored shaded area between them (green when endgame leads, red when trails). Prompt's `score_gap` framing rule simplified since the chart makes gap composition self-evident (Phase 68)
- Pre-merge milestone cohesion review — critical failing frontend test fixed, dead codegen pipeline completed (Phase 66 switchover finished: 3 FE chart components now import from generated zone constants), stale `Filters:` prompt reference removed (bumped to `endgame_v15`)

**Known deferred items:**

- Phase 67 descoped — VAL-01 (ground-truth regression test against SEED-001 canonical user fixture) and VAL-02 (admin-impersonation eyeball validation across 5 real user profiles) not executed. Insights were enabled for all users via commit `c91478e`. Recommended follow-up in v1.12: retrofit snapshot test against one real production user fixture.

---

## v1.10 Advanced Analytics (Shipped: 2026-04-19)

**Phases completed:** 11 phases (48, 52-55, 57, 57.1, 59-62), 28 plans, delivered via PRs #38, #43, #47, #49, #50, #51, #52 — all squash merged. Phase 56 cancelled, Phase 58 moved to backlog (999.6).
**Stats:** 249 files changed, +54835 / -1852 lines, 124 commits over ~12 days (2026-04-07 → 2026-04-19)

**Key accomplishments:**

- Endgame tab performance — 8 per-class timeline queries collapsed into 2, consolidated `/api/endgames/overview` serving every endgame chart in one round trip on a single AsyncSession, deferred filter apply on desktop (Phase 52)
- Endgame Score Gap & Material Breakdown — signed endgame vs non-endgame score difference plus material-stratified WDL table (ahead/equal/behind at endgame entry, later renamed Conversion/Parity/Recovery) with Good/OK/Bad verdict calibration (Phases 53, 59)
- Opponent-based self-calibrating baseline for Conv/Parity/Recov bullet charts — opponent's rate against the user replaces global average, muted when sample < 10 games (Phase 60)
- Time pressure analytics — per-time-control clock stats table (Phase 54) + two-line user-vs-opponents score chart across 10 time-remaining buckets with backend aggregation (Phase 55 + iteration via quick tasks)
- Endgame ELO Timeline — skill-adjusted rating per (platform, time-control) combination with paired Endgame ELO / Actual ELO lines, asof-join anchor on user's real rating, weekly volume bars for data-weight transparency (Phases 57 + 57.1)
- Conversion/recovery persistence filter — material imbalance required at endgame entry AND 4 plies later, threshold lowered 300cp → 100cp, validated against Stockfish eval analysis (Phase 48)
- Test suite hardening — `flawchess_test` TRUNCATE on session start, deterministic 15-game `seeded_user` fixture, aggregation sanity tests (WDL perspective, material tally, rolling windows, filter intersections, recency boundaries, within-game dedup, endgame transitions), router integration tests asserting exact integer counts (Phase 61)
- Admin user impersonation — superusers can impersonate any user via a new /admin page with shadcn Command+Popover search, single auth_backend + ClaimAwareJWTStrategy wrapper (zero call-site changes), last_login/last_activity frozen during impersonation, persistent impersonation pill in header with × to end session (Phase 62)
- Sentry Error Test moved from Global Stats to Admin tab; superuser-gated nav entry

---

## v1.9 UI/UX Restructuring (Shipped: 2026-04-10)

**Phases completed:** 3 phases (49-51), 7 plans, delivered via PRs #40, #41, #42
**Stats:** 57 files changed, +8692 / -1602 lines, ~21-hour execution window

**Key accomplishments:**

- Openings desktop sidebar — collapsible left-edge 48px icon strip + 280px on-demand Filters/Bookmarks panel with overlay/push behavior at the 1280px breakpoint, live filter apply on desktop
- Openings mobile unified control row — Tabs | Color | Bookmark | Filter lifted outside the board collapse region so controls stay visible when the board is collapsed; 44px tappable collapse handle; backdrop-blur translucent sticky surface
- Endgames mobile visual alignment — 44px backdrop-blur sticky row with 44px filter button matching the Openings mobile pattern (EGAM-01)
- Global Stats filters wired end-to-end — `opponent_type` and `opponent_strength` through `/stats/global` and `/stats/rating-history`, plus hooks/API client layer; bot games now excluded by default
- Stats subtab layout restructuring — 2-column Bookmarked Openings: Results on desktop (lg breakpoint), stacked WDLChartRows for mobile Most Played replacing the cramped 3-col table
- Homepage 2-column desktop hero — left=hero content, right=Interactive Opening Explorer preview (heading + screenshot + bullets), pills row removed, Opening Explorer removed from FEATURES list
- Global Stats rename — "Stats" → "Global Stats" across desktop nav, mobile bottom bar, More drawer, mobile header, plus new page h1; FilterPanel opponent controls enabled

---

## v1.8 Guest Access (Shipped: 2026-04-06)

**Phases completed:** 4 phases (44-47), delivered via PR #37
**Stats:** 56 files changed, +3915 / -1294 lines, 3 new test files (1193 lines of tests)

**Key accomplishments:**

- Guest session foundation — `is_guest` User model, JWT-based guest sessions with 30-day auto-refresh, IP rate limiting
- Guest frontend — "Use as Guest" buttons on homepage and auth page, persistent guest banner indicating limited access
- Email/password promotion — backend promotion service, register-page promotion flow preserving all imported data
- Google SSO promotion — OAuth promotion route with guest identity preservation across redirect, email collision handling
- Security fix — patched Google OAuth for CVE-2025-68481 CSRF vulnerability (double-submit cookie validation)
- UX polish — import page guest guard, auth page logo linking, delete button disabled during active imports

---

## v1.7 Consolidation, Tooling & Refactoring (Shipped: 2026-04-03)

**Phases completed:** 6 phases, 11 plans, 17 tasks

**Key accomplishments:**

- Astral `ty` static type checker integrated into CI — zero backend type errors, all functions annotated
- Knip dead export detection + `noUncheckedIndexedAccess` — zero dead code, strict TypeScript index safety
- Import pipeline ~2x faster — unified single-pass PGN processing, bulk CASE UPDATE, batch size 10→28
- SQL aggregation (COUNT().filter()) replacing Python-side W/D/L counting loops
- Consistent naming and deduplication — router prefixes, shared apply_game_filters, frontend buildFilterParams
- Dead code removal — 7 dead files deleted, unused shadcn/ui re-exports cleaned, -1522 lines
- CSS variable brand buttons (.btn-brand) replacing JS constant, typed Pydantic response models on all endpoints

---

## v1.6 UI Polish & Improvements (Shipped: 2026-03-30)

**Phases completed:** 6 phases, 11 plans

**Key accomplishments:**

- Centralized theme system with CSS variables, charcoal containers with SVG noise texture, brand subtab highlighting
- Shared WDLChartRow component replacing all inconsistent WDL chart implementations across the app
- Openings reference table (3641 entries from TSV) with SQL-side WDL aggregation and filter support
- Most Played Openings redesign: top 10 per color, dedicated table UI with minimap popovers
- Opening Statistics rework: smart default chart data from most-played openings, chart-enable toggles on bookmarks
- Mobile drawer sidebars for filters and bookmarks with deferred filter apply on close

---

## v1.3 Project Launch (Shipped: 2026-03-22)

**Phases completed:** 4 phases, 10 plans, 12 tasks

**Key accomplishments:**

- Full codebase renamed from Chessalytics to FlawChess across 20 files — PWA manifest, logo, GitHub org transfer
- Complete Docker Compose stack (FastAPI + Caddy 2.11.2 + PostgreSQL) deployed to Hetzner VPS with auto-TLS
- GitHub Actions CI/CD pipeline: test + lint + SSH deploy + health check polling
- Sentry error monitoring on backend (sentry-sdk[fastapi]) and frontend (@sentry/react) with Docker build-time DSN injection
- Public homepage with feature sections, FAQ, and register/login CTA; SEO meta tags, sitemap.xml, robots.txt
- Per-platform rate limiter (asyncio.Semaphore) protecting chess.com/lichess imports from concurrent bans
- Privacy policy page at /privacy; professional README with screenshots and self-hosting instructions

---

## v1.2 Mobile & PWA (Shipped: 2026-03-21)

**Phases:** 17–19 (3 phases, 5 plans)

Made the application work great on smartphones as an installable PWA with mobile-optimized navigation, touch interactions, and dev workflow for phone testing.

**Key accomplishments:**

- Installable PWA with service worker, chess-themed icons, and Workbox caching (NetworkOnly for API routes)
- Mobile bottom navigation bar with direct tabs and slide-up "More" drawer (vaul-based)
- Click-to-move chessboard on touch devices with sticky board layout on Openings page
- 44px touch targets on all interactive elements, no horizontal scroll at 375px
- Android/iOS in-app install prompts (beforeinstallprompt + manual iOS instructions)
- Cloudflare Tunnel dev workflow for HTTPS phone testing

---

## v1.1 — Opening Explorer & UI Restructuring

**Shipped:** 2026-03-20
**Phases:** 11–16 (6 phases, 15 plans)

Added interactive move explorer with W/D/L stats per position, restructured UI with tabbed Openings hub and dedicated Import page, enriched game import data, and redesigned game cards.

**Key accomplishments:**

- Move explorer with next-move W/D/L stats, click-to-navigate, transposition handling
- Chessboard arrows showing next moves with win-rate color coding
- UI restructured: tabbed Openings hub (Moves/Games/Statistics) + dedicated Import page
- Enhanced import: clock data, termination reason, time control fix, multi-username sync
- Game cards redesigned: 3-row layout with icons, hover/tap minimap showing final position
- Data isolation fixes, Google SSO last_login, cache clearing on auth transitions

---

## v1.0 — Initial Platform

**Shipped:** 2026-03-15
**Phases:** 1–10

Built the complete multi-user chess analysis platform: game import from chess.com/lichess, Zobrist hash position matching, interactive board with W/D/L analysis, position bookmarks with auto-suggestions, game cards, rating/stats pages, and browser automation optimization.

**Key capabilities:**

- Import pipeline with incremental sync (chess.com + lichess)
- Position analysis via precomputed Zobrist hashes (white/black/full)
- Position bookmarks with drag-reorder, mini boards, piece filter
- Auto-generated bookmark suggestions from most-played openings
- Game cards with rich metadata and pagination
- Rating history, global stats, openings W/D/L charts
- Multi-user auth with data isolation
