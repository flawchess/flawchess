---
phase: 144
slug: user-28-a-b-validation
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-06-30
---

# Phase 144 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x |
| **Config file** | pyproject.toml |
| **Quick run command** | `uv run pytest tests/scripts/test_ab_validate_gate.py` |
| **Full suite command** | `uv run pytest -n auto` |
| **Estimated runtime** | ~quick: seconds; full: minutes |

---

## Sampling Rate

- **After every task commit:** Run the quick run command for the touched area
- **After every plan wave:** Run the full suite command
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** ~10 seconds (quick), full suite minutes

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| P01-T1 (Wave 0) | 144-01 | 1 | VALID-01, VALID-02 | T-144-01 | engine-free, read-only harness | unit (scaffold) | `uv run pytest tests/scripts/test_ab_validate_gate.py --co -q` | ❌ W0 | ⬜ pending |
| ungated bypasses gate | 144-01 | 1 | VALID-01 | T-144-01 | ungated arm never calls `apply_forcing_line_filter` | unit | `uv run pytest tests/scripts/test_ab_validate_gate.py::test_ungated_arm_bypasses_gate -x` | ❌ W0 | ⬜ pending |
| both arms same blobs | 144-01 | 1 | VALID-01 | T-144-03 | no engine/EnginePool reference | unit | `uv run pytest tests/scripts/test_ab_validate_gate.py::test_both_arms_use_same_blobs -x` | ❌ W0 | ⬜ pending |
| gated ≤ ungated | 144-01 | 1 | VALID-01 | — | gate suppresses a subset | unit | `uv run pytest tests/scripts/test_ab_validate_gate.py::test_gated_lte_ungated -x` | ❌ W0 | ⬜ pending |
| report output sections | 144-01 | 1 | VALID-02 | T-144-05 | report has all required sections | unit | `uv run pytest tests/scripts/test_ab_validate_gate.py::test_report_output -x` | ❌ W0 | ⬜ pending |
| dropped-case fields | 144-01 | 1 | VALID-02 | — | motif/FEN/PV/lichess per case | unit | `uv run pytest tests/scripts/test_ab_validate_gate.py::test_dropped_case_fields -x` | ❌ W0 | ⬜ pending |
| lichess URL encoding | 144-01 | 1 | VALID-02 | — | FEN percent-encoded, side-to-move appended | unit | `uv run pytest tests/scripts/test_ab_validate_gate.py::test_lichess_url_encodes_fen -x` | ❌ W0 | ⬜ pending |
| live report generation | 144-02 | 2 | VALID-02 | T-144-05 | committed report from dev-28 run | manual+grep | `ls reports/retag/ab-validation-*.md && grep -lq 'Dropped Cases' reports/retag/ab-validation-*.md` | ❌ W0 | ⬜ pending |
| margin commit + pointer | 144-02 | 2 | VALID-02 | T-144-04 | pointer comment references report | grep+unit | `grep -q 'Phase 144' app/services/forcing_line_gate.py && uv run pytest tests/scripts/test_ab_validate_gate.py -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/scripts/test_ab_validate_gate.py` — created in Plan 01 Task 1 BEFORE the harness; covers all 6 VALID-01/VALID-02 unit cases above.
- [ ] Test uses the session-maker injection pattern from `test_retag_flaws.py` (the model to follow) against the per-run cloned test DB — never a real `--db dev` target.
- [ ] Test reuses the `_FORCING_BLOB` / `_NON_FORCING_BLOB` fixture shapes and the committed-fixture + finally-cleanup pattern (eval-lottery isolation memory).
- [ ] No `@pytest.mark.integration` / real-dev-DB dependency in CI: the seeded session-maker test IS the integration coverage. The live dev-28 run (216 flaws) is the manual Plan 02 Task 1 step.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Hand-check of dropped cases → explicit false-negative count | VALID-02 | Requires the user's chess judgment (HUMAN-UAT) — adjudicate each dropped case via lichess deep-link as false-negative (good tag killed) vs correct drop (noise) | Open each case's lichess analysis link, mark FN vs correct; fold FN count into the A/B summary |
| Final `ONLY_MOVE_WIN_PROB_MARGIN` decision | VALID-02 | Keep 0.35 unless hand-check shows it fails — a human judgment call | Confirm 0.35 stands (record justification) or change the constant if hand-check fails it |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
