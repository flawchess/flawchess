---
phase: "259"
slug: "facepalm-first-principles-refit"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: "2026-11-21"
---

# Phase 259 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution. Source: 259-RESEARCH.md,
> "## Validation Architecture".

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (pytest-xdist, pytest-asyncio), per-worker PostgreSQL test DBs cloned from a migrated template |
| **Config file** | `pyproject.toml`, `tests/conftest.py` |
| **Quick run command** | `uv run pytest tests/services/test_line_material.py tests/services/test_facepalm_score.py -x` |
| **Full suite command** | `uv run pytest -n auto -x` |
| **Estimated runtime** | quick ~30 seconds, full suite several minutes |

---

## Sampling Rate

- **After every task commit:** Run the touched test files (quick run command or the task's own command)
- **After every plan wave:** Run `uv run pytest -n auto -x`
- **Before each squash-merge to `main`:** the full pre-merge gate from CLAUDE.md
- **Before a release:** the full serial suite once (`-n auto` green is not serial-CI green)
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 60 seconds for the quick command

---

## Per-Task Verification Map

Filled by the planner per task. Behaviours and commands to draw from (no REQ-IDs; decisions are the keys):

| Decision | Behavior | Test Type | Automated Command | File Exists |
|----------|----------|-----------|-------------------|-------------|
| D-02 | Quiet walk: long exchange neutral, static exchange at line end, desperado kept, mate-first best move, too-short NULL | unit | `uv run pytest tests/services/test_line_material.py -x` | ✅ extend |
| D-13 | 2883555:47 gives missed 0.0 | unit | `uv run pytest tests/services/test_line_material.py -x` | ❌ W0 fixture |
| D-03, D-04 | Stored scalars equal the decaying mean on quiet arrays; NULL encoding | unit | `uv run pytest tests/services/test_facepalm_material.py -x` | ✅ extend |
| D-05, D-07 | Hook writes scalars and reply probability for both sides | integration | `uv run pytest tests/services/test_maia_flaw_scoring.py -x` | ✅ extend |
| D-07 | Line mode never overwrites the reply probability; reply mode resumes | integration | `uv run pytest tests/scripts/test_backfill_maia_flaws.py tests/services/test_maia_flaw_scoring.py -x` | ✅ extend |
| D-08 | Scalar SQL and Python twin parity, NULL handling, type twin | unit + DB | `uv run pytest tests/services/test_facepalm_score.py tests/services/test_facepalm_seed.py -x` | ✅ rewrite at switch |
| D-09 | Review tool classifies rule changes by cause | unit | `uv run pytest tests/scripts/test_quiet_rule_review.py -x` | ❌ W0 |
| D-12, D-15 | Fit: fixed shape, `--check-constants` round trip, missing-row flag | unit | `uv run pytest tests/scripts/test_fit_facepalm.py tests/scripts/test_facepalm_features.py -x` | ✅ rewrite |
| D-17 | New covering index holds every score input | unit + DB | `uv run pytest tests/services/test_flaw_comparison.py -k index -x` | ✅ re-point |
| D-18 | JIT tests kept or removed with the helper | unit | `uv run pytest tests/services/test_flaw_comparison.py -k jit -x` | ✅ |
| Switch readers | Compiled SQL names the new columns | unit | `uv run pytest tests/test_query_utils.py tests/test_library_repository.py -x` | ✅ update |

### Per-task map (filled at planning, 2026-11-21)

| Task | Decisions | Type | Automated command | Status |
|------|-----------|------|-------------------|--------|
| 259-01 T1 | D-02, D-03, D-13 | unit | `uv run pytest tests/services/test_facepalm_inputs.py -x` | ⬜ |
| 259-01 T2 | D-02, D-04, D-11 | unit | `uv run pytest tests/services/test_line_material.py tests/services/test_facepalm_inputs.py -x` | ⬜ |
| 259-02 T1 | D-09, D-13 | unit + script | `uv run pytest tests/scripts/test_quiet_rule_review.py -k d13 -x` | ⬜ |
| 259-02 T2 | D-07, D-09, D-12 | unit + DB | `uv run pytest tests/scripts/test_facepalm_features.py tests/scripts/test_quiet_rule_review.py -x` | ⬜ |
| 259-03 T1 | D-09 | dev run | `uv run python scripts/blunder_check/quiet_rule_review.py --features temp/blunder-check/features-dev-259-03.tsv --out temp/blunder-check/quiet-review-dev-259-03.md` | ⬜ |
| 259-03 T2-T3 | D-09, D-14 | manual (prod, owner) | report committed; owner decision | ⬜ |
| 259-04 T1 | D-05, D-07, D-10 | integration (DB) | `uv run pytest tests/services/test_maia_flaw_scoring.py -k "material_inputs_and_reply_prob" -x` | ⬜ |
| 259-04 T2 | D-07, D-11 | integration | `uv run pytest -n auto tests/services/test_maia_flaw_scoring.py tests/scripts/test_backfill_maia_flaws.py -x` | ⬜ |
| 259-05 T1 | D-07, D-11 | integration (DB) | `uv run pytest tests/scripts/test_backfill_maia_flaws.py -k "reply_mode_fills_both_sides" -x` | ⬜ |
| 259-05 T2 | D-10, D-11 | integration | `uv run pytest -n auto tests/scripts/test_backfill_maia_flaws.py tests/services/test_maia_flaw_scoring.py -x` | ⬜ |
| 259-06 T1 | D-10, D-11 | dev run | `uv run python scripts/backfill_maia_flaws.py --db dev --status --mode reply --user-id 28` | ⬜ |
| 259-06 T2 | gate | full gate + serial suite | `uv run pytest -x` | ⬜ |
| 259-06 T3 | D-10, D-11 | manual (prod) | line log EXIT=0, reply pass launched | ⬜ |
| 259-07 T1 | D-01, D-03, D-08 | script | `uv run pytest tests/scripts/test_fit_facepalm.py -k "committed_259_features" -x` | ⬜ |
| 259-07 T2 | D-12, D-14, owner trim | unit | `uv run pytest tests/scripts/test_fit_facepalm.py tests/scripts/test_blunder_check_metrics.py tests/scripts/test_facepalm_features.py --durations=5 -x` | ⬜ |
| 259-07 T3 | open question 6 | unit (conditional) | `uv run ty check scripts/ tests/ && uv run ruff check scripts/ tests/` | ⬜ |
| 259-08 T1 | D-15 | integration (DB) | `uv run pytest tests/scripts/test_blunder_check_calibration.py -x` | ⬜ |
| 259-08 T2 | D-05 | unit | `uv run pytest -n auto tests/scripts/test_miss_labels.py tests/scripts/test_blunder_check_metrics.py tests/scripts/test_blunder_check_calibration.py -x` | ⬜ |
| 259-09 T1 | D-05, D-08 | DB | `uv run pytest tests/services/test_facepalm_seed.py -x` | ⬜ |
| 259-09 T2 | D-08, D-18, owner trim | unit + DB | `uv run pytest tests/services/test_facepalm_score.py tests/services/test_facepalm_owner_fixtures.py tests/scripts/test_fit_facepalm.py -x` | ⬜ |
| 259-09 T3 | D-11 | full suite | `uv run pytest -n auto -x` | ⬜ |
| 259-10 T1 | D-17 | unit + DB | `uv run pytest tests/scripts/test_build_facepalm_inputs_index.py tests/services/test_flaw_comparison.py -k "index" -x` | ⬜ |
| 259-10 T2 | D-05, owner trim | unit | `uv run pytest tests/services/test_facepalm_material.py tests/services/test_facepalm_inputs.py -x` | ⬜ |
| 259-11 T1 | D-11, D-17 | dev run | `uv run python scripts/build_facepalm_inputs_index.py --db dev --check-only` | ⬜ |
| 259-11 T2-T3 | D-11, D-12, D-13, D-15, D-17 | manual (prod, owner) | index build log EXIT=0; owner decision | ⬜ |
| 259-12 T1 | D-15, D-16 | script + full gate | `uv run pytest tests/scripts/test_fit_facepalm.py -k "reproduce_from_the_committed_features" -x` | ⬜ |
| 259-12 T2-T3 | D-11, D-17, D-18 | manual (prod) | deploy verified; JIT report decision line | ⬜ |
| 259-13 T1 | D-05, D-06 | integration | `uv run pytest -n auto tests/services/test_maia_flaw_scoring.py tests/scripts/test_backfill_maia_flaws.py -x` | ⬜ |
| 259-13 T2 | D-06 | unit | `uv run pytest -n auto tests/scripts/ -x` | ⬜ |
| 259-13 T3 | D-02, D-06 | unit + full suite | `uv run pytest -n auto -x` | ⬜ |
| 259-14 T1 | D-05, D-06, D-17 | DB | `uv run pytest tests/services/test_maia_flaw_scoring.py tests/test_library_router.py -k "material_inputs_and_reply_prob or facepalm" -x` | ⬜ |
| 259-14 T2 | D-18 | full suite | `uv run pytest -n auto -x` | ⬜ |
| 259-15 T1 | D-06 | dev run + serial suite | `uv run pytest -x` | ⬜ |
| 259-15 T2-T3 | D-06, D-10 | manual (owner, prod) | owner decision; prod at f3a7b9c1e259 | ⬜ |

No three consecutive executor tasks lack an automated command; the manual rows are orchestrator checkpoints.

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/services/line_material_fixtures.py` — `expected_quiet_loss` per fixture and the 2883555:47 fixture (plan 01)
- [ ] `tests/scripts/test_quiet_rule_review.py` — tests for the D-09 review tool (plan 02)
- [ ] `tests/services/facepalm_owner_fixtures.py` — reply probability and quiet scalars for the owner fixtures (plan 09)
- [ ] `tests/services/test_facepalm_score.py` — window test re-pointed to the new features TSV (plan 09, re-pinned in plan 12)

---

## Manual-Only Verifications

| Behavior | Decision | Why Manual | Test Instructions |
|----------|----------|------------|-------------------|
| Rule review report confirmed | D-09 | Owner judgement on before / after positions | Owner reads the report and confirms the rule |
| Prod line and reply passes complete | D-10, D-11 | Operator runs on prod | Status counts and the readiness gate before the switch |
| Concurrent index build valid | D-17 | Operator step on prod | `indisvalid` is true for the new index |
| Model and cuts confirmed | D-15 | Owner checkpoint | Owner confirms the fit and sets `FACEPALM_SCORE_MIN` / `FACEPALM_STATS_MIN` |
| JIT on vs off | D-18 | Needs prod data volume | EXPLAIN ANALYZE on user 95 with JIT on and off |
| Array column drop | D-06 | One-way, human-gated | Owner approves after no reader is left |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
