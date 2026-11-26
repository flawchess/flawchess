---
phase: 262-facepalm-promotions-and-key-move-gate
reviewed: 2026-11-23T20:30:00Z
depth: standard
files_reviewed: 22
files_reviewed_list:
  - app/services/line_material.py
  - app/services/facepalm_score.py
  - app/services/facepalm_zones.py
  - app/services/blunder_check_rules.py
  - scripts/backfill_promotion_material.py
  - scripts/backfill_maia_flaws.py
  - scripts/blunder_check/fit_facepalm.py
  - scripts/blunder_check/facepalm_features.py
  - scripts/blunder_check/refresh_features_material.py
  - scripts/blunder_check/refit_shift.py
  - scripts/blunder_check/caught_rate.py
  - tests/services/test_line_material.py
  - tests/services/line_material_fixtures.py
  - tests/services/test_facepalm_inputs.py
  - tests/services/test_facepalm_score.py
  - tests/scripts/test_fit_facepalm.py
  - tests/scripts/test_facepalm_features.py
  - tests/scripts/test_backfill_maia_flaws.py
  - tests/scripts/test_backfill_promotion_material.py
  - tests/scripts/test_refresh_features_material.py
  - tests/scripts/test_refit_shift.py
  - tests/scripts/test_caught_rate.py
findings:
  critical: 0
  warning: 3
  info: 4
  total: 7
  necessity: 0
status: issues_found
---

# Phase 262: Code Review Report

**Reviewed:** 2026-11-23T20:30:00Z
**Depth:** standard
**Files Reviewed:** 22
**Status:** issues_found

## Summary

Reviewed what commit 60fe9c80c and 3a96b73da changed. The ten test modules that cover these files pass (338 tests, run through the suite only).

The core rule is sound. I traced `_promotion_gain`, `_victim_value`, `_exchange_value`, `_count_step`, `_quiet_walk_end` and `_ends_in_exchange` and found no logic error.
- The en passant early return is correct.
- A quiet promotion has a non-zero victim value, so it no longer sets the desperado square (D-03).
- A line ending on a promotion is settled by the static exchange.
- A captured promoted piece nets out to the pawn.

The Python and SQL twins of the allowed-loss gate agree, including NULL handling.
- Both guard a NULL played probability or NULL loss first.
- Both read a NULL `missed` as 0.0.
- Both compare the raw `missed`, never `lam * missed`.
- At `lam = 0` both still evaluate the gate and the missed term is omitted. This is pinned by the compiled-SQL column count test and the mixed-row parity row.

No critical defect found. The three warnings concern the already-run prod pass: a candidate-filter coverage gap, a crash window in the undo log, and a biased dry-run sample. The four info items are smaller.

## Warnings

### WR-01: The promotion pass filter cannot see promotions that only occur inside the static exchange

**File:** `scripts/backfill_promotion_material.py:87-159` (filter), `app/services/line_material.py:166-175` (rule it must cover)
**Issue:** The D-07 filter selects rows by a promotion token in the stored lines or in `move_san`. But D-01 also changed `_exchange_value`, which now prices a capture-promotion made *inside* the static exchange. That recapture is never in a stored line. The phase's own test shows it: `test_see_prices_a_capture_promotion` uses the line `"g8f8 b7b1"`, which has no promotion token, yet its stored value moves from 2 to 10 under the new rule.

Such rows are therefore not candidates. After the pass they keep the old stored pair, while the go-forward hook and any later line pass compute the new one. The result is two populations of rows scored by different material rules, which is the inconsistency D-06 set out to avoid.

The prod dry run reported `Sample checked / mismatches: 2000 / 0`. That does not clear this class, because the sample is not representative (see WR-03). The class is probably rare, since it needs a line ending on a capture on rank 1 or 8 with a pawn on the 7th or 2nd rank able to recapture. The impact is unknown, because nothing measured it.

**Fix:** Measure first, then widen. The pass is idempotent and guarded, so a second run is safe.
```python
# 1. Dry-run the pass over ALL line-stamped blunders with the token filter dropped:
#    candidate_page_stmt(..., filter=None); the report's "Would change" is the miss count.
# 2. If non-zero, add the lines the exchange can reach to the filter, for example a last
#    token that lands on rank 1 or 8: regexp_match(pv, '[a-h][1-8][a-h][18]$'), then re-run.
```
Add a regression test with the `"g8f8 b7b1"` position that asserts it is a candidate.

### WR-02: The undo log is appended after the commit and never fsynced, so a crash loses the only way back

**File:** `scripts/backfill_promotion_material.py:540-545` (order), `scripts/backfill_promotion_material.py:486-510` (`_append_undo`)
**Issue:** The module docstring says the undo log "is the way back" for an in-place overwrite. `_process_page` commits the page and only then calls `_append_undo`. `_append_undo` flushes the Python buffer (`handle.flush()`) but does not `os.fsync`. A SIGKILL, OOM kill, power loss, or an `OSError` such as a full disk between `commit()` and the append leaves up to `FLAWS_PER_BATCH` (2000) rows rewritten with no record of their old pair. The cooperative SIGINT/SIGTERM handling does not help for those failure modes. The re-run path cannot recover them either, because a re-run sees the new values as stored and logs nothing.

