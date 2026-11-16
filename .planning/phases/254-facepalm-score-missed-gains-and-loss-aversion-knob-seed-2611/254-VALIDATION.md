---
phase: "254"
slug: "facepalm-score-missed-gains-and-loss-aversion-knob-seed-2611"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: true) (#2117)
status: validated
nyquist_compliant: true
wave_0_complete: true
created: "2026-11-14"
---

# Phase 254 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Source: `254-RESEARCH.md` § Validation Architecture.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (+ pytest-xdist; async DB tests via the project's `test_engine` fixtures) |
| **Config file** | `pyproject.toml` / `tests/conftest.py` (per-session cloned Postgres DB) |
| **Quick run command** | `uv run pytest tests/services/test_facepalm_score.py tests/services/test_line_material.py -x` |
| **Full suite command** | `uv run pytest -n auto -x` |
| **Estimated runtime** | ~12 seconds quick; full suite several minutes |

---

## Sampling Rate

- **After every task commit:** Run the quick run command plus the touched module's own test file
- **After every plan wave:** Run `uv run pytest -n auto -x`
- **Before `/gsd-verify-work`:** Full suite must be green; full pre-merge gate (CLAUDE.md) before each squash-merge (R1, R2, refit, drop). Run the serial suite before a release (serial CI can expose isolation bugs `-n auto` hides)
- **Max feedback latency:** 30 seconds (quick command)

---

## Per-Task Verification Map

Task IDs are `{plan}-T{n}` from the 254-NN-PLAN.md files (planned 2026-11-14; revised the same day after plan check:
plans 01, 02, 08 and 13 were split into 01 + 15, 02 + 16, 08 + 18 and 13 + 17, and the R2 code plans run one after
another, 08 then 18 then 09).

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 254-15-T1, 254-15-T2 | 15 | 2 | D-01 | T-254-02 | SQL twin equals Python twin for every model shape, lambda in {0, 0.5, 1}, NULLs in every input | DB unit | `uv run pytest tests/services/test_facepalm_score.py -q` | ✅ (extend) | ✅ green |
| 254-18-T1 | 18 | 8 | D-01 | T-254-23 | Chip and filter agree for every returned row (facts grid) | DB integration | `uv run pytest tests/repositories/test_library_repository.py tests/test_library_repository.py tests/test_query_utils.py tests/test_library_router.py -n auto -q -k facepalm` | ✅ (rewrite seeds) | ✅ green |
| 254-15-T1 | 15 | 2 | D-01 / D-12 | T-254-02 | Pre-refit model reproduces the Phase 250 score on a grid (frozen old formula) | unit | `uv run pytest tests/services/test_facepalm_score.py -q -k reproduces` | ✅ | ✅ green |
| 254-02-T2 | 02 | 3 | D-01 | T-254-23 | Facts seeded for a target score read back that target through facepalm_expr (band-edge margins) | DB | `uv run pytest tests/services/test_facepalm_seed.py -q` | ✅ | ✅ green |
| 254-13-T1, 254-13-T2 | 13 | 13 | D-02 / D-19 | T-254-44 | Hook and backfill no longer write the stored score or line-loss keys; scored count computed in memory; legacy column mapping gone | unit + DB | `uv run pytest tests/services/test_maia_flaw_scoring.py tests/services/test_maia_flaw_stats.py tests/services/test_line_material.py tests/scripts/test_backfill_maia_flaws.py -n auto -q` | ✅ (extend) | ✅ green |
| 254-17-T1 | 17 | 14 | D-02 / D-19 | T-254-37 | No reader or writer of the dropped columns left in app/, every script or tests/ before the migration (gates G1 and G2 print 0) | grep gate | `grep -rnE "GameFlaw\.(facepalm_score\|line_loss_[0-9])\|(\bf\|\bgf\|game_flaws)\.(facepalm_score\|line_loss_[0-9])\|facepalm_score IS (NOT )?NULL" app scripts tests --include='*.py' \| wc -l` (and G2 in 254-17-PLAN.md) | ✅ (gate) | ✅ green |
| 254-17-T2 | 17 | 14 | D-19 | T-254-37 | Model lacks the six dropped columns; dev round trip; full suite and script smoke runs on the dropped schema | unit + DB | `uv run pytest -n auto -x` | ✅ (extend) | ✅ green |
| 254-08-T1, 254-18-T1 | 08, 18 | 7, 8 | D-03 / D-04 | T-254-24, T-254-25 | Drill uses the drill lambda, library uses the library lambda (distinct constants); own pick keeps the flaw_owner_id pin | DB integration | `uv run pytest tests/repositories/test_blunder_check_repository.py tests/test_library_router.py -n auto -q` | ✅ (extend) | ✅ green |
| 254-15-T1 | 15 | 2 | D-05 / D-18 | T-254-02 | D-05 table cases: loss / missed derivation incl. negative missed, NULLs, mates | unit | `uv run pytest tests/services/test_facepalm_score.py -q -k "d05 or missed"` | ✅ | ✅ green |
| 254-04-T2 | 04 | 3 | D-06 / D-07 / D-08 | T-254-12 | Fit stages pick deterministically; zero-coefficient inputs omitted; `--check-constants` covers selectors | unit (synthetic TSV) | `uv run pytest tests/scripts/test_fit_facepalm.py tests/scripts/test_blunder_check_metrics.py -n auto -q` | ✅ (extend) | ✅ green |
| 254-16-T2, 254-03-T1 | 16, 03 | 4, 5 | D-08 | T-254-06 | Hook writes best prob + pre spread from the existing policy call (call count unchanged); `pre` mode writes only its keys and stamp | DB | `uv run pytest tests/services/test_maia_flaw_scoring.py tests/scripts/test_backfill_maia_flaws.py -n auto -q` | ✅ (extend) | ✅ green |
| 254-01-T1, 254-01-T2, 254-02-T1 | 01, 02 | 1, 3 | D-09 / D-17 | T-254-01, T-254-07 | Arrays: slot N == -loss_at(N) on all 250 fixtures; best-line facts; opponent mate settles; mate by first move = ply 0; CHECK rejects bad shapes | unit + DB | `uv run pytest tests/services/test_line_material.py tests/services/test_facepalm_score.py -q` | ✅ (extend) | ✅ green |
| 254-03-T2 | 03 | 5 | D-09 / D-17 | T-254-08, T-254-09 | Copy tool: sign flip, NULL rows untouched, idempotent, resumable; parity check | DB | `uv run pytest tests/scripts/test_copy_line_material.py -q` | removed with the script in plans 13 / 17 | ✅ green until R2; retired with the drop (the copy has no source column left) |
| 254-16-T1 | 16 | 4 | D-09 | T-254-05 | Fingerprint includes pv at the flaw ply: a changed best line blocks the write | DB | `uv run pytest tests/services/test_maia_flaw_scoring.py -q -k fingerprint` | ✅ (extend) | ✅ green |
| 254-04-T2, 254-09-T2 | 04, 09 | 3, 9 | D-13 | T-254-34 | Report sections exist (cuts x material type, pool per band own / foreign) | unit | `uv run pytest tests/scripts/test_fit_facepalm.py tests/scripts/test_blunder_check_calibration.py -n auto -q` | ✅ (extend) | ✅ green |
| 254-05-T1, 254-05-T2 | 05 | 5 | D-14 / D-15 | T-254-14, T-254-15 | Sampler filters (rating < 2000, both lines >= 3 plies or mate, used games excluded), stratification, blind output has no values | unit (fake rows) | `uv run pytest tests/scripts/test_miss_labels.py -q` | ✅ | ✅ green |
| 254-04-T1 | 04 | 3 | D-16 | T-254-11 | Features script reads pv at the flaw ply, outputs new columns; legacy TSV still loads | unit | `uv run pytest tests/scripts/test_facepalm_features.py tests/scripts/test_fit_facepalm.py -n auto -q` | ✅ (extend) | ✅ green |
| 254-04-T3, 254-12-T1 | 04, 12 | 3, 12 | Specifics | T-254-35 | Window 14 and fixtures 817357/24, 820181/65 pinned at their fitted scores. Known shortfall, owner accepted 2026-11-15: the fixtures score 0.146 / 0.154 (below the cut) and Window 14 is unscored (line too short) | unit + DB | `uv run pytest tests/services/test_facepalm_owner_fixtures.py tests/services/test_facepalm_score.py -n auto -q` | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] Facts-based seeding helper (replaces `facepalm_score=` seeds in 9 test files, 30 call sites): `tests/facepalm_seed.py` in 254-02-T2, adopted by 254-08, 254-18 and 254-09
- [x] `tests/services/test_facepalm_score.py` — reproduction test, D-05 cases, extended parity grid: 254-15-T1, 254-15-T2
- [x] `tests/scripts/test_miss_labels.py` — new sampler script: 254-05-T1
- [x] Copy-tool tests in `tests/scripts/test_copy_line_material.py` (separate script, not a backfill mode): 254-03-T2
- [x] Owner fixtures 817357/24 and 820181/65 as embedded FEN + lines (no DB dependency): 254-01-T1 (lines), 254-04-T3 (score inputs)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| About 50 blind miss labels | D-14 | Owner judgement is the ground truth | Owner labels the sampler's blind output; TSV committed under `reports/blunder-check/` |
| `FACEPALM_SCORE_MIN` choice | D-13 | Owner decision at a blocking checkpoint | Owner reads the fit report (fair / unfair at several cuts by loss / miss type, pool per rating band) and sets the cut |
| Prod passes (copy, `pre` Maia pass, line pass) | D-09, D-08, D-12 | Long prod runs, orchestrator-started, detached | Orchestrator runs them from the prod-run worktree (`.claude/worktrees/phase-254-prod`, detached at the deployed commit; branch and checkout map in 254-06-PLAN.md), checks coverage counts and prod connection headroom |
| Expression matches stored column on prod before the drop | D-02 | Prod read-only check gating a one-way migration | Orchestrator compares expression vs stored `facepalm_score` within float4 precision |
| R2 post-deploy parity failure rolls back | D-01, D-12 | Prod deploy action | Plan 10 Task 3 step 5: a failed parity check (or a reader-caused Sentry issue) reverts the code-only R2 squash commit, deploys the revert, confirms the server SHA, and stops before plan 11 |
| Commits land on the branch the map names | D-12 | Orchestrator git actions across releases | After each cycle open / close (plans 06, 10, 11, 12, 14), `git branch --show-current` in the main checkout matches the branch and checkout map in 254-06-PLAN.md; executor plans 08, 18, 09, 10, 12, 13, 17, 14 assert it in a task precondition |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 30s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** validated 2026-11-16 (all automated commands green on main at 234b1a8a4: 724 passed; grep gate prints 0)

## Validation Audit 2026-11-16

| Metric | Count |
|---|---|
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |
