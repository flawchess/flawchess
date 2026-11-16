---
phase: quick-261116-mco
plan: 01
subsystem: blunder-check / facepalm label sampling
tags: [facepalm, labels, sampler, decaying-mean, SEED-261115-agg]
status: complete
requires:
  - scripts/blunder_check/miss_labels.py (set 7 sampler)
  - app/services/line_material.py (material arrays)
provides:
  - scripts/blunder_check/decaying_mean.py (DECAY_DEPTHS, DECAY_RATIO, DECAY_WEIGHTS, loss_series, gain_series, decaying_mean)
  - "miss_labels.py --mode disagreement --append-to (set 8 blind draw, append-only)"
affects:
  - the later refit phase (decaying mean vs first-stable vs depth 3)
tech-stack:
  added: []
  patterns: ["append-only label file writer", "stratified draw with same-group borrowing"]
key-files:
  created:
    - scripts/blunder_check/decaying_mean.py
    - tests/scripts/test_decaying_mean.py
  modified:
    - scripts/blunder_check/miss_labels.py
    - tests/scripts/test_miss_labels.py
    - tests/scripts/test_facepalm_features.py
    - tests/scripts/test_fit_facepalm.py
decisions:
  - "DISAGREEMENT_MIN_PAWNS = 0.5 (orchestrator override of the plan's 1.0)"
  - "Per-depth gain floored at 0 in decaying_mean.py; shipped FACEPALM_MISSED_FLOOR (None) untouched, the refit settles it"
metrics:
  duration: "about 1h (incl. a 3.5 min dev smoke)"
  completed: 2026-11-16
actuals:
  tokens: 17600
  tasks: 3
  commits: 3
plan_head_before: 4fca7c65ad6400f8dffe8e3b9f6a8f31f28178dd
plan_head_after: 5d1adcb01eb0b2152a756ca8bcbeca18f5771a98
---

# Phase quick-261116-mco Plan 01: Facepalm label set 8 sampler (disagreement draw) Summary

`miss_labels.py --mode disagreement --append-to <label file>` draws about 60 blind rows (23 loss-disagreement, 22 miss-disagreement, 15 plain depth-3 pure misses) where the shipped depth-3 input and a decaying mean over odd depths 1/3/5/7/9 (weights 1, 1/2, 1/4, 1/8, 1/16) differ by at least 0.5 pawns, and appends them as set 8 in the set-7 row shape without touching an existing byte.

## What was built

