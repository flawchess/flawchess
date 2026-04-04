# Project Research Summary

**Project:** FlawChess v1.8 — Advanced Analytics
**Domain:** Chess analytics platform — ELO-adjusted endgame skill, opening risk metrics, cross-platform rating normalization
**Researched:** 2026-04-04
**Confidence:** HIGH (architecture based on direct codebase inspection); MEDIUM (rating normalization constants and opening risk formulas)

## Executive Summary

FlawChess v1.8 adds opponent-strength-adjusted endgame metrics and opening risk signals to a production chess analytics platform. The implementation requires no new libraries, no schema migrations for the core ELO adjustment feature, and no new architectural patterns — all computation is pure Python arithmetic over data already stored in the `games` table (`white_rating`, `black_rating`, `platform`, `user_color`). The recommended approach is to extend the existing `EndgamePerformanceResponse` with a new `adjusted_endgame_skill: float` field (not replace the existing `endgame_skill`), add a separate `/endgames/elo-timeline` endpoint for the rolling window chart, and compute opening risk as normalized Shannon entropy of WDL distributions inline in `get_next_moves()` with zero additional SQL.

The primary technical risk is not implementation complexity — it is correctness of the ELO normalization formula and data correctness (specifically opponent color logic and NULL rating handling). The lichess-to-chess.com offset is an empirical approximation, not an authoritative constant; it must be implemented as a named Python function with explicit documentation of its limitations and surfaced to users with an "approximate" disclosure. The opponent color derivation is the inverse of the user rating pattern already in the codebase (`user_color == "white"` means `opponent_rating == black_rating`), and getting it backwards is a silent bug that produces a plausible-looking but wrong adjusted score. Both risks are well-understood and preventable with targeted unit tests written before wiring values into the adjustment formula.

The phased approach recommended by research separates the ELO-adjusted skill score and gauge (quick win, high value) from the ELO timeline chart (same infrastructure, separate endpoint) and treats opening risk as an independent track. This ordering minimizes blast radius if the opening risk formula definition requires iteration, while delivering the headline ELO-adjusted endgame score to users as soon as the first phase is complete.

## Key Findings

### Recommended Stack

No new dependencies are needed for v1.8. All required computation is available from Python's `statistics` stdlib, SQLAlchemy's `func.avg()`, and existing Recharts components already in use. Adding numpy, scipy, or external rating converters would be massive overkill for averaging hundreds of rows per user. The existing `EndgameGauge.tsx` component is already fully generic (accepts `value`, `label`, and `zones` props) and requires no changes to display the adjusted score. The new ELO Skill Timeline chart reuses the identical Recharts `LineChart` pattern from `EndgameConvRecovChart.tsx`.

**Core technologies:**
- Python `statistics` stdlib: mean/stdev for normalized opponent rating — no new dependency needed
- SQLAlchemy 2.x `func.avg()`: already used for existing aggregations, no changes required
- PostgreSQL 18 `CASE WHEN`/`AVG`: standard SQL, no new features required
- Recharts `LineChart`: existing usage pattern in `EndgameConvRecovChart.tsx` — clone for ELO timeline
- `EndgameGauge.tsx`: already accepts any float value; reuse as-is for adjusted score display

### Expected Features

**Must have (table stakes):**
- Opponent-strength context for skill metrics — users who understand rating systems expect this; raw percentages without opponent quality context are misleading
- Sufficient sample size enforcement — explicit minimum game count threshold before displaying ELO-adjusted score; `elo_adjusted: bool` flag in API response from day one
- Trend/timeline for the ELO-adjusted skill score — all major chess analytics platforms show metrics over time; a single current score is less actionable
- Hover/tooltip explaining ELO adjustment formula — opaque numbers drive churn; info popover pattern already in use on Endgames tab

**Should have (competitive differentiators):**
- ELO-adjusted endgame skill gauge — no public tool adjusts endgame conversion/recovery by opponent strength; genuine gap versus lichess Insights, chess.com Insights, and Aimchess
- Cross-platform rating normalization (lichess to chess.com equivalent) — FlawChess is uniquely positioned here since it ingests both platforms; tapering offset approximation disclosed transparently
- Opening drawishness metric — draw rate surfaced as an explicit named metric in Opening Statistics; already computable from existing WDL data with zero backend work
- Opening risk as WDL entropy per candidate move — inline in existing `get_next_moves()`, zero additional SQL

