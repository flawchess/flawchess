# Phase 70: Backend opening insights service - Context

**Gathered:** 2026-04-26 (revised 2026-04-26 after algorithm redesign)
**Status:** Ready for planning
**Requirements:** INSIGHT-CORE-01, INSIGHT-CORE-02, INSIGHT-CORE-03, INSIGHT-CORE-04, INSIGHT-CORE-05, INSIGHT-CORE-06, INSIGHT-CORE-07, INSIGHT-CORE-08, INSIGHT-CORE-09

<domain>
## Phase Boundary

Backend-only. Build a user-scoped `opening_insights_service` (and the supporting Pydantic schemas + thin router) that produces a structured 4-section response of ranked, deduplicated `OpeningInsightFinding` payloads under the user's active filter set.

The algorithm is **first-principles, not opening-list-driven**: a single SQL aggregation per (user, color) over `game_positions` transitions in the early-to-mid opening window (entry_ply ∈ [3, 16]) returns every (entry_hash, candidate_san) pair where ≥20 games of evidence cleared the strength/weakness threshold (>0.55 win or loss rate). Phase 70 reuses `apply_game_filters` shared filter logic and the `game_positions` Zobrist-hash schema. Adds **one Alembic migration** for a partial composite index that makes the aggregation index-only-scannable for heavy users (verified 816 ms for the Hikaru-class outlier with 65k games / 5.7M positions; 65 ms for a median user). No LLM, no precompute, no benchmark-DB consumption. Phase 71 (Stats subtab UI), 72 (Moves subtab inline bullets), 73 (meta-recommendation, stretch), 74 (bookmark badge, stretch) build on top.

Three REQUIREMENTS.md amendments emerge from this discussion (apply at Phase 70 commit time, see decisions D-15 and D-17):
1. INSIGHT-CORE-02 is rewritten end-to-end. The "scan top-N most-played openings per color" framing is replaced by "scan all (entry, candidate) transitions in entry_ply ∈ [3, 16] with ≥20 games per candidate".
2. INSIGHT-CORE-04 keeps its `MIN_GAMES_PER_CANDIDATE` floor concept but the value moves from 10 → 20.
3. INSIGHT-CORE-05 classifier switches from `score = (W + D/2) / n` to `win_rate = W / n` (strengths) / `loss_rate = L / n` (weaknesses) with a strict `>` boundary at 0.55 so the classification matches `frontend/src/lib/arrowColor.ts` exactly.

Bookmarks are **excluded from the discovery algorithm** entirely (see D-18). They remain a UI feature for explicit user tracking; Phase 74 (stretch) maps insights → bookmarks for a badge but doesn't influence what gets discovered.

</domain>

<decisions>
## Implementation Decisions

### Algorithm Shape (replaces INSIGHT-CORE-02 entry-source semantics)

- **D-30:** Discovery is a **single SQL aggregation per color** over `game_positions` transitions, NOT a per-entry next-moves scan.
  ```sql
  WITH transitions AS (
    SELECT gp.game_id, gp.ply, gp.move_san,
           LAG(gp.full_hash) OVER (PARTITION BY gp.game_id ORDER BY gp.ply) AS entry_hash
    FROM game_positions gp
    WHERE gp.user_id = :uid AND gp.ply BETWEEN 1 AND 17
  )
  SELECT t.entry_hash, t.move_san,
         COUNT(DISTINCT g.id) AS n,
         COUNT(DISTINCT g.id) FILTER (WHERE <win_cond>)  AS w,
         COUNT(DISTINCT g.id) FILTER (WHERE <draw_cond>) AS d,
         COUNT(DISTINCT g.id) FILTER (WHERE <loss_cond>) AS l
  FROM transitions t
  JOIN games g ON g.id = t.game_id
  WHERE g.user_id = :uid AND g.user_color = :color
    AND <apply_game_filters predicates>
    AND t.ply BETWEEN 4 AND 17
    AND t.entry_hash IS NOT NULL
  GROUP BY t.entry_hash, t.move_san
  HAVING COUNT(DISTINCT g.id) >= 20
     AND (
       COUNT(DISTINCT g.id) FILTER (WHERE <win_cond>)::float / COUNT(DISTINCT g.id) > 0.55
       OR
       COUNT(DISTINCT g.id) FILTER (WHERE <loss_cond>)::float / COUNT(DISTINCT g.id) > 0.55
     )
  ```
  Two queries per request (one for `user_color = 'white'`, one for `'black'`). Each returns at most a few hundred candidate-rows pre-classification. Python finishes the work: classify, attribute, dedupe, rank, cap.
- **D-31:** **New Alembic migration adds a partial composite index** that makes the LAG-based transitions CTE an index-only scan:
  ```sql
  CREATE INDEX ix_gp_user_game_ply
    ON game_positions(user_id, game_id, ply)
    INCLUDE (full_hash, move_san)
    WHERE ply BETWEEN 1 AND 17;
  ```
  Column order matters: `(user_id, game_id, ply)` is exactly the ordering the LAG window function needs (PARTITION BY game_id ORDER BY ply within a user), so PostgreSQL streams rows directly without a re-sort. INCLUDE keeps `full_hash` and `move_san` in the index leaves so the table is never touched (`Heap Fetches: 0`). Partial-on-`ply ≤ 17` keeps the index small (~9% of table size — covers entry_ply 3..16 + their successor candidate moves). **Verified 2026-04-26 against dev DB**: user 7 (Hikaru, 65,440 games / 5.7M positions) drops from 2.0 s to 816 ms; user 28 (5,045 games / 336k positions) sits at 65 ms.
- **D-32:** `MIN_ENTRY_PLY = 3` and `MAX_ENTRY_PLY = 16` are the entry-position bounds (inclusive, both ends). Candidate ply is therefore 4..17. The CTE filters `ply BETWEEN 1 AND 17` (one ply earlier so the LAG can see the entry) and the outer query filters `t.ply BETWEEN 4 AND 17`. min_ply=3 skips opening-move noise (1.e4, 1.d4, etc.); max_ply=16 (= move 8 by black, move 8.5 by white) covers all opening theory of practical interest. Entries beyond ply 16 rarely clear `n ≥ 20` anyway.
- **D-33:** `MIN_GAMES_PER_CANDIDATE = 20` — the evidence floor on each `(entry_hash, candidate_san)` pair. Tightened from the original INSIGHT-CORE-04 floor of 10. At n=20 the binomial 95% CI on a 60% rate is ~±22%, which is loose but acceptable when the W/D/L counts are visible on the finding card. The threshold is cheap to revisit after Phase 71 telemetry.

### Response Structure (reframes INSIGHT-CORE-02 / INSIGHT-CORE-07)

- **D-01:** Response is structured by color × class into FOUR named lists:
  ```python
  class OpeningInsightsResponse(BaseModel):
      white_weaknesses: list[OpeningInsightFinding]
      black_weaknesses: list[OpeningInsightFinding]
      white_strengths:  list[OpeningInsightFinding]
      black_strengths:  list[OpeningInsightFinding]
  ```
  Phase 71 renders four labeled sections ("⬜ White Opening Weaknesses", "⬛ Black Opening Weaknesses", "⬜ White Opening Strengths", "⬛ Black Opening Strengths"). The endpoint always returns all four lists; empty sections are valid empty-state.
- **D-02:** Caps from INSIGHT-CORE-07 are applied **per section**: top-5 weaknesses + top-3 strengths per color. Visible ceiling on screen is `5 + 5 + 3 + 3 = 16` findings.
- **D-03:** Each `OpeningInsightFinding` carries an explicit `color: Literal["white", "black"]` field so the same payload is reusable in Phase 72's Moves-tab inline bullets without binning by section.

### Classification & Severity (aligns INSIGHT-CORE-05 with `arrowColor.ts`)

- **D-04:** Classification uses **`win_rate = W / n`** and **`loss_rate = L / n`** with a strict `>` boundary at 0.55:
  - `weakness` if `loss_rate > 0.55`
  - `strength` if `win_rate > 0.55`
  - Otherwise neutral, dropped at the SQL HAVING clause.
  Mirrors `frontend/src/lib/arrowColor.ts:39-61` exactly: `winPct > 55 → light/dark green`; `lossPct > 55 → light/dark red`. A position rendered grey on the board never surfaces as a finding.
- **D-05:** Severity tier maps 1:1 onto the arrow's two color shades:
  - `severity = "major"` if the qualifying rate is `≥ 0.60` (dark green / dark red)
  - `severity = "minor"` if the qualifying rate is in `(0.55, 0.60)` (light green / light red)
  - Schema: `classification: Literal["weakness", "strength"]` + `severity: Literal["minor", "major"]`.
- **D-06:** `score = (W + D/2) / n` is still computed and exposed in the payload (per INSIGHT-CORE-08) for downstream display use — but it is NOT the classifier. `win_rate`, `loss_rate`, and `score` all appear on the finding alongside `wins, draws, losses, n_games`.

### Ranking & Cap Application

- **D-07:** Within each of the four sections, sort by **`(severity desc, n_games desc)`** — all `major` findings appear before any `minor`, and within a tier larger `n_games` wins.
- **D-08:** Caps applied AFTER the sort: take the first 5 (weaknesses) or 3 (strengths) per color section.
- **D-09:** No built-in recency weighting in the ranking formula. The user's active recency filter already lets them restrict the window if they want recent-only findings.

### Filter Contract & Endpoint

- **D-10:** New Pydantic request model `OpeningInsightsRequest` in a new file `app/schemas/opening_insights.py`. Mirrors the existing `/openings/*` and `/stats/most-played-openings` query-param surface 1:1:
  ```python
  recency: str | None = None
  time_control: list[str] | None = None
  platform: list[str] | None = None
  rated: bool | None = None
  opponent_type: str = "human"
  opponent_strength: Literal["any", "stronger", "similar", "weaker"] = "any"
  elo_threshold: int = DEFAULT_ELO_THRESHOLD
  color: Literal["all", "white", "black"] = "all"
  ```
- **D-11:** The v1.11 `FilterContext` in `app/schemas/insights.py` is **not** reused. Decoupling avoids cross-feature breakage when one filter shape evolves (rated 2-state vs 3-state, etc.).
- **D-12:** The `color` filter is **orthogonal to the section structure**: the endpoint returns all four sections regardless of `color=white/black/all`. Phase 71 may optionally collapse off-color sections in the UI; backend contract is invariant. INSIGHT-CORE-01 is satisfied by the other six filters reshaping findings.
  - **Optimization permitted:** when `color != "all"`, the planner MAY skip the SQL query for the unused color and return an empty list for those two sections. ~50% latency saving when the user has narrowed the view.
- **D-13:** Route placement: **`POST /api/insights/openings`**. Symmetric with `POST /api/insights/endgame`. The router lives in `app/routers/insights.py` (extend the existing file). POST + JSON body avoids URL-length issues on `time_control[]` / `platform[]`.
- **D-14:** The endpoint MUST NOT inherit the v1.11 `_validate_full_history_filters` gate from `app/routers/insights.py:39-72`. That gate is endgame-LLM-specific. For openings, every filter must reshape findings per INSIGHT-CORE-01.

### Bookmarks (removed from algorithm)

- **D-18:** **Bookmarks are NOT consumed by the discovery algorithm.** The original design (D-18 / D-19 in the pre-redesign spec) tried to use bookmarks as an auxiliary entry source. With the first-principles transition aggregation, every position the user has played is implicitly scanned — bookmarks add no algorithmic value. Phase 74 (stretch) still maps the response back to bookmarks for a UI badge, but at the visualization layer; bookmarks never influence what's discovered.
- **D-20:** No per-user total-game floor. With four always-present sections, "mostly empty" is normal for new users; Phase 71's empty-state copy ("no findings cleared the threshold — try lowering filters or import more games") handles the message uniformly.

### Dedupe & Attribution (resolves INSIGHT-CORE-06)

