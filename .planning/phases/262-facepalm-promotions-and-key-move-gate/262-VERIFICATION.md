---
phase: 262-facepalm-promotions-and-key-move-gate
verified: 2026-11-23T21:10:00Z
status: human_needed
score: 10/11 must-haves verified
covered_files:
  - ".planning/phases/262-facepalm-promotions-and-key-move-gate/262-01-PLAN.md"
  - ".planning/phases/262-facepalm-promotions-and-key-move-gate/262-01-SUMMARY.md"
  - ".planning/phases/262-facepalm-promotions-and-key-move-gate/262-02-PLAN.md"
  - ".planning/phases/262-facepalm-promotions-and-key-move-gate/262-02-SUMMARY.md"
  - ".planning/phases/262-facepalm-promotions-and-key-move-gate/262-03-PLAN.md"
  - ".planning/phases/262-facepalm-promotions-and-key-move-gate/262-03-SUMMARY.md"
  - ".planning/phases/262-facepalm-promotions-and-key-move-gate/262-04-PLAN.md"
  - ".planning/phases/262-facepalm-promotions-and-key-move-gate/262-04-SUMMARY.md"
  - ".planning/phases/262-facepalm-promotions-and-key-move-gate/262-05-PLAN.md"
  - ".planning/phases/262-facepalm-promotions-and-key-move-gate/262-05-SUMMARY.md"
  - ".planning/phases/262-facepalm-promotions-and-key-move-gate/262-06-PLAN.md"
  - ".planning/phases/262-facepalm-promotions-and-key-move-gate/262-06-SUMMARY.md"
  - ".planning/phases/262-facepalm-promotions-and-key-move-gate/262-07-PLAN.md"
  - ".planning/phases/262-facepalm-promotions-and-key-move-gate/262-07-SUMMARY.md"
  - "app/services/blunder_check_rules.py"
  - "app/services/facepalm_score.py"
  - "app/services/facepalm_zones.py"
  - "app/services/line_material.py"
  - "reports/blunder-check/facepalm-features-2026-11-23.tsv"
  - "reports/blunder-check/facepalm-fit-2026-11-23.md"
  - "reports/maia-flaws-backfill/promotion-pass-prod-run-20261123T174801Z.md"
  - "scripts/backfill_maia_flaws.py"
  - "scripts/backfill_promotion_material.py"
  - "scripts/blunder_check/caught_rate.py"
  - "scripts/blunder_check/facepalm_features.py"
  - "scripts/blunder_check/fit_facepalm.py"
  - "scripts/blunder_check/refit_shift.py"
  - "scripts/blunder_check/refresh_features_material.py"
covered_digest: "v4:sha256:a9360021c9364831b8dc90c2127226bb86cecdc7338934eb4d4860dd45591079"
behavior_unverified: 0
overrides_applied: 0
gaps: []
human_verification:
  - test: "Check that the token filter of the promotion pass leaves no stale rows (review WR-01), by a dry run of the pass over all line-stamped blunders with the token filter dropped, on prod."
    expected: "Would change = 0 (or a small number that the owner accepts). The dev measurement is 0 of 20,381 blunders without a promotion token."
    why_human: "Needs a read-only prod run of about 4.7M replayed rows. The verifier may not read prod, and the committed dry-run sample (2,000 rows, lowest user ids only, WR-03) is weak evidence for rows without a token."
  - test: "Confirm the owner looked at the 20 newly passing rows of reports/blunder-check/refit-shift-2026-11-23.md (spot-check requirement of the ROADMAP) and was content."
    expected: "Owner agrees the rows that newly pass 0.70 are fair questions, in particular the 'promotion (inputs changed)' rows."
    why_human: "The committed record shows the owner's verdict on the model (confirm-keep-cuts, quoted in 262-06-SUMMARY.md), but the quote talks about label row 177 and the concept, not the 20-row list. Only the owner can say the list was reviewed."
  - test: "Confirm the prod-side claims that are not in a committed report: pair consistency (0 rows with exactly one of material_loss / material_missed NULL), the three undo-log spot rows, server SHA 1d7ac168 live, and the 4 board-failure rows left on their old values."
    expected: "Matches 262-07-SUMMARY.md."
    why_human: "Prod reads are out of bounds for the verifier. The pass counters, dry-run numbers and EXPLAIN are backed by committed reports (checked below); these four are backed only by the summary."
