---
phase: 263-foreign-blunder-fillers
reviewed: 2026-11-23T22:35:14Z
depth: standard
files_reviewed: 39
files_reviewed_list:
  - alembic/versions/20261202_120000_b3d5f7a9c264_phase_263_foreign_blunder_source.py
  - alembic/versions/20261202_130000_c4e6a8b0d375_phase_263_retire_warmup_and_filler_identity.py
  - app/models/drill_session.py
  - app/models/drill_solve.py
  - app/repositories/blunder_check_repository.py
  - app/repositories/train_leaderboard_repository.py
  - app/repositories/train_repository.py
  - app/routers/blunder_check.py
  - app/routers/train.py
  - app/schemas/blunder_check.py
  - app/schemas/train.py
  - app/services/activity_queries.py
  - app/services/blunder_check_grading.py
  - app/services/guest_cleanup_service.py
  - app/services/train_foreign.py
  - app/services/train_pool.py
  - frontend/scripts/check-activity-layout.mjs
  - frontend/src/App.tsx
  - frontend/src/components/admin/TrainScoreScreenDemo.tsx
  - frontend/src/components/train/ImportAskActions.tsx
  - frontend/src/components/train/TrainReveal.tsx
  - frontend/src/components/train/TrainRevealGameFooter.tsx
  - frontend/src/components/train/TrainScoreScreen.tsx
  - frontend/src/components/train/TrainSolveScreen.tsx
  - frontend/src/components/train/TrainStartScreen.tsx
  - frontend/src/components/train/TrainVerdictDetails.tsx
  - frontend/src/components/train/blunder-check/BlunderCheckGameFooter.tsx
  - frontend/src/hooks/useTrainRevealQuery.ts
  - frontend/src/lib/trainBotCopy.ts
  - frontend/src/pages/Train.tsx
  - frontend/src/pages/Welcome.tsx
  - frontend/src/pages/activity/ActivityPage.tsx
  - frontend/src/pages/activity/render.js
  - frontend/src/types/activity.ts
  - frontend/src/types/train.ts
  - tests/conftest.py
  - tests/repositories/test_train_foreign.py
  - tests/services/test_train_foreign.py
  - tests/test_phase_263_migration.py
findings:
  critical: 0
  warning: 4
  info: 7
  total: 11
  necessity: 0
status: issues_found
---

# Phase 263: Code Review Report

**Reviewed:** 2026-11-23T22:35:14Z
**Depth:** standard
**Files Reviewed:** 39
**Status:** issues_found

## Summary

Scope: `git diff d28f50117..HEAD -- . ':!.planning'` on branch `gsd/phase-263-foreign-blunder-fillers` (HEAD `583c9597a`), reviewed in the worktree. Source files were read in full or through their full diff; the four test files listed were read for reliability only, the other test files in the diff were not line-reviewed. One finding (WR-04) sits in a file the phase did not touch (`frontend/src/lib/trainLeaderboard.ts`) because the deletion left its copy stale. The necessity rubric (`necessity-review.md`) was read; no necessity finding met its evidence rule (the one candidate, the `reconstructed[:n]` cap, predates the phase).

No blocker was found. The eight named claims, attacked one by one:

1. **Privacy.** Holds for ids, names and links on every path read: fresh compose, resume, the IntegrityError race-loser resume, solve, reveal, review. `_wire_game_id` nulls the id at both `ComposedPuzzle` sites and in `RevealedPuzzle`; no other endpoint serializes a `drill_solves.game_id` (archive reads `drill_items`, activity returns counts, `puzzle_cooled_pairs` filters `source == SR_ITEM`). One gap against D-21's wording: the reveal sends the stranger's game timestamp to the second, not a date (WR-02).
2. **Owner keying.** Holds at every site found: `_existing_owner_flaw_keys`, `_composition_puzzle_types`, `_answer_keys_by_position` (flaw and position joins), `_classify_and_certify_solve`, `_mark_session_complete_if_done`, and in `reveal_for_puzzle` the move SAN, the flaw blob and the facepalm flag. No solver-keyed read of a foreign row remains.
3. **The draw.** Excludes the solver's games and guests in SQL, is capped at two statements, and returns `[]` on an empty pool. The sort is bounded by the TABLESAMPLE (0.1% and 0.4% of `games`) and the CTE `LIMIT` (40 to 200 games). Two parts of the claim are false as worded (IN-05), and the D-16 sharp guarantee has a hole (WR-01, reproduced).
4. **Migration c4e6a8b0d375.** The DELETE predicate is exactly "open, no solved row, at least one unsolved `source = 2` row". `drill_solves.session_id` is the only FK to `drill_sessions` and cascades. The downgrade restores both columns with the Phase 206 definitions. No reader of `is_warmup` or `sharp_puzzle_id` is left in `app/`, `scripts/`, `analysis/`, `bin/`, `docs/` or `frontend/src` (only the two migrations and tests mention them).
5. **Legacy `source = 2` rows.** Solved rows serialize as `"sharp_filler"`, keep their points (`_POINTS_EXPR` has no source filter) and are untouched by both migrations. Unsolved rows are skipped by `load_session_puzzles`, excluded from `_mark_session_complete_if_done`, and graded keyless if a stale client posts one. Residual: the nav badge still counts them until Train is opened (IN-06).
6. **Accuracy board.** `_ACCURACY_SOURCES` is applied at both aggregate sites (`fetch_week_aggregates`, `fetch_session_contribution`); points totals are unfiltered. The user-facing copy for "on Points but not on Accuracy" still names the retired lichess puzzles (WR-04).
7. **Lazy completion.** Guarded by `status == "open" and not puzzles and solved_results`, so it cannot complete a session with a servable puzzle or an untouched one. `apply_day_completion` is idempotent on `streak_credited_on`, and `now_utc` is threaded from the router's `dev_now_utc`. No defect found.
8. **Frontend.** Types match the server schemas field for field. The foreign footer never calls `useLibraryGame`, and Analyze opens the position only. The `own_puzzle_count === 0` score-screen copy is false for the exhausted-day user D-13 was written for (WR-03).