- **D-21:** Dedupe on `resulting_position_hash` (the Zobrist hash of the position AFTER the candidate move) is **scoped within a single color section**, not cross-color. Same hash appearing in both white and black sections is preserved as two distinct findings — they describe genuinely different repertoire issues even if a transposition makes the positions identical.
- **D-22:** Attribution lookup: for each surviving finding, query `openings` table rows where `full_hash == entry_hash`; pick the row with `MAX(ply_count)` — deepest opening = most specific name. Implementation: one batched `SELECT ... WHERE full_hash IN (...)` covering all surviving findings (~16 max after caps) per request.
- **D-23:** Fallback when no `openings` row matches the entry hash → walk back along the entry's lineage. Concretely: in the same SQL that computes transitions, also expose the SAN sequence (or the parent_hash chain) so Python can probe `openings` table at successive parent positions until a match is found. If none is found at any depth, set `opening_name = "<unnamed line>"` and `opening_eco = ""`. Empty-string convention matches `OpeningWDL.full_hash` handling in `app/schemas/stats.py`.
- **D-24:** Cross-entry dedupe within a section: if two different entries lead to the same resulting hash (e.g., via transposition), keep ONE finding — the one whose **entry** has the higher `ply_count` from the openings attribution (deeper/more-specific entry wins). Rare in practice but the rule is locked.
- **D-25:** Deep-link target = entry FEN + candidate-move SAN (NOT the resulting FEN). User lands at the position where the choice was made, with the candidate move highlighted. Payload field: `entry_fen: str` + `candidate_move_san: str` — flat, no nested object. The entry FEN is reconstructed by replaying the entry-position SAN sequence from the start, NOT stored on `game_positions` (no `fen` column there).

### Schema & Service Layout (Claude's Discretion)

- **D-26:** New file `app/schemas/opening_insights.py` for `OpeningInsightsRequest`, `OpeningInsightFinding`, `OpeningInsightsResponse`. Do NOT extend `app/schemas/insights.py` (endgame-LLM-coupled).
- **D-27:** New file `app/services/opening_insights_service.py` for the compute pipeline. Single public entry point `compute_insights(session, user_id, request) -> OpeningInsightsResponse`. New repository function in `app/repositories/openings_repository.py` (or a new `opening_insights_repository.py` — planner picks) for the transition-aggregation SQL — do NOT inline raw SQL in the service.
- **D-28:** Configuration constants live as module-level constants at the top of `opening_insights_service.py`:
  ```python
  MIN_ENTRY_PLY = 3
  MAX_ENTRY_PLY = 16
  MIN_GAMES_PER_CANDIDATE = 20
  LIGHT_THRESHOLD = 0.55          # mirrors arrowColor.ts LIGHT_COLOR_THRESHOLD/100
  DARK_THRESHOLD = 0.60           # mirrors arrowColor.ts DARK_COLOR_THRESHOLD/100
  WEAKNESS_CAP_PER_COLOR = 5
  STRENGTH_CAP_PER_COLOR = 3
  ```
  Pattern follows `arrowColor.ts` (`MIN_GAMES_FOR_COLOR`, `LIGHT_COLOR_THRESHOLD`, `DARK_COLOR_THRESHOLD`) — no env vars, no DB-stored settings, no separate registry module like `endgame_zones.py`. Tunable via PR.
- **D-29:** No service-layer caching in Phase 70 (INSIGHT-CORE-09). With the index in place, even Hikaru-class outliers complete in <1 s.

### REQUIREMENTS.md / ROADMAP / CHANGELOG Amendments (apply at Phase 70 commit time)

- **D-15:** **INSIGHT-CORE-02 is rewritten end-to-end.** Old text described a "top-10 most-played per color × per-position next-moves scan". New text describes the single-SQL transition aggregation in entry_ply ∈ [3, 16] with `MIN_GAMES_PER_CANDIDATE = 20`. Bookmarks are explicitly out of scope as an algorithmic input. The phase 70 success-criterion 2 in `.planning/milestones/v1.13-ROADMAP.md` ("scan top-10 most-played openings per color") needs the same rewrite.
- **D-16:** **INSIGHT-CORE-04 floor moves from `n ≥ 10` to `n ≥ 20`.**
- **D-17:** Apply all amendments by editing `.planning/REQUIREMENTS.md` (top of file) AND `.planning/milestones/v1.13-ROADMAP.md` Phase 70 success-criteria block in the same commit that lands the implementation, with a CHANGELOG.md `[Unreleased]` § Changed entry describing both the algorithm shift (top-N entry-source → first-principles transition aggregation) and the classifier alignment with arrow coloring.

