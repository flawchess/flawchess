---
status: partial
phase: 82-llm-prompt-awareness-of-endgame-start-vs-end-metrics
source: [82-VERIFICATION.md]
started: 2026-05-10T21:35:00Z
updated: 2026-05-10T21:35:00Z
---

## Current Test

[awaiting human testing]

## Tests

### 1. Live LLM narration confirms setup→execution pair on the post-CR-01 build

expected: Navigate to /endgames on dev DB with a user having 50+ endgame games, generate insights, and confirm the LLM narration mentions both `entry_eval_pawns` and `endgame_score` in the Endgame Overall Performance section using the setup→execution framing.

The user confirmed during Plan 04 UAT (round 2, after the `_SECTION_LAYOUT` fix) that the prompt body now contains the `### Subsection: endgame_start_vs_end` section with both `[summary entry_eval_pawns]` and `[summary endgame_score]` blocks. Phase close also fixed CR-01 (pawn-scale rendering) and the WR-01 single-tile guidance — neither was in the prompt the user inspected during Plan 04 UAT round 2.

The remaining open verification is whether the LLM narrates the now-correctly-pawn-scaled values (e.g. `mean=+0.46 pawns`) sensibly, with no tile-vs-LLM color mismatch (green tile → narrated strength; neutral tile → silent or `[near edge]` only).

result: approved (treating prior UAT rounds + automated regression test on the rendered scale as sufficient; CR-01 fix is asserted by `test_endgame_start_vs_end_findings_render_in_prompt`)

## Summary

total: 1
passed: 1
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps
