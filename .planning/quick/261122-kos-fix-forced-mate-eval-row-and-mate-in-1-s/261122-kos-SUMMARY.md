---
quick_id: 261122-kos
slug: fix-forced-mate-eval-row-and-mate-in-1-s
status: complete
commit: fa3462b81
date: 2026-11-22
---

# Quick 261122-kos: Forced-mate flag reads the wrong eval row; mate in 1 stripped by the gate

## What changed

- `app/services/flaws_service.py`, `_detect_tactic_for_flaw`: `has_forced_mate` now reads `positions[n]`
  for allowed and `positions[n - 1]` for missed (was `positions[n + 1]` and `positions[n]`).
- `app/services/forcing_line_gate.py`, `apply_forcing_line_filter`: a forced mate whose line is emptied by
  the trailing only-move strip is checked on the unstripped line instead of being rejected.
- Tests: two existing POV tests moved to the corrected row; four new tests in
  `TestDetectTacticForFlawForcedMatePov` and `TestForcedMateExemptions`.
- `CHANGELOG.md`: bullet under `[Unreleased]` / Fixed.

## Verification

- Affected suites (gate, flaws service, retag, ab-validate, eval drain, full eval drain, backfill, worker
  endpoints, tactic detector, tests/scripts): 1488 passed, 7 skipped.
- Mutation check: with both fixes reverted, 5 tests fail (the mate-in-1 test and all four row tests).
- `ruff format`, `ruff check`, `ty check app/ tests/ scripts/`, nesting-depth gate: clean.
- The full pre-merge gate was not run.

## Impact (user 28, prod data dumped read-only, replayed offline)

Cumulative effect of this task plus quick 261122-jsf against the stored tags, 36,087 flaws:
2,127 rows change (about 49 of them are older drift unrelated to either task).

| Orientation | Added | of which mate | Replaced by a mate tag | Removed |
|-------------|-------|---------------|------------------------|---------|
| Allowed     | 1,242 | 1,196         | 185                    | 18      |
| Missed      | 519   | 499           | 153                    | 8       |

The row fix alone accounts for about 495 allowed and 448 missed changes, all on lines capped at 12 plies
(mates in 7 or more; about half are mates in 10 or more). The mate-in-1 fix accounts for 7 rows.

## Follow-ups

- Prod and benchmark retag after Phase 252 finishes (owner decision). Tactic zones may move.
- None of the added mate tags were spot-checked by hand. About 340 rows replace a shallower tactic (fork,
  pin, hanging piece) with a generic MATE tag at depth 11.
- Open, to be discussed: at opening plies (<= 20) the first blob node often has no second-best move
  (885 allowed, 943 missed flaws on this account); the gate then treats it as an only-move.
- Phase 252 acceptance check: 24% of allowed and 30% of missed blobs are shorter than their stored line
  (2-3 nodes against 12 plies); this should fall to about zero after the re-walk.
