# Requirements: FlawChess v1.13 — Opening Insights

**Milestone goal:** Surface opening-line strengths and weaknesses for each user via auto-scanning of most-played and bookmarked openings, with templated findings and deep-links into the Move Explorer at the implicated entry position. **Independent of the v1.12 benchmark DB** — opening positions are book theory (engine eval ≈ 0.0), so absolute under-/over-performance over n ≥ 10 games is actionable without population baselines.

**Source:** SEED-005. **Approach:** pure templated/rule-based in v1; LLM wrap-up deferred to v1.13.x or v1.14.

## v1.13 Requirements

### Backend insight-generation service (INSIGHT-CORE)

- [ ] **INSIGHT-CORE-01**: User-scoped `opening_insights_service` accepts the same filter object the rest of the openings stats use (color, time control, recency, opponent type/strength, rated). Filters reshape findings; same-filter equivalence is required.
- [ ] **INSIGHT-CORE-02**: Scan input = top-10 most-played openings per color (reusing the existing Stats-tab service-layer call) ∪ user's bookmarked positions. Apply min-games floor per entry (default 50; configurable).
- [ ] **INSIGHT-CORE-03**: For each entry position, scan only the immediate next ply of candidate moves the user has played (no recursion — deeper named openings appear as their own top-10 entries).
- [ ] **INSIGHT-CORE-04**: For each (entry_position, candidate_move) pair with n ≥ 10 games, compute `loss_rate = losses / n` and `score = (wins + draws/2) / n`.
- [ ] **INSIGHT-CORE-05**: Classify as **weakness** if `loss_rate ≥ 0.55`; **strength** if `score ≥ 0.60`. Drop neutral findings.
- [ ] **INSIGHT-CORE-06**: Deduplicate findings by Zobrist hash of the resulting position. When the same hash surfaces under multiple openings (e.g. Scandinavian generic vs Scandinavian Main Line), attribute to the **deepest matching opening** only.
- [ ] **INSIGHT-CORE-07**: Rank findings by frequency × severity. Cap displayed findings (default top 5 weaknesses + top 3 strengths; configurable). Exact formula resolved during Phase A `/gsd-discuss-phase`.
- [ ] **INSIGHT-CORE-08**: Output structured `OpeningInsightFinding` payload — `{opening_name, opening_eco, entry_fen, candidate_move_san, n_games, w, d, l, loss_rate, score, classification, deep_link_target}`.
- [ ] **INSIGHT-CORE-09**: Latency budget — on-the-fly response acceptable for typical users (≤ ~2k games). Cache at the service layer only if heavy users (10k+ games) push past the budget; **do NOT** add a precompute pipeline preemptively.

### Frontend — Stats subtab integration (INSIGHT-STATS)

- [ ] **INSIGHT-STATS-01**: `OpeningInsightsBlock` component on Openings → Stats subtab as the primary insight surface.
- [ ] **INSIGHT-STATS-02**: Renders templated bullets, e.g. "You lose 62% as Black after 1.e4 c5 2.Nf3 d6 3.d4 cxd4 4.Nxd4 (n=18) → [open in Move Explorer]". Strengths styled with green semantic; weaknesses with red.
- [ ] **INSIGHT-STATS-03**: Deep-link click navigates to Openings → Moves tab pre-loaded at the entry FEN with the candidate move highlighted on the board.
- [ ] **INSIGHT-STATS-04**: Empty state when no findings clear the thresholds — clear copy explaining the threshold + min-games floor.
- [ ] **INSIGHT-STATS-05**: Block respects active filter set; updates when filters change (matches v1.11 endgame insights pattern).
- [ ] **INSIGHT-STATS-06**: Mobile-equivalent rendering (component must survive the mobile drawer / single-column layout — see CLAUDE.md frontend rules).

### Frontend — Moves subtab inline bullets (INSIGHT-MOVES)

