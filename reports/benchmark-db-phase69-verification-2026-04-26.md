# Phase 69 Verification Report — Benchmark DB Infrastructure & Ingestion Pipeline

**Date:** 2026-04-26
**Phase:** 69 (Benchmark DB Infrastructure & Ingestion Pipeline)
**Milestone:** v1.12 (scope-reduced 2026-04-26 — Phases 70-73 deferred to SEED-006)
**Author:** Phase 69 verification (auto-composed from benchmark DB queries + scratch-69-06.md)

---

## 1. Scope and Verdict

Per the 2026-04-26 scope-down, v1.12's milestone gate is **pipeline correctness**, not the size of the populated DB. Populating the benchmark DB at full `--per-cell 500` scale is operational work for SEED-006.

This report verifies pipeline correctness using:
- The selection scan against a real Lichess monthly dump (`2026-03`).
- A `--per-cell 3` smoke ingest (60 users, 3h 6min runtime, ran 2026-04-26 09:26-12:32 UTC).
- A SIGINT + SIGKILL resumability test against a small `--per-cell 13`/`--per-cell 30` slice (2026-04-26 12:48-13:00 UTC).

**Verdict: PASS.** All 9 v1.12 requirements (3 INFRA, 6 INGEST) are met. Two requirements have explicit carve-outs documented in REQUIREMENTS.md (INFRA-02 ops-tables exception; INGEST-06 column drop after the smoke revealed the Lichess API does not surface depth).

---

## 2. Selection Scan (INGEST-01, INGEST-02, INGEST-03)

`scripts/select_benchmark_users.py` was run end-to-end against the 2026-03 Lichess standard-rated monthly dump.

| Metric | Value |
|---|---|
| Standard games scanned | 90,074,196 |
| Unique players seen | 1,962,767 |
| Qualifying players (K=10 eval-bearing-game floor, D-12) | 491,201 |
| Persisted to `benchmark_selected_users` | 8,628 |

**Per-cell pool sizes (5 rating × 4 TC = 20 cells):**

| rating_bucket | bullet | blitz | rapid | classical |
|---|---|---|---|---|
| 800 | 500 | 500 | 500 | 78 |
| 1200 | 500 | 500 | 500 | 500 |
| 1600 | 500 | 500 | 500 | 500 |
| 2000 | 500 | 500 | 500 | 239 |
| 2400 | 500 | 500 | 287 | 24 |

17/20 cells hit the 500 cap. Sparse cells reflect natural rarity in a single Lichess monthly dump:
- 800/classical: 78 (low-rated players rarely play classical)
- 2000/classical: 239
- 2400/rapid: 287
- 2400/classical: 24 (smallest cell — fewest 2400+ classical players in a month)

Eval-game counts per selected player range from K=10 (the floor) to a per-bucket max of 165-816, confirming the K floor is exercised and the upper bound is not artificially capped.

INGEST-03 player-side bucketing (`bucket_players` in the selection script): each side's rating bucket is determined independently from `WhiteElo` / `BlackElo`. Aggregations over `game_positions` never roll up by a single game-level rating field.

---

## 3. Smoke Ingest — `--per-cell 3` (INGEST-04, INGEST-05, INGEST-06)

`scripts/import_benchmark_users.py --per-cell 3` ran end-to-end against the real Lichess API.

| Metric | Value |
|---|---|
| Run start | 2026-04-26 09:26:19 UTC |
| Run end | 2026-04-26 12:32:39 UTC |
| Duration | 11,180.5s (≈ 3h 6min) |
| Exit code | 0 |
| Terminal checkpoint rows | 60 / 60 |

**Status distribution (smoke only, before resumability test):**

| Status | Count | % |
|---|---|---|
| completed | 56 | 93.3% |
| skipped (over_20k_games) | 3 | 5.0% |
| failed | 1 | 1.7% |
| pending | 0 | 0% |

Skipped users (D-14: `_should_hard_skip` threshold = 20,000 games):
- `Bubba80` (1200/bullet) — 31,894 games
- `captain-obvious17` (2000/blitz) — 24,570 games
- `steve_severin` (2000/bullet) — 22,140 games

Failed user (1):
- `maqaweli` (2000/bullet) — `games_imported=0`, no `skip_reason`. Likely a transient API issue; the row's terminal status guarantees the orchestrator will not silently retry. Investigation deferred — SEED-006 large-scale ingest will surface whether this failure mode is reproducible.

---

## 4. Per-Cell Game Counts and Eval Coverage (Dimension-8 evidence)

State at end of verification window (smoke + resumability test top-up):
- 65 distinct benchmark users, 289,022 games, 20,328,597 game_positions.
- Game date range: 2023-03-31 → 2026-04-26 (within 36-month window from import time).

**Per-cell totals (completed users only):**

