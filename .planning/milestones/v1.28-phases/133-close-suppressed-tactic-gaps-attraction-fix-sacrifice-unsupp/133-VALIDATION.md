---
phase: 133
slug: close-suppressed-tactic-gaps-attraction-fix-sacrifice-unsuppress-mate-geometry-trapped-piece-fixtures
status: approved
nyquist_compliant: true
wave_0_complete: false
created: 2026-06-23
---

# Phase 133 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x (`uv run pytest`) |
| **Config file** | `pyproject.toml` / `pytest.ini` (existing) |
| **Quick run command** | `uv run pytest tests/scripts/tagger/test_detector_precision.py -s` |
| **Family run command** | `uv run pytest tests/services/test_tactic_comparison_service.py -k test_family_mapping` |
| **Full suite command** | `uv run pytest -n auto -x` |
| **Estimated runtime** | quick ~20–40s · full suite per CLAUDE.md gate |

All infrastructure exists. The CC0 puzzle harness scores every motif (TRAIN floor-gated, TEST held-out) on every run; the family test asserts the family count. **No Wave 0 setup needed.**

---

## Sampling Rate

- **After every task commit:** Run the quick harness command (re-measures all motif precision/recall).
- **After every plan wave:** Run the full suite (`uv run pytest -n auto -x`) + family test.
- **Before `/gsd-verify-work`:** Full backend suite + frontend lint/test green (CLAUDE.md pre-merge gate).
- **Max feedback latency:** ~40s for the per-task harness signal.

---

## Per-Task Verification Map

| Task area | Wave | Requirement | Test Type | Automated Command | Status |
|-----------|------|-------------|-----------|-------------------|--------|
| Attraction off-by-one fix (`boards[k+2]`→`[k+3]`) | 1 | D-08 precision floor | unit/harness | `uv run pytest tests/scripts/tagger/test_detector_precision.py -s` | ⬜ pending |
| Arabian-mate cook geometry port | 1 | floor passes, removed from SUPPRESSED | unit/harness | harness | ⬜ pending |
| Boden-mate cook geometry port | 1 | floor passes, removed from SUPPRESSED | unit/harness | harness | ⬜ pending |
| Dovetail-mate cook geometry port (was only-FP) | 1 | floor passes, removed from SUPPRESSED | unit/harness | harness | ⬜ pending |
| Unsuppress attraction + sacrifice (floor + family + frontend + family-count test) | 2 | family count == 17, chips surface | unit | `uv run pytest tests/services/test_tactic_comparison_service.py -k test_family_mapping` | ⬜ pending |
| Correct stale docstrings (attraction "PV depth", sacrifice "never wins") | 2 | manual review | manual | n/a | ⬜ pending |
| Regenerate tactic-tagger report | 2 | report reflects shipped motifs | manual/script | `/tactic-tagger-report` | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

*Existing infrastructure covers all phase requirements.* The harness (`tests/scripts/tagger/test_detector_precision.py`) already scores every motif on every run; the family test (`test_family_mapping_ten_families`) already asserts the count.

---

## Manual-Only Verifications

| Behavior | Why Manual | Test Instructions |
|----------|------------|-------------------|
| Stale docstring corrections in `precision_floors.py` | Prose accuracy, not behavior | Read the attraction (Phase 132-04) and sacrifice docstrings; confirm they no longer claim "PV depth limit" / "never wins single-winner dispatch". |
| Tactic-tagger report regeneration | Report is a generated artifact | Run `/tactic-tagger-report`; confirm attraction/sacrifice/arabian/boden/dovetail show `shipped` with their measured precision. |
| Frontend tactic chip surfacing for new families | Visual | Confirm attraction + sacrifice appear in the "advanced" `TACTIC_GROUPS` section (built via `npm run build`/`tsc -b` per CLAUDE.md). |

---

## Validation Sign-Off

- [ ] All tasks have automated verify (harness/family test) or are explicit manual-only items above
- [ ] Sampling continuity: harness runs after every task commit (no 3 consecutive tasks without automated verify)
- [ ] No Wave 0 gaps (existing infra)
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter at plan-checker pass

**Approval:** pending
