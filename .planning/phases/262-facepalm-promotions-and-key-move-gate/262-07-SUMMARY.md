---
phase: 262-facepalm-promotions-and-key-move-gate
plan: 07
subsystem: facepalm-score
tags: [facepalm, release, prod-pass, D-01, D-04, D-06, D-07]
requires:
  - phase: 262-06
    provides: "owner decision confirm-keep-cuts and the confirmed Constants block"
  - phase: 262-04
    provides: "scripts/backfill_promotion_material.py"
provides:
  - "Phase 262 score live on prod (release PR #506, server 1d7ac168)"
  - "Stored promotion rows on prod carry the new material inputs"
  - "FACEPALM_262_SWITCH_AT set for the caught-rate score-version split"
affects: []
key-files:
  created:
    - reports/maia-flaws-backfill/promotion-pass-prod-dry-20261123T164427Z.md
    - reports/maia-flaws-backfill/promotion-pass-prod-run-20261123T174801Z.md
    - reports/maia-flaws-backfill/promotion-pass-prod-dry-20261123T184431Z.md
  modified:
    - app/services/blunder_check_rules.py
    - tests/scripts/test_fit_facepalm.py
    - tests/services/test_facepalm_score.py
    - CHANGELOG.md
    - scripts/blunder_check/caught_rate.py
key-decisions:
  - "Owner go-ahead for the release, 2026-11-23, verbatim: \"go, feed is stopped, push the extra main commit\""
  - "The release also carries quick task 261123-lb8 (blunder check scoring rebalance and its points migration), a local main commit the owner asked to push"
  - "Cuts unchanged, so the frontend FACEPALM_HIGH_CUTOFF and its tests are untouched"
requirements-completed: [D-01, D-04, D-06, D-07]
completed: 2026-11-23
status: complete
actuals:
  tasks: 3
---

# Phase 262 Plan 07: Release and prod promotion pass Summary

The refitted facepalm score is live for every player, and all 124,216 stored promotion rows that needed it on prod carry the new material inputs.

## Tasks 1 and 2 (executor, commits 9b2d2b1ee and 66b141e84)

- The six FACEPALM_* coefficients are the Constants block of reports/blunder-check/facepalm-fit-2026-11-23.md as printed; `--check-constants` with the default type gate reproduces them in a test. The three cuts keep their values and carry a "262 checkpoint" sentence.
- COMMITTED_FEATURES and `_FEATURES_TSV` point to facepalm-features-2026-11-23.tsv. Frontend untouched.
- Changelog bullet under `## [Unreleased]`, `### Changed`.
- Executor gate, all exit 0: ruff format, ruff check, ty (app and analysis), depth gate, `pytest -n auto -x` (7043 passed, 8 skipped), serial `pytest -x` (7043 passed, 8 skipped, 427 s), frontend lint, build, tests, knip.

## Task 3 (orchestrator)

| Step | Result |
|---|---|
| Pre-deploy dry run on prod | exit 0: 163,656 candidates, 124,216 would change, sample 2,000 checked / 0 mismatches, 4 board failures |
| Owner go-ahead | given with the dry-run numbers (quoted in the frontmatter) |
| Squash-merge to main | 60fe9c80c; one conflict in .planning/STATE.md, resolved to the phase side. Gate re-run on the merged tree: backend 7053 passed, 8 skipped; frontend lint, build, tests, knip all 0 |
| Release | PR #506, CI green (backend, frontend, docker, test), squash-merged as 1d7ac168f |
| Deploy | bin/deploy.sh exit 0; server at 1d7ac168; site HTTP 200; forward-port pushed (d34eacbd5). T_DEPLOY = 2026-11-23T17:47:39Z (end of the deploy run) |
| Prod pass | started 17:48:01Z, exit 0 after 3,380 s: 124,216 changed, 0 guard misses, 4 board failures. Undo log temp/promotion-pass/undo-prod-20261123T174800Z.tsv, 124,217 lines |
| Dry run after | exit 0: 0 would change, sample mismatches 0 |
| Pair consistency (prod, MCP) | 0 rows with exactly one of material_loss / material_missed NULL |
| Undo log spot check | three rows (games 472153, 2270977, 3243757) hold their new pair on prod |
| Caught-rate switch | FACEPALM_262_SWITCH_AT = 2026-11-23T17:47:39Z (commit 3a96b73da); tests/scripts/test_caught_rate.py 34 passed; `caught_rate.py --db prod` shows the split (phase_259 83 windows, phase_262 412 windows) |

Pass counters: loss up / down 66,865 / 9,796; missed up / down 53,750 / 18,843; 11 rows went from NULL to a value; type flips 43,461 missed win to allowed loss and 9,170 the other way. The run changed exactly the rows the dry run predicted.

## Deviations from Plan

- **Dry run started early and alongside the feed.** The pre-deploy dry run ran while the executor did Tasks 1 and 2 (it does not read the constants) and while the line-repair feed was still active, under the owner's earlier go-ahead for read-only prod reads. The feed was stopped before the release; the pass then changed exactly the predicted count.
- **Extra main commit in the release.** Local main was one commit ahead of origin (quick task 261123-lb8). Pushed on the owner's instruction, so the release carries it and its migration.
- **Foreign commit in the squash.** Another session committed its feed run report (a23edda50, one report file) onto the phase branch while it was checked out; it is part of the squash.
- **Runs launched as harness background tasks** instead of setsid nohup; same logs and EXIT markers.
- **The plan's `uv run python caught_rate.py --db prod` report** was written to gitignored temp/facepalm-262/caught-rate-split-prod.md, not committed.
- **Sentry check (step 7) not done.** The Sentry connector needs authentication in this session. Site liveness and the backend log tail were clean right after the deploy.
- **The 4 board failures were not investigated.** Those rows are skipped and keep their old values.
- **Code review ran after the deploy** (the plan folds the release into its last task): 0 critical, 3 warnings, 4 info; see 262-REVIEW.md and 262-REVIEW-DISPOSITION.md. WR-01 (rows whose only promotion is inside the static exchange are not candidates) measured 0 of 20,381 on dev; prod unmeasured.

## Rollback

Costly (D-06): a revert release plus a guarded UPDATE back to the old pair from the undo log. No code implements that UPDATE yet (review IN-04).

## Self-Check: PASSED