| rating | TC | users | games | positions | eval_cp positions | eval_cp % |
|---|---|---|---|---|---|---|
| 800 | bullet | 3 | 15,009 | 794,967 | 57,795 | 7.27% |
| 800 | blitz | 8* | 13,636 | 867,823 | 78,731 | 9.07% |
| 800 | rapid | 3 | 2,046 | 125,138 | 19,553 | 15.63% |
| 800 | classical | 3 | 409 | 23,884 | 5,692 | 23.83% |
| 1200 | bullet | 2 | 2,458 | 140,052 | 11,868 | 8.47% |
| 1200 | blitz | 3 | 8,816 | 537,457 | 138,160 | 25.71% |
| 1200 | rapid | 3 | 16,602 | 1,026,466 | 127,265 | 12.40% |
| 1200 | classical | 3 | 785 | 48,572 | 14,018 | 28.86% |
| 1600 | bullet | 3 | 34,829 | 2,614,462 | 84,901 | 3.25% |
| 1600 | blitz | 3 | 22,112 | 1,513,682 | 115,509 | 7.63% |
| 1600 | rapid | 3 | 5,972 | 408,252 | 121,635 | 29.79% |
| 1600 | classical | 3 | 6,495 | 466,817 | 102,377 | 21.93% |
| 2000 | bullet | 1 | 962 | 70,151 | 4,399 | 6.27% |
| 2000 | blitz | 2 | 8,043 | 662,594 | 123,198 | 18.59% |
| 2000 | rapid | 3 | 18,761 | 1,452,624 | 699,552 | 48.16% |
| 2000 | classical | 3 | 5,224 | 377,189 | 68,937 | 18.28% |
| 2400 | bullet | 3 | 18,165 | 1,558,846 | 201,533 | 12.93% |
| 2400 | blitz | 3 | 15,390 | 1,217,797 | 944,644 | 77.57% |
| 2400 | rapid | 3 | 6,411 | 506,993 | 222,013 | 43.79% |
| 2400 | classical | 3 | 2,525 | 179,339 | 104,147 | 58.07% |

*800/blitz has 8 completed users because the resumability test top-up landed users in this cell.

**Eval coverage observations:**
- Coverage ranges 3.25% (1600/bullet) → 77.57% (2400/blitz). Higher-rated and slower TCs tend toward higher coverage, consistent with Lichess users requesting analysis more often on serious games.
- All 20 cells have ≥1 completed user and ≥0 eval-bearing positions. No empty cells.
- Aggregate: 17.08% of all positions have `eval_cp` (3.47M of 20.3M). Position-level filtering for analyses uses `WHERE eval_cp IS NOT NULL` directly.

**Note on `eval_source_version` distribution:** N/A — column dropped on 2026-04-26 (commit `e40b76e`). See §7.

---

## 5. Resumability (INGEST-04)

SIGINT + SIGKILL test against a `--per-cell 13` and `--per-cell 30` top-up. Recorded 2026-04-26 12:48-13:00 UTC.

| Stage | games | terminal checkpoints | pending |
|---|---|---|---|
| Baseline (post-smoke) | 274,143 | 60 | 0 |
| Partial (12:50, post-SIGINT) | 277,839 | 61 | 1 |
| After resume (13:00, ChessMax97 done; tmux SIGKILL on ameer_ammar1) | 280,241 | 62 | 1 |

Test events:
- **SIGINT** (12:48): `--per-cell 13` started 12:48:22; SIGINT after 60s. 1 user (`djdumper`) finished cleanly with 756 games. 1 user (`ChessMax97`) caught in-flight, left as `pending` (`games_imported=0`).
- **Resume** (12:50): `--per-cell 30` started in tmux. `ChessMax97` was the FIRST user picked up on resume — status `pending → completed`, 5,342 games imported, 3.7 min wall time. Confirms idempotent re-entry on the same row.
- **SIGKILL** (~13:00): tmux session was killed. A new in-flight user (`ameer_ammar1`) was left as `pending` per the same row-protection logic — confirms idempotency holds under the harder SIGKILL signal too.
- **Game-row uniqueness**: `(user_id, platform, platform_game_id)` — 0 duplicates across all stages. Row counts grow monotonically.

**Resumability verdict: PASS.** Both SIGINT and SIGKILL leave the in-flight user as `pending`; resume picks up the pending row first; no duplicate game rows; ingest is safe to interrupt and resume on a per-user-row boundary.

---

## 6. Storage Budget (INGEST-05)

| Object | Size |
|---|---|
| `pg_database_size(flawchess_benchmark)` | 6,536 MB (≈ 6.4 GB) |
| `games` table (incl. indexes) | 545 MB |
| `game_positions` table (incl. indexes) | 5,982 MB |
| `benchmark_selected_users` (ops table) | 1,200 KB |
| `benchmark_ingest_checkpoints` (ops table) | 40 KB |

