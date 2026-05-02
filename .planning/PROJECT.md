# FlawChess

## What This Is

FlawChess — a free, open-source chess analysis platform at flawchess.com. Tagline: "Engines are flawless, humans play FlawChess." Users import their games from chess.com and lichess and analyze where they actually win and lose. Position matching uses Zobrist hashes (not opening names), so analysis stays consistent across platforms.

Five feature areas, mirrored on the homepage:

1. **Endgame Analytics** (hero) — WDL by endgame type, conversion/recovery rates when up/down material, Endgame ELO timeline per (platform, time control), and LLM-narrated personalized feedback on what the stats mean.
2. **Opening Explorer & Insights** — step through any position and see WDL per candidate move; an automatic 16-half-move scan surfaces opening strengths and weaknesses; works for the user and for scouting opponents.
3. **Time Management Stats** — average clock advantage/deficit at endgame entry, performance under matching time-pressure levels vs opponents, flag rates per time control.
4. **Opening Comparison & Tracking** — bookmark openings, compare WDL trends over time, filter by time control to see what works where.
5. **System Opening Filter** — filter by user's pieces only (e.g. London, King's Indian) so all opponent variations roll up under one system.

Mobile-first PWA, installable on iOS/Android, with drawer-based filter and bookmark sidebars.

## Core Value

Users get position-precise WDL analysis (openings + endgames + time pressure) on top of their actual chess.com and lichess games, with personalized LLM commentary on endgame performance and an auto-generated opening-strengths/weaknesses report. No per-platform fragmentation, no manual opening tagging.

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
- ✓ Backend `opening_insights_service` with `POST /api/insights/openings` — single SQL transition aggregation per (user, color) over `game_positions` for entry plies in [3, 16], LAG-window CTE + windowed `array_agg` passes `entry_san_sequence` to the service. Strict `>` 0.55 win/loss boundary, `MIN_GAMES_PER_CANDIDATE = 20` evidence floor, severity tier major (≥ 0.60) / minor — v1.13 Phase 70
- ✓ Two-pass attribution with parent-prefix Zobrist lookup (ctypes c_int64 signed-int64 conversion to match polyglot hashes); unmatched findings dropped, never surfaced as `<unnamed line>` placeholders — v1.13 Phase 70
- ✓ Partial composite covering index `ix_gp_user_game_ply` via Alembic `postgresql_concurrently=True` + `autocommit_block` — keeps the LAG-window scan an Index Only Scan with Heap Fetches: 0 at ~9% of `game_positions` size — v1.13 Phase 70
- ✓ Frontend `OpeningInsightsBlock` on Openings → Stats subtab with severity-accented `OpeningFindingCard` (DARK_RED / LIGHT_RED / DARK_GREEN / LIGHT_GREEN from `arrowColor.ts`), shared `LazyMiniBoard` thumbnail, four-state rendering. CI test `test_opening_insights_arrow_consistency` enforces backend/frontend threshold lock-step — v1.13 Phase 71
- ✓ Deep-link wiring — clicking a finding's Moves link replays `entry_san_sequence`, flips the board if needed, applies the matching color filter, navigates to Move Explorer with sticky severity tint + one-shot pulse on the candidate row — v1.13 Phase 71
- ✓ Openings page subnav layout refactor — desktop subnav lifts above `SidebarLayout`; mobile gains a sticky 4-tab subnav with filter button, board becomes non-sticky on Moves/Games and hidden on Stats/Insights, chevron-fold collapsible removed — v1.13 Phase 71.1
- ✓ Score-based opening insights — chess score `(W + 0.5·D)/N` is the canonical metric; effect-size gate against a 0.50 pivot with strict `≤`/`≥` boundaries (minor 0.45/0.55, major 0.40/0.60). Trinomial Wald 95% half-width drives `confidence: "low" | "medium" | "high"` (≤ 0.10 → high, ≤ 0.20 → medium, else low) — actual variance of `X ∈ {0, 0.5, 1}`, not the binomial-Wilson approximation. `loss_rate` / `win_rate` removed from API; `confidence` + `p_value` added to `OpeningInsightFinding` and `NextMoveEntry`. `MIN_GAMES_PER_CANDIDATE` dropped 20 → 10 for discovery framing — v1.14 Phase 75
- ✓ Frontend score-based coloring shipped end-to-end — `arrowColor.ts` migrated (effect-size only, no confidence cue on arrows); Move Explorer moves-list row tint by score with extended mute `(game_count < 10 OR confidence === 'low')`; Conf column with sort key `(confidence DESC, |score - 0.50| DESC)`; `OpeningFindingCard` shows score-based prose with level-specific confidence indicator and directional p-value tooltip; `UNRELIABLE_OPACITY` mute on cards/rows; four `InfoPopover` triggers on `OpeningInsightsBlock` section headers. Mobile parity at 375px. CI consistency test enforces backend/frontend threshold lock-step. PR #71 inline hotfix forces grey arrow + skips row tint when `confidence === 'low'` — v1.14 Phase 76
- ✓ Troll-opening watermark — `troll-face.svg` renders as 30%-opacity bottom-right watermark on `OpeningFindingCard` (mobile + desktop) and a small inline icon next to qualifying SAN rows in `MoveExplorer` (desktop only via `hidden sm:inline-block`). Frontend-only matching via side-only FEN piece-placement key (no backend schema, no Zobrist hash, no API contract change); curation via Node/TS script with per-ply emission for human pruning. Decorative `<img>` idiom (`alt=""` + `aria-hidden="true"`, `pointer-events-none`) — v1.14 Phase 77

