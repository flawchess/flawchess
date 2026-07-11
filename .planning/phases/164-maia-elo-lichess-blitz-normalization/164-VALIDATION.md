---
phase: 164
slug: maia-elo-lichess-blitz-normalization
status: approved
nyquist_compliant: true
wave_0_complete: true
created: 2026-07-11
---

# Phase 164 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x (backend) · vitest (frontend) |
| **Config file** | `pyproject.toml` (backend) · `frontend/vitest.config.ts` |
| **Quick run command** | `uv run pytest tests/test_chesscom_to_lichess.py` |
| **Full suite command** | `uv run pytest -n auto` then `( cd frontend && npm test -- --run )` |
| **Estimated runtime** | ~5s (unit) · ~2min (full backend) |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_chesscom_to_lichess.py`
- **After every plan wave:** Run `uv run pytest -n auto` (backend) / `( cd frontend && npm test -- --run )` (frontend wave)
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds (unit tier)

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 164-01-* | 01 | 1 | SEED-093 | — | N/A (pure conversion math, no external input) | unit | `uv run pytest tests/test_chesscom_to_lichess.py` | ✅ | ⬜ pending |
| 164-02-* | 02 | 2 | SEED-093 | — | N/A | integration | `uv run pytest tests/test_library_service.py` (may be Wave 0) | ❌ W0 | ⬜ pending |
| 164-03-* | 03 | 2 | SEED-093 | — | N/A | unit | `( cd frontend && npm test -- --run useMaiaEloDefault )` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] Locate/confirm home for the `_build_card` normalized-field integration test — research flagged no dedicated `test_library_service.py` exists yet. Planner must either create it or point the serialization test at the correct existing suite.

*Otherwise: existing infrastructure (`tests/test_chesscom_to_lichess.py`, frontend vitest) covers all phase requirements.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Maia slider seats at the normalized (not raw) ELO while the analysis header still shows the raw platform rating | SEED-093 | End-to-end UI behavior across serialization + hook; not unit-observable | Open the analysis board for a chess.com blitz game; confirm header shows raw rating (e.g. "1720") while the Maia ELO slider defaults to the higher Lichess-blitz-equivalent value |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
