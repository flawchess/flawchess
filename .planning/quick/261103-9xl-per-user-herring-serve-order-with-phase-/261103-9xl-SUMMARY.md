---
quick_id: 261103-9xl
status: complete
commit: 340ff459f
---

# Summary: per-user herring serve order with phase round-robin

## Done

- `herring_stmt` (`app/services/train_pool.py`) now orders by `preferred DESC`, then
  `row_number() OVER (PARTITION BY preferred, phase ORDER BY md5(user_id:id), id)`, then the
  per-user hash, then `id`. Total and stable per user, different across users, phases
  interleaved. The phase order within a round is hash-driven, not `phase ASC`, so no phase
  starves with only 2 herring slots per session.
- Docstring rewritten for the new order; the false claim that `WINNABILITY_FLOOR_ES` is
  enforced at generation time was corrected.
- `ix_herring_pool_recency` no longer backs any query. It was kept (no migration) and is noted
  on the model as safe to drop.
- Tests: replaced the id-ASC tie test with per-user stability; added different-across-users,
  phase round-robin, and preferred-tier-outranks-rotation tests. Mutation check: reverting
  `herring_stmt` to HEAD fails `differs_across_users` and `round_robins_phases`.

## Verification

- Prod read-only check with an equivalent query: users 1, 28 and 500 get different first-9
  sequences, each cycling through all three phases.
- `ruff`, `ty`, nesting gate clean; 674 Train/herring/drill tests pass.

## Notes / follow-ups

- Users who already saw the old global head keep their served set (exclusion is by
  `herring_pool_id`); from now on they draw from their own per-user order.
- Out of scope, seed candidates: the opening bucket is mostly ply 12–16 (book territory),
  and there is no winnability cap at generation (310 rows have mover ES > 0.80).
