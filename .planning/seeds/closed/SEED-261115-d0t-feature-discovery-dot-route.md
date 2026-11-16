---
id: SEED-261115-d0t
status: closed. Resolved by Phase 255 (squash-merge 6fd0ff2f2 on main, 2026-11-15; unreleased). Completion is stored server-side on users.prompt_state.feature_route. Owner decision D-23 added during planning: a locked step pauses the route. Left open: review Info items IN-01..IN-05 (255-REVIEW-DISPOSITION.md) and a multi-day lock without a games delete keeping the old current stamp.
promoted_to: Phase 255 (2026-11-15, owner: build now while Phases 252 and 254 wait; completion stored server-side)
promoted: 2026-11-15
planted: 2026-11-15
planted_during: v2.29, Phase 254 executing. Recovered from an unsaved /gsd-explore session with the owner (2026-11-09, session d7913f78); the session stopped on the storage question below and wrote no artifact
trigger_when: owner wants to announce a new feature to existing users (first case: blunder-check training leaving beta), or any nav/onboarding work. Frontend-only unless server-side storage is chosen, so it can run beside compute-heavy backend phases
scope: small to medium, one phase. A route registry, one arbiter hook, dot rendering on nav items and subtabs, migration of the three existing dot systems. Plus a users column and backfill if completion is stored server-side
---

# SEED-261115-d0t: One feature-discovery route for the red pulsating dot

One coherent strategy for the red pulsating dot: an ordered route of features, with the dot in exactly one
place at a time, moving from one unexplored feature to the next. It covers both onboarding (new users) and
announcing a new feature (returning users) with a single mechanism.

## Why This Matters

Three dot systems exist today and do not know about each other:

- **Nav dots** (`frontend/src/App.tsx`, `useNavIndicators`, `useUserFlag`): Openings then Endgames (the
  Endgames dot is gated on the Openings visit), plus an independent Train dot and the Train waiting-count
  badge. The Openings and Train dots can show together.
- **Openings sidebar chain** (`frontend/src/pages/openings/useSidebarState.ts`): played-as, then filters, then
  bookmarks. Raw localStorage keys (`played-as-hint-dismissed`, `filters-hint-dismissed`), not scoped per
  user. A working small version of the route idea.
- **Re-announcing Train** was done by minting a new flag key (`train_bots_visited`), so the versioning
  problem is already here.

There is no way to tell a returning user that a feature such as blunder-check training now exists. SEED-199
(closed, dormant) has the reach data that motivates this and noted two weak spots: flags are per device, and
a dot on a tab that has scrolled out of view does nothing.

## Owner decisions (2026-11-09)

1. **Dot only.** No "What's New" panel and no static "New" pills.
2. **One dot at a time**, on a route that goes from one unexplored feature to the next.
3. **The dot must solve the path problem**: a target is often a subtab, so the dot shows on the nav item
   first and on the subtab once the user is in the section. One logical step, drawn in two places.

## Proposed shape (discussed, not locked)

- **One ordered route.** Each step has an ID, a target path (e.g. `nav:train` then
  `subtab:train/blunder-check`) and a completion condition (visited, or used).
- **A new feature is a step appended to the route.** New users reach it after onboarding; veterans who have
  finished everything else go straight to it. No second announcement system.
- **One arbiter hook** returns the first unfinished step and replaces the three systems above.
- **Completion is a set of step IDs, not an index** (the owner's first idea was an index in localStorage). An
  index breaks when a step is inserted or reordered.

## Open questions

1. **Where completion lives**: decided server-side (owner, 2026-11-15); the shape is open. Background: localStorage: no backend work, but
   every new device or browser replays the route. Server-side (e.g. a JSONB column on `users`): follows the
   user across devices and makes the bootstrap a one-time backfill; guests already have user rows.
2. **Bootstrapping existing users.** Veterans start with no completion IDs and would be walked through
   Openings, filters and Endgames again before reaching the new feature. Seed completion from the existing
   flags, or from server data (bookmarks exist, pages visited).
3. **A stuck dot blocks the route.** A user who never cares about bookmarks would never see the
   blunder-check dot. Suggested: new-feature steps take priority over leftover onboarding steps, and an
   onboarding step auto-skips after a few ignored sessions. Not decided.
4. **Interplay with the Train waiting-count badge**, which today outranks the Train dot.
5. **Route order and contents**, and whether SEED-199's sticky subnav has to ship first so a subtab dot is
   visible on long pages.

## Breadcrumbs

- `../../frontend/src/App.tsx` (`useNavIndicators`, `NavDot`, flag constants)
- `../../frontend/src/hooks/useUserFlag.ts`
- `../../frontend/src/pages/openings/useSidebarState.ts`, `../../frontend/src/pages/Openings.tsx` (sidebar chain)
- `closed/SEED-199-subnav-discoverability.md` (Umami reach data, sticky subnav, subtab dot caveats)
- `SEED-261108-dk0-blunder-check-training.md` (the first feature to announce)
