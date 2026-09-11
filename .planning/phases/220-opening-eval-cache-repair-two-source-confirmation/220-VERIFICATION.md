---
phase: 220-opening-eval-cache-repair-two-source-confirmation
verified: 2026-09-11T20:15:00Z
status: human_needed
score: 5/5 roadmap success criteria verified; 12/12 CACHEFIX requirements verified
covered_files: [".claude/skills/db-report/SKILL.md", ".planning/phases/220-opening-eval-cache-repair-two-source-confirmation/220-01-PLAN.md", ".planning/phases/220-opening-eval-cache-repair-two-source-confirmation/220-01-SUMMARY.md", ".planning/phases/220-opening-eval-cache-repair-two-source-confirmation/220-02-PLAN.md", ".planning/phases/220-opening-eval-cache-repair-two-source-confirmation/220-02-SUMMARY.md", ".planning/phases/220-opening-eval-cache-repair-two-source-confirmation/220-03-PLAN.md", ".planning/phases/220-opening-eval-cache-repair-two-source-confirmation/220-03-SUMMARY.md", ".planning/phases/220-opening-eval-cache-repair-two-source-confirmation/220-04-PLAN.md", ".planning/phases/220-opening-eval-cache-repair-two-source-confirmation/220-04-SUMMARY.md", ".planning/phases/220-opening-eval-cache-repair-two-source-confirmation/220-05-PLAN.md", ".planning/phases/220-opening-eval-cache-repair-two-source-confirmation/220-05-SUMMARY.md", ".planning/phases/220-opening-eval-cache-repair-two-source-confirmation/220-06-PLAN.md", ".planning/phases/220-opening-eval-cache-repair-two-source-confirmation/220-06-SUMMARY.md", ".planning/phases/220-opening-eval-cache-repair-two-source-confirmation/220-07-PLAN.md", ".planning/phases/220-opening-eval-cache-repair-two-source-confirmation/220-07-SUMMARY.md", ".planning/phases/220-opening-eval-cache-repair-two-source-confirmation/220-08-PLAN.md", ".planning/phases/220-opening-eval-cache-repair-two-source-confirmation/220-08-SUMMARY.md", ".planning/phases/220-opening-eval-cache-repair-two-source-confirmation/220-CONTEXT.md", "CHANGELOG.md", "alembic/versions/20260909_120000_a1c2e3f40001_phase_220_opening_cache_audit.py", "alembic/versions/20260912_120000_b7d4f5a60002_phase_220_cache_provenance.py", "app/models/opening_cache_audit.py", "app/models/opening_position_eval.py", "app/routers/eval_remote.py", "app/services/eval_apply.py", "app/services/eval_drain.py", "scripts/backfill_flaws.py", "scripts/opening_cache_repair.py"]
covered_digest: "v1:sha256:ee8c060907c9cae2004c1abee392277531ceac26dc8d9cda1cb5ecd4c4a74165"
behavior_unverified: 0
overrides_applied: 0
behavior_unverified_items: []
coincidental_reliance_items: []
human_verification:
  - test: "Run the `db-report` skill against the dev database and visually confirm the rendered report's §3 shows Check C (lichess cross-check) and Check D (opening bounce rate) with their verdict lines and reference blockquotes formatted correctly."
    expected: "Both checks render as readable markdown with correct numbers, matching the structural grep checks already passing."
    why_human: "Markdown rendering quality is a visual/readability judgment; deferred from plan 02 and plan 07 to end-of-phase UAT per workflow.human_verify_mode default. No test can assert prose quality."
  - test: "Review the four judgment-tier prohibitions (never-delete-unaudited, never-touch-lichess-evals-except-exact-match, never-move-the-goalposts, never-self-confirm) against the live prod repair run and the shipped write path."
    expected: "All four hold — confirmed by this verifier's code-level judge review (see Prohibitions section) — but they are marked `verification: flagged` (judgment-tier, not test-tier) in every plan's frontmatter and were never resolved by a human sign-off."
    why_human: "Per the honest-verifier protocol, a judgment-tier prohibition's LLM-judge verdict is non-authoritative; it belongs in the end-of-phase human checkpoint, not a silent pass."
  - test: "After a few days of live production traffic, query `opening_position_eval` for `disagreements >= 1` and `>= 2`, and check Sentry for `source=opening-cache` messages."
    expected: "A handful of `>= 1` rows is expected noise; a growing `>= 2` population is the D-12 misalignment signature and should be filed as a new seed, not tolerated silently."
    why_human: "Explicitly deferred as a day-0-only reading in 220-08-SUMMARY.md (disagreements were 0/0 at deploy time, before any live Release-2 write had happened) — this is real-time production behavior no static check can pre-verify."
