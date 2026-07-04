---
phase: 148-pipeline-tactic-correctness-fixes-code-review-2026-07-02
reviewed: 2026-07-04T09:06:56Z
depth: standard
files_reviewed: 9
files_reviewed_list:
  - app/routers/eval_remote.py
  - app/services/chesscom_client.py
  - app/services/endgame_service.py
  - app/services/engine.py
  - app/services/eval_drain.py
  - app/services/flaws_service.py
  - app/services/lichess_client.py
  - app/services/score_confidence.py
  - app/services/tactic_detector.py
findings:
  critical: 1
  warning: 2
  info: 1
  total: 4
status: issues_found
---

# Phase 148: Code Review Report

**Reviewed:** 2026-07-04T09:06:56Z
**Depth:** standard
**Files Reviewed:** 9
**Status:** issues_found

## Summary

Phase 148 was scoped as five targeted correctness fixes plus general hygiene. Four of
the five fixes check out: the `tactic_detector.py` truncated-mate fallback tags only
the generic `MATE` motif (never a named-mate subtype) and is unreachable unless every
prior named/back-rank/generic mate detector already failed to fire, so no double-tagging
risk; the `eval_drain.py` all-fail circuit breaker correctly gates on `eval_targets`
non-empty (preserving `test_engine_none_marks_complete`), never stamps
`evals_completed_at`, and emits one aggregated Sentry event with no interpolated
variables; the `eval_remote.py` `entry_eval_lease_expiry > now()` guard is correct SQL
and is covered by a dedicated regression test; the `score_confidence.py` /
`endgame_service.py` covariance-correction term is algebraically sound, is
divide-by-zero-safe (the `eg_n <= 0 or ne_n <= 0` guard fires first), and
`shared_n=0` is proven byte-identical to the prior formula by a dedicated test.

The `flaws_service.py` fix (item 2, full-FEN `_recompute_fen_map`) is also correct:
`board.fen()` is now stored for detector-internal PV replay, but the persisted
`game_flaws.fen` column is still split back to piece-placement-only via
`fen_before_flaw.split(" ")[0]` in `_build_flaw_record`, so the CLAUDE.md
`board_fen()`-only contract for the API-facing column is preserved. No
Zobrist/position-comparison call site was touched.

However, the **same file introduces a new, untested sign-convention bug** in the
`has_forced_mate` derivation added to wire item 1 (the tactic-detector truncated-mate
fallback) into the flaw pipeline: `positions[n].eval_mate` / `positions[n + 1].eval_mate`
are white-perspective absolute values (documented at
`tests/services/test_flaws_service.py:10` and enforced everywhere else in this same
file via the existing `_pov_mate()` helper), but the new code checks `> 0` unconditionally
regardless of which side is actually to move. This silently breaks the fallback (and can
misfire it) for every black-POV flaw — roughly half of all flaw records. See CR-01.

## Critical Issues

### CR-01: `has_forced_mate` flag ignores eval_mate's white-perspective sign convention for black POV

**File:** `app/services/flaws_service.py:483-487` and `app/services/flaws_service.py:505-511`
**Issue:**
`GamePosition.eval_mate` is stored white-perspective absolute (positive = white mates,
negative = black mates) — this convention is explicit in
`app/services/engine.py:253` ("positive = white mates, negative = black mates"),
restated at `tests/services/test_flaws_service.py:10`, and already correctly handled
everywhere else in this file via the `_pov_mate()` helper (line 212-216:
`return pos.eval_mate if mover_color == "white" else -pos.eval_mate`) and the
`_solver_color_for()` helper (line 518-532), which computes exactly the POV color
needed here.

The two new `has_forced_mate` derivations added for Phase 148 item 1 bypass both
helpers and test the raw value directly against `0`:

```python
# "missed" orientation — pov = board_before.turn (the mover)
_mate_missed = positions[n].eval_mate if 0 <= n < len(positions) else None
has_forced_mate_missed = _mate_missed is not None and _mate_missed > 0
return detect_tactic_motif(board_before, pv, has_forced_mate=has_forced_mate_missed)

# "allowed" orientation — pov = board_after_flaw.turn (the refuting side)
_mate_allowed = positions[n + 1].eval_mate if n + 1 < len(positions) else None
has_forced_mate_allowed = _mate_allowed is not None and _mate_allowed > 0
return detect_tactic_motif(
    board_after_flaw, pv_allowed, has_forced_mate=has_forced_mate_allowed
)
```

`eval_mate > 0` only means "the side that is to move has a forced mate" when that side
is White. When the POV side (mover for "missed", refuter for "allowed") is Black, a
genuine forced mate for that side is stored as `eval_mate < 0`, so:

- **False negative** (the common case): a real deep forced mate for Black, truncated
  before the mating position, is never flagged (`_mate < 0` fails the `> 0` check) —
  the exact "silently fell through to Tier 2+ untagged" bug the phase set out to fix,
  now reintroduced for every black-POV flaw.
- **False positive** (less common but real): when it's Black's move and White has an
  unstoppable mate regardless of Black's reply (`eval_mate > 0` while POV is Black),
  the flag incorrectly fires `has_forced_mate=True` for Black's POV, and the
  fallback in `tactic_detector.py` will tag `TacticMotifInt.MATE` attributed to the
  wrong side using a PV that is not actually a mating line for Black.