### Active (v1.15)

- [ ] **EVAL-01**: Endgame conv/recov classification uses Stockfish eval (depth 15) at the entry position instead of the material-imbalance + 4-ply persistence proxy
- [ ] **EVAL-02**: New game imports populate `eval_cp` / `eval_mate` for span-entry positions where the lichess `%eval` annotation is absent
- [ ] **EVAL-03**: Historical span-entry positions across benchmark and prod databases are backfilled with engine evals
- [ ] **EVAL-04**: Endgame queries simplified to threshold on `eval_cp` / `eval_mate` directly; the proxy code path is removed (hard cutover)
- [ ] **EVAL-05**: Validation report (`/conv-recov-validation` skill) re-run post-backfill confirms agreement is engineered to ~100% by construction on the now-fully-populated subset and headline gauges remain stable

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

## Current Milestone: v1.15 Eval-Based Endgame Classification

**Goal:** Replace the material-imbalance + 4-ply persistence proxy for endgame conversion/recovery classification with Stockfish eval (depth 15) populated into the existing `eval_cp` / `eval_mate` columns on `game_positions`. Backfill historical span-entry positions across benchmark + prod, eval new span-entry positions during import going forward, refactor endgame queries to threshold on eval, and remove the proxy entirely (hard cutover). Trust existing lichess `%eval` annotations where present; only fill gaps. Keep the `material_imbalance` column for other downstream features.

**Target features:**
- Stockfish (depth 15) integrated as a backend runtime dependency, with a thin engine wrapper that backfill and the import path share
- One-time backfill script that populates `eval_cp` / `eval_mate` for endgame span-entry rows where both columns are NULL — runs on benchmark first, then prod
- Import pipeline change: after endgame classification, eval the entry position of each per-class span (1-3 positions per game)
- Endgame service / repository refactor: drop `_MATERIAL_ADVANTAGE_THRESHOLD`, drop `PERSISTENCE_PLIES`, drop the `array_agg(... ORDER BY ply)[5]` contiguity case-expression — replace with a direct lookup of `eval_cp` / `eval_mate` at the span-entry row, with the existing `color_sign` flip and mate handling as max conv/recov
- Index migration: swap `INCLUDE` columns on `ix_gp_user_endgame_game` so the new query stays index-only
- Validation: re-run `/conv-recov-validation` on benchmark post-backfill; agreement should be ~100% by construction on the subset that previously had eval, and headline gauges should not shift more than expected for any `(rating, TC)` cell

**Source:** Validation report at `reports/conv-recov-validation-2026-05-02.md` flagged that the proxy holds at ~81.5% agreement vs Stockfish on the populated subset (22% eval coverage from lichess only) but misses ~24% of substantive material-edge sequences. Queen and pawnless classes underperform structurally. Conversation between user and Claude on 2026-05-02 quantified the cost (~1.5M positions × 35 ms at depth 15 ≈ 2 hours on 8 cores for the benchmark backfill) and confirmed `eval_cp` / `eval_mate` already exist on `game_positions` (lichess-perspective, white POV — same convention as `material_imbalance`).

