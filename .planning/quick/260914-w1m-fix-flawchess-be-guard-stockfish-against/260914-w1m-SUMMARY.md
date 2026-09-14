---
quick_id: 260914-w1m
status: complete
date: 2026-09-14
commit: b96da37a7
---

# Summary: guard Stockfish against impossible custom-position boards (FLAWCHESS-BE)

## What changed

- `app/services/engine.py` `_acquire_and_analyse`: returns `None` for `Board.is_valid() == False`
  before taking a worker slot. Defence in depth for every caller.
- `app/services/eval_apply.py` `_collect_full_ply_targets`: returns `[]` when the PGN root is
  invalid. Single choke point for the local full drain, tier-4b bestmove lane, remote atomic
  lease/submit and `scripts/opening_cache_repair.py`. With no targets the drain stamps the game
  complete through the no-holes path, so it leaves the eval lottery for good.
- Tests: `test_invalid_board_never_reaches_the_engine` (mocked protocol never called, slot not
  consumed), `test_collect_invalid_root_returns_no_targets`, and a contrast test that a legal
  "from position" root still yields targets. Reverting the two guards makes the first two fail.
- CHANGELOG bullet under Unreleased / Fixed.

## Not changed, and why

- Flaw-blob lane (`_build_flaw_blob_lease_positions`): all 47 flaws on the 12 affected prod
  games already carry blobs, and future invalid-root games get no evals, hence no flaws, so the
  lane never sees them.
- Remote lease 204 for an invalid-root game leaves it pending briefly; the local drain claims
  and stamps it on its next pick, so there is no lasting churn.
- Existing garbage evals/flaws on the 12 prod games were left in place (stamped complete,
  scoped to three users). A cleanup would be a separate decision.

## Verification

- `uv run pytest tests/services/test_engine_nodes.py tests/services/test_full_eval_drain.py -k "invalid_board_never or invalid_root or valid_custom_root"` — 3 passed; 2 fail with the guards reverted.
- ty, ruff, function-size gate: clean. Full backend suite and frontend lint/tests: run as the pre-merge gate before deploy.