The prod run has already finished. The script is documented as the template for later runs (for example the deferred benchmark-DB backfill), so the ordering should be fixed before it is reused.

**Fix:** Write and fsync the log before the commit. An over-reporting log is harmless, because the documented rollback is guarded on "current pair equals the logged new pair".
```python
applied, misses = await _write_page(session, changes)
_append_undo(undo_log, applied)   # includes os.fsync(handle.fileno())
await session.commit()
```

### WR-03: The dry-run sample covers only the lowest user ids, so it is weak evidence for "non-token rows replay to their stored pair"

**File:** `scripts/backfill_promotion_material.py:221-225`
**Issue:** `_sample_stmt` takes the games with `game_id % 50 == 0` and then `ORDER BY user_id, game_id, ply LIMIT 2000`. That is the first 2000 matching blunders in primary-key order, so it comes from the one or few users with the lowest ids, not a spread over users, time controls and eras. The exit-3 safety check (the token filter missed a place the rule reads) is only as good as this sample. WR-01 shows a real class the sample would not necessarily hit.

**Fix:** Order by a hash so the sample is spread across users.
```python
.order_by(func.md5(cast(GameFlaw.game_id * 1000 + GameFlaw.ply, Text))).limit(size)
```
Alternatively, drop the `LIMIT`, use a larger modulus, and stratify per user.

## Info

### IN-01: A real-run report prints "Sample checked / mismatches: 0 / 0" although no sample was run

**File:** `scripts/backfill_promotion_material.py:388`, `scripts/backfill_promotion_material.py:679-686`
**Issue:** The sample check runs only in dry runs. The prod run report (`reports/maia-flaws-backfill/promotion-pass-prod-run-20261123T174801Z.md`) still shows `Sample checked / mismatches: 0 / 0`, which reads as a passed check.
**Fix:** In a real run print `n/a (dry run only)` for that line, or omit it.

### IN-02: `_best_recapture` relies on python-chess yielding the queen promotion first

**File:** `app/services/line_material.py:155-163`
**Issue:** The cheapest attacker is chosen with `min(captures, key=...)`. A pawn capture onto the last rank generates four moves (Q, R, B, N) with the same attacker value, and `min` returns the first. That is the queen only because `generate_pseudo_legal_moves` emits promotions in the order Q, R, B, N (I confirmed the order for a7xb8 with python-chess 1.11). The static exchange silently depends on that unspecified ordering. If it changed, the SEE would under-price the best promotion.
**Fix:** Make the choice explicit with a tie-break key.
```python
key=lambda m: (_SEE_VALUES[board.piece_type_at(m.from_square) or chess.PAWN], -_promotion_gain(m))
```

### IN-03: The caught-rate switch time can mislabel two small windows, and the checkpoint script is only valid before the pass

**File:** `scripts/blunder_check/caught_rate.py:104-110`, `scripts/blunder_check/refit_shift.py:81-84`
**Issue:**
- `FACEPALM_262_SWITCH_AT` is set to the end of the deploy run (17:47:39). Sessions composed between the container restart and that moment already used the new model but are labelled `phase_259`.
- Sessions composed during the promotion pass (about 17:48 to 18:44 UTC) are labelled `phase_262` but snapshotted partly stale material inputs (accepted under D-06).
- `refit_shift.py` hard-codes `PHASE_259_COEFS` but reads the stored material pair. After the pass the "shipped" side is no longer the Phase 259 state, and `candidate_coefs()` equals the live constants. That is fine at the checkpoint, but the script is misleading afterwards.

**Fix:** Say in the `caught_rate.py` comment that the split is approximate to within the deploy and pass window. Mark `refit_shift.py` as checkpoint-only in its docstring.

### IN-04: Duplicated page recompute, and a documented rollback that no code implements

**File:** `scripts/blunder_check/refit_shift.py:462-481`, `scripts/backfill_promotion_material.py:429-453`, `scripts/backfill_promotion_material.py:31-34`
**Issue:** `_recompute_page` exists twice, once over an `AsyncSession` and once over an `AsyncConnection`, with identical bodies. The undo-log docstring describes a "replay-free guarded UPDATE" rollback, but no script performs it. The only way back is a hand-written query over the TSV, which is a risk for a costly-to-reverse change (D-06).
**Fix:** Share one function that takes an `AsyncSession | AsyncConnection`. If the pass is reused, add a small `--undo-log <file>` rollback mode with the guarded UPDATE (`SET old WHERE current = logged new`).

---

_Reviewed: 2026-11-23T20:30:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
