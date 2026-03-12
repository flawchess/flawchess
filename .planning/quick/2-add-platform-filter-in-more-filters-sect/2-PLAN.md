---
phase: quick-2
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
    - "Platform filter appears in More filters section, below Time control, with Chess.com and Lichess toggle buttons"
    - "Selecting one or both platforms restricts analysis results to games from those platforms"
    - "Default (no selection / all selected) returns games from all platforms"
  artifacts:
    - path: "app/schemas/analysis.py"
      provides: "platform filter field on AnalysisRequest"
      contains: "platform"
    - path: "app/repositories/analysis_repository.py"
      provides: "DB filter on Game.platform column"
      contains: "Game.platform"
    - path: "frontend/src/components/filters/FilterPanel.tsx"
      provides: "Platform multiselect UI in More filters"
      contains: "platforms"
  key_links:
    - from: "frontend/src/pages/Dashboard.tsx"
      to: "POST /analysis/positions"
      via: "platform field in request body"
      pattern: "filters\\.platforms"
    - from: "app/repositories/analysis_repository.py"
      to: "games table"
      via: "Game.platform.in_(platform)"
      pattern: "Game\\.platform"
---

<objective>
Add a platform filter (Chess.com / Lichess) to the More filters collapsible section in FilterPanel, directly below Time control. Works identically to time control — multiselect toggle buttons, null means all platforms, list means restrict to those platforms. Wired end-to-end through backend.

Purpose: Users who import from both platforms can isolate analysis to one platform.
Output: Platform filter UI + backend filtering on Game.platform column.
</objective>

<execution_context>
@/home/aimfeld/.claude/get-shit-done/workflows/execute-plan.md
@/home/aimfeld/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md

<interfaces>
<!-- FilterPanel.tsx key exports -->
export interface FilterState {
  matchSide: MatchSide;
  timeControls: TimeControl[] | null; // null = all
  rated: boolean | null;
  recency: Recency | null;
  color: Color | null;
  // ADD: platforms: Platform[] | null; // null = all
}

export const DEFAULT_FILTERS: FilterState = { ... };

<!-- api.ts existing types -->
export type Platform = 'chess.com' | 'lichess';

<!-- AnalysisRequest (Pydantic) -->
class AnalysisRequest(BaseModel):
    target_hash: int
    match_side: Literal["white", "black", "full"] = "full"
    time_control: list[Literal["bullet", "blitz", "rapid", "classical"]] | None = None
    rated: bool | None = None
    recency: Literal["week", "month", "3months", "6months", "year", "all"] | None = None
    color: Literal["white", "black"] | None = None
    # ADD: platform: list[Literal["chess.com", "lichess"]] | None = None

<!-- _build_base_query signature in analysis_repository.py -->
def _build_base_query(select_entity, user_id, hash_column, target_hash,
                      time_control, rated, recency_cutoff, color) -> Any:
    ...
    if time_control is not None:
        base = base.where(Game.time_control_bucket.in_(time_control))
    # ADD analogous platform filter:
    # if platform is not None:
    #     base = base.where(Game.platform.in_(platform))

<!-- Game model column -->
platform: Mapped[str] = mapped_column(String(20), nullable=False)  # "chess.com" | "lichess"

<!-- Dashboard.tsx request construction (both handleAnalyze and handlePageChange) -->
const request = {
  target_hash: ...,
  match_side: filters.matchSide,
  time_control: filters.timeControls,
  rated: filters.rated,
  recency: filters.recency,
  color: filters.color,
  // ADD: platform: filters.platforms,
};
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add platform filter to backend schema, repository, and service</name>
  <files>app/schemas/analysis.py, app/repositories/analysis_repository.py, app/services/analysis_service.py</files>
  <action>
    1. `app/schemas/analysis.py` — Add `platform` field to `AnalysisRequest`:
       ```python
       platform: list[Literal["chess.com", "lichess"]] | None = None
       ```
       Place it after `time_control` for logical grouping.

    2. `app/repositories/analysis_repository.py` — Add `platform` parameter to `_build_base_query`, `query_all_results`, and `query_matching_games`. In `_build_base_query` add filter analogous to the existing `time_control` filter:
       ```python
       if platform is not None:
           base = base.where(Game.platform.in_(platform))
       ```
       Pass `platform=platform` from both `query_all_results` and `query_matching_games` to `_build_base_query`.

    3. `app/services/analysis_service.py` — Pass `platform=request.platform` when calling `query_all_results` and `query_matching_games` (both call sites in `analyze()`).

    No migration needed — `Game.platform` column already exists.
  </action>
  <verify>
    <automated>cd /home/aimfeld/Projects/Python/chessalytics && uv run pytest tests/ -x -q 2>&1 | tail -20</automated>
  </verify>
  <done>All existing tests pass; `AnalysisRequest` accepts `platform` field; repository applies `Game.platform.in_()` filter when platform list is provided.</done>
