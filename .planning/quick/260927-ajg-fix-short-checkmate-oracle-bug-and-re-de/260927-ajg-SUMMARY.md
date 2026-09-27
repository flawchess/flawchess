---
quick_id: 260927-ajg
status: complete
---

# Quick 260927-ajg: short checkmate oracle bug — summary

## Root cause

`_compute_eval_coverage` excluded the terminal row from the denominator (260615-rb1) but not the
row before a checkmating last move. That row holds the mated position's eval, which the engine
cannot score, so it is always null. A 7-ply mate scored 6/7 = 0.857 < `EVAL_COVERAGE_MIN`,
`count_game_severities` / `classify_game_flaws` returned `GameNotAnalyzed`, and the drain
stamped `full_evals_completed_at` while leaving oracle columns, accuracy and `game_flaws` empty.
Only 4-9 ply mates were affected (10+ plies lose the same row but still clear 0.90). Found by the
2026-09-27 prod sanity check (Check E).

## Changes

- `app/services/flaws_service.py`: when the last move's SAN ends with `#` and the last movable
  row has no eval, drop that row from the coverage denominator. Numerator unchanged (the row is
  null by condition).
- `tests/services/test_flaws_service.py`: Scholar's mate regression (coverage 1.0, severities and
  flaws no longer `GameNotAnalyzed`), sparse-mate stays below the gate, non-mate missing last eval
  is not excused. Reverting the fix fails both regression tests.
- `scripts/backfill_flaws.py --oracle-gap`: re-derives games with full evals but NULL oracle
  columns through the drain's `_classify_and_fill_oracle` (flaws + oracle + accuracy, blob
  preserving, clears `blobs_completed_at` so tier-4 re-picks the new flaws), one game per
  transaction under the per-game advisory lock. `tests/test_backfill_flaws.py` covers dry-run,
  fill, and the still-sparse skip; it also fails with the fix reverted.
- `.claude/skills/db-report/SKILL.md`: Query 11b oracle-gap probe, since Check B's `count(*)`
  denominator hid this class of gap.

Deviation: the first full-suite run failed `test_lease_lifo` because the new DB test seeded games
with `evals_completed_at` NULL, which the global LIFO entry-lane lease test running in parallel
claimed. Seeded games now carry every completion stamp a drained game has.

## Prod re-derive

- Dry run: 1,070 candidates, would fill 1,016, skipped 54 (non-standard-start games with no
  evals), 0 errors.
- Real run (2026-09-27 06:37-07:39 UTC, from the worktree code over the tunnel): filled 1,016,
  skipped 54, 0 errors.
- Verification (db-report Query 11b afterwards): the oracle gap is down from 1,070 to 54, all of
  them non-standard-start chess.com games with no evals (expected residue). A mid-run spot check
  showed filled games carrying oracle counts, accuracy, flaw rows (~1.1 blunders per game, the
  mated side's losing move) and a cleared `blobs_completed_at` so tier-4 adds tactic tags.

Pre-merge gate: ruff format/check, ty (app/tests/scripts + analysis), nesting gate, full backend
suite (4751 passed), frontend lint/build/test (4408 passed)/knip all green.

## Follow-up

The prod drain runs the unfixed code until the next deploy, so short mates completed before then
land in the gap again. After the next deploy, rerun
`uv run python scripts/backfill_flaws.py --db prod --oracle-gap`.