- `scripts/blunder_check/decaying_mean.py` (pure, no I/O): `loss_series`, `gain_series`, `decaying_mean`, `DECAY_RATIO = 0.5`, `DECAY_WEIGHTS`. Depth-3 parity with the shipped `loss_feature` / `missed_feature` is tested on 10 rows. `app/`, `FACEPALM_*` constants and the real label file are unchanged (`git diff 78c3a5aa5 -- app/ reports/blunder-check/facepalm-labels.tsv` is empty).
- `miss_labels.py`: `MissCandidate` carries `played_material` / `best_material`; `build_candidate(..., mode=)` keeps depth-3 pure misses plus any row where `disagreement_group` is not None; `series_shape` (spike / early / late / other, in that precedence); `disagreement_group`; `stratify_disagreement` (quotas loss 6/6/6/5, miss 6/5/6/5, plain 15 over set 7's cells; a short stratum borrows from its own group, `*_other` first, borrowed rows keep their own stratum; shortfall and unfilled per group are reported, never padded across groups); `append_blind_rows` (append mode only, header check, n continues from the file's max, set-7 shape of 14 fields with 9 trailing empty cells, one newline only if the file lacks a trailing one); extended key entries (n, set, group, stratum, arrays, depth-3 inputs, decaying means, best_prob, pre_spread); `disagreement_summary_line`.
- Guards, all before Maia or any DB connection, exit `EXIT_APPEND_REFUSED = 7`: `--db dev` with the real label file as append target; missing target or bad header; the target already holds set 8 (restore with git before a rerun); `--append-to` without `--mode disagreement`. The append target is added to the excluded label files.
- Mode defaults: seed 261116, key file `temp/blunder-check/set8-key.json`, 15 plain misses (misses mode keeps seed 254, 40 pure misses, set 7's key path).

## Threshold arithmetic (DISAGREEMENT_MIN_PAWNS = 0.5, cap 5, weights sum 1.9375)

The orchestrator lowered the threshold from the plan's 1.0 to 0.5 so the cases the label set exists for are reachable. Gap = |depth-3 value - decaying mean|:

| Shape | Gap | Qualifies from |
| --- | --- | --- |
| early: v at depth 1 only, 0 at depth 3 | v / 1.9375 = 0.516 v | 1 pawn |
| spike at depth 3 (0 elsewhere) | 0.742 v | 1 pawn (spike minimum height 1) |
| late: v held from depth 5 on (0 at 1 and 3) | 0.226 v | 3 pawns (a piece: 0.68; 2 pawns: 0.45, no) |
| spike at depth 5 alone | 0.129 v | 4 pawns (cap 5 gives 0.65) |
| value only at depth 7 or 9 | at most 0.32 at the cap | never |

The seed's queen-trade best line (gains 1, 1, 5 capped, 1, 1) has a gap of 0.516 and is drawn as a `miss_spike` (the plan expected None at 1.0). Scarce strata: late and depth-5 spikes; cheap: early and depth-3 spikes.

## Verification

- Tests: `uv run pytest -n auto tests/scripts/test_decaying_mean.py tests/scripts/test_miss_labels.py tests/scripts/test_facepalm_features.py tests/scripts/test_fit_facepalm.py`: 109 passed (test_decaying_mean 17, test_miss_labels 30 of which 18 are new, plus the two downstream files).
- `ruff format --check scripts/blunder_check tests/scripts` clean (62 files), `ruff check` clean, `uv run --group maia-inference ty check app/ tests/ scripts/` zero errors, `scripts/check_function_size.py --fail-over-depth 4` on both modules: no breaches.
- Downstream tolerance: `parse_labels` returns set-8 rows with label ""; `gather_labels` passes them through; `fit_facepalm` already treated an empty label as unlabelled (REASON_NO_LABEL, listed under "Extra rows"), proven by a new test with rows 241-243 (no change to fit_facepalm.py). `test_parse_labels_on_the_real_label_file` now holds before and after the prod append (sets 1-7 = 230 rows, set 8 optional).

## Dev smoke (real dev DB, real Maia, read-only; appended to a COPY under temp/)

Command: `uv run --group maia-inference python scripts/blunder_check/miss_labels.py --db dev --mode disagreement --sample-percent 50 --max-rating 3000 --append-to temp/blunder-check/set8-smoke-labels.tsv --key-out temp/blunder-check/set8-smoke-key.json` (exit 0, 3.5 minutes; the harness moved it to the background after 180 s, it completed normally).

Summary line:

```
candidates read 5014; dropped: unstable_line 1891; stable 3123; by material type: loses 799, loses_and_misses 376, misses 805, neither 1143; supply per stratum: loss_spike 129, loss_early 86, loss_late 74, loss_other 477, miss_spike 185, miss_early 78, miss_late 30, miss_other 191; rows written 60 (1-2 / easy 1, 1-2 / hard 1, 1-2 / mid 2, 3-4 / easy 1, 3-4 / hard 2, 3-4 / mid 1, 5-8 / easy 1, 5-8 / hard 1, 5-8 / mid 1, 9+ / easy 1, 9+ / hard 1, 9+ / mid 2, loss_early 6, loss_late 6, loss_other 5, loss_spike 6, miss_early 5, miss_late 6, miss_other 5, miss_spike 6); shortfall: none; unfilled loss 0, miss 0, plain 0
```

Per-stratum yield: every quota filled, no shortfall (loss_spike 6/129, loss_early 6/86, loss_late 6/74, loss_other 5/477, miss_spike 6/185, miss_early 5/78, miss_late 6/30, miss_other 5/191, plain 15 over 12 cells). Dev has 5,014 candidate blunders at 50%, so prod's 0.5% draw (set 7 read about 8.7k rows, 5.8k stable) should have comparable or larger supply, with `miss_late` (30 here) the tightest stratum.

Checks on the copy: the first `size(real file)` bytes equal the real file (`cmp`), 60 appended lines with n 241-300, all 14 fields, set 8, elo/move/link filled, hidden cells and label empty; the key file maps 60 n values (group counts loss 23, miss 22, plain 15). The real label file has no diff.

## Prod run (orchestrator; needs the tunnel, not run by the executor)

```bash
bin/prod_db_tunnel.sh
uv run --group maia-inference python scripts/blunder_check/miss_labels.py --db prod --mode disagreement --append-to reports/blunder-check/facepalm-labels.tsv --key-out temp/blunder-check/set8-key-2026-11-16.json 2>&1 | tee temp/blunder-check/set8-prod-2026-11-16.log
```

Defaults: seed 261116 (set 7 used 254), sample 0.5% (set 7's 0.5% prod draw read 8,719 rows, 5,787 stable), 15 plain misses, mover rating cap 2000.

Reading the summary line: `supply per stratum` is how many candidates the pool offered each of the 8 disagreement strata; `rows written` should be 60 (23 loss, 22 miss, 15 plain cells); `shortfall` lists strata that borrowed (a stratum whose own supply was below its quota; borrowed rows keep their stratum label); `unfilled loss/miss/plain` must be 0 for a full draw.

Rerun recipe if a group is unfilled: a second set-8 append is refused, so restore the file first: `git checkout -- reports/blunder-check/facepalm-labels.tsv`, then rerun with a larger `--sample-percent` (for example 1.0 or 2.0). The orchestrator commits the appended rows (the label file) and keeps the key file in gitignored `temp/` (never commit it). The 60 new rows are blind (label empty, no comment cell); the owner labels them in the file.

## Deviations from Plan

### Auto-fixed / adjusted

**1. [Orchestrator override] Threshold 0.5 instead of 1.0.** The plan's pinned tests were recomputed for 0.5: `0,0,-4,-4,-4` now draws as loss_late (0.903), the "None" cases became `0,0,-2,-2,-2` (0.452) and `0,0,-1,0,0` (0.129), and the queen-trade best line is a `miss_spike` instead of None. The docstring and this SUMMARY carry the 0.5 arithmetic.

**2. [Rule 1 - test fixture] Test pool material types.** A best-line mate at ply 4 is not a depth-3 pure miss (material "neither"), so a miss_late fixture must not carry material "misses"; otherwise it would enter the plain cell grouping with no missed size and raise. Fixed in the tests only (production data cannot produce that combination).

**3. [Rule 3 - typing] Quota typing.** ty rejected `dict[Literal[...], int]` passed as `Mapping[str, int]` (invariant key); the draw helpers now take `Sequence[tuple[DisagreementStratum, int]]`. Behaviour unchanged.

**4. Misses-mode `--append-to` refused.** `--append-to` without `--mode disagreement` is refused (the plan did not specify it; otherwise `args.out` would be None in misses mode).

**5. Tests for plain-cell shortfall.** The fake pools used in the borrowing and summary tests produce plain-cell shortfall (the extra pure rows move the tertile cuts), so those assertions check the disagreement strata only.

### Other

- `fit_facepalm.py` and `facepalm_features.py` needed no change (tolerance proven by tests).
- Not done by design: the prod draw, the refit, the "loses material" gate, WR-01, WR-03.

## Known Stubs

None.

## Threat Flags

None. DB access is unchanged (`make_readonly_engine`, no new SQL); the only new write path is the append-only label writer with the guards above.

## Commits

- `ebfa3a6d8` feat(quick-261116-mco): set-8 disagreement draw tracer, decaying-mean helper, append-only label rows
- `ea641e2c1` feat(quick-261116-mco): set-8 borrowing, summary line, append guards and mode defaults
- `5d1adcb01` test(quick-261116-mco): downstream tolerance of unlabelled set-8 rows, ty-clean quota typing

## Self-Check: PASSED

- Files exist: scripts/blunder_check/decaying_mean.py, tests/scripts/test_decaying_mean.py (created); miss_labels.py and three test files modified.
- Commits ebfa3a6d8, ea641e2c1, 5d1adcb01 are ancestors of HEAD; `git rev-list --count 4fca7c65a..HEAD` = 3.
- `app/` and `reports/blunder-check/facepalm-labels.tsv` are byte-identical to 78c3a5aa5.

## Prod draw (orchestrator, 2026-11-16)

Run with the command above (defaults: seed 261116, sample 0.5%), exit 0, read-only.

- Candidates read 9,548; dropped 3 (game already labelled) and 1,943 (unstable line); 7,602 stable.
- Supply per stratum: loss_spike 304, loss_early 218, loss_late 191, loss_other 1,257, miss_spike 381, miss_early 196, miss_late 69, miss_other 450.
- 60 rows written (23 loss, 22 miss, 15 plain), no shortfall, nothing unfilled.
- Appended to `reports/blunder-check/facepalm-labels.tsv` as set 8, n 241 to 300. The first 230 rows are byte-identical to the previous commit (`cmp`); all 60 new rows have 14 fields with empty hidden cells and an empty label.
- Key file: `temp/blunder-check/set8-key-2026-11-16.json` (gitignored, not committed).
