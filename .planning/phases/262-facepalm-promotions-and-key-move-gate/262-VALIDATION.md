---
phase: "262"
slug: "facepalm-promotions-and-key-move-gate"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: "2026-11-23"
---

# Phase 262 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Source: `262-RESEARCH.md` § Validation Architecture.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest with xdist (repo pin) |
| **Config file** | `pyproject.toml` (`addopts = "--ignore=tests/scripts/benchmarks --ignore=tests/scripts/tagger"`) |
| **Quick run command** | `uv run pytest tests/services/test_line_material.py tests/services/test_facepalm_inputs.py tests/services/test_facepalm_score.py tests/services/test_facepalm_owner_fixtures.py tests/services/test_facepalm_zones.py tests/scripts/test_fit_facepalm.py tests/scripts/test_facepalm_features.py tests/scripts/test_caught_rate.py -n 4 -x` |
| **Full suite command** | `uv run pytest -n auto -x` |
| **Estimated runtime** | ~13 seconds (quick), full suite a few minutes |

---

## Sampling Rate

- **After every task commit:** Run the quick run command (or the subset for the touched module)
- **After every plan wave:** Run `uv run pytest -n auto -x`
- **Before `/gsd-verify-work`:** Full suite must be green, plus the CLAUDE.md pre-merge gate before the squash-merge
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

