# Phase 107 — Artifacts & Source Coverage Audit

**Generated:** 2026-06-05 (planner)
**Plans:** 7 (107-01 … 107-07) across 4 waves.

---

## Artifacts this phase produces

Every symbol/file created or extended by Phase 107, for downstream-phase reference
(the deferred Flaws subtab, Analysis viewer, Train surfaces all consume some of these).

### Backend (D-01 slice — Plan 01)

| Artifact | Location | Notes |
|----------|----------|-------|
| `TagDistribution.miss_rate: float` | `app/schemas/library.py` | New flat float; `miss_count / total_mb_flaws`, `0.0` when none |
| `TagDistribution.lucky_escape_rate: float` | `app/schemas/library.py` | New flat float |
| `TagDistribution.while_ahead_rate: float` | `app/schemas/library.py` | New flat float |
| three counters in `_compute_tag_distribution` | `app/services/library_service.py` | Computed, not stored — no migration |
| new `TestFlawStats` tests | `tests/services/test_library_service.py` | Cover the 3 rates + the 0.0-no-flaws edge |

No new route. Endpoint remains `GET /api/library/flaw-stats` (never `mistake-stats`).

### Frontend foundations (Plan 02)

| Artifact | Location |
|----------|----------|
| theme constants: `SEV_BLUNDER`/`SEV_MISTAKE`/`SEV_INACCURACY` | `frontend/src/lib/theme.ts` |
| theme constants: `FAM_TEMPO`,`FAM_TEMPO_BG`,`FAM_TEMPO_LOW_CLOCK`,`FAM_TEMPO_IMPATIENT`,`FAM_TEMPO_CONSIDERED`,`FAM_TEMPO_UNMEASURED` | `frontend/src/lib/theme.ts` |
| theme constants: `FAM_OPPORTUNITY`,`FAM_OPPORTUNITY_BG`,`FAM_IMPACT`,`FAM_IMPACT_BG` | `frontend/src/lib/theme.ts` |
| theme constants: `PHASE_OPENING`,`PHASE_MIDDLEGAME`,`PHASE_ENDGAME` | `frontend/src/lib/theme.ts` |
| TS types: `FlawTag`,`FlawSeverity`,`TempoTag`,`AnalysisState`, per-game card type, `LibraryGamesResponse`,`SeverityRates`,`TagDistribution`,`FlawTrendPoint`,`FlawStatsResponse` | `frontend/src/types/library.ts` |
| API client: `libraryApi.getGames`, `libraryApi.getFlawStats` | `frontend/src/api/client.ts` |
| hooks: `useLibraryGames`, `useLibraryFlawStats`, `buildLibraryParams` | `frontend/src/hooks/useLibrary.ts` |

### Shared pagination (Plan 03)

| Artifact | Location |
|----------|----------|
| `Pagination` component (`{ currentPage, totalPages, onPageChange }`) | `frontend/src/components/results/Pagination.tsx` |
| `GameCardList` rewired to consume `Pagination` (behavior-preserving) | `frontend/src/components/results/GameCardList.tsx` |

### Card primitives + filter (Plan 04)

| Artifact | Location | Key testids |
|----------|----------|-------------|
| `SeverityBadge` | `frontend/src/components/library/SeverityBadge.tsx` | `severity-{severity}-{gameId}` |
| `TagChip` | `frontend/src/components/library/TagChip.tsx` | `chip-{tagName}-{gameId}` |
| `NoAnalysisState` | `frontend/src/components/library/NoAnalysisState.tsx` | `no-analysis-{gameId}` |
| `LibraryFilterPanel` | `frontend/src/components/filters/LibraryFilterPanel.tsx` | `filter-severity-blunder`,`filter-severity-mistake`,`btn-reset-filters` |

### Flaw-Stats panel (Plan 05)

| Artifact | Location | Key testids |
|----------|----------|-------------|
| `FlawStatsBand` | `frontend/src/components/library/FlawStatsBand.tsx` | `flaw-stats-band`,`stat-cell-{blunders,mistakes,inaccuracies,result-changing}` |
| `FlawTrendChart` | `frontend/src/components/library/FlawTrendChart.tsx` | `flaw-trend-chart` |
| `FlawTagDistribution` | `frontend/src/components/library/FlawTagDistribution.tsx` | `tag-distribution-block`,`tempo-stacked-bar`,`phase-histogram`,`opportunity-rates`,`impact-rates` |
| `FlawStatsPanel` | `frontend/src/components/library/FlawStatsPanel.tsx` | `flaw-stats-panel`,`flaw-stats-norm-toggle`,`flaw-stats-toggle-game`,`flaw-stats-toggle-100`,`flaw-stats-denominator` |

### Card list + assembly (Plans 06–07)

