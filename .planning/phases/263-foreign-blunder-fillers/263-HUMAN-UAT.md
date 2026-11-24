---
phase: 263-foreign-blunder-fillers
status: complete
source: plan 263-10 (owner review items raised by plans 02, 03, 05, 08, 09 plus the orchestrator and owner-only steps)
created: 2026-11-23
---

# Phase 263 Human UAT

Items for `/gsd-verify-work`. Each has what to check and the pass condition. Items 1 to 3 are owner decisions,
item 4 is run by the orchestrator, item 5 is a manual step before the browser walk-through, item 6 is only reachable
after the deploy, item 7 needs the dev stack, item 8 needs a device. Items 9 to 11 are informational (no action requested) and recorded so they are not rediscovered.

Order of operations: item 4 (prod EXPLAIN) runs before the squash-merge; item 5 (dev DB upgrade) runs right before
the browser walk-through in item 7; item 6 (old filler reveal) is only reachable after the deploy.

## 1. Owner copy review of every new string

**Check:** read each string in the app, in context, and approve or reword. Score-screen, guest and Welcome wording
is a proposal (orchestrator ruling 5), not owner-written.

| String | File | Text |
|---|---|---|
| D-11 return tail (every foreign puzzle) | `frontend/src/lib/trainBotCopy.ts` (`FOREIGN_TAIL`) | "From a similarly rated player's game, so it won't come back." |
| D-12 no-own welcome (owner-written) | `frontend/src/lib/trainBotCopy.ts` (`INTRO_NO_OWN_PUZZLES_WELCOME_COPY`) | "Hi there! These puzzles come from games of players at your level. Once some of your games are imported and analyzed, puzzles will come from your own games." |
| D-13 start sentence | `frontend/src/lib/trainBotCopy.ts` (`NO_OWN_DUE_TODAY_COPY`, testid `train-landing-no-own-due`) | "None of your own mistakes are due today. Today's puzzles come from similarly rated players." |
| no-own score note, first session (proposal) | `frontend/src/lib/trainBotCopy.ts` (`NO_OWN_PUZZLES_NOTE_FIRST`) | "Those puzzles came from games of players at your level." |
| no-own score note, later sessions (proposal) | `frontend/src/lib/trainBotCopy.ts` (`NO_OWN_PUZZLES_NOTE_LATER`) | "Those came from games of players at your level, so nothing comes back yet." |
| guest sign-up line on the score screen (proposal, new) | `frontend/src/lib/trainBotCopy.ts` (`GUEST_SIGNUP_ASK_SCORE`) | "Sign up free and your own blunders become your puzzles. Your streak and everything you have solved stay exactly where they are." |
| Welcome page delta (proposal) | `frontend/src/pages/Welcome.tsx` (`DELTA_2`) | "Train switches from other players' blunders to the mistakes in your own games." |
| foreign verdict fact | `frontend/src/lib/trainBotCopy.ts` (`fromForeignGame`) | "Several moves work here, just not the game move." |
| neutral tour chips line | `frontend/src/lib/trainBotCopy.ts` (tour chips string) | "Each chip is a line: your Move, the engine's Best, and the Game move if known. ..." |
| reveal footer (from `game_info`, no names) | `frontend/src/components/train/blunder-check/BlunderCheckGameFooter.tsx` (`ForeignGameFooter`) | "<time control> · player rated <rating> · <date>" |

**Pass:** each line approved, or the owner gives replacement wording (then reword the constant and update the one test
that pins it).

## 2. D-13 "established user" reading (assumption)

**Check:** the D-13 start sentence shows when the user `hasGames` and `modes.puzzles.first_session_done === true`,
and the open session holds no own puzzle (none due, the exhausted day). The reading is strict so a pending progress
query never flashes the sentence (263-02).

**Pass:** the owner confirms this definition of "established user" or names another.

## 3. Research A5 and A6

- **A5:** D-16 (one sharp puzzle in a first-ever session) binds only when the session has a foreign shortfall; an
  all-own first session of soft puzzles stays as it was (263-03). Pass: owner accepts, or asks to force a sharp foreign
  pick into every first session.
- **A6:** the "???" facepalm badge shows on a foreign game move, read from the game owner's flaw row (263-06). Pass:
  owner accepts, or asks for the badge to be switched off for foreign puzzles (one boolean).

## 4. Prod EXPLAIN of the draw (run by the orchestrator, before the squash-merge)

**Check:** run `263-PROD-EXPLAIN.sql` through the read-only prod MCP, each statement twice, cold: the band step at
level 1500 and at level 2600, and the nearest step at level 2600. Report execution time, buffer reads and the row count
per statement. Compare with `263-RESEARCH.md` section Prod EXPLAIN results (CTE alone at system(0.1): 91 ms, 344 page
reads; stage two about 400 ms cold).

**Pass:** step one (the band draw, both levels) at most 0.5 s cold; step one plus step two at most 1.5 s cold. A miss
blocks the squash-merge and goes back to planning (lower the sample percent, not the `ORDER BY random()`). Run the same
statements once more after the deploy as confirmation and record both readings here.

Result before the squash-merge: **pass** (2026-11-23, orchestrator, read-only prod MCP, one cold run per statement;
the second cold run per statement was not done, each sample reads different pages so one run is already cold):

| Statement | Execution | Planning | Rows | Buffers read / hit | Sampled games in band |
|---|---|---|---|---|---|
| 1. band, level 1500, system(0.1) | 201 ms | 14 ms | 49 | 612 / 2718 | 728 of 755 scanned |
| 2. band, level 2600, system(0.1) | 146 ms | 8 ms | 35 | 571 / 952 | 180 of 185 scanned |
| 3. nearest, level 2600, system(0.4) | 337 ms | 8 ms | 34 | 1427 / 889 | 4102 candidates |

Step one is at most 201 ms against the 0.5 s budget; step one plus step two at level 2600 is 483 ms against 1.5 s.
At level 2600 the band step alone found 180 band games and 35 servable blunders, so the nearest step would not run
for a default session there.
Result after the deploy: _pending_ (also run the band and nearest statements once with `LIMIT 200` in place of `LIMIT 40`: the
game limit is clamped 40..200 and the pre-merge run measured 40 only; security audit note on T-263-04 / T-263-26)

## 5. Manual pre-UAT step: upgrade the shared dev DB

**Not done by any executor.** The dev DB is shared with the main checkout and has NOT been upgraded (heads
`b3d5f7a9c264` then `c4e6a8b0d375` are pending). Run just before the browser walk-through in item 7, from this
worktree (`/home/aimfeld/Projects/Games/flawchess-263`):

```bash
uv run alembic current            # record the output; the dev DB was at a7c3e5f9b261 at plan time
uv run alembic upgrade head       # applies e5c1b7d3a9f2, b3d5f7a9c264 and c4e6a8b0d375
```

Warnings:

- The main checkout's backend maps the columns this phase drops (`drill_sessions.is_warmup`,
  `drill_solves.sharp_puzzle_id`), so its Train endpoints fail until this branch is squash-merged. Once the upgrade is
  applied the main checkout's backend must run this branch's code, or be stopped.
- The migration deletes untouched open dev sessions that hold lichess filler rows.
- Migration `c4e6a8b0d375` is one-way for the dropped `drill_solves.sharp_puzzle_id` (owner decision 2026-11-23), for
  `is_warmup`, and for the deleted untouched sessions (122 measured on prod). The downgrade re-adds both columns empty.
  Unlike the dev DB, this applies to prod at deploy time.

To undo on dev, from this worktree:

```bash
uv run alembic downgrade e5c1b7d3a9f2
```

(`e5c1b7d3a9f2` is the revision before both phase migrations; the downgrade deletes source 3 rows first.)

**Pass:** `alembic current` shows `c4e6a8b0d375 (head)` after the upgrade, and the dev backend starts and serves
`/train/*`.

## 6. Reveal of an old lichess filler right after the deploy

**Check:** complete a session that contains a lichess filler just before the deploy, then open the reveal of that
filler after the deploy. Expect a few 404 events in Sentry for the reveal right after the deploy (the filler set and its
service are gone).

