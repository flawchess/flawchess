---
quick_id: 261015-pjr
status: complete
commit: cb0be8e3a
---

# Quick 261015-pjr summary

Guests with imported games now get their own Train copy audience
(`has_games_guest` in `frontend/src/lib/trainBotCopy.ts`) instead of the
registered-account strings that claimed their games were being analyzed.

| Surface | Before (guest with games) | After |
|---|---|---|
| Intro welcome | "...puzzles created from your own games." | "Sign up free and you will improve by solving puzzles created from your own mistakes." |
| Intro warm-up step | "We're still analyzing your games..." | "Guest games are not analyzed automatically, so this is a warm-up session. Sign up free and your own mistakes take over." |
| Warm-up reveal tail | "...Your own positions will." | "...Sign up free and your own positions will." |
| Warm-up score clause | "Once your games are analyzed, your own mistakes take over." | "Guest games are not analyzed automatically, so your own mistakes are not here yet." (line 2 stays GUEST_SIGNUP_ASK_SCORE) |

Registered accounts and zero-game audiences are byte-identical.

Out of scope (unchanged): per-persona LANDING_GREETINGS, which still say
"your own games" to everyone by design.

## Verification

- vitest trainBotCopy + Train.solveLoop: 113 passed
- Mutation check: reverting the audienceKey line fails the 3 new tests
- Full frontend suite 5614 passed; lint, build (tsc -b), knip clean
- CHANGELOG [Unreleased] Fixed bullet added
