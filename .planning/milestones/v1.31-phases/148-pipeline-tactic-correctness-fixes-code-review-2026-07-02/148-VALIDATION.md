---
phase: 148
slug: pipeline-tactic-correctness-fixes-code-review-2026-07-02
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-07-04
---

# Phase 148 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x (backend) |
| **Config file** | `pyproject.toml` / `tests/conftest.py` (per-run DB isolation) |
| **Quick run command** | `uv run pytest tests/<file>::<test> ` (single new test) |
| **Full suite command** | `uv run pytest -n auto -x` |
| **Estimated runtime** | ~single test <30s; full suite ~minutes |

---

## Sampling Rate

- **After every task commit:** Run the task's new/affected test(s) directly.
- **After every plan wave:** Run `uv run pytest -n auto -x` (full backend suite).
- **Before `/gsd-verify-work`:** Full suite must be green + `uv run ty check app/ tests/` clean.
- **Max feedback latency:** ~30s (single test) / a few minutes (full suite).

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| TBD (planner fills) | — | — | — | — | N/A | unit | `uv run pytest ...` | ✅ existing infra | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*
*The planner populates one row per item (1–5); each item ships its own unit test + verify loop per CONTEXT.md D-06.*

---

## Wave 0 Requirements

- Existing infrastructure covers all phase requirements (pytest + per-run-DB isolation + conftest `build_detector_board` already present).
- No new framework install. New tests attach to existing test files identified in RESEARCH.md (§ test/fixture strategy).

---

## Manual-Only Verifications

*All phase behaviors have automated verification.* Each of the five fixes is unit-testable:
mate-fallback tag + ep/castling FEN round-trip (item 1), dead-pool drain releases lease and does NOT stamp (item 2), shared-cohort SE widens (item 3), malformed game skipped + import completes (item 4), stale-lease submit guard rejects (item 5).

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s (single test)
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
