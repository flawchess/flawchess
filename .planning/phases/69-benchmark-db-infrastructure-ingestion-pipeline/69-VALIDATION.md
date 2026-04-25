---
phase: 69
slug: benchmark-db-infrastructure-ingestion-pipeline
status: planned
nyquist_compliant: false
wave_0_complete: false  # Plan 02 Task 02-01 builds the test scaffold
created: 2026-04-25
---

# Phase 69 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Source: `69-RESEARCH.md` §12 Validation Architecture.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x + pytest-asyncio (asyncio_mode = "auto") |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` (existing) |
| **Quick run command** | `uv run pytest tests/test_benchmark_ingest.py -x` |
| **Full suite command** | `uv run pytest` |
| **Estimated runtime** | ~5 s for benchmark unit tests; ~60 s full suite |

Type checker (must pass with zero errors before suite is considered green):
- `uv run ty check app/ tests/ scripts/`

Lint/format (run after edits):
- `uv run ruff check .` / `uv run ruff format .`

---

## Sampling Rate

- **After every task commit:** Run the targeted unit test for the file modified (`uv run pytest tests/test_benchmark_ingest.py::<test_name> -x`).
- **After every plan wave:** Run `uv run pytest tests/test_benchmark_ingest.py -x` plus `uv run ty check app/ tests/ scripts/`.
- **Before `/gsd-verify-work`:** Full suite must be green: `uv run pytest && uv run ty check app/ tests/ scripts/ && uv run ruff check .`
- **Max feedback latency:** 60 seconds (full suite).

---

## Per-Task Verification Map

> Task IDs are placeholders until plans are written; the planner MUST update this table after PLAN.md creation so each task with verification evidence has a row here. Wave-0 column flags whether the test file/scaffolding exists at the time the task runs.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 69-01-04 | 01 (compose + init SQL — checkpoint) | 1 | INFRA-01 | T-69-01 | DB instance isolated by project/volume/port/user | manual smoke | `docker compose -f docker-compose.benchmark.yml -p flawchess-benchmark ps` (status = healthy) | ❌ W0 | ⬜ pending |
| 69-01-04 | 01 (init SQL grants — checkpoint) | 1 | INFRA-01 | T-69-02 | RO role has SELECT only, no INSERT/UPDATE/DELETE | unit (psql) | `psql ... -c "SELECT has_table_privilege('flawchess_benchmark_ro', 'games', 'INSERT')"` returns `f` | ❌ W0 | ⬜ pending |
| 69-02-03 | 02 (alembic migration eval_depth/source) | 1 | INFRA-02, INGEST-06 | — | Migration applies cleanly to dev/prod/test/benchmark uniformly | integration | `DATABASE_URL=postgresql+asyncpg://...:5433/flawchess_benchmark uv run alembic upgrade head` (exit 0; columns present) | ❌ W0 | ⬜ pending |
| 69-02-02 | 02 (eval_source_version constant) | 2 | INGEST-06 | — | New Lichess imports populate `eval_source_version='lichess-pgn'`; chess.com leaves both NULL | unit | `uv run pytest tests/test_benchmark_ingest.py::test_eval_columns -x` | ❌ W0 | ⬜ pending |
| 69-02-01 | 02 (centipawn convention note) | 2 | INGEST-06 | — | Documented agreement of signed-from-white centipawn parsing with a known sample | docstring/test | `uv run pytest tests/test_benchmark_ingest.py::test_centipawn_convention -x` OR `docs/benchmark-ingest-notes.md` references known FEN+eval sample | ❌ W0 | ⬜ pending |
| 69-03-02 | 03 (MCP server registration — checkpoint) | 1 | INFRA-03 | T-69-02 | `flawchess-benchmark-db` MCP server registered, read-only | manual smoke | `mcp__flawchess-benchmark-db__query` returns `count(*)` from `games` and `game_positions` | ❌ W0 (manual) | ⬜ pending |
| 69-04-03 | 04 (selection scan + parser) | 2 | INGEST-01 | T-69-07 | Streaming pre-filter extracts headers + `[%eval` flag without parsing moves | unit | `uv run pytest tests/test_benchmark_ingest.py::test_scan_dump_parser -x` | ❌ W0 | ⬜ pending |
| 69-04-02 | 04 (player bucketing) | 2 | INGEST-02, INGEST-03 | — | Median Elo + modal TC assigns players to one (rating × TC) cell from grid | unit | `uv run pytest tests/test_benchmark_ingest.py::test_player_bucketing -x` | ❌ W0 | ⬜ pending |
| 69-06-04 | 05/06 (orchestrator + SIGINT resumability — manual checkpoint in Plan 06) | 3 | INGEST-04 | T-69-05 | SIGINT mid-import + resume yields identical row counts to uninterrupted run | integration/manual | Manual procedure in RESEARCH.md §11; row-count parity recorded in verification report | ❌ W0 (manual) | ⬜ pending |
| 69-05-01 | 05 (stub User row creation) | 3 | INGEST-02 | — | Stub User satisfies FastAPI-Users invariants but never serves auth | unit | `uv run pytest tests/test_benchmark_ingest.py::test_stub_user_invariants -x` | ❌ W0 | ⬜ pending |
| 69-05-01 | 05 (per-user 20k hard skip) | 3 | INGEST-02 | T-69-06 | Users with >20k window-bounded games are hard-skipped with audit log | unit | `uv run pytest tests/test_benchmark_ingest.py::test_outlier_skip -x` | ❌ W0 | ⬜ pending |
| 69-06-05 | 06 (smoke + 100/cell + storage check) | 4 | INGEST-05 | — | Total benchmark DB size ≤ 100 GB after 100/cell run; queen cell ≥ 1k samples | manual / SQL | MCP `SELECT pg_size_pretty(pg_database_size('flawchess_benchmark'))` ≤ 100 GB; queen rowcount ≥ 1000 | ❌ post-ingest (manual) | ⬜ pending |
| 69-06-07 | 06 (per-cell evidence for Phase 70) | 4 | INGEST-03, INGEST-05 | — | All 20 (rating × TC) cells populated; eval coverage rate computed | manual / SQL | Verification report contains §"Per-cell game counts" + §"Eval coverage per cell" tables | ❌ post-ingest | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

> Task IDs replaced 2026-04-25 from PLAN.md task IDs. All 9 phase requirements (INFRA-01..03, INGEST-01..06) are mapped to at least one row above.

---

## Wave 0 Requirements

- [ ] `tests/test_benchmark_ingest.py` — stubs for `test_scan_dump_parser`, `test_player_bucketing`, `test_eval_columns`, `test_centipawn_convention`, `test_stub_user_invariants`, `test_outlier_skip`
- [ ] `tests/conftest.py` — verify existing async DB session fixtures cover an isolated `DATABASE_URL` override (or add a `benchmark_session` fixture)
- [ ] `docker-compose.benchmark.yml` — benchmark compose file
- [ ] `deploy/init-benchmark-db.sql` — benchmark init SQL with read-only role grants
- [ ] `bin/benchmark_db.sh` — start/stop/reset analog of `bin/reset_db.sh`
- [ ] `zstandard` (or `python-zstandard`) added to `pyproject.toml` dev/runtime extras (or CLI `zstd`/`zstdcat` fallback documented)
- [ ] `~/.claude.json` MCP servers section gains `flawchess-benchmark-db` entry (manual user-level edit, documented in CLAUDE.md §Database Access)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| MCP server returns row counts via `mcp__flawchess-benchmark-db__query` | INFRA-03 | MCP servers are user-level (`~/.claude.json`); no automated test harness for the Claude Code MCP runtime | After registering server, restart Claude Code, then call `mcp__flawchess-benchmark-db__query` with `SELECT count(*) FROM games; SELECT count(*) FROM game_positions;` and confirm non-error response |
| SIGINT resumability test | INGEST-04 | Requires real Lichess HTTP traffic; running in CI would hammer the public API | Run on a small synthetic dump (or one short Lichess user). Procedure in RESEARCH.md §11: (1) start ingest with `--per-cell 1`, (2) `kill -SIGINT $PID` mid-import, (3) restart from same checkpoint, (4) compare final row counts of `games` and `game_positions` against an uninterrupted reference run |
| Storage budget verification (`<= 100 GB at 100/cell`) | INGEST-05 | Requires the actual ingest to have completed (operational, not unit-test scoped) | After the 100/cell ingest run completes, run MCP query `SELECT pg_size_pretty(pg_database_size('flawchess_benchmark'))` and append the result to the verification report |
| Centipawn convention agreement check | INGEST-06 | Verifying that signed-from-white centipawns match a known external sample is a one-off check, not a regression test | Pick one Lichess game with `[%eval ...]` annotations; assert that `game_positions.eval_cp` for the position matches the PGN `[%eval]` value when interpreted as signed-from-white centipawns. Document in `docs/benchmark-ingest-notes.md` |

---

## Dimension 8: Evidence for Phase 70 (Downstream)

Phase 70 (classifier validation replication) consumes Phase 69's output. Phase 69 MUST produce:

1. **Per-cell game counts** — confirms 20-cell coverage at the threshold required for Phase 70's 10x sample target.
2. **Eval coverage per cell** — Phase 70 filters `eval_cp IS NOT NULL`; queries must succeed.
3. **`eval_source_version` distribution** — sanity check that all imported Lichess games tagged `'lichess-pgn'`.
4. **Resumability proof** — row-count parity recorded in verification report so the gate verdict in Phase 70 isn't undermined by an ingest restart blowing up the dataset.

The above evidence MUST be appended to the Phase 69 verification report (or `reports/benchmark-db-phase69-verification-YYYY-MM-DD.md`) before `/gsd-verify-work`.

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies (planner fills task IDs)
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify (planner enforces)
- [ ] Wave 0 covers all `❌ W0` references in the verification map
- [ ] No watch-mode flags in test commands
- [ ] Feedback latency < 60s for unit tests
- [ ] `nyquist_compliant: true` set in frontmatter once planner has filled the task map and checker has confirmed coverage

**Approval:** pending