Also checked and clean: no `asyncio.gather`, no inline `datetime.now()`, no N+1 in composition (the foreign stage costs at most five statements), no new `except` block, and the nesting gate passes (`check_function_size.py app/ --fail-over-depth 4`: 1700 functions, no breaches).

## Narrative Findings (AI reviewer)

Findings follow, grouped by severity. Confidence is stated where it is not certain.

## Warnings

### WR-01: D-16 sharp guarantee is lost when the sharp pick comes from the second draw step

**Classification:** WARNING
**File:** `app/repositories/train_repository.py:2738-2759` (`_foreign_picks`), `app/repositories/train_repository.py:2845` (`reconstructed[:shortfall]`)
**Issue:** `pick_foreign_candidates` moves the first sharp candidate to the front of *its own step's* ranking, and `_foreign_picks` appends each step's picks with `picks.extend(...)`. A sharp candidate found only by the nearest step therefore lands after every band-step pick. `_backfill_foreign_blunders` then trims to `reconstructed[:shortfall]`, while `_foreign_picks` collects `shortfall + FOREIGN_FILLER_RECONSTRUCT_SLACK` picks. When the band step returns `shortfall` or `shortfall + 1` picks with no sharp one, the nearest step runs with `want_sharp=True`, finds a sharp blunder, places it at index `>= shortfall`, and the trim drops it. The first-ever session then has no sharp puzzle although one was drawn, which is what D-16 rules out.

Reproduced with a pure probe (both seams stubbed, no database): `shortfall=6`, band step returning six soft candidates, nearest step returning sharp ones gave picks `[5, 2, 6, 3, 4, 1, 103, 100]`, sharp at indexes 6 and 7, none inside the trim.

Reach is narrow: it needs a thin band sample and no sharp blunder among its picks (about 0.62^n for n picks at the measured 38% sharp share). It matters most at the rating extremes, where the band step is thin by design. `test_first_ever_session_opens_on_sharp_foreign_blunder` does not cover a sharp pick that arrives in step two.
**Fix:** Keep the D-16 pick in front across steps, for example in `_foreign_picks`:

```python
wanted_sharp = want_sharp and not _has_sharp(picks)
new = pick_foreign_candidates(..., want_sharp=wanted_sharp, rng=rng)
if wanted_sharp and new and _has_sharp(new[:1]):
    picks = [new[0], *picks, *new[1:]]  # D-16: the sharp pick must survive the shortfall trim
else:
    picks.extend(new)
```

Add a test where the band step yields exactly `shortfall` soft picks and the nearest step yields a sharp one, and confirm it fails without the fix.

### WR-02: Foreign reveal sends the stranger's game timestamp to the second; D-21 allows a date

**Classification:** WARNING
**File:** `app/repositories/train_repository.py:4845-4857` (`_foreign_game_info`), `app/schemas/train.py:65`, `app/routers/train.py:83`
**Issue:** D-21 lists the neutral facts as "time control, the mover's rating, date". `GameInfo.played_at` is a full `datetime`, filled from `game.played_at`, and the footer renders only the date (`formatDateWithYear`). The wire therefore carries more than the UI shows: an exact start time, the exact rating and the exact time control string. For a lichess game those three match essentially one row of the public monthly game dump, which gives the stranger's username by lookup. This is the one place where claim 1 ("never leaks the stranger's identity") does not fully hold.