---

# Phase 220: Opening Eval Cache Repair & Two-Source Confirmation Verification Report

**Phase Goal:** Repair the poisoned `opening_position_eval` dedup cache and every game it
tainted, then stop a single engine write from ever poisoning it again — Release 1 (repair
pipeline, audit tables, submit-path cache write) and Release 2 (two-source confirmation),
both deployed to production.

**Verified:** 2026-09-11T20:15:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

This is an 8-plan, two-release phase (Release 1: plans 01-05 + prod run in 06; Release 2:
plans 07-08) with heavy operator/production involvement. Verification combined (a) direct
code inspection of every artifact against its plan's `must_haves`, (b) re-running the
project's own automated test suite and quality gates in this session (not trusting the
SUMMARY claims), and (c) cross-checking git/production state against what the SUMMARYs
assert. Production-side numbers I cannot re-query (the actual prod repair run, the 14
CACHEFIX-11 acceptance queries, the post-deploy confirmed/candidate split) are treated as
operator-recorded evidence per the verification brief and cited from `220-06-SUMMARY.md`
/ `220-08-SUMMARY.md`.

### Observable Truths (ROADMAP Success Criteria — the roadmap contract)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Dev smoke: full pipeline runs end-to-end against dev with a real SIGTERM-mid-batch kill/resume on every stage; no row screened twice, no row skipped | ✓ VERIFIED | `220-05-SUMMARY.md` transcript: 4 literal `kill -TERM` resumes (screen x2, confirm, rederive); `last_game_id_walked` monotonic; 3 real defects found and fixed with regression tests (`test_screen_reaches_terminal_position_of_short_game`, `test_propagate_transitions_status_to_repaired`, `TestPoolFromEnv`), all present and passing in this session's test run |
| 2 | Prod repair: all stages finish, report lands under `reports/opening-cache-repair/`, every CACHEFIX-11 assertion holds | ✓ VERIFIED | `reports/opening-cache-repair/opening-cache-repair-2026-09-11.md` exists on disk (confirmed by `ls`); `220-06-SUMMARY.md` documents all 14 acceptance queries with PASS verdicts, including the primary histogram-vs-lichess-IQR-control signal converging in every band; operator-recorded prod evidence, cited as such |
| 3 | Hardening ships as its own squash-merge; candidate→promote, candidate→replace+Sentry, confirmed-never-overwritten, both read paths ignore candidates, an accepted remote submit writes/promotes through the same function as the tick | ✓ VERIFIED | Code-verified in this session: `_partition_cache_writes`/`_apply_cache_writes` in `app/services/eval_drain.py` implement the 4-bucket algorithm exactly as specified; `eval_apply._fetch_dedup_evals` has the sole `.where(OpeningPositionEval.confirmed.is_(True))`, zero occurrences of `OpeningPositionEval.confirmed` in `app/routers/eval_remote.py`; `tests/services/test_eval_drain.py`, `tests/services/test_full_eval_drain.py`, `tests/test_eval_worker_endpoints.py` all pass in this session (244 tests) |
| 4 | Legacy-cohort sample (CACHEFIX-10) run and its numbers/decision recorded, whichever way it goes | ✓ VERIFIED | `220-06-SUMMARY.md`: `LEGACY-COHORT-DECISION: NO BUILD`, ratio 1.17 (rule needs >2.0), full numerator/denominator table recorded; appended to the committed report |
| 5 | No `bin/reset_db.sh`, no cache truncation, no flaw-threshold/storage-convention/`DEDUP_MAX_PLY` change, no lichess re-evaluation, no benchmark re-clone/re-run | ✓ VERIFIED | Code-verified: `propagate`'s predicate is `IS NOT DISTINCT FROM` exact-old-value only (the only permitted lichess-game contact, by design — confirmed in `scripts/opening_cache_repair.py`); `220-06-SUMMARY.md`/`220-08-SUMMARY.md` Q13 and step 5 attest `git log --oneline -40 -- reports/benchmark/ analysis/` shows no regeneration commit; no `bin/reset_db.sh` invocation appears in any SUMMARY |

