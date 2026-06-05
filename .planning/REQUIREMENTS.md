# Requirements: FlawChess — v1.24 Library Page

**Defined:** 2026-06-05
**Core Value:** Position-precise WDL across openings + endgames + time pressure on top of users' actual chess.com / lichess games, with personalized LLM commentary on endgame performance and an auto-generated opening-strengths/weaknesses report.

**Milestone scope note:** This milestone delivers only the **Library page shell + the Import and Overview subtab migrations** — the first step of SEED-036. Per explicit user instruction, the rest of the SEED-036 vision (Games subtab, mistake-type filter, mistake-stats panel, Analysis viewer, mistake-detection backend, on-demand best-move endpoint) is **deliberately left unplanned** and lives in `.planning/seeds/SEED-036-library-page-milestone.md`.

## v1 Requirements

Requirements for this milestone. Each maps to the single roadmap phase.

### Library Page

- [ ] **LIB-01**: User can navigate to a new top-level **Library** page from the desktop nav, the mobile bottom bar, and the mobile "More" drawer.
- [ ] **LIB-02**: The Library page presents deep-linkable, URL-routed subtabs using the same Openings-style `<Tabs variant="brand">` pattern (`navigate('/library/<tab>')`), with each subtab implemented as its own `.tsx` file mirroring the Openings page structure.
- [ ] **LIB-03**: User can access the existing Import workflow as the **Import** subtab at `/library/import` (its own tsx, leftmost subtab); visiting the old `/import` URL redirects to `/library/import`.
- [ ] **LIB-04**: User can access the existing global Overview dashboard as the **Overview** subtab at `/library/overview` (its own tsx, migrated from `GlobalStats.tsx`); visiting the old `/overview` URL redirects to `/library/overview`.
- [ ] **LIB-05**: Top-level navigation shows **Library · Openings · Endgames** (plus the superuser-only Admin item), with Import and Overview removed as standalone top-level nav items.
- [ ] **LIB-06**: The `totalGames === 0` notification dot appears on the **Library** nav item (moved from the former Import nav item).
- [ ] **LIB-07**: The default landing subtab is state-dependent — a user with zero imported games lands on **Import**; a user with games lands on **Overview**. Home's gameless-user redirect targets `/library/import`.
- [ ] **LIB-08**: The Library page is **always accessible** (never import-gated, because it hosts Import); the Import and Overview subtabs are always open.
- [ ] **LIB-09**: The Library page and both subtabs work on mobile — responsive subtab control plus the responsive layouts preserved from the migrated Import and Overview pages, with `data-testid` / ARIA / semantic-HTML conventions on all new interactive elements and containers.

## v2 Requirements

Deferred to future phases of the SEED-036 Library milestone (not in this roadmap):

### Library — Games & Mistakes

- **LIBG-01**: Games subtab — filterable game archive with mistake-type filter (eval-driven, Lichess-analyzed games only).
- **LIBG-02**: Mistake-detection backend service deriving per-ply inaccuracy/mistake/blunder from stored `eval_cp` / `eval_mate`.
- **LIBG-03**: Mistake-stats panel — counts/rates per mistake type, normalized, with trend over time.
- **LIBG-04**: Analysis subtab — per-mistake viewer (board, stepper, move list, eval/material timeline, jump-to-mistake).
- **LIBG-05**: On-demand single-position best-move endpoint (`POST /api/analysis/best-move`), rate-limited / concurrency-capped.

## Out of Scope

Explicitly excluded for this milestone. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Games / Analysis subtabs (any UI) | Need the mistake-detection backend layer; deferred to future SEED-036 phases per explicit user instruction |
| Mistake-type filter, mistake-stats panel | Same — depend on the deferred eval-derived mistake layer |
| On-demand best-move endpoint (server-side Stockfish) | Belongs with the Analysis subtab; threat-modeled surface deferred to a later phase |
| Material-delta filter | Cut in the 2026-06-03 SEED-036 rework (pre-eval proxy, superseded by eval-driven mistakes) |
| Full-game server-side Stockfish at import time | Permanently out of scope (OOM history, CLAUDE.md / FLAWCHESS-3Q) |
| New backend endpoints or schema changes in this milestone | Phase 1 is a pure frontend restructure + route migration; no backend work |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| LIB-01 | Phase 104 | Pending |
| LIB-02 | Phase 104 | Pending |
| LIB-03 | Phase 104 | Pending |
| LIB-04 | Phase 104 | Pending |
| LIB-05 | Phase 104 | Pending |
| LIB-06 | Phase 104 | Pending |
| LIB-07 | Phase 104 | Pending |
| LIB-08 | Phase 104 | Pending |
| LIB-09 | Phase 104 | Pending |

**Coverage:**
- v1 requirements: 9 total
- Mapped to phases: 9
- Unmapped: 0 ✓

---
*Requirements defined: 2026-06-05*
*Last updated: 2026-06-05 after initial definition for v1.24 Library Page*