No test in `tests/services/test_flaws_service.py` exercises `has_forced_mate_missed` /
`has_forced_mate_allowed` for a black-POV flaw ply (the only monkeypatch test for the
"allowed" fen-map replay, `test_detect_tactic_for_flaw_replays_ep_capture_without_parse_error`,
never sets `eval_mate` and stubs out `detect_tactic_motif` entirely), so this regressed
silently.

**Fix:** Reuse the existing `_pov_mate()` / `_solver_color_for()` helpers instead of
comparing the raw stored value directly:

```python
# "missed" orientation
_mate_missed = positions[n] if 0 <= n < len(positions) else None
_pov_mate_missed = _pov_mate(_mate_missed, _solver_color_for(n, "missed")) if _mate_missed else None
has_forced_mate_missed = _pov_mate_missed is not None and _pov_mate_missed > 0
return detect_tactic_motif(board_before, pv, has_forced_mate=has_forced_mate_missed)

# "allowed" orientation
_pos_allowed = positions[n + 1] if n + 1 < len(positions) else None
_pov_mate_allowed = (
    _pov_mate(_pos_allowed, _solver_color_for(n, "allowed")) if _pos_allowed else None
)
has_forced_mate_allowed = _pov_mate_allowed is not None and _pov_mate_allowed > 0
return detect_tactic_motif(
    board_after_flaw, pv_allowed, has_forced_mate=has_forced_mate_allowed
)
```

Add a regression test with a black-POV flaw ply carrying a negative `eval_mate`
(forced mate for Black) feeding a truncated PV, asserting the fallback still fires —
mirroring `TestHasForcedMateFallback` in `test_tactic_detector.py` but at the
`_detect_tactic_for_flaw` integration level where the sign conversion actually happens.

## Warnings

### WR-01: `_recompute_fen_map` docstring/comment at line 128 not updated for split-back behavior

**File:** `app/services/flaws_service.py:128-130`
**Issue:** The `FlawRecord` TypedDict field comment still reads `# board_fen() of the
position BEFORE the flawed move (piece placement only)`, which is now technically true
of the *output* value again (since `_build_flaw_record` splits the full FEN back down),
but the surrounding narrative doesn't cross-reference the new split-back step in
`_build_flaw_record` (`board_fen_only = fen_before_flaw.split(" ")[0]`). A future reader
tracing `fen_map` values could reasonably assume `FlawRecord.fen` is filled directly
from `fen_map.get(n, "")` (the pre-148 behavior) and miss that a transform now happens
in between.
**Fix:** Add a one-line cross-reference in the `FlawRecord.fen` comment pointing at
`_build_flaw_record`'s split-back step, e.g.: `# board_fen()-equivalent (piece
placement only) — derived from fen_map's full FEN via .split(" ")[0] in
_build_flaw_record, see Phase 148 D-02`.

### WR-02: `has_forced_mate` truncated-mate fallback records an approximate `tactic_depth`

**File:** `app/services/tactic_detector.py:2500-2506`
**Issue:** The fallback sets `_fallback_depth = len(moves) - 1`, i.e. the last ply of
the *truncated* PV, not the ply at which the actual mate occurs (which is unknown —
the PV was capped at `PV_CAP_PLIES` before reaching it). Every other mate detector's
`depth` return value is the true mating ply (`boards[-1].is_checkmate()` holds at that
index). Consumers that sort/join on `tactic_depth` (e.g. the depth-primary dispatcher a
few lines below, or any downstream code assuming depth reflects the actual mate ply)
will see a systematically shallower depth than reality for every truncated-mate row.
This is a known, accepted approximation per the inline comment, but it is not
documented as a caveat on the function's public docstring (`detect_tactic_motif`'s
`Returns:` section describes `tactic_depth` uniformly as "raw half-move ply index...
or None" with no carve-out for the truncated case).
**Fix:** Add a one-line caveat to the `detect_tactic_motif` docstring's `Returns:`
section noting that `tactic_depth` is the last-displayed-ply approximation (not the
true mate ply) when `has_forced_mate=True` and the PV was truncated before mate.

## Info

### IN-01: `entry_submit_eval`'s lease-expiry guard change is undocumented against a stale-worker-id edge case

**File:** `app/routers/eval_remote.py:891-912`
**Issue:** The new predicate correctly excludes expired leases, but note for future
maintainers: `Game.entry_eval_lease_expiry > sa.func.now()` evaluates to SQL `NULL`
(row excluded) if `entry_eval_lease_expiry` is ever `NULL` while `entry_eval_leased_by`
is non-null (e.g. a manual DB fixup, or a future code path that clears one column
without the other). Today `_claim_entry_eval_games` always sets both columns together
in the same `UPDATE`, so this can't currently happen — but there's no DB-level
`CHECK` or NOT NULL constraint enforcing the pairing, so a future change to the claim
path could silently reintroduce the pre-148 stale-lease bug without any test catching
it (the existing coverage only exercises the past-timestamp case, not the NULL case).
**Fix:** No code change required now; consider a test asserting the guard also
excludes a row with `entry_eval_leased_by` set but `entry_eval_lease_expiry IS NULL`,
to lock in the invariant as a specification rather than an implicit assumption.

---

_Reviewed: 2026-07-04T09:06:56Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