**Score:** 5/5 roadmap success criteria verified.

### Requirements Coverage (CACHEFIX-01..12, phase-local IDs from ROADMAP.md)

| Requirement | Source Plan | Description | Status | Evidence |
|---|---|---|---|---|
| CACHEFIX-01 | 01 | 4 audit tables at Alembic head | ✓ SATISFIED | `alembic upgrade head` clean, `alembic revision --autogenerate` empty diff (re-verified this session); tables confirmed in migration file |
| CACHEFIX-02 | 01,03,04 | 7-stage script, `--db` required, resumable, strict gating | ✓ SATISFIED | `scripts/opening_cache_repair.py` (3547 lines) has all 12 subcommands wired (`seed`,`calibrate`,`screen`,`orphans`,`confirm`,`propagate`,`propagate_best_moves`,`rederive`,`demote`,`report`,`legacy-sample`); 78 tests pass in `tests/scripts/test_opening_cache_repair.py` + model tests this session |
| CACHEFIX-03 | 01 | `calibrate` floors + hash-asserted `screen` walk | ✓ SATISFIED | Code + tests verified this session (`TestCalibrate`, `TestScreen`) |
| CACHEFIX-04 | 03 | `confirm` at 1M nodes, floor-gated overwrite | ✓ SATISFIED | `TestConfirm` (7 tests) passing this session |
| CACHEFIX-05 | 03 | `propagate` old-value predicate, post-move shift | ✓ SATISFIED | `TestPropagate` (5 tests) passing; `IS NOT DISTINCT FROM` + `ply = n.ply - 1` confirmed by grep in `scripts/opening_cache_repair.py` |
| CACHEFIX-06 | 03 | `rederive` through drain's classifier, blob/tactic preservation | ✓ SATISFIED | `TestRederive` (7 tests) passing; `refresh_game_oracle_counts` confirmed public in `app/services/eval_apply.py`; `pg_advisory_xact_lock` confirmed in both `scripts/opening_cache_repair.py` and `app/routers/eval_remote.py` (D-04 both sides) |
| CACHEFIX-07 | 04,06 | `report` under `reports/opening-cache-repair/` | ✓ SATISFIED | 3 committed report files on disk; prod report (`opening-cache-repair-2026-09-11.md`) contains the verification block, histogram, 9-named-hash table |
| CACHEFIX-08 | 07,08 | Two-source confirmation + provenance columns | ✓ SATISFIED | Migration `b7d4f5a60002` verified (single 7-column `ALTER TABLE`, `MARK_CONFIRMED_SQL` keyset walk); `OPENING_CACHE_AGREE_MAX_SCORE_DELTA = 0.03` confirmed in code; D-12 Sentry throttle (`_DISAGREEMENT_SENTRY_THRESHOLD: int = 2`) confirmed; D-13 self-promotion guard confirmed via `source_game_id` partitioning logic; deployed to prod (`origin/production` = `6110d8631`, confirmed via `git fetch`+`git log`) |
| CACHEFIX-09 | 02 | db-report sanity Checks C+D | ✓ SATISFIED (structure); visual render is a deferred human-check | `.claude/skills/db-report/SKILL.md` has both `### Check C —` and `### Check D —` headings, verdict lines, `NOT confirmed` counter; grep-verified this session. The rendered-report visual confirmation was deferred to end-of-phase UAT in both `220-02-SUMMARY.md` and `220-07-SUMMARY.md` — still open, see Human Verification |
| CACHEFIX-10 | 04,06 | legacy-cohort sample + decision | ✓ SATISFIED | `NO BUILD` verdict recorded with full numbers in `220-06-SUMMARY.md`; `TestLegacySample` (9 tests) passing this session |
| CACHEFIX-11 | 05,06,08 | Prod acceptance assertions | ✓ SATISFIED | 14 acceptance queries in `220-06-SUMMARY.md`, all PASS; `CHANGELOG.md` carries the Release 1 user-facing bullet (grep-confirmed this session) |
| CACHEFIX-12 | 02 | Submit path writes the cache | ✓ SATISFIED | `_worker_evaluated_plies`/`_cache_targets`/`engine_targets_for_cache` confirmed in `app/routers/eval_remote.py`; benchmark-lane growth 0→9,681→42,921 rows documented across `220-02`, `220-06`, `220-08` SUMMARYs (operator-recorded prod/benchmark-DB evidence) |

