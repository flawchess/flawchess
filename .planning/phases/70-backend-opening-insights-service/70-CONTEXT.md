# Phase 70: Backend opening insights service - Context

**Gathered:** 2026-04-26
**Status:** Ready for planning
**Requirements:** INSIGHT-CORE-01, INSIGHT-CORE-02, INSIGHT-CORE-03, INSIGHT-CORE-04, INSIGHT-CORE-05, INSIGHT-CORE-06, INSIGHT-CORE-07, INSIGHT-CORE-08, INSIGHT-CORE-09

<domain>
## Phase Boundary

Backend-only. Build a user-scoped `opening_insights_service` (and the supporting Pydantic schemas + thin router) that produces a structured 4-section response of ranked, deduplicated `OpeningInsightFinding` payloads under the user's active filter set. No LLM, no precompute, no benchmark-DB consumption. Reuses the existing `query_top_openings_sql_wdl` (PRE-01 fix landed), `query_next_moves` aggregation, `apply_game_filters` shared filter implementation, and the `game_positions` Zobrist-hash schema. No new schema or migration. Phase 71 (Stats subtab UI), 72 (Moves subtab inline bullets), 73 (meta-recommendation, stretch), 74 (bookmark badge, stretch) build on top.

Two REQUIREMENTS.md amendments emerged from this discussion (apply at Phase 70 commit time, see "REQUIREMENTS amendments" decisions D-15 and D-16):
1. INSIGHT-CORE-02 scan input changes from "top-10 most-played per color" to "top-20 most-played per color".
2. INSIGHT-CORE-05 classifier switches from `score = (W + D/2) / n` to `win_rate = W / n` for strengths (and the boundary tightens from `≥ 0.55 / ≥ 0.60` to strict `> 0.55`) so the classification matches `frontend/src/lib/arrowColor.ts` exactly.

</domain>

<decisions>
## Implementation Decisions

### Response Structure (reframes INSIGHT-CORE-02 / INSIGHT-CORE-07)

- **D-01:** Response is structured by color × class into FOUR named lists, not one flat findings array:
  ```python
  class OpeningInsightsResponse(BaseModel):
      white_weaknesses: list[OpeningInsightFinding]
      black_weaknesses: list[OpeningInsightFinding]
      white_strengths:  list[OpeningInsightFinding]
      black_strengths:  list[OpeningInsightFinding]
  ```
  Phase 71 renders four labeled sections ("⬜ White Opening Weaknesses", "⬛ Black Opening Weaknesses", "⬜ White Opening Strengths", "⬛ Black Opening Strengths"). The endpoint always returns all four lists; empty sections are valid empty-state and surface a per-section "no findings cleared the threshold" message in Phase 71.
- **D-02:** Caps from INSIGHT-CORE-07 are applied **per section**, not globally: top-5 weaknesses + top-3 strengths per color. So the visible ceiling on screen is `5 + 5 + 3 + 3 = 16` findings. Configurable per-section.
- **D-03:** Each `OpeningInsightFinding` carries an explicit `color: Literal["white", "black"]` field so the same payload is reusable in Phase 72's Moves-tab inline bullets without binning by section.

### Classification & Severity (reinterprets INSIGHT-CORE-05 to align with `arrowColor.ts`)

- **D-04:** Classification uses **`win_rate = W / n`** (not `score = (W + D/2) / n`) and **`loss_rate = L / n`** with a strict `>` boundary at 0.55:
  - `weakness` if `loss_rate > 0.55`
  - `strength` if `win_rate > 0.55`
  - Otherwise neutral, dropped.
  This matches `frontend/src/lib/arrowColor.ts:39-61` exactly: `winPct > 55 → light/dark green`; `lossPct > 55 → light/dark red`. A position that's grey on the board never surfaces as a finding; a position rendered light/dark green or red on the board is a candidate.
- **D-05:** Severity tier maps 1:1 onto the arrow's two color shades:
  - `severity = "major"` if the qualifying rate is `≥ 0.60` (dark green / dark red on the board)
  - `severity = "minor"` if the qualifying rate is in `(0.55, 0.60)` (light green / light red on the board)
  - Schema: `classification: Literal["weakness", "strength"]` + `severity: Literal["minor", "major"]` (two separate fields, both on every finding).