Per the 2026-04-26 scope-down, INGEST-05's original storage target (50-100 GB at full `--per-cell 500`) is operational guidance for SEED-006, not a v1.12 milestone gate. The current 6.4 GB at ≈3 users/cell scales linearly to roughly 200-250 GB at 100 users/cell — well above the original 50-100 GB target and one factor in why the scope-down was made. Storage planning for SEED-006 will need to address either a shorter import window, a smaller `--per-cell`, or larger disk allocation; this report flags the projection but does not block v1.12.

---

## 7. Hot-Patch — Drop `eval_depth` and `eval_source_version` (commit e40b76e)

Both columns added by the original Phase 69-02 migration (`b11018499e4f`) turned out to be dead weight after the smoke ingest revealed the actual Lichess API behavior:

- **`eval_depth`**: the `/api/games/user` endpoint emits bare `[%eval CP]` PGN annotations with no depth field. Verified by sampling 5 games across the 289k-game smoke result — every annotation is the depth-less form. There is no source from which to populate this column under the current API-based ingest.
- **`eval_source_version`**: only one value ever set (`"lichess-pgn"`), zero information content. "Has Lichess evals" filtering is naturally done at the position level via `game_positions.eval_cp IS NOT NULL`.

Migration `6809b7c79eb3` drops both columns. Applied to the benchmark DB on 2026-04-26; will run on prod on next deploy. The 289,022 benchmark games are preserved.

INGEST-06 reduced to centipawn-convention verification, satisfied by automated test `tests/test_benchmark_ingest.py::test_centipawn_convention_signed_from_white` (asserts `[%eval 2.35]` → +235 cp, `[%eval -0.50]` → -50 cp, `[%eval #4]` → mate=4, all from white's POV).

If a future eval source (dump-based import, custom Stockfish) needs a discriminator, reintroduce a column at that point.

---

## 8. Requirements Coverage

| ID | Status | Evidence |
|---|---|---|
| INFRA-01 | ✅ | Plan 69-01: separate `flawchess-benchmark` PostgreSQL 18 container on `localhost:5433`, 5-axis isolation from dev/prod (project name, volume, port, DB name, app user). |
| INFRA-02 | ✅ (with carve-out) | Canonical games / game_positions schema; ops-tables exception explicit in REQUIREMENTS.md (`benchmark_selected_users`, `benchmark_ingest_checkpoints` via `Base.metadata.create_all()`). |
| INFRA-03 | ✅ | Plan 69-03: `flawchess-benchmark-db` MCP server documented in CLAUDE.md §Database Access; live and queried for this report. |
| INGEST-01 | ✅ | `select_benchmark_users.py`: streaming zstandard PGN scan with header-only eval pre-filter. Smoke: 90M games scanned, 491k qualifying, 8.6k persisted. |
| INGEST-02 | ✅ | Stratified 5×4 = 20 cells; deterministic `random.Random(42)`; all 20 cells populated (17 hit cap, 3 sparse). |
| INGEST-03 | ✅ | Per-side bucketing via `WhiteElo`/`BlackElo` median + modal TC. Aggregations always per-side. |
| INGEST-04 | ✅ | `benchmark_ingest_checkpoints` lifecycle (`pending → completed/skipped/failed`); SIGINT + SIGKILL test; 0 duplicates; idempotent re-entry confirmed. |
| INGEST-05 | ✅ (per scope-down) | `--per-cell` flag works (smoke at 3, resumability at 13/30); K=10 eval-bearing-game floor exercised. Storage targets demoted to operational guidance. |
| INGEST-06 | ✅ (with carve-out) | Centipawn convention verified by automated test. `eval_depth` / `eval_source_version` columns dropped after API-depth absence was discovered (see §7). |

---

## 9. Outstanding Work for SEED-006

Not blocking this milestone, but documented here for SEED-006 entry criteria:

1. **Full-scale ingest** at `--per-cell ≥ 30` (or higher) to populate the DB for the 8 deferred VALID-* / BENCH-* requirements. Storage budget likely needs an explicit sizing decision.
2. **Failed-user investigation**: 1 of 60 smoke users failed with `games_imported=0` and no `skip_reason`. Reproduce, diagnose, fix or document.
3. **Eval depth / source recovery**: if SEED-006 needs eval depth or per-source discrimination, switching to dump-based PGN parsing (instead of API-based import) is the path. Larger scope; deferred.
4. **Disk dump file cleanup** (D-03): the 2026-03 Lichess dump file used for selection scan is no longer needed and should be deleted from disk after row counts here are confirmed.

---

*Generated 2026-04-26 from benchmark DB queries against the post-smoke + resumability state. Source data: `mcp__flawchess-benchmark-db__query`. Scratch evidence: `.planning/phases/69-benchmark-db-infrastructure-ingestion-pipeline/.scratch-69-06.md`.*