### Attribution Edge Cases (added during revision 2026-04-26)

- **D-34:** Unmatched-lineage findings are **dropped, not sentinel-attributed.** When the entry hash matches no Opening AND the parent-lineage walk (D-23) exhausts without finding a named ancestor, the finding is omitted from the response entirely — never surfaced with an empty/sentinel `entry_fen` or with the `<unnamed line>` name as a fallback for an unreachable position. This replaces an earlier (BLOCKER-1, revision 2026-04-26) instruction in Plan 70-04 to fall back to `chess.Board().fen()` (the initial position FEN), which would have produced an incorrect deep-link target — a finding the user lands on the empty start position for is worse than no finding at all. The strict ply-3..16 entry window plus the seeded openings table covers the vast majority of practical cases; Phase 71 telemetry can revisit if the unmatched rate exceeds expectations. Sentry tag `openings.attribution.unmatched_dropped` may be set to track the rate.

### Claude's Discretion

- Implementation file layout details: file paths above are recommendations; planner finalizes.
- Exact Pydantic field types and `Literal` enumerations: planner picks tightest types matching existing `app/services/stats_service.py` and `app/repositories/openings_repository.py` signatures.
- The 4-section response can equivalently be modeled as a flat `findings: list[OpeningInsightFinding]` with frontend binning by `(color, classification)`. The 4-named-lists shape is preferred for explicitness.
- Whether the parent-lineage walk for D-23 attribution is a recursive CTE in SQL, a batched second query, or an in-Python walk over a `parent_hash → opening_name` map. Either is fine; pick whatever keeps the latency budget.
- Error handling: standard Sentry capture pattern per CLAUDE.md (no variable-in-message errors). Empty findings under all filters is NOT an error — return empty sections.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase Source Documents
- `.planning/seeds/SEED-005-opening-weakness-insights.md` — full architecture rationale, why self-referential is sufficient, prior-work list. The "Why Self-Referential Is Sufficient" and "Prior Work (Do Not Re-Derive)" sections are load-bearing.
- `.planning/REQUIREMENTS.md` §INSIGHT-CORE-01..INSIGHT-CORE-09 — locked requirements for this phase. **Note: D-15 / D-16 / D-17 amend INSIGHT-CORE-02, INSIGHT-CORE-04, INSIGHT-CORE-05 — apply edits at Phase 70 commit time.**
- `.planning/milestones/v1.13-ROADMAP.md` Phase 70 — success criteria. Note success-criterion 2 (top-10 entry source) and success-criterion 4 (ranking formula resolved here) need amendment per D-15.
- `.planning/PROJECT.md` §"v1.13 Opening Insights" — milestone scope, target features.

### Existing Backend (read-only inputs / reuse points)
- `app/repositories/query_utils.py::apply_game_filters` — the single shared filter implementation (CLAUDE.md "Shared Query Filters"). Phase 70's transition-aggregation query embeds this directly in the JOIN-to-games predicates.
- `app/repositories/openings_repository.py::query_next_moves` (line 359) — informative reference for per-position aggregation; Phase 70 does NOT call this. The new transition-aggregation query is structurally different (one query for ALL entries vs one query per entry).
- `app/services/stats_service.py::recency_cutoff` — converts the `recency` string filter to a `datetime` cutoff. Phase 70 reuses identically.
- `app/models/opening.py::Opening` — `(eco, name, ply_count, fen, full_hash, pgn)`. `ply_count` is the deepest-attribution disambiguator for D-22 and the cross-entry dedupe tiebreaker for D-24.

