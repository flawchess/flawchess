# Requirements: FlawChess — v1.24 Library Page

**Defined:** 2026-06-05
**Core Value:** Position-precise WDL across openings + endgames + time pressure on top of users' actual chess.com / lichess games, with personalized LLM commentary on endgame performance and an auto-generated opening-strengths/weaknesses report.

**Milestone scope note:** This milestone delivers only the **Library page shell + the Import and Overview subtab migrations** — the first step of SEED-036. Per explicit user instruction, the rest of the SEED-036 vision (Games subtab, mistake-type filter, mistake-stats panel, Analysis viewer, mistake-detection backend, on-demand best-move endpoint) is **deliberately left unplanned** and lives in `.planning/seeds/SEED-036-library-page-milestone.md`.

## v1 Requirements

Requirements for this milestone. Each maps to the single roadmap phase.

### Library Page

- [x] **LIB-01**: User can navigate to a new top-level **Library** page from the desktop nav, the mobile bottom bar, and the mobile "More" drawer.
- [x] **LIB-02**: The Library page presents deep-linkable, URL-routed subtabs using the same Openings-style `<Tabs variant="brand">` pattern (`navigate('/library/<tab>')`), with each subtab implemented as its own `.tsx` file mirroring the Openings page structure.
- [x] **LIB-03**: User can access the existing Import workflow as the **Import** subtab at `/library/import` (its own tsx, leftmost subtab); visiting the old `/import` URL redirects to `/library/import`.
- [x] **LIB-04**: User can access the existing global Overview dashboard as the **Overview** subtab at `/library/overview` (its own tsx, migrated from `GlobalStats.tsx`); visiting the old `/overview` URL redirects to `/library/overview`.
- [x] **LIB-05**: Top-level navigation shows **Library · Openings · Endgames** (plus the superuser-only Admin item), with Import and Overview removed as standalone top-level nav items.
- [x] **LIB-06**: The `totalGames === 0` notification dot appears on the **Library** nav item (moved from the former Import nav item).
- [x] **LIB-07**: The default landing subtab is state-dependent — a user with zero imported games lands on **Import**; a user with games lands on **Overview**. Home's gameless-user redirect targets `/library/import`.
- [x] **LIB-08**: The Library page is **always accessible** (never import-gated, because it hosts Import); the Import and Overview subtabs are always open.
- [x] **LIB-09**: The Library page and both subtabs work on mobile — responsive subtab control plus the responsive layouts preserved from the migrated Import and Overview pages, with `data-testid` / ARIA / semantic-HTML conventions on all new interactive elements and containers.

## v2 Requirements

SEED-036 Library — analysis half. **LIBG-02 / LIBG-06 / LIBG-07 are in v1.24 scope (Phase 105); LIBG-08 / LIBG-09 are now in v1.24 scope (Phase 106).** The rest stay deferred to subsequent phases (not yet roadmapped). Full design in `.planning/seeds/SEED-036-library-page-milestone.md`.

### Library — Games & Mistakes

