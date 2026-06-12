---
phase: 116
slug: all-ply-engine-core
status: verified
threats_open: 0
asvs_level: 1
created: 2026-06-12
---

# Phase 116 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| migration → prod DB | DDL + bulk UPDATE run automatically on container startup via deploy/entrypoint.sh | Alembic revision SQL; no user data |
| stored PGN → python-chess | `_collect_full_ply_targets` parses untrusted stored PGN text | PGN string; no external input |
| import lane ↔ full drain | two background coroutines contend for the same EnginePool + DB pool | engine UCI; DB connection pool |
| worker pool RSS → 4g container | N Stockfish workers at 1M nodes + import + Postgres share the backend container memory cgroup | process memory; no data crossing |

---

## Threat Register

| Threat ID | Category | Component | Disposition | Mitigation | Status |
|-----------|----------|-----------|-------------|------------|--------|
| T-116-01 | Denial of Service | In-migration backfill UPDATE (NOT EXISTS over ~30M game_positions rows) | mitigate | EXPLAIN (ANALYZE, BUFFERS) confirmed safe: nested loop anti-join via ix_game_positions_game_id (798ms dev, no full scan). In-migration path chosen. CR-01 fix adds `move_san IS NOT NULL` filter to exclude terminal rows. | closed |
| T-116-02 | Tampering | New Alembic revision chaining | mitigate | `down_revision = "07994baf3b15"` pinned; single head (last file in versions dir). Up/down round-trip tested in `tests/test_migration_116_full_evals.py`. | closed |
| T-116-03 | Information Disclosure | Cross-user `ix_gp_full_hash_opening` (drops user_id scoping) | accept | Documented in Accepted Risks Log. | closed |
| T-116-04 | Denial of Service | Full drain starving the hot import/entry-ply lane | mitigate | `_any_active_import_or_entry_ply_pending` yield gate implemented; both predicates (ImportJob.status, Game.evals_completed_at) indexed. Gate enforced in `_full_drain_tick` Step 0. Tested in `TestYieldGate`. | closed |
| T-116-05 | Tampering | Full drain overwriting lichess %evals (data integrity) | mitigate | `is_analyzed` gate in `_apply_full_eval_results` skips plies with existing non-NULL evals. Dedup is marker-gated on `full_evals_completed_at IS NOT NULL` (not `evals_completed_at`) to exclude depth-15 source rows (Pitfall 4). Tested by `test_dedup_excludes_depth15_source`. | closed |
| T-116-06 | Denial of Service | asyncio.gather sharing an AsyncSession | mitigate | `asyncio.gather` in `_full_drain_tick` Step 3 runs after `load_session` is closed and before `write_session` is opened. Enforced by `test_gather_outside_session` AST scan in CI. | closed |
| T-116-07 | Repudiation | Silent engine failures losing eval coverage with no signal | mitigate | WR-05 aggregated Sentry pattern: (a) all-fail circuit breaker fires `set_context + set_tag + capture_message` and leaves game pending (no silent coverage loss); (b) partial failures fire ONE aggregated `capture_message` per game with `set_context("eval", {game_id, failed_ply_count})` + `set_tag("source", "full_eval_drain")`. No f-string variables in either message string (Sentry grouping preserved). | closed |
| T-116-08 | Denial of Service | Pool-size bump to 8 exceeding the 4g backend mem_limit (OOM-kill) | mitigate | QUEUE-07 measured per-worker RSS at 1M nodes (dev: 1w=277MB, 8w=2083MB). Conservative prod accounting: 8×368MB + 0.3GB = ~3.24GB; ~0.76GB headroom under 4g. D-116-13 gate: deploy at pool 6 first, soak prod ~24h, bump to 8 only if headroom + latency clean. Accounting comment in `engine.py` lines 109-137. Human checkpoint approved 2026-06-12. | closed |
| T-116-09 | Repudiation | Stale docs misleading a future deploy into unsafe pool size | mitigate | All three stale comments corrected: "STOCKFISH_POOL_SIZE=4 to use all 4 vCPUs" removed from `engine.py`; "STOCKFISH_POOL_SIZE up to 6" removed from `docker-compose.yml`; "pool lowered" note clarified to "hotfix era only" in `CLAUDE.md`; Phase 116 accounting paragraph added to `CLAUDE.md`. | closed |
| T-116-SC | Tampering | npm/pip/cargo supply chain | accept | Documented in Accepted Risks Log. | closed |

*Status: open · closed*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-116-01 | T-116-03 | `ix_gp_full_hash_opening` index spans all users by design (EVAL-03 cross-user dedup). The index is over `full_hash` — a 64-bit Zobrist integer with no PII content. It is consumed only by the server-side `_fetch_dedup_evals` helper, which is gated on `full_evals_completed_at IS NOT NULL` and never called from a user-facing API endpoint. No hash is exposed through any API response. Risk: a future developer could add an API route that queries this index directly, bypassing user scoping. Control: `API never exposes hashes` is a documented project invariant (CLAUDE.md). | Phase 116 executor | 2026-06-12 |
| AR-116-02 | T-116-SC | No new npm, pip, or cargo packages were added in any of the three Phase 116 plans. All three SUMMARY files record `tech-stack: added: []`. Supply chain risk is unchanged from pre-phase baseline. | Phase 116 executor | 2026-06-12 |

