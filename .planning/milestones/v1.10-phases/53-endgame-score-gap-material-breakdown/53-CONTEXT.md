# Phase 53: Endgame Score Gap & Material Breakdown - Context

**Gathered:** 2026-04-12
**Status:** Ready for planning
**Mode:** Auto-generated (discuss skipped — specs refined in docs/endgame-analysis-v2.md sections 1-2)

<domain>
## Phase Boundary

Users see an endgame score difference metric (endgame score minus non-endgame score) and a material-stratified WDL table showing performance when ahead, equal, or behind at endgame entry — directly answering "how much worse do I score in endgames?" and "does my material situation at entry predict my result?"

</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion
All implementation choices are at Claude's discretion — discuss phase was skipped per user request. Detailed specs are in `docs/endgame-analysis-v2.md` sections 1-2. Use ROADMAP phase goal, success criteria, and codebase conventions to guide decisions.

</decisions>

<code_context>
## Existing Code Insights

Codebase context will be gathered during plan-phase research.

</code_context>

<specifics>
## Specific Ideas

Detailed formulas and layout specs are in `docs/endgame-analysis-v2.md`:
- Section 1: Endgame Score Difference — Score = (Win% + Draw%/2) / 100, difference = endgame score - non-endgame score, green/red color coding
- Section 2: Material-Stratified WDL Table — 3 material buckets (Ahead >=+100cp, Equal, Behind <=-100cp), verdict calibrated against user's overall score

</specifics>

<deferred>
## Deferred Ideas

None — discuss phase skipped.

</deferred>
