---
phase: 124
slug: schema-tactic-detector
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-17
---

# Phase 124 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x (async, per-run PostgreSQL via xdist) |
| **Config file** | `pyproject.toml` (`[tool.pytest.ini_options]`), `tests/conftest.py` |
| **Quick run command** | `uv run pytest tests/test_tactic_detector.py` |
| **Full suite command** | `uv run pytest -n auto` |
| **Estimated runtime** | ~detector unit tests <10s; full suite ~minutes |

---

## Sampling Rate

- **After every task commit:** Run the quick command for the touched module
- **After every plan wave:** Run `uv run pytest -n auto` (full backend suite)
- **Before `/gsd-verify-work`:** Full suite + `uv run ty check app/ tests/` must be green
- **Max feedback latency:** ~10 seconds for detector unit tests

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| (planner fills) | — | — | TACSCH-01/02, TACDET-01..04 | — | N/A | unit | `uv run pytest tests/test_tactic_detector.py` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_tactic_detector.py` — per-motif fixture set (~10–15 positives/motif from prod flaws) + shared hard-negative set
- [ ] `tests/fixtures/` — FEN/PV fixture data for hand-labeled motifs (format = Claude's discretion)
- [ ] Precision-measurement harness asserting ≥90% (core 8) / ≥95% (tier-3 + named-mate) per-motif precision; recall NOT gated

*Existing pytest infrastructure (per-run DB, conftest) covers integration tests against `classify_game_flaws`.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Hand-labeling fixture positives/negatives | TACDET-03 | Ground-truth labels come from human inspection of prod flaws, not from cook.py output | Inspect `game_flaws` + `game_positions.pv` rows; label motif by eye |

*All detector logic + the precision bar are automated once fixtures are labeled.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
