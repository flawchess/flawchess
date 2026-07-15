---
phase: 169-clocked-board-game-loop-usebotgame
plan: 07
subsystem: verification
tags: [uat, human-verify, acceptance-gate]

requires:
  - phase: 169 (plan 06)
    provides: "The assembled /bots page — the complete clocked bot game under test"
provides:
  - "Human sign-off on the full clocked bot game (nine-point browser checklist, PLAY-03..09)"
affects: [170-localstorage-resume, 171-bots-page-setup-and-store]

tech-stack:
  added: []
  patterns: []

key-files:
  created: []
  modified: []

key-decisions:
  - "Checkpoint approved by the developer with no punch list — no gap-closure pass needed"

requirements-completed: [PLAY-03, PLAY-04, PLAY-05, PLAY-06, PLAY-07, PLAY-08, PLAY-09]

duration: human checkpoint (approved 2026-07-12)
---

# Phase 169 Plan 07: Human UAT of the clocked bot game — Summary

Verification-only plan. The developer ran the nine-point browser checklist on the
real `/bots` route (dev server, client-side game) and **approved** the checkpoint
with no failing items on 2026-07-12:

1. PLAY-03 — drag + click-to-click moves, illegal/off-turn snap-back, Fischer
   increment credited, input locked during bot think.
2. PLAY-05/D-05/D-06 — bot clock ticks down live, thinking dot pulses, reveal
   delay floors fast moves, bot never flags.
3. PLAY-04 — hidden-tab interval does not unfairly drain either clock.
4. D-07 — low-time red digits with tenths, single low-time sound at the crossing.
5. PLAY-06 — end condition reached, result dialog shows correct outcome + reason.
6. PLAY-07/D-04 — two-step resign confirm, draw-offer throttle after decline
   (tooltip + blip), bot never offers a draw or resigns.
7. PLAY-08/D-08 — mute toggle persists across reload; vendored lila sfx set
   accepted tonally (no alternative set requested).
8. PLAY-09/D-11/D-12 — dialog dismiss → persistent strip, Analyze deep-link
   lands on /analysis with the game's moves, New game restarts.
9. D-13 — move scroll-back goes view-only with a Return-to-live affordance; new
   moves only apply at the live position.

No code changes were made by this plan. No punch list; no `/gsd-plan-phase --gaps`
pass required. This closes the phase acceptance gate ahead of `/gsd-verify-work`.
