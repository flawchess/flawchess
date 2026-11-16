---
phase: quick-261116-spc
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - app/services/maia_flaw_scoring.py
  - scripts/backfill_maia_flaws.py
  - app/models/game_flaw.py
  - docs/dev-tooling.md
  - tests/services/test_maia_flaw_scoring.py
  - tests/services/maia_fakes.py
  - tests/scripts/test_backfill_maia_flaws.py
autonomous: true
requirements:
  - SEED-261114-iuv-A1
  - SEED-261114-iuv-A3

estimate:
  tokens: 140000
  raw_tokens: 140000
  tasks: 3
  confidence: low

must_haves:
  truths:
    - "L-01: after a full-mode score (the post-commit hook in every lane, or `--mode full`), an opponent blunder whose mover is rated and whose played move is in the policy carries maia_reply_spread and maia_pre_spread (and maia_best_prob when the best move is known), computed at the OPPONENT's pinned Elo, with exactly one extra inference (the post-blunder board); its four line facts (line_mate_ply, played_line_material, best_line_material, best_line_mate_ply) stay NULL even when stored lines exist and even when stale values were on the row."
    - "L-01: user and opponent mistakes keep the three Maia columns and the four line facts NULL; user-blunder rows, the four stamps and the user-blunder counters (user_blunders, spreads_scored, scores_set, pre_scored) are identical with and without opponent blunders in the game."
    - "L-01/L-03: facepalm_expr(FACEPALM_DRILL_LAMBDA) evaluates to NULL in SQL for an opponent-blunder row that carries maia_played_prob and the three Maia columns, so the drill reader and the library reader without a side gate keep ignoring opponent rows."
    - "L-02: `scripts/backfill_maia_flaws.py --mode opponent` selects games by ROW (an opponent blunder with maia_played_prob IS NOT NULL AND maia_reply_spread IS NULL, opponent decided by is_opponent_expr), runs one pre-blunder plus one post-blunder inference per such blunder at the mover's pinned Elo, writes ONLY maia_reply_spread, maia_best_prob, maia_pre_spread on those rows, and never writes maia_played_prob, a user-side row or any stamp; a second run over a finished scope selects 0 games."
    - "L-02: the opponent mode shares the existing plumbing: hash-residue shards, the advisory-lock plus fingerprint write gate, --db dev|benchmark|prod, --dry-run, --user-id, --limit, --workers / --shard, --throttle-ms, exit 3 without Maia, --cutoff rejected, and `--status --mode opponent` prints its own counts including the residue (opponent_blunders_pending)."
    - "L-02: rows Maia cannot score (stalemating blunders: no_legal_reply; boards that cannot be rebuilt) stay selected by later runs by design, but a single run never loops: each shard selects one snapshot and iterates it once; the residue is documented in the script docstring."
    - "L-04: the scorer and script docstrings, the usage block, the docs/dev-tooling.md entry and the game_flaw.py comment describe the new opponent scope; no migration, no new stamp, no reader, repository or frontend change."
  artifacts:
    - path: app/services/maia_flaw_scoring.py
      provides: "ScoringMode 'opponent', OPPONENT_ROW_COLUMNS, _is_opponent_blunder, _is_opponent_target, _opponent_maia_values (shared by full and opponent modes), _opponent_values, _opponent_row, _scope_flaws, GameMaiaScore opponent counters, no-stamp write entry"
      contains: "OPPONENT_ROW_COLUMNS"
    - path: scripts/backfill_maia_flaws.py
      provides: "--mode opponent, _OPPONENT_PENDING_CLAUSE compiled from is_opponent_expr, opponent report counters, --status --mode opponent"
      contains: "_OPPONENT_PENDING_CLAUSE"
    - path: tests/services/maia_fakes.py
      provides: "assert_maia_lane_state with the opponent-blunder rule (Maia columns set, line facts NULL)"
      contains: "def assert_maia_lane_state"
    - path: tests/services/test_maia_flaw_scoring.py
      provides: "full-mode opponent tests, user-unchanged test, facepalm_expr NULL test, opponent-mode scorer and write tests"
    - path: tests/scripts/test_backfill_maia_flaws.py
      provides: "opponent-mode run, rerun, residue, selector, shard, CLI, Maia-missing and status tests"
  key_links:
    - from: "app/services/maia_flaw_scoring.py _derive_flaw_values"
      to: "_opponent_maia_values"
      via: "one early-return branch for an opponent blunder with base stats"
      pattern: "_opponent_maia_values"
    - from: "scripts/backfill_maia_flaws.py _STAMP_CLAUSE_BY_MODE['opponent'] and the opponent status query"
      to: "_OPPONENT_PENDING_CLAUSE"
      via: "one shared constant, so selector and status cannot drift"
      pattern: "_OPPONENT_PENDING_CLAUSE"
    - from: "app/services/maia_flaw_scoring.py _is_opponent_target"
      to: "scripts/backfill_maia_flaws.py _OPPONENT_PENDING_CLAUSE"
      via: "the same row predicate in Python (scope) and SQL (selection)"
      pattern: "_is_opponent_target"
    - from: "write_game_maia_scores"
      to: "_STAMP_COLUMN_BY_MODE['opponent']"
      via: "constant NULL stamp read, so require_unstamped never skips and _mark_stamps sets nothing"
      pattern: "\"opponent\": sa.null()"