### New Schema
- **`alembic/versions/{rev}_add_gp_user_game_ply_index.py`** (NEW) — migration adding `ix_gp_user_game_ply` partial composite index per D-31. Index DDL exactly:
  ```sql
  CREATE INDEX ix_gp_user_game_ply
    ON game_positions(user_id, game_id, ply)
    INCLUDE (full_hash, move_san)
    WHERE ply BETWEEN 1 AND 17;
  ```
  Migration includes a comment block explaining the column ordering rationale (matches LAG window's PARTITION BY / ORDER BY) so a future maintainer doesn't reorder the columns "for symmetry" with sibling indexes.
  - Also update `app/models/game_position.py::GamePosition.__table_args__` to declare the index alongside the existing ones, so `alembic --autogenerate` doesn't regress.
  - Use `op.create_index(..., postgresql_concurrently=True)` and split into a separate revision from any data-modifying migrations (CONCURRENTLY can't run inside a transaction).

### Existing Frontend (alignment source — backend MUST match exactly)
- `frontend/src/lib/arrowColor.ts` lines 15-29 — `MIN_GAMES_FOR_COLOR = 10` (NOT used by Phase 70 — Phase 70's floor is 20), `LIGHT_COLOR_THRESHOLD = 55`, `DARK_COLOR_THRESHOLD = 60`. **The thresholds in `app/services/opening_insights_service.py` MUST match these literal values.** Phase 70 should add a CI test (Python regex-parse `arrowColor.ts` and assert equality with `LIGHT_THRESHOLD * 100` and `DARK_THRESHOLD * 100`, similar to `tests/services/test_endgame_zones_consistency.py`) so a future arrow-color tweak doesn't silently de-sync the insights classifier.
- `frontend/src/lib/arrowColor.ts::getArrowColor` lines 39-61 — the strict `> 55` boundary semantics. D-04 references this exact behavior.
- `frontend/src/lib/arrowColor.test.ts` — boundary fixtures. Reference for Phase 70's classifier unit tests.

### v1.11 Insights Reference Patterns (informative, NOT reused)
- `app/services/insights_service.py` — reference for "service that orchestrates per-window compute". Phase 70 follows the same single-public-entry-point pattern but does NOT import or extend.
- `app/schemas/insights.py::FilterContext` (line 109) — the v1.11 filter shape. Phase 70 deliberately decouples (D-11).
- `app/routers/insights.py` (whole file) — reference for the router/service split idiom. Phase 70 extends this file with the `POST /insights/openings` route (D-13). The `_validate_full_history_filters` gate (lines 39-72) is **not** applied (D-14).

### Project Conventions
- `CLAUDE.md` §"Coding Guidelines" — type safety, ty compliance, no magic numbers, `Literal[...]` for enums.
- `CLAUDE.md` §"Critical Constraints" — `AsyncSession` not safe for `asyncio.gather`. Phase 70's two color queries are sequential on the same session.
- `CLAUDE.md` §"Backend Layout" — `routers/` HTTP only, `services/` business logic, `repositories/` DB access. Phase 70 adds files in all three layers (one router edit, one new service, one new repo function or file, one Alembic migration).
- `CLAUDE.md` §"Router Convention" — `APIRouter(prefix="/insights", tags=["insights"])` already exists; new route uses relative path `/openings` (NOT `/insights/openings`).
- `CLAUDE.md` §"Error Handling & Sentry" — `sentry_sdk.capture_exception` in non-trivial except blocks; `set_context` for variable data; never embed variables in error messages.

### Performance Evidence (verified 2026-04-26 against dev DB)
- `EXPLAIN (ANALYZE, BUFFERS)` numbers below are baseline expectations — Phase 70 plan-checker should flag any regression.

| User | Games | Positions | max_ply=16, n≥20, with `ix_gp_user_game_ply` |
|------|-------|-----------|------|
| 28 (median) | 5,045 | 336k | **65 ms** (Index Only Scan, Heap Fetches: 0) |
| 7 (Hikaru, p99) | 65,440 | 5.7M | **816 ms** (Index Only Scan, Heap Fetches: 0) |

Without the index, user 7 takes 2.0 s (parallel seq scan + disk-spilled merge sort on game_id, ply). The index ordering `(user_id, game_id, ply)` is load-bearing — `(user_id, ply, ...)` does NOT win because the LAG window's PARTITION BY game_id requires a re-sort.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`apply_game_filters`** (`app/repositories/query_utils.py`) — embed directly in the JOIN-to-games predicates of the new transition-aggregation query. This is the single source of truth for time control, platform, rated, opponent type, recency, opponent strength, and color filtering.
- **`recency_cutoff`** helper (`app/services/stats_service.py`) — converts the `recency` string filter to a `datetime` cutoff. Phase 70 reuses identically.
- **`Opening` SQLAlchemy model** (`app/models/opening.py:7`) — `(eco, name, ply_count, fen, pgn, full_hash)`. The single batched `SELECT ... WHERE full_hash IN (...)` for D-22's deepest-opening attribution.
- **`GamePosition` model** (`app/models/game_position.py`) — note that `move_san` and `full_hash` are already there; no schema change other than the new index. **There is no `fen` column on `game_positions`** — entry FEN reconstruction for D-25 deep-link uses python-chess to replay the SAN sequence from the start position.

### Established Patterns
- **Service-layer composition over repositories** — `app/services/openings_service.py::get_next_moves` orchestrates several repository calls then post-processes in Python. Phase 70 follows the same shape (one or two repo calls + Python classify/dedupe/rank/cap).
- **Sequential awaits on a single `AsyncSession`** — CLAUDE.md mandates this; SQLAlchemy AsyncSession is not safe for concurrent gather. Phase 70 runs the two color queries sequentially.
- **Pydantic v2 with `Literal[...]` for enums** — every state field on `OpeningInsightFinding` (`color`, `classification`, `severity`) is a `Literal`. ty compliance follows.
- **No magic numbers, named module-level constants** — D-28's full constant list lives at the top of `opening_insights_service.py`.
- **String-form full_hash in API responses** (`app/schemas/stats.py::OpeningWDL.full_hash: str`) — 64-bit ints are stringified at the API boundary because JSON's number type loses precision. Phase 70's `OpeningInsightFinding.entry_full_hash` and `resulting_full_hash` follow the same convention.
- **Display-name "vs. " prefix for off-color rows** (`query_top_openings_sql_wdl` lines 250-260) — Phase 70 doesn't use that helper, but if attribution-via-openings yields a name whose ply parity disagrees with the user's color, apply the same prefix in the service layer for visual consistency with stats UI.
- **Partial composite indexes with INCLUDE** — pattern follows `ix_gp_user_endgame_game` in the existing `__table_args__`: filtered to a subset of rows, INCLUDE-only payload columns. Same idiom.

### Integration Points
- **Phase 71 (Stats subtab UI)** consumes `OpeningInsightsResponse` directly. Schema field names are the contract — renaming after Phase 71 ships forces a frontend revision.
- **Phase 72 (Moves subtab inline bullets)** consumes the same response and bins findings by `(color, classification, entry_full_hash == current_displayed_hash)`. The `color` field on each finding (D-03) makes this binning a simple filter.
- **Phase 73/74 (stretch)** consume the same response — meta-recommendation aggregates over the four lists; bookmark badge maps `bookmark.target_hash → entry_full_hash` to a count of findings.
- **`tests/services/test_opening_insights_service.py`** is in scope for Phase 70 unit tests. Cover at minimum: classification boundaries (loss_rate / win_rate at 0.549, 0.550, 0.551, 0.599, 0.600 — verifying strict `>` and severity boundary), severity tier assignment, ranking sort order (severity desc, n_games desc), per-section caps, dedupe by resulting_hash within color, deepest-by-ply_count attribution, parent-lineage attribution fallback, unnamed-line fallback.
- **`tests/services/test_opening_insights_arrow_consistency.py`** (NEW, mirrors `test_endgame_zones_consistency.py` from Phase 63) — Python regex-parses `frontend/src/lib/arrowColor.ts` for `LIGHT_COLOR_THRESHOLD`, `DARK_COLOR_THRESHOLD` literals and asserts equality with the Python service's module-level constants. Catches future arrow-color drift.
- **`tests/repositories/test_opening_insights_repository.py`** (NEW) — integration tests for the transition-aggregation query against fixtures. At minimum: verify entry_ply boundaries (3 and 16 inclusive, 2 and 17 excluded), the LAG correctly nulls at ply=0, n_games >= 20 floor, win/loss filter conditions match user_color correctly.
- **CHANGELOG.md** under `[Unreleased]` § Changed gets one entry per D-17 noting the algorithm redesign + classifier alignment with arrow coloring.

</code_context>

<specifics>
## Specific Ideas

- **Four-section response shape**: `white_weaknesses`, `black_weaknesses`, `white_strengths`, `black_strengths`, each a `list[OpeningInsightFinding]`. Phase 71 renders four headers with white-square / black-square chess-piece visual cues per the user's intended UI.
- **Single SQL aggregation per color** in entry_ply [3, 16], `n ≥ 20`, classification at SQL HAVING level. Caps per section: 5 weaknesses + 3 strengths per color = up to 16 findings on screen.
- **`OpeningInsightFinding` field set** (combined from INSIGHT-CORE-08 + decisions above):
  ```python
  class OpeningInsightFinding(BaseModel):
      color: Literal["white", "black"]
      classification: Literal["weakness", "strength"]
      severity: Literal["minor", "major"]

      opening_name: str       # "<unnamed line>" when no openings-table match anywhere on lineage
      opening_eco: str        # "" when no openings-table match
      display_name: str       # may include "vs. " prefix when off-color attribution

      entry_fen: str          # reconstructed via python-chess SAN replay
      entry_full_hash: str    # str-form for JSON precision
      candidate_move_san: str
      resulting_full_hash: str # for Phase 72 dedupe matching

      n_games: int
      wins: int
      draws: int
      losses: int

      win_rate: float         # used as classifier for strengths
      loss_rate: float        # used as classifier for weaknesses
      score: float            # (W + D/2) / n; informative only
  ```
  The `source: Literal["top_openings", "bookmark"]` field from the prior design is **dropped** — bookmarks are no longer an algorithmic input (D-18). Phase 74's bookmark badge can be computed at the UI layer by intersecting the response with the user's bookmarks.
- **Configuration constants** (D-28) at the top of `opening_insights_service.py`:
  ```python
  MIN_ENTRY_PLY = 3
  MAX_ENTRY_PLY = 16
  MIN_GAMES_PER_CANDIDATE = 20
  LIGHT_THRESHOLD = 0.55
  DARK_THRESHOLD = 0.60
  WEAKNESS_CAP_PER_COLOR = 5
  STRENGTH_CAP_PER_COLOR = 3
  ```
- **Test boundary fixtures** mirror `arrowColor.test.ts` exactly: 55.0% → not a finding (grey/neutral); 55.1% → minor; 59.9% → minor; 60.0% → major; 65.0% → major. Both for `loss_rate` (weaknesses) and `win_rate` (strengths). Plus n=19 (excluded) / n=20 (included) for the evidence floor.

</specifics>

<deferred>
## Deferred Ideas

- **LLM narration of opening insights** — explicitly v1.13.x or v1.14 per REQUIREMENTS.md "Future Requirements". Phase 70 stays pure templated.
- **Per-bookmark-card weakness badge** — Phase 74 (stretch). Phase 70 exposes `entry_full_hash` on each finding so Phase 74 can map bookmarks → finding counts at the UI layer (no second backend call needed).
- **Aggregate / meta-recommendation finding** — Phase 73 (stretch). Operates over `OpeningInsightsResponse` as a pure post-processing step.
- **Engine-eval-based weakness detection** — out of scope for v1.13.
- **Population-relative weakness signals** — out of scope for v1.13; SEED-005 § "Why Self-Referential Is Sufficient" is the load-bearing argument.
- **Service-layer caching for heavy users** — INSIGHT-CORE-09 explicitly defers; with the new index even Hikaru-class users complete in <1 s, so this is unlikely to become urgent.
- **Per-user total-game floor** — discussed and rejected (D-20).
- **Continuous severity × frequency ranking** — discussed and rejected (D-07). The discrete two-tier ranking matches the visual idiom.
- **Recency-weighted ranking** — discussed and rejected (D-09). Recency is already a user-controllable filter.
- **MAX_ENTRY_PLY > 16** — out of scope for v1. Findings beyond ply 16 are rare for non-elite users and the search space grows linearly. Revisit if telemetry shows users with deep theory feel under-served.
- **Bookmarks as discovery input** — discussed and rejected (D-18). Bookmarks remain a UI tracking feature; they do not influence what is discovered.

</deferred>

---

*Phase: 70-backend-opening-insights-service*
*Context gathered: 2026-04-26 (revised after algorithm redesign exploration same day)*
