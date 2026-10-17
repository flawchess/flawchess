---
phase: 241-codebase-cleanup
plan: 01
subsystem: planning-docs
tags: [glossary, style-guide, terminology, hygiene]
requires: []
provides:
  - "241-STYLE-GUIDE.md §3.3: 79-row glossary binding prose vocabulary for the phase"
affects: [241-05..241-51 comment wave, 241-59, 241-69]
tech-stack:
  added: []
  patterns: []
key-files:
  created: []
  modified:
    - .planning/phases/241-codebase-cleanup/241-STYLE-GUIDE.md
key-decisions:
  - "D-01: canonical terms bind prose and new code only; existing identifiers change via INVENTORY §3/§5, D-05, D-16"
  - "D-03 overrides: row 2 canonical player/opp, row 16 puzzle in prose"
  - "D-04 seed-candidate annotations on rows 43, 59, 60, 79"
  - "D-05: walkthrough -> tour recorded on row 21 with kept contracts"
status: complete
duration: ~10min
completed: 2026-10-16
actuals:
  tokens: 14000
  tasks: 1
  commits: 1
plan_head_before: 3bce9acb621d80e08d0ae296e01efcea0a351049
plan_head_after: 88b3e1d36febef8d758f034daa5df2395dce68b2
---

# Phase 241 Plan 01: Style guide glossary Summary

STYLE-GUIDE §3.3 now holds all 79 INVENTORY §2 glossary rows with the canonical choice as printed, plus the D-01 binding note and the D-03/D-04/D-05 overrides and annotations.

## Tasks

| Task | Name | Commit |
|------|------|--------|
| 1 | Write the 79-row glossary into STYLE-GUIDE §3.3 | 88b3e1d36 |

## What changed

- Replaced the §3.3 placeholder row with a `| # | Concept | Canonical | Also seen (to retire) | Decided |` table, rows 1-79 in INVENTORY order.
- Replaced the intro's last sentence with the D-01 binding rule and added the sentence that glossary terms do not spawn renames. Added one sentence on contracts staying whatever a row says.
- Row 2 and row 16 carry `D-03`; row 21 carries the full `D-05` note with kept contracts (`review_walkthrough`, `train-bot-walkthrough` / `btn-train-bot-walkthrough-next` testids, `trainTelemetry.ts` persisted/wire keys); rows 43, 59, 60, 79 carry `D-04: seed candidate, no merge in this phase`; row 59 also records that the `formatScore` to `formatEval` rename in `EngineLines.tsx` still ships (plan 241-59). All other rows carry `D-02`.
- No other section of the style guide was touched; the single commit diff is confined to the §3.3 region.

## Verification

- 79 numbered rows in §3.3: pass.
- Rows 2, 16, 21, 43, 59, 60, 79 all contain a D-03/D-04/D-05 annotation (7 of 7): pass.
- Only the style guide was modified before the task commit: pass.

## Deviations from Plan

None. Plan executed as written. Minor judgement call: in "Also seen" I listed only non-contract names, and wrote "none (all contracts)" for rows 1, 4, 6, 34, 58, 76, 78; rows 57 and 62 read "none" since they have no alternative names to retire.

## Known Stubs

None.

## Threat Flags

None.

## Self-Check: PASSED

- FOUND: .planning/phases/241-codebase-cleanup/241-STYLE-GUIDE.md (modified, 79 rows)
- FOUND: commit 88b3e1d36
