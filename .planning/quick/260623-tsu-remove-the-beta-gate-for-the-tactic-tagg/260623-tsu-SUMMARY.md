---
quick_id: 260623-tsu
slug: remove-the-beta-gate-for-the-tactic-tagg
date: 2026-06-23
status: complete
commit: 2cd0bc99
---

# Quick Task 260623-tsu: Remove the beta gate for tactic tagging — Summary

## What changed

The tactic-tagging feature was gated on `userProfile.beta_enabled` in six frontend
surfaces (no backend gating — confirmed). Removed every gate so the feature is
visible to all users:

- **`LibraryGameCard.tsx`** — removed `betaEnabled` and `showTacticColumns`; the
  three-column Missed / Allowed / Context chip layout, tactic-motif collection, and
  tactic-depth arrow badges now always render. Dropped the non-beta single-row
  fallback and the `useUserProfile` import.
- **`FlawCard.tsx`** — tactic-motif chips, depth labels, and legend motifs always
  render; dropped the `useUserProfile` import.
- **`FlawFilterControl.tsx`** — tactic sections (depth / orientation / families /
  advanced) now gate on the tab opt-in (`showTacticFilter`) alone; the Context
  section is always collapsible. Dropped the `useUserProfile` import.
- **`EvalChart.tsx`** — removed the `betaEnabled` prop entirely; tooltip tactics
  always listed for the active marker.
- **`TacticComparisonGrid.tsx`** — removed the `return null` non-beta gate and
  merged the inner/outer component split into a single component.
- **`TacticMotifChip.tsx`, `FlawStatsPanel.tsx`** — updated stale beta-gate comments.

The `beta_enabled` field on the profile type (`types/users.ts`) is **kept** — it's
part of the API response contract and may gate a future beta. It is simply no longer
read anywhere in the frontend.

### Tests + changelog

- Removed the `beta gating` describe block in `FlawFilterControl.test.tsx` and the
  `non-beta user → renders null` test in `TacticComparisonGrid.test.tsx`, plus their
  now-dead mock scaffolding.
- Removed dead `useUserProfile`/`useAuth` mocks from `LibraryGameCard.test.tsx` and
  `FlawCard.test.tsx` (those components no longer read either hook).
- Fixed the `FlawsTab.test.tsx` mock comment (still required for `is_guest`).
- Added a `### Changed` CHANGELOG entry under `[Unreleased]`.

## Verification

- `npx tsc -b` → 0 errors
- `npm run lint` → 0 errors (only pre-existing `coverage/` artifact warnings)
- `npm run knip` → clean
- `npm test -- --run` → 92 files, 1098 tests passed
- `grep betaEnabled frontend/src` (non-test) → no matches

Backend untouched, so the backend gate (ruff/ty/pytest) does not apply.

## Commit

`2cd0bc99` feat(library): remove beta gate for tactic tagging
