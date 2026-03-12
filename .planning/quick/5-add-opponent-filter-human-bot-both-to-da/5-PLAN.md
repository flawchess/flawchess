---
phase: quick-5
plan: 1
type: execute
wave: 1
depends_on: []
files_modified:
  - app/schemas/analysis.py
  - app/repositories/analysis_repository.py
  - app/services/analysis_service.py
  - frontend/src/types/api.ts
  - frontend/src/components/filters/FilterPanel.tsx
  - frontend/src/pages/Dashboard.tsx
autonomous: true
requirements: []

must_haves:
  truths:
    - "Opponent filter appears in More filters below the Rated filter, with Human / Bot / Both toggle buttons"
    - "Default state is Human — computer games are excluded unless Bot or Both is selected"
    - "Selecting Bot restricts analysis results to computer opponent games only"
    - "Selecting Both includes all games regardless of opponent type"
  artifacts:
    - path: "app/schemas/analysis.py"
      provides: "opponent_type field on AnalysisRequest"
      contains: "opponent_type"
    - path: "app/repositories/analysis_repository.py"
      provides: "DB filter on Game.is_computer_game column"
      contains: "is_computer_game"
    - path: "frontend/src/components/filters/FilterPanel.tsx"
      provides: "Opponent toggle UI in More filters below Rated"
      contains: "opponentType"
  key_links:
    - from: "frontend/src/pages/Dashboard.tsx"
      to: "POST /analysis/positions"
      via: "opponent_type field in request body"
      pattern: "filters\\.opponentType"
    - from: "app/repositories/analysis_repository.py"
      to: "games table"
      via: "Game.is_computer_game filter"
      pattern: "is_computer_game"
---

<objective>
Add an opponent type filter (Human / Bot / Both) to the More filters section of FilterPanel, positioned below the Rated filter. Default is Human (computer games excluded). Wired end-to-end through backend via `is_computer_game` on the `games` table.

Purpose: Users can isolate analysis to games against human opponents (the common case) or specifically study computer games.
Output: Opponent filter UI + backend `is_computer_game` filtering applied by default.
</objective>

<execution_context>
@/home/aimfeld/.claude/get-shit-done/workflows/execute-plan.md
@/home/aimfeld/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md

<interfaces>
<!-- Game model (app/models/game.py) -->
is_computer_game: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

<!-- AnalysisRequest (app/schemas/analysis.py) — current optional filters -->
time_control: list[Literal["bullet", "blitz", "rapid", "classical"]] | None = None
platform: list[Literal["chess.com", "lichess"]] | None = None
rated: bool | None = None
recency: Literal["week", "month", "3months", "6months", "year", "all"] | None = None
color: Literal["white", "black"] | None = None
# ADD: opponent_type: Literal["human", "bot", "both"] = "human"

<!-- _build_base_query signature (app/repositories/analysis_repository.py) — add parameter -->
def _build_base_query(select_entity, user_id, hash_column, target_hash,
                      time_control, platform, rated, recency_cutoff, color) -> Any:
    if rated is not None:
        base = base.where(Game.rated == rated)
    # ADD analogous opponent_type filter below rated:
    # if opponent_type == "human":
    #     base = base.where(Game.is_computer_game == False)
    # elif opponent_type == "bot":
    #     base = base.where(Game.is_computer_game == True)
    # (both = no filter)

<!-- FilterState (frontend/src/components/filters/FilterPanel.tsx) -->
export interface FilterState {
  matchSide: MatchSide;
  timeControls: TimeControl[] | null;
  platforms: Platform[] | null;
  rated: boolean | null;
  recency: Recency | null;
  color: Color | null;
  // ADD: opponentType: 'human' | 'bot' | 'both';
}
export const DEFAULT_FILTERS: FilterState = {
  matchSide: 'full',
  timeControls: null,
  platforms: null,
  rated: null,
  recency: null,
  color: null,
  // ADD: opponentType: 'human',
};

