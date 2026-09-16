---
quick_id: 260916-gj7
status: complete
date: 2026-09-16
commits:
  - dffeae65e perf: index opening_cache_audit.sample_game_id, drop dead ix_games_full_pv_pending
  - 1b60cadd3 docs: db-report Check C gates on sign flips and equal-vs-decisive only
---

# Summary: 260916-gj7 DB report follow-ups

All three items from `reports/db-stats/db-report-prod-2026-09-16.md` done inline.

1. **Partial index `ix_opening_cache_audit_sample_game_id`** (`WHERE sample_game_id IS NOT NULL`) added to the model `__table_args__` and migration `c3a9e1f70003`. Fixes the FK SET NULL seq scan on every user delete / re-import batch.
2. **`ix_games_full_pv_pending` dropped** in the same migration; downgrade recreates it. Never model-declared, so no model change.
3. **Check C in `.claude/skills/db-report/SKILL.md`**: `n_bad` now counts only `>150cp AND (sign flip OR least(|cache|,|med|) < 100)`; the raw `>150cp` count is reported as `n_gross` (secondary, never fails the check). References updated with the 2026-09-16 snapshot.

## Verification

- `alembic upgrade head` -> `downgrade -1` -> `upgrade head` round-trip on the dev DB: clean.
- `alembic check`: "No new upgrade operations detected" (model and migration agree).
- New Query 12 SQL executed on the dev DB: runs, returns `n_checked/n_bad/n_gross`.
- ruff format/check and ty on touched files: clean.

## Deploy note

The migration runs at container startup (non-concurrent). The new index covers ~a third of 2.5M rows; expected to build in seconds on prod. Effect is verifiable in the next db report: `seq_scan` on `opening_cache_audit` should stop growing.
