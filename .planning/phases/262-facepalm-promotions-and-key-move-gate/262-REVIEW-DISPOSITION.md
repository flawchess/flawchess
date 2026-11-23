---
phase: 262-facepalm-promotions-and-key-move-gate
source: 262-REVIEW.md
recorded: 2026-11-23
---

# Phase 262: Code Review Disposition

Dispositions: `open` (recorded, not yet triaged), `fixed`, `skipped`, `deferred`.

| ID | Severity | Disposition | Source |
|---|---|---|---|
| WR-01 | warning | deferred | Candidate filter misses capture-promotions that happen only inside the static exchange. Measured on dev after the review (read-only, temp/facepalm-262/measure_wr01_dev.py): 0 of 20,381 blunders without a promotion token replay to a different pair. Rare; prod was not measured (a full replay of about 4.7M rows). Follow-up for the owner to decide. |
| WR-02 | warning | open | Undo log is appended after the page commit and not fsynced. The prod run finished with a complete log (124,216 rows); matters for later runs of the script. |
| WR-03 | warning | open | Dry-run sample draws from the lowest user ids only. The dev measurement above covers every non-token blunder on dev; the prod sample stays weak evidence. |
| IN-01 | info | open | Real-run report prints a 0 / 0 sample line although no sample ran. |
| IN-02 | info | open | `_best_recapture` relies on python-chess ordering for the queen promotion tie-break. |
| IN-03 | info | open | FACEPALM_262_SWITCH_AT is the end of the deploy run; sessions composed during the pass carry partly stale inputs. |
| IN-04 | info | open | `_recompute_page` duplicated in refit_shift.py; the undo-log rollback is documented but not implemented. |