**Defer (v2+):**
- ELO adjustment for opening statistics — causal direction is murky; defer until endgame version validated
- Per-endgame-type ELO adjustment breakdown — additive refinement after aggregate version ships
- Server-side eval computation for unanalyzed games — requires dedicated compute tier not feasible on current VPS
- Opening volatility from eval data (RMS of win-probability changes) — requires per-move eval, available only for analyzed games; significant additional pipeline complexity

### Architecture Approach

All v1.8 features follow the strict 3-layer pattern: routers (HTTP only) → services (business logic) → repositories (SQL only). No new files are needed at the directory level — all additions are new functions or modified functions within existing modules. The key architectural decisions are: (1) rating normalization lives entirely in `endgame_service.py` as named pure functions with module-level constants, not in SQL; (2) `elo_adjusted_skill` is added to `EndgamePerformanceResponse` rather than a new endpoint, avoiding dual loading state management for one screen section; (3) opening risk entropy is computed inline in `get_next_moves()` from already-fetched WDL counts, with zero extra queries; (4) the new `query_elo_skill_rows()` is a separate repository function from the existing `query_endgame_entry_rows()` to avoid silently breaking positional tuple unpacking in existing callers.

**Major components:**
1. `endgame_service.py` — new functions: `_normalize_rating()`, `_compute_elo_adjusted_skill()`, `get_elo_skill_timeline()`, `_compute_elo_skill_rolling_series()`
2. `endgame_repository.py` — new `query_elo_skill_rows()` alongside existing `query_endgame_entry_rows()`
3. `schemas/endgames.py` — `EndgamePerformanceResponse` extended with `adjusted_endgame_skill: float` and `elo_adjusted: bool`; new `EloSkillTimelinePoint` and `EloSkillTimelineResponse`
4. `routers/endgames.py` — new `GET /endgames/elo-timeline` endpoint
5. `EloSkillTimelineChart.tsx` — new single-line Recharts component cloned from `EndgameConvRecovChart.tsx` pattern
6. `openings_service.py` — new `_wdl_entropy()` pure function; `get_next_moves()` attaches `risk: float` per move

### Critical Pitfalls

1. **Opponent color logic inverted** — `user_color == "white"` means `opponent_rating == black_rating` (the inverse of the user-rating pattern already in `stats_repository.py`). This is a silent bug that produces a plausible-looking but wrong adjusted score. Write a unit test asserting correct derivation before wiring any values into the formula.

2. **NULL opponent ratings silently bias the adjustment** — `white_rating`/`black_rating` are nullable. SQL `AVG()` and Python averaging both silently skip NULLs with no warning. Track `rated_games_count`, define `MIN_RATED_GAMES_FOR_ELO_ADJUSTMENT = 10`, and include `elo_adjusted: bool` in the API response from day one so the frontend can show "Raw score (insufficient rating data)" instead of a false ELO-adjusted label.

3. **ELO gauge zone thresholds break if `endgame_skill` field is replaced** — the adjusted score can exceed 100 when facing above-reference opponents; existing zone thresholds are calibrated to the raw [0, 100] domain. Add `adjusted_endgame_skill` as a new field; never replace `endgame_skill` in-place. Decide the adjusted score display domain before writing any gauge code.

4. **Rolling ELO timeline missing pre-fill pattern** — the existing `get_endgame_timeline()` fetches all historical data (no recency filter) then filters output points in Python. Omitting this from the new ELO timeline causes cold-start artifacts when recency filters are active. Copy the two-step pattern (`recency_cutoff=None` to DB, filter output points in Python) explicitly.