No `⚠ MISSING` or `✗ BLOCKED` requirements.

### Required Artifacts

| Artifact | Expected | Status | Details |
|---|---|---|---|
| `alembic/versions/..._phase_220_opening_cache_audit.py` | 4 audit tables, Release 1 | ✓ VERIFIED | Exists, `alembic current` = at this revision as one of two 220 migrations |
| `alembic/versions/..._phase_220_cache_provenance.py` | 7 provenance columns, Release 2 | ✓ VERIFIED | Exists; content matches plan spec exactly (single `ALTER TABLE`, `MARK_CONFIRMED_SQL` keyset walk) |
| `app/models/opening_cache_audit.py` | 4 ORM models | ✓ VERIFIED | Exists, registered in `alembic/env.py` / `app/models/__init__.py` |
| `app/models/opening_position_eval.py` | 7 new columns, updated docstring | ✓ VERIFIED | All 7 columns present with the "Assumption Delta" doc for `source_game_id` (no FK) |
| `scripts/opening_cache_repair.py` | 11-stage operator script | ✓ VERIFIED | 3547 lines, all subcommands wired, `--db`/`--dry-run`/`--limit` on every stage (spot-checked) |
| `app/services/eval_drain.py` | Shared cache write function, candidate/promote/replace, deterministic backfill | ✓ VERIFIED | `_upsert_opening_cache`, `_partition_cache_writes`, `OPENING_CACHE_AGREE_MAX_SCORE_DELTA`, deterministic `ORDER BY` on `OPENING_CACHE_BACKFILL_SQL` all present and match spec |
| `app/services/eval_apply.py` | Confirmed-only read filter, `refresh_game_oracle_counts` | ✓ VERIFIED | Both present; `_fetch_dedup_evals` is the sole filter location |
| `app/routers/eval_remote.py` | Submit-path cache write, advisory lock | ✓ VERIFIED | `_worker_evaluated_plies`, `pg_advisory_xact_lock`, zero second `confirmed` filter |
| `scripts/backfill_flaws.py` | `--from-repair-table` delegating wrapper | ✓ VERIFIED | Present (per `220-03-SUMMARY.md`; not re-grepped independently this session but confirmed via passing `tests/test_backfill_flaws.py`) |
| `.claude/skills/db-report/SKILL.md` | Check C + Check D | ✓ VERIFIED | Both headings, verdict lines, reference blockquotes present |
| `CHANGELOG.md` | Release 1 + Release 2 entries | ✓ VERIFIED | Both bullets present under `## [Unreleased]` (1 heading, confirmed) |
| `reports/opening-cache-repair/*.md` | Committed audit trail | ✓ VERIFIED | 3 files on disk, dated 09-09, 09-10, 09-11 |

### Key Link Verification

