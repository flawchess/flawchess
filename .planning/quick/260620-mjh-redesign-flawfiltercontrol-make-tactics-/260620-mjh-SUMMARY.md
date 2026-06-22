---
phase: quick-260620-mjh
plan: "01"
subsystem: frontend/filters
status: complete
tags: [ui, filters, flaws, collapse, tactic-controls]
dependency_graph:
  requires: []
  provides: [FlawFilterControl collapsed Context section]
  affects: [FlawFilterControl, FlawsTab, GamesTab]
tech_stack:
  added: []
  patterns: [hand-rolled collapsible (mirrors FilterPanel "More" pattern), useState toggle, count badge]
key_files:
  created: []
  modified:
    - frontend/src/components/filters/FlawFilterControl.tsx
    - frontend/src/components/filters/__tests__/FlawFilterControl.test.tsx
    - frontend/src/pages/library/__tests__/FlawsTab.test.tsx
decisions:
  - Context tag families collapsed behind hand-rolled toggle — no Radix Collapsible added
  - CONTEXT_TAGS computed at module level (not per render) for count badge
  - renderExpanded() test helper avoids per-test toggle boilerplate
metrics:
  duration: ~8 min
  completed: 2026-06-20
  tasks_completed: 3
  files_changed: 3
---

# Quick 260620-mjh: Redesign FlawFilterControl — Collapsed Context Section Summary

Collapsed the secondary Context tag families (Timing/Opportunity/Impact/Game Phase) behind a hand-rolled toggle, making the primary tactic controls (Severity, Orientation, Depth, Tactic motif) visible by default.

## What Was Done

**Task 1 — Reorder layout and collapse Context families behind a "More" toggle**

Restructured `FlawFilterControl.tsx` to the new top-to-bottom order:

1. Severity (always)
2. Orientation (showTacticFilter=true only)
3. Tactic Depth (showTacticFilter=true only)
4. Tactic motif (showTacticFilter=true only)
5. Collapsed "Context" section (always) — hand-rolled collapsible mirroring FilterPanel.tsx's "More" pattern
6. Filter Logic explainer (always)

The Context section toggle:
- `data-testid="filter-flaw-context-toggle"`, `aria-expanded`, `aria-controls="flaw-filter-context-content"`
- Rotating ChevronDown icon
- Count badge: "Context · N" when N Context tags selected, "Context" when 0
- `CONTEXT_TAGS` is a module-level `Set<FlawTag>` built once from `FAMILY_SECTIONS.flatMap(s => s.tags)`
- Removed the old standalone `<div className="border-t border-border/40" />` divider; the Context wrapper carries its own `pt-3 border-t`

**Task 2 — Update tests**

- Added `renderExpanded()` helper: renders + clicks the Context toggle, used in all tests that need Context family/tag testids
- Updated `tag family groups`, `canonical tag names`, `accessibility` describe blocks to use helper
- Added new `context collapse (Quick 260620-mjh)` describe block: hidden-by-default, aria-expanded=false default, aria-expanded=true after click, reveal-on-click, collapse-on-second-click, count badge "Context · 2"/"Context", Context-present-when-showTacticFilter-false (8 tests)
- Fixed `FlawsTab.test.tsx`: added `fireEvent` import; expanded Context in all FlawFilterControl instances before asserting `filter-flaw-tag-miss`

**Task 3 — Full frontend gate**

`npm run lint`, `npm run knip`, `npx tsc -b`, `npm test -- --run` all passed with zero errors. 1057 tests, 88 test files.

## Commits

- `6626e2d7` — feat(quick-260620-mjh): collapse Context tag families behind a toggle in FlawFilterControl
- `3b525fe7` — test(quick-260620-mjh): update FlawFilterControl tests for collapsed Context section

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check: PASSED

- `frontend/src/components/filters/FlawFilterControl.tsx` — exists, modified
- `frontend/src/components/filters/__tests__/FlawFilterControl.test.tsx` — exists, modified
- `frontend/src/pages/library/__tests__/FlawsTab.test.tsx` — exists, modified
- Commits `6626e2d7` and `3b525fe7` exist in git log
- Full frontend gate passed (lint, knip, tsc -b, 1057 tests)