---

# Phase 262: Facepalm Promotions as Material and Key-Move Gate Verification Report

**Phase Goal:** Make the facepalm score see pawn breakthroughs and score every blunder on the move that matches its type, in one refit. Two changes share the refit and the owner checkpoint.
**Verified:** 2026-11-23
**Status:** human_needed
**Re-verification:** No, initial verification

The code on `main` delivers the goal. Both rule changes are in the shipped code, both score twins agree, the refit constants are the ones the fit tool prints, the release is on `origin/production`, and the prod pass reports exist and match the summaries. No truth failed. Three items need a human or a prod read (see frontmatter), the main one being the completeness of the pass's token filter (WR-01), which nothing measured on prod.

The ROADMAP entry has no `Success Criteria` list and no requirement IDs, so the truths below are derived from the goal paragraph and the CONTEXT decisions D-01 to D-08.

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | D-01: a promotion credits the promoting side with the promoted piece minus the pawn (queen 8, rook 4, bishop or knight 2) inside `_victim_value`; capture-promotion adds the captured piece; the first move, the quiet walk and the static exchange read it | VERIFIED | `app/services/line_material.py`: `_promotion_gain` (l.135-142) and `_victim_value` (l.145-152, en passant branch first). `_exchange_value` now takes `gain = _victim_value(...)` (l.176, with a bug-fix comment). `_replay_line` and `_quiet_facts_after_first_move` price steps and the first move with `_victim_value`; `_quiet_walk_end` and `_ends_in_exchange` read `victim_value`, so a promotion continues the walk and a line ending on one is settled by the static exchange. Tests `test_promotion_gain_per_piece`, `test_quiet_promotion_rules`, `test_see_prices_a_capture_promotion` pass. |
| 2 | D-02: no cap, floor or mate constant changes; an opponent queen promotion on the next move stores the cap 5.0 | VERIFIED | `git diff 60fe9c80c~1 60fe9c80c -- app/services/blunder_check_rules.py` touches only the coefficient block, comments and the two cut comments. `test_opponent_queen_promotion_next_move_stores_the_cap` and `test_promotion_cap_examples_store_the_decaying_mean` pass (the 262-01 SUMMARY corrects the CONTEXT example 0.23 to 0.0, per-depth 0, 0, -1, -1, -1). |
| 3 | D-03: the capture of a freshly promoted piece on its promotion square counts | VERIFIED | `test_desperado_exclusion_counts_a_freshly_promoted_piece` passes. Mechanism visible in `_count_step` (l.235-247): a promotion has a non-zero `victim_value`, so the blunderer's move no longer sets `quiet_square`. My own run of the D-03 FEN `1r4k1/P7/8/8/8/8/8/6K1`, line `g8f7 a7a8q b8a8 ...` read 1 at depths 1, 3, 5. |
| 4 | D-04: the score reads the reply exactly on an allowed loss (`loss > 0 and loss >= missed`) and the best move otherwise, one shared condition in both twins and the type rule, no minimum loss | VERIFIED | `app/services/facepalm_score.py`: `is_allowed_loss` (l.224-231), `_allowed_loss_sql` (l.277-279), `_key_move_term` and `_key_move_sql` use them (NULL guard still the first CASE branch), `facepalm_type_of` and `facepalm_type_sql` use them. No other `loss > 0` score gate remains in `app/` (grep). The scripts that mirror the gate (`facepalm_features._has_null_score_input`, `backfill_maia_flaws._fetch_reply_status`, `fit_facepalm._reads_reply`) use the shared rule. Python/SQL parity tests incl. the mixed row pass. Mutation by me: replacing `is_allowed_loss` with `loss > 0` makes `test_is_allowed_loss_rule` fail. |
| 5 | D-05: the fit report carries the old gate as information only | VERIFIED | `facepalm-fit-2026-11-23.md` has "Old gate reference (D-05)": type 0.889 CV AUC, 94 / 11 at 0.70; loss gate 0.902, 99 / 12. `test_old_gate_reference_section` passes. |
| 6 | One refit on label sets 1 to 8 with the new inputs and gate; new `FACEPALM_*` constants pasted as printed and reproduced by `--check-constants`; AUC only a range check | VERIFIED | `FACEPALM_MODEL` printed from the live module equals the report's Constants block exactly (-1.7891, -0.6193, 0.8879, 0.3993, 1.1635, 0.8057). `tests/scripts/test_fit_facepalm.py` (incl. the `--check-constants` tests) passes on the committed 2026-11-23 table. AUC range check printed as 0.019 against 0.02 (at the edge, labelled "within range", never used to choose). Label file unchanged. |
| 7 | Blocking owner checkpoint: owner confirms model and cuts; fair / unfair table at cuts 50% to 70%; drill pool size; spot-check of about 20 newly passing rows | VERIFIED (record), see human item 2 | 262-06-SUMMARY.md quotes the owner verbatim ("I believe the changes are conceptually sound. confirm-keep-cuts") and keeps `FACEPALM_SCORE_MIN` / `FACEPALM_STATS_MIN` 0.70. The D-15 table is in the fit report; the drill pool by cut is in the appended "Prod facts" section; `refit-shift-2026-11-23.md` lists exactly 20 newly passing rows with analysis links. Whether the owner reviewed those 20 rows is not provable from files. |
| 8 | Targeted material pass: a re-runnable one-connection script covering rows with a promotion token (D-07), with dry run, sample check, guarded change-only UPDATE and undo log; the gate change needs no pass | VERIFIED | `scripts/backfill_promotion_material.py`: `promotion_candidate_filter` (pv at ply + 1, pv and `best_move` at the flaw ply, `move_san` with "="), `as_real` 4-byte compare, `exit_code_for` (exit 3 on sample mismatch), `pool_size=1`. 21 tests pass. Reports back the summary: prod dry run 163,656 candidates / 124,216 would change / sample 2,000 with 0 mismatches / 4 board failures; real run changed 124,216, 0 guard misses, 3,380 s, the same counters as the dry run; post-pass dry run would change 0. The gate change itself writes nothing (it is a score expression). |
| 9 | The token filter is complete: no row without a promotion token changes under the new rule (ROADMAP: "only rows with a promotion token ... can change") | UNCERTAIN | Code review WR-01 (disposition: deferred): `_exchange_value` now prices capture-promotions that occur only inside the static exchange, and those recaptures are never in a stored line, so such rows are not candidates and keep the old pair after the pass while the go-forward hook computes the new one. Measured on dev only: 0 of 20,381 non-token blunders replay to a different pair. Prod unmeasured. The prod sample check is weak evidence (WR-03: first 2,000 blunders of `game_id % 50 == 0` in primary-key order, i.e. the lowest user ids). Likely rare, but a falsifiable claim with no prod evidence. See human item 1. |
| 10 | D-06: one release carries the rule, the gate and the constants together; the pass runs straight after the deploy; changelog bullet | VERIFIED | `origin/production` contains `60fe9c80c` and `1d7ac168f` (release PR #506) and the production copy of `facepalm_score.py` has `is_allowed_loss`. `CHANGELOG.md` l.71 carries the bullet under `[Unreleased]`. Timeline in the reports is consistent: deploy end 17:47:39Z, pass started 17:48:01Z (undo log name `...T174801Z`), report generated 18:44:21Z = start + 3,380 s. The release also carries quick task 261123-lb8 (owner-approved, noted in 262-07-SUMMARY.md). |
| 11 | D-08 and the 261 snapshot rule: provisional zone bands not re-derived but noted; the caught-rate calibration separates old and new score versions without rewriting snapshots | VERIFIED | `facepalm_zones.py` docstring carries the Phase 262 D-08 note, no band value changed (`test_facepalm_zones.py` passes). `caught_rate.py`: `FACEPALM_262_SWITCH_AT = 2026-11-23T17:47:39Z`, `version_of`, `--rescore`; `test_caught_rate.py` passes; no migration or UPDATE on `blunder_check_windows`. |

**Score:** 10/11 truths verified (1 uncertain, 0 behavior-unverified)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `app/services/line_material.py` | promotion rule | VERIFIED | substantive, wired through `facepalm_material_inputs` (hook, line pass, features, pass script) |
| `app/services/facepalm_score.py` | shared allowed-loss condition | VERIFIED | both twins, type twins, `__all__` export |
| `app/services/blunder_check_rules.py` | new constants | VERIFIED | equal to the fit report block |
| `app/services/facepalm_zones.py` | D-08 note | VERIFIED | docstring only |
| `scripts/backfill_promotion_material.py` | targeted pass | VERIFIED | 776 lines, 21 tests, docs entry in `docs/dev-tooling.md` |
| `scripts/blunder_check/refresh_features_material.py`, `refit_shift.py`, `fit_facepalm.py`, `caught_rate.py` | refit and checkpoint tooling | VERIFIED | tests pass; spike probes deleted (the `spike/` directory is gone) |
| `reports/blunder-check/*2026-11-23*`, `facepalm-explain-262.md`, `reports/maia-flaws-backfill/promotion-pass-prod-*` | evidence | VERIFIED (exist, say what the summaries say) | counters in all three pass reports match 262-07-SUMMARY.md |

### Key Link Verification

| From | To | Via | Status |
|------|----|-----|--------|
| `_victim_value` | quiet walk, first move, `_exchange_value` | direct call | WIRED |
| `is_allowed_loss` / `_allowed_loss_sql` | key-move twin, type twin, features NULL rule, status counters, fit tool | direct import | WIRED |
| `facepalm_material_inputs` | go-forward hook, line pass, pass script, `refit_shift`, features refresh | single writer | WIRED |
| fit report Constants block | `blunder_check_rules.py` | `--check-constants` test | WIRED |
| `FACEPALM_262_SWITCH_AT` | caught-rate report split | `version_of` | WIRED |

### Data-Flow Trace (Level 4)

Backend only, no rendered values. The stored `material_loss` / `material_missed` pair is written by `facepalm_material_inputs` from stored lines and read by the score expression; the index `ix_game_flaws_facepalm_inputs` covers the same columns (prod EXPLAIN in `facepalm-explain-262.md`: Index Only Scan for both reader statements, counts 172 to 195 ms, comparison 18 ms). FLOWING.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Phase test files | `uv run pytest tests/services/test_line_material.py tests/services/test_facepalm_score.py tests/services/test_facepalm_inputs.py tests/scripts/test_fit_facepalm.py tests/scripts/test_backfill_promotion_material.py tests/scripts/test_refit_shift.py tests/scripts/test_caught_rate.py tests/services/test_facepalm_zones.py tests/scripts/test_refresh_features_material.py -q` | 256 passed | PASS |
| Gate mutation | patch `is_allowed_loss` to `loss > 0`, run `test_facepalm_score.py` | `test_is_allowed_loss_rule` fails | PASS (tests are not vacuous) |
| Constants equal the fit report | import `FACEPALM_MODEL` and compare to the report block | equal | PASS |
| Nesting-depth gate | `uv run python scripts/check_function_size.py app/ --fail-over-depth 4` | OK, 1,684 functions, no breaches | PASS |
| Lint | `uv run ruff check app scripts tests` | All checks passed | PASS |

Not run by me: the full backend suite and the frontend gate (summaries report 7,053 passed on the merged tree, CI green on PR #506; I did not reproduce them).

### Probe Execution

No probe scripts are declared by the phase (no `probe-*.sh`). SKIPPED.

### Requirements Coverage

The phase has no requirement IDs in REQUIREMENTS.md (ROADMAP: "TBD"). Plans reference D-01 to D-08 of 262-CONTEXT.md instead: D-01 to D-04 (truths 1 to 4), D-05 (5), D-06 and D-07 (8, 9, 10), D-08 (11). No orphaned decision.

### Anti-Patterns Found

No `TBD`, `FIXME`, `XXX`, `TODO` or `HACK` in the 11 changed source files. No stubs; no hardcoded empty data on a scoring path.

| Finding | Severity | Note |
|---------|----------|------|
| WR-01 candidate filter cannot see promotions that occur only inside the static exchange | Warning | Truth 9; deferred in `262-REVIEW-DISPOSITION.md`; prod unmeasured |
| WR-02 undo log appended after commit, not fsynced | Warning | The prod run finished with a complete log (124,217 lines per the summary); matters for any reuse of the script. The rollback UPDATE itself is not implemented (IN-04) |
| WR-03 dry-run sample drawn from the lowest user ids | Warning | Weakens the evidence for truth 9 |
| IN-01 real-run report prints "Sample checked / mismatches: 0 / 0" although no sample ran | Info | Visible in the prod run report; reads as a passed check |
| IN-02 `_best_recapture` tie-break relies on python-chess emitting the queen promotion first | Info | Verified true for python-chess 1.11 by the reviewer |
| IN-03 switch time is the end of the deploy run, sessions during the pass carry partly stale inputs | Info | Accepted under D-06 |
| 4 board failures in the pass | Info | Rows skipped, keep old values; not investigated (262-07-SUMMARY.md) |

None of these blocks the goal. WR-02 and WR-03 and the open info items are recorded as `open` in the disposition file and are not phase blockers.

### Human Verification Required

1. **Prod completeness of the token filter (WR-01).**
   **Test:** Read-only dry run of the pass over all line-stamped blunders with the token filter dropped (or a hash-spread sample, WR-03).
   **Expected:** Would change = 0, or a count the owner accepts; if non-zero, widen the filter (for example a last token landing on rank 1 or 8) and re-run the idempotent pass.
   **Why human:** Needs prod access; dev says 0 of 20,381.

2. **The 20-row spot-check.**
   **Test:** Confirm the owner went through the 20 newly passing rows in `reports/blunder-check/refit-shift-2026-11-23.md`.
   **Expected:** Rows are fair questions at 0.70.
   **Why human:** The owner's recorded sentence is about row 177 and the model, not the list.

3. **Prod-only claims without a committed report.**
   **Test:** Pair consistency (no row with exactly one of the pair NULL), the three undo-log spot rows, server SHA, the 4 board-failure rows.
   **Expected:** As in 262-07-SUMMARY.md.
   **Why human:** Prod reads are not allowed to the verifier.

### Gaps Summary

No failed truth and no blocker. The phase goal (promotions seen as material, key-move term on the type rule, one refit with owner sign-off, targeted pass, one release) is achieved in the code on `main` and on `origin/production`. The status is `human_needed` only because of the three items above; the only substantive risk is truth 9, a probably small population of prod rows whose stored pair may still follow the old rule. Follow-ups recorded elsewhere and not required here: correct label 177 at the next refit (262-06-SUMMARY.md), and decide WR-01 to WR-03 (the disposition file leaves them open or deferred).

Note on claims that differ from the CONTEXT numbers: the CONTEXT expected about 145k changed rows and about 1,600 rows losing their score; prod measured 124,216 and 161. These are explained in the reports (best-move probability backfill filled most NULLs; the dry run is the authority) and do not contradict the goal.

---

_Verified: 2026-11-23T21:10:00Z_
_Verifier: Claude (gsd-verifier)_
