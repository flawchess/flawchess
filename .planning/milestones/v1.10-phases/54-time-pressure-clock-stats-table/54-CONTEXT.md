# Phase 54: Time Pressure — Clock Stats Table - Context

**Gathered:** 2026-04-12
**Status:** Ready for planning
**Mode:** Auto-generated (discuss skipped — specs refined in docs/endgame-analysis-v2.md section 3.1)

<domain>
## Phase Boundary

Users see a per-time-control summary table of clock state when entering endgames, answering "how much time do I have when endgames start?" with columns for avg time remaining (% + absolute seconds), opponent avg time, clock diff, and net timeout rate.

</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion
All implementation choices are at Claude's discretion — discuss phase was skipped per user request. Detailed specs are in `docs/endgame-analysis-v2.md` section 3.1. Use ROADMAP phase goal, success criteria, and codebase conventions to guide decisions.

</decisions>

<code_context>
## Existing Code Insights

Codebase context will be gathered during plan-phase research.

</code_context>

<specifics>
## Specific Ideas

Detailed formulas and layout specs are in `docs/endgame-analysis-v2.md` section 3.1:
- User clock at endgame entry = clock_seconds at first user-ply in endgame span (even ply if white, odd if black)
- Time remaining % = (clock_seconds / time_control_seconds) * 100
- Clock difference = user_clock - opponent_clock (seconds)
- Net timeout rate = (endgame timeout wins - losses) / total endgame games * 100
- One row per time control, respects sidebar filters
- Games without clock_seconds excluded from time columns; note shows coverage %

</specifics>

<deferred>
## Deferred Ideas

None — discuss phase skipped.

</deferred>
