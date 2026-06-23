---
quick_id: 260623-tsu
slug: remove-the-beta-gate-for-the-tactic-tagg
date: 2026-06-23
---

# Quick Task 260623-tsu: Remove the beta gate for the tactic tagging feature (frontend)

## Goal

Tactic tagging was visible only to users with `userProfile.beta_enabled`. The gate
lived in several frontend surfaces (no backend gating). Remove it so every user
sees the feature; keep the `beta_enabled` field on the profile type (API contract).

## Tasks

1. **Remove the beta gate from all tactic surfaces.**
   - `LibraryGameCard.tsx`: drop `betaEnabled`/`showTacticColumns`; always render the
     Missed/Allowed/Context column layout, tactic-motif chips, and depth arrow badges.
   - `FlawCard.tsx`: always render tactic-motif chips, depth labels, and legend motifs.
   - `FlawFilterControl.tsx`: gate tactic sections on the tab opt-in (`showTacticFilter`)
     only; Context section is always collapsible.
   - `EvalChart.tsx`: remove the `betaEnabled` prop; tooltip tactics always listed.
   - `TacticComparisonGrid.tsx`: drop the null-on-non-beta gate; merge the inner/outer
     split into one component.
   - `TacticMotifChip.tsx` / `FlawStatsPanel.tsx`: update stale beta-gate comments.
   - Remove now-unused `useUserProfile` imports.

2. **Update tests + changelog.**
   - Remove tests asserting non-beta hiding (`FlawFilterControl`, `TacticComparisonGrid`).
   - Remove now-dead `beta_enabled`/`useAuth` mocks (`LibraryGameCard`, `FlawCard`),
     fix the stale `FlawsTab` mock comment (still needed for `is_guest`).
   - Add a `### Changed` CHANGELOG entry under `[Unreleased]`.

## Verify

- `npx tsc -b` — zero errors
- `npm run lint` — zero errors
- `npm run knip` — clean
- `npm test -- --run` — full suite green
- `grep -rn "betaEnabled" frontend/src` (non-test) — no matches

## Done

All gates green; no `beta_enabled`/`betaEnabled` reads remain in frontend source
(the profile type field is retained as the API contract).