- **LIBG-01**: Games subtab — filterable game archive (metadata + mistake-count filters), game cards with B/M/I counts + curated tag chips, mistake-stats panel with analyzed-% denominator. *(deferred — later phase)*
- **LIBG-02** *(Phase 105)*: On-the-fly mistake-detection service deriving per-ply severity (inaccuracy/mistake/blunder) from stored `eval_cp` / `eval_mate`, using the Lichess-aligned expected-score-drop thresholds (0.05 / 0.10 / 0.15 on the [0,1] ES scale), from the mover's perspective; mate handled via the ±1000 cp-equivalent mapping (Option B); no materialization, no schema change; chess.com / unanalyzed games yield an explicit "no analysis" result.
- **LIBG-03**: Mistake-stats panel — counts/rates per mistake type, normalized, with trend over time + analyzed-game (≥90%-coverage) denominator. *(deferred — later phase)*
- **LIBG-04**: Analysis subtab — per-flaw viewer (board, stepper, move list, eval/material timeline, jump-to-mistake), deep-link detail route. *(deferred — later phase)*
- **LIBG-05**: On-demand single-position best-move endpoint (`POST /api/analysis/best-move`), rate-limited / concurrency-capped. *(deferred — later phase)*
- **LIBG-06** *(Phase 105)*: The detection service emits the eight attribution tags per flaw — `miss`, `unpunished`, `from-winning`, `result-changing`, `phase`, and exactly one tempo tag of {`time-pressure`, `hasty`, `knowledge-gap`} (move-time + clock derived; initial thresholds documented and tunable).
- **LIBG-07** *(Phase 105)*: Each flaw is returned as a typed structured object (ply, FEN, side, severity, tags, eval before/after) documented as the consumption contract for the Games / Flaws / Analysis surfaces and SEED-037 Train, designed so materialization is a drop-in later optimization.
- **LIBG-08** *(Phase 106)*: Games-list endpoint extends `apply_game_filters` with a boolean mistake-type `EXISTS` filter (game contains ≥1 of a selected severity; severity thresholds as bound parameters, no count thresholds, no materialization, no backfill) and returns per-game B/M/I severity counts plus a curated, aggregated/deduped set of card tag-chips (game-level dedupe, inaccuracy-level tags and `phase` excluded), reusing the Phase 105 kernel; chess.com / unanalyzed-lichess games return an explicit "no engine analysis" state, never a false zero-flaw game. Backend of LIBG-01.
- **LIBG-09** *(Phase 106)*: Stats-panel aggregate endpoint over the filtered analyzed-only set — per-severity counts/rates (normalized per game and per 100 moves), the full tag distribution (tempo split, result-changing rate, phase histogram), and a trend-over-time series — with the explicit `% analyzed` (≥90%-per-ply-coverage) denominator and analyzed-game N stated in the response. Cross-game work pushed into a SQL window-scan returning only flagged mistake+blunder rows; Python applies tags + tag-distribution stats over that reduced set. Backend of LIBG-03.

## Out of Scope

Explicitly excluded for this milestone. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Games / Flaws / Analysis subtabs (any UI) | Phase 106 builds the Games-surface *backend*; all SEED-036 UI surfaces remain deferred to subsequent phases |
| Mistake-type filter / stats-panel UI | The backend (LIBG-08/09) lands in Phase 106; the UI that renders them is deferred to the Games-subtab frontend phase |
| On-demand best-move endpoint (server-side Stockfish) | Belongs with the Analysis subtab; threat-modeled surface deferred to a later phase |
| Material-delta filter | Cut in the 2026-06-03 SEED-036 rework (pre-eval proxy, superseded by eval-driven mistakes) |
| Full-game server-side Stockfish at import time | Permanently out of scope (OOM history, CLAUDE.md / FLAWCHESS-3Q) |
| Schema changes / materialization for the mistake layer | Phases 105–106 are on-the-fly only — no new columns, table, migration, or backfill |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| LIB-01 | Phase 104 | Complete |
| LIB-02 | Phase 104 | Complete |
| LIB-03 | Phase 104 | Complete |
| LIB-04 | Phase 104 | Complete |
| LIB-05 | Phase 104 | Complete |
| LIB-06 | Phase 104 | Complete |
| LIB-07 | Phase 104 | Complete |
| LIB-08 | Phase 104 | Complete |
| LIB-09 | Phase 104 | Complete |
| LIBG-02 | Phase 105 | Complete |
| LIBG-06 | Phase 105 | Complete |
| LIBG-07 | Phase 105 | Complete |
| LIBG-08 | Phase 106 | Planned |
| LIBG-09 | Phase 106 | Planned |

**Coverage:**

- v1 requirements: 9 total (all Complete)
- v1.24 analysis-half (Phase 105): LIBG-02, LIBG-06, LIBG-07
- v1.24 Games-surface backend (Phase 106): LIBG-08, LIBG-09
- Deferred (later phases): LIBG-01 / LIBG-03 *(UI only — their backend is LIBG-08/09, Phase 106)*, LIBG-04, LIBG-05

---
*Requirements defined: 2026-06-05*
*Last updated: 2026-06-05 after initial definition for v1.24 Library Page*