Confidence: certain about the wire content. The severity is a judgement: the shape is inherited from blunder check's footer (Phase 249 D-09), and the position itself plus a date and rating can still be matched offline with more work, so truncating is hardening, not a cure. Flagged because this phase adds a new surface for it and D-21 says "date".
**Fix:** Send a date, not a timestamp, for a stranger's game. Either change `GameInfo.played_at` to a `date` (and `GameInfoRow` with it, which also tightens blunder check's footer) or truncate in `_foreign_game_info` and `blunder_check_repository.game_info_for`. Check `formatDateWithYear` with a date-only string so the shown day does not shift in negative-UTC time zones.

### WR-03: Score-screen copy tells an established user their games are not analyzed yet

**Classification:** WARNING
**File:** `frontend/src/lib/trainBotCopy.ts:974-996` (branch), `:774` (`has_games` clause), `:800-801` (`NO_OWN_PUZZLES_NOTE_LATER`), `:759-765` (reminder ask)
**Issue:** `scoreBubbleCopy` takes the `noOwnPuzzles` branch for every session with `own_puzzle_count === 0`, keyed only on `hasGames` and `isGuest`. D-13 names a second population for that same flag: the established user on an exhausted day, whose games are analyzed and whose own puzzles simply are not due. `TrainStartScreen.tsx:405-409` detects that user (`hasGames && first_session_done === true`) and shows "None of your own mistakes are due today." At the end of the same session the score bubble then reads "Those came from games of players at your level, so nothing comes back yet. Once your games are analyzed, your own mistakes take over." followed by "...so the habit is there when they arrive." Both statements are false for this user and contradict the start screen.

The clause wording predates the phase (the warm-up variant said the same), but the phase rewrote these lines and introduced the established-user distinction on the start screen only, so the two screens now disagree. Certain from the code; not run in a browser.
**Fix:** Pass the same "established" fact into `ScoreBubbleInput` (or reuse the D-13 predicate) and give that audience its own clause without the analysis promise and the "when they arrive" ask, falling through to the regular reminder ask. The wording is an owner decision (D-11 to D-13 are copy decisions), so this needs a line from the owner rather than a silent rewrite.

### WR-04: "Tactics puzzles don't count here" still describes the deleted lichess fillers

**Classification:** WARNING
**File:** `frontend/src/lib/trainLeaderboard.ts:72-73` (`ACCURACY_NOT_ENTERED_COPY`), `:245` (`viewerHint`)
**Issue:** The hint for a viewer who is on the Points board but not on Accuracy reads "You're not on this board yet: tactics puzzles don't count here." "Tactics puzzles" was the user-facing name for the lichess fillers this phase deletes (D-03). After the phase the puzzles that earn points but stay off Accuracy are similarly rated players' blunders (D-18), which no screen calls tactics puzzles, so a new user whose first solves this week are all foreign is told about a puzzle kind that no longer exists. The file is outside the phase diff; it is dead copy left behind by the deletion. Reach is limited to a viewer with points and zero own or herring solves in the week.
**Fix:** Reword to the new source, for example "You're not on this board yet: other players' blunders don't count here.", and update the two code comments at `:245` and `:351` plus the pinned strings in `trainLeaderboard.test.ts` and `TrainLeaderboardCard.test.tsx`. Wording is the owner's call.

## Info

### IN-01: The "owner-keyed sources" set is defined three times

**Classification:** INFO
**File:** `app/repositories/train_repository.py:2233`, `:3381`, `:3438`
**Issue:** `_OWNER_KEYED_SOURCES` is the named constant, but `_position_answer_key` and `_answer_keys_by_position` each spell out `(DrillSource.SR_ITEM, DrillSource.FOREIGN_BLUNDER)` again. A future owner-keyed source added to the constant would be dropped from the resume path but still graded keyless at compose time, which is the class of missed site claim 2 is about. The constant is also defined below `load_session_puzzles`, its first user.
**Fix:** Use `_OWNER_KEYED_SOURCES` at both sites and move the definition above its first use.

### IN-02: `_classify_legacy_filler_solve` takes an argument only to delete it

**Classification:** INFO
**File:** `app/repositories/train_repository.py:3876-3886`
**Issue:** The function accepts `solve`, runs `del solve`, and returns a constant. The parameter exists only to mirror its siblings. Its fix-site comment also overstates what it protects: it says a pre-deploy browser is not stranded on a 404, but migration `c4e6a8b0d375` deletes every untouched open session holding an unsolved filler, so a browser on the first puzzle of such a session does get the 404 on its first solve (deploy-minute only, self-heals on reload).
**Fix:** Drop the parameter and call `_classify_legacy_filler_solve()`, or inline the constant. Narrow the comment to "a session that already has a solve".

### IN-03: `ForeignCandidate` uses bare `str` for platform and time-control bucket