**Pass:** the reveal shows "Couldn't load the full reveal details." while the verdict (points, streak) stays usable.

## 7. Browser walk-through on the dev stack (after item 5)

**Check:** a fresh account (guest and registered), first session filled by foreign blunders. Requires foreign games in
the dev DB at the account's level (non-guest users with analyzed games); otherwise the session stays short, which is
the accepted empty-pool outcome.

- the intro opens with the D-12 welcome (item 8 for the phone measurement);
- the D-11 tail shows on every foreign puzzle after solving, the neutral reveal footer shows time control, player
  rating and date with no name and no link;
- Analyze on a foreign puzzle opens the position only, never the game;
- the "???" badge and the "game move" wording read as neutral (no "your move");
- the score screen shows the no-own note and (as a guest) the sign-up line;
- a registered user with games and a finished puzzles session sees the D-13 sentence on an exhausted day;
- the Train accuracy board counts own puzzles and red herrings only; the Activity dashboard splits the source rows.

**Pass:** each line behaves as described and the owner approves the look.

## 8. Phone checks (device)

- **D-12 welcome length (263-02):** the welcome is 155 characters, over `STEPPER_COPY_MAX_CHARS` (145). The wording is
  left exactly as the owner wrote it, and the copy test only holds it to seven 24 px lines. Pass: it fits the intro
  bubble without clipping at 375x667; otherwise shorten the wording or raise the budget on purpose.
- **Activity label (263-05):** the Activity dashboard row for the retired source is labelled "Sharp filler (retired)",
  shortened from the D-19 example "Sharp filler · lichess (retired)" because the long label overlapped at 320 and
  360 px. Pass: the owner accepts the shorter label, or picks another that fits.

## 9. Informational: test gaps recorded, no action requested

- **263-03:** no test can isolate the `answer_key_present` servability predicate, because two other predicates already
  exclude an empty blob.
- **263-08:** the explicit legacy-row skip on resume is not isolated by a test; the generic no-game skip already drops
  those rows.

## 10. Deferred (out of scope, recorded per orchestrator ruling 6)

- Cross-mode repeat: a foreign blunder served in Train can later appear inside a blunder-check foreign window for the
  same user (blunder check's served set is `blunder_check_windows` only). Not covered by D-17.
- An untouched open session whose every row became unservable after composition (no solve yet) still waits for expiry
  (pre-existing SR-orphan behaviour).
- Anonymised in-app view of a stranger's game and a facepalm-weighted filler draw: CONTEXT deferred ideas.

## 11. Release

Before the squash-merge, run the full pre-merge gate once more from the merge base if `main` has moved. The CHANGELOG
bullets are already under `## [Unreleased]` (`Changed` and `Removed`).

## 12. Code review follow-ups (added after the review, 2026-11-23)

**Owner wording needed (review WR-03, open):** the score-screen bubble for a session with no own puzzles
(`frontend/src/lib/trainBotCopy.ts`, the `noOwnPuzzles` notes) says "Once your games are analyzed, your own mistakes
take over". An established user on an exhausted day (all own puzzles on cooldown) sees that line although their games
are analyzed, while the start screen of the same session shows the D-13 sentence. Decide the wording for that case.

**Owner sign-off on new copy (review WR-04, fixed in 903d6ccec):** the Accuracy board's not-entered line in
`frontend/src/lib/trainLeaderboard.ts` now reads "You're not on this board yet: similarly rated players' blunders
don't count here." (was: "tactics puzzles don't count here").

**Informational:** review WR-01 (D-16 sharp pick lost from the nearest step) and WR-02 (foreign reveal sent the game
time, now date only) were fixed with tests that fail without the fix; dispositions are in `263-REVIEW-DISPOSITION.md`.
The security audit found that red-herring rows still send another user's `game_id` on compose, resume and reveal
(pre-existing, outside this phase), and that the library game and tactic-lines endpoints are not owner-scoped by
design, so the nulled `game_id` is the only control for a foreign puzzle. Candidates for a seed.