## Current State

v1.14 Score-Based Opening Insights shipped 2026-04-29 (PRs #69, #70, #71, #72, #73). Fourteen milestones complete (v1.0–v1.14), 73 phases (+4 inserted), live at flawchess.com.

v1.14 folded SEED-007 Option A (Wilson on score, 0.50 pivot, no user-baseline) and SEED-008 (label reframe + confidence cues) under a single calibrated framing. Score `(W + 0.5·D)/N` is the canonical metric across `opening_insights_service.py`, `openings_repository.py`, `arrowColor.ts`, and the `NextMoveEntry` / `OpeningInsightFinding` API payloads. Effect-size gate against a 0.50 pivot with strict `≤`/`≥` boundaries (minor 0.45/0.55, major 0.40/0.60). Trinomial Wald 95% half-width — using the actual variance of the chess result distribution `X ∈ {0, 0.5, 1}`, not the binomial-Wilson approximation that over-states uncertainty when draws are common — drives the `confidence: "low" | "medium" | "high"` badge surfaced on Insights cards and Move Explorer moves-list rows. `loss_rate` / `win_rate` removed cleanly; `severity` retained alongside the new `confidence` and `p_value` fields. `MIN_GAMES_PER_CANDIDATE` dropped 20 → 10 to enable discovery framing; the badge calibrates trust where the hard floor used to gate. The conceptual pivot is "effect size decides what shows up, confidence annotates how sure we are" — the right inversion for a discovery UI.

Frontend shipped end-to-end with mobile parity at 375px: arrows colored by score (effect-size only, no confidence cue on arrows); moves-list row tint by score with extended mute `(game_count < 10 OR confidence === 'low')`; new Conf column with sort key `(confidence DESC, |score - 0.50| DESC)`; `OpeningFindingCard` shows score-based prose with level-specific confidence indicator and directional p-value tooltip; `UNRELIABLE_OPACITY` mute on cards/rows; four `InfoPopover` triggers on `OpeningInsightsBlock` section headers. PR #71 inline hotfix forces grey arrow + skips row tint when `confidence === 'low'`, strengthening the at-a-glance board read. INSIGHT-UI-04 (soften titles per SEED-008) descoped 2026-04-28 per Phase 76 D-04: severity word never appeared as user-facing text; confidence badge + sort calibration deliver SEED-008's intent without rewriting "Weakness/Strength" titles.

Phase 77 added a troll-opening watermark — frontend-only matching via a side-only FEN piece-placement key (no backend schema, no Zobrist hash, no API contract change). `troll-face.svg` renders as 30%-opacity bottom-right watermark on `OpeningFindingCard` (mobile + desktop) and a small inline icon next to qualifying SAN rows in `MoveExplorer` (desktop only via `hidden sm:inline-block`). Curation is offline via a Node/TS script that emits per-ply candidates (both colors) for human pruning. Decorative `<img>` idiom (`alt=""` + `aria-hidden="true"`, `pointer-events-none`) keeps the asset cacheable and out of the accessibility tree.

LLM narration of opening insights remains deferred — v1.14 shipped the calibrated data plumbing (effect size + confidence + p_value) that future LLM narration would consume. Population-relative weakness signals stay gated on full benchmark ingest (SEED-006).

<details>
<summary>Previous milestone snapshots (v1.13, v1.12)</summary>

v1.13 Opening Insights shipped 2026-04-27 (PRs #66, #67, #68). v1.13 fulfilled SEED-005 with a templated/rule-based opening-insights pipeline. Backend `opening_insights_service` scans every (entry_position, candidate_move) pair across entry plies [3, 16] via a single LAG-window CTE per (user, color) over `game_positions`, deduplicates by Zobrist hash with deepest-opening attribution, applies an `n ≥ 20` evidence floor and a strict `>` 0.55 win/loss boundary, and emits `OpeningInsightFinding[]` with `entry_san_sequence` so the frontend can replay the line on demand. Frontend `OpeningInsightsBlock` on Openings → Stats renders severity-accented per-finding cards with deep-links into the Move Explorer pre-positioned at the entry FEN. Phase 71.1 refactored the Openings page subnav to match the Endgames pattern. Mid-milestone scope-down on 2026-04-27 dropped Phases 72/73/74. v1.13 deliberately did NOT consume the v1.12 benchmark DB — opening positions are book theory.

v1.12 Benchmark DB Infrastructure & Ingestion Pipeline shipped 2026-04-26 (PR #65). v1.12 delivered the operational half of SEED-002: a separate `flawchess-benchmark` PostgreSQL 18 instance on port 5433, a third read-only MCP server (`flawchess-benchmark-db`), Alembic-driven schema parity with dev/prod/test (no fork), a streaming `zgrep` eval pre-filter, a stratified subsampling pipeline at the player-opportunity level on (rating × TC) with separate `WhiteElo`/`BlackElo` per side, and a SIGINT/SIGKILL-resumable per-user checkpoint orchestrator. Smoke-validated end-to-end via a `--per-cell 3` ingest of 274k games / 19.4M positions in 3h 6min. Scoped down on 2026-04-26 from 5 phases (69-73) to 1 (69); Phases 70-73 moved to SEED-006. Hot-patch dropped `games.eval_depth` + `games.eval_source_version` after the smoke confirmed Lichess's `/api/games/user` emits bare `[%eval cp]` with no depth field.

</details>

## Context

- **Current state:** v1.13 shipped 2026-04-27. 70 phases complete across 13 milestones. Live at flawchess.com with CI/CD and Sentry.
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
| Single SQL transition aggregation per (user, color) over `game_positions` | LAG-window CTE on `(user_id, game_id, ply)` index streams transitions without re-sort; HAVING enforces evidence floor and threshold at SQL level — no Python-side post-filter | ✓ Good |
| `entry_san_sequence` via `array_agg` window with `BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING` | Frontend can replay the line on the chessboard without a separate roundtrip; sequence is "everything before the entry move" by construction | ✓ Good |
| Strict `>` 0.55 win/loss boundary mirroring `frontend/src/lib/arrowColor.ts` | CI test `test_opening_insights_arrow_consistency` asserts threshold lock-step; eliminates classifier/visual divergence | ✓ Good |
| Severity tier `major (≥ 0.60) / minor (>0.55, <0.60)` with arrowColor border mapping | Severity becomes a visual axis (DARK_RED / LIGHT_RED / DARK_GREEN / LIGHT_GREEN) consistent with arrow stroke colors | ✓ Good |
| Two-pass attribution (direct + parent-prefix lookup) with drop-on-miss | Avoids `<unnamed line>` placeholders; ctypes c_int64 conversion required to match python-chess polyglot signed-int64 hashes (BLOCKER-2) | ✓ Good |
| `MIN_GAMES_PER_CANDIDATE = 20` as `MIN_GAMES_PER_CANDIDATE` (was n=10 in original spec) | n=10 was too noisy in real-world testing; n=20 settles WDL into a believable rate before classification | ✓ Good |
| Bookmarks NOT consumed as algorithmic input | Bookmarks remain a UI feature for explicit user tracking; opening insights operate on actual play frequency, not curated picks | ✓ Good |
| Constants in tiny `opening_insights_constants.py` module (16 lines) | Avoids circular import between repository (uses constants in SQL) and service (uses constants in classification) | ✓ Good |
| Repository owns module-level threshold constants, service re-exports | Single source of truth on the SQL boundary; constants colocate with the queries that embed them | ✓ Good |
| Partial composite covering index `ix_gp_user_game_ply` with `INCLUDE (full_hash, move_san)` | Index Only Scan with Heap Fetches: 0; partial predicate `ply BETWEEN 1 AND 17` keeps the index ~9% of `game_positions` size | ✓ Good |
| First project use of `postgresql_concurrently=True` + `autocommit_block` | Required for index creation on a write-heavy table without locking out import; rationale captured inline so future autogenerate doesn't reorder columns | ✓ Good |
| `LazyMiniBoard` extracted from inline `GameCard` function into shared `frontend/src/components/board/` module | Reused by `OpeningFindingCard` (deep-link card) and the future Insights bookmark surfaces; IntersectionObserver lazy render preserved byte-for-byte | ✓ Good |
| Single `<a href>` whole-card touch target on `OpeningFindingCard` | Originally split, then collapsed to the whole card; reverted in quick-task 260427-h3u to explicit "Moves" + "Games" links because the whole-card target obscured which subtab opened | ⚠️ Revisit (link semantics may evolve) |
| Phase 71.1 inserted mid-milestone (Openings subnav refactor to match Endgames pattern) | Frontend layout debt surfaced during Phase 71 UAT; cheaper to fix in-milestone than carry the diverging desktop/mobile shapes into v1.14 | ✓ Good |
| v1.13 scope-down to Phases 70+71+71.1 (72/73/74 descoped) | Move Explorer row tint already conveys the signal at the displayed position; per-finding cards already deliver per-opening actionable signal at finer granularity than an aggregate; bookmark-badge density risked alert fatigue | ✓ Good |
| Templated/rule-based v1, no LLM | Defer LLM narration until templated findings are in real users' hands and we know which findings are worth narrating; v1.11 LLM stack remains available for v1.13.x or v1.14 | ✓ Good |
| v1.13 deliberately does NOT consume v1.12 benchmark DB | Opening positions are book theory (engine eval ≈ 0.0); absolute under-/over-performance over n ≥ 20 is actionable without population baselines per SEED-005 § Why Self-Referential Is Sufficient | ✓ Good |
| Score `(W + 0.5·D)/N` replaces loss/win rate as the canonical metric | One number drives classification, color, and badge; `severity`/`confidence`/`p_value` are derived layers on top. Eliminates the `loss_rate > 0.55` asymmetry of v1.13 | ✓ Good |
| Trinomial Wald 95% half-width (variance `(W + 0.25·D)/N − score²`) over binomial Wilson | Chess result distribution `X ∈ {0, 0.5, 1}` is trinomial; binomial Wilson over-states uncertainty when draws are common. Standard formula in BayesElo / Ordo. Pure-Python `math` only, no scipy | ✓ Good |
| Strict `≤` / `≥` boundaries on score and half-width thresholds | Eliminates ambiguity at the boundary; constants live in `opening_insights_constants.py` for retunability | ✓ Good |
| API exposes both `confidence` (badge) and `p_value` (tooltip) | Frontend renders effect size (severity) + precision (confidence) + significance (tooltip) per finding without overloading any one cue | ✓ Good |
| `MIN_GAMES_PER_CANDIDATE` 20 → 10 for discovery framing | Confidence badge replaces hard-floor gate; surfaces low-confidence candidates as discovery signal rather than filtering them out | ✓ Good |
| Sort key `(confidence DESC, |score - 0.50| DESC)` | High-confidence findings rise within each severity bucket; effect-size is within-confidence tiebreak | ✓ Good |
| INSIGHT-UI-04 descoped (no title rewrite per SEED-008) | Severity word never appeared as user-facing text (only drove border color); confidence badge + sort carry SEED-008 intent without rewriting "Weakness/Strength" titles | ✓ Good |
| Force grey arrow + skip row tint when `confidence === 'low'` (PR #71, post-Phase 76 inline hotfix) | Board reads cleaner; low-confidence findings still surface in the table with the badge but don't visually claim authority on the board | ✓ Good |
| Single `compute_confidence_bucket` shared module + CI structural assertion | One implementation, asserted by CI; `opening_insights_service` and the move-explorer payload both consume it; CI consistency test enforces backend/frontend threshold lock-step | ✓ Good |
| Troll-opening matching frontend-only via side-only FEN piece-placement key | No backend schema / Zobrist hash / API contract change. Small read-only curated set; lookup once per finding render | ✓ Good |
| Per-ply emission (both colors) in curation script | Pushes ambiguity into human review step instead of guessing at "the defining position" of an opening | ✓ Good |
| Decorative `<img>` watermark with `alt=""` + `aria-hidden="true"` + `pointer-events-none` | Asset stays cacheable, browser handles scaling, kept out of accessibility tree, doesn't block underlying interactive elements | ✓ Good |
| Phase 77 added off-roadmap-scope under v1.14 | Frontend-only follow-on with no v1.15 dependency; cheaper to ship under v1.14 than open a hyphenated milestone | ✓ Good |

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
*Last updated: 2026-05-02 — v1.15 Eval-Based Endgame Classification opened. Single-phase milestone: replace the material-imbalance + 4-ply persistence proxy for endgame conv/recov classification with Stockfish eval (depth 15). Source: `reports/conv-recov-validation-2026-05-02.md`. SEED-010 Library milestone gated until v1.15 ships.*
