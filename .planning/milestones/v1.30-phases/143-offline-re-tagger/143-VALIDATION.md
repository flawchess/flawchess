---
phase: 143
slug: offline-re-tagger
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-06-30
---

# Phase 143 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x (uv-managed) |
| **Config file** | `pyproject.toml` (`[tool.pytest.ini_options]` addopts) |
| **Quick run command** | `uv run pytest tests/services/test_forcing_line_gate.py -q` |
| **Full suite command** | `uv run pytest -n auto` |
| **Estimated runtime** | quick ~5s; full suite ~minutes (per-run DB clone) |

---

## Sampling Rate

- **After every task commit:** Run the plan's quick command (gate tests / flaws_service tests / retag_flaws test).
- **After every plan wave:** Run `uv run pytest -n auto` for the touched packages.
- **Before `/gsd-verify-work`:** Full suite + `uv run ty check app/ scripts/ tests/` must be green.
- **Max feedback latency:** < 120s for the per-task quick commands.

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 143-01-01 | 01 | 1 | RETAG-01 | T-143-01 | No global margin mutation (worker-pool-safe) | unit | `uv run pytest tests/services/test_forcing_line_gate.py -q` | ✅ | ⬜ pending |
| 143-01-02 | 01 | 1 | GATE-03, GATE-04 | — | N/A | unit | `uv run pytest tests/services/test_forcing_line_gate.py -v -k "defender or margin or MatePriority"` | ✅ | ⬜ pending |
| 143-02-01 | 02 | 2 | RETAG-02 | T-143-02 | Gate-skip on NULL blob; empty list rejected | unit | `uv run pytest tests/services/test_flaws_service.py -q` | ✅ | ⬜ pending |
| 143-02-02 | 02 | 2 | RETAG-02, GATE-03, GATE-04 | T-143-03 | No DB blob read at classify time | integration | `uv run pytest tests/services/test_full_eval_drain.py tests/services/test_eval_drain.py -q` | ✅ | ⬜ pending |
| 143-03-01 | 03 | 3 | RETAG-01, RETAG-02 | T-143-04, T-143-05 | argparse type=int; --db Literal allowlist; prod write on server only | structural | `test ! -f scripts/backfill_tactic_tags.py && test -f scripts/retag_flaws.py && uv run ty check scripts/retag_flaws.py` | ✅ | ⬜ pending |
| 143-03-02 | 03 | 3 | RETAG-01 | T-143-06 | Malformed/NULL blob handled conservatively | structural | `uv run ty check scripts/retag_flaws.py` | ✅ | ⬜ pending |
| 143-03-03 | 03 | 3 | RETAG-01, RETAG-02 | T-143-07 | Change-only UPDATE (no-op rows skipped) | integration | `uv run pytest tests/scripts/test_retag_flaws.py -v` | ❌ W0 (created by this task) | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Success-Criteria → Test Map

| ROADMAP SC | Requirement | Verified by | Type |
|------------|-------------|-------------|------|
| SC1 — `--dry-run --margin X --user-id N` reports per-motif delta, no DB write; `--db dev\|benchmark\|prod` | RETAG-01 | `tests/scripts/test_retag_flaws.py` (dry-run writes report + 0 rows) + operator UAT | integration + manual |
| SC2 — mate-priority hierarchy (only-best/both-mates/mate-in-1-never-suppressed/fall-through) | GATE-03 | `tests/services/test_forcing_line_gate.py::TestMatePriority` (audited fully covered) | unit |
| SC3 — defender branch-then-reconverge does not kill a forced line | GATE-04 | `tests/services/test_forcing_line_gate.py::test_multi_ply_defender_ambiguity_does_not_kill_line` | unit |
| SC4 — idempotent update via the single classify path | RETAG-02 | `_classify_tactic_gated` wrapper unit test (flaws_service) + `tests/scripts/test_retag_flaws.py` second-run-0-rows | unit + integration |

---

## Wave 0 Requirements

- [ ] `tests/scripts/test_retag_flaws.py` — does not exist yet; created by task 143-03-03 (the script `retag_flaws.py` itself does not exist until task 143-03-01). This is the only MISSING test artifact; it is created in the same plan that produces the code under test, against the existing per-run DB fixture infrastructure (`tests/conftest.py`, mirroring `tests/test_backfill_flaws.py`).

All other test files (`test_forcing_line_gate.py`, `test_flaws_service.py`, `test_full_eval_drain.py`, `test_eval_drain.py`) already exist and are extended in place.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| End-to-end dry-run against a populated dev DB | RETAG-01 | Requires the dev DB with real Phase 142 blobs for user 28; "no dev DB reset in plans" — the automated gate uses an injected session_maker against the per-run test DB instead | Start dev DB, run `uv run python scripts/retag_flaws.py --db dev --dry-run --margin 0.35 --user-id 28`; confirm `reports/retag/retag-YYYY-MM-DD.md` is written and an immediate second dry-run reports 0 rows would change |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (only `tests/scripts/test_retag_flaws.py`, created with its code)
- [x] No watch-mode flags
- [x] Feedback latency < 120s for quick commands
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-06-30
