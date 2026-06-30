---
phase: 146
slug: offload-live-submit-forcing-line-continuation-eval-to-the-re
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-07-01
---

# Phase 146 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x (async, per-run DB) |
| **Config file** | `pyproject.toml` / `tests/conftest.py` (per-run DB clone) |
| **Quick run command** | `uv run pytest -n auto tests/test_eval_remote.py tests/test_eval_queue_service.py` |
| **Full suite command** | `uv run pytest -n auto -x` |
| **Estimated runtime** | ~120 seconds (full), ~20s (targeted) |

---

## Sampling Rate

- **After every task commit:** Run the quick run command for the touched surface
- **After every plan wave:** Run the full suite command
- **Before `/gsd-verify-work`:** Full suite must be green + `uv run ty check app/ tests/` zero errors
- **Max feedback latency:** 120 seconds

---

## Per-Task Verification Map

*Populated by the planner from PLAN.md tasks. Each task that changes behavior must map to an automated `<verify>` command (pytest node id or ty check) or be flagged Manual-Only below.*

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 01-1 | 146-01 | 1 | D-03 | T-146-01 | Schema narrowing; old payload ignored (no extra='forbid') | unit | `uv run pytest -n auto tests/test_eval_remote.py tests/test_eval_worker_endpoints.py -x -k "submit or schema or blob_null or second_best"` | ⚠️ partial (new asserts) | ⬜ pending |
| 01-2 | 146-01 | 1 | D-01 | T-146-02 | `:recency_window` bound param, no f-string | unit | `uv run pytest -n auto tests/test_eval_queue_service.py -x -k "tier4 or recency or claim_tier4"` | ❌ new test | ⬜ pending |
| 02-1 | 146-02 | 1 | D-04 | T-146-04, T-146-05, T-146-06 | Token-opaque echo; bounded lease; single-sleep self-pacing | unit | `uv run pytest -n auto tests/test_remote_eval_worker.py -x -k "ladder or flaw_blob or empty or sleep"` | ❌ new test (rung-4) | ⬜ pending |
| 02-2 | 146-02 | 1 | D-03 consequence / RESEARCH §5 | — | N/A | unit | `uv run pytest -n auto tests/test_remote_eval_worker.py -x -k "timeout or eval_positions or full_ply or multipv"` | ⚠️ partial (timeout assert new) | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- Existing pytest infrastructure (per-run DB clone, async fixtures) covers all phase requirements. No new framework install.
- New/extended tests expected: live `_apply_submit` leaves blobs NULL + stamps both completion markers; `SubmitEval` accepts payload without second-best fields; `_claim_tier4_blob` recency ordering; worker rung-4 lease/submit loop (unit-level, engine mocked).

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| End-to-end dev validation: live submit → NULL blobs → tier-4 drain → gated retag → tags denoised | SEED-071 core contract | Requires a running worker + dev DB drain cycle | Run `scripts/backfill_multipv.py --dev-validate` (or equivalent) against the dev DB after a live submit; confirm blobs fill and tactic tags are gated. No dev DB reset. |
| Server runs zero Stockfish on live `/submit` path | SEED-071 / FLAWCHESS-7Y | Behavioral/observability claim | Confirm no EnginePool call in `_apply_submit` path (source assertion) + observe `/submit` latency in dev. |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 120s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
