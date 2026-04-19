# Phase 55: Time Pressure — Performance Chart - Context

**Gathered:** 2026-04-12
**Status:** Ready for planning
**Mode:** Auto-generated (discuss skipped — specs refined in docs/endgame-analysis-v2.md section 3.2)

<domain>
## Phase Boundary

Users see a two-line comparison chart showing their score vs opponents' score across time pressure buckets at endgame entry, answering "do I crack under time pressure more than my opponents?" — tabbed by time control.

</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion
All implementation choices are at Claude's discretion — discuss phase was skipped per user request. Detailed specs are in `docs/endgame-analysis-v2.md` section 3.2. Use ROADMAP phase goal, success criteria, and codebase conventions to guide decisions.

</decisions>

<code_context>
## Existing Code Insights

Codebase context will be gathered during plan-phase research.

</code_context>

<specifics>
## Specific Ideas

Detailed formulas and layout specs are in `docs/endgame-analysis-v2.md` section 3.2:
- 10 equal-width buckets (0-10%, 10-20%, ..., 90-100%) based on time remaining % at endgame entry
- Blue "My score" line = AVG(user_score) grouped by user's time bucket
- Red "Opponent's score" line = AVG(1 - user_score) grouped by opponent's time bucket
- Tabbed by time control (bullet/blitz/rapid/classical)
- Dim points with < 10 games, hide tabs with < 10 endgame games
- Games without clock_seconds excluded

</specifics>

<deferred>
## Deferred Ideas

None — discuss phase skipped.

</deferred>
