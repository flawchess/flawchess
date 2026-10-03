---
phase: 229-umami-identify-feature-events
review: 229-REVIEW.md
recorded: 2026-10-03
fix_commit: fcadc13a2
---

# Phase 229 — Code Review Disposition

| ID | Severity | Finding | Disposition | Note |
|----|----------|---------|-------------|------|
| WR-01 | warning | Runbook deletion SQL: real-looking id, preview runs into delete, defaults to COMMIT | fixed | Placeholder `REPLACE_WITH_USERS_ID`, separate preview/delete blocks, delete ends in `ROLLBACK` (fcadc13a2) |
| WR-02 | warning | GameResultDialog tracks analyze after a possibly synchronous navigation | fixed | Track first; test pins page attribution under a navigating onAnalyze (fcadc13a2) |
| WR-03 | warning | Slider `onValueCommit` fires per keyboard arrow step | accepted | Pointer drags fire once; keyboard stepping is rare and each step is a committed value. Debounce adds state for little gain. Revisit if Umami shows bursts |
| WR-04 | warning | Re-clicking the active strength/depth preset sends filter-change | fixed | Guard on `activePreset`; test covers both filters (fcadc13a2) |
| WR-05 | warning | Tapping the last active time control is a no-op but fires; chips carry no on/off | fixed (partial) | No-op clamp now silent (test added). On/off value deferred: would change the registry type for `time-control`, which is a naming change best decided before release |
| WR-06 | warning | MobileFilterDrawer tracks from a useEffect, contradicting the rule | documented | Exception and its precondition written into frontend/CLAUDE.md (fcadc13a2) |
| IN-01 | info | Events fire when optional callback is absent | accepted | Handlers render only with a callback in practice |
| IN-02 | info | chip-cycle conflates flaw chips and Move Stats cells | accepted | Owner decision 2026-10-03: keep one target |
| IN-03 | info | Admin id stays in tracker during impersonation | accepted | Satisfies D-11; D-10 excludes admin ids at analysis time |
| IN-04 | info | analytics.ts imports FilterState type from a component | accepted | Type-only import, no runtime cycle |
| IN-05 | info | Openings toggle reports `color`, Library/Endgames `played-as` | fixed | Owner decision 2026-10-03: unified into `played-as`, `color` target removed (2c437a7f3) |
