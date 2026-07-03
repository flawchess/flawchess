---
created: 2026-07-03T00:00:00.000Z
title: Self-heal the 36 Path-C eval-hole games (user 218) via warm dedup cache
area: database
priority: medium
files:
  - app/services/eval_drain.py
  - scripts/
---

## Problem

36 prod games (all user 218), 642 mid-game plies, are stamped `full_evals_completed_at`
but have NULL evals — opening-weighted holes from the per-eval 5s wall-clock timeout firing
under batch saturation, then Path-C-stamped complete after `MAX_EVAL_ATTEMPTS = 3`. Because
they're stamped, the drain (`WHERE full_evals_completed_at IS NULL`) never revisits them.
Full diagnosis: `.planning/notes/eval-chart-opening-holes-root-cause.md`.

## Fix (self-heal — cheap, cache is now warm)

Re-open these games to the drain so it refills the opening holes via **dedup transplants**
(the `opening_position_eval` cache is now warm for these openings → no engine calls, no
timeouts). One targeted UPDATE on prod (via `bin/prod_db_tunnel.sh` + a maintenance script,
NOT a raw prod write without review):

```sql
-- Re-open only games that actually have non-terminal engine holes, scoped to the affected set.
-- MUST reset full_eval_attempts too, or the next attempt = 3 = MAX re-hits Path C immediately.
UPDATE games
SET full_evals_completed_at = NULL,
    full_pv_completed_at    = NULL,
    full_eval_attempts      = 0
WHERE id IN (<the 36 ids>);   -- or a prod-wide predicate: games with a non-terminal
                              -- game_positions hole AND full_evals_completed_at IS NOT NULL
```

## Watch-outs

- **Reset `full_eval_attempts = 0`** — the #1 trap. Stored value is 2; without the reset the
  re-drain's `new_attempts = 3 = MAX` re-stamps on any residual hole.
- Consider doing this **after** the durable fix (SEED-076) lands, or during a **low-load
  window**, so a fresh saturation doesn't re-time-out the same openings. With the cache warm,
  dedup should avoid the engine entirely — verify by checking the re-drain fills holes
  without new Sentry "residual holes" warnings.
- **Prod-wide sweep:** user 218 is the only holey set found today, but the same predicate
  (non-terminal position hole + `full_evals_completed_at IS NOT NULL`) may find historical
  Path-C games from earlier heavy batches. Scope the sweep, `log()` the count.
- Re-running the drain also re-runs flaw classification + oracle counts for these games
  (`_classify_and_fill_oracle`), which is correct/desired but worth noting for idempotency.