- **D-06:** `score = (W + D/2) / n` is still computed and exposed in the payload (per INSIGHT-CORE-08) for downstream display use — but it is NOT the classifier. `win_rate`, `loss_rate`, and `score` all appear on the finding alongside `wins, draws, losses, n_games`.

### Ranking & Cap Application (resolves INSIGHT-CORE-07 "formula resolved in Phase 70")

- **D-07:** Within each of the four sections, sort by **`(severity desc, n_games desc)`** — all `major` findings appear before any `minor`, and within a tier larger `n_games` wins. No continuous severity × frequency score; severity stays a discrete two-level tag.
- **D-08:** Caps applied AFTER the sort: take the first 5 (weaknesses) or 3 (strengths) per color section. With caps of 5/3, you'll mostly see majors first; minors only fill the remainder when there aren't enough majors. Post-cap, surface order is deterministic.
- **D-09:** No built-in recency weighting in the ranking formula. The user's active recency filter (`recency` parameter) already lets them restrict the window if they want recent-only findings. One mechanism, not two.

### Filter Contract & Endpoint (resolves INSIGHT-CORE-01 filter compatibility)

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
  (Final type-tightening on `recency` is a planner concern — match `app/services/stats_service.recency_cutoff` accepted values.)
- **D-11:** The v1.11 `FilterContext` in `app/schemas/insights.py` is **not** reused. It's locked by the v1.11 endgame LLM prompt contract and uses `rated_only: bool` (2-state) where openings need 3-state `rated: bool | None`. Decoupling avoids cross-feature breakage when one filter shape evolves.
- **D-12:** The `color` filter is **orthogonal to the section structure**: the endpoint returns all four sections regardless of `color=white/black/all`. Phase 71 may optionally collapse off-color sections in the UI when `color != "all"`, but the backend contract is invariant. INSIGHT-CORE-01 ("equivalent filters → equivalent rankings") is satisfied because the other six filters DO reshape findings.
- **D-13:** Route placement: **`POST /api/insights/openings`**. Symmetric with `POST /api/insights/endgame` (v1.11). The router lives in `app/routers/insights.py` (extend the existing file, don't fork). POST + JSON body avoids URL-length issues if `time_control[]` / `platform[]` filter lists grow, and matches the JSON-body convention of the rest of `/openings/*` POST endpoints (`next-moves`, `positions`, `time-series`).
- **D-14:** The endpoint MUST NOT inherit the v1.11 `_validate_full_history_filters` gate from `app/routers/insights.py:39-72`. That gate is endgame-LLM-specific (the LLM system prompt frames things as "your full history"). For openings, every filter must reshape findings per INSIGHT-CORE-01 — gating non-default filters would be wrong.

### REQUIREMENTS.md Amendments (apply at Phase 70 commit time)

- **D-15:** **INSIGHT-CORE-02 scan input changes from top-10 to top-20 per color.** REQUIREMENTS.md and `.planning/milestones/v1.13-ROADMAP.md` Phase 70 success-criterion 2 currently say "top-10 most-played openings per color"; this discussion locks **top-20**. The existing `query_top_openings_sql_wdl(limit=...)` already accepts the limit — call with `limit=20`. Performance: 20 entries × ~5 candidate moves each × 2 colors = ~40 sequential `query_next_moves` calls per request. Same SQL-side aggregation, comfortably under the on-the-fly latency budget for typical users (INSIGHT-CORE-09).
- **D-16:** **INSIGHT-CORE-05 classifier switches from `score ≥ 0.60` to `win_rate > 0.55` (with severity tier at 0.60).** See D-04 / D-05. The amended REQUIREMENTS-CORE-05 wording becomes: "Classify as **weakness** if `loss_rate > 0.55`; **strength** if `win_rate > 0.55`. Within each class, severity is `major` if the qualifying rate is `≥ 0.60`, else `minor`. Drop neutral findings."
- **D-17:** Apply both amendments by editing `.planning/REQUIREMENTS.md` (top of file) AND `.planning/milestones/v1.13-ROADMAP.md` Phase 70 success-criteria block in the same commit that lands the implementation, with a one-line note in `CHANGELOG.md` under `[Unreleased]` § Changed describing the threshold shift to "match the board arrow coloring exactly". Don't ship the implementation without the matching REQUIREMENTS edit — they're load-bearing on each other for Phase 71's empty-state copy.

### Bookmarks Scope & Floors

- **D-18:** Bookmarks are scoped to a section by **strict color match**: `bookmark.color == "white"` → white sections only; `bookmark.color == "black"` → black sections only; `bookmark.color IS NULL` bookmarks are **excluded** from the scan entirely. The user's existing `match_side` field on bookmarks is irrelevant for Phase 70 — only `color` drives section assignment.
- **D-19:** Bookmarks **bypass the 50-game entry-position floor** (INSIGHT-CORE-02 `min-games-per-entry`). User explicitly opted in by bookmarking; the per-candidate `n ≥ 10` floor (INSIGHT-CORE-04) still applies and naturally suppresses thin bookmarks (a 30-game bookmark with 5 candidate moves of ~6 each produces zero findings).
- **D-20:** No per-user total-game floor. With four always-present sections, "mostly empty" is normal for new users; Phase 71's empty-state copy ("no findings cleared the threshold — try lowering filters or import more games") handles the message uniformly. One fewer config knob.

### Dedupe & Attribution (resolves INSIGHT-CORE-06)

- **D-21:** Dedupe on `resulting_position_hash` (the Zobrist hash of the position AFTER the candidate move) is **scoped within a single color section**, not cross-color. Same hash appearing in both white and black sections is preserved as two distinct findings — they describe genuinely different repertoire issues even if a transposition makes the positions identical.
- **D-22:** Attribution lookup: for each surviving finding, query `openings` table rows where `full_hash == resulting_position_hash`; pick the row with `MAX(ply_count)` — deepest opening = most specific name. The finding's `opening_name`, `opening_eco`, `display_name` come from that row. Implementation: one batched `SELECT ... WHERE full_hash IN (...)` covering all surviving findings (~16 max after caps), one extra round trip per request.
- **D-23:** Fallback when no `openings` row matches the resulting hash → attribute to the **entry's** opening (parent). For bookmarks where the entry itself has no `openings` match, use `bookmark.label` as `opening_name` and leave `opening_eco = ""` (empty-string convention, consistent with `OpeningWDL.full_hash` empty-string handling in `app/schemas/stats.py`).
- **D-24:** Cross-entry dedupe within a section: if two different entries lead to the same resulting hash (e.g., Sicilian Najdorf and Sicilian generic both have the user playing into the same Nxd4 resulting position), keep ONE finding — the one whose **entry** has the higher `ply_count` (deeper/more-specific entry wins). Rare in practice but the rule is locked.
- **D-25:** Deep-link target = entry FEN + candidate-move SAN (NOT the resulting FEN). User lands at the position where they made the choice, with the candidate move highlighted on the board. Payload field: `deep_link_target: { entry_fen: str, candidate_move_san: str }` (or just `entry_fen` + reuse the existing `candidate_move_san` field — planner picks the cleanest shape).

### Schema & Service Layout (Claude's Discretion)

- **D-26:** New file `app/schemas/opening_insights.py` for `OpeningInsightsRequest`, `OpeningInsightFinding`, `OpeningInsightsResponse`. Do NOT extend `app/schemas/insights.py` (endgame-LLM-coupled, locked by the v1.11 prompt contract).
- **D-27:** New file `app/services/opening_insights_service.py` for the compute pipeline. Single public entry point `compute_insights(session, user_id, request) -> OpeningInsightsResponse`.
- **D-28:** Configuration constants (50-game entry floor, n≥10 candidate floor, 0.55/0.60 thresholds, severity boundary 0.60, top-5/top-3 caps) live as module-level constants at the top of `opening_insights_service.py`. Pattern follows `arrowColor.ts` (`MIN_GAMES_FOR_COLOR`, `LIGHT_COLOR_THRESHOLD`, `DARK_COLOR_THRESHOLD`) — no env vars, no DB-stored settings, no separate registry module like `endgame_zones.py`. Tunable via PR; if Phase 71 / 72 telemetry shows a need for per-user knobs, revisit then.
- **D-29:** No service-layer caching in Phase 70 (INSIGHT-CORE-09). Add only if heavy users (10k+ games) breach the latency budget after Phase 71 is in production.

### Claude's Discretion

- Implementation file layout details: file paths above are recommendations; planner finalizes.
- Exact Pydantic field types and `Literal` enumerations: planner picks tightest types matching existing `app/services/stats_service.py` and `app/repositories/openings_repository.py` signatures.
- The 4-section response can equivalently be modeled as a flat `findings: list[OpeningInsightFinding]` with frontend binning by `(color, classification)`. The 4-named-lists shape is preferred for explicitness, but if planner argues the flat shape simplifies the executor's task and Phase 71 doesn't suffer, that's acceptable. (Implementation must still satisfy D-02's per-section caps either way.)
- Empty-color-filter behavior: D-12 says ignore `color` filter for section structure. If during planning it becomes obvious that the frontend benefits from the backend honoring `color` (e.g., to skip computing the unused color and save ~50% latency), we can revisit — but the response shape stays four-keyed.
- Whether the `openings`-table attribution lookup is a single batched `IN (...)` query vs joined into the main aggregation. Either is fine.
- Error handling: standard Sentry capture pattern per CLAUDE.md (no variable-in-message errors). Empty findings under all filters is NOT an error — return empty sections. The endpoint should not 4xx for "no findings".

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase Source Documents
- `.planning/seeds/SEED-005-opening-weakness-insights.md` — full architecture rationale, why self-referential is sufficient, prior-work list, phase decomposition, open questions resolved during this discussion. Read end-to-end. The "Why Self-Referential Is Sufficient", "Prior Work (Do Not Re-Derive)", and "Open Questions" sections are load-bearing.
- `.planning/REQUIREMENTS.md` §INSIGHT-CORE-01..INSIGHT-CORE-09 — locked requirements for this phase. **Note: D-15 / D-16 / D-17 amend INSIGHT-CORE-02 and INSIGHT-CORE-05 — apply edits at Phase 70 commit time.**
- `.planning/milestones/v1.13-ROADMAP.md` Phase 70 — success criteria. Note success-criterion 2 (top-10) and success-criterion 4 (ranking formula resolved here) need amendment per D-15.
- `.planning/PROJECT.md` §"v1.13 Opening Insights" — milestone scope, target features.