Task IDs are `<plan>-T<task>` (for example 262-01-T2 is Task 2 of 262-01-PLAN.md).

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 262-01-T1 | 01 | 1 | D-01 (tracer: opponent queen promotion stores the capped pair) | T-262-01 | tokens parsed by `_parse_move`, never raise | unit | `uv run pytest tests/services/test_facepalm_inputs.py -x` | ✅ extend | ⬜ pending |
| 262-01-T2 | 01 | 1 | D-01 (promotion gain, walk through recapture, line ending on promotion, capture-promotion inside the exchange, four fixture values), D-03 (freshly promoted piece captured on its square counts) | T-262-02 | per-depth clip to 5 unchanged | unit | `uv run pytest tests/services/test_line_material.py -x` and `-k desperado` | ✅ extend | ⬜ pending |
| 262-01-T3 | 01 | 1 | D-01 (stored pair for the cap examples), D-02 (cap and floor constants unchanged) | — | N/A | unit | `uv run pytest tests/services/test_facepalm_inputs.py tests/services/test_facepalm_score.py -k "promotion or write_time_material_rule_is_pinned or known_d04" -x` | ✅ | ⬜ pending |
| 262-02-T1 | 02 | 1 | D-04 (shared condition, mixed row reads the best-move term, NULL rules, SQL / Python parity incl. a mixed stored row) | T-262-03 | twins cannot disagree | unit + DB | `uv run pytest tests/services/test_facepalm_score.py -x` | ✅ extend | ⬜ pending |
| 262-02-T2 | 02 | 1 | D-04 (fit design row, exclusions and scorer follow the gate; `--gate loss` reproduces the Phase 259 constants) | — | N/A | unit | `uv run pytest tests/scripts/test_fit_facepalm.py -x` | ✅ extend | ⬜ pending |
| 262-02-T3 | 02 | 1 | D-04 (features NULL-input count, reply-status residues) | T-262-04 | same covering-index columns | unit + DB | `uv run pytest tests/scripts/test_facepalm_features.py -k null_score_input -x` and `tests/scripts/test_backfill_maia_flaws.py -k reply_status` | ✅ extend | ⬜ pending |
| 262-03-T1 | 03 | 2 | D-01 (refit inputs recomputed offline from the raw lines, Phase 259 pair kept) | T-262-05 | old pair copied verbatim | unit | `uv run pytest tests/scripts/test_refresh_features_material.py -x` | ❌ W0 (created by this task) | ⬜ pending |
| 262-03-T2 | 03 | 2 | D-05 (old-gate reference line), 259 D-12 (shipped baseline = Phase 259 shape) | — | N/A | unit | `uv run pytest tests/scripts/test_fit_facepalm.py -k "old_gate or alternatives or shipped_baseline or changed_inputs" -x` | ❌ W0 (tests added by this task) | ⬜ pending |
| 262-03-T3 | 03 | 2 | Refit run (new features TSV, fit report, byte-reproducible) | T-262-06 | committed, reproducible inputs | offline run | `cmp` of the newest fit report with a re-run | ❌ W0 (TSV created by this task) | ⬜ pending |
| 262-04-T1 | 04 | 2 | D-06 / D-07 (tracer: candidate query, guarded update, undo log, report, re-run 0) | T-262-07 | pass updates only promotion rows, only when stored values still match | DB integration | `uv run pytest tests/scripts/test_backfill_promotion_material.py -x` | ❌ W0 (created by this task) | ⬜ pending |
| 262-04-T2 | 04 | 2 | D-07 (every token place, NULL rows, 4-byte-float-only difference, guard miss, sample check exit 3) | T-262-07, T-262-08, T-262-10 | one connection, all-or-nothing pages | DB integration | `uv run pytest tests/scripts/test_backfill_promotion_material.py -x` | ✅ (after T1) | ⬜ pending |
| 262-04-T3 | 04 | 2 | D-07 dev rehearsal (dry run, real run, re-run 0) | T-262-09 | URL never printed, undo log in temp/ | operator smoke | `uv run python scripts/backfill_promotion_material.py --db dev --dry-run --report-dir temp/promotion-pass` | ✅ (after T1) | ⬜ pending |
| 262-05-T1 | 05 | 3 | Checkpoint view (refit_shift on dev) | T-262-12 | read-only, one connection | operator smoke | `uv run python scripts/blunder_check/refit_shift.py --db dev --mod 1 --out temp/promotion-pass/refit-shift-dev.md` | ❌ W0 (created by this task) | ⬜ pending |
| 262-05-T2 | 05 | 3 | D-04 (refit_shift version scoring, unscored rows), spike probes removed | T-262-11 | no user ids in the report | unit | `uv run pytest tests/scripts/test_refit_shift.py -x` | ❌ W0 (created by this task) | ⬜ pending |
| 262-05-T3 | 05 | 3 | Caught-rate split by session start, `--rescore`; D-08 (bands unchanged, docstring note) | T-262-13 | snapshots never rewritten | unit | `uv run pytest tests/scripts/test_caught_rate.py tests/services/test_facepalm_zones.py -x` | ✅ extend | ⬜ pending |
| 262-06-T1 | 06 | 4 | Checkpoint chain on dev with candidate constants, restored | T-262-14 | no candidate constant left behind | operator smoke | `git diff --quiet -- app/services/blunder_check_rules.py` | ✅ | ⬜ pending |
| 262-06-T2 | 06 | 4 | Prod facts (calibration, refit_shift, rescored caught rate, D-04 unscored count, EXPLAIN index-only) | T-262-15 | one read-only connection per step | manual (orchestrator, prod) | `grep -c "Index Only Scan using ix_game_flaws_facepalm_inputs" reports/blunder-check/facepalm-explain-262.md` | ❌ (report created by this task) | ⬜ pending |
| 262-06-T3 | 06 | 4 | 259 D-15 owner decision (model, cuts, hard-to-catch cut) | T-262-16 | blocking human | manual (owner) | — | — | ⬜ pending |
| 262-07-T1 | 07 | 5 | Constants (`--check-constants` reproduces the pasted constants), cuts, frontend coupling | T-262-19 | frontend cutoff pinned to the stats cut | unit | `uv run pytest tests/scripts/test_fit_facepalm.py -k reproduce_from_the_committed_features -x` | ✅ repoint | ⬜ pending |
| 262-07-T2 | 07 | 5 | Changelog, full pre-merge gate, serial suite | — | N/A | gate | `uv run pytest -x` (plus the CLAUDE.md gate) | ✅ | ⬜ pending |
| 262-07-T3 | 07 | 5 | D-06 / D-07 prod: dry run, deploy, pass, re-run 0, caught-rate switch | T-262-17, T-262-18, T-262-20, T-262-21 | guarded, logged, idempotent prod write | manual (orchestrator, prod) | `grep -c "^EXIT=0" temp/promotion-pass/prod-run.log` | — | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/scripts/test_backfill_promotion_material.py` (or the chosen script name): seeded games with a promotion token in each of the three places, a row without a token, a stored-NULL row, a 4-byte-float-only difference that must not count, a concurrent rewrite (262-04-T1, 262-04-T2)
- [ ] Fit-report test for the D-05 old-gate line and the redefined shipped baseline (262-03-T2)
- [ ] New features TSV under `reports/blunder-check/` (input of the `--check-constants` test) (262-03-T3)
- [ ] `tests/scripts/test_refresh_features_material.py` (262-03-T1) and `tests/scripts/test_refit_shift.py` (262-05-T2)

Each Wave 0 item is created by the task that first needs it (TDD inside the task), so no separate Wave 0 plan exists.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Owner confirms the model, `FACEPALM_SCORE_MIN`, `FACEPALM_STATS_MIN` and the spot-check rows | 259 D-15, ROADMAP | owner judgement, blocking checkpoint | Review the fit report and the about 20 rows that newly pass 0.7 |
| Dev rehearsal of the pass | D-07 | operator smoke on the dev DB (262-04-T3, executor-runnable) | `uv run python scripts/backfill_promotion_material.py --db dev --dry-run --report-dir temp/promotion-pass`; expect about 624 rows that would change and 0 mismatches in the sample without a token, then the real run and a re-run with 0 |
| Index-only scan under the new gate on prod | Claude's discretion (index) | needs prod, run by the orchestrator over the tunnel | EXPLAIN of the score expression on prod before the release, see RESEARCH Finding 6 |
| Prod dry run, then the pass | D-06, D-07 | prod operator run after the deploy | Dry run first, compare with the dev ratio, then the real run on one connection |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
