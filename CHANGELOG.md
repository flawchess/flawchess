# Changelog

All notable changes to FlawChess are documented here.

The format is inspired by [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
with releases aligned to GSD milestones rather than individual phases. Dates are
in `YYYY-MM-DD` (Europe/Zurich).

## [Unreleased]

### Fixed
- PRE-01: Top-10 most-played openings now include opponent-defined openings (e.g. `vs. Caro-Kann Defense: Hillbilly Attack` for a Black user) which were previously hidden by a ply-parity filter. Off-color rows render with a `vs. ` prefix; same-color rows are unchanged.

## [v1.11] LLM-first Endgame Insights — 2026-04-24

First LLM-backed feature. On-demand Endgame Insights via `POST /api/insights/endgame`,
backed by a deterministic findings pipeline, a generic `llm_logs` Postgres table,
and a dual-line Endgame vs Non-Endgame Score timeline chart. Phase 67
(Validation & Beta Rollout) was descoped — insights shipped to all users rather
than behind a beta cohort flag.

### Added
- LLM-backed endgame insights endpoint (`POST /api/insights/endgame`) returning a structured `EndgameInsightsReport` (overview + up to 4 section insights). Cached on a findings hash, rate-limited to 3 misses/hr/user, soft-fails to the last cached report (Phase 65).
- Phase 63: Findings pipeline foundation for LLM Endgame Insights — deterministic `compute_findings` service produces per-subsection-per-window `EndgameTabFindings` with zone, trend, and sample-quality annotations over the existing `/api/endgames/overview` data
- Phase 63: Shared zone registry (`app/services/endgame_zones.py`) as the single source of truth for thresholds and the 3-zone schema (weak/typical/strong) that backs both narrative and chart visuals
- Phase 63: Python→TypeScript zone codegen (`scripts/gen_endgame_zones_ts.py`) with CI drift guard so frontend gauge constants can never silently diverge from the Python registry
- Phase 64: Generic `llm_logs` Postgres table (18 columns, BigInteger PK, JSONB for filter_context/flags/response_json, FK CASCADE to users) with 5 indexes, designed to host every future LLM feature (not endgame-specific)
- Phase 64: Async `LlmLogRepository.create_llm_log` that opens its own session scope, so log rows persist even when the caller's request-scoped transaction rolls back; `get_latest_log_by_hash` stub ready for Phase 65's findings-hash cache
- Phase 64: Automatic per-call cost accounting via `genai-prices` with `LookupError` soft-fallback (`cost_usd=0`, `error=cost_unknown:<model>`) so unknown models never break logging

### Changed
- `SubsectionFinding` gains optional `series: list[TimePoint] | None` for the four timeline subsections, populated with weekly (last_3mo) or monthly weighted-mean (all_time) resampled points (Phase 65).
- Phase 63: Recovery gauge typical band re-centered to 0.25–0.35 per D-10 (previously 0.3–0.4)
- Endgame insights prompt bumped to `endgame_v6`: rate/percent metrics rendered on the 0-100 scale end-to-end so narration matches the page (no more `0.65` prose next to `65%` charts); pawnless findings filtered from the LLM payload to match the hidden UI row; system prompt rewritten with a UI-vocabulary block, a `win_rate`-citation ban, and rules for staleness, latest-bucket anchoring, activity-gap narration, intra-type asymmetry hunting, grounding checks, and within-noise delta handling.
- Endgame insights payload now ships precomputed signals so the LLM stops redoing math: `## Payload summary` header, `STALE:` markers on series trailing >6mo behind the newest bucket, `# trend:` direction tags under every series, `# asymmetry` flags on opposing-zone Conversion/Recovery pairs per endgame type, `# low-time gap` scalar on the time-pressure chart, `# delta` annotations for paired all_time↔last_3mo scalars with a `within-noise` flag on small-sample shifts.
- Endgame insights prompt bumped to `endgame_v7`: all rate/percent values rendered as whole-number `%` in both prompt and UI (drops the confusing `pp` unit); `net_timeout_rate` switched to `higher_is_better` with no internal sign flip (positive raw = strong, matching the UI's coloring); the within-noise rule promoted to a global constraint that binds the overview paragraph text as well as bullets; new precomputed tags (`# weakest type`, `# recovery pattern`, `[near edge]` proximity hints inline on bullets); flat-trend series collapsed to a single stable-around line; stale `endgame_elo_gap` combo series blocks dropped when a live combo exists; redundant `last_3mo` scalar bullets dropped when the delta is within-noise; prompt intensifier forbidden list expanded to block "severe"/"critical"/"drastic"-style overclaims; system prompt redundancy trimmed and Series-interpretation rules consolidated.
- Endgame insights prompt bumped to `endgame_v9`: `EndgameInsightsReport` gains first-class `player_profile` (paragraph) and `recommendations` (2-4 short bullets) fields, surfaced as stacked top-of-page cards above the data-analysis overview; recommendations are allowed to be more directive than the overview but stay grounded in weak/typical-zone metrics with a register calibrated to the most-played combo's Elo (theory jargon ≥1200, named positions ≥1800). The `score_gap` scalar bug is fixed: the misleading `score_gap (all_time)` bullet inside `score_gap_timeline` (which was actually the latest weekly-bucket value mislabeled as an aggregate) is dropped, and the `## Subsection: overall` scalar always emits alongside the `overall_wdl` chart so the all-time number matches the chart row math. Payload format cleaned up: dropped the always-on `Filters:` header (only `## Scoping caveat` remains, when opponent_strength is set) and the redundant `Conversion/Recovery asymmetries detected: N` count.
- Endgame page: "Time Pressure at Endgame Entry" table and mobile cards gain a weighted "All time controls" aggregate row when multiple time controls are present, mirroring the weighted mean the LLM narrates so users can reconcile the written summary with the visible data.
- Phase 68: Endgame tab now shows a dual-line "Endgame vs Non-Endgame Score over Time" chart (both absolute Score series, with a shaded band between them, green when endgame leads, red when it trails) in place of the old single-line "Score Gap over Time" chart. The backend subsection was renamed from `score_gap_timeline` to `score_timeline` and now emits three findings per window — one each for `endgame_score`, `non_endgame_score`, and `score_gap` — each with its own `[summary …]` + `[series …]` block (deterministic order: endgame_score, non_endgame_score, score_gap). Prompt bumped to `endgame_v14`, dropping the now-redundant `score_gap` framing rule (the two-line chart makes gap composition self-evident) and introducing a `[n=<N> for every point]` disclosure that replaces per-point `(n=<N>)` suffixes when N is constant across a series. The info popover drops the "Score Gap is a comparison, not an absolute measure" caveat.
- v1.11 cleanup pass: `endgame_v15` prompt bump drops the stale `Filters:` header reference from the `avg_clock_diff_pct` glossary entry (the header itself was removed in v9). Zone-threshold consolidation finishes the Phase 66 switchover — three chart components now import numeric zone boundaries from `frontend/src/generated/endgameZones.ts` (codegen'd from `app/services/endgame_zones.py`) instead of maintaining inline duplicates; gauge band colors moved to `frontend/src/lib/theme.ts`.

## [v1.10] Advanced Analytics — 2026-04-19

Endgame-focused advanced analytics pass: score gaps, material breakdowns,
time-pressure analysis, skill-adjusted Endgame ELO, plus test hardening and
admin impersonation.

### Added

- Endgame Score Gap & Material Breakdown — signed endgame vs non-endgame score
  difference plus material-stratified WDL table (Conversion / Parity / Recovery)
  with Good / OK / Bad verdict calibration (Phases 53, 59).
- Opponent-based self-calibrating baseline for Conv / Parity / Recov bullet
  charts — opponent's rate against the user replaces global average, muted when
  sample < 10 games (Phase 60).
- Time pressure analytics — per-time-control clock stats table (Phase 54) and
  two-line user-vs-opponents score chart across 10 time-remaining buckets with
  backend aggregation (Phase 55).
- Endgame ELO Timeline — skill-adjusted rating per (platform, time-control)
  combination with paired Endgame ELO / Actual ELO lines, asof-join anchor on
  user's real rating, weekly volume bars for data-weight transparency (Phases
  57, 57.1).
- Admin user impersonation — superusers can impersonate any user via new
  `/admin` page with shadcn Command+Popover search, single `auth_backend` +
  `ClaimAwareJWTStrategy` wrapper (zero call-site changes), last_login /
  last_activity frozen during impersonation, persistent impersonation pill in
  header (Phase 62).

### Changed

- Endgame tab performance — 8 per-class timeline queries collapsed into 2,
  consolidated `/api/endgames/overview` serving every endgame chart in one
  round trip on a single `AsyncSession`, deferred filter apply on desktop
  (Phase 52).
- Conversion / recovery persistence filter — material imbalance required at
  endgame entry AND 4 plies later, threshold lowered 300cp → 100cp, validated
  against Stockfish eval analysis (Phase 48).
- Sentry Error Test moved from Global Stats to Admin tab; superuser-gated nav
  entry.

### Tests

- Test suite hardening — `flawchess_test` TRUNCATE on session start,
  deterministic 15-game `seeded_user` fixture, aggregation sanity tests (WDL
  perspective, material tally, rolling windows, filter intersections, recency
  boundaries, within-game dedup, endgame transitions), router integration tests
  asserting exact integer counts (Phase 61).

## [v1.9] UI/UX Restructuring — 2026-04-10

Responsive sidebar restructuring for Openings, mobile control-row alignment,
Stats subtab redesign, and a global Stats → Global Stats rename with opponent
filters wired end-to-end.

### Added

- Openings desktop sidebar — collapsible left-edge 48px icon strip + 280px
  on-demand Filters / Bookmarks panel with overlay / push behavior at the
  1280px breakpoint, live filter apply on desktop.
- Openings mobile unified control row — Tabs | Color | Bookmark | Filter
  lifted outside the board collapse region so controls stay visible when the
  board is collapsed; 44px tappable collapse handle; backdrop-blur translucent
  sticky surface.
- Global Stats filters — `opponent_type` and `opponent_strength` wired
  end-to-end through `/stats/global` and `/stats/rating-history`, bot games
  excluded by default.

### Changed

- Endgames mobile visual alignment — 44px backdrop-blur sticky row with 44px
  filter button matching the Openings mobile pattern.
- Stats subtab layout — 2-column Bookmarked Openings: Results on desktop (lg
  breakpoint), stacked WDLChartRows for mobile Most Played replacing the
  cramped 3-col table.
- Homepage 2-column desktop hero — left = hero content, right = Interactive
  Opening Explorer preview (heading + screenshot + bullets); pills row removed,
  Opening Explorer removed from FEATURES list.
- Stats renamed to "Global Stats" across desktop nav, mobile bottom bar, More
  drawer, mobile header, plus new page h1.

## [v1.8] Guest Access — 2026-04-06

Free try-before-signup: users can play with FlawChess as a guest, then promote
their guest account into a full account without losing any imported data.

### Added

- Guest session foundation — `is_guest` User model, JWT-based guest sessions
  with 30-day auto-refresh, IP rate limiting on guest creation.
- Guest frontend — "Use as Guest" buttons on homepage and auth page,
  persistent guest banner indicating limited access.
- Email / password promotion — backend promotion service, register-page
  promotion flow preserving all imported data.
- Google SSO promotion — OAuth promotion route with guest identity
  preservation across redirect, email collision handling.

### Security

- Patched Google OAuth for CVE-2025-68481 CSRF vulnerability (double-submit
  cookie validation).

### Fixed

- Import page guest guard, auth page logo linking, delete button disabled
  during active imports.

## [v1.7] Consolidation, Tooling & Refactoring — 2026-04-03

Tooling and code-quality consolidation: static type checking, dead-code
detection, import pipeline speedup, and naming cleanup.

### Added

- Astral `ty` static type checker in CI — zero backend type errors, all
  functions annotated.
- Knip dead export detection + TypeScript `noUncheckedIndexedAccess` — zero
  dead code, strict index-access safety.

### Changed

- Import pipeline ~2x faster — unified single-pass PGN processing, bulk CASE
  UPDATE, batch size 10 → 28.
- SQL aggregation (`COUNT().filter()`) replacing Python-side W/D/L counting
  loops.
- Consistent naming and deduplication — router prefixes, shared
  `apply_game_filters`, frontend `buildFilterParams`.
- CSS variable brand buttons (`.btn-brand`) replacing JS constant, typed
  Pydantic response models on all endpoints.

### Removed

- 7 dead files deleted, unused shadcn/ui re-exports cleaned, -1522 lines.

## [v1.6] UI Polish & Improvements — 2026-03-30

Centralized theme system, shared WDL chart component, a new Openings reference
table from 3641 curated openings, and mobile drawer sidebars.

### Added

- Centralized theme system with CSS variables, charcoal containers with SVG
  noise texture, brand subtab highlighting.
- Shared `WDLChartRow` component replacing all inconsistent WDL chart
  implementations.
- Openings reference table (3641 entries from TSV) with SQL-side WDL
  aggregation and filter support.
- Most Played Openings redesign — top 10 per color, dedicated table UI with
  minimap popovers.
- Mobile drawer sidebars for filters and bookmarks with deferred filter apply
  on close.

### Changed

- Opening Statistics — smart default chart data from most-played openings,
  chart-enable toggles on bookmarks.

## [v1.5] Endgame Analytics & Engine Data — 2026-03-28

Game phase classification at import, material signatures for endgame
categorization, engine analysis metrics ingestion, and the first cut of the
Endgames tab.

### Added

- Game phase classification (opening / middlegame / endgame) per position at
  import.
- Material signature, imbalance, and endgame class per position at import.
- Engine analysis data import (eval, accuracy, move quality) from chess.com
  and lichess.
- Endgame performance statistics in a dedicated Endgames tab, filterable by
  type (rook, minor piece, pawn, queen, mixed).
- Conversion stats (win rate when up material) with timeline charts.
- Recovery stats (draw / win rate when down material) with timeline charts.
- Homepage refresh with feature showcase, FAQ, and acknowledgements.

## [v1.4] Web Analytics — 2026-03-28

### Added

- Web analytics via self-hosted Umami.

## [v1.3] Project Launch — 2026-03-22

Production launch: rebrand to FlawChess, Hetzner deployment, CI/CD, Sentry,
public homepage, rate limiting, and privacy policy.

### Added

- Complete Docker Compose stack (FastAPI + Caddy 2.11.2 + PostgreSQL) deployed
  to Hetzner VPS with auto-TLS.
- GitHub Actions CI/CD pipeline — test + lint + SSH deploy + health check
  polling.
- Sentry error monitoring on backend (`sentry-sdk[fastapi]`) and frontend
  (`@sentry/react`) with Docker build-time DSN injection.
- Public homepage with feature sections, FAQ, and register / login CTA; SEO
  meta tags, sitemap.xml, robots.txt.
- Per-platform rate limiter (`asyncio.Semaphore`) protecting chess.com /
  lichess imports from concurrent bans.
- Privacy policy page at `/privacy`; professional README with screenshots and
  self-hosting instructions.

### Changed

- Full codebase renamed from Chessalytics to FlawChess across 20 files — PWA
  manifest, logo, GitHub org transfer.

## [v1.2] Mobile & PWA — 2026-03-21

Installable PWA with mobile-first navigation, touch interactions, and a phone
testing dev workflow.

### Added

- Installable PWA with service worker, chess-themed icons, Workbox caching
  (NetworkOnly for API routes).
- Mobile bottom navigation bar with direct tabs and slide-up "More" drawer
  (vaul-based).
- Click-to-move chessboard on touch devices with sticky board layout on
  Openings page.
- 44px touch targets on all interactive elements, no horizontal scroll at
  375px.
- Android / iOS in-app install prompts (`beforeinstallprompt` + manual iOS
  instructions).
- Cloudflare Tunnel dev workflow for HTTPS phone testing.

## [v1.1] Opening Explorer & UI Restructuring — 2026-03-20

Interactive move explorer with W/D/L stats per position, tabbed Openings hub,
dedicated Import page, enriched import data, and redesigned game cards.

### Added

- Move explorer with next-move W/D/L stats, click-to-navigate, transposition
  handling.
- Chessboard arrows showing next moves with win-rate color coding.
- Tabbed Openings hub (Moves / Games / Statistics) and dedicated Import page.
- Enhanced import — clock data, termination reason, time control fix,
  multi-username sync.
- Game cards — 3-row layout with icons, hover / tap minimap showing final
  position.

### Fixed

- Data isolation bugs between users.
- Google SSO last_login not being updated.
- Stale cache on auth transitions.

## v1.0 Initial Platform — 2026-03-15

First public version of FlawChess: multi-user chess analysis with game import
from chess.com and lichess, Zobrist-hash position matching, interactive board,
bookmarks, game cards, and rating / stats pages.

### Added

- Import pipeline with incremental sync (chess.com + lichess).
- Position analysis via precomputed Zobrist hashes (white / black / full) for
  indexed integer equality lookups.
- Interactive chess board to specify search positions by playing moves.
- Filters: time control, rated / casual, recency, color, opponent type,
  position color.
- Position bookmarks with drag-reorder, mini boards, piece filter.
- Auto-generated bookmark suggestions from most-played openings.
- Game cards with rich metadata and pagination.
- Rating history, global stats, openings W/D/L charts.
- Multi-user auth with data isolation.

[Unreleased]: https://github.com/flawchess/flawchess/compare/v1.11...HEAD
[v1.11]: https://github.com/flawchess/flawchess/compare/v1.10...v1.11
[v1.10]: https://github.com/flawchess/flawchess/compare/v1.9...v1.10
[v1.9]: https://github.com/flawchess/flawchess/compare/v1.8...v1.9
[v1.8]: https://github.com/flawchess/flawchess/compare/v1.7...v1.8
[v1.7]: https://github.com/flawchess/flawchess/compare/v1.6...v1.7
[v1.6]: https://github.com/flawchess/flawchess/compare/v1.5...v1.6
[v1.5]: https://github.com/flawchess/flawchess/compare/v1.4...v1.5
[v1.4]: https://github.com/flawchess/flawchess/compare/v1.3...v1.4
[v1.3]: https://github.com/flawchess/flawchess/compare/v1.2...v1.3
[v1.2]: https://github.com/flawchess/flawchess/compare/v1.1...v1.2
[v1.1]: https://github.com/flawchess/flawchess/compare/47cca4c...v1.1
