---
phase: quick-260614-tgs
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - app/services/eval_drain.py
  - scripts/resweep_holed_games.py
  - tests/services/test_full_eval_drain.py
autonomous: true
requirements: [SEED-049]
must_haves:
  truths:
    - "A checkmate-ending engine game stamps full_evals_completed_at on attempt 1 with failed_ply_count == 0 (no retries, no cap-path Sentry event)."
    - "A game with a genuine mid-game NULL post-move eval still counts as a hole and still retries (Path B unchanged)."
    - "resweep_holed_games does not re-arm games whose only hole is the game-ending move ply."
  artifacts:
    - path: app/services/eval_drain.py
      provides: "Game-ending ply excluded from failed_ply_count (live drain) and from the resweep predicate."
    - path: scripts/resweep_holed_games.py
      provides: "CLI tool unchanged in interface; predicate fix lives in eval_drain.resweep_holed_games which it calls."
    - path: tests/services/test_full_eval_drain.py
      provides: "Three new regression tests per the seed."
  key_links:
    - from: "_collect_full_ply_targets"
      to: "_apply_full_eval_results"
      via: "is_game_over() knowledge threaded onto the last real target"
      pattern: "ends_game"
---

<objective>
Implement SEED-049 Option (a): a ply whose move ends the game (resulting position
`is_game_over()`) is NOT an eval hole. Its NULL post-move eval is legitimate and
expected, exactly like the already-excluded terminal ply.

Purpose: ~99.9% of prod "holes" are this structural game-ending-move artifact, not
transient Stockfish timeouts. Today the SEED-045 bounded retry fires (and the cap path
stamps complete-with-holes + emits a Sentry warning) on ~1,379 positions it can never
fill. After this fix the retry mechanism fires only on the ~2 genuinely transient holes
it was designed for, and checkmate-ending games stamp clean on attempt 1 (Path A).

Output: corrected `failed_ply_count` in the live drain, a corrected resweep predicate,
and three regression tests. NO migration, NO lichess backfill, NO `eval_mate` writes.
</objective>

<execution_context>
@$HOME/.claude/gsd-core/workflows/execute-plan.md
@$HOME/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/seeds/SEED-049-game-ending-ply-false-hole.md
@./CLAUDE.md
@app/services/eval_drain.py
@scripts/resweep_holed_games.py
@tests/services/test_full_eval_drain.py