- [ ] **INSIGHT-MOVES-01**: Inline bullet next to existing red/green candidate-move arrows on the Openings → Moves board.
- [ ] **INSIGHT-MOVES-02**: Bullets are scoped to the **currently displayed** position (one finding per displayed candidate, not the full scan). No deep-link — user is already at the position.
- [ ] **INSIGHT-MOVES-03**: Reuses the same `OpeningInsightFinding` payload from INSIGHT-CORE.

### Stretch (in-scope but deferrable)

- [ ] **INSIGHT-META-01** (stretch): Aggregate-level finding rendered above the per-finding list — e.g. "You have weaknesses across 8 different openings — consider narrowing your repertoire" or "Your Caro-Kann shows 5 weak responses — focus revision here". Templated rule-based; LLM narration is **out of scope** for v1.13.
- [ ] **INSIGHT-BADGE-01** (stretch): Visual badge on bookmark cards (e.g. small red dot + count chip) when the bookmarked opening surfaces ≥ 1 weakness. Apply to both desktop bookmarks panel and mobile bookmarks drawer.

## Pre-v1.13 Quick Tasks (gate before Phase A starts building on the algo)

- [ ] **PRE-01**: Drop the parity filter from `query_top_openings_sql_wdl` (`app/repositories/stats_repository.py:264-265`). 48% of named ECO openings (1599 of 3301) are white-defined and currently invisible in the black top-10; verified against Hillbilly Attack (816 black games in dev DB, currently filtered out). See `.planning/todos/pending/2026-04-26-top10-openings-parity-bug.md`.

## Future Requirements (deferred)

- LLM narration of opening insights — revisit as v1.13.x or v1.14 once templated findings are in real users' hands and we know which findings are worth narrating
- Pre-compute pipeline for opening insights — only if INSIGHT-CORE-09 latency budget is breached for heavy users
- Population-relative weakness signals — gated on full benchmark ingest (SEED-006); deliberately not part of v1.13 because book-move equality makes population baselines redundant for opening insights

## Out of Scope

- **LLM narration of v1.13 findings** — pure templated only; LLM is a deliberate scope expansion, deferred (see Future Requirements)
- **Population-relative weakness signals** — argued in SEED-005 § Why Self-Referential Is Sufficient; book-move equality makes the population layer non-actionable
- **Engine-eval-based weakness detection** — "engine says +1.5 here but you played a move that drops it to -0.3" requires per-position engine analysis FlawChess does not import for every game; revisit if v2 "human-like engine analysis" lands
- **Time-pressure-as-weakness** — mixes opening prep with time management; belongs in time-pressure analytics
- **Opponent-rating-conditioned thresholds** — already covered by global filters (opponent_strength)
- **Recursive scan into deeper opening lines** — explicitly avoided; deeper named openings surface as their own top-10 entries; recursion would thin samples below n=10

## Traceability

PRE-01 is a pre-v1.13 quick task gating Phase 70 — intentionally not mapped to a phase.

| REQ-ID | Phase |
|--------|-------|
| INSIGHT-CORE-01 | 70 |
| INSIGHT-CORE-02 | 70 |
| INSIGHT-CORE-03 | 70 |
| INSIGHT-CORE-04 | 70 |
| INSIGHT-CORE-05 | 70 |
| INSIGHT-CORE-06 | 70 |
| INSIGHT-CORE-07 | 70 |
| INSIGHT-CORE-08 | 70 |
| INSIGHT-CORE-09 | 70 |
| INSIGHT-STATS-01 | 71 |
| INSIGHT-STATS-02 | 71 |
| INSIGHT-STATS-03 | 71 |
| INSIGHT-STATS-04 | 71 |
| INSIGHT-STATS-05 | 71 |
| INSIGHT-STATS-06 | 71 |
| INSIGHT-MOVES-01 | 72 |
| INSIGHT-MOVES-02 | 72 |
| INSIGHT-MOVES-03 | 72 |
| INSIGHT-META-01 | 73 (stretch) |
| INSIGHT-BADGE-01 | 74 (stretch) |

---
*Last updated: 2026-04-26 — v1.13 roadmap created (Phases 70-74). Coverage: 20/20 active requirements mapped.*
