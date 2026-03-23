---
phase: quick
plan: 260323-rtg
subsystem: frontend/pwa
tags: [icons, pwa, android, ios, imagemagick]
dependency_graph:
  requires: []
  provides: [padded-pwa-icons, maskable-icon]
  affects: [frontend/vite.config.ts, frontend/public/icons/]
tech_stack:
  added: []
  patterns: [pwa-maskable-icon, separate-any-maskable-purposes]
key_files:
  created:
    - frontend/public/icons/icon-maskable-512.png
  modified:
    - frontend/public/icons/icon-192.png
    - frontend/public/icons/icon-512.png
    - frontend/public/icons/apple-touch-icon.png
    - frontend/vite.config.ts
decisions:
  - "Used ImageMagick fuzz 10% transparency removal to strip black bg for 'any' icons"
  - "Maskable and apple-touch-icon retain solid #0a0a0a bg (no bg removal needed)"
  - "Character sized at 66-70% of canvas to ensure safe zone compliance"
metrics:
  duration: "~5 minutes"
  completed: "2026-03-23T19:13:40Z"
  tasks_completed: 2
  tasks_total: 3
  files_modified: 5
---

# Quick Task 260323-rtg: Create Better Android and iOS App Icons Summary

**One-liner:** Padded PWA icons with separate maskable variant (safe-zone content) to prevent Android adaptive icon clipping of the horse character.

## What Was Done

Generated four icon variants from `logo/flawchess-logo-portrait-1280x1280.png` using ImageMagick, and updated the PWA manifest to declare separate `any` and `maskable` icon entries.

### Icons Generated

| File | Size | Background | Content Size | Purpose |
|------|------|------------|--------------|---------|
| icon-192.png | 192x192 | Transparent | 131x131 (68%) | any |
| icon-512.png | 512x512 | Transparent | 348x348 (68%) | any |
| icon-maskable-512.png | 512x512 | #0a0a0a solid | 338x338 (66%) | maskable |
| apple-touch-icon.png | 180x180 | #0a0a0a solid | 126x126 (70%) | apple |

### Manifest Change

The `icons` array in `frontend/vite.config.ts` was updated from:
- Two entries: 192 (no purpose), 512 (`purpose: 'any maskable'` combined)

To three entries:
- 192 `purpose: 'any'` — transparent bg for browsers/iOS
- 512 `purpose: 'any'` — transparent bg for browsers
- 512 `purpose: 'maskable'` — solid bg, safe-zone padding for Android adaptive icons

## Commits

| Task | Description | Hash |
|------|-------------|------|
| Task 1 | Generate padded PWA icon variants | 5c7e6c1 |
| Task 2 | Split manifest icons into separate any/maskable entries | b60e1c4 |

## Task 3: Checkpoint (Human Verification)

Task 3 is a `checkpoint:human-verify` step. Verification steps:

1. Run `npm run dev` in `frontend/`
2. Open Chrome DevTools > Application > Manifest — verify three icon entries appear
3. Visually inspect icons in `frontend/public/icons/`:
   - icon-192.png and icon-512.png: transparent bg, horse centered with padding
   - icon-maskable-512.png: dark bg, horse centered with extra safe-zone padding
   - apple-touch-icon.png: dark bg, horse centered with padding
4. Upload `icon-maskable-512.png` to https://maskable.app/editor to verify character fits all mask shapes
5. Optionally deploy and re-install PWA on Android to confirm no clipping

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical Detail] Black background removal for "any" icons**
- **Found during:** Task 1
- **Issue:** The plan's command pattern for "any" icons did not include background removal, but the source logo has a solid black background. Without removal, the "transparent bg" icons would have a black square.
- **Fix:** Added `-fuzz 10% -transparent black` to the ImageMagick command for icon-192.png and icon-512.png. The maskable and apple-touch-icon variants did not need this (they use solid #0a0a0a bg intentionally).
- **Files modified:** frontend/public/icons/icon-192.png, frontend/public/icons/icon-512.png

## Known Stubs

None.

## Self-Check: PASSED

- [x] frontend/public/icons/icon-192.png — 192x192 PNG, exists
- [x] frontend/public/icons/icon-512.png — 512x512 PNG, exists
- [x] frontend/public/icons/icon-maskable-512.png — 512x512 PNG, exists (new file)
- [x] frontend/public/icons/apple-touch-icon.png — 180x180 PNG, exists
- [x] frontend/vite.config.ts — three-entry icons array with correct purposes
- [x] Commit 5c7e6c1 — verified in git log
- [x] Commit b60e1c4 — verified in git log
