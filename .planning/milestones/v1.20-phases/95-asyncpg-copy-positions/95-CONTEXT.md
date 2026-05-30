# Phase 95: asyncpg COPY for `bulk_insert_positions` — Context

**Gathered:** 2026-05-27
**Status:** Ready for planning
**Source:** SEED-027 §Thread B (Thread A already shipped via PR #144 / prod SHA 65511c9 on 2026-05-26)

<domain>
## Phase Boundary

Switch the position-row bulk write path from SQLAlchemy `insert(GamePosition).values(chunk)` to asyncpg's binary `Connection.copy_records_to_table` so each Postgres backend's per-statement parser/executor memory becomes roughly constant in the chunk size instead of scaling with `rows × columns` (currently up to 1700 × 19 ≈ 32k bound parameters per statement). `bulk_insert_positions` is the heaviest INSERT path in the import pipeline; concurrent dual-platform imports were observed to push the Postgres container to its `mem_limit` cgroup cap in the 2026-05-26 user-109 incident (FLAWCHESS-3Q, third recurrence).

Thread A (SEED-027) — `shared_buffers=2GB`, `effective_cache_size=8GB`, container `mem_limit=12g` — is **already deployed** via hotfix PR #144 (production at SHA `65511c9`, verified live). This phase is Thread B only and has no Thread A overlap.

**Locked carryover:**
- `bulk_insert_positions` callable signature stays the same (`session: AsyncSession, position_rows: list[dict]) -> None`) so `app/services/import_service.py:686` and `tests/test_reclassify.py:100` need no caller-side change.
- `bulk_insert_games` is **untouched** — it uses `pg_insert(...).values(...).on_conflict_do_nothing(...)` for dedup, which COPY cannot express. Only `bulk_insert_positions` moves to COPY.
- Atomicity vs `bulk_insert_games` is preserved by enrolling the COPY in the active SQLAlchemy session transaction (asyncpg COPY participates in the transaction held by the connection it runs on).
- Chunking stays at `chunk_size = 1700` — no longer for the 32k-param ceiling (COPY has no such ceiling), but to bound peak Python-side memory and yield to the asyncio loop between chunks. Comment is rewritten to reflect the new rationale.

**Out of scope:**
- Per-user concurrent-platform serialization (Thread C in SEED-027 post-mortem) — deferred to a separate seed if this phase doesn't close FLAWCHESS-3Q under dual-platform stress.
- Switching `bulk_insert_games` to COPY (loses `ON CONFLICT DO NOTHING`).
- Memory-pressure alerting (Sentry/Grafana threshold on cgroup memory > 80% of `mem_limit`) — observability concern, separate seed.
- Stockfish pool sizing — the failing SQL in the incident was the position INSERT, not the `evals_completed_at` UPDATE.
- Production deploy — Plan 02 verifies on local dev DB only; production deploy is a separate `/deploy` invocation by the user after sign-off.

</domain>

<decisions>
## Implementation Decisions

### asyncpg connection acquisition (locked from seed)

- **D-1: Acquire the raw asyncpg `Connection` from the SQLAlchemy `AsyncSession` via the documented chain.** SQLAlchemy async wrapper exposes the underlying asyncpg `Connection` through `(await session.connection()).get_raw_connection().driver_connection` (SQLAlchemy 2.x async API). Do not bypass the session by acquiring a separate connection from the engine — that would put COPY in a different transaction and break atomicity with `bulk_insert_games`.
  - **Why:** asyncpg's `copy_records_to_table` runs on a `Connection`, not on a SQLAlchemy `Session`. The session's active transaction is held on its own connection; the COPY must run on that same connection to participate in the transaction.

### Column order policy (locked)

- **D-2: Column order passed to `copy_records_to_table(columns=[...])` is enumerated explicitly in `bulk_insert_positions`, NOT introspected at runtime from `GamePosition.__table__.columns`.** The explicit list is the **functional contract** the COPY relies on — drift between Python-side ordering and Postgres column order would silently miswrite data.
  - **Why:** introspection through `__table__.columns` reflects declaration order in the SQLAlchemy model and would change if a future column is added in the middle of the model class. An explicit hard-coded list makes the contract visible at the call site and the test asserts that every model column appears in the list.
  - **How to apply:** the unit test `test_bulk_insert_positions_column_coverage` introspects `GamePosition.__table__.columns` and asserts the explicit list is `set-equal` to it (excluding the auto-`id` primary key). If a new column is added to `GamePosition`, the test fails until the explicit list is updated. This converts "column drift" from a silent data-corruption bug into a CI failure.

### NULL handling (locked)

- **D-3: Records passed to `copy_records_to_table` are tuples (not dicts) with `None` for missing optional fields.** `bulk_insert_positions` receives `list[dict]` from `import_service` where some keys (`material_count`, `material_signature`, `material_imbalance`, `has_opposite_color_bishops`, `piece_count`, `backrank_sparse`, `mixedness`, `phase`, `eval_cp`, `eval_mate`, `endgame_class`) may be absent for older code paths or sparse data. Translate `dict.get(col, None)` for every column.
  - **Why:** asyncpg's COPY protocol needs positional tuples in column order. A missing dict key would either raise `KeyError` (if accessed via `[]`) or silently substitute `None` (if `.get()`). We want `None`, but want it explicit.

### Feature flag question (decided NO)

- **D-4: No feature flag for the COPY path.** SEED-027 §"Open questions" raised whether to gate behind `IMPORT_POSITIONS_COPY=1`. Decision: **no flag**.
  - **Why:** (a) rollback is one `git revert` of the PR — same blast radius as a flag toggle; (b) feature flags rot and accumulate as tech debt; (c) the COPY path is well-trodden asyncpg territory (documented fastest path for bulk insert in asyncpg's own benchmarks), not an experimental code path; (d) `git revert` after a verified production deploy is fundamentally the same recovery posture as the v1.18 hotfixes (#139, #144), which also shipped without flags.
  - **How to apply:** the plan ships a direct cutover. If a regression surfaces post-deploy, recovery is `git revert` + redeploy, not a flag flip.

### Empty-batch behavior (locked)

- **D-5: Empty `position_rows` is a no-op, same as today.** Current implementation returns early on `if not position_rows: return`. The COPY version preserves this — asyncpg's `copy_records_to_table` with an empty iterable would be a wasted round-trip, and the early-return is also the documented pattern.

### Verification posture (locked)

- **D-6: Verification is a local-dev-DB dual-platform stress test, NOT a prod run.** Production deploy of this phase is the user's call after Plan 02 produces a report showing acceptance criteria are met on dev. The stress test seeds dev DB with two real production accounts' game ranges (e.g. user 109's GmAhmedAli / PhAhmedAlssiad split) replayed locally, or synthesizes a 7k+ game multi-platform dataset.
  - **Why:** the FLAWCHESS-3Q failure mode is reproducible under sufficient memory pressure with concurrent imports; dev DB on a developer laptop has less RAM than prod but the same `bulk_insert_positions` hot path. A locally observed reduction in per-backend anon-rss during a synthetic stress run is sufficient signal to deploy.
  - **How to apply:** Plan 02's script captures `docker stats` at 5 s intervals + `pg_stat_activity` snapshots; report writes to `reports/phase95-import-stress-test-{date}.md` (mirrors Phase 91's report naming convention).

### Test transaction-rollback strategy (locked)

- **D-7: The transaction-rollback atomicity test uses an explicit failed flush after `bulk_insert_positions` completes, within the same session.** Test flow: open async session, call `bulk_insert_games` + `bulk_insert_positions` (both succeed), then trigger a constraint-violating second insert in the same session, assert rollback leaves both `games` and `game_positions` empty for the test user.
  - **Why:** the COPY's transaction enrollment is the load-bearing invariant for atomicity. A direct integration test that exercises rollback is the cheapest proof that the COPY committed to the right transaction.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Seed & post-mortem
- `.planning/seeds/SEED-027-db-memory-budget-and-positions-copy.md` — full incident + decision context, including the OOM-killer dmesg, why v1.18's PR #139 didn't fix it, the column-order trap on hotfix forward-ports, and the Thread A/B split rationale
- `reports/phase91-import-stress-test-2026-05-21.md` — baseline import throughput numbers (~11 g/s dual-platform); Plan 02 mirrors this report's shape

### Code (the modification surface)
- `app/repositories/game_repository.py:161-187` — current `bulk_insert_positions` implementation (the only function changed in Plan 01)
- `app/repositories/game_repository.py:14-38` — `bulk_insert_games` (untouched; kept on `pg_insert` for `ON CONFLICT DO NOTHING`)
- `app/services/import_service.py:680-689` — caller of `bulk_insert_positions` inside the import hot lane (Phase 91 two-lane split)
- `app/models/game_position.py` — `GamePosition` model with the 19-ish columns; canonical column ordering source

### Tests (the test surface)
- `tests/test_reclassify.py:66-100` — existing call site through `bulk_insert_games + bulk_insert_positions`; useful as a real-data fixture for Plan 01's integration tests
- `tests/test_import_service.py:471-720` — existing mocks of `bulk_insert_positions` (must keep passing after refactor)

### Production environment (already at Thread A baseline)
- `docker-compose.yml` § `db` service — `shared_buffers=2GB`, `effective_cache_size=8GB`, `mem_limit=12g`, `memswap_limit=12g`, `max_connections=30` (live as of PR #144 / prod SHA 65511c9)
- `CLAUDE.md` § "Production Server" — OOM history table; this phase closes the 2026-05-26 user-109 entry

### asyncpg API surface
- asyncpg `Connection.copy_records_to_table(table_name, *, records, columns=None, schema_name=None, timeout=None)` — binary COPY protocol, runs in the active transaction of the connection it's called on
- SQLAlchemy async `(await session.connection()).get_raw_connection().driver_connection` — documented path to the underlying asyncpg `Connection`

</canonical_refs>

<specifics>
## Specific Ideas

**Implementation skeleton (target shape — full code to be written in Plan 01):**

```python
# app/repositories/game_repository.py
async def bulk_insert_positions(session: AsyncSession, position_rows: list[dict]) -> None:
    if not position_rows:
        return

    columns = (
        "game_id", "user_id", "ply",
        "full_hash", "white_hash", "black_hash",
        "move_san", "clock_seconds",
        "material_count", "material_signature", "material_imbalance",
        "has_opposite_color_bishops",
        "piece_count", "backrank_sparse", "mixedness", "phase",
        "eval_cp", "eval_mate", "endgame_class",
    )

    raw_conn = (await session.connection()).get_raw_connection().driver_connection

    chunk_size = 1700  # Yield to event loop between chunks; bound peak Python memory.
    for i in range(0, len(position_rows), chunk_size):
        chunk = position_rows[i : i + chunk_size]
        records = [tuple(row.get(col) for col in columns) for row in chunk]
        await raw_conn.copy_records_to_table(
            "game_positions", records=records, columns=columns
        )
    await session.flush()
```

**Unit test additions (target — full file Δ in Plan 01):**

- `test_bulk_insert_positions_column_coverage` — asserts the explicit `columns` tuple set-equals `{c.name for c in GamePosition.__table__.columns if c.name != "id"}`
- `test_bulk_insert_positions_round_trip` — insert a 3-row batch with all optional fields populated, SELECT them back, assert every column matches
- `test_bulk_insert_positions_null_optional_fields` — insert a 2-row batch with **only** required fields (game_id, user_id, ply, hashes), assert SELECT returns `None` for every optional column
- `test_bulk_insert_positions_empty_batch_noop` — call with `[]`, assert no SQL was issued (mock or pg_stat_statements scratch)
- `test_bulk_insert_positions_rollback_atomicity` — insert games + positions, then trigger a post-COPY violation, assert both tables empty after rollback (per D-7)
- `test_bulk_insert_positions_chunking_across_chunk_size` — insert `chunk_size + 1` rows (1701), assert all 1701 land in the table (proves the chunk loop is correct after the protocol-limit reason for chunking went away)

**Stress test design (target — Plan 02):**

- Seed dev DB with a synthetic ~7000-game dataset (or replay user 109's range from local PGN fixtures if available)
- Spawn two concurrent `import_service.run_import` tasks (one chess.com, one lichess) via a dedicated test script under `scripts/stress_test_dual_platform_import.py`
- Sample `docker stats flawchess-dev-db-1` at 5 s intervals → CSV
- Sample `SELECT pid, state, query_start FROM pg_stat_activity WHERE datname='flawchess_dev'` at 5 s intervals → CSV
- Report comparison: pre-COPY baseline (re-run on the previous commit) vs post-COPY measurement on this branch
- Acceptance: post-COPY peak `flawchess-dev-db-1` memory < pre-COPY peak by a measurable margin; zero `ConnectionDoesNotExistError` in either job's `error_message`

</specifics>

<deferred>
## Deferred Ideas

- **Memory-pressure alerting** (Sentry/Grafana cgroup memory > 80% of `mem_limit`) — captured in SEED-027 §Open Questions; separate observability seed
- **Per-user concurrent-platform serialization** — only revisit if Thread B doesn't close FLAWCHESS-3Q under dual-platform stress
- **Switch `bulk_insert_games` to COPY** — explicitly out of scope; loses `ON CONFLICT DO NOTHING`
- **Replace `bulk_insert_positions` with `INSERT ... ON CONFLICT DO NOTHING` via COPY-to-staging-table pattern** — not needed; positions are only inserted for newly-inserted game IDs (per the existing docstring), so dedup is unnecessary

</deferred>

---

*Phase: 95-asyncpg-copy-positions*
*Context gathered: 2026-05-27 directly from SEED-027 §Thread B (no discuss-phase — seed is comprehensive)*