5. **Opening risk conflating draw rate with loss rate** — `1 - draw_rate` penalizes sharp openings where the user wins sharply (Sicilian, King's Indian Attack) and rewards passive drawish lines (Berlin Defense). Define opening risk as loss-focused (WDL entropy or `loss_pct`) and validate against a Berlin Defense position before shipping.

## Implications for Roadmap

Based on research, suggested phase structure:

### Phase 1: ELO-Adjusted Endgame Skill — Backend + Gauge
**Rationale:** All data is already available (no migration needed), the formula is well-defined in the backlog spec, and the frontend change is minimal (swap gauge value, add conditional label). Delivers the headline feature immediately. Unit tests for `_normalize_rating()` and `_compute_elo_adjusted_skill()` catch the color-inversion and NULL pitfalls before any frontend work proceeds.
**Delivers:** `adjusted_endgame_skill: float` and `elo_adjusted: bool` in `EndgamePerformanceResponse`; gauge updated to show adjusted value with conditional "ELO-adjusted" vs "Raw score" label; info popover explaining adjustment
**Addresses:** ELO-adjusted skill (P1 must-have), cross-platform normalization (P1 must-have), sample size enforcement (table stakes)
**Avoids:** Color logic inversion (unit test required before wiring), NULL rating silent bias (`elo_adjusted: bool` flag), gauge semantic breakage (new field, not replacement of existing `endgame_skill`)

### Phase 2: ELO-Adjusted Skill Timeline
**Rationale:** Reuses the same `query_elo_skill_rows()` infrastructure from Phase 1. Adding the timeline is a new endpoint plus a new frontend chart component — fully independent after Phase 1 backend is complete. Lowest-risk phase because the Recharts and rolling-window patterns are already proven in the codebase.
**Delivers:** `GET /endgames/elo-timeline` endpoint; `EloSkillTimelineChart.tsx` rolling window chart rendered in Endgames stats tab
**Uses:** `_compute_elo_skill_rolling_series()` mirroring `_compute_conv_recov_rolling_series`; `query_elo_skill_rows()` from Phase 1
**Avoids:** Rolling pre-fill omission (copy the two-step pattern from `get_endgame_timeline()` explicitly, not from scratch)

### Phase 3: Opening Risk — WDL Entropy Per Move
**Rationale:** Fully independent from Phases 1 and 2 (different service, different schema, different frontend component). Zero new SQL queries. The formula definition is where the pitfall lives — define and document `_wdl_entropy()` explicitly before writing any code, and validate against a Berlin Defense test case before shipping.
**Delivers:** `risk: float` field on `NextMoveEntry`; risk badge per move row in move explorer; opening drawishness surfaced as explicit draw rate metric (zero additional backend work)
**Addresses:** Opening risk differentiator (P1 must-have); opening drawishness surfacing (same phase, trivially included)
**Avoids:** Risk-score inversion (formula defined as entropy over WDL, not `1 - draw_rate`); Berlin Defense test validates formula before merge

### Phase Ordering Rationale

- Phase 1 before Phase 2: Phase 2 reuses `query_elo_skill_rows()` from Phase 1 backend; splitting keeps PR sizes manageable and allows independent validation of the performance endpoint before adding the timeline endpoint
- Phase 3 is fully independent: opening risk touches a completely different service/repository/component chain and can be interleaved or run after Phases 1-2 without dependency
- Opening drawishness (surfacing draw rate as named metric in Opening Statistics) is zero-backend-work and belongs in Phase 3 at negligible additional cost
- Per-endgame-type ELO breakdown and opening volatility from eval are explicitly deferred — they add complexity without completing the headline features first

### Research Flags

No phases require a `/gsd-research-phase` step. All key decisions are resolved in the research files.

Phases with standard patterns (skip research):
- **Phase 1 (ELO backend + gauge):** Architecture fully specified from direct codebase inspection in ARCHITECTURE.md. Implementation plan detailed with precise component list. No novel patterns.
- **Phase 2 (ELO timeline):** Direct clone of `get_conv_recov_timeline()` / `EndgameConvRecovChart.tsx`. No new patterns.
- **Phase 3 (opening risk):** WDL entropy formula well-specified in ARCHITECTURE.md. Only open decision is final formula choice (entropy vs `loss_pct`) — resolve in planning, not research.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | No new dependencies; existing stack validated in production. Only stdlib and already-imported libraries involved. |
| Features | HIGH (formula mechanics) / MEDIUM (normalization constants) | ELO adjustment formula and WDL entropy formula are well-specified. Lichess-to-chess.com offset constants are empirical approximations from community data — treat as calibration values, not authoritative numbers. |
| Architecture | HIGH | Based on direct codebase inspection of all affected modules in v1.7 (shipped 2026-04-03). Component boundaries, query shapes, and integration points are precisely documented. |
| Pitfalls | HIGH | Pitfalls 1-4 are directly observable from the codebase (nullable columns in `app/models/game.py`, positional tuple unpacking in existing callers, rolling series pre-fill pattern in `endgame_service.py`). Pitfall 5 is domain-verified. |

**Overall confidence:** HIGH for implementation path; MEDIUM for calibration of normalization constants

### Gaps to Address

- **Lichess offset constants:** The formula `offset = max(0, 350 - (lichess_rating - 1400) * 0.3)` is an approximation. Implement as named module-level constants (`_LICHESS_BASE_OFFSET`, `_LICHESS_TAPER_PER_POINT`, `_LICHESS_TAPER_START`) with a docstring calling them calibration values subject to revision. Long-term accuracy gap: monitor adjusted scores for mixed-platform users after ship and revise constants if systematic bias appears.
- **Opening risk formula final choice:** Research recommends WDL entropy but notes `loss_pct` is also viable. Resolve in Phase 3 planning by deciding which is more actionable to users. Validate against Berlin Defense test case before merging.
- **Adjusted score display domain:** The ELO-adjusted score can exceed 100 for users consistently facing above-reference opponents. Decide gauge display domain (cap at 100, scale to 120, or show overflow indicator) in Phase 1 planning before writing any gauge code.
- **Entry row deduplication for opponent rating average:** `query_endgame_entry_rows` returns per-(game, endgame_class) rows — a single game may appear multiple times (multiple endgame phases). Compute `avg_normalized_opponent_rating` by deduplicating by `game_id` first to avoid over-weighting games with multiple endgame classifications. Resolve in Phase 1 implementation.

## Sources

### Primary (HIGH confidence)
- Direct codebase inspection: `app/services/endgame_service.py`, `app/repositories/endgame_repository.py`, `app/models/game.py`, `app/repositories/stats_repository.py`, `app/schemas/endgames.py`, `frontend/src/components/charts/EndgamePerformanceSection.tsx`, `EndgameGauge.tsx`, `useEndgames.ts` — architecture and integration findings
- `.planning/ROADMAP.md` Phase 999.5 backlog spec — ELO normalization formula, reference rating 1500, adjustment formula
- [Python `statistics` module docs](https://docs.python.org/3/library/statistics.html) — stdlib `mean()`, `stdev()` confirmed in Python 3.4+
- [asyncpg issue #127](https://github.com/MagicStack/asyncpg/issues/127) — 32767 parameter limit confirmed

### Secondary (MEDIUM confidence)
- [ChessGoals.com Rating Comparison](https://chessgoals.com/rating-comparison/) — cross-platform rating offset pattern (2,489 players, RD < 150)
- [NoseKnowsAll Universal Rating Converter 2024](https://lichess.org/@/NoseKnowsAll/blog/introducing-a-universal-rating-converter-for-2024/X2QAH27t) — offset varies by skill level; classical/rapid only; blitz excluded from universal formula
- [jk_182: Quantifying Volatility of Chess Games](https://lichess.org/@/jk_182/blog/quantifying-volatility-of-chess-games/H6MWvX98) — WDL entropy vs eval-swing volatility distinction
- [Why Opening Statistics Are Wrong — D2D4C2C4](https://lichess.org/@/D2D4C2C4/blog/why-opening-statistics-are-wrong/VKNZ1oKw) — FlawChess user-scoped methodology avoids aggregate DB distortion

### Tertiary (LOW confidence)
- [The Ultimate Chess.com vs Lichess Rating Comparison — attackingchess.com](https://www.attackingchess.com/the-ultimate-chess-com-vs-lichess-rating-comparison/) — empirical offset data; varies, not authoritative
- [lichess forum: rating conversion formulae](https://lichess.org/forum/general-chess-discussion/rating-conversion-formulae-lichessorg--chesscom) — community linear regression formulas per time control; methodology unclear
- [Aimchess analytics features](https://aimchess.com/) — feature list for competitor comparison; features may change

---
*Research completed: 2026-04-04*
*Ready for roadmap: yes*