<!-- Dashboard.tsx request construction (handleAnalyze and handlePageChange) -->
const request = {
  target_hash: ...,
  match_side: filters.matchSide,
  time_control: filters.timeControls,
  platform: filters.platforms,
  rated: filters.rated,
  recency: filters.recency,
  color: filters.color,
  // ADD: opponent_type: filters.opponentType,
  offset: ...,
  limit: PAGE_SIZE,
};
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add opponent_type filter to backend schema and repository</name>
  <files>app/schemas/analysis.py, app/repositories/analysis_repository.py, app/services/analysis_service.py</files>
  <action>
    1. `app/schemas/analysis.py` — Add `opponent_type` field to `AnalysisRequest` after `rated`:
       ```python
       opponent_type: Literal["human", "bot", "both"] = "human"
       ```
       Import `Literal` is already present. Default `"human"` means computer games are excluded by default.

    2. `app/repositories/analysis_repository.py` — Add `opponent_type: str = "human"` parameter to `_build_base_query`, `query_all_results`, and `query_matching_games`. In `_build_base_query`, add the filter after the `rated` check:
       ```python
       if opponent_type == "human":
           base = base.where(Game.is_computer_game == False)  # noqa: E712
       elif opponent_type == "bot":
           base = base.where(Game.is_computer_game == True)   # noqa: E712
       # "both" = no filter
       ```
       Pass `opponent_type=opponent_type` from `query_all_results` and `query_matching_games` down to `_build_base_query`. Use `Game.is_computer_game` — column already exists, no migration needed.

    3. `app/services/analysis_service.py` — Pass `opponent_type=request.opponent_type` at both call sites in `analyze()`: the `query_all_results` call and the `query_matching_games` call.
  </action>
  <verify>
    <automated>cd /home/aimfeld/Projects/Python/chessalytics && uv run pytest tests/ -x -q 2>&1 | tail -20</automated>
  </verify>
  <done>All tests pass. `AnalysisRequest` accepts `opponent_type` with default `"human"`. Repository applies `Game.is_computer_game` filter for human/bot values and passes through for "both".</done>
</task>

<task type="auto">
  <name>Task 2: Add opponent filter UI to FilterPanel and wire through Dashboard</name>
  <files>frontend/src/types/api.ts, frontend/src/components/filters/FilterPanel.tsx, frontend/src/pages/Dashboard.tsx</files>
  <action>
    1. `frontend/src/types/api.ts` — Add `OpponentType` type and the field on `AnalysisRequest`:
       ```typescript
       export type OpponentType = 'human' | 'bot' | 'both';
       ```
       Add to `AnalysisRequest` interface:
       ```typescript
       opponent_type?: OpponentType;
       ```

    2. `frontend/src/components/filters/FilterPanel.tsx`:
       a. Import `OpponentType` from `@/types/api` (add to existing import line).
       b. Add `opponentType: OpponentType` to `FilterState` interface.
       c. Add `opponentType: 'human'` to `DEFAULT_FILTERS` (default excludes computer games).
       d. In the More filters collapsible `<div className="mt-2 space-y-3">`, insert the Opponent section directly after the Rated section (i.e., as the third item, below Rated, above Recency):
          ```tsx
          {/* Opponent */}
          <div>
            <p className="mb-1 text-xs text-muted-foreground">Opponent</p>
            <ToggleGroup
              type="single"
              value={filters.opponentType}
              onValueChange={(v) => {
                if (!v) return;
                update({ opponentType: v as OpponentType });
              }}
              variant="outline"
              size="sm"
            >
              <ToggleGroupItem value="human">Human</ToggleGroupItem>
              <ToggleGroupItem value="bot">Bot</ToggleGroupItem>
              <ToggleGroupItem value="both">Both</ToggleGroupItem>
            </ToggleGroup>
          </div>
          ```
          Use `ToggleGroup` (same component as Played as / Match side / Rated) rather than custom buttons — it maps cleanly to a single required selection with no null state.

    3. `frontend/src/pages/Dashboard.tsx` — In both `handleAnalyze` and `handlePageChange` request objects, add:
       ```typescript
       opponent_type: filters.opponentType,
       ```

    Also update the empty-state hint text at line ~227 to mention "opponent" filter alongside the existing filter names, or leave it as-is if the string is generic enough (use judgment).
  </action>
  <verify>
    <automated>cd /home/aimfeld/Projects/Python/chessalytics/frontend && npm run build 2>&1 | tail -20</automated>
  </verify>
  <done>Frontend builds without TypeScript errors. FilterPanel shows Opponent toggle (Human / Bot / Both) in More filters below Rated. Human is pre-selected by default. Dashboard passes opponent_type to the analysis API.</done>
</task>

</tasks>

<verification>
- `uv run pytest tests/ -x -q` passes
- `npm run build` passes with no TypeScript errors
- `uv run ruff check app/schemas/analysis.py app/repositories/analysis_repository.py app/services/analysis_service.py` passes
- Default filter state sends `opponent_type: "human"` — computer games excluded unless user selects Bot or Both
</verification>

<success_criteria>
- Opponent filter (Human / Bot / Both) appears in More filters below Rated as a single-select toggle
- Default is Human — analysis excludes computer opponent games out of the box
- Selecting Bot shows only computer opponent games
- Selecting Both includes all games
- No TypeScript errors, no Python lint errors, all tests pass
</success_criteria>

<output>
After completion, create `.planning/quick/5-add-opponent-filter-human-bot-both-to-da/5-SUMMARY.md` using the summary template.
</output>
