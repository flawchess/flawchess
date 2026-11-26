---
phase: "256"
slug: "facepalm-refit-material-aggregated-over-depths"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: true) (#2117)
status: validated
nyquist_compliant: false
wave_0_complete: true
created: "2026-11-16"
---

# Phase 256 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Source: `256-RESEARCH.md` § Validation Architecture.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (xdist), per-worker cloned PostgreSQL DB (`tests/conftest.py`) |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `uv run pytest -n auto tests/services/test_facepalm_score.py tests/services/test_facepalm_material.py tests/services/test_facepalm_owner_fixtures.py tests/scripts/test_fit_facepalm.py tests/scripts/test_decaying_mean.py` |
| **Full suite command** | `uv run pytest -n auto -x` |
| **Estimated runtime** | ~25 seconds quick (today's four existing files: 170 passed in 23 s) |

---

## Sampling Rate

- **After every task commit:** Run the quick run command (plus `uv run ty check app/ tests/ scripts/`)
- **After every plan wave:** Run `uv run pytest -n auto -x`. One exception: wave 1 (plan 01) removes
  the scalar `FacepalmFacts` parameters and wave 2 (plan 02) moves the script-side callers, so after
  wave 1 run `uv run pytest -n auto -x --ignore=tests/scripts/test_blunder_check_calibration.py
  --ignore=tests/scripts/test_fit_facepalm.py`; the full suite and `uv run ty check app/ tests/ scripts/`
  are green again at the end of wave 2
- **Before `/gsd-verify-work`:** Full CLAUDE.md pre-merge gate must be green, including
  `uv run python scripts/check_function_size.py app/ --fail-over-depth 4`
- **Max feedback latency:** ~30 seconds
- **Gap-closure proof:** the WR-01 and WR-03 tests are proven by reverting each fix and watching the test fail

---

## Per-Task Verification Map

Task IDs filled in by the planner (2026-11-16), renumbered the same day after the plan check
split the former plans 01 and 04 (eight plans now). `256-PP-TN` = plan PP, task N. Each wave-0 gap
is created by the task that first needs it (tracer-first: the test lands with the code it pins).

| Task ID | Decision | Behavior | Test Type | Automated Command | File Exists | Status |
|---------|----------|----------|-----------|-------------------|-------------|--------|
| 256-01-T1 | D-03 | Every input unscored when played[3] unknown and no mate within 3 | unit | `uv run pytest tests/services/test_facepalm_material.py -k coverage` | ✅ | ✅ green |
| 256-01-T1, 256-03-T2 | D-06 | Series, decaying mean (01-T1), first stable (03-T2), mate rules, odd slots only, NULL skipping | unit | `uv run pytest tests/services/test_facepalm_material.py` | ✅ | ✅ green |
| 256-01-T1, 256-03-T2 | D-06 | SQL twin parity: decaying-mean models in the existing grid (01-T1); aggregate grid over every input x gate x spread form (03-T2) | integration (DB) | `uv run pytest tests/services/test_facepalm_score.py -k parity` | ✅ | ✅ green |
| 256-01-T1, 256-03-T2 | D-06 | `facepalm_expr` over seeded stored facts equals the Python twin for aggregate models | integration (DB) | `uv run pytest tests/services/test_facepalm_score.py -k stored_facts` | ✅ | ✅ green |
| 256-01-T1 | D-06 | Reader-test seed helper probes the twin with the array it seeds | integration (DB) | `uv run pytest tests/services/test_facepalm_seed.py` | ✅ | ✅ green |
| 256-02-T1 | D-06 / refactor | Fit loader carries both nine-slot arrays; the Phase 254 constants still reproduce from the 2026-11-15 table | script | `uv run pytest tests/scripts/test_fit_facepalm.py::test_fit_loads_both_schemas` and `--check-constants` on the 2026-11-15 TSV | ✅ | ✅ green |
| 256-02-T2 | D-13 / calibration | `BlunderRecord` arrays, cache v4 refuses v3; whole tree type-checks | unit | `uv run pytest tests/scripts/test_blunder_check_calibration.py` and `uv run ty check app/ tests/ scripts/` | ✅ | ✅ green |
| 256-03-T1 | D-04 | NULL best prob on a no-loss gated row: None in both twins and through facepalm_expr; losing row and additive form unchanged; revert run fails | unit + DB | `uv run pytest tests/services/test_facepalm_score.py -k best_prob` | ✅ | ✅ green |
| 256-04-T2 | D-05 / D-12 | Per-spec exclusion and counts; NULL-spread pure miss kept under gated form; revert run fails | unit | `uv run pytest tests/scripts/test_fit_facepalm.py -k exclusion` | ✅ | ✅ green |
| 256-05-T1 | D-07 / D-09 | Input choice by AUC, share, then preference order; three-input comparison | unit | `uv run pytest tests/scripts/test_fit_facepalm.py -k material_input` | ✅ | ✅ green |
| 256-05-T2 | D-10 / D-13 | Constants block is the chosen input's final; chosen-model section states assumptions A1 / A2 / A4 | unit | `uv run pytest tests/scripts/test_fit_facepalm.py -k "chosen_input_final or assumptions"` | ✅ | ✅ green |
| 256-06-T1 | D-08 | Hold-out pipeline on sets 1-7, scored on set 8, per input; disagreement flag | unit | `uv run pytest tests/scripts/test_fit_facepalm.py -k holdout` | ✅ | ✅ green |
| 256-01-T1, 256-03-T2, 256-04-T2 | D-11 | `loses()` semantics (01-T1), gate parity in both twins (03-T2), stage-2 gate candidates (04-T2) | unit + DB | `uv run pytest tests/services/test_facepalm_score.py tests/services/test_facepalm_material.py tests/scripts/test_fit_facepalm.py -k gate` | ✅ | ✅ green |
| 256-01-T1 | 254 D-12 | Defaults reproduce the Phase 250 score | unit | `uv run pytest tests/services/test_facepalm_score.py::test_new_twin_reproduces_phase_250_score` | ✅ | ✅ green |
| 256-04-T1 | refactor | Forced depth_3 fit reproduces the 2026-11-15 constants | script | `uv run pytest tests/scripts/test_fit_facepalm.py -k 2026_11_15` | ✅ | ✅ green |
| 256-08-T1 | D-10 | Shipped constants reproduce from the new committed TSV (`--check-constants` exit 0) | script | `uv run pytest tests/scripts/test_fit_facepalm.py -k refit_features` | ✅ | ✅ green |
| 256-01-T2, 256-08-T2 | D-13 | Owner fixtures carry arrays (01-T2); outcome under the new model pinned (08-T2) | unit + DB | `uv run pytest tests/services/test_facepalm_owner_fixtures.py` | ✅ | ✅ green |
| 256-06-T2 | D-13 | Owner section: commented rows, extra rows, pure-miss pass rates | unit | `uv run pytest tests/scripts/test_fit_facepalm.py -k owner` | ✅ | ✅ green |
| 256-07-T1 | D-01 | Set 8 fully labelled before the refit (exit 1 on 2026-11-16) | script | the label check in 256-07-PLAN Task 1 `<verify>` | ✅ (one-liner) | ✅ green |
| 256-08-T2 | D-13 | Window 14 unscored or below FACEPALM_SCORE_MIN, read from the new TSV | unit | `uv run pytest tests/services/test_facepalm_score.py -k window_14` | ✅ | ✅ green |
| 256-03-T3 | parity | `decaying_mean.py` (sampler) equals the app aggregate where definitions agree | unit | `uv run pytest tests/scripts/test_decaying_mean.py` | ✅ | ✅ green |
| 256-08-T3 | D-15 | Full CLAUDE.md pre-merge gate, changelog bullet | gate | pre-merge gate commands (CLAUDE.md) | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] `tests/services/test_facepalm_material.py` — series, aggregates, mate rules, the queen-trade best line
      `(1, 1, 1, 1, 10, 10, 1, 1, 1)`, the `-3, -3, 0, ...` early-swing row, arrays that stop at depth 3 / 5,
      garbage in even slots
- [x] Parity grid for aggregate models in `tests/services/test_facepalm_score.py` (a separate grid with varied
      arrays, not the existing 6,048-row grid multiplied by every input and gate)
- [x] `PHASE_254_MODEL` in `tests/facepalm_models.py` and the 2026-11-15 reproduction test
- [x] Synthetic facts writer in `tests/scripts/test_fit_facepalm.py` fills all nine slots (varied across depths)
      and set 8

---

## Manual-Only Verifications

| Behavior | Decision | Why Manual | Test Instructions |
|----------|----------|------------|-------------------|
| Set 8 is fully labelled before the refit | D-01 | The owner labels the 60 blind rows | Precondition check on `reports/blunder-check/facepalm-labels.tsv`; stop while any set 8 row is unlabelled |
| Chosen material input and `FACEPALM_SCORE_MIN` | D-08, D-13 | Owner decision at a blocking checkpoint | Owner reads the fit report (per-candidate CV and set 8 hold-out, fixtures, cuts 50% to 70%) and confirms |
| Prod feature pull and calibration re-run | D-02 | Needs the prod tunnel; subagents have no prod access | Orchestrator runs the commands in `256-RESEARCH.md` through `bin/prod_db_tunnel.sh` |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 30s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** validated 2026-11-16 (all 20 automated rows run green after wave 8; D-01, D-02, D-08/D-13 manual items done in plan 256-07)

## Validation Audit 2026-11-16

| Metric | Count |
|---|---|
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |
