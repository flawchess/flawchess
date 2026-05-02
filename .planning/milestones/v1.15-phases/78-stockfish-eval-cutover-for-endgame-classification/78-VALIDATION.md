---
phase: 78
slug: stockfish-eval-cutover-for-endgame-classification
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-02
---

# Phase 78 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (backend), vitest (frontend — not used this phase) |
| **Config file** | `pyproject.toml` (pytest section) |
| **Quick run command** | `uv run pytest tests/services/test_engine.py tests/repositories/test_endgame_repository.py -x` |
| **Full suite command** | `uv run ruff check . && uv run ty check app/ tests/ && uv run pytest` |
| **Estimated runtime** | ~120 seconds (backend full); ~5 seconds (engine + repo subset) |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest <touched test file> -x`
- **After every plan wave:** Run `uv run ruff check . && uv run ty check app/ tests/ && uv run pytest -x`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 120 seconds

---

## Per-Task Verification Map

(Filled by planner from PLAN.md tasks. Each row maps a task to its requirement, automated command, and test/file existence at Wave 0 time.)

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/services/test_engine.py` — wrapper unit tests for ENG-02 (mate-in-N, cp-advantage, white/black sign convention)
- [ ] `tests/repositories/test_endgame_repository_eval.py` — classification rule tests for REFAC-02 (sign flip, ±100 cp, mate shortcut, parity)
- [ ] `tests/scripts/test_backfill_eval.py` — backfill script idempotency / resume tests on tiny seeded fixture (FILL-01, FILL-02)
- [ ] `tests/services/test_import_eval.py` — import-path eval integration test (IMP-01: lichess values preserved, NULL rows populated)
- [ ] Stockfish binary available on test runner PATH (CI: `apt install stockfish`; local: prerequisite)
- [ ] `tests/conftest.py` — engine fixture (session-scoped, starts/stops engine once per session per D-02)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `docker compose exec backend stockfish --help` succeeds | ENG-01 | Requires built backend image | After image rebuild: `docker compose up -d backend && docker compose exec backend stockfish --help` — confirm version line matches pinned tag |
| Benchmark `/conv-recov-validation` ≥ 99% agreement | VAL-01 | Requires full benchmark backfill (~2 hours) | After D-07 round 2: invoke `/conv-recov-validation` skill against benchmark DB; assert headline agreement ≥ 99% |
| Live UI gauges sensible on 3-5 test users | VAL-02 | Requires prod backfill + deploy | After D-07 round 3 + deploy: operator inspects Endgames page for representative test users covering different (rating, TC) cells |
| `EXPLAIN (ANALYZE, BUFFERS)` shows Index Only Scan with Heap Fetches near zero | REFAC-04 | Requires populated dataset | After backfill: run an `EXPLAIN` against `query_endgame_entry_rows` representative invocation; confirm `Index Only Scan using ix_gp_user_endgame_game` and `Heap Fetches: 0` (or near zero) |
| `pgrep stockfish` count remains stable across N evaluations | ENG-01 | Confirms long-lived UCI process | In a running backend container, trigger N evals via test endpoint or import; before/after `pgrep -c stockfish` should be unchanged |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 120s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