</task>

<task type="auto">
  <name>Task 2: Add platform filter UI to FilterPanel and wire through Dashboard</name>
  <files>frontend/src/types/api.ts, frontend/src/components/filters/FilterPanel.tsx, frontend/src/pages/Dashboard.tsx</files>
  <action>
    1. `frontend/src/types/api.ts` — Add `platform` field to `AnalysisRequest`:
       ```typescript
       platform?: Platform[] | null;
       ```

    2. `frontend/src/components/filters/FilterPanel.tsx`:
       a. Add `platforms: Platform[] | null` to `FilterState` interface (null = all).
       b. Add `platforms: null` to `DEFAULT_FILTERS`.
       c. Import `Platform` type from `@/types/api` (already exported there).
       d. Add constants mirroring the time control pattern:
          ```typescript
          const PLATFORMS: Platform[] = ['chess.com', 'lichess'];
          const PLATFORM_LABELS: Record<Platform, string> = {
            'chess.com': 'Chess.com',
            lichess: 'Lichess',
          };
          ```
       e. Add `togglePlatform` and `isPlatformActive` helpers, identical in logic to `toggleTimeControl` / `isTimeControlActive` but for platforms.
       f. In the More filters collapsible `<div className="mt-2 space-y-3">`, add the platform section directly after the Time control section (before Rated):
          ```tsx
          {/* Platform */}
          <div>
            <p className="mb-1 text-xs text-muted-foreground">Platform</p>
            <div className="flex flex-wrap gap-1">
              {PLATFORMS.map((p) => (
                <button
                  key={p}
                  onClick={() => togglePlatform(p)}
                  className={cn(
                    'rounded border px-2 py-0.5 text-xs transition-colors',
                    isPlatformActive(p)
                      ? 'border-primary bg-primary text-primary-foreground'
                      : 'border-border bg-transparent text-muted-foreground hover:border-foreground hover:text-foreground',
                  )}
                >
                  {PLATFORM_LABELS[p]}
                </button>
              ))}
            </div>
          </div>
          ```

    3. `frontend/src/pages/Dashboard.tsx` — In both `handleAnalyze` and `handlePageChange` request objects, add:
       ```typescript
       platform: filters.platforms,
       ```

    The `togglePlatform` logic: when toggling off the last platform, keep it selected (prevent empty list) — same behavior as time control. When all platforms are selected, store null (no filter). When subset selected, store the subset array.
  </action>
  <verify>
    <automated>cd /home/aimfeld/Projects/Python/chessalytics/frontend && npm run build 2>&1 | tail -20</automated>
  </verify>
  <done>Frontend builds without TypeScript errors. FilterPanel shows Platform toggle buttons (Chess.com, Lichess) in More filters below Time control. Dashboard passes platform filter to analysis API.</done>
</task>

</tasks>

<verification>
- `uv run pytest tests/ -x -q` passes
- `npm run build` passes with no TypeScript errors
- `uv run ruff check app/schemas/analysis.py app/repositories/analysis_repository.py app/services/analysis_service.py` passes
</verification>

<success_criteria>
- Platform filter (Chess.com / Lichess) appears in More filters, below Time control, using the same toggle-button multiselect style
- Selecting only "Chess.com" restricts analysis results to chess.com games
- Selecting only "Lichess" restricts to lichess games
- Default state (null) includes both platforms
- No TypeScript errors, no Python lint errors, all tests pass
</success_criteria>

<output>
After completion, create `.planning/quick/2-add-platform-filter-in-more-filters-sect/2-SUMMARY.md` using the summary template.
</output>