**Classification:** INFO
**File:** `app/services/train_foreign.py:71-72`, casts at `:98-99`
**Issue:** `platform: str` and `time_control_bucket: str | None` hold values from fixed sets, then are `cast` to `Platform` and `TimeControlBucket` at the single use site. Project rule: never a bare `str` for a fixed set of values. The statement already restricts `platform` to `ANALYTICS_INCLUDED_PLATFORMS`.
**Fix:** Type the fields as `AnalyticsPlatform` and `TimeControlBucket | None` and cast once in `_draw_foreign_candidates`, where the row leaves SQL.

### IN-04: Names and comments left over from the filler era

**Classification:** INFO
**File:** `app/repositories/train_leaderboard_repository.py:30-31`, `app/repositories/train_repository.py:4243-4244`, `frontend/src/types/train.ts:43`, `frontend/src/types/train.ts:564`
**Issue:** `SolveTotals.non_filler_points` / `non_filler_puzzles` (and their readers in `train_leaderboard.py`) now mean "accuracy-board solves", a positive list that also excludes a non-filler source. The `_mark_session_complete_if_done` docstring still says the flaw join is keyed on `(user_id, game_id, ply)` two paragraphs after the new text says it is keyed on the game owner. `types/train.ts:43` says `server_graded_moves` is "empty for sharp fillers", and `:564` says "non-filler solves (accuracy board)".
**Fix:** Rename the two fields to `accuracy_points` / `accuracy_puzzles` when the file is next touched, and correct the three comments.

### IN-05: Claim 3 is narrower in code than as stated: no-repeat is per position, and the solver's own game can arrive as the opponent's copy

**Classification:** INFO
**File:** `app/repositories/train_repository.py:2702-2717`, `app/services/train_foreign.py:124`, `app/services/train_pool.py:1119`
**Issue:** Two parts of "the draw never returns..." do not hold as worded.
(a) `_served_foreign_positions` and the pick exclude `(game_id, ply)`, not the game. A second blunder from a stranger's game already served to this user can be drawn in a later session. D-17 as written ("a foreign blunder is never served twice") is honored; "a game already served" is not what the code enforces.
(b) The only own-game exclusion is `foreign_sample.user_id != solver_id`. If the stranger played the game against the solver, the stranger's copy passes, and the solver gets their own game from the other side labelled "from a similarly rated player's game", with the opponent recognisable to them. Needs both players to be FlawChess users and a hit in a 0.1% sample, so it is rare. Blunder check's foreign pick has the same property.
**Fix:** None required for D-17. If (b) matters, exclude sampled games whose opponent username equals the solver's `lichess_username` / `chess_com_username` for the game's platform.

### IN-06: The nav badge still counts unservable rows until Train is opened

**Classification:** INFO
**File:** `app/repositories/train_repository.py:1925-1931` (`get_waiting_puzzle_count`), `:2029-2035` (`_open_unfinished_exists`)
**Issue:** Both read paths compute "remaining" as `puzzle_count - solved_count`, with none of the exclusions `_mark_session_complete_if_done` applies. A touched session whose remaining rows are unsolved legacy fillers (at deploy) or foreign puzzles from a deleted game keeps the badge lit and reports waiting puzzles until the next `POST /train/sessions`, where the 263-09 lazy completion closes it. The session is not pinned open, but the badge points at puzzles that do not exist. The same gap existed for orphaned own puzzles; foreign fillers add a second way to reach it.
**Fix:** Reuse the remaining-count predicate of `_mark_session_complete_if_done` (extract the SELECT into a shared read-only helper) in both functions.

### IN-07: The "level 2600" test isolation does not cover the nearest step

**Classification:** INFO
**File:** `tests/repositories/test_train_foreign.py:15-16`, `:178-180`; `tests/conftest.py:610-625`
**Issue:** `real_foreign_draw` sets both draw steps to TABLESAMPLE 100, and the tests rely on "pin the solver to 2600, where no other test seeds" to keep other rows out. That holds for the band step only. The nearest step has no distance cap, and it runs whenever the band step returns fewer than `shortfall + 2` picks, which is the case in `test_short_session_fills_with_foreign_blunder_and_grades_on_owner_key` (one seeded blunder, then `assert len(composed.puzzles) == 1`). Any committed non-guest game with a servable blunder left in the worker database, at any rating, would be drawn and fail that assertion. The suite is green serially and in parallel today, so nothing leaks now; this is a latent trap for the next test that commits such a game without cleanup.
**Fix:** Correct the docstrings to say the pin isolates the band step only, and in the tests that assert an exact count either patch `FOREIGN_FILLER_DRAW_STEPS` to the band step alone or assert on the seeded game's presence instead of the total.

---

_Reviewed: 2026-11-23T22:35:14Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