| Artifact | Location | Key testids |
|----------|----------|-------------|
| `LibraryGameCard` | `frontend/src/components/results/LibraryGameCard.tsx` | `library-game-card-{gameId}`,`severity-row-{gameId}` |
| `LibraryGameCardList` | `frontend/src/components/results/LibraryGameCardList.tsx` | `library-game-card-list` |
| `GamesTab` | `frontend/src/pages/library/GamesTab.tsx` | `games-tab-content`,`btn-filters` |
| `LibraryPage` (modified) | `frontend/src/pages/library/LibraryPage.tsx` | `tab-games`,`tab-games-mobile` (+ route `/library/games`, returning-user default) |

---

## Multi-Source Coverage Audit

Every source item is COVERED by a plan. No MISSING items → no phase split needed.

### GOAL (ROADMAP Phase 107 Success Criteria)

| # | Success Criterion | Covered by |
|---|-------------------|------------|
| 1 | Card archive from `/library/games`, B/M/I counts + family-colored chips, explicit no-analysis state | Plans 02 (types/hook), 04 (badge/chip/no-analysis), 06 (card), 07 (assembly) |
| 2 | Tag chips display-only, family-colored, no assumed Flaws route | Plan 04 (TagChip, D-07) |
| 3 | Metadata filters + boolean mistake-severity filter; no chessboard/opening filter | Plans 04 (LibraryFilterPanel), 07 (wiring) |
| 4 | Flaw-Stats panel: per-game/per-100 rates, tempo split, result-changing, phase histogram, trend, explicit `% analyzed` + N | Plans 01 (D-01 rates), 05 (panel) |
| 5 | Mobile drawer parity, full data-testid/ARIA/semantic-HTML, isError on every chain | Plans 04–07 (esp. 07 assembly) |

### REQ (REQUIREMENTS.md phase_req_ids)

| Req | Description | Covered by |
|-----|-------------|------------|
| LIBG-01 | Games subtab frontend — card archive, severity filter, B/M/I counts, family chips, no-analysis state, mobile drawer | Plans 02, 03, 04, 06, 07 |
| LIBG-03 | Flaw-Stats panel frontend — per-severity rates, tag distribution, trend, `% analyzed` + N | Plans 01, 02, 05, 07 |

### RESEARCH (107-UI-SPEC.md + 107-PATTERNS.md design contract)

| Item | Covered by |
|------|------------|
| All §Color theme constants | Plan 02 (theme.ts) |
| Analyzed card contract (Sketch 001-A) | Plans 04, 06 |
| Flaw-Stats panel contract (Sketch 002-A), incl. tempo unmeasured remainder | Plan 05 |
| Filter Panel Extension (severity filter) | Plan 04 |
| Desktop sidebar / mobile drawer layout | Plan 07 |
| Pagination reuse seam | Plan 03 |
| Copywriting Contract (all copy strings) | Plans 04–07 |
| Browser-automation testid/ARIA table | Plans 04–07 |

The UI-SPEC §API Data Mapping "verify this gap" note on opportunity/impact rates is RESOLVED by
CONTEXT.md D-01 (backend extension, Plan 01) — superseding the spec's open "derive client-side"
fallback. D-02 explicitly rejected the client-side derivation.

### CONTEXT (107-CONTEXT.md D-XX decisions)

| Decision | Covered by |
|----------|------------|
| D-01 backend slice (3 flat float rates + counters + tests) | Plan 01 |
| D-02 client-side derivation rejected | Honored in Plan 05 (reads backend fields, not chips) |
| D-03 Zone 3 renders Opportunity/Impact from real fields, no placeholders | Plan 05 |
| D-04 extract shared Pagination | Plan 03 |
| D-05 LibraryGameCard is a separate component (no GameCard genericization) | Plan 06 |
| D-06 pagination blast radius — behavior-preserving for Openings/Endgames | Plan 03 (acceptance criterion) + Plan 07 (re-verified at full assembly) |
| D-07 chips display-only, honest ARIA, no toast, no assumed route | Plan 04 |
| Discretion: trend chart AreaChart vs LineChart | Plan 05 (AreaChart per EndgameScoreOverTimeChart) |
| Discretion: pagination component vs hook | Plan 03 (component) |

### Exclusions (not gaps)

- Tag-chip deep-link into a Flaws view — Deferred Idea (CONTEXT.md); chips display-only.
- Per-card eval sparkline — Deferred Idea / roadmap out-of-scope.
- "Coming soon" placeholder scaffolding — Deferred Idea; data is real via D-01.
- Flaws subtab UI, Analysis viewer (LIBG-04), best-move endpoint (LIBG-05) — later phases.

**Audit result: all GOAL / REQ / RESEARCH / CONTEXT items COVERED. No split required.**
