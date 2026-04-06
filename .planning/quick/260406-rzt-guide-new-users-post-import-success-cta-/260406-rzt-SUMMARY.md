---
phase: quick
plan: 260406-rzt
subsystem: frontend
tags: [ux, onboarding, bookmarks, import, cta]
dependency_graph:
  requires: []
  provides: [post-import-cta, bookmarks-notification-dot, bookmarks-empty-state-guidance]
  affects: [Import page, Openings page, PositionBookmarkList]
tech_stack:
  added: []
  patterns: [pulsing-dot-animation, asChild-button-link]
key_files:
  created: []
  modified:
    - frontend/src/pages/Import.tsx
    - frontend/src/pages/Openings.tsx
    - frontend/src/components/position-bookmarks/PositionBookmarkList.tsx
decisions:
  - CTA placed inside ImportProgressBar component (not ImportPage) so it appears per-job inline with the progress bar
  - Pulsing dot uses Tailwind animate-ping — no custom CSS needed
  - Empty state prioritizes Suggest over Save since it requires no manual navigation
metrics:
  duration: ~5 minutes
  completed: 2026-04-06T18:15:00Z
  tasks_completed: 3
  tasks_total: 3
  files_modified: 3
---

# Phase quick Plan 260406-rzt: Guide New Users Post-Import Success CTA Summary

One-liner: Post-import "Explore your openings" CTA, pulsing bookmark tab notification dot, and actionable Suggest-first empty state to guide new users from import to first bookmark.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add success CTA to Import page | 5185e54 | frontend/src/pages/Import.tsx |
| 2 | Add pulsing dot on Bookmarks tab | ab9ac3f | frontend/src/pages/Openings.tsx |
| 3 | Improve bookmarks empty state | 4dbdea0 | frontend/src/components/position-bookmarks/PositionBookmarkList.tsx |

## What Was Built

### Task 1 — Import page CTA (Import.tsx)
Added `BookOpenIcon`, `ArrowRight` imports from lucide-react and `Link` from react-router-dom. After the progress bar `div`, when `isDone && data.games_imported > 0`, a primary Button rendered as a Link navigates to `/openings`. The CTA is hidden for zero-game syncs and failed imports.

### Task 2 — Pulsing notification dot (Openings.tsx)
- **Desktop**: Added `relative` class to the `TabsTrigger value="bookmarks"` and injected a pulsing span (`animate-ping` + solid dot) in the top-right corner when `bookmarks.length === 0`.
- **Mobile**: Added `relative` class to the bookmark icon Button and the same pulsing span with testid `bookmarks-notification-dot-mobile`.
- Dot disappears automatically once `bookmarks.length > 0` (i.e., first bookmark created).

### Task 3 — Bookmarks empty state (PositionBookmarkList.tsx)
Replaced the single-paragraph plain text with a structured `div` containing three elements: a header line "No opening bookmarks yet.", a Sparkles-icon row pointing to Suggest as the primary recommended action, and a Save-icon row as the manual alternative. Both icon colors use `text-primary` to tie them visually to the action buttons above.

## Verification

- `npx tsc --noEmit` — passed (no errors)
- `npm run lint` — passed (no errors)
- `npm run build` — passed (built in 4.39s)
- `npm test` — passed (73/73 tests)
- `npm run knip` — passed (no dead exports)

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None.

## Threat Flags

None — no new network endpoints, auth paths, or schema changes.

## Self-Check: PASSED

- frontend/src/pages/Import.tsx — modified (BookOpenIcon, ArrowRight, Link imports + CTA block)
- frontend/src/pages/Openings.tsx — modified (desktop tab dot + mobile button dot)
- frontend/src/components/position-bookmarks/PositionBookmarkList.tsx — modified (improved empty state)
- Commits 5185e54, ab9ac3f, 4dbdea0 — all present in git log
