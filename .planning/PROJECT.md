# FlawChess

## What This Is

FlawChess — a multi-user chess analysis platform that lets players import their games from chess.com and lichess, then analyze win/draw/loss rates for specific board positions. It solves the problem of inconsistent opening categorization on existing platforms — instead of relying on opening names, users define positions visually and filter by actual piece placement. Includes an interactive move explorer showing next moves with W/D/L stats per position, endgame performance analytics with conversion/recovery metrics, and a polished mobile PWA experience with drawer-based sidebars.

## Core Value

Users can determine their success rate for any opening position they specify, filtering by their own pieces only, regardless of how platforms categorize the opening.

## Requirements

### Validated

- ✓ Import games from chess.com and lichess via API by username — v1.0
- ✓ On-demand re-sync to fetch latest games — v1.0
- ✓ Store all available game metadata for future analyses — v1.0
- ✓ Interactive chess board to specify search positions by playing moves — v1.0
- ✓ Filter analysis by white/black/both position matching — v1.0
- ✓ Filter by time control, rated/casual, recency, color, opponent type — v1.0
- ✓ Display win/draw/loss rates for matching games — v1.0
- ✓ Display matching games as cards with metadata and platform links — v1.0
- ✓ Multi-user support with data isolation — v1.0
- ✓ Position bookmarks with auto-suggestions, mini boards, drag-reorder — v1.0
- ✓ Rating history and global stats pages — v1.0
- ✓ Move explorer showing next moves with W/D/L stats per move — v1.1
- ✓ Store move SAN in game_positions with index for performant lookups — v1.1
- ✓ Dedicated Import page replacing import modal — v1.1
- ✓ Merged Openings tab with Move Explorer / Games / Statistics sub-tabs — v1.1
- ✓ Shared filter sidebar across Openings sub-tabs — v1.1
- ✓ Enhanced game import: clock data, termination, time control fix — v1.1
- ✓ Game cards with 3-row layout, icons, hover minimap — v1.1
- ✓ PWA setup (manifest, service worker, installable, chess knight icons) — v1.2
- ✓ Dev workflow for phone testing (LAN + Cloudflare tunnel) — v1.2
- ✓ Mobile-first navigation with bottom bar, "More" drawer, responsive header — v1.2
- ✓ Click-to-move chessboard on touch devices with sticky mobile layout — v1.2
- ✓ 44px touch targets on all interactive elements, no horizontal scroll at 375px — v1.2
- ✓ Android/iOS in-app PWA install prompts — v1.2
- ✓ CI/CD pipeline (GitHub Actions: test + SSH deploy + health check) — v1.3
- ✓ Sentry error monitoring (backend + frontend) — v1.3
- ✓ Full rebrand from Chessalytics to FlawChess (code, PWA, GitHub org) — v1.3
- ✓ Docker Compose production deployment on Hetzner with Caddy auto-TLS — v1.3
- ✓ Public homepage with feature sections, FAQ, register/login CTA — v1.3
- ✓ SEO fundamentals (meta tags, Open Graph, sitemap.xml, robots.txt) — v1.3
- ✓ Privacy policy page at /privacy — v1.3
- ✓ Per-platform import rate limiter preventing chess.com/lichess bans — v1.3
- ✓ Professional README with screenshots and self-hosting instructions — v1.3
- ✓ Web analytics via self-hosted Umami — v1.4
- ✓ Game phase classification (opening/middlegame/endgame) per position at import — v1.5
- ✓ Material signature, imbalance, and endgame class per position at import — v1.5
- ✓ Engine analysis data import (eval, accuracy, move quality) from chess.com/lichess — v1.5
- ✓ Endgame performance statistics in dedicated Endgames tab — v1.5
- ✓ Endgame stats filterable by type (rook, minor piece, pawn, queen, mixed) — v1.5
- ✓ Conversion stats (win rate when up material) with timeline charts — v1.5
- ✓ Recovery stats (draw/win rate when down material) with timeline charts — v1.5
- ✓ Homepage with feature showcase, FAQ, acknowledgements — v1.5
- ✓ Centralized theme system (CSS variables, charcoal containers, noise texture) — v1.6
- ✓ Shared WDL chart component replacing all inconsistent implementations — v1.6
- ✓ Openings reference table (3641 entries from TSV) with SQL-side WDL aggregation — v1.6
- ✓ Most played openings (top 10 per color) with filter support and minimap popovers — v1.6
- ✓ Smart default chart data from most-played openings when no bookmarks exist — v1.6
- ✓ Chart-enable toggle on bookmark cards with localStorage persistence — v1.6
- ✓ Mobile drawer sidebars for filters and bookmarks with deferred apply — v1.6
- ✓ Knip for frontend dead export detection with CI integration — v1.7
- ✓ Naming improvements (router prefixes, endpoint relocation) — v1.7
- ✓ Code deduplication (shared apply_game_filters, frontend buildFilterParams) — v1.7
- ✓ Dead code removal (7 dead files, unused hooks/types/exports, -1522 lines) — v1.7
- ✓ noUncheckedIndexedAccess TypeScript strictness (56 type errors fixed) — v1.7
- ✓ Static type checking with astral `ty` + CI/CD integration — v1.7
- ✓ DB query optimization (SQL aggregations replacing Python-side counting) — v1.7
- ✓ DB column types verified optimal (no migration needed) — v1.7
- ✓ Refactor button brand colors to CSS variables (.btn-brand) — v1.7
- ✓ Consistent Pydantic response models across all API endpoints — v1.7
- ✓ Import speed optimization (~2x throughput, single PGN parse, bulk UPDATE) — v1.7
- ✓ Guest access — "Use as Guest" button on homepage, JWT-based guest sessions with 30-day auto-refresh — v1.8
- ✓ Guest as first-class User row with is_guest=True, full platform access without special-casing — v1.8
- ✓ Account promotion via email/password or Google SSO, preserving all imported data — v1.8
- ✓ Guest UX — persistent guest banner, import page info box, auth page logo linking — v1.8
- ✓ OAuth CSRF fix (CVE-2025-68481) and guest creation IP rate limiting — v1.8
- ✓ Openings mobile: unified control row (Tabs | Color | Bookmark | Filter) outside the board collapse region, staying visible when the board is collapsed; enlarged board-action column buttons and 44px collapse handle; backdrop-blur translucent sticky surface (MMOB-01) — v1.9 Phase 50
- ✓ Endgames mobile: visual-alignment pass on the sticky top row to match the Openings unified row (backdrop-blur, 44px height, 44px filter button) (EGAM-01) — v1.9 Phase 50
- ✓ Openings desktop: collapsible left-edge sidebar (48px icon strip + 280px on-demand Filters/Bookmarks panel) with overlay/push behavior at the 1280px breakpoint, live filter apply on desktop (DESK-01..05) — v1.9 Phase 49
- ✓ Stats subtab: 2-column Bookmarked Openings: Results on desktop (lg breakpoint) and stacked WDLChartRows for mobile Most Played (STAB-01, STAB-02) — v1.9 Phase 51
- ✓ Homepage: static 2-column desktop hero with Opening Explorer preview (heading + screenshot + bullets), pills row removed, Opening Explorer removed from FEATURES (HOME-01) — v1.9 Phase 51
- ✓ Stats page relabeled to "Global Stats" across desktop nav, mobile bottom bar, More drawer, and mobile header, with new page h1; opponent_type + opponent_strength filters wired end-to-end through /stats/global and /stats/rating-history, defaulting to excluding bot games (GSTA-01, GSTA-02) — v1.9 Phase 51
- ✓ Conversion & recovery persistence filter — 4-ply persistence check + 100cp threshold for conv/recov classification — v1.10 Phase 48
- ✓ Endgame tab performance — 8-query timeline collapsed to 2, consolidated `/api/endgames/overview` endpoint, deferred desktop filter apply — v1.10 Phase 52
- ✓ Endgame Score Gap & Material Breakdown — signed score difference + material-stratified WDL table (Conversion/Parity/Recovery) with Good/OK/Bad verdict calibration — v1.10 Phases 53, 59
- ✓ Opponent-based self-calibrating baseline for Conv/Parity/Recov bullet charts (muted when sample < 10 games) — v1.10 Phase 60
- ✓ Time pressure analytics — per-time-control clock stats table + two-line user-vs-opponents score chart across 10 buckets — v1.10 Phases 54, 55
- ✓ Endgame ELO Timeline — skill-adjusted rating per (platform, time-control) combination with asof-join anchor on user's real rating and weekly volume bars — v1.10 Phases 57, 57.1
- ✓ Test suite hardening — TRUNCATE on session start, seeded_user fixture, aggregation sanity + material tally + router integration tests — v1.10 Phase 61
- ✓ Admin user impersonation — superuser can impersonate any user via new /admin page, single auth_backend + ClaimAwareJWTStrategy, impersonation pill in header, last_login/last_activity frozen — v1.10 Phase 62
- ✓ LLM-backed Endgame Insights endpoint — `POST /api/insights/endgame` returns a structured `EndgameInsightsReport` (overview + up to 4 Section insights) via pydantic-ai Agent, cached on findings_hash, rate-limited 3 misses/hr, soft-fails to last cached report — v1.11 Phase 65
- ✓ Deterministic findings pipeline — `compute_findings` over `/api/endgames/overview` produces `SubsectionFinding` per subsection × window (`all_time`, `last_3mo`) with zone/trend/sample-quality annotations and three cross-section flags — v1.11 Phase 63
- ✓ Shared zone registry (`endgame_zones.py`) — single source of truth for thresholds; Python→TypeScript codegen with CI drift guard — v1.11 Phase 63
- ✓ Generic `llm_logs` Postgres table — designed for reuse across future LLM features (18 cols, JSONB, FK CASCADE, 5 indexes, genai-prices cost accounting with `cost_unknown:<model>` soft-fallback) — v1.11 Phase 64
- ✓ Provider-agnostic model selection — `PYDANTIC_AI_MODEL_INSIGHTS` env var, startup validation, system prompt versioned in `app/prompts/endgame_insights.md` — v1.11 Phase 65
- ✓ Frontend `EndgameInsightsBlock` — parent-lifted mutation state, overview + 4 inline Section blocks, single retry affordance on failure — v1.11 Phase 66
- ✓ Dual-line Endgame vs Non-Endgame Score over Time chart — replaces single-line Score Gap chart with shaded gap fill (green when endgame leads, red when trails); prompt simplified — v1.11 Phase 68
- ✓ Isolated `flawchess-benchmark` PostgreSQL 18 instance on port 5433, deployed via `docker-compose.benchmark.yml` with read-only MCP role, `bin/benchmark_db.sh` lifecycle script, and Alembic-driven schema parity with dev/prod/test (no schema fork) — v1.12 Phase 69
- ✓ Third read-only MCP server `flawchess-benchmark-db` registered and documented in `CLAUDE.md` Database Access section — v1.12 Phase 69
- ✓ Resumable Lichess monthly-dump ingestion pipeline with `zgrep`-streaming eval pre-filter, per-user checkpoint, idempotent inserts via existing `(platform, platform_game_id)` unique constraint, SIGINT + SIGKILL safety — v1.12 Phase 69
- ✓ Stratified subsampling at the player-opportunity level on (rating_bucket × time_control) — 5 buckets × 4 TCs, separate `WhiteElo` / `BlackElo` per side; smoke-validated via `--per-cell 3` ingest of 274k games / 19.4M positions in 3h 6min — v1.12 Phase 69
- ✓ Centipawn convention (signed from white's POV, centipawns vs pawn-units) verified by `tests/test_benchmark_ingest.py::test_centipawn_convention_signed_from_white` running in CI — v1.12 Phase 69

### Active (v1.13)

- [ ] Opening weakness and strength insights (SEED-005) — v1.13 in flight

### Deferred (gated on full benchmark ingest — SEED-006)

- [ ] Classifier validation replication at 10–100x scale (Phase B gate)
- [ ] Rating-stratified material-vs-eval offset analysis
- [ ] Parity proxy validation against Stockfish eval
- [ ] `/benchmarks` skill upgrade — population baselines and rating-bucketed zone thresholds applied to `frontend/src/lib/theme.ts`

### Out of Scope

- Manual PGN file upload — API import only
- In-app game viewer — link to chess.com/lichess instead
- Human-like engine analysis — future: engine evaluation filtered by human move plausibility at target Elo (see Maia Chess approach)
- Offline API data caching — chess data is user-specific + authenticated; caching risks stale analysis
- Swipe-to-navigate between tabs — conflicts with chessboard touch gestures
- Material configuration filter for endgames — deferred to future milestone

## Current Milestone: v1.13 Opening Insights

**Goal:** Surface opening-line strengths and weaknesses for each user via auto-scanning of most-played and bookmarked openings, with templated findings and deep-links into the Move Explorer at the implicated entry position. Build on the existing `game_positions` Zobrist-hash architecture and the v1.11 in-tab insights placement idiom. **Independent of the benchmark DB** — opening positions are book theory (engine eval ≈ 0.0), so absolute under-/over-performance over n ≥ 10 games is actionable without population baselines.

**Target features:**
- Backend `opening_insights_service` — scans top-10 most-played openings per color + bookmarked positions, classifies each (entry_position, candidate_move) pair as weakness (loss_rate ≥ 0.55) / strength (score ≥ 0.60) at n ≥ 10 games, dedupes by Zobrist hash with deepest-opening attribution, ranks by frequency × severity (formula resolved in Phase A discuss)
- Frontend `OpeningInsightsBlock` on Openings → Stats subtab — templated bullets with red/green semantics, deep-links navigate to Openings → Moves tab pre-loaded at the entry FEN with the candidate move highlighted
- Pure templated/rule-based in v1 — no LLM. LLM wrap-up deferred to v1.13.x or v1.14 once findings are in real users' hands.

**Descoped 2026-04-27** (after Phases 70 + 71 + 71.1 shipped):
- ~~Inline weakness/strength bullets on Openings → Moves~~ — covered by existing `MoveExplorer` row tint via `getArrowColor`; bullet on top of tint was redundant signal.
- ~~(Stretch) Meta-recommendation aggregate finding~~ — Phase 71's per-finding cards already deliver actionable per-opening signal at finer granularity.
- ~~(Stretch) Bookmark-card weakness badge~~ — nav notification-dot density already high; a third badge channel risks alert fatigue.

**Pre-v1.13 quick tasks:**
- v1.11 VAL-01 — insights snapshot test against a canonical user fixture (no benchmark dependency)
- Top-10 most-played-openings parity-filter fix — `query_top_openings_sql_wdl` excludes ~half of eligible named openings per color (white-defined openings invisible in black top-10 and vice versa); confirmed bug via Hillbilly Attack example. Phase A reuses this service-layer call, so fix it before v1.13 builds on it. See `.planning/todos/pending/2026-04-26-top10-openings-parity-bug.md`.

## Current State

v1.12 Benchmark DB Infrastructure & Ingestion Pipeline shipped 2026-04-26 (PR #65). Twelve milestones complete (v1.0–v1.12), 67 phases (+3 inserted), live at flawchess.com.

v1.12 delivered the operational half of SEED-002: a separate `flawchess-benchmark` PostgreSQL 18 instance on port 5433, a third read-only MCP server (`flawchess-benchmark-db`), Alembic-driven schema parity with dev/prod/test (no fork), a streaming `zgrep` eval pre-filter that drops the ~85% of Lichess dump games without `[%eval` headers before they hit python-chess, a stratified subsampling pipeline at the player-opportunity level on (rating × TC) with separate `WhiteElo`/`BlackElo` per side, and a SIGINT/SIGKILL-resumable per-user checkpoint orchestrator. Smoke-validated end-to-end via a `--per-cell 3` ingest of 274k games / 19.4M positions in 3h 6min. Verification report at `reports/benchmark-db-phase69-verification-2026-04-26.md`.

The milestone was scoped down on 2026-04-26 from 5 phases (69-73) to 1 (69). Phases 70-73 (classifier validation at scale, rating-stratified offsets, Parity validation, `/benchmarks` skill upgrade & rating-bucketed zone recalibration) moved to SEED-006, gated on the full benchmark ingest. Pipeline correctness was the v1.12 deliverable; populating the DB is operational ops work, not a milestone gate.

A hot-patch mid-Phase 69 dropped two dead columns (`games.eval_depth` and `games.eval_source_version`) added by plan 69-02's migration, after the smoke confirmed Lichess's `/api/games/user` endpoint emits bare `[%eval cp]` annotations with no depth field. Lesson: don't trust documentation about "depth available in PGN" — Lichess **dump** exports include depth, **API** exports do not. Verify with a sample before specifying schema.

## Context

- **Current state:** v1.12 shipped 2026-04-26. 67 phases complete across 12 milestones. Live at flawchess.com with CI/CD and Sentry.
- **Stack:** FastAPI + React 19/TS/Vite 5 + PostgreSQL + python-chess + TanStack Query + Tailwind + shadcn/ui (Command, Popover)
- **Auth:** FastAPI-Users (JWT + Google SSO + guest sessions with is_guest flag + impersonation via ClaimAwareJWTStrategy)
- **Core algorithm:** Zobrist hashes (white_hash, black_hash, full_hash) precomputed at import for indexed integer equality lookups
- **PWA:** vite-plugin-pwa + Workbox (NetworkOnly for API routes), vaul drawer, tailwindcss-safe-area
- **Analytics:** Consolidated `/api/endgames/overview` serves every endgame chart in one round trip on a single AsyncSession; deferred filter apply on desktop (matches mobile)
- **LLM stack (v1.11):** pydantic-ai Agent with env-var-driven model selection (`PYDANTIC_AI_MODEL_INSIGHTS`), `genai-prices` for cost accounting, generic `llm_logs` Postgres table as prompt-engineering harness
- **Benchmark DB (v1.12):** separate PostgreSQL 18 instance on port 5433 (`docker-compose.benchmark.yml`), shares canonical Alembic chain with dev/prod/test, benchmark-only ops tables (`benchmark_selected_users`, `benchmark_ingest_checkpoints`) created via `Base.metadata.create_all()` against the benchmark engine on first invocation
- **Known issues:** react-chessboard v5 arrow clearing workaround (clearArrowsOnPositionChange: false), BoardArrow local type definition, touch drag disabled (click-to-move only on mobile), Phase 60/61 have incomplete SUMMARY.md artifacts (no functional impact); pre-existing ORM/DB column drift (`game_positions.clock_seconds`, `games.white_accuracy`, `games.black_accuracy` REAL→Float) on every Alembic autogenerate — deferred cleanup migration outstanding

## Constraints

- **Tech stack**: Python backend (FastAPI), uv for package management
- **Database**: PostgreSQL with asyncpg — must support efficient position-based queries across thousands of games
- **Deployment**: Must work locally and be deployable to a server
- **Libraries**: Use established open-source libraries (python-chess, etc.) rather than reinventing
- **HTTP client**: httpx async only — never use requests or berserk

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| FastAPI for backend | User expertise, async support, modern Python | ✓ Good |
| API-only import (no PGN upload) | Simpler v1, covers primary use case | ✓ Good |
| Interactive board over FEN input | Better UX for target users | ✓ Good |
| uv for package management | Fast, modern Python tooling | ✓ Good |
| React 19 + TypeScript + Vite 5 | react-chessboard 5.x requires React 19 | ✓ Good |
| PostgreSQL (no SQLite) | Multi-user concurrent writes, BIGINT index, asyncpg | ✓ Good |
| DB wipe for v1.1 | No migration needed — reimport after schema change | ✓ Good |
| Zobrist hash position matching | 64-bit integer equality vs FEN string comparison | ✓ Good |
| move_san ply semantics | SAN on ply N = move played FROM that position | ✓ Good |
| DISTINCT + GROUP BY for transpositions | COUNT(DISTINCT g.id) prevents double-counting | ✓ Good |
| Filter state in OpeningsPage parent | Survives tab switches without reset | ✓ Good |
| QueryClient singleton in lib/ | Shared across 401 interceptor and auth transitions | ✓ Good |
| vite-plugin-pwa with generateSW | Zero-config, Vite 7 compatible, Workbox managed | ✓ Good |
| vaul for mobile drawer | Handles scroll lock, backdrop, iOS momentum natively | ✓ Good |
| Click-to-move only on mobile | HTML5 DnD absent on iOS Safari; drag causes black screen | ✓ Good |
| Duplicate mobile Openings layout | Sticky board incompatible with sidebar's flex-column | ⚠️ Revisit |
| CSS variables + Tailwind utilities for theme | Centralized colors without abandoning Tailwind workflow | ✓ Good |
| SVG feTurbulence noise texture | Lightweight CSS-only texture, no image assets | ✓ Good |
| Shared WDLChartRow component | Single source of truth for all WDL visualizations | ✓ Good |
| Openings reference table from TSV | 3641 curated openings with ECO/PGN/FEN for position lookup | ✓ Good |
| SQL-side WDL aggregation (func.count.filter) | Moves counting from Python loops to SQL for performance | ✓ Good |
| Deferred filter apply on mobile sidebar close | Prevents API spam while user adjusts multiple filters | ✓ Good |
| Vaul drawers for mobile sidebars | Consistent with existing More drawer pattern, good touch UX | ✓ Good |
| Hetzner CX32 + Docker Compose + Caddy | Simple single-VPS deployment for solo dev | ✓ Good |
| Plausible over Google Analytics | No cookie consent required, GDPR-simple | ✓ Good |
| Sentry for both backend + frontend | Single project, DSN baked at Docker build time | ✓ Good |
| asyncio.Semaphore rate limiter | Per-platform concurrency control without Redis/Celery | ✓ Good |
| Backend expose-only (no ports) | Caddy is sole internet-facing entry point | ✓ Good |
| astral ty for static type checking | Catches type errors at CI time, complements ruff | ✓ Good |
| Knip for dead export detection | Automated CI gate prevents dead code accumulation | ✓ Good |
| noUncheckedIndexedAccess in TS | Forces safe array/Record index access patterns | ✓ Good |
| Unified process_game_pgn | Single PGN walk per game instead of 3 separate passes | ✓ Good |
| Bulk CASE UPDATE for move_count/result_fen | One SQL statement per batch vs N per-game UPDATEs | ✓ Good |
| .btn-brand CSS class over JS constant | Styling concern in CSS, not JS import chain | ✓ Good |
| Bearer transport for guest JWTs | Avoids dual-transport complexity, Safari/Firefox ETP issues | ✓ Good |
| Guest as User row with is_guest=True | Promotion is single-row UPDATE, no FK migration needed | ✓ Good |
| Register-page promotion over modal | Cleaner UX, reuses existing register form, less code | ✓ Good |
| Consolidated /api/endgames/overview | All endgame charts in one round trip, sequential on one AsyncSession | ✓ Good |
| 2-query timeline via GROUP BY (game_id, endgame_class) | Collapsed 8 per-class queries, 150-500s → few seconds on prod | ✓ Good |
| Deferred filter apply on desktop | Matches existing mobile pattern; avoids query storm | ✓ Good |
| 4-ply persistence + 100cp conv/recov threshold | Reduces transient-capture noise; validated against Stockfish eval | ✓ Good |
| Opponent-based self-calibrating baseline | Replaces global-average with opponent's rate against the user | ✓ Good |
| Skill-adjusted Endgame ELO formula | actual_elo + 400·log10(skill/(1-skill)); not performance rating | ✓ Good |
| Asof-join anchor on user's real rating | Fixes rolling-mean lag that confused "actual" terminology | ✓ Good |
| Weekly volume bars on timeline charts | Visual weight indicator per weekly point | ✓ Good |
| Single auth_backend + ClaimAwareJWTStrategy | Zero changes to existing Depends(current_active_user) call sites | ✓ Good |
| Truncate flawchess_test at pytest session start | Enables deterministic integer assertions via seeded_user fixture | ✓ Good |
| Split time_control into base_time + increment | Time pressure % denominator per-game base time, clamped at 2x | ✓ Good |
| pydantic-ai Agent with provider-agnostic model env var | `PYDANTIC_AI_MODEL_INSIGHTS` lets model swap without code changes; startup fails fast on missing/invalid | ✓ Good |
| System prompt in file (`app/prompts/endgame_insights.md`), not string literal | Versioned, diff-readable, bumping `_PROMPT_VERSION` is the cache-invalidation handle | ✓ Good |
| Generic `llm_logs` table, not `insights_llm_logs` | Designed up-front to host every future LLM feature; `endpoint` column distinguishes consumers | ✓ Good |
| Findings-hash cache + 3-miss/hr/user rate limit with soft-fail | Equivalent filter states reuse cached report; over-limit returns last cached rather than error | ✓ Good |
| Shared zone registry + Python→TS codegen with CI drift guard | Narrative and chart visuals agree by construction; no two-sided drift | ✓ Good |
| Parent-lifted mutation state for EndgameInsightsBlock (no Context) | `useEndgameInsights` in Endgames.tsx; block + 4 slot instances observe same state | ✓ Good |
| Dual-line Score chart over single-line Score Gap chart | Makes endgame-vs-non-endgame composition self-evident; eliminated the prompt's score_gap framing rule | ✓ Good |
| Phase 67 descope — rollout to all users instead of beta cohort | Fast learning from real telemetry; tradeoff: no automated regression guard against prompt changes | — Pending (snapshot test deferred to pre-v1.13) |
| Separate `flawchess-benchmark` Postgres instance, not a schema in dev/prod | Isolation from prod; safe to wipe and reseed; second MCP server with read-only role keeps the analysis interactive | ✓ Good |
| Same canonical Alembic chain as dev/prod/test (no schema fork) | Lichess `[%eval` populates the existing `game_positions.eval_cp`/`eval_mate` columns; no benchmark-only games / game_positions variant to maintain | ✓ Good |
| Benchmark-only ops tables via `Base.metadata.create_all()` | `benchmark_selected_users` and `benchmark_ingest_checkpoints` exist solely to drive the orchestrator; carving them out of Alembic keeps the analytical schema clean | ✓ Good |
| Streaming `zgrep` eval pre-filter before python-chess | Drops the ~85% of dump games without `[%eval` headers an order of magnitude faster than structural parsing | ✓ Good |
| Player-side bucketing on `WhiteElo` / `BlackElo` separately | Each side belongs to its own rating cell; aggregations over `game_positions` never roll up by a single game-level rating field | ✓ Good |
| Per-user checkpoint table + idempotent `(platform, platform_game_id)` inserts | SIGINT/SIGKILL-resumable without dedup logic at the application layer; duplicates blocked by the existing unique constraint | ✓ Good |
| v1.12 scope-down to Phase 69 only (Phases 70-73 → SEED-006) | Full benchmark ingest is days of wall-clock ops work, not a milestone gate; treating it as one was blocking unrelated work like v1.13 opening insights | ✓ Good |
| Smoke-from-`--per-cell 3` over interim `--per-cell 30` ingest | Pipeline-correctness evidence collected from a small smoke run rather than blocking on a multi-day full ingest; aligns with the scope-down framing | ✓ Good |
| Hot-patch drop of `eval_depth` + `eval_source_version` mid-Phase 69 | Post-smoke sampling proved both columns were dead (Lichess API emits bare `[%eval cp]` with no depth field); lighter than running a corrective phase | ✓ Good |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd:transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd:complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-04-27 — v1.13 Phases 72/73/74 descoped after Phases 70 + 71 + 71.1 shipped; milestone ready for close.*
