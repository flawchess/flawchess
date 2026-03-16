---
phase: 11
slug: schema-and-import-pipeline
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-16
---

# Phase 11 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x + pytest-asyncio |
| **Config file** | `pyproject.toml` (`[tool.pytest.ini_options]`, `asyncio_mode = "auto"`) |
| **Quick run command** | `uv run pytest tests/test_zobrist.py tests/test_import_service.py -x` |
| **Full suite command** | `uv run pytest` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_zobrist.py tests/test_import_service.py -x`
- **After every plan wave:** Run `uv run pytest`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 11-01-01 | 01 | 1 | MEXP-01 | unit | `uv run pytest tests/test_game_repository.py -x -k move_san` | ❌ W0 | ⬜ pending |
| 11-01-02 | 01 | 1 | MEXP-01 | integration | `uv run pytest tests/test_game_repository.py -x -k move_san` | ❌ W0 | ⬜ pending |
| 11-01-03 | 01 | 1 | MEXP-02 | integration | `uv run pytest tests/test_game_repository.py -x -k covering_index` | ❌ W0 | ⬜ pending |
| 11-01-04 | 01 | 1 | MEXP-03 | unit | `uv run pytest tests/test_zobrist.py -x -k move_san` | ❌ W0 | ⬜ pending |
| 11-01-05 | 01 | 1 | MEXP-03 | unit | `uv run pytest tests/test_zobrist.py -x -k move_san` | ❌ W0 | ⬜ pending |
| 11-01-06 | 01 | 1 | MEXP-03 | unit | `uv run pytest tests/test_import_service.py -x -k move_san` | ❌ W0 | ⬜ pending |
| 11-01-07 | 01 | 1 | MEXP-03 | integration | `uv run pytest tests/test_game_repository.py -x -k reimport` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_zobrist.py` — add `test_hashes_for_game_returns_move_san`, `test_hashes_for_game_move_san_null_on_final_ply`, `test_hashes_for_game_move_san_ply_zero`
- [ ] `tests/test_game_repository.py` — update `_make_position_row()` helpers to include `move_san` field; add `test_bulk_insert_positions_with_move_san`
- [ ] `tests/test_import_service.py` — update `position_rows` assertion to verify `move_san` key is present

*Existing test infrastructure covers all execution — only new test cases needed, not new framework setup.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| EXPLAIN ANALYZE shows covering index used | MEXP-02 | Requires populated DB with VACUUM ANALYZE; rolled-back test transactions may not show Index Only Scan | Run `VACUUM ANALYZE game_positions` then `EXPLAIN ANALYZE SELECT move_san, COUNT(*) FROM game_positions WHERE user_id=1 AND full_hash=X GROUP BY move_san;` — verify index name in output |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