---

<objective>
Score opponent blunders with the three Maia columns (maia_reply_spread, maia_pre_spread, maia_best_prob) in the live full-mode hook, and add a stamp-free `--mode opponent` backfill that fills them on existing opponent-blunder rows, without ever giving opponent rows line facts (SEED-261114-iuv Part A, steps 1 and 3).

Owner-locked scope from the planning context, cited below as L-01 .. L-04:
- L-01: full mode computes and writes the three columns for opponent blunders too (severity blunder, mover's pinned Elo); line facts stay user-only and NULL on opponent rows; mistakes stay unscored; user-side behaviour, the spread / line / pre modes, the stamps and the user-blunder report counters do not change.
- L-02: new backfill mode `opponent` (plus the scoring mode): one pre-blunder plus one post-blunder inference per opponent blunder, single pass, writes only the three columns, selection by row (maia_reply_spread IS NULL AND maia_played_prob IS NOT NULL, opponent mover), no stamp column, no migration, no stamp writes; resumable, sharded, same write gate, all existing CLI flags; guests handled like the existing modes (no filter).
- L-03: tests (listed per task).
- L-04: docs and comments.

Out of scope (do NOT implement): opponent line facts, side gates on the readers (app/repositories/blunder_check_repository.py, app/repositories/library_repository.py), library stats (seed Part B), any deploy, running the backfill against prod or benchmark, frontend changes.

Purpose: the hook change must land first because today a full re-score (e.g. the tier-4 blob submit hook) writes NULL Maia values on opponent rows, which would wipe anything the backfill fills. After both ship, the operator can backfill the 2.3M prod opponent blunders as a later, separate step.
Output: updated scorer, backfill script with `--mode opponent`, tests, docs.
</objective>

<execution_context>
@~/.claude/gsd-core/workflows/execute-plan.md
@~/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.planning/seeds/SEED-261114-iuv-facepalm-rate-library-stats.md
@CLAUDE.md
@app/services/maia_flaw_scoring.py
@scripts/backfill_maia_flaws.py
@app/services/maia_flaw_stats.py
@tests/services/maia_fakes.py

Read on demand (large; read only the line ranges named in the tasks):
- tests/services/test_maia_flaw_scoring.py (fixtures 100-312; tests to update 481-556, 677-704, 772-797, 1623-1646; pre-mode patterns 1164-1262; Scotch helpers 1891-1922)
- tests/scripts/test_backfill_maia_flaws.py (fixtures 69-230; `_select` 496-513; full-mode test 516-534; `_boards_by_ply` / `_facepalm_values` 556-583; `_set_game` / `_set_flaw` 834-850; pre-mode patterns 1170-1425)
- app/repositories/game_flaws_repository.py lines 175-203 (FACEPALM_COLUMNS, FACEPALM_PRE_COLUMNS) and 300-314 (bulk_update_flaw_maia_stats: one executemany, every row the SAME key set)
- app/repositories/query_utils.py lines 61-99 (mover_is_white_at_ply, is_opponent_expr)

Facts established while planning (verified in this worktree at 887b8b3af):
- Checkout root is the worktree on branch `quick/maia-opponent-blunders`. Never read or write the main checkout (another session runs Phase 256 there).
- Phase 256 (unmerged) edits maia_flaw_scoring.py lines 84-92 (the blunder_check_rules and line_material imports) and the body of `_row_score`; in tests/services/test_maia_flaw_scoring.py it edits the import block near line 37 and the tests at ~444, 886-1090, 2054-2140; in tests/scripts/test_backfill_maia_flaws.py the tests at ~607, 778, 876. Do not touch those regions. Put new tests in new sections at the END of each test file; add any stdlib import (e.g. `import dataclasses`) in the stdlib block at lines 10-17, and reach new scorer names through the already imported `maia_flaw_scoring` module instead of extending the `from app.services.maia_flaw_scoring import (...)` list.
- `is_opponent_expr(literal_column("ob.ply"), literal_column("g.user_color"))` compiled with the asyncpg dialect (`sqlalchemy.dialects.postgresql.asyncpg`) and `compile_kwargs={"literal_binds": True}` renders exactly `CASE WHEN (ob.ply % 2 = 0) THEN g.user_color = 'black' ELSE g.user_color = 'white' END` (single `%`, paramstyle numeric_dollar). The generic postgresql dialect targets a pyformat driver and doubles the `%`, which asyncpg would pass to Postgres verbatim as invalid SQL, so use the asyncpg dialect.
- The existing selector `_SELECT_SHARD_SQL` joins `users u` with no guest filter, so the opponent mode adds none (L-02 "follow the existing modes").
- At the _PGN ply-5 decision position (1. e4 e5 2. Nf3 Nc6 3. Bb5, Black to move, played a7a6) `g8f6` is legal: use it as a stored best line / best move fixture at ply 5.
- `reports/maia-flaws-backfill/` is tracked in git; the dev smoke must write its report to gitignored `temp/maia-opp-smoke/` via `--report-dir`.
- The worktree has no `.env`; `settings.DATABASE_URL_DEV` defaults to the dev compose DB on localhost:5432, and the Maia model is present at frontend/public/maia/maia3_simplified.onnx. Never touch `.env` files; never run bin/reset_db.sh.
- Test isolation: only create Game rows through the existing `make_game` fixtures (they delete in teardown; the global eval lottery must never see a leaked non-guest game).
</context>

<tasks>

<task type="tracer" tdd="true">
  <name>Task 1: Full-mode hook scores opponent blunders (three Maia columns, no line facts), end to end through the lanes and facepalm_expr</name>
  <files>app/services/maia_flaw_scoring.py, tests/services/test_maia_flaw_scoring.py, tests/services/maia_fakes.py, tests/scripts/test_backfill_maia_flaws.py</files>
  <precondition>The dev Postgres (compose project flawchess-dev) accepts connections on localhost:5432 (`pg_isready -h localhost -p 5432`).</precondition>
  <behavior>
    - User white, flaws at plies 2, 5, 8 of _PGN with a stored line at ply + 1 for plies 2 and 5 (`_mainline_line`; _PGN has no ply 9) and `g8f6` as the best pv at ply 5, stale `_STALE_FACEPALM` values seeded on ply 5: after `score_game_flaws_after_apply`, ply 5 has maia_reply_spread == reply_spread(fake policy at the post-blunder board), maia_pre_spread == pre_blunder_spread(fake policy at the pre-blunder board), maia_best_prob == that policy's g8f6 probability, maia_played_prob set, and line_mate_ply, played_line_material, best_line_material, best_line_mate_ply all None; all four stamps set.
    - The recorded full_policy calls for ply 5 are (pre5.fen(), pinned Black Elo) and (post5.fen(), pinned Black Elo): the opponent's own Elo, never the user's.
    - Opponent mistake (ply 5 severity 1) and a user mistake: all three Maia columns and all four line facts None, no post-blunder call for them.
    - User output unchanged: for the same loaded inputs with and without the ply-5 opponent flaw (`dataclasses.replace(inputs, flaws=...)`), the user rows (plies 2 and 8) are equal dicts and user_blunders, spreads_scored, scores_set, pre_scored are equal; with the opponent flaw opponent_blunders == 1, opponent_spreads_scored == 1, opponent_pre_scored == 1.
    - SQL: `select(GameFlaw.ply, facepalm_expr(FACEPALM_DRILL_LAMBDA))` for that game returns None for ply 5 although its three Maia columns and maia_played_prob are non-NULL; control: after setting played_line_material on ply 5 to `_STALE_FACEPALM["played_line_material"]` the same expression is non-NULL (the NULL comes from the line facts alone).
    - Existing expectations that encoded "opponent blunders get nothing" are updated to the new rule (line facts NULL, spread set), not deleted.
  </behavior>
  <action>
Per L-01, in app/services/maia_flaw_scoring.py, additive and tight (no drive-by refactor; do not touch lines 81-92 or `_row_score`, which Phase 256 edits):

1. Add `_is_opponent_blunder(inputs, flaw) -> bool` right after `_is_user_blunder`: severity is `_SEVERITY_INT["blunder"]` and `_is_user_blunder` is False. No new parity code: the mover side comes from the existing `_is_user_blunder` (which uses `mover_is_white_at_ply`).
2. Add `_opponent_maia_values(flaw, board, played_uci, elo, probs) -> tuple[FacepalmStats, MaiaPreStats, list[MaiaReason]]` right after `_pre_inputs`. It runs `_derive_reply_spread(board, played_uci, elo)` (the one post-blunder inference, `elo` is the mover's, i.e. the opponent's, pinned Elo) and `_pre_inputs(flaw, probs)` (no inference), and returns a FacepalmStats that is `null_facepalm_stats()` with only `maia_reply_spread` filled, the pre stats, and the concatenated reasons. Docstring: the four line facts stay None on purpose, because the drill reader (`load_blunder_flaws` and the unserved-blunder EXISTS in app/repositories/blunder_check_repository.py) and the library reader (`fetch_page_facepalm_scores` in app/repositories/library_repository.py) have no side gate and rely on opponent rows scoring NULL in facepalm_expr.
3. In `_derive_flaw_values`, insert one early-return branch immediately BEFORE the existing `if stats is None or not _is_user_blunder(inputs, flaw):` line: when `stats is not None` and `_is_opponent_blunder(inputs, flaw)`, call `_opponent_maia_values(flaw, board, played_uci, elo, probs)` and return `_FlawValues(stats, facepalm, pre, reasons + opponent_reasons)`. Leave every other line of the function as is; extend its docstring by one sentence (opponent blunders get the spread and pre inputs, never line facts). The no-rating and no-stats paths already yield NULLs for opponent rows via `_scope_facepalm`.
4. `GameMaiaScore`: add `opponent_blunders`, `opponent_spreads_scored`, `opponent_pre_scored` (int, default 0, with a comment) after `pre_scored`. In `score_game`, `spreads_scored` and `pre_scored` must now count only rows whose flaw is a user blunder (pair `scope_flaws` with `rows` using `zip(..., strict=True)` and filter with `_is_user_blunder`), because full-mode opponent rows now carry those keys and the report's user counters must not change. Compute the three opponent counters the same way with `_is_opponent_blunder`. Leave the `scores_set=` expression and its `_row_score` call unchanged (opponent rows have NULL line facts, so they never score). If the counting makes `score_game` hard to read, a small helper that counts non-None values of one key over (flaw, row) pairs matching a predicate is fine; keep nesting depth at or below 4.
5. Docstrings: module docstring step 2 now says one post-blunder inference per scorable blunder of EITHER side (opponent blunders at the opponent's pinned Elo, SEED-261114-iuv Part A), line facts only for user-side blunders, and why (the readers without a side gate). Also adjust the `_flaw_row` and `score_game` docstrings where they say non-user rows get NULL facepalm values. Commas, not em-dashes.

Per L-03, in tests/services/maia_fakes.py update `assert_maia_lane_state` (used by the drain and the remote / blob submit endpoint tests): a user blunder keeps today's rule; an opponent blunder must have the four line-fact columns None always, and when expect_stamped, the flaw has a legal reply and its maia_played_prob is not None, non-None maia_reply_spread and maia_pre_spread; every other flaw (mistakes, or expect_stamped False) keeps all facepalm and pre columns None. Keep the return value (number of user-side blunders with a spread) and update the docstring.

Per L-03, update these existing tests to the new rule (assert line facts None and spread set on the opponent row; keep names unless misleading, fix docstrings), all outside the Phase 256 hunks:
- tests/services/test_maia_flaw_scoring.py: `test_spread_scope_black_user_scores_only_own_blunders` (ply 4), `test_spread_scope_mistakes_and_opponent_stay_null` (the `opponent_ply` row), `_RECORDED_CALL_COUNT_WHITE_USER` (now 6: three base calls plus post-blunder calls for plies 2, 5, 8) and the docstring of `test_call_count_is_base_plus_scorable_user_blunders`, `test_game_without_user_blunders_stamped_without_extra_calls` (now 3 calls; ply 2 mistake all None, ply 5 spread set and line facts None), `test_facepalm_scope_non_user_rows_null` (ply 5: stale line facts cleared to None, spread set; ply 2 mistake all None), `test_one_full_policy_call_per_flaw` (now 2 calls: ply 5 base plus its post-blunder call).
- tests/scripts/test_backfill_maia_flaws.py: `test_full_mode_default_writes_base_and_facepalm_values_and_all_stamps` (ply 5: spread set, the four line facts None).

Write the new tests from the behavior block FIRST (red), in a new section at the end of tests/services/test_maia_flaw_scoring.py titled for opponent blunders (SEED-261114-iuv Part A): full-mode fill without line facts (with stored lines and stale values present), opponent and user mistakes stay NULL, user output unchanged, call Elo is the opponent's, facepalm_expr NULL plus the control. Use the existing helpers (`make_game`, `_score`, `_recording_policy`, `_pinned_elo`, `_replayed`, `_mainline_line`, `_inputs`, `_flaw_row_full`, `_STALE_FACEPALM`, `fake_full_policy`, `reply_spread`, `pre_blunder_spread`) and `maia_flaw_scoring.<name>` for anything new.
  </action>
  <verify>
    <automated>uv run --group maia-inference pytest tests/services/test_maia_flaw_scoring.py tests/scripts/test_backfill_maia_flaws.py -n auto -q && uv run --group maia-inference pytest tests/services/test_full_eval_drain.py tests/test_eval_worker_endpoints.py -n auto -q -k maia_flaw && uv run python scripts/check_function_size.py app/ --fail-over-depth 4</automated>
  </verify>
  <done>The hook writes the three Maia columns on opponent blunders at the opponent's Elo with one extra inference each, opponent rows never get line facts (proven with stored lines present and by facepalm_expr returning NULL in SQL), mistakes stay NULL, user rows and user counters are byte-for-byte unchanged, and every lane test (drain, atomic submit, blob submit) passes with the updated shared assertion.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Opponent scoring mode plus `--mode opponent` backfill run (row-selected, three columns only, no stamp)</name>
  <files>app/services/maia_flaw_scoring.py, scripts/backfill_maia_flaws.py, tests/services/test_maia_flaw_scoring.py, tests/scripts/test_backfill_maia_flaws.py</files>
  <behavior>
    - Scorer, user white, flaws at plies 1 (opponent blunder, no stored played prob), 2 (user blunder), 3 (opponent blunder with stored played prob AND stored reply spread), 5 (opponent blunder with stored played prob, spread NULL, best pv g8f6), 7 (opponent mistake with stored played prob): `score_game(inputs, None, "opponent")` returns rows only for ply 5, the row's key set is exactly {user_id, game_id, ply} plus OPPONENT_ROW_COLUMNS, the recorded calls are exactly [(pre5.fen(), pinned Black Elo), (post5.fen(), pinned Black Elo)], and the three values equal the full-mode row's values for ply 5; opponent counters are 1/1/1, user counters 0.
    - Scorer residue: _STALEMATE_PGN with user black (ply 18, White's stalemating Qe6, is the opponent's blunder) and a stored played prob: opponent mode writes maia_reply_spread None with reason no_legal_reply, maia_pre_spread non-None, exactly one inference.
    - Scorer: a game whose only blunders are user-side (with stored played probs) yields no rows and no inference in opponent mode.
    - Write: `write_game_maia_scores([opponent score], require_unstamped=True)` returns "stamped" (meaning written), sets none of the four stamps, leaves ply 5's maia_played_prob at the stored value; writing the same score again returns "stamped" again (no stamp gate).
    - Script run (base-stamped game, seed_base, user white, flaws 2, 5, 8, pv {5: "g8f6"}, `_SEEDED_FACEPALM` on ply 2): `run_shard(mode="opponent")` selects 1 game, spends exactly two inferences (pre5 then post5), fills ply 5's three columns, leaves every other column of every row (including ply 5's maia_played_prob 0.11) and all four stamps unchanged; report file `dev-opponent-<stamp>-shard0.json` has opponent_spreads_scored 1, opponent_pre_scored 1, opponent_spreads_null 0, opponent_pre_null 0, spreads_scored 0, pre_scored 0.
    - Script rerun: a second run selects 0 games and changes nothing.
    - Script residue: a seeded opponent blunder with a wrong stored fen (fen_override {5: "8/8/8/8/8/8/8/8"}) is selected, counted as fen_mismatch, keeps a NULL spread, the run returns normally, and a second run selects the game again.
    - Selector: selects exactly {white-user game with a seeded opponent blunder at ply 5, black-user game with seeded opponent blunders at plies 2 and 8}; not a game without played probs, not a game whose ply-5 spread is already set, not a white-user game whose ply 5 is a mistake (its user blunders 2 and 8 have played prob set and spread NULL, proving the parity and severity filters).
    - Shards: over 12 seeded games and 3 shards the opponent selections are disjoint and exhaustive.
    - CLI: `--mode opponent` parses, "opponent" is in BACKFILL_MODE_CHOICES, `--mode opponent --cutoff ...` exits; `_shard_process_entry(mode="opponent")` without Maia returns EXIT_MAIA_UNAVAILABLE without calling run_shard.
  </behavior>
  <action>
Per L-02, scorer side (app/services/maia_flaw_scoring.py), additive:

1. `ScoringMode` gains "opponent"; add a comment line to the mode comment block: opponent blunders only, the three Maia keys from one pre-blunder plus one post-blunder inference each, reading nothing else and stamping nothing (SEED-261114-iuv Part A).
2. Add `FACEPALM_PRE_COLUMNS` to the existing `from app.repositories.game_flaws_repository import (...)` list (lines 71-79, not the 81-92 block) and define `OPPONENT_ROW_COLUMNS: tuple[str, ...]` as maia_reply_spread followed by the FACEPALM_PRE_COLUMNS, next to `LINE_ROW_COLUMNS`, with a comment. Add it to `__all__`.
3. `_is_opponent_target(inputs, flaw) -> bool`: `_is_opponent_blunder` and `flaw.stored_played_prob is not None` and `flaw.stored_reply_spread is None`. Docstring: the Python twin of the script's `_OPPONENT_PENDING_CLAUSE` row predicate; the stored played probability is required because the hook only writes it when the board, the rating and the played move all check out.
4. `_opponent_values(inputs, flaw, board, played_uci) -> tuple[dict[str, float | None], list[MaiaReason]]`, modeled on `_pre_values`: `_mover_elo` None gives all three None plus "no_rating" (no inference); otherwise ONE `full_policy(board.fen(), elo)` at the pre-blunder board (None raises MaiaInferenceUnavailableError), the `compute_maia_flaw_stats` guard (stats None gives all three None plus its reasons, the hook's rule), then `_opponent_maia_values` from Task 1 for the post-blunder inference and the pre inputs, mapped to the OPPONENT_ROW_COLUMNS keys. The played probability computed here is discarded and never enters the row.
5. `_opponent_row(inputs, flaw, boards, game_reason, reasons)` shaped exactly like `_pre_row` (game_reason, else the `_flaw_board` guard, reasons counted); the row is the PK plus exactly the OPPONENT_ROW_COLUMNS keys (all None when unscorable), so one executemany compiles.
6. Scope: add `_scope_flaws(inputs, mode) -> list[FlawMaiaInput]` (full: every flaw; opponent: `_is_opponent_target`; spread / line / pre: `_is_user_blunder`). In `score_game` replace only the `scope_plies` conditional with the plies of `_scope_flaws(inputs, mode)`; in `_score_rows` add an opponent branch before the `_USER_BLUNDER_ROW_BUILDERS` lookup that builds `_opponent_row` for `_scope_flaws(inputs, "opponent")`. A game without targets replays nothing and runs no inference.
7. Write gate: add `"opponent": sa.null()` to `_STAMP_COLUMN_BY_MODE` with a comment (no stamp column, the row predicate is the checkpoint, so the in-lock read selects a constant NULL and a game is never already_stamped). `_mark_stamps` needs no new code path (no branch matches "opponent"); add a one-line comment saying opponent sets nothing. Add an opponent bullet to the `write_game_maia_scores` docstring (checks no stamp, sets none, outcome "stamped" means the rows were written). The advisory lock and the fingerprint re-read stay exactly as they are and apply to opponent writes too.
8. Docstrings: `score_game` gets one sentence for opponent mode; the module docstring gets a short opponent-mode paragraph like the pre-mode one.

Per L-02, script side (scripts/backfill_maia_flaws.py):

9. `BACKFILL_MODE_CHOICES` gains "opponent"; the `--mode` help text gets an opponent sentence.
10. Build `_OPPONENT_IS_MOVER_SQL: str` at module level by compiling `is_opponent_expr(literal_column("ob.ply"), literal_column("g.user_color"))` with the asyncpg dialect and literal binds (see the planning facts for why not the generic dialect), and `_OPPONENT_PENDING_CLAUSE: str` = an EXISTS over `game_flaws ob` with `ob.game_id = g.id`, `ob.severity = ` the `_SEVERITY_INT["blunder"]` value, `ob.maia_played_prob IS NOT NULL`, `ob.maia_reply_spread IS NULL` and the compiled mover expression. Comment: shared by the selector and the status counts, built only from constants (no CLI value), no stamp and no base-stamp requirement (selection is by row, L-02). Register it as `_STAMP_CLAUSE_BY_MODE["opponent"]` (that slot holds a row predicate here; say so in the comment). No guest filter, same as every existing mode.
11. Within one run there is no re-selection: `select_shard_game_ids` runs once per shard and `_run_batches` iterates that snapshot. Do not add any loop that re-queries; residue rows only come back in a later run (Task 3 documents this).
12. Report: add `opponent_spreads_scored`, `opponent_spreads_null`, `opponent_pre_scored`, `opponent_pre_null` to `ShardReport` (comment: opponent blunders in modes full and opponent). In `_tally_stamped`, for modes "full" and "opponent", add `score.opponent_spreads_scored` / `score.opponent_blunders - score.opponent_spreads_scored` and the pre pair; leave the existing user-counter mode tuples unchanged (opponent mode adds nothing to them). Add the four keys to `_combined_total_line` and `opponent_spreads_scored=` to `_progress_line`.
13. No change to `_start_maia_and_run` (opponent needs Maia through the existing non-line branch) or to the `--cutoff` rule (already rejects every non-line mode); the tests prove both.

Tests (L-03), red first, in new end-of-file sections: the scorer behaviors in tests/services/test_maia_flaw_scoring.py (use `_store_base_values` to seed stored played probs / spreads, `_recording_policy`, `_pinned_elo`, `_STALEMATE_PGN`, `_STALEMATE_PLY`, `maia_flaw_scoring.OPPONENT_ROW_COLUMNS`); the script behaviors in tests/scripts/test_backfill_maia_flaws.py (use `make_game(seed_base=True, base_stamped=..., user_color=..., severities=..., fen_override=..., pv=...)`, `_set_flaw`, `_run(..., mode="opponent")`, `_select(..., "opponent")`, `_boards_by_ply`, `_SEEDED_FACEPALM`, `_SHARD_GAMES`, `_SHARD_COUNT`; add a new helper that snapshots every game_flaws column except OPPONENT_ROW_COLUMNS rather than editing `_columns_except_pre`; mirror `test_pre_mode_needs_maia` and `test_cli_accepts_pre_mode_and_rejects_cutoff_with_it` for opponent). Compare selector output as a set.
  </action>
  <verify>
    <automated>uv run --group maia-inference pytest tests/services/test_maia_flaw_scoring.py tests/scripts/test_backfill_maia_flaws.py -n auto -q && uv run python scripts/check_function_size.py app/ --fail-over-depth 4 && uv run ruff check app/services/maia_flaw_scoring.py scripts/backfill_maia_flaws.py tests/services/test_maia_flaw_scoring.py tests/scripts/test_backfill_maia_flaws.py tests/services/maia_fakes.py</automated>
  </verify>
  <done>`--mode opponent` fills exactly the three columns on opponent-blunder rows selected by the row predicate, with one pre and one post inference each, never touches maia_played_prob, user rows or stamps, goes through the unchanged lock plus fingerprint gate, shards disjointly, reruns to zero selections, and keeps unscorable rows as a visible residue without looping inside a run.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: `--status --mode opponent`, docs and comments, full checks plus the dev-DB smoke</name>
  <files>scripts/backfill_maia_flaws.py, tests/scripts/test_backfill_maia_flaws.py, docs/dev-tooling.md, app/models/game_flaw.py</files>
  <precondition>The dev Postgres (compose project flawchess-dev) accepts connections on localhost:5432 (`pg_isready -h localhost -p 5432`).</precondition>
  <behavior>
    - Two seeded games (user white, flaws 2, 5, 8, seed_base, pv {5: "g8f6"}), opponent run with limit 1, then `fetch_status(maker, user, "opponent")` returns exactly, in this order: opponent_pending_games 1, opponent_blunders_total 2, opponent_blunders_with_played_prob 2, opponent_blunders_with_spread 1, opponent_blunders_with_pre_spread 1, opponent_blunders_with_best_prob 1, opponent_blunders_pending 1; `_print_status("dev", user, "opponent")` prints the same pairs space-joined as `key=value`.
  </behavior>
  <action>
Per L-02 status (scripts/backfill_maia_flaws.py): add an opponent branch to `fetch_status` that calls a new `_fetch_opponent_status(session, user_id)`. It runs `_stamp_counts` over a new `_OPPONENT_STATUS_QUERIES` dict with one key, `opponent_pending_games` (count of games matching `_OPPONENT_PENDING_CLAUSE`, the selector's own constant, with the `{u}` user slot), then six counts from a new `_opponent_blunder_count_stmt(user_id, *, extra_where=())` that mirrors `_user_blunder_count_stmt` but filters with `is_opponent_expr(GameFlaw.ply, Game.user_color)` (do not modify `_user_blunder_count_stmt`): opponent_blunders_total, opponent_blunders_with_played_prob, opponent_blunders_with_spread, opponent_blunders_with_pre_spread, opponent_blunders_with_best_prob, opponent_blunders_pending (played prob IS NOT NULL and reply spread IS NULL: what a finished run leaves, i.e. the residue). Update the `fetch_status` docstring. Write the status test first (red).

Per L-04 docs and comments:
- scripts/backfill_maia_flaws.py module docstring: add a `--mode opponent` entry to the Modes list stating: selection by row (games with an opponent blunder whose maia_played_prob is set and maia_reply_spread is NULL), ONE pre-blunder inference (maia_best_prob, maia_pre_spread) plus ONE post-blunder inference (maia_reply_spread) per such blunder at the mover's pinned Elo, writes only those three columns, never maia_played_prob, never line facts, never a stamp; no stamp column exists for it, so the row predicate is the checkpoint and a rerun resumes; the deploy ordering (run it only against a DB whose lanes already run the updated full-mode hook, otherwise a full re-score by the old hook NULLs the values again); the residue (stalemating blunders counted as no_legal_reply, plus rows whose board cannot be rebuilt, keep a NULL spread and are selected again by every later run; one run never loops because each shard iterates one snapshot; `--status --mode opponent` shows the residue as opponent_blunders_pending); guests handled like the other modes. Add two usage lines: a prod run with `PYTHONUNBUFFERED=1 uv run --group maia-inference python scripts/backfill_maia_flaws.py --db prod --mode opponent --workers 8 --throttle-ms 50` and `uv run python scripts/backfill_maia_flaws.py --db prod --status --mode opponent`. Also fix the docstring's opening paragraph if it still claims every mode stamps.
- docs/dev-tooling.md, the `scripts/backfill_maia_flaws.py` bullet only: the mode list becomes `full|spread|line|pre|opponent`, `full` writes the four stamps (the entry still says three), add one sentence for `pre` and one for `--mode opponent` (row-selected, the three Maia columns of opponent blunders, no stamp, run after the hook deploy, residue visible in `--status --mode opponent`).
- app/models/game_flaw.py: in the Phase 250 comment block above `maia_reply_spread`, replace the sentence that restricts these facts to user-side blunders under 250 D-06 with the current scope: maia_reply_spread (and the Phase 254 maia_best_prob / maia_pre_spread) are written for blunders of both players since SEED-261114-iuv Part A, while line_mate_ply and the three Phase 254 line-fact columns stay user-side only (opponent rows keep them NULL so facepalm_expr stays NULL there). Adjust the `maia_reply_spread` definition line so it says the blunderer's pinned Elo still (it is the mover's). Comment text only, no model change.

Then run the full check list from the worktree root and fix every finding: `uv run ruff format app/ tests/ scripts/` (apply), `uv run ruff check .`, `uv run --group maia-inference ty check app/ tests/ scripts/` (zero errors), `uv run python scripts/check_function_size.py app/ --fail-over-depth 4`, the test command below, and the dev-DB smoke: `uv run --group maia-inference python scripts/backfill_maia_flaws.py --db dev --mode opponent --workers 1 --limit 20 --dry-run --report-dir temp/maia-opp-smoke` (exit 0; a dry run writes nothing; 0 selected is acceptable on a dev DB without opponent played probs, record what happened) followed by `uv run python scripts/backfill_maia_flaws.py --db dev --status --mode opponent` (prints the seven keys). Never run the backfill without `--dry-run` against dev, and never against benchmark or prod.
  </action>
  <verify>
    <automated>uv run --group maia-inference pytest tests/services/test_maia_flaw_scoring.py tests/scripts/test_backfill_maia_flaws.py tests/services/test_facepalm_score.py tests/scripts/test_blunder_check_calibration.py tests/scripts/test_facepalm_features.py tests/scripts/test_miss_labels.py -n auto -q && uv run --group maia-inference pytest tests/services/test_full_eval_drain.py tests/test_eval_worker_endpoints.py -n auto -q -k maia_flaw && uv run ruff check . && uv run ruff format --check app/ tests/ scripts/ && uv run --group maia-inference ty check app/ tests/ scripts/ && uv run python scripts/check_function_size.py app/ --fail-over-depth 4 && ! grep -q "only (D-06)" app/models/game_flaw.py && grep -qF -- "--mode opponent" scripts/backfill_maia_flaws.py && grep -qF -- "--mode opponent" docs/dev-tooling.md && git diff --quiet 887b8b3af -- app/repositories/ app/services/facepalm_score.py app/routers/ alembic/ frontend/ && uv run --group maia-inference python scripts/backfill_maia_flaws.py --db dev --mode opponent --workers 1 --limit 20 --dry-run --report-dir temp/maia-opp-smoke && uv run python scripts/backfill_maia_flaws.py --db dev --status --mode opponent</automated>
  </verify>
  <done>`--status --mode opponent` prints the seven counts (pending games, totals, per-column fills, residue), all docs and comments describe the opponent scope accurately, ruff / format / ty / depth gates are clean, the readers, repositories, facepalm expression, migrations and frontend are untouched, and the dev smoke exits 0 in dry-run plus status.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| operator CLI -> DB | `backfill_maia_flaws.py` writes game_flaws rows on dev / benchmark / prod; CLI flags (`--user-id`, `--limit`, shard numbers) reach SQL |
| scorer writes -> drill and library readers | rows written here are read by `load_blunder_flaws`, the drill's unserved-blunder EXISTS and `fetch_page_facepalm_scores`, which have no side gate |
| concurrent lanes -> same rows | the live hook (drain, atomic submit, tier-4 blob submit) and the backfill can write the same game concurrently |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-spc-01 | Tampering | opponent rows leaking into drill selection and library facepalm chips | high | mitigate | `_opponent_maia_values` fills only maia_reply_spread and the pre keys; the four line facts stay None in full mode and are absent from opponent-mode rows (key-set test); Task 1 asserts NULL line facts with stored lines and stale values present and that facepalm_expr(FACEPALM_DRILL_LAMBDA) is NULL in SQL on the opponent row, with a control proving the NULL comes from the line facts; `git diff --quiet` gate on app/repositories/ and app/services/facepalm_score.py |
| T-spc-02 | Tampering | opponent mode overwriting maia_played_prob, user-side rows or stamps | high | mitigate | rows carry the PK plus exactly OPPONENT_ROW_COLUMNS; scope limited by `_is_opponent_target`; `_STAMP_COLUMN_BY_MODE["opponent"]` is a constant NULL and `_mark_stamps` sets nothing; the script test snapshots every other column of every row and all four stamps before and after a run |
| T-spc-03 | Tampering | stale write over a concurrently reshaped game | medium | mitigate | opponent writes go through the unchanged `write_game_maia_scores` path: ascending advisory locks plus the in-lock fingerprint re-read (severity, fen, both lines, best move); a mismatch writes nothing |
| T-spc-04 | Tampering | old hook wiping backfilled opponent values | medium | mitigate | the full-mode hook change ships in the same change and first in task order; the script docstring and docs/dev-tooling.md require the hook deploy before any prod or benchmark run |
| T-spc-05 | Tampering (SQL injection) | `_OPPONENT_PENDING_CLAUSE` text SQL | low | mitigate | built only from constants (`_SEVERITY_INT`, the compiled `is_opponent_expr` with literal binds of `0`, `'black'`, `'white'`); user_id, limit, shard and num_shards stay bound parameters |
| T-spc-06 | Denial of service | residue rows re-selected forever / prod load | low | mitigate | one snapshot per shard iterated once (no in-run re-query); residue visible as opponent_blunders_pending in `--status`; existing `--throttle-ms`, one-connection pool per shard; this plan runs nothing against benchmark or prod |
| T-spc-SC | Tampering | npm/pip/cargo installs | low | accept | no package is installed or added; uv uses the existing lockfile groups |
</threat_model>

<verification>
- `uv run --group maia-inference pytest tests/services/test_maia_flaw_scoring.py tests/scripts/test_backfill_maia_flaws.py -n auto` passes, plus the `-k maia_flaw` lane tests in tests/services/test_full_eval_drain.py and tests/test_eval_worker_endpoints.py.
- `uv run ruff check .`, `uv run ruff format --check app/ tests/ scripts/`, `uv run --group maia-inference ty check app/ tests/ scripts/` (zero errors) and `uv run python scripts/check_function_size.py app/ --fail-over-depth 4` are clean.
- `git diff --quiet 887b8b3af -- app/repositories/ app/services/facepalm_score.py app/routers/ alembic/ frontend/` (no reader, repository, expression, migration or frontend change).
- `git diff 887b8b3af -- app/services/maia_flaw_scoring.py` shows no change to lines 81-92 or to the body of `_row_score` (Phase 256 merge surface).
- Dev smoke: the opponent dry run exits 0 with its report under temp/maia-opp-smoke/, and `--status --mode opponent` prints the seven keys.
</verification>

<success_criteria>
- New games scored by any lane get the three Maia columns on opponent blunders (opponent's Elo), never line facts; user-side output, stamps and user counters are unchanged.
- `--mode opponent` backfills the three columns on existing opponent-blunder rows by row predicate, with no stamp and no migration, resumable, sharded, behind the same write gate, and with a documented, visible residue.
- facepalm_expr stays NULL on opponent rows, so the drill and the library keep ignoring opponents without any reader change.
- Docs (script docstring and usage, docs/dev-tooling.md, scorer docstring, game_flaw.py comment) match the behaviour.
</success_criteria>

<output>
Create `.planning/quick/261116-spc-maia-columns-for-opponent-blunders-full-/261116-spc-SUMMARY.md` when done. Include: the per-task commits; the dev smoke output (selected / scored counts and the status line); the operator commands for a later benchmark and prod run (status first, then `--mode opponent` with workers and throttle, deploy-first ordering); the residue explanation; and any deviation from this plan with its reason.
</output>