### Existing Backend (read-only inputs / reuse points)
- `app/repositories/stats_repository.py::query_top_openings_sql_wdl` (line 209) — top-N most-played openings per color with SQL-side WDL aggregation. PRE-01 fix has landed. Phase 70 calls this twice (white, black) with `limit=20`.
- `app/repositories/openings_repository.py::query_next_moves` (line 359) — per-position aggregation with `(move_san, result_hash, game_count, wins, draws, losses)` per candidate move. The structurally-correct query for INSIGHT-CORE-04. NEVER bypass — no need to reimplement WDL aggregation.
- `app/repositories/openings_repository.py::query_transposition_counts` (line 437) — irrelevant for Phase 70 (used by Move Explorer for "games reaching this resulting position via any move order"; insights only need the direct-from-entry count which `query_next_moves` already returns).
- `app/repositories/query_utils.py::apply_game_filters` — the single shared filter implementation (CLAUDE.md "Shared Query Filters"). Inherited transitively via `query_top_openings_sql_wdl` and `query_next_moves`. Insights service does not call it directly.
- `app/repositories/position_bookmark_repository.py::get_bookmarks` (line 21) — list bookmarks for a user. Phase 70 reads `(target_hash, fen, color, label)` per bookmark and applies D-18's strict color match.
- `app/services/stats_service.py::get_most_played_openings` (line 231) — reference implementation of the top-10 (now top-20) flow. Phase 70's compute pipeline mirrors the early steps (recency_cutoff → query_top_openings_sql_wdl per color) before diverging into the per-entry next-moves scan.
- `app/services/openings_service.py::get_next_moves` (line 354) — reference implementation of the next-moves orchestration (recency_cutoff → wdl_counts → next_moves → transposition_counts → result_fen replay → response). Phase 70 reuses the per-entry next-moves call but skips wdl_counts and transposition_counts (not needed) and skips result_fen replay (insights doesn't need to display the resulting position; only the entry FEN + candidate SAN).
- `app/models/opening.py::Opening` — `Opening` table schema (eco, name, ply_count, fen, full_hash, pgn). `ply_count` is the deepest-attribution disambiguator for D-22.
- `app/models/position_bookmark.py::PositionBookmark` (line 1) — bookmark schema (target_hash, fen, color, label, match_side). `color` field drives D-18's strict match.

### Existing Frontend (alignment source — backend MUST match exactly)
- `frontend/src/lib/arrowColor.ts` lines 15-29 — `MIN_GAMES_FOR_COLOR = 10`, `LIGHT_COLOR_THRESHOLD = 55`, `DARK_COLOR_THRESHOLD = 60`. **The thresholds in `app/services/opening_insights_service.py` MUST match these literal values.** Phase 70 should add a CI test (Python regex-parse `arrowColor.ts` and assert equality, similar to `tests/services/test_endgame_zones_consistency.py` from Phase 63) so a future arrow-color tweak doesn't silently de-sync the insights classifier.
- `frontend/src/lib/arrowColor.ts::getArrowColor` lines 39-61 — the strict `> 55` boundary semantics. D-04 ("strict >") references this exact behavior.
- `frontend/src/lib/arrowColor.test.ts` — boundary fixtures (e.g., `getArrowColor(55, 20, 20, false) === GREY`). Reference for Phase 70's classifier unit tests.

### v1.11 Insights Reference Patterns (informative, NOT reused)
- `app/services/insights_service.py` — reference for "service that orchestrates per-window compute". Phase 70 follows the same single-public-entry-point pattern but does NOT import or extend.
- `app/schemas/insights.py::FilterContext` (line 109) — the v1.11 filter shape. Phase 70 deliberately decouples (D-11) — referenced here as a "do not reuse" anchor.
- `app/routers/insights.py` (whole file) — reference for the router/service split idiom. Phase 70 extends this file with the `POST /insights/openings` route (D-13). The `_validate_full_history_filters` gate (lines 39-72) is **not** applied to the new route (D-14).

### Project Conventions
- `CLAUDE.md` §"Coding Guidelines" — type safety, ty compliance, no magic numbers, `Literal[...]` for enums.
- `CLAUDE.md` §"Critical Constraints" — `AsyncSession` not safe for `asyncio.gather`. Phase 70's per-entry scan is sequential by construction (~40 awaits on the same session).
- `CLAUDE.md` §"Backend Layout" — `routers/` HTTP only, `services/` business logic, `repositories/` DB access. Phase 70 adds files in all three layers (one router edit, one new service, zero new repo files — repo layer is fully reused).
- `CLAUDE.md` §"Router Convention" — `APIRouter(prefix="/insights", tags=["insights"])` already exists; new route uses relative path `/openings` (NOT `/insights/openings`).
- `CLAUDE.md` §"Error Handling & Sentry" — `sentry_sdk.capture_exception` in non-trivial except blocks; `set_context` for variable data; never embed variables in error messages.
- `CLAUDE.md` §"Communication Style" — em-dash sparingly in user-facing text. (Relevant for the `OpeningInsightFinding` template strings in Phase 71, not Phase 70 itself.)

### Related Quick Tasks
- `.planning/quick/260426-*-top10-openings-parity-bug` (or equivalent path) — PRE-01 landed, fixing `query_top_openings_sql_wdl` to drop the parity filter. Without this fix, ~48% of named ECO openings (white-defined) would be invisible in the black scan, breaking Phase 70's input.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`query_top_openings_sql_wdl`** (`app/repositories/stats_repository.py:209`) — call twice (color="white" limit=20, color="black" limit=20) with the user's filter set. Returns `(eco, name, display_name, pgn, fen, full_hash, total, wins, draws, losses)` rows. Phase 70 only needs `(full_hash, fen, name, eco, ply_count[via openings], total)` — the WDL columns are for the entry's overall stats, not the per-candidate scan.
- **`query_next_moves`** (`app/repositories/openings_repository.py:359`) — the structurally-correct query for the per-entry candidate-move WDL aggregation. Returns `(move_san, result_hash, game_count, wins, draws, losses)`. Phase 70 calls this once per entry hash (~40 calls per request).
- **`apply_game_filters`** — inherited transitively via the two repository calls above. No direct call from `opening_insights_service.py`.
- **`get_bookmarks`** (`app/repositories/position_bookmark_repository.py:21`) — single call to fetch user's bookmarks; Phase 70 filters in Python by `bookmark.color in ("white", "black")` per D-18.
- **`recency_cutoff`** helper (`app/services/stats_service.py`) — converts the `recency` string filter to a `datetime` cutoff. Phase 70 reuses identically.
- **`Opening` SQLAlchemy model** (`app/models/opening.py:7`) — `(eco, name, ply_count, fen, pgn, full_hash)`. The single-query batched lookup for D-22's deepest-opening attribution.

### Established Patterns
- **Service-layer composition over repositories** — `app/services/openings_service.py::get_next_moves` orchestrates 4 repository calls then post-processes in Python. Phase 70 follows the same shape.
- **Sequential awaits on a single `AsyncSession`** — CLAUDE.md mandates this; SQLAlchemy AsyncSession is not safe for concurrent gather. Phase 70's ~40 per-entry next-moves calls are sequential by construction.
- **Pydantic v2 with `Literal[...]` for enums** — every state field on `OpeningInsightFinding` (`color`, `classification`, `severity`) is a `Literal`. ty compliance follows.
- **No magic numbers, named module-level constants** — D-28's `LIGHT_THRESHOLD = 0.55` / `DARK_THRESHOLD = 0.60` / `MIN_GAMES_PER_CANDIDATE = 10` / `MIN_GAMES_PER_ENTRY = 50` / `WEAKNESS_CAP_PER_COLOR = 5` / `STRENGTH_CAP_PER_COLOR = 3` / `TOP_OPENINGS_LIMIT = 20`.
- **String-form full_hash in API responses** (`app/schemas/stats.py::OpeningWDL.full_hash: str`) — 64-bit ints are stringified at the API boundary because JSON's number type loses precision. Phase 70's `OpeningInsightFinding.entry_full_hash` (if exposed) follows the same convention.
- **Display-name "vs. " prefix for off-color rows** (`query_top_openings_sql_wdl` lines 250-260, PRE-01 result) — already handled at the repository layer; Phase 70 just propagates `display_name` into findings.

### Integration Points
- **Phase 71 (Stats subtab UI)** consumes `OpeningInsightsResponse` directly. Schema field names are the contract — renaming after Phase 71 ships forces a frontend revision.
- **Phase 72 (Moves subtab inline bullets)** consumes the same response and bins findings by `(color, classification, entry_full_hash == current_displayed_hash)`. The `color` field on each finding (D-03) makes this binning a simple filter.
- **Phase 73/74 (stretch)** consume the same response — meta-recommendation aggregates over the four lists; bookmark badge maps `bookmark.target_hash` to the count of findings whose entry matches.
- **`tests/services/test_opening_insights_service.py`** is in scope for Phase 70 unit tests. Cover at minimum: classification boundaries (loss_rate / win_rate at 0.549, 0.550, 0.551, 0.599, 0.600 — verifying strict `>` and severity boundary), severity tier assignment, ranking sort order (severity desc, n_games desc), per-section caps, dedupe by resulting_hash within color, deepest-by-ply_count attribution, fallback to entry opening, fallback to bookmark.label, bookmark color strict match, bookmark entry-floor bypass.
- **`tests/services/test_opening_insights_arrow_consistency.py`** (NEW, mirrors `test_endgame_zones_consistency.py` from Phase 63) — Python regex-parses `frontend/src/lib/arrowColor.ts` for `LIGHT_COLOR_THRESHOLD`, `DARK_COLOR_THRESHOLD`, `MIN_GAMES_FOR_COLOR` literals and asserts equality with the Python service's module-level constants. Catches future arrow-color drift.
- **CHANGELOG.md** under `[Unreleased]` § Changed gets a one-line entry per D-17 noting the classifier alignment with arrow coloring.

</code_context>

<specifics>
## Specific Ideas

- **Four-section response shape** locked by user: `white_weaknesses`, `black_weaknesses`, `white_strengths`, `black_strengths`, each a `list[OpeningInsightFinding]`. Phase 71 renders four headers with white-square / black-square chess-piece visual cues per the user's intended UI ("⬜ White Opening Weaknesses", etc.).
- **Top-20 most-played openings per color** (not top-10). Apply caps per section: 5 weaknesses + 3 strengths per color = up to 16 findings on screen.
- **Strict color match for bookmarks** (D-18): `bookmark.color == "white"` → white sections only; `"black"` → black only; `NULL` → excluded.
- **`OpeningInsightFinding` field set** (combined from INSIGHT-CORE-08 + decisions above):
  ```python
  class OpeningInsightFinding(BaseModel):
      color: Literal["white", "black"]
      classification: Literal["weakness", "strength"]
      severity: Literal["minor", "major"]

      opening_name: str
      opening_eco: str       # "" when no openings-table match
      display_name: str      # may include "vs. " prefix from PRE-01

      entry_fen: str
      entry_full_hash: str   # str-form for JSON precision (matches OpeningWDL convention)
      candidate_move_san: str
      resulting_full_hash: str  # for Phase 72 dedupe matching

      n_games: int
      wins: int
      draws: int
      losses: int

      win_rate: float        # used as classifier for strengths
      loss_rate: float       # used as classifier for weaknesses
      score: float           # (W + D/2) / n; informative only

      source: Literal["top_openings", "bookmark"]  # for telemetry / Phase 74 badge mapping
  ```
  Planner finalizes — this is the recommended set. The `deep_link_target` field in INSIGHT-CORE-08 is satisfied by `entry_fen + candidate_move_san` directly (no nested object needed).
- **Configuration constants** (D-28) at the top of `opening_insights_service.py`:
  ```python
  TOP_OPENINGS_LIMIT = 20
  MIN_GAMES_PER_ENTRY = 50          # bypassed for bookmarks (D-19)
  MIN_GAMES_PER_CANDIDATE = 10      # always applied
  LIGHT_THRESHOLD = 0.55            # mirrors arrowColor.ts LIGHT_COLOR_THRESHOLD/100
  DARK_THRESHOLD = 0.60             # mirrors arrowColor.ts DARK_COLOR_THRESHOLD/100
  WEAKNESS_CAP_PER_COLOR = 5
  STRENGTH_CAP_PER_COLOR = 3
  ```
- **Test boundary fixtures** mirror `arrowColor.test.ts` exactly: 55.0% → not a finding (grey/neutral); 55.1% → minor; 59.9% → minor; 60.0% → major; 65.0% → major. Both for `loss_rate` (weaknesses) and `win_rate` (strengths).

</specifics>

<deferred>
## Deferred Ideas

- **LLM narration of opening insights** — explicitly v1.13.x or v1.14 per REQUIREMENTS.md "Future Requirements". Phase 70 stays pure templated.
- **Per-bookmark-card weakness badge** — Phase 74 (stretch). Phase 70 exposes `entry_full_hash` and `source: Literal["top_openings", "bookmark"]` on each finding so Phase 74 can map bookmarks → finding counts without a second backend call.
- **Aggregate / meta-recommendation finding** — Phase 73 (stretch). Operates over `OpeningInsightsResponse` as a pure post-processing step.
- **Engine-eval-based weakness detection** — out of scope for v1.13 (REQUIREMENTS.md). Different milestone if it lands at all.
- **Population-relative weakness signals** — out of scope for v1.13; SEED-005 § "Why Self-Referential Is Sufficient" is the load-bearing argument. Re-revisit only if a future user-research finding contradicts it.
- **Service-layer caching for heavy users (10k+ games)** — INSIGHT-CORE-09 explicitly defers; Phase 70 does NOT add it. Telemetry from Phase 71 production rollout drives the decision.
- **Per-user total-game floor** — discussed and rejected (D-20). If new-user UX feedback after Phase 71 ships shows the empty-section state is confusing, revisit.
- **Continuous severity × frequency ranking** — discussed and rejected (D-07). The discrete two-tier ranking matches the visual idiom; revisit only if real-world data shows top-3/top-5 ordering produces obviously bad surfacings.
- **Recency-weighted ranking** — discussed and rejected (D-09). Recency is already a user-controllable filter.
- **Switching frontend gauge components / EndgameInsightsBlock to share `OpeningInsightsBlock` patterns** — that's a Phase 71 UI concern, not Phase 70.

</deferred>

---

*Phase: 70-backend-opening-insights-service*
*Context gathered: 2026-04-26*
