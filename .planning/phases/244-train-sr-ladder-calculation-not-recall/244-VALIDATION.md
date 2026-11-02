---
phase: "244"
slug: "train-sr-ladder-calculation-not-recall"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
status: validated
nyquist_compliant: true
wave_0_complete: true
created: "2026-11-02"
---

# Phase 244 — Validation Strategy

> Reconstructed from artifacts (State B) after execution. Coverage contract = CONTEXT decisions D-01..D-11 via PLAN must_haves (no REQ-IDs for this phase).

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (backend, PostgreSQL per-worker clone), vitest (frontend) |
| **Config file** | `pyproject.toml`, `tests/conftest.py`, `frontend/vite.config.ts` |
| **Quick run command** | `uv run pytest tests/services/test_train_scheduler.py tests/test_migration_244_sr_ladder_due_dates.py` |
| **Full suite command** | `uv run pytest -n auto -x` and `( cd frontend && npm test -- --run )` |
| **Estimated runtime** | ~60 s backend, ~90 s frontend |

---

## Sampling Rate

- **After every task commit:** quick run command
- **After every plan wave:** full suite command
- **Before `/gsd-verify-work`:** full suite green (2026-11-02: backend 5668 passed / 19 skipped, frontend 5706 passed)
- **Max feedback latency:** ~90 s

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 244-01-01 | 01 | 1 | D-01/D-11 correct +10, mastery at 2, first attempt counts | — | N/A | unit | `uv run pytest tests/services/test_train_scheduler.py` (`test_ladder_constants_match_phase_244`, `test_streak_1_correct_masters_at_exactly_2`, `test_correct_first_attempt_counts_toward_mastery`, `test_fail_then_two_correct_masters`) | ✅ | ✅ green |
| 244-01-01 | 01 | 1 | D-01 fail +4, Door A at 3, Door B at 4 | — | N/A | unit | `uv run pytest tests/services/test_train_scheduler.py` (`test_lapses_below_leech_then_two_in_a_row_masters_not_parks`, `test_fail_count_2_ever_correct_false_parks_at_exactly_3`) | ✅ | ✅ green |
| 244-01-01 | 01 | 1 | D-02 exact offsets, no schedule arg | — | N/A | unit + integration | `test_due_dates_are_exact_offsets_on_every_weekday`, `test_signature_has_no_weekday_mask_parameter`; `uv run pytest tests/routers/test_train.py -k "masters_item_at_two or ignores_sparse_weekday_mask"` | ✅ | ✅ green |
| 244-01-01 | 01 | 1 | D-01 old offset dict removed | — | N/A | static | `uv run ty check app/ tests/ scripts/` (any stale import fails) | ✅ | ✅ green |
| 244-01-02 | 01 | 1 | New drill_items due immediately | — | N/A | integration | `uv run pytest tests/repositories/test_train_repository.py -k due_immediately` | ✅ | ✅ green |
| 244-01-03 | 01 | 1 | D-05/D-07/D-08/D-09/D-06/D-10 migration push semantics (cases A–K) | — | N/A | integration (real SQL) | `uv run pytest tests/test_migration_244_sr_ladder_due_dates.py` (`test_push_due_dates_per_case`) | ✅ | ✅ green |
| 244-01-03 | 01 | 1 | D-05 idempotent re-run | — | N/A | integration | `test_push_due_dates_rerun_is_noop` | ✅ | ✅ green |
| 244-02-01 | 02 | 2 | D-01 mastered tail "Two in a row ... retired", stats-card explainers | — | N/A | unit | `( cd frontend && npx vitest run src/lib/__tests__/trainBotCopy.test.ts src/components/train/__tests__/TrainStatsCard.test.tsx )` | ✅ | ✅ green |
| 244-02-01 | 02 | 2 | D-03 returnPhrase / NEXT_SESSION_TAIL unchanged | — | N/A | unit | `returnPhrase (truth table)` suite in `trainBotCopy.test.ts` | ✅ | ✅ green |
| 244-02-02 | 02 | 2 | Pre-merge gate | — | N/A | gate | CLAUDE.md pre-merge gate | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

Mutation evidence (244-01-SUMMARY): reverting new-item due date to today+1, dropping the `floor > today` predicate, and dropping the `source = 0` filter each failed the corresponding test.

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Docstrings/comments describe 2-in-a-row, Door B at 4, schedule-independent dates; none calls a first attempt memory-free | D-04 | Prose in docstrings | Read `app/services/train_scheduler.py`, `app/models/drill_item.py`, `upsert_settings` docstring |
| Home card + README copy match new ladder; no "three solves / three days / six misses" | D-01/D-11 (244-02) | Static marketing copy | `grep -rniE "three (correct|solves|in a row)\|six (misses\|times)" frontend/src README.md` returns no ladder hits |
| CHANGELOG [Unreleased] bullet | 244-02 | Release notes | Inspect `CHANGELOG.md` top of `[Unreleased]` |
| Migration downgrade is a documented no-op | D-05 | One-way data migration, no behavior to assert | Read `downgrade()` in `alembic/versions/20261102_120000_e2a7c4f9b244_*.py` |
| Prod pushed-row count ≈ 436 | D-05 sizing | Prod-only data | After deploy, check the migration log line "Phase 244: pushed due_date on N active drill_items" |

---

## Validation Sign-Off

- [x] All tasks have automated verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (none missing)
- [x] No watch-mode flags
- [x] Feedback latency < 120 s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-11-02
