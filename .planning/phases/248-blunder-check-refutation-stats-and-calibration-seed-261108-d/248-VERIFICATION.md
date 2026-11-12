---
phase: 248-blunder-check-refutation-stats-and-calibration-seed-261108-d
verified: 2026-11-10T15:30:00Z
status: passed
score: 12/12 must-haves verified
covered_files:
  - ".planning/phases/248-blunder-check-refutation-stats-and-calibration-seed-261108-d/248-01-PLAN.md"
  - ".planning/phases/248-blunder-check-refutation-stats-and-calibration-seed-261108-d/248-01-SUMMARY.md"
  - ".planning/phases/248-blunder-check-refutation-stats-and-calibration-seed-261108-d/248-02-PLAN.md"
  - ".planning/phases/248-blunder-check-refutation-stats-and-calibration-seed-261108-d/248-02-SUMMARY.md"
  - ".planning/phases/248-blunder-check-refutation-stats-and-calibration-seed-261108-d/248-03-PLAN.md"
  - ".planning/phases/248-blunder-check-refutation-stats-and-calibration-seed-261108-d/248-03-SUMMARY.md"
  - ".planning/phases/248-blunder-check-refutation-stats-and-calibration-seed-261108-d/248-04-PLAN.md"
  - ".planning/phases/248-blunder-check-refutation-stats-and-calibration-seed-261108-d/248-04-SUMMARY.md"
  - ".planning/phases/248-blunder-check-refutation-stats-and-calibration-seed-261108-d/248-05-PLAN.md"
  - ".planning/phases/248-blunder-check-refutation-stats-and-calibration-seed-261108-d/248-05-SUMMARY.md"
  - ".planning/phases/248-blunder-check-refutation-stats-and-calibration-seed-261108-d/248-06-PLAN.md"
  - ".planning/phases/248-blunder-check-refutation-stats-and-calibration-seed-261108-d/248-06-SUMMARY.md"
  - ".planning/phases/248-blunder-check-refutation-stats-and-calibration-seed-261108-d/248-07-PLAN.md"
  - ".planning/phases/248-blunder-check-refutation-stats-and-calibration-seed-261108-d/248-07-SUMMARY.md"
  - ".planning/phases/248-blunder-check-refutation-stats-and-calibration-seed-261108-d/248-08-PLAN.md"
  - ".planning/phases/248-blunder-check-refutation-stats-and-calibration-seed-261108-d/248-08-SUMMARY.md"
  - "alembic/versions/20261109_120000_c4e9b1d7f248_phase_248_maia_refutation.py"
  - "app/models/game.py"
  - "app/models/game_flaw.py"
  - "app/repositories/game_flaws_repository.py"
  - "app/services/maia_flaw_scoring.py"
  - "app/services/maia_flaw_stats.py"
  - "reports/blunder-check/blunder-check-calibration-2026-11-10.md"
  - "reports/blunder-check/spot-check-2026-11-10.md"
  - "reports/maia-flaws-backfill/prod-refutation-coverage.md"
  - "scripts/backfill_maia_flaws.py"
  - "scripts/blunder_check/metrics.py"
  - "scripts/blunder_check/oddness.py"
  - "scripts/blunder_check/render.py"
  - "scripts/blunder_check/sample.py"
  - "scripts/blunder_check/spot_check.py"
  - "scripts/blunder_check_calibration.py"
covered_digest: "v4:sha256:a87c67fc38f41e180da74a242787d7258aa9c8b3ab04d42ee0f35d89a83f876a"
behavior_unverified: 0
overrides_applied: 0
---

# Phase 248: Blunder-Check Refutation Stats and Calibration Verification Report

