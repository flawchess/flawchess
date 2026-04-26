---
phase: 260419-gjq
description: Retire Phase 56 (subsumed by 57) and move Phase 58 (Opening Risk) to backlog
date: 2026-04-19
status: in-progress
---

# Quick Task 260419-gjq — Retire Phase 56 and backlog Phase 58

## Goal

Edit `.planning/ROADMAP.md` to mark Phase 56 as cancelled and move Phase 58 to the backlog as Phase 999.6, without renumbering any shipped phases (57, 57.1, 59, 60, 61).

## Context

- Phase 56 (Endgame ELO — Backend + Breakdown Table) is unimplemented but its scope was absorbed into Phase 57 (Endgame ELO — Timeline Chart), which shipped 2026-04-18.
- Phase 58 (Opening Risk & Drawishness) is unimplemented. v1.10 is endgame-focused, so opening-related work is a better fit for an upcoming Opening Insights milestone.
- `/gsd-remove-phase` cannot be used because it renumbers subsequent phases, which would corrupt shipped phases.
- No stub directories exist at `.planning/phases/56-*/` or `.planning/phases/58-*/` — pure ROADMAP edit.
- Existing backlog entries: 999.1. Next number: **999.6**.

## Tasks

### Task 1 — Mark Phase 56 as cancelled in ROADMAP.md

Edit `.planning/ROADMAP.md`:

- **v1.10 phase checklist (line 139):** change `- [ ] **Phase 56: Endgame ELO — Backend + Breakdown Table** - Backend computation and per-(platform, time-control) table UI with filters` to `- [~] **Phase 56: Endgame ELO — Backend + Breakdown Table** — cancelled, subsumed by Phase 57`.
- **Phase 56 detail section (line 236):** insert a new line immediately after the `### Phase 56: ...` heading: `**Status**: Cancelled — subsumed by Phase 57`.
- **Phase 57 detail section (line 250):** remove the `**Depends on**: Phase 56` line (now moot).

### Task 2 — Move Phase 58 to backlog as 999.6

Edit `.planning/ROADMAP.md`:

- **v1.10 phase checklist (line 141):** delete the `- [ ] **Phase 58: Opening Risk & Drawishness** - ...` line.
- **Phase 58 detail section (lines 287-297):** delete the entire `### Phase 58: Opening Risk & Drawishness` block including all its fields, and the separator blank line before Phase 59.
- **Backlog section (after the existing entries, before the blank lines at line 449):** append:

  ```
  ### Phase 999.6: Opening Risk & Drawishness (BACKLOG)

  **Goal:** Risk and drawishness metrics per position in the move explorer.
  **Requirements:** TBD
  **Plans:** 0 plans
  **Context:** Moved from v1.10 Advanced Analytics — v1.10 is an endgame-focused milestone and opening risk metrics are a better fit for the upcoming Opening Insights milestone (discovering weaknesses in most-played opening lines). Re-evaluate scope at that time.

  Plans:
  - [ ] TBD (promote with /gsd-review-backlog when ready)
  ```

### Task 3 — Update STATE.md

- Append a "Quick Tasks Completed" row for this task.
- Update the "Last activity" line.

### Task 4 — Commit

Commit all artifact + ROADMAP.md changes with message:
`docs(quick-260419-gjq): retire Phase 56 and move Phase 58 to backlog`

## Constraints

- No phase renumbering. Phases 57, 57.1, 59, 60, 61 keep their numbers.
- Do not touch any other roadmap content.
- Do not create or delete phase directories.