| From | To | Via | Status | Details |
|---|---|---|---|---|
| `scripts/opening_cache_repair.py` | `app.core.config.db_url_for_target` | `--db` target resolution | ✓ WIRED | Confirmed by plan-01 grep acceptance criteria (re-verified via passing `test_omitting_db_exits_nonzero`-style tests in this session's full run) |
| `eval_remote._apply_atomic_submit` | `eval_drain._upsert_opening_cache` | shared write function, 2nd call site | ✓ WIRED | `engine_targets_for_cache` kwarg confirmed at the `apply_full_eval` call site |
| `eval_apply._fetch_dedup_evals` | `eval_remote._fetch_cached_opening_hashes` | confirmed filter inherited by delegation | ✓ WIRED | Zero `OpeningPositionEval.confirmed` references in `eval_remote.py`, confirmed by grep |
| `rederive` / `_apply_flaw_blob_submit` | `pg_advisory_xact_lock(_game_write_lock_key(game_id))` | D-04 shared serialization point | ✓ WIRED | Present in both `scripts/opening_cache_repair.py` and `app/routers/eval_remote.py` |
| `opening_cache_audit.status` | `opening_position_eval.confirmed` | Release-2 migration's `MARK_CONFIRMED_SQL` | ✓ WIRED | Migration file inspected directly; joins on exactly `screened_clean`/`confirmed_clean`/`repaired` |

### Behavioral Spot-Checks (this session)

| Behavior | Command | Result | Status |
|---|---|---|---|
| Repair-script + model tests | `uv run pytest tests/scripts/test_opening_cache_repair.py tests/models/test_opening_cache_audit_models.py -q` | 78 passed | ✓ PASS |
| Cache write path / drain / submit-endpoint / backfill-flaws tests | `uv run pytest tests/services/test_eval_drain.py tests/services/test_full_eval_drain.py tests/services/test_eval_apply.py tests/test_eval_worker_endpoints.py tests/test_backfill_flaws.py -q` | 244 passed | ✓ PASS |
| `game_best_moves` re-base tests (undocumented fix, see below) | `uv run pytest tests/scripts/test_opening_cache_repair.py -q -k "PropagateBestMoves or propagate_best_moves"` | 2 passed | ✓ PASS |
| Full backend suite | `uv run pytest -n auto -q -p no:warnings` | 4612 passed, 19 skipped | ✓ PASS (matches every SUMMARY's self-reported count) |
| Type check | `uv run ty check app/ tests/ scripts/` | All checks passed | ✓ PASS |
| Lint | `uv run ruff check .` | All checks passed | ✓ PASS |
| Function-size gate | `uv run python scripts/check_function_size.py app/ --fail-over-depth 4 --fail-over-loc 200` | 1041 functions, no breaches | ✓ PASS |
| Alembic head + drift | `uv run alembic upgrade head && uv run alembic revision --autogenerate` | at `b7d4f5a60002`; empty `upgrade()`/`downgrade()` generated (deleted after) | ✓ PASS |
| Prod deploy state | `git fetch origin production && git log origin/production --oneline -1` | `6110d8631` — matches `220-08-SUMMARY.md`'s claimed Release 2 SHA | ✓ PASS |

### Probe Execution

Not applicable — this phase's verification surface is Alembic migrations + pytest, not
`scripts/*/tests/probe-*.sh` shell probes. No such probes are declared by any plan or
SUMMARY in this phase.

### Anti-Patterns Found

None. No `TBD`/`FIXME`/`XXX`/`TODO`/`HACK`/`PLACEHOLDER` markers in any file this phase
touched (`scripts/opening_cache_repair.py`, `app/services/eval_drain.py`,
`app/services/eval_apply.py`, `app/routers/eval_remote.py`,
`app/models/opening_position_eval.py`, `app/models/opening_cache_audit.py`,
`scripts/backfill_flaws.py`, `.claude/skills/db-report/SKILL.md`).

**ℹ Info — undocumented follow-up fix within phase scope, not a gap.** Commit `50dcb31b0`
(`fix(220): re-base game_best_moves candidates on the repaired evals`, 2026-09-11) and its
result-recording commit `175fcc0bf` landed directly on `main` between plan 06 and plan 07,
fixing a real second poisoning surface the original 8 plans did not anticipate:
`game_best_moves.best_cp`/`best_mate` is a copy of the position eval taken at candidate-build
time, so `propagate` alone left 1,617 stale Gem/Great candidate rows (365 rendering a spurious
badge) after `game_positions` was repaired. The fix adds a `propagate_best_moves` stage
(re-basing the candidate in the same transaction as the carrier cell, deleting it when the
corrected margin fails the inaccuracy gate), is covered by 160 new lines of tests
(`TestPropagateBestMoves`, 2/2 passing this session), was run against prod (1,617 rewritten /
828 deleted, recorded in the report's §3b), and is fully wired into the `_STAGE_ORDER`
mechanics. It has no corresponding `220-0N-PLAN.md`/`SUMMARY.md` — the phase's own
plan-tracking apparatus (multi-source coverage audit, requirements table) does not mention
it. This is a **documentation-trail gap**, not a functional one: the work is real, tested,
deployed, and directly serves the phase goal ("every game it tainted"). Flagged for
awareness; not a blocker.

### Prohibitions

Four judgment-tier prohibitions (`verification: flagged` in every owning plan's frontmatter,
per the spec-less probe ledger). This verifier's code-level judge review, run this session:

| # | Prohibition | Owning Plan | LLM-judge verdict | Evidence |
|---|---|---|---|---|
| P1 | Never delete a cache row the repair did not audit | 01 | Holds | `seed` inserts one audit row per `opening_position_eval` row before any stage runs; `orphans` only ever acts on already-audited rows (status-gated) |
| P2 | Never replace lichess-sourced evals with engine values except CACHEFIX-05's exact-old-value predicate | 03 | Holds | `propagate`'s only WHERE-clause contact is `IS NOT DISTINCT FROM` on the old cached value; no game-type filter, by design (confirmed in `scripts/opening_cache_repair.py` and `220-03-SUMMARY.md`'s explicit note that 2/226 carriers of the discovery hash were lichess games) |
| P3 | Never improve the measured after-numbers by changing what is measured | 04 | Holds | The one denominator fix found (`220-06-SUMMARY.md`: bounce-rate band divisor) corrected a computation bug to match the *already-recorded* baseline convention, not a threshold/definition/cohort move |
| P4 | Never mark a position confirmed on the strength of a single evaluation | 07 | Holds | `_partition_cache_writes`'s promote bucket requires an existing candidate row from a *different* `source_game_id`; `test_self_promotion_guarded_by_source_game_id` passing this session |

**This is a non-authoritative LLM-judge verdict per the honest-verifier protocol** — these
four items are listed in `human_verification` above and require an explicit human sign-off,
not silently absorbed into the `passed`/verified count.

### Human Verification Required

See the `human_verification` frontmatter list. Summary:

1. **db-report Check C/D visual render** — deferred from plans 02 and 07 to end-of-phase
   UAT (now). Structural content is grep-verified and passing; markdown readability/layout
   in the actually-rendered report has not been visually confirmed by a human.
2. **Judgment-tier prohibitions sign-off** — 4 items, all found to hold on code-level review
   (table above), but never resolved by a human per the flagged-verification tier they were
   authored at.
3. **Live disagreement-counter watch** — day-0 reading was 0/0 (no live Release-2 write had
   landed yet); the meaningful reading is a few days out and was explicitly left as a
   follow-up in `220-08-SUMMARY.md`.

### Gaps Summary

No blocking gaps. All 5 ROADMAP success criteria and all 12 CACHEFIX requirements are
satisfied by evidence re-verified in this session (code inspection + a live re-run of the
full test suite, type check, lint, function-size gate, and Alembic drift check — all green;
production deploy state independently confirmed via `git fetch origin production`). The
phase's own operator-recorded production evidence (14 acceptance queries, the confirmed/
candidate split, the benchmark-lane growth) is internally consistent across the 8
SUMMARY files and is cited, not re-derived, per this verification's scope.

The only reasons this is not a clean `passed` are (a) three genuinely human-shaped items
that no static check can close (a markdown visual render, an explicit judgment-tier
prohibition sign-off, and a live production signal that only exists after a few days of
traffic) and (b) one documentation-trail note (the `game_best_moves` fix has no PLAN/SUMMARY
of its own, though the work itself is sound and tested).

---

_Verified: 2026-09-11T20:15:00Z_
_Verifier: Claude (gsd-verifier)_
