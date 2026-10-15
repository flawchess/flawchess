---
quick_id: 261015-pjr
slug: truthful-train-warm-up-copy-for-guests-w
mode: quick
---

# Quick 261015-pjr: truthful Train warm-up copy for guests with imported games

## Problem

`audienceKey()` in `frontend/src/lib/trainBotCopy.ts` lets `hasGames` win over
`isGuest` (Phase 224 D-03). A guest who imported games therefore gets the
registered-account copy, which says their games are being analyzed. Guest games
are never analyzed automatically (eval queue guards `u.is_guest = false` except
tier-1 manual Analyze clicks), so the promise never comes true. Seen in the
2026-10-15 guest walkthrough in three places: intro warm-up step, every warm-up
reveal tail, warm-up score clause. Intro welcome also promises "puzzles created
from your own games".

Prod: 18 of 37 guests who completed a Train session had imported games.

## Task 1: add a `has_games_guest` audience

- `CopyAudienceKey` gains `has_games_guest`; `audienceKey()` returns it for
  `hasGames && isGuest`. Comment the fix at the site (why D-03's ordering was wrong).
- Add `has_games_guest` entries to `INTRO_WELCOME_COPY`, `INTRO_WARMUP_COPY`,
  `WARMUP_TAIL_COPY`, `WARMUP_SCORE_CLAUSE`: truthful (guest games are not
  analyzed automatically) and ending on the sign-up pitch where it does not
  duplicate the score screen's `GUEST_SIGNUP_ASK_SCORE` second line.
- Stepper copy stays <= `STEPPER_COPY_MAX_CHARS`; no em-dashes.
- Out of scope: per-persona `LANDING_GREETINGS` (audience-agnostic by design),
  `GUEST_SIGNUP_ASK_SCORE`, non-warm-up variants.

files: frontend/src/lib/trainBotCopy.ts

## Task 2: tests

- Replace the "has_games audience (any isGuest value) is byte-identical"
  assertions in `frontend/src/lib/__tests__/trainBotCopy.test.ts` with:
  registered-with-games stays byte-identical; guest-with-games never matches
  the "analyzing / are analyzed" pattern and contains "sign up" (intro warm-up,
  tail) across all four tables.
- Score screen: guest-with-games line 2 stays `GUEST_SIGNUP_ASK_SCORE`.

verify: `cd frontend && npx vitest run src/lib/__tests__/trainBotCopy.test.ts src/pages/__tests__/Train.solveLoop.test.tsx && npm run lint && npm run build`