*Accepted risks do not resurface in future audit runs.*

---

## Unregistered Threat Flags

All threat flags in the three SUMMARY files mapped to existing registered threat IDs:

- 116-01-SUMMARY: T-116-01 (backfill cost), T-116-02 (migration chaining), T-116-03 (cross-user index) — all registered.
- 116-02-SUMMARY: T-116-04 (yield gate), T-116-05 (lichess eval overwrite), T-116-06 (gather inside session), T-116-07 (silent failures) — all registered.
- 116-03-SUMMARY: T-116-09 (stale docs) — registered. T-116-08 (pool-size OOM) — registered.

No unregistered flags.

---

## Verification Evidence

### T-116-01
- `alembic/versions/20260612_120000_add_full_evals_completed_at.py:92-104` — `op.execute(UPDATE ... AND gp.move_san IS NOT NULL ...)` backfill with terminal exclusion.
- 116-01-SUMMARY.md §Backfill EXPLAIN Result — "nested loop anti-join, 798ms, no full table scan; IN-MIGRATION backfill chosen."

### T-116-02
- `alembic/versions/20260612_120000_add_full_evals_completed_at.py:36` — `down_revision: Union[str, None] = "07994baf3b15"`.
- `tests/test_migration_116_full_evals.py:214-255` — up/down/re-up round-trip test.

### T-116-03
- Accepted; see AR-116-01.

### T-116-04
- `app/services/eval_drain.py:210-228` — `_any_active_import_or_entry_ply_pending` implementation with both indexed predicates.
- `app/services/eval_drain.py:911-913` — Step 0 yield-gate call in `_full_drain_tick`.
- `tests/services/test_full_eval_drain.py:647-696` — `TestYieldGate` with active import and entry-ply pending cases.

### T-116-05
- `app/services/eval_drain.py:199` — `Game.full_evals_completed_at.isnot(None)` dedup marker gate in `_fetch_dedup_evals`.
- `app/services/eval_drain.py:282-283` — `is_analyzed` preservation gate in `_apply_full_eval_results`.
- `tests/services/test_full_eval_drain.py:292-325` — `test_dedup_excludes_depth15_source` confirming depth-15 source exclusion.

### T-116-06
- `app/services/eval_drain.py:974` — comment "load_session is now closed" before gather.
- `app/services/eval_drain.py:981-983` — `asyncio.gather(*(engine_service.evaluate_nodes(...)))` with no open session scope.
- `tests/services/test_full_eval_drain.py:598-633` — `test_gather_outside_session` AST scan.

### T-116-07
- `app/services/eval_drain.py:994-1002` — all-fail circuit breaker: `set_context("eval", {"game_id": game_id, "failed_ply_count": len(engine_targets)})` + `set_tag("source", "full_eval_drain")` + `capture_message("full-drain: all engine evals failed for game — leaving pending", level="warning")`; returns `False` (game stays pending).
- `app/services/eval_drain.py:1016-1022` — partial failure aggregated Sentry: `set_context("eval", {"game_id": game_id, "failed_ply_count": failed_ply_count})` + `set_tag` + `capture_message("full-drain engine returned None tuple", ...)`.
- Neither message string contains f-string variables (Sentry grouping preserved).
- `tests/services/test_full_eval_drain.py:535-583` — `test_all_fail_keeps_game_pending` verifies circuit breaker keeps game pending.

### T-116-08
- `app/services/engine.py:109-137` — QUEUE-07/D-116-12 comment block: measured RSS table, conservative prod accounting, D-116-13 deploy-at-6 gate plan.
- `docker-compose.yml:79-88` — Phase 116 accounting comment.
- 116-03-SUMMARY.md §Measured RSS Numbers — dev-measured table (1w=277MB, 4w=1056MB, 6w=1586MB, 8w=2083MB).
- 116-03-SUMMARY.md §Deploy Plan — "D-116-13 (APPROVED 2026-06-12): ship at STOCKFISH_POOL_SIZE=6, soak ~24h, bump to 8 only if headroom confirmed + latency clean."

### T-116-09
- `grep -n "all 4 vCPUs" app/services/engine.py` — 0 matches (stale comment removed).
- `grep -n "STOCKFISH_POOL_SIZE up to 6" docker-compose.yml` — 0 matches (replaced with Phase 116 accounting block).
- `CLAUDE.md:219` — "hotfix era only -- prod has since been raised to 6 stably; see Phase 116 pool accounting below" (stale "lowered" note corrected).
- `CLAUDE.md:221` — Phase 116 STOCKFISH_POOL_SIZE accounting paragraph added.

### T-116-SC
- Accepted; see AR-116-02.

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-06-12 | 10 | 10 | 0 | gsd-security-auditor (claude-sonnet-4-6) |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-06-12
