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
- ✓ Endgame conv/recov classification migrated from material-imbalance + 4-ply persistence proxy to direct Stockfish-eval thresholding (±100 cp on `eval_cp`, color-flipped to user perspective; `eval_mate` short-circuits to ±1,000,000 cp). Hard cutover, proxy code path removed entirely. Closes the structural gap on Queen and pawnless classes — v1.15 Phase 78
- ✓ Pinned Stockfish in backend Docker image (sf_17 → sf_18 with SHA-256 supply-chain verification); `app/services/engine.py` async wrapper with FastAPI lifespan integration; `scripts/backfill_eval.py` idempotent + resumable CLI driver with `--workers N` parallel evaluation via `EnginePool` — v1.15 Phase 78
- ✓ Import-time eval pass: per-class span-entry rows + middlegame entry row populated on every new import in `_flush_batch`, same transaction. Adds well under 1s to the typical-game import path. Module-level `EnginePool` of `STOCKFISH_POOL_SIZE` workers (prod ships 2) parallelises the eval pass via `asyncio.gather` — v1.15 Phase 78 + PR #79
- ✓ Alembic `c92af8282d1a` reshapes `ix_gp_user_endgame_game INCLUDE` from `material_imbalance` to `eval_cp` / `eval_mate` so endgame queries stay index-only. `_classify_endgame_bucket(eval_cp, eval_mate, user_color)` is the single classification helper — v1.15 Phase 78
- ✓ Per-position `phase` SmallInteger column on `game_positions` (0=opening, 1=middlegame, 2=endgame) computed via Python port of [lichess `Divider.scala`](https://github.com/lichess-org/scalachess/blob/master/core/src/main/scala/Divider.scala) using existing `piece_count`, `backrank_sparse`, `mixedness` inputs. 11 Divider parity tests lock output to lichess reference. Populated on every new import and backfilled across benchmark + prod (Alembic `1efcc66a7695`) — v1.15 Phase 79
- ✓ Middlegame entry position (`MIN(ply)` of `phase = 1` per game) Stockfish-evaluated at depth 15 alongside endgame span-entry positions, populated into the same `eval_cp` / `eval_mate` columns. Substrate for v1.16 opening-stats analyses — v1.15 Phase 79
- ✓ Opening Stats subtab — avg eval at middlegame entry ± std (user POV) with one-sample t-test confidence pill (`compute_eval_confidence_bucket`) and CI-whisker MiniBulletChart, on bookmarked + most-played tables. Later restructured into a two-column card grid via quick task 260506-rtk that replaced MostPlayedOpeningsTable — v1.16 Phase 80
- ✓ Move Explorer + Opening Insights WDL/score/confidence/p_value now reflect resulting-position (transposition-inclusive). `query_transposition_wdl` + `query_resulting_position_wdl` repo helpers; `game_count` and the n≥10 surfacing gate stay move-played for honest disclosure — v1.16 Phase 80.1
- ✓ Endgame Start vs End twin-tile section above the WDL table: entry-eval (cp, Wald-z sig-tested vs 0) + endgame score (Wilson score test vs 50%), three-state color, n≥10 gate, "we can't tell" framing for non-significant verdicts. `EndgamePerformanceResponse` gains `entry_eval_mean_pawns`, `entry_eval_n`, `entry_eval_p_value`, `entry_eval_ci_low_pawns`, `entry_eval_ci_high_pawns`, `endgame_score_p_value` — v1.16 Phase 81
- ✓ LLM endgame-insights prompt awareness of Start vs End metrics — `MetricId` + `SubsectionId` Literal extensions, `ZONE_REGISTRY` entries for `entry_eval_pawns` (band ±0.5 after D-08 tightening) + `endgame_score` (band [0.45, 0.55]); prompt version `endgame_v23` → `endgame_v24` — v1.16 Phase 82
- ✓ Stockfish-baseline predicted endgame score — `eval_cp_to_expected_score` (Lichess sigmoid k=0.00368208) + `eval_mate_to_expected_score`; 5 new `EndgamePerformanceResponse` fields (`entry_expected_score`, `_n`, `_p_value`, `_ci_low`, `_ci_high`); 2x2 grid restructure of Start vs End (Where you start + What you do with it × Stockfish baseline + your achieved); LLM prompt `endgame_v25` → `endgame_v26` narrates achievable-vs-achieved gap as headline diagnostic. Closes SEED-014 — v1.16 Phase 83

- ✓ Endgames page table→card redesign (Sections 1–3 on the WDL + ScoreBullet card pattern); eval-based ΔES Score Gap replacing the degenerate rate-based mirror-bucket peer-diff; hypothesis tests + 95% CIs on Endgame Score Differences; Endgame Skill dropped end-to-end and the timeline rebuilt as Endgame ELO via a logistic stretch around Actual ELO; full Time Pressure rework with benchmark-calibrated zones; inactivity-gap annotations on all 6 ordinal-axis timeline charts — v1.17 Phases 84–88.4 (Phase 89 Polish dropped; 87.3 percentile composite superseded by 87.4→87.6)
- ✓ Import pipeline memory-leak fix (bound-parameter `executemany` replacing the per-batch unique-SQL `case()`+`IN` leak), per-batch `AsyncSession` recycle, periodic + on-DB-reconnect orphan-job reaper, bounded-retry failure-state recording — v1.18 Phase 90
- ✓ Two-lane import: hot path holds no Stockfish work, separate `run_eval_drain()` lifespan coroutine evaluates entry plies in the background. `games.evals_completed_at` + partial index, Stockfish-coverage header bar, per-metric "based on N of M eligible games" caveat on every eval-dependent stat — v1.18 Phase 91
- ✓ Custom date range filter — closed `Recency` string union on the API wire replaced with explicit `from_date` / `to_date` params; 9th "Custom range…" item in the recency dropdown with desktop Popover + mobile nested Drawer (shadcn Calendar); `Recency` → `RecencyPreset` UI-only type — v1.18 Phase 92

- ✓ Peer-relative percentile chips on Endgame metrics — per-(metric, ELO anchor, TC) cohort CDF family built from 50-Elo sliding windows (K=200 floor-passing users), per-(user, TC) rating anchor (game-weighted blended median over converted-chess.com + native-lichess games), bare `p23` pill chip face + 4-bullet tooltip with rating-anchor disclosure, filter-independent (chip is a trait of the user, not a view of their data) — v1.19 Phases 93, 94, 94.1, 94.2, 94.3, 94.4

- ✓ Time-control-aware endgame reporting — Endgame Metrics section split into per-TC cards (Conv/Recov on TC-specific bands, Parity/Score Gap on the shared band); Endgame Type Breakdown restructured into collapsible per-TC accordion cards with a 2×2 type-tile grid (Mixed dropped) banded per-(class × TC); peer-relative percentile chips on the per-TC Conversion/Parity/Recovery rates (12 new per-(metric, TC) cohort metrics); generated cohort-CDF lookup demoted from Python source to a `benchmark_cohort_cdf` DB table — v1.21 Phases 97, 98, 99, 99.1

- ✓ Per-run/per-xdist-worker test database cloned from a migrated template (`CREATE DATABASE … TEMPLATE`); session-start `TRUNCATE … CASCADE` whole-schema lock retired; advisory-lock template auto-refresh on Alembic head drift; killed runs self-heal; `pytest -n auto` safe and 2.2x faster (18.56s vs 40.29s) — v1.22 Phase 100
- ✓ 11 frontend deps brought to latest major across six bisectable atomic clusters (lucide-react 1, Vite 8 + plugin-react 6, jsdom 29, eslint 10 stack, TypeScript 6, recharts 3); recharts 3 visual-UAT'd; typescript-eslint ↔ TS6/eslint-10 peer-compat clean — v1.22 Phase 101

- ✓ AI endgame report reasons over peer-relative percentile rank (cohort-framed, "vs ~{anchor}-rated players") and narrates time pressure (Score Gap by Remaining Time, Clock Gap, Net Flag Rate) under the cohort `zone` gate; relaxed Data Analysis overview cap; prompt vocabulary audited against the concepts accordion + tooltip popovers; p-values + CI bounds kept OUT; `endgame_v35` → `endgame_v43` — v1.23 Phase 102 (LLM-01..07)
- ✓ GM-feedback endgame recommendation refinements — decision-speed time-trouble advice, no fabricated mechanism, no named theoretical positions at any Elo; GM Noël Studer study link in the Recommendations card; prompt condensed ~35% (`endgame_v44`) — v1.23 Phase 103

- ✓ Top-level **Library** page hosting Import and Overview as deep-linkable URL-routed `<Tabs variant="brand">` subtabs (`/library/import`, `/library/overview`); nav dropped to Library · Openings · Endgames (+ Admin); old routes redirect, `totalGames === 0` dot moved to Library, state-dependent landing (LIB-01..09) — v1.24 Phase 104
- ✓ On-the-fly mistake-detection service — per-ply severity (Lichess-aligned 0.05/0.10/0.15 ES-drop thresholds, mate Option B) + attribution tags derived from stored `eval_cp`/`eval_mate`, typed `FlawRecord` contract, no schema change (LIBG-02/06/07) — v1.24 Phase 105
- ✓ Games-surface backend — `GET /api/library/games` mistake-filtered archive (per-game B/M/I counts + deduped chips) + `GET /api/library/mistake-stats` aggregates, via `apply_game_filters` `EXISTS` + SQL window-scan (LIBG-08/09) — v1.24 Phase 106
- ✓ Games subtab frontend — filterable game-card archive + Flaw-Stats panel (per-severity rates, tag distribution, trend, `% analyzed` + N); returning-user default subtab (LIBG-01/03) — v1.24 Phase 107
- ✓ Flaws subtab + `game_flaws` materialization (composite PK `(user_id, game_id, ply)`, M+B-only) + per-flaw endpoint + shared cross-tab Flaw filter (single-flaw `EXISTS`, OR-within / AND-across family) + `scripts/backfill_flaws.py` single-classify-path — v1.24 Phase 108 (SEED-038)
- ✓ Per-card expected-score eval chart — recharts area chart (white-perspective lichess sigmoid, 50% midline, advantage shading), your-flaw dots, phase-transition lines, per-ply tooltips scrubbing the miniboard; delivered inline on the existing payload (LIBG-10) — v1.24 Phase 109
- ✓ Flaw-tag taxonomy overhaul — tempo `hasty`/`unrushed`, outcome-independent impact ladder `reversed`/`squandered`, canonical chip names + definition popovers (codegen'd `flawThresholds.ts` + CI drift gate), active-filter chip emphasis — v1.24 Phase 110
- ✓ Apply-only filter model across all filter panels (Reset + Apply footer) + Flaws-subtab card rework (2-up `Card` grid, banded header + 132px miniboard + eval swing, View-game modal via `GET /api/library/games/{game_id}`) — v1.24 Phases 111, 112

- ✓ Opponent-flaw materialization — `game_flaws` records both sides' mistakes/blunders for every analyzed game; the player/opponent split is **derived at query time** via a single tested `is_opponent_expr(ply, games.user_color)` helper (no `is_opponent` column / migration / index — FLAWX-03 voided); all classify paths persist opponent flaws with no extra engine cost; every existing reader retrofitted with a player-only gate (FLAWX-01/02/04) — v1.25 Phase 113
- ✓ Benchmark flaw-delta "typical" zones — `/benchmarks` §5 chapter computing per-(metric, ELO×TC) Q1/Q3 quartile delta zones for all 15 flaw-delta metrics with ELO/TC marginals and per-axis Cohen's-d collapse verdicts (the light delta-IQR zone, not the 99-breakpoint CDF) (FLAWBMK-01..04) — v1.25 Phase 114
- ✓ Exact `games.ply_count` replacing `move_count` — one migration (add + backfill + drop, ~10s on prod); display stays full-moves; exact per-game user-move denominator with zero `game_positions` access (SEED-041 §9) — v1.25 Phase 114.1
- ✓ You-vs-opponent flaw comparison — `GET /api/library/flaw-comparison` returning the full 15-bullet inventory via a unified per-100-moves paired per-game delta + CI (FLAWCMP-02 Wilson method voided in favour of one estimator), honoring all game filters; old tag-distribution zone replaced by a family-grouped `MiniBulletChart` grid (measure + CI + benchmark blue zone) with per-bullet tooltips (definition / sign / tempo caveat / filter×zone) and a section-level sample gate (FLAWCMP-01/03/04/05, FLAWUI-01..06) — v1.25 Phase 115

## Current Milestone: v1.26 Full-Game Eval Pipeline

**Goal:** Every active user's recent games get full per-ply Stockfish analysis at Lichess parity, server-side, unlocking flaw features for chess.com games and broadening v1.25's comparison reach beyond the ~37–51 heavy-analysis users.

**Target features:**
- All-ply eval drain — extend `eval_drain.py` from entry-plies to all non-book plies at 1M nodes / NNUE / multiPV=1 (SEED-012 D-6; measured 0.98s/position on prod); evals into `game_positions.eval_cp/eval_mate` with ply≤20 `full_hash` dedup lookup (D-5)
- Tiered priority queue — explicit requests > automatic windows > idle backlog (D-4); round-robin per user within tiers; tier-1 fans one game's positions across the whole pool (~10s wall-clock, measured); replaces the LIFO id-DESC pick
- Hybrid demand UX (D-3) — automatic window (~200 recent games, <1 day catch-up measured) queued on import/activity; explicit "analyze more" affordance with progress; "(only analyzed games)" indicators
- PV capture at flaw-adjacent plies (D-7) — persisted so SEED-039's motif classifier needs no second engine pass later
- Flaw materialization follow-through — newly evaluated games flow through the existing `classify_game_flaws` path so Library/comparison features light up as analysis completes
- Pluggable-worker queue shape (D-8) — workers lease jobs and post evals, so browser/external workers can join later without redesign

**Key context:** All throughput numbers measured (spikes 001–003, Q-008 resolved): 5.83 positions/s on 6 SCHED_IDLE workers ≈ 8.4k games/day, zero API impact; full-DB idle drain ~66 days. Memory accounting against the backend container's 4g limit before raising `STOCKFISH_POOL_SIZE` is a known constraint. SEED-039 (tactic motifs) and SEED-037 (Train) stay out of scope — natural v1.27+ candidates.

### Backlog candidates (future-milestone candidates)

- [ ] **SEED-037 Train** — spaced-repetition blunder drills over the `game_flaws` archive (split from SEED-010; natural follow-on now that both-mover flaws are materialized)
- [ ] **SEED-039 tactic-family flaw tags** — the tactic-motif taxonomy that upgrades `miss` from proxy to literal `missed-fork` etc.; extends the v1.25 comparison backbone (FLAWTAC); consumes the PVs v1.26 captures
- [ ] **SEED-036 remainder** — the Analysis detail viewer (LIBG-04) + on-demand best-move endpoint (LIBG-05), deferred from v1.24; full spec in `.planning/seeds/SEED-036-library-page-milestone.md`
- [ ] **SEED-030 Track A** — split oversized multi-concern modules (structural code-health; Track B closed by Phase 99.1)
- [ ] Other dormant seeds: SEED-029 (benchmarks deterministic rebuild), SEED-033 (cap explorer + partial-index Zobrist hashes)

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

## Current State

v1.25 Flaw-Stats Opponent Comparison shipped to production 2026-06-12 — 4 phases (113, 114, 114.1, 115), 8 plans, released via PR #185 (`78c19514`). The Library flaw-stats panel is now a **you-vs-opponent comparison** instead of a self-only descriptive panel. **Phase 113** generalized the flaw classifier to persist both sides' mistakes/blunders in `game_flaws` (the classifier already evaluated both colors, so no extra engine cost), with the player/opponent split **derived at query time** via a single tested `is_opponent_expr(ply, games.user_color)` helper — no `is_opponent` column, no migration, no index (the original FLAWX-03 design was voided after the indexing premise proved false); every existing reader was retrofitted with a player-only gate so opponent rows don't leak into self-only views. **Phase 114** added a `/benchmarks` §5 chapter computing per-(metric, ELO×TC) Q1/Q3 quartile "typical" delta zones for all 15 flaw-delta metrics with ELO/TC marginals and per-axis Cohen's-d collapse verdicts (the lightweight delta-IQR zone, deliberately not the 99-breakpoint endgame CDF). **Phase 114.1** (inserted, SEED-041 §9) replaced `games.move_count` (±1 half-move accurate) with an exact `games.ply_count` via one migration, giving an exact per-game user-move denominator with zero `game_positions` access. **Phase 115** shipped the comparison surface: `GET /api/library/flaw-comparison` returning the full 15-bullet inventory via a **unified per-100-moves paired per-game delta** estimator with a bootstrap/normal CI — the SEED-040 count-rate-vs-proportion family split (and the Wilson difference-of-proportions method, FLAWCMP-02) was superseded by this single estimator during planning. The old tag-distribution zone was replaced by a uniform, family-grouped `MiniBulletChart` grid (measure + CI error bar + benchmark blue zone when available), with per-bullet tooltips disclosing definition, sign convention, tempo caveat, and the filter×zone interaction, plus a section-level sample gate. The feature ships for the ~37–51 heavy-analysis users; broader reach is gated on SEED-012 (coverage). Deferred to v2: tactic-motif comparison families (SEED-039) and coverage raising (SEED-012). Twenty-five milestones complete (v1.0–v1.25), live at flawchess.com. Next: `/gsd-new-milestone`.

v1.24 Library Page shipped 2026-06-09 — 9 phases (104–112), 37 plans, ~105 commits over 6 days (`a3585d6c` → `4192f4b9`). What began as a pure-frontend shell + route migration grew into the full analysis half of SEED-036: an eval-driven mistake/flaw archive over the user's analyzed games. **Phase 104** introduced the top-level **Library** page (Import + Overview folded in as deep-linkable URL-routed `<Tabs variant="brand">` subtabs; nav dropped to Library · Openings · Endgames (+ Admin); old routes redirect, `totalGames === 0` dot moved to Library, state-dependent landing). **Phases 105–106** built the on-the-fly mistake-detection kernel (per-ply severity from stored `eval_cp`/`eval_mate` via Lichess-aligned ES-drop thresholds + attribution tags, typed `FlawRecord`) and the two Games-surface endpoints. **Phase 107** shipped the Games subtab (filterable card archive + Flaw-Stats panel; now the returning-user default). **Phase 108** added the Flaws subtab backed by a materialized **`game_flaws`** table (composite PK `(user_id, game_id, ply)`, M+B-only), a per-flaw endpoint, a shared cross-tab Flaw filter, and `scripts/backfill_flaws.py` over a single classify path. **Phase 109** put a per-card expected-score eval chart on each analyzed Games card (inline payload, no new endpoint). **Phase 110** finalized the flaw-tag taxonomy (tempo `hasty`/`unrushed`, outcome-independent impact ladder `reversed`/`squandered`, canonical chip names + definition popovers under a codegen drift gate). **Phases 111–112** polished the filter UX into a staged Apply-only model and reworked the Flaws subtab into a 2-up `Card` grid with a View-game modal (new `GET /api/library/games/{game_id}`). Four Alembic migrations (create `game_flaws`, alter impact columns, rename `lucky`, drop display columns); `game_flaws` ships empty to prod. Deferred to a later phase (still in SEED-036): the Analysis detail viewer (LIBG-04) and the on-demand best-move endpoint (LIBG-05). Twenty-five milestones complete (v1.0–v1.24), live at flawchess.com. Next: `/gsd-new-milestone`.

v1.23 LLM Endgame-Insights Statistical-Reasoning Rework shipped 2026-06-03 — 2 phases (102, 103), 3 plans, 37 commits over 3 days (`3943b893` → `89403360`). Phase 102 reworked the endgame-insights LLM payload + prompt to reason over the v1.17–v1.21 statistical metric set and the v1.19 peer-relative percentile annotations: cohort-framed percentile rank woven into narration ("vs ~{anchor}-rated players"), time-pressure narration restored (Score Gap by Remaining Time, Clock Gap, Net Flag Rate), a relaxed Data Analysis overview cap that only fires longer with ≥3 distinct signals, and a vocabulary audit against the concepts accordion + tooltip popovers. The cohort `zone` field stays the sole gate on *whether* a metric is narrated (preserving `feedback_llm_significance_signal`); p-values + CI bounds stayed OUT. Prompt walked `endgame_v35` → `endgame_v43` across the auto-chain; HUMAN-UAT (LLM-07, the primary verification) signed off 2026-06-02 across short-history / sparse-section / full-history production users. Phase 103 (unplanned follow-on) applied three chess-GM recommendation-quality fixes — decision-speed time-trouble advice, no fabricated mechanism, no named theoretical positions at any Elo — added a fixed GM Noël Studer study link to the Recommendations card, and condensed the prompt ~35% (`endgame_v44`, payload shape unchanged). Phase 102 landed via local squash-merge (PR #173 closed); Phase 103 via direct gated commits. Twenty-four milestones complete (v1.0–v1.23), live at flawchess.com. Requirements LLM-01..07 all complete (archived at `.planning/milestones/v1.23-REQUIREMENTS.md`); REQUIREMENTS.md removed, fresh for the next milestone.

v1.22 Maintenance — Test Isolation & Frontend Major Upgrades shipped 2026-05-31 — 2 phases (100, 101), 3 plans, 31 commits in a single day (`45d882c7` → `db8eca80`). Phase 100 gave each `pytest` run (and each `pytest-xdist` worker) its own database cloned from a migrated template via `CREATE DATABASE … TEMPLATE`, retiring the hostile session-start `TRUNCATE … RESTART IDENTITY CASCADE` whole-schema lock; the template auto-refreshes on Alembic head drift under a `pg_advisory_lock`, killed runs self-heal, and `pytest -n auto` is now safe and 2.2x faster (18.56s vs 40.29s serial; CI stays serial). Phase 101 brought 11 majors-behind frontend deps to their latest major across six bisectable atomic clusters (lucide-react 1, Vite 8 + plugin-react 6, jsdom 29, eslint 10 stack, TypeScript 6, recharts 3), each gated so a failure bisects to one cluster; recharts 2 → 3 passed a desktop + mobile visual UAT after one zone-band regression was fixed and regression-tested, and the typescript-eslint ↔ TS6/eslint-10 peer-compat resolved cleanly. The window also folded in small direct-to-`main` backend maintenance (uv dep refresh + Dependabot clears, pydantic-ai-slim 1.85 → 1.104, Gemini 3 thinking-level support). Twenty-three milestones complete (v1.0–v1.22), live at flawchess.com. No formal requirements (both phases sourced from SEED-031 / SEED-032); REQUIREMENTS.md stays in place tracking the deprioritized LLM Statistical Reasoning scope (backlog Phase 999.7).

v1.21 Time-Control-Aware Endgame Metrics shipped 2026-05-31 — 4 phases (97, 98, 99, 99.1), 15 plans, delivered via PRs #160 (Phase 97), #163/#164 (Phase 98), #167 (Phase 99), #168 (Phase 99.1). The Endgames page is now time-control-honest end to end: the aggregated Conversion/Parity/Recovery cards became one card per TC (bullet/blitz/rapid/classical) with TC-specific Conv/Recov neutral bands (benchmark TC d≈0.9) and the shared global band on Parity + Score Gap; the Endgame Type Breakdown became full-width collapsible per-TC accordion cards with the user's primary (time-weighted) TC expanded by default, each holding a 2×2 grid of rook/minor_piece/pawn/queen tiles (Mixed dropped) with Conv/Recov gauges restored on per-(class × TC) bands; and peer-relative percentile chips landed on the per-TC Conversion/Parity/Recovery rates (12 new per-(metric, TC) cohort metrics via the pooled-per-user builder). Phase 99.1 then relocated the 3.1 MB generated `COHORT_PERCENTILE_CDF` registry out of Python source into a `benchmark_cohort_cdf` DB table (module ~130k → ~250 lines, byte-for-byte chip parity, no behaviour change), closing SEED-030 Track B. Prod backfill of the 12 new rate-percentile metrics is deferred to deploy. v1.20 (Phases 95, 96 — asyncpg COPY + Import Readiness Gate) shipped 2026-05-29. Twenty-two milestones complete (v1.0–v1.21), live at flawchess.com; next is v1.22 Maintenance — Test Isolation & Frontend Major Upgrades (Phases 100, 101). The LLM Statistical Reasoning rework is deprioritized to backlog Phase 999.7.

v1.19 Endgame Percentiles shipped 2026-05-27 — 6 phases (93, 94, 94.1, 94.2, 94.3, 94.4), ~45 plans, delivered through PR #145 plus earlier per-phase PRs. Peer-relative percentile chips are now live on the Endgames page: per-(metric, ELO anchor, TC) cohort CDFs built from 50-Elo sliding windows replace the global pool; per-(user, TC) rating anchors use a game-weighted blended median over converted-chess.com + native-lichess games (D-12 reversal); the chip face shrinks to a bare `p23` pill with a 4-bullet tooltip that discloses the rating anchor + per-platform composition; chips are a *trait* of the user computed once per Stage A/B trigger and independent of UI filter state. The Time Pressure section gains 12 per-TC chips (3 per `TimePressureTcCard`). Phase 95 (LLM Statistical Reasoning) was split into v1.20 before milestone close. SEED-019 closed; SEED-025 + SEED-026 v2 closed. Nineteen milestones complete (v1.0–v1.19), live at flawchess.com.

v1.18 Import Pipeline Hardening shipped 2026-05-22 — 3 phases (90, 91, 92), 17 plans, 54 commits over 3 days (commit 114211c2 → f5224b4f), delivered via PRs #130, #137, #138 + production hotfix #139 (FLAWCHESS-3Q DB pool / max_connections / container memory caps and Hetzner CPX32 → CPX42). Two prod OOM recurrences in the v1.17 → v1.18 gap drove the milestone: the per-batch unique-SQL leak in `_flush_batch` Stage 5 (`case()` + `IN` against a literal bind set) was replaced with bound-parameter `executemany`; the hot import path now holds no Stockfish work (a separate `run_eval_drain()` lifespan coroutine picks 10 games per tick from a partial index `WHERE evals_completed_at IS NULL` and evaluates outside any session scope); a Stockfish-coverage header bar and per-metric "based on N of M eligible games" caveat on every eval-dependent stat surface the cold lane's progress honestly. The closed `Recency` string union was replaced on the API wire with `from_date` / `to_date` params (Phase 92), with a 9th "Custom range…" entry in the recency dropdown backed by shadcn Calendar (desktop Popover, mobile nested Drawer). Seeds SEED-017 / SEED-018 / SEED-022 / SEED-023 closed in this milestone.

v1.17 Endgame Stats Card Redesign shipped 2026-05-19 — 13 phases (84, 85, 85.1, 86, 87, 87.1, 87.2, 87.4, 87.5, 87.6, 88, 88.3, 88.4), ~54 plans, 203 commits over 8 days, delivered via PRs #89–#117. The three table-driven Endgames-page sections (`EndgamePerformanceSection`, `EndgameScoreGapSection`, grouped `EndgameWDLChart`/`EndgameConvRecovChart`) are gone, replaced by the WDL + ScoreBullet card pattern. What began as a layout refactor became a statistical-rigor pass: the rate-based mirror-bucket peer-diff bullet (mathematically degenerate — Conv-Gap ≡ Recov-Gap by mirror symmetry) was retired for an eval-based per-span ΔES Score Gap anchored to the Stockfish baseline; Endgame Score Differences gained two-sample z + paired one-sample z hypothesis tests with 95% CI whiskers; the Endgame Skill concept was dropped entirely and the timeline rebuilt as Endgame ELO via a logistic stretch around Actual ELO (`endgame_elo + non_endgame_elo == 2·actual_elo`, fixing the sigmoid bias and the violated "Actual ELO between the lines" invariant); Time Pressure was reworked with benchmark-calibrated `PRESSURE_BIN_SCORE_NEUTRAL_ZONES` and a zone-banded zero-centered line chart; and all 6 ordinal-axis timeline charts gained inactivity-gap break annotations. Phase 89 (Polish) dropped from scope; 87.3 percentile composite superseded by 87.4→87.6. LLM endgame prompt advanced `endgame_v26` → `endgame_v35` across the milestone.

v1.16 Stockfish Eval Analyses shipped 2026-05-11 — 5 phases (80, 80.1, 81, 82, 83), 24 plans, 118 commits over 7 days, delivered via PRs #80, #82, #85, #86, #88. 80 phases before v1.17 (+5 inserted: 27.1, 28.1, 41.1, 57.1, 71.1, plus mid-milestone 80.1).

The Endgame Start vs End section above the Endgame Overall Performance WDL table is now a 2×2 grid: rows are "Where you start" (entry eval, in pawns) and "What you do with it" (achieved endgame score); columns are Stockfish baseline (predicted via Lichess sigmoid `1/(1+exp(-k·cp))`, k=0.00368208) and the user's measured value. Each tile carries a sig-tested verdict (Wald-z for entry eval vs 0; Wilson for endgame_score vs 50%; Wilson for entry_expected_score vs achieved endgame_score) with three-state color and `n ≥ 10` reliability gate; mobile stacks chronologically setup → execution. LLM narration (`endgame_v26`) frames the achievable-vs-achieved gap as the headline diagnostic and uses tightened cohort bands (entry_eval_pawns ±0.5; endgame_score [0.45, 0.55]) so borderline-but-significant findings land in `zone="typical"` and stay silent. The aggregation runs against `query_endgame_bucket_rows` (one row per game, eval at chronologically first endgame position) so `entry_eval_n + mate_excluded + null_excluded == endgame_wdl.total` by construction.

Phase 80 ships the Opening Stats subtab eval column with t-test confidence pill and CI-whisker MiniBulletChart on both bookmarked and most-played tables; the table layout was later replaced by a two-column card grid in quick task `260506-rtk`. Phase 80.1 swapped WDL/score/confidence/p_value on Move Explorer rows and Opening Insights findings from move-played to resulting-position (transposition-inclusive) via the new `query_transposition_wdl` + `query_resulting_position_wdl` repo helpers; `game_count` and the n≥10 surfacing gate stay move-played for honest disclosure. SEED-014 (Stockfish-baseline expected score for endgame entries) closed by Phase 83; follow-up gap-as-first-class-metric work tracked in SEED-015.

v1.15 replaced the material-imbalance + 4-ply persistence proxy for endgame conversion / parity / recovery classification with direct Stockfish-eval thresholding (±100 cp on `eval_cp` after color-sign flip; `eval_mate` short-circuits to ±1,000,000 cp). Hard cutover — `_MATERIAL_ADVANTAGE_THRESHOLD`, `PERSISTENCE_PLIES`, and the `array_agg(... ORDER BY ply)[PERSISTENCE_PLIES + 1]` contiguity case-expression deleted from the codebase. `material_imbalance` column retained for other consumers. Closes the structural gap on Queen and pawnless classes where the proxy underperformed (~24% miss rate on substantive material-edge sequences per the 2026-05-02 baseline). Stockfish is shipped via a pinned binary in the backend Docker image (sf_17 → sf_18 with SHA-256 supply-chain verification); `app/services/engine.py` is the single async wrapper consumed by both `scripts/backfill_eval.py` and the import path. Module-level `EnginePool` of `STOCKFISH_POOL_SIZE` workers (prod ships 2) parallelises the import-time eval pass via `asyncio.gather`. Alembic `c92af8282d1a` reshapes `ix_gp_user_endgame_game INCLUDE` from `material_imbalance` to `eval_cp` / `eval_mate` so endgame queries stay index-only. `_classify_endgame_bucket(eval_cp, eval_mate, user_color)` is the single classification helper.

Phase 79 added a per-position `phase` SmallInteger column on `game_positions` (0=opening, 1=middlegame, 2=endgame) computed via Python port of lichess `Divider.scala` using existing `piece_count`, `backrank_sparse`, `mixedness` inputs (no second board scan). 11 Divider-sourced parity assertions lock output to the lichess reference on a curated FEN fixture set. The middlegame-entry position (`MIN(ply)` of `phase = 1` per game) is also Stockfish-evaluated at depth 15 alongside endgame span-entry positions, populated into the same `eval_cp` / `eval_mate` columns. The combined Phase 78 + Phase 79 backfill ran on benchmark first, then prod, in a single operator cutover (D-79-10) — substrate now in place for v1.16 opening-stats analyses.

VAL-01 / PHASE-VAL-01 (re-run `/conv-recov-validation` post-backfill for ~100% agreement) were rescinded as moot once REFAC-03 deleted the proxy code path: agreement metric becomes undefined when there's only one classifier. The `/conv-recov-validation` skill was deleted on 2026-05-03.

Inline quick tasks during the milestone window: 260501-s0u rebuilt the endgame UI from a benchmark report (clock-pressure neutral band ±10pp → ±5pp; recovery typical band [25%, 35%] → [25%, 40%]; six per-class Conversion/Recovery mini-gauges replaced the grouped WDL bar chart; LLM endgame insights prompt v18 reframes Conv/Recov as delta-from-class-baseline). 260503 recalibrated gauge typical bands from the 2026-05-03 benchmark report. 260503-fef applied an equal-footing opponent filter (`abs(opp_rating - user_rating) ≤ 100`) to the `/benchmarks` skill so population baselines reflect peer-vs-peer matchups.

v1.14 Score-Based Opening Insights shipped 2026-04-29 (PRs #69, #70, #71, #72, #73).

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

- **Current state:** v1.24 Library Page shipped 2026-06-09. 25 milestones complete (v1.0–v1.24); ~32k LOC backend (`app`), ~48k LOC frontend (`frontend/src`). Live at flawchess.com with CI/CD and Sentry.
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
| Hard cutover for endgame classification (v1.15 REFAC-03) | Removed the proxy code path entirely rather than running both side-by-side. The validation report had already established the proxy's structural ceiling on queen + pawnless classes; a fallback would have re-introduced the failure mode for any game without lichess `%eval` annotation | ✓ Good |
| `_classify_endgame_bucket(eval_cp, eval_mate, user_color)` as single classification helper | SQL projects raw white-perspective eval; service layer applies user-color sign flip. Mate scores short-circuit to ±1,000,000 cp so the same threshold handles both | ✓ Good |
| Pinned Stockfish binary in backend Docker image with SHA-256 verification | Supply-chain verification on a binary that runs as a long-lived UCI process — not a per-call subprocess fork. CI runner installs `stockfish` via apt so engine wrapper tests run | ✓ Good |
| Module-level `EnginePool` over per-call engine spawn | Parallelises the import-time eval pass via `asyncio.gather` with `STOCKFISH_POOL_SIZE` workers; sequential callers see no change. Default 1 outside prod, prod ships 2 via `docker-compose.yml` | ✓ Good |
| FILL-02 relaxed mid-plan (drop `full_hash` dedup) | Row-level idempotency only via `WHERE eval_cp IS NULL AND eval_mate IS NULL`. Hash dedup added complexity for marginal CPU savings on a one-shot backfill | ✓ Good |
| `phase` SmallInteger column via Python port of lichess `Divider.scala` | Reuses existing `piece_count`, `backrank_sparse`, `mixedness` per-position fields — no second python-chess board scan. 11 Divider parity tests lock output to the lichess reference | ✓ Good |
| Combined Phase 78 + Phase 79 operator cutover (D-79-10) | Single benchmark + prod backfill pass, single PR #78, single deploy. Saved an operational round-trip and consolidated the deployment risk window | ✓ Good |
| VAL-01 / PHASE-VAL-01 rescinded as moot post-cutover | The `/conv-recov-validation` skill compared proxy vs eval on the populated subset; once the proxy was deleted, the agreement metric became undefined. Skill deleted 2026-05-03 | ✓ Good |
| Endgame UI calibration shipped as inline quick tasks (260501-s0u, 260503), not a separate phase | v1.15 milestone scope was strictly backend; UI gauge recalibration ran inline against the new benchmark report rather than blocking the cutover | ✓ Good |
| Mid-milestone Phase 80.1 inserted (transposition WDL fix) | The 57%→61% mismatch surfaced during Phase 80 UAT was a loud UX bug; cheaper to fix in-milestone than carry into v1.17 | ✓ Good |
| `entry_eval_n` aggregated against `query_endgame_bucket_rows`, not per-class entry_rows (Phase 81 D-22) | UAT against user 28 surfaced a ~5-game under-count when summing per-class entry rows; bucket_rows gives one row per game at chronologically first endgame position, locking `n + mate + null == total` by construction | ✓ Good |
| Cohort band on `entry_eval_pawns` tightened IQR ±0.75 → ±0.5 (Phase 82 D-08) | Avoids over-narrating small-but-significant findings; the user-28 pattern now correctly lands in `zone="typical"` and stays silent on both tile and LLM | ✓ Good |
| No `verdict` field on `SubsectionFinding` (Phase 82 D-06, Phase 83 D-19) | Significance independent of cohort would license LLM over-narration; tighten cohort band instead — matches memory `feedback_llm_significance_signal.md` | ✓ Good |
| Lichess sigmoid k=0.00368208 for eval → expected score (Phase 83) | Same constant Lichess uses to color their eval bars; established mapping, no need to retune. `eval_mate` short-circuits to ±1.0 expected score | ✓ Good |
| 2x2 grid restructure of Start vs End over inserting a third tile (Phase 83) | Stockfish baseline + user achieved now share the same units (W+0.5D ∈ [0,1]) and same visual idiom; the achievable-vs-achieved gap is visually readable instead of requiring LLM prose to translate centipawns → score | ✓ Good |
| Forbidden-word guarding in prompt assets via regression test scanning the prompt file (Phase 83) | Single source of truth: any narration-guidance line using a forbidden term fails CI before the prompt ships | ✓ Good |
| Single-bullet doctrine — one peer bullet per Conv/Parity/Recov + Section 3 card (v1.17 Phase 84 pivot) | Cohort/p50 bullets were a rating-tier confound roughly redundant with ELO; one self-calibrating peer frame per card is cleaner | ✓ Good |
| Eval-based ΔES Score Gap replaces rate-based mirror-bucket peer-diff (v1.17 Phase 87.2) | The rate-based peer-diff was mathematically degenerate: Conv-Gap ≡ Recov-Gap by mirror symmetry, Parity-Gap an affine of `user_parity` — two rows, one signal | ✓ Good |
| Endgame Skill concept dropped entirely (v1.17 Phase 87.4) | No composite definition (mean / percentile / rate aggregate) survived cohort-deconfound + individual-interpretation + temporal-stability + median-coincide scrutiny | ✓ Good |
| Endgame ELO = logistic stretch around Actual ELO, `eg_elo + non_eg_elo == 2·actual_elo` (v1.17 Phase 87.6) | Additive-K and FIDE-PR mappings both broke the "Actual ELO between the lines" invariant (~88% of points) and carried sigmoid bias; the stretch is symmetric and invariant-preserving by construction | ✓ Good |
| Time-pressure zones calibrated from the Lichess benchmark cohort, pooled across ELO within (TC, quintile) (v1.17 Phase 88) | Benchmarks are the source of truth for "typical"; the within-band ELO gradient (stronger players greener) is intended, not noise | ✓ Good |
| Phase 89 (Polish) dropped at v1.17 close | Popover/gating/automation/375px-parity polish was absorbed incrementally across the inserted phases' UAT cycles; a dedicated phase added no remaining value | — Pending |
| Per-TC Conv/Recov bands but shared Parity/Score Gap band (v1.21 Phase 97) | Benchmark Cohen's d ≈ 0.9 on the TC axis for Conv/Recov (they genuinely differ per speed) vs d < 0.15 for Parity/Score Gap (collapse on TC, so one band is correct everywhere) | ✓ Good |
| Per-(class × TC) bands with no TC-mix blending; Mixed dropped from type tiles (v1.21 Phase 98) | Each single-TC card judged against that TC's own reference is the TC-honest replacement for the superseded blended-band approach; Mixed is the least-actionable catch-all and its WDL tracks the overall endgame number | ✓ Good |
| Score Gap banded per-TC despite being TC-flat (v1.21 Phase 98) | One consistent per-tile card grammar beats hoisting a single band that breaks per-TC cohesion; the four near-identical bands are a known, chosen redundancy | ✓ Good |
| Generated cohort CDF demoted from Python source to `benchmark_cohort_cdf` DB table (v1.21 Phase 99.1) | A 3.1 MB / ~130k-line generated dict parsed into the heap on every process start is maintainability debt; the lookup is background-only so a sync interpolator over a batched-prefetched table is sufficient. Closes SEED-030 Track B | ✓ Good |
| Player/opponent flaw split derived at query time, not stored as an `is_opponent` column (v1.25 Phase 113, voids FLAWX-03) | `is_opponent` is ~50% selective (no useful index) and a `GROUP BY` dimension, not a selective filter; the existing PK `(user_id, game_id, ply)` already covers two-sided per-game reads. A single tested `is_opponent_expr(ply, user_color)` helper keeps the fragile ply-parity convention in one place — no column, no migration, no index | ✓ Good |
| Unified per-100-moves paired per-game delta estimator for all 15 flaw metrics (v1.25 Phase 114/115, voids FLAWCMP-02) | SEED-040's count-rate-vs-proportion family split (paired delta vs Wilson difference-of-proportions) added complexity for no benefit; one estimator + one CI method across the whole grid is simpler and keeps the benchmark zone portable across ELO cells | ✓ Good |
| Lightweight delta-IQR benchmark zone (Q1/Q3 per ELO×TC), not a 99-breakpoint percentile CDF (v1.25 Phase 114) | The CDF cost trajectory does not survive the future SEED-039 tactic-motif roadmap (would need Stockfish PVs across millions of cohort games per motif); two quartiles of one derived metric per cell is enough to anchor a "typical" zone | ✓ Good |
| Exact `games.ply_count` replaces `move_count` (v1.25 Phase 114.1, SEED-041 §9) | `move_count` (full-move count) pins the half-move total only to ±1, blocking an exact per-game user-move denominator without a 190M-row `game_positions` scan; storing exact `ply_count` gives the denominator with zero positions access and speeds both the §5 chapter and the live endpoint | ✓ Good |

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
*Last updated: 2026-06-12 — v1.26 Full-Game Eval Pipeline milestone opened (sourced from SEED-012's server-first v1 amendment; continues at Phase 116). Server-side all-ply Stockfish drain at Lichess parity (1M nodes NNUE, measured 0.98s/position on prod, 5.83 pos/s on 6 SCHED_IDLE workers ≈ 8.4k games/day with zero API impact — spikes 001–003, Q-008 resolved): tiered priority queue (explicit > auto windows > idle backlog, round-robin per user, tier-1 position fan-out ≈ 10s/game), hybrid demand UX (~200-game auto window, <1 day catch-up), evals into `game_positions` with ply≤20 dedup, PV capture at flaw-adjacent plies for SEED-039, flaw-classification follow-through, pluggable-worker queue shape for future browser workers. Out of scope: SEED-039 motif classifier, SEED-037 Train, client-side workers. (Prior footer below.)*

*Last updated: 2026-06-12 after v1.25 Flaw-Stats Opponent Comparison milestone shipped to production (Phases 113, 114, 114.1, 115; tag v1.25; PR #185, `78c19514`). The Library flaw-stats panel is now a you-vs-opponent comparison: both-mover `game_flaws` materialization with a query-time `is_opponent_expr` split (no `is_opponent` column — FLAWX-03 voided), a `/benchmarks` §5 chapter of per-(ELO×TC) Q1/Q3 flaw-delta "typical" zones with Cohen's-d collapse verdicts, an inserted `move_count`→exact `ply_count` swap (SEED-041 §9), and a `GET /api/library/flaw-comparison` endpoint feeding a family-grouped 15-bullet `MiniBulletChart` grid. The SEED-040 count-rate/proportion family split was superseded by a single unified per-100-moves paired-delta estimator (FLAWCMP-02 Wilson method voided). Ships for the ~37–51 heavy-analysis users; broader reach gated on SEED-012. Deferred to v2: tactic-motif families (SEED-039), coverage raising (SEED-012). No active milestone follows; next is `/gsd-new-milestone` (leading candidates: SEED-037 Train, SEED-039 tactic-motif tags, or the SEED-036 remainder). (Prior footer below.)*

*Last updated: 2026-06-09 — v1.25 Flaw-Stats Opponent Comparison milestone opened (sourced from SEED-040; continues at Phase 113). Reworks the Library flaw-stats panel from self-only descriptive stats into a you-vs-opponent comparison: per flaw tag, one bullet chart = the you−opponent frequency delta + a real CI + a lightweight benchmark "typical" zone (per-(ELO×TC) IQR of that delta, not full percentiles). Spine: opponent-flaw materialization (add `is_opponent`, drop the player-only filter — nearly free, no engine cost) → benchmark backfill + `/benchmarks` extension (delta quartiles + Cohen's-d collapse verdict per flaw-delta metric) → API + ~13-bullet UI grid reusing `MiniBulletChart`. Two CI methods by design: paired per-game rate-deltas/100-moves (count families: Flaw Rate, tempo, phase) vs Wilson difference-of-proportions (`miss`/`lucky`/`reversed`/`squandered`). Out of scope: eval-coverage raising (Q-007 bottleneck — ships for the ~37–51 heavy-analysis users, coverage stays SEED-012's job) and tactic-motif bullets (SEED-039, cohort-PV cost). Already done upstream: the `game_flaws` table (v1.24 Phase 108), impact-tag threshold recalibration (`35f742af`/`4192f4b9`), the bullet component (SEED-021). (Prior footer below.)*

*Last updated: 2026-06-09 after v1.24 Library Page milestone (Phases 104–112; tag v1.24). The Library shipped as a full eval-driven mistake/flaw archive: Import/Overview folded into deep-linkable subtabs, on-the-fly mistake-detection kernel + materialized `game_flaws` table, Games and Flaws subtabs, per-card expected-score eval charts, a finalized flaw-tag taxonomy (`hasty`/`unrushed`, `reversed`/`squandered`), a cross-tab Flaw filter, and an Apply-only filter model. What started as a pure-frontend Phase-104 shell grew into a 9-phase full-stack milestone. Deferred to a later phase (still in SEED-036): the Analysis detail viewer (LIBG-04) + best-move endpoint (LIBG-05). Phase 111 (Library UI polish) shipped via direct commits with no GSD plan artifacts. No active milestone follows; next is `/gsd-new-milestone` (leading candidate: SEED-036 remainder or SEED-037 Train over the new `game_flaws` archive). (Prior footer below.)*

*Last updated: 2026-06-05 — v1.24 Library Page milestone opened. First phase only: create the `/library` page shell with the Openings-style URL-routed subtab pattern and fold the existing Import and Overview pages in as their own-tsx subtabs (`/import` → `/library/import`, `/overview` → `/library/overview`, with redirects); top-level nav drops to Library · Openings · Endgames · (Admin) and the zero-games notification dot moves to the Library nav item. The remaining SEED-036 scope (Games/Analysis subtabs, mistake-detection backend, mistake-type filter, mistake-stats panel, best-move endpoint) is deliberately left unplanned. (Prior footer below.)*

*Last updated: 2026-05-31 — after v1.22 Maintenance — Test Isolation & Frontend Major Upgrades milestone (Phases 100, 101; tag v1.22). Per-run/per-xdist-worker template-cloned test DB retiring the session-start TRUNCATE lock (`pytest -n auto` safe, 2.2x faster), and 11 frontend deps brought to latest major across six bisectable atomic clusters (recharts 3 visual-UAT'd). No active milestone follows; next is `/gsd-new-milestone` (leading candidate: backlog Phase 999.7 LLM Statistical Reasoning). (Prior footer below.)*

*Last updated: 2026-05-31 — after v1.21 Time-Control-Aware Endgame Metrics milestone (Phases 97, 98, 99, 99.1; tag v1.21). The Endgames page is now time-control-honest end to end: per-TC Endgame Metrics cards (TC-specific Conv/Recov bands, shared Parity/Score Gap band), collapsible per-TC Endgame Type Breakdown cards (2×2 type tiles, Mixed dropped, per-(class × TC) bands), peer-relative percentile chips on the per-TC Conv/Parity/Recov rates (12 new per-(metric, TC) cohort metrics), and the generated cohort-CDF lookup demoted from Python source (~130k lines) to a `benchmark_cohort_cdf` DB table (SEED-030 Track B closed). Prod backfill of the 12 rate-percentile metrics deferred to deploy. The v1.20→v1.21 "Current Milestone" header drift flagged at the prior close is now reconciled: header points to v1.22 LLM Statistical Reasoning (Phase 100). (Prior footer: 2026-05-31 mid-v1.21, Phase 99 complete — 3 TC-parameterised pooled-per-user rate builders, 12 new `benchmark_metric` ENUM values via migrations `3981239fd391` / `52c928794fe7`, COHORT_PERCENTILE_CDF regenerated against the benchmark DB snapshot 2026-05-30.)*

*Previous: 2026-05-19 after v1.17 milestone. v1.17 Endgame Stats Card Redesign shipped — 13 phases (84–88.4), ~54 plans, delivered via PRs #89–#117. Phase 89 (Polish) dropped from scope; Phase 87.3 (percentile composite) superseded by 87.4→87.6.*

*Previous: 2026-05-12 — v1.17 (Endgame Stats Card Redesign) opened. Frontend-only refactor (with Phase 84 as the lone backend touch) replacing 3 table-driven sections on the Endgames page with the WDL+ScoreBullet card pattern.*

*Previous: 2026-05-11 after v1.16 milestone — Stockfish Eval Analyses shipped (PRs #80, #82, #85, #86, #88). 5 phases (80, 80.1, 81, 82, 83), 24 plans, 118 commits in 7 days. SEED-014 closed by Phase 83; SEED-015 (predicted-vs-achieved gap as first-class metric) remains dormant.*

*Previous: 2026-05-09 — Phase 81 (Endgame Start vs End twin-tile section) complete. UAT against user 28 surfaced D-22 amendment switching entry-eval source from per-class entry_rows to game-level bucket_rows, eliminating a ~5-game under-count and locking the n + mate + null + total invariant by construction.*
