---
created: 2026-05-31T00:00:00.000Z
title: Phase 99 prod backfill — rate-percentile metrics (conversion/parity/recovery)
area: database
files:
  - scripts/backfill_user_percentiles.py
  - alembic/versions/20260530_extend_benchmark_metric_for_rate_percentiles.py
  - alembic/versions/20260530_220134_52c928794fe7_add_rate_family_names_to_benchmark_metric.py
---

## Problem

Phase 99 added 12 new rate-percentile metrics (`conversion_rate`/`parity_rate`/`recovery_rate` × 4 TCs) plus 3 bare family-name ENUM values. The cohort CDF artifact (`global_percentile_cdf.py`) was regenerated and the **dev** DB was backfilled, but the **prod** backfill was explicitly deferred to deploy time per the D-11 human-action checkpoint (signed off 2026-05-31). Without the prod backfill, the new rate chips will suppress (no `rate_percentile`) for all prod users even after the code ships.

## Solution

Run the per-user prod backfill **after this milestone (v1.21) is deployed to production**. The two ENUM migrations (`3981239fd391` extend_benchmark_metric_for_rate_percentiles, `52c928794fe7` add_rate_family_names) apply automatically on backend container startup at deploy, so only the per-user rows remain:

```bash
bin/prod_db_tunnel.sh                                      # open tunnel → localhost:15432
# verify alembic is at head on prod (auto-applied at deploy); if not: uv run alembic upgrade head
uv run python scripts/backfill_user_percentiles.py --target prod --snapshot-date 2026-05-30
bin/prod_db_tunnel.sh stop
```

`_assert_target_safe` port-checks the prod target (refuses any non-15432 URL). The CDF artifact is static and ships with the code — prod reads the same CDF as dev; this step only materializes per-user percentile rows.

## Verification

After the backfill, query prod `user_benchmark_percentiles` for `metric IN ('conversion_rate','parity_rate','recovery_rate')` — expect non-zero rows for bullet/blitz/rapid (classical suppresses below the ≥30-span floor, per D-05). Then load a prod user's endgame metrics and confirm the title-line rate chips render alongside the existing ΔES-gap chips (D-01 coexistence).

## Context

- Phase: 99 — Percentile badges for conversion/parity/recovery
- Checkpoint: 99-05 Task 3 (D-11), signed off 2026-05-31 → defer to deploy
- See `.planning/phases/99-percentile-badges-for-conversion-parity-and-recovery/99-05-SUMMARY.md` § Prod Backfill Disposition
