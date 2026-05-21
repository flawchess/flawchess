---
phase: 260521-d6o
plan: 01
subsystem: services/eval_drain
tags: [perf, refactor, cold-drain, tdd]
requires: []
provides: [single-walk-target-collection]
affects: [app/services/eval_drain.py]
tech-stack:
  added: []
  patterns: [single-walk-pgn-replay, spec-then-snapshot]
key-files:
  created: []
  modified:
    - app/services/eval_drain.py
    - tests/services/test_eval_drain.py
    - tests/services/test_import_service.py
decisions:
  - "Keep _collect_midgame_eval_targets / _collect_endgame_span_eval_targets signatures so import_service.py:_collect_covered_game_ids works unchanged."
  - "Production cold-drain path (_collect_eval_targets_from_db) calls _collect_eval_targets_per_game directly to avoid the wrappers' double walk."
  - "Split per-game helper into _collect_target_specs (pure, no parse) + _snapshot_boards (single mainline walk) + assembler — three small functions instead of one 100-line monolith."
metrics:
  duration: "~30 min"
  completed: 2026-05-21
---

# Quick 260521-d6o: Fix redundant PGN replays in the cold-drain eval lane

One-liner: replaced the cold drain's O(N) parse-and-walk per target ply with a single PGN parse + single mainline walk per game, snapshotting board state at every target ply at once.

## What changed

`app/services/eval_drain.py`:

- New `_TargetSpec` dataclass (frozen, slots) describing one entry ply that needs a Stockfish eval.
- New `_collect_target_specs(plies_list)` — pure, no PGN parsing. Derives the (ply, eval_kind, endgame_class) set up front: at most one midgame entry per game (D-79-08), plus one entry per contiguous-ply endgame-class island. Skips plies already covered by lichess `%eval` (T-78-17).
- New `_snapshot_boards(pgn_text, target_plies)` — parses the PGN once via `chess.pgn.read_game`, walks the mainline once, and stores `board.copy()` at each target ply. Early-break when all targets are filled. Returns `{}` for unparseable PGNs or empty target sets (no parse needed).
- New `_collect_eval_targets_per_game(g_id, pgn_text, plies_list)` — combines the two: derives specs, returns `[]` without parsing when no targets, otherwise snapshots boards and assembles `_EvalTarget` rows (midgame first, then endgame targets in ply-ascending order).
- `_collect_midgame_eval_targets` and `_collect_endgame_span_eval_targets` rewritten as thin filters over the per-game helper. Signatures unchanged.
- `_collect_eval_targets_from_db` (the production cold-drain path) now calls `_collect_eval_targets_per_game` directly per game, so each game is parsed at most once per drain tick (the two public wrappers would walk twice when called back-to-back; this is documented in their docstrings and is acceptable because the only outside caller, `_collect_covered_game_ids`, hits each game once).

Module docstring updated with a "Quick 260521-d6o follow-up" note.

## What stayed the same

- Public signatures of `_collect_midgame_eval_targets` and `_collect_endgame_span_eval_targets` are byte-identical to before.
- `import_service.py:_collect_covered_game_ids` works unchanged — `git diff --stat -- app/services/import_service.py` is empty.
- `app/services/zobrist.py` and `scripts/backfill_eval.py` are untouched.
- T-78-17 lichess %eval preservation semantics: plies with `eval_cp` or `eval_mate` already populated are never added to the target set.
- D-09 / R-02 cold-drain invariants: engine `(None, None)` still marks the game complete.

## Cleanup of dead code

Two helpers were removed because they had zero production callers:

- `_collect_eval_targets_for_games(rows)` — its docstring already admitted it was unused ("run_eval_drain loads targets directly from GamePosition DB rows for correctness").
- `_build_game_eval_data_from_pgn(game_id, pgn_text)` — explicitly a stub that returned `[(game_id, pgn_text, [])]`.

`_board_at_ply` was deleted from `app/services/eval_drain.py` (replaced by `_snapshot_boards`). The separate `_board_at_ply` in `scripts/backfill_eval.py` is a different symbol and was not touched (out of scope per plan).

## Test class added

`TestSingleWalkTargetCollection` in `tests/services/test_eval_drain.py` — 7 tests:

1. **Single-parse invariant**: 1 midgame + 2 endgame-class islands; assert `chess.pgn.read_game` is called at most once per collector via monkeypatched counter wrapper. (RED before refactor: endgame collector called read_game 2 times = 1 per island. GREEN after.)
2. **Covered game skips parse**: all candidate plies pre-covered → `read_game` invoked 0 times, both collectors return `[]`.
3. **Parse failure**: unparseable PGN → both collectors return `[]`, no exception.
4. **Mainline ends before target ply**: unreachable endgame target silently dropped, reachable midgame kept.
5. **Midgame covered, endgame uncovered**: midgame returns `[]`, endgame returns 1 target.
6. **Multiple islands of same class**: class=1 / class=2 / class=1 sequence yields 3 separate targets.
7. **Board snapshot is pre-push**: confirms 0-indexed, pre-push semantics — board at midgame entry ply=2 of "1. e4 e5 2. Nf3 *" has e4+e5 played, knight still on g1.

## Deviations from Plan

None — plan executed as written. One micro-decision: the per-game helper was split into three small functions (`_collect_target_specs`, `_snapshot_boards`, `_collect_eval_targets_per_game`) rather than one monolithic helper, per the plan's cohesion-check note (CLAUDE.md ≤ 100 logic LOC, ≤ 3 nesting depth). Each piece is independently readable.

## Pre-PR gate results

- `uv run ruff format app/ tests/` — 155 files left unchanged (after the focused reformat of eval_drain.py + test_eval_drain.py during the refactor).
- `uv run ruff check app/ tests/ --fix` — all checks passed.
- `uv run ty check app/ tests/` — all checks passed (zero errors).
- `uv run pytest -x` — **1612 passed, 6 skipped** (full backend suite green).
- Frontend gates — not exercised (this task does not touch `frontend/`).

## Plan verification commands

1. `grep -c "chess\.pgn\.read_game" app/services/eval_drain.py` → 2 matches; only one is a call site (line 174), the other is the new docstring note. **Pass** (1 production call site, down from N parses per game).
2. `git diff --stat -- app/services/zobrist.py app/services/import_service.py scripts/backfill_eval.py` → empty. **Pass** (scope guard holds).
3. `uv run pytest tests/services/test_import_service.py -x` → 4 passed. **Pass** (Stage 5c covered-game gate still works against the wrappers).
4. `uv run pytest -x` → 1612 passed. **Pass**.
5. CLAUDE.md pre-PR gates (ruff format / ruff check / ty check) — all clean. **Pass**.

## Commit

- `56277b78` perf(260521-d6o): single-walk PGN parse per game in cold-drain eval lane

## Self-Check: PASSED

- `app/services/eval_drain.py` — modified, contains `_collect_eval_targets_per_game`, `_snapshot_boards`, `_collect_target_specs`. `_board_at_ply`, `_collect_eval_targets_for_games`, `_build_game_eval_data_from_pgn` removed.
- `tests/services/test_eval_drain.py` — modified, `TestSingleWalkTargetCollection` class with 7 async test methods present.
- `tests/services/test_import_service.py` — modified (one comment update only).
- Commit `56277b78` exists on `worktree-agent-af99ccac9445789db`.
