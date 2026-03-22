---
phase: 23-launch-readiness
plan: 04
subsystem: frontend-import-ui, documentation
tags: [concurrent-import, notice, readme, branding, MON-03-deferred]
dependency_graph:
  requires: [23-02]
  provides: [STAB-01, BRAND-05, MON-03]
  affects: [frontend/src/pages/Import.tsx, README.md]
tech_stack:
  added: []
  patterns: [lucide-react Info icon, conditional notice rendering]
key_files:
  created: []
  modified:
    - frontend/src/pages/Import.tsx
    - README.md
decisions:
  - "MON-03 (analytics) acknowledged as deferred — no Plausible/analytics implementation in phase 23"
  - "Concurrent importer notice placed inside ImportProgressBar component (per-job, not global)"
metrics:
  duration: ~5 minutes
  completed: 2026-03-22
  tasks_completed: 2
  tasks_total: 2
  files_modified: 2
---

# Phase 23 Plan 04: Concurrent Importer Notice and Professional README Summary

**One-liner:** Concurrent importer notice on Import page using `other_importers` field; README rewritten with Zobrist hash USP, badges, tech stack, and local dev instructions.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add concurrent importer notice to Import page | 121383d | frontend/src/pages/Import.tsx |
| 2 | Create professional README | f416dbc | README.md |

## What Was Built

### Task 1: Concurrent Importer Notice

Added a notice to `ImportProgressBar` (in `Import.tsx`) that appears below the progress bar when `data.other_importers > 0`. The notice:
- Shows the count and platform name: "2 other users are also importing from chess.com — progress may be slower than usual."
- Uses correct singular/plural grammar ("1 other user is" vs "N other users are")
- Disappears automatically when `other_importers` returns to 0 on the next poll (every 2s)
- Has `data-testid="import-concurrent-notice"` for automation
- Uses `Info` icon from `lucide-react`
- Has no dismiss button per spec (ephemeral by design)

Import.tsx has a single layout (no separate desktop/mobile sections for the progress area), so the notice was added once inside `ImportProgressBar`.

### Task 2: Professional README

Rewrote README.md (92 lines -> 117 lines) with:
- Logo, tagline "Engines are flawless, humans play FlawChess", shield.io badges
- Project description highlighting the Zobrist hash position-matching USP
- 7-item feature list including mobile PWA and open source
- Screenshots placeholder pointing to flawchess.com
- Tech stack table (Backend, Frontend, Database, Chess, Auth, Monitoring, Hosting)
- Local Development section with full setup for backend and frontend
- Architecture section explaining Zobrist hashing
- Contributing, License (MIT), and Links (flawchess.com + support@flawchess.com)

### MON-03 Acknowledgement

Analytics (Plausible or similar) is deferred. MON-03 requirement is acknowledged in this plan with no implementation — the decision to use Plausible Cloud was documented in STATE.md during v1.3 roadmap planning. No analytics code is added in phase 23.

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — no stub data or placeholder values were introduced.

## Self-Check: PASSED

- frontend/src/pages/Import.tsx: FOUND with import-concurrent-notice, other_importers, Info icon
- README.md: FOUND, 117 lines (>= 50 minimum)
- Commit 121383d: FOUND
- Commit f416dbc: FOUND
- Build: PASSED (npm run build exits 0)