# Background facts already verified (do not re-litigate):
# - Post-move storage (SEED-044): row k holds the eval of the position AFTER move k.
#   For the game-ending move (row at ply = ply_count - 1), the after-position is the
#   game-over terminal. _collect_full_ply_targets already SKIPS appending a terminal
#   eval-donor when `board.is_game_over()` (eval_drain.py ~line 217). So pos_eval has
#   no entry for ply_count, and _post_move_eval(pos_eval, ply_count - 1) returns
#   (None, None) — the false hole the live drain currently counts.
# - The --db {dev,benchmark,prod} flag on scripts/resweep_holed_games.py and the
#   optional session_maker param on resweep_holed_games are ALREADY committed
#   (ce3f6456). Working tree is clean. Do NOT add them.
# - flaws_service.py:172 (`eval_mate > 0`) is the reason eval_mate = 0 is unrepresentable;
#   it rules out Option (b). Read-only context — do NOT change it.
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Exclude the game-ending ply from failed_ply_count (live drain)</name>
  <files>app/services/eval_drain.py</files>
  <behavior>
    - A checkmate-ending engine game (e.g. "1. e4 e5 2. Qh5 Nc6 3. Bc4 Nf6?? 4. Qxf7# 1-0")
      produces failed_ply_count == 0 from _apply_full_eval_results even though the
      last real row's post-move eval is (None, None), because that row's move ended the game.
    - A genuine mid-game NULL (engine hole at a non-game-ending ply's after-position)
      still increments failed_ply_count (Path B / retry behavior preserved).
  </behavior>
  <action>
    Thread the game-over knowledge that _collect_full_ply_targets already computes into
    the failed_ply_count counter in _apply_full_eval_results.

    1. Add a new boolean field `ends_game: bool = False` to the `_FullPlyEvalTarget`
       dataclass, documented as: "SEED-049 — True for the single real (non-terminal) row
       whose move ENDS the game (resulting position is_game_over()). Under post-move storage
       its after-eval is the game-over terminal, which is deliberately unevaluable and never
       gets a donor, so its NULL post-move eval is legitimate — never counted as a hole."

    2. In _collect_full_ply_targets, after the mainline loop, when `ply_count > 0 AND
       board.is_game_over()` is True (the branch that currently SKIPS the terminal donor),
       set `ends_game=True` on the LAST appended real target whose `ply == ply_count - 1`
       (the game-ending move's row). Only set it if that row actually has a DB target
       (it is in ply_meta — it always will for a complete game, but guard defensively:
       find it by scanning targets for the one with `ply == ply_count - 1`, or track the
       last non-terminal target as you build the list). Do NOT set ends_game when the game
       ended by resignation/timeout (board not game-over) — that final move IS assessable
       and a genuine hole there should still count.

    3. In _apply_full_eval_results, in the engine-game hole branch (the
       `if eval_cp is None and eval_mate is None:` block at ~line 437), do NOT increment
       failed_ply_count when `target.ends_game` is True. The row is still written normally
       (eval stays NULL, best_move still written if available) — only the COUNT changes,
       so the game stamps complete on attempt 1 (Path A) instead of churning through the
       retry/cap path. Add a comment citing SEED-049 explaining the game-ending move's
       after-position is the unevaluable game-over terminal.

    Keep ty-clean (the new field has a default so all existing construction sites compile).
    No magic numbers. Do not touch the is_lichess_eval_game branch or the terminal-donor
    skip logic itself.
  </action>
  <verify>
    <automated>uv run pytest -n auto tests/services/test_full_eval_drain.py -x</automated>
  </verify>
  <done>
    _FullPlyEvalTarget has an ends_game field; _collect_full_ply_targets sets it on the
    game-ending move's row only when the final position is game-over; _apply_full_eval_results
    does not count that ply as a hole. Existing full-drain tests still pass.
  </done>
</task>

<task type="auto">
  <name>Task 2: Exclude the game-ending move ply from the resweep predicate</name>
  <files>app/services/eval_drain.py</files>
  <action>
    Fix the resweep_holed_games predicate (~line 1620-1640) so it does not re-arm games
    whose ONLY hole is the game-ending move ply.

    Current predicate flags a game when it has a row with eval_cp IS NULL AND eval_mate IS
    NULL AND ply < MAX(ply). Under post-move storage the game-ending move lands at
    ply = MAX(ply) - 1 in games with no separate terminal row (the common case), so the
    existing `ply < MAX(ply)` exclusion does NOT cover it. The 2 genuine mid-game holes
    observed in prod are at ply < MAX(ply) - 1, so excluding the game-ending move ply is
    precise and safe.

    Use the move_san checkmate proxy combined with a positional guard. Add to the WHERE
    clause an exclusion so a NULL row is NOT treated as a hole when it is the game-ending
    move ply, identified by EITHER:
      (a) `gp_table.c.move_san LIKE '%#%'` (the move delivered checkmate — 1,333/1,379 of
          observed false holes), OR
      (b) `gp_table.c.ply >= max_ply_per_game.c.max_ply - 1` (the last move ply — covers
          stalemate / insufficient-material endings that do not annotate '#', plus the
          checkmate case; the genuine mid-game holes at ply < max_ply - 1 are unaffected).

    Implement the exclusion as `gp_table.c.ply < max_ply_per_game.c.max_ply - 1` so only
    holes strictly before the game-ending move ply count. This is the SQL proxy; it does
    NOT board-replay. Add a `# SEED-049 - 1` constant or, better, define a module-level
    `_GAME_ENDING_PLY_OFFSET: int = 1` and use it in the predicate so the `- 1` is not a
    bare magic number (CLAUDE.md). Update the existing docstring "A hole is a non-terminal,
    non-mate ply..." block to state the new definition (hole = eval NULL AND eval_mate NULL
    AND ply < max_ply - 1) and to explain the SEED-049 game-ending-move exclusion.

    TRADEOFF to record in the SUMMARY (decided): the `ply < max_ply - 1` positional guard
    is exact for the game-ending move under post-move storage and needs no board replay or
    move_san LIKE check, because every game's last move sits at max_ply - 1 regardless of
    how it ended (checkmate, stalemate, insufficient material, resignation, timeout). The
    move_san '%#%' proxy is therefore redundant for correctness; the positional guard alone
    is sufficient and avoids a full-board replay. Resignation/timeout endings whose last
    move has a real eval are unaffected (they are not NULL holes). Keep the implementation
    to the positional guard only; do NOT add a board-replay path.
  </action>
  <verify>
    <automated>uv run pytest -n auto tests/services/test_full_eval_drain.py -k resweep -x</automated>
  </verify>
  <done>
    resweep_holed_games predicate excludes the game-ending move ply (ply >= max_ply - 1)
    via a named offset constant; docstring updated; scripts/resweep_holed_games.py needs
    no change (it calls this function).
  </done>
</task>

<task type="auto">
  <name>Task 3: Regression tests for the three seed scenarios</name>
  <files>tests/services/test_full_eval_drain.py</files>
  <action>
    Add three tests mirroring the existing patterns in this file (reuse _CHECKMATE_PGN,
    _TWO_MOVE_PGN, the full_drain_session_maker / full_drain_test_user fixtures, and the
    engine-result patching style used by test_no_holes_stamps_complete_first_tick and
    test_transient_hole_withholds_stamp_increments_attempts).

    1. test_checkmate_game_stamps_complete_first_tick: a checkmate-ending game
       (_CHECKMATE_PGN, the final move Qxf7# ends the game) drains and stamps
       full_evals_completed_at on attempt 1 with failed_ply_count == 0 and NO cap-path
       Sentry event — even though the game-ending move's row has a NULL post-move eval.
       Assert the marker is set, full_eval_attempts is unchanged (0), and the
       game-ending row's eval stays NULL (the legitimate empty game-ending ply).

    2. test_midgame_null_still_retries: a game with a genuine mid-game NULL post-move eval
       at a non-game-ending ply still counts as a hole and still goes to Path B (marker NOT
       stamped, full_eval_attempts incremented). This can reuse / adapt the existing
       _TWO_MOVE_PGN transient-hole test but make the hole a NON-game-ending ply so it is
       NOT excluded by the SEED-049 fix. (_TWO_MOVE_PGN "1. e4 e5 *" is NOT game-over at
       its end, so its last move IS assessable and a NULL there is a real hole — verify the
       existing transient-hole test still expresses this; if it already does, add a short
       assertion/comment tying it to SEED-049 rather than duplicating.)

    3. test_resweep_skips_game_ending_ply: seed an engine game whose ONLY NULL-eval hole is
       at the game-ending move ply (ply = max_ply - 1) and full_evals_completed_at set;
       assert resweep_holed_games(dry_run=True, session_maker=...) does NOT count it. Also
       seed a control game with a genuine mid-game hole (ply < max_ply - 1) and assert it
       IS counted, proving the predicate still re-arms real holes.

    Follow the module's existing fixture wiring and avoid bin/reset_db.sh (per CLAUDE.md /
    project memory — tests run against the per-run test DB). Keep tests parallel-safe (use
    the module's dedicated user-id range / unique game ids).
  </action>
  <verify>
    <automated>uv run pytest -n auto tests/services/test_full_eval_drain.py -x</automated>
  </verify>
  <done>
    Three tests added and passing: checkmate stamps complete on attempt 1 with
    failed_ply_count == 0; a genuine mid-game NULL still retries; resweep skips the
    game-ending ply but still flags a real mid-game hole.
  </done>
</task>

</tasks>

<verification>
Full backend gate (CLAUDE.md Pre-PR checklist, backend-only change):

```bash
uv run ruff format app/ tests/ scripts/
uv run ruff check app/ tests/ scripts/ --fix
uv run ty check app/ tests/
uv run pytest -n auto -x
```

All four must be clean before merge. No frontend changes, so the frontend gate is N/A.
</verification>

<success_criteria>
- Checkmate-ending engine games stamp full_evals_completed_at on attempt 1 with
  failed_ply_count == 0 (Path A) — no retries, no cap-path Sentry warning, no 3x churn.
- A genuine mid-game NULL (ply < max_ply - 1) still counts as a hole and still retries.
- resweep_holed_games no longer re-arms games whose only hole is the game-ending move ply,
  but still re-arms games with real mid-game holes.
- No migration, no lichess backfill, no eval_mate writes.
- ty clean, ruff clean, full backend suite green.
</success_criteria>

<output>
Create `.planning/quick/260614-tgs-seed-049-exclude-the-game-ending-ply-fro/260614-tgs-SUMMARY.md` when done.
Record the resweep predicate tradeoff decision (positional guard `ply < max_ply - 1` is
exact and sufficient; move_san '%#%' proxy redundant; no board replay).
</output>