**Phase Goal:** Store how likely a player at the blunderer's rating is to find the punishment of each user-side blunder, and calibrate blunder-check selection on prod data, so the selection phase builds on measured constants.
**Verified:** 2026-11-10
**Status:** passed
**Re-verification:** No, initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Two typed nullable columns on `game_flaws` (REAL prob, SMALLINT rank) plus a separate completion stamp exist, metadata-only (D-01, D-09, D-22) | VERIFIED | Migration `c4e9b1d7f248` adds `game_flaws.maia_refutation_prob REAL`, `maia_refutation_rank SMALLINT`, `games.maia_refutation_completed_at TIMESTAMPTZ`, all nullable, no default/index/CHECK; `alembic heads` = single head `c4e9b1d7f248`; models match (`game_flaw.py`, `game.py`). |
| 2 | The value stored is Maia's prob/rank for Stockfish's best reply in the post-blunder position, source `COALESCE(best_move, pv[0])` at `ply+1`, rank = 1 + strictly-higher count (D-02, D-20) | VERIFIED | `_flaw_fingerprint_select` outer-joins aliased `GamePosition` at `GameFlaw.ply + 1` with `coalesce(best_move, nullif(split_part(pv,' ',1),''))`; `compute_refutation_stats` reuses `_rank`. Mutation check: changing the join to `ply` makes `test_refutation_tracer_user_blunder_scored_and_both_stamps` fail. |
| 3 | Scope is exactly user-side blunders (severity 2, parity vs `user_color`), misses included; mistakes and opponent flaws stay NULL (D-03, D-06) | VERIFIED | `_is_user_blunder` uses `_SEVERITY_INT["blunder"]` and `mover_is_white_at_ply` from `query_utils`; no concreteness columns anywhere. Tests `test_refutation_scope_*` pass (both colors, mistakes/opponent NULL). Prod slice check: 103/103 user blunders scored, 277 other flaw rows with no refutation value. |
| 4 | Elo is the blunderer's pinned Elo (taken from the pre-push board mover), fed to `full_policy` (symmetric self/oppo feed); post-blunder board comes from replay/in-memory boards, never `game_flaws.fen` (D-04, D-05) | VERIFIED | `_derive_refutation(board, played_uci, elo, ...)` with `elo` from `_mover_elo(inputs, board)`; `post = pre_board.copy(stack=False)` + push; `full_policy` feeds one `elo_to_input` as both. Mutation check: hard-coding a different Elo fails `test_refutation_elo_is_the_blunderers_for_both_colors`. En-passant/castling/no-mutation tests pass. |
| 5 | Go-forward: every lane that scores flaws today (drain, remote atomic submit, flaw-blob-submit, backfill) writes the pair with both stamps; Maia-unavailable never stamps (D-07, D-09) | VERIFIED | `score_game_flaws_after_apply` (default `full` mode) is the single hook called from `eval_drain.py:1582`, `eval_remote.py:1096` and `:1484`; `write_game_maia_scores` stamps both columns in full mode; `is_maia_available()` guard returns before any write. Lane tests in `test_full_eval_drain.py`/`test_eval_worker_endpoints.py` and `test_refutation_maia_absent_stamps_neither` pass. Prod evidence: 460 post-deploy live-lane games carried refutation values with no backfill (678 of 679 blunders). |
| 6 | Reclassification (D-08): no-Maia reclassify keeps survivors by omission, new rows NULL, both stamps cleared; Maia-loaded apply re-scores | VERIFIED | `clear_maia_flaws_completed` now clears both stamps in one UPDATE (WHERE either non-NULL); all callers (`eval_apply.py:1149`, `backfill_flaws.py:417`, `opening_cache_repair.py:2080`) go through it; `MAIA_REFUTATION_COLUMNS` is separate from the blob/tactic tuples and `flaw_record_to_row` emits no refutation keys (grep: no refutation reference in `eval_apply.py`/`flaws_service.py`). Tests `test_reclassify_*`, `test_refutation_full_rescore_clears_row_downgraded_from_blunder`, `test_reclassify_clear_helper_clears_both_stamps` pass. |
| 7 | Backfill `--mode refutation` is sharded (md5 residue), checkpointed on its own stamp, writes only the pair + stamp, terminates (zero-blunder games stamped), re-run selects nothing (D-10, D-22) | VERIFIED | `_STAMP_CLAUSE_BY_MODE["refutation"]` = `maia_refutation_completed_at IS NULL AND maia_flaws_completed_at IS NOT NULL`; refutation rows carry only PK + 2 keys; zero-blunder games replay nothing and run no inference. 8 `test_refutation_mode_*` tests pass. Prod: both catch-up runs EXIT=0 with `games_selected=0`. |
| 8 | Prod: go-forward shipped, full backfill + catch-up run, coverage >= 99% of user-side blunders in fully evaluated games with NULL remainder bucketed (D-11, D-12, D-21) | VERIFIED (from committed evidence) | Deploy `e60dd1302` (release PR #469) in git history; local `temp/maia-refutation-backfill/prod-full.log` has `EXIT=0` and total line `games_stamped=1026584 refutations_scored=2293321 refutations_null=4071 write/score failures 0`; summing the 9 committed shard JSONs reproduces those totals exactly. `reports/maia-flaws-backfill/prod-refutation-coverage.md`: denom 2,301,338, scored 2,297,262, **99.823%**, NULL buckets (terminal no pv 0.078%, non-terminal no best_move/pv 0.061%, no rating 0.037%, invalid_root 17, unstamped 3) all at or below the D-21 probe. 247-07 completed first (247-07-SUMMARY exists, 99.570%) per D-12. Prod not re-queried (no access). |
| 9 | Calibration report: miss classification (allowed/pure/mixed), findability grid by Elo bucket, eval band, hazard window fit, herring supply, per-user supply, provenance, arrow oddness, sample sizes, "how to read" (D-13..D-17, D-23) | VERIFIED | `reports/blunder-check/blunder-check-calibration-2026-11-10.md` (242 lines, committed) contains every section with per-cell n: Cases by Elo bucket, Findability grid (allowed/pure/mixed at t 0.05-0.50 plus rank-1), Eval band (5 bands, blunders and herring), Window fit (positions 1-5, hazard weights 0.265/L 3-5), Herring supply, Supply per user (estimate, labelled), Provenance (engine vs lichess), Arrow oddness (+ unselected baseline), Control (99.9% stored-vs-recomputed agreement). Built from read-only `scripts/blunder_check_calibration.py`; 5 phase test files pass (159 tests re-run by verifier). |
| 10 | Report states recommended constants (R, X', eval band) as recommendation only; spot-check of about 20 windows per Elo bucket, human-readable, no user identifiers (D-18) | VERIFIED | Recommended R = 0.3, X' = 0.2, band [0.10, 0.90] with rationale; `spot-check-2026-11-10.md` is committed with 120 windows, exactly 20 in each of 6 buckets (62 allowed, 34 herring, 13 pure miss, 11 mixed), game link + lead-in + judged moves + answer + refutation; grep finds no `username`/`user_id`. |
| 11 | Scope guard: no selection service, API/router, UI, schedule, leaderboard, or constants wired into app code (D-19) | VERIFIED | `git diff --name-only 157076b62^ HEAD -- app frontend` lists only the models/repository/scoring/stats files plus a `frontend/package*.json` dependency patch bump from an unrelated release; no `app/routers` or `app/schemas` changes; the two reports are the only files in the report commit `7ed12276c`. |
| 12 | Quality gates hold on the shipped code | VERIFIED | Verifier re-ran: `ruff check` clean, `ty check app/ scripts/` clean, `check_function_size.py` no breaches (1317 functions), 159 tests across the stats/scoring/backfill/metrics/calibration files pass. No TBD/FIXME/XXX markers in any phase file. |

**Score:** 12/12 truths verified (0 present but behavior-unverified)

### Requirements Coverage (CONTEXT decisions D-01..D-23)

| Requirement | Source Plans | Status | Evidence |
|-------------|-------------|--------|----------|
| D-01 columns | 01 | SATISFIED | Truth 1 |
| D-02 / D-20 refutation source | 01, 07 | SATISFIED | Truth 2 |
| D-03 scope | 01, 03 | SATISFIED | Truth 3 |
| D-04 Elo | 01 | SATISFIED | Truth 4 |
| D-05 exact positions | 01, 03 | SATISFIED | Truth 4 |
| D-06 no concreteness columns | 01 | SATISFIED | Truth 3 |
| D-07 go-forward | 01 | SATISFIED | Truth 5 |
| D-08 reclassification | 01 | SATISFIED | Truth 6 |
| D-09 / D-22 completion signal | 01, 03 | SATISFIED | Truths 1, 5, 7 |
| D-10 backfill | 03, 07 | SATISFIED | Truth 7 |
| D-11 phase-done conditions | 06, 07, 08 | SATISFIED | Truth 8 (deploy go-ahead recorded in 248-06-SUMMARY; coverage 99.823%; report committed) |
| D-12 sequencing with 247-07 | 06, 07 | SATISFIED | Truth 8 |
| D-13..D-16, D-23 calibration math | 02, 04, 08 | SATISFIED | Truth 9 |
| D-17 arrow oddness | 05, 08 | SATISFIED | Truth 9 |
| D-18 outputs | 05, 08 | SATISFIED | Truth 10 |
| D-19 out of scope | 06, 08 | SATISFIED | Truth 11 |
| D-21 99% bar / NULL budget | 07 | SATISFIED | Truth 8 |

No orphaned decisions: every D-ID in the PLAN `requirements:` fields (D-01..D-23 collectively) maps to a verified truth. D-02 research proof on dev rows is recorded in 248-RESEARCH; the code and tests encode it, and the ply+1 mutation fails the tests.

### Key Link Verification

| From | To | Via | Status |
|------|----|-----|--------|
| eval_drain / eval_remote (2 sites) | `score_game_flaws_after_apply` | direct call after commit | WIRED |
| `score_game` | `compute_refutation_stats` / `full_policy` | `_derive_refutation` | WIRED |
| `write_game_maia_scores` | `mark_maia_refutation_completed` / `bulk_update_flaw_maia_stats` | same txn, advisory-locked, fingerprint re-check (includes severity and ply+1 reply) | WIRED |
| eval_apply / backfill_flaws / opening_cache_repair | `clear_maia_flaws_completed` (clears both stamps) | helper | WIRED |
| `backfill_maia_flaws.py --mode` | `score_game(..., mode)` and `write_game_maia_scores` | mode rides on `GameMaiaScore` | WIRED |
| calibration script | stored `maia_refutation_*`, `maia_best_*` columns + classifier `_run_all_moves_pass` | read-only session | WIRED (control 99.9%) |

### Data-Flow Trace (Level 4)

Stored columns are populated with real Maia values on prod: coverage 99.823% (2,297,262 of 2,301,338), median probability 0.53, 69/103 rank-1 on the slice, never a static fallback. The calibration report reads those stored values (not recomputes) and agrees with an independent recompute of flaw severities at 99.9%.

### Behavioral Spot-Checks

| Behavior | Check | Result |
|----------|-------|--------|
| Phase tests (stats, scoring, backfill, metrics, calibration) | `pytest` on the 5 files | 159 passed |
| Refutation source is ply+1 | mutate join to `ply`, run scoring tests | FAILED as expected, file restored |
| Elo is the blunderer's | hard-code another Elo, run scoring tests | FAILED as expected, file restored |
| Prod totals match shard JSONs | sum of 9 shard JSONs vs log total line | exact match |

Working tree confirmed clean after the mutation checks.

### Probe Execution

No probes declared by this phase. SKIPPED.

### Anti-Patterns Found

None blocking. No debt markers. The open code-review findings (248-REVIEW-DISPOSITION.md: 3 warnings, 6 info, 0 critical) are robustness items in the report scripts and backfill error handling; none contradicts a must-have and the prod backfill ran with 0 write/score failures.

### Advisory (non-blocking, from 248-REVIEW.md)

- WR-01: `--from-cache` with a mismatching `--db` can resolve cached game ids against the wrong database when re-rendering the spot-check. The committed spot-check was rendered from the prod cache against prod, so its content is unaffected.
- WR-02: backfill treats `StaleDataError` as a generic failure; relevant only to future long catch-up runs.
- WR-03: `MAX_BLUNDER_POSITION` coupled to `WINDOW_LENGTHS` by comment only; both are 5 today.
- Cosmetic: a spot-check window with the blunder at position 1 prints an empty "Judged user moves:" list.

### Human Verification Required

None for phase completion. The owner's review of the spot-check (and possible GM review) and the decision to wire R / X' / band into the selection phase are the expected follow-up (D-18: recommendation only), not an unmet deliverable of this phase.

### Gaps Summary

No gaps. The schema, go-forward scoring on all lanes, reclassification handling, refutation-mode backfill, prod rollout with coverage verification, and the committed calibration report with spot-check all exist, are wired, and are corroborated by tests, mutation checks, committed reports, shard JSONs and local logs. Prod-side claims (deploy, coverage SQL, live-lane check) were checked against committed reports and git history only; they could not be re-queried.

---

_Verified: 2026-11-10_
_Verifier: Claude (gsd-verifier)_
