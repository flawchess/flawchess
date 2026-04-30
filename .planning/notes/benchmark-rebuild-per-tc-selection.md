---
title: Benchmark DB rebuild — per-TC selection, perfType + max truncation, drop 20k skip
date: 2026-04-30
context: Captured during session reviewing `reports/benchmarks-2026-04-30.md`. The current benchmark DB suffers three composable issues that all resolve cleanly together. Decision: rebuild the benchmark DB from scratch with `--per-cell 100` after the fixes land.
related_files:
  - scripts/select_benchmark_users.py
  - scripts/import_benchmark_users.py
  - app/services/lichess_client.py
  - app/models/benchmark_selected_user.py
  - app/models/benchmark_ingest_checkpoint.py
  - .claude/skills/benchmarks/SKILL.md
  - reports/benchmarks-2026-04-30.md (will become stale on rebuild)
related_seeds: [SEED-006, SEED-009]
---

# Benchmark DB rebuild — per-TC selection, perfType + max truncation

## Problems being solved (all in one rebuild)

### 1. Mode-based selection excludes strong-classical cohorts

`select_benchmark_users.py` buckets each player to exactly one TC via `Counter(tcs).most_common(1)[0][0]` (modal TC across all their snapshot-month games). Players whose mode is bullet/blitz never enter the classical pool even if they have a substantial classical history.

Evidence from the current DB (avg games per user, currently classical-bucketed users):

| ELO  | classical | bullet | blitz | rapid | total | classical share |
|------|-----------|--------|-------|-------|-------|-----------------|
| 800  | 107       | 40     | 26    | 121   | 294   | 36% (rapid wins) |
| 1200 | 279       | 5      | 19    | 229   | 533   | 52% |
| 1600 | 534       | 32     | 96    | 225   | 887   | 60% |
| 2000 | 620       | 228    | 209   | 191   | 1,248 | 50% |
| 2400 | 508       | 229    | 442   | 161   | 1,340 | **38% (blitz wins!)** |

Classical-2400 users *already in the classical pool* play more blitz than classical. The 9133 selection pool was thinnest at classical-2400 (40 ingested, can't reach `--per-cell 100`) precisely because mode-eligibility kicks out the multi-TC strong players. Per-TC eligibility (a user qualifies for the classical cell if they have ≥K classical eval games in the snapshot, regardless of their other TCs) should multiply the candidate pool 2-4× for that cell.

A second, quieter bug: median Elo today is computed across all TCs. A 1900-blitz / 2200-classical specialist gets a single ~2050 median that mis-buckets at least one of their TCs. Per-TC median fixes this.

### 2. 20k post-hoc skip wastes resources and contaminates queries

`HARD_SKIP_THRESHOLD = 20_000` in `import_benchmark_users.py` triggers AFTER the import already persisted every game. Current state: 37 users marked `status='skipped'` (avg 31k games each, max 77k); their games stay in the DB. The `/benchmarks` skill's `selected_users` CTE doesn't filter on checkpoint status, so these 37 leak into all results — they're 3.8% of users but ~30% of bullet/blitz game volume.

`max=N` on the lichess API solves both: cap server-side, never download the long tail, eliminate the skip path entirely.

### 3. PerfType filter unused — fetches games we discard

`lichess_client.py:82-86` documents that `perfType` causes silent truncation for general FlawChess imports (excludes correspondence/chess960/from-position). For *benchmark* fetches, where every (user, cell) is bucketed to one TC and we don't want correspondence/chess960 anyway, this is exactly the desired behavior — turn the footgun into a feature, opt-in via a new param.

## Design

### Schema changes

Both benchmark tables need their unique constraint relaxed from `(lichess_username)` to `(lichess_username, tc_bucket)`:

`app/models/benchmark_selected_user.py:39`:
```python
# Before
UniqueConstraint("lichess_username", name="uq_benchmark_selected_users_username")
# After
UniqueConstraint("lichess_username", "tc_bucket", name="uq_benchmark_selected_users_username_tc")
```

`app/models/benchmark_ingest_checkpoint.py:38`:
```python
# Before
UniqueConstraint("lichess_username", name="uq_benchmark_ingest_checkpoints_username")
# After
UniqueConstraint("lichess_username", "tc_bucket", name="uq_benchmark_ingest_checkpoints_username_tc")
```

Update the docstrings of both models to reflect that one user can occupy multiple cells (one per qualifying TC).

INFRA-02: benchmark tables are not in the canonical Alembic chain. Tables are created via `metadata.create_all()` on first invocation. Rebuild path: drop the benchmark DB volume and let the scripts recreate everything (see Rebuild procedure below). No migration file needed.

### `app/services/lichess_client.py` — add `max_games` and `perf_type` params

```python
async def fetch_lichess_games(
    client: httpx.AsyncClient,
    username: str,
    user_id: int,
    since_ms: int | None = None,
    max_games: int | None = None,           # NEW
    perf_type: str | None = None,           # NEW: "bullet"|"blitz"|"rapid"|"classical"
    on_game_fetched: Callable[[], None] | None = None,
) -> AsyncIterator[NormalizedGame]:
    ...
    if since_ms is not None:
        params["since"] = str(since_ms)
    if max_games is not None:
        params["max"] = str(max_games)
    if perf_type is not None:
        # Opt-in: silent-truncation behavior is desired for benchmark ingest
        # (filters server-side to one TC; correspondence/chess960/fromPosition
        # are excluded, which matches benchmark requirements).
        params["perfType"] = perf_type
```

Defaults are `None` so user-facing imports are unchanged.

`run_import` in `app/services/import_service.py` will need to thread these params through to `fetch_lichess_games`. Add `max_games` and `perf_type` as optional kwargs on whatever entry point the benchmark orchestrator calls; for the FlawChess user-facing import flow, pass `None` (current behavior).

### `scripts/select_benchmark_users.py` — per-TC eligibility & per-TC median Elo

Replace the bucketing logic in `bucket_players` and the per-player aggregation in `scan_dump_for_players`:

```python
# Today: PlayerStats has flat lists of elos and tcs across all games.
# After: index per-TC.
class PlayerStats(TypedDict):
    elos_by_tc: dict[str, list[int]]    # tc -> list of Elo at game time
    eval_count_by_tc: dict[str, int]    # tc -> count of eval-bearing games

def scan_dump_for_players(...) -> dict[str, PlayerStats]:
    ...
    for record in parse_pgn_stream(text_stream):
        tc = compute_tc_bucket(record["time_control"])
        if tc is None:
            continue
        for username, elo in sides:
            if not username or elo is None:
                continue
            stats = player_stats[username]
            stats["elos_by_tc"][tc].append(elo)
            if record["has_eval"]:
                stats["eval_count_by_tc"][tc] = stats["eval_count_by_tc"].get(tc, 0) + 1

def bucket_players(player_stats, eval_threshold) -> dict[tuple[int, str], list[str]]:
    """Each user can produce up to 4 (rating_bucket, tc) entries — one per
    TC where they meet the per-TC eval threshold."""
    out: dict[tuple[int, str], list[str]] = defaultdict(list)
    for username, stats in player_stats.items():
        for tc, elos in stats["elos_by_tc"].items():
            if not elos:
                continue
            if stats["eval_count_by_tc"].get(tc, 0) < eval_threshold:
                continue
            sorted_elos = sorted(elos)
            median_elo_in_tc = sorted_elos[len(sorted_elos) // 2]
            rb = _rating_bucket(median_elo_in_tc)
            if rb is None:
                continue
            out[(rb, tc)].append(username)
    return out
```

Persistence (`persist_selection`) updates:
- `median_elos` becomes `median_elos_by_tc: dict[tuple[str, str], int]` keyed by `(username, tc)`.
- `eval_counts` becomes `eval_counts_by_tc: dict[tuple[str, str], int]`.
- The dedup `existing` set must be keyed on `(username, tc)` not just username, matching the new compound unique constraint.

CLI args unchanged (`--per-cell 500` etc).

### `scripts/import_benchmark_users.py` — per-(user, tc) jobs with `perfType` and `max=2000`

Constants:
```python
HARD_SKIP_THRESHOLD = 20_000   # DELETE — superseded by max=2000
MAX_GAMES_PER_USER_TC = 2000   # NEW: lichess `max` param per (user, tc)
WINDOW_MONTHS = 36              # keep — used as `since` floor
```

Logic changes:
1. `_load_cell_data`: pool now keyed `(lichess_username, tc_bucket)` since users can appear in multiple cells. Already grouped by cell — minor refactor needed because `compute_deficit_users` currently dedups on username alone; change to dedup on `(username, tc)` keys.
2. `compute_deficit_users` signature: change `pool: list[str]` and `completed: set[str]` to `list[tuple[str, str]]` and `set[tuple[str, str]]`. The orchestrator already iterates per-cell, so this is largely renaming.
3. `_upsert_checkpoint_pending` / `_update_checkpoint`: lookup key is `(lichess_username, tc_bucket)` not just `lichess_username`. Add `tc_bucket` to the WHERE clause in both.
4. `_import_one_user`: thread `tc_bucket` into the `run_import` call. Add `max_games=MAX_GAMES_PER_USER_TC` and `perf_type=tc_bucket` to whatever entry point passes through to `fetch_lichess_games`. Drop the `_should_hard_skip` branch — it's now dead.
5. Stub user (`create_stub_user`): unchanged, one User per real lichess_username. Multiple ImportJob rows per user is fine.
6. `synthetic_job` pre-seed: keep the `last_synced_at = window_start` trick. Adjust to be per-(user, platform=lichess, perf_type) if `get_latest_for_user_platform` needs to differentiate; otherwise one synthetic_job per user is fine because subsequent calls to `run_import` for the same user with different `perf_type` will replay against the same cursor (which is OK because `bulk_insert_games` dedups on natural key).

Acceptance smoke test: a single user who qualifies in (2000, bullet) and (2000, classical) should produce two checkpoint rows, two `benchmark_selected_users` rows, and end up with ≤2000 bullet games + ≤2000 classical games in the `games` table.

### `.claude/skills/benchmarks/SKILL.md` — minor cleanup

The SKILL queries already filter `g.time_control_bucket::text = bsu.tc_bucket`, which works correctly when one user appears in multiple `benchmark_selected_users` rows (each row contributes only its TC's games). Two changes needed:

1. **Drop the proposed `WHERE bic.status = 'completed'` workaround** for the outlier-leak issue (memory: `project_benchmark_outliers_unfiltered.md`). After the rebuild, `over_20k_games` is impossible — `max=2000` truncates pre-fetch. The memory file can be marked obsolete or deleted after the rebuild verifies.
2. **Update the report-header caveat** about per-user history. With `max=2000` per (user, tc), the time-spread per user shrinks substantially. Adjust the "rating_bucket = rating-at-snapshot, history runs up to 3yr" caveat to reflect the new bound.

No changes to query SQL beyond those caveats.

### `reports/benchmarks-2026-04-30.md`

Becomes stale on rebuild. Keep it for historical reference; do NOT regenerate today's filename. Next `/benchmarks` run produces a fresh dated file.

## Rebuild procedure

Run after all code changes land. Order matters:

1. **Stop the benchmark DB**: `bin/benchmark_db.sh stop`
2. **Drop the benchmark volume**: `docker volume rm flawchess-benchmark_db_data` (verify the exact name with `docker volume ls | grep benchmark`).
3. **Restart**: `bin/benchmark_db.sh start`. The Docker init script creates the empty DB + read-only role; the new selection script will create `benchmark_selected_users` and `benchmark_ingest_checkpoints` with the new compound unique constraints on first invocation.
4. **Run alembic upgrade head** against the benchmark DB to recreate the canonical tables (`users`, `games`, `game_positions`, etc.):
   ```
   DATABASE_URL=postgresql+asyncpg://flawchess_benchmark:flawchess_benchmark@localhost:5433/flawchess_benchmark \
     uv run alembic upgrade head
   ```
5. **Run user selection** against the existing 2026-03 dump:
   ```
   uv run python scripts/select_benchmark_users.py \
     --dump-path /path/to/lichess_db_standard_rated_2026-03.pgn.zst \
     --dump-month 2026-03 \
     --per-cell 500 \
     --eval-threshold 5 \
     --db-url postgresql+asyncpg://flawchess_benchmark:flawchess_benchmark@localhost:5433/flawchess_benchmark
   ```
   Validate per-cell candidate counts (esp. classical-2400 — should rise from current ~40 to several hundred).
6. **Dry-run the ingest**:
   ```
   DATABASE_URL=postgresql+asyncpg://flawchess_benchmark:flawchess_benchmark@localhost:5433/flawchess_benchmark \
     uv run python scripts/import_benchmark_users.py \
       --per-cell 100 \
       --snapshot-month-end 2026-03-31 \
       --dry-run
   ```
   Should report ~2000 (user, tc) pairs to import (5 ELO × 4 TC × ~100/cell, modulo qualified pool sizes).
7. **Run the ingest**: same command without `--dry-run` (and with `--yes` if running unattended). Plan for several hours of wall-clock time. Resumable on SIGINT.
8. **Verify**:
   - Row count in `benchmark_selected_users` ≈ ~1500-2000 (some users in multiple cells).
   - Row count in `benchmark_ingest_checkpoints` with `status='skipped'` should be **0** (the over-20k skip path is removed; the only remaining skip reasons are runtime errors).
   - Per-cell user count via the §0 sanity query in SKILL.md should hit ~100 in every cell, including classical-2400.
   - Spot-check 2-3 users with multi-TC membership: verify each (user, tc) has its own checkpoint row and game volume ≤2000 per TC.
9. **Run `/benchmarks`** to produce the new report, compare to `reports/benchmarks-2026-04-30.md`. Expected effects:
   - Bullet/blitz pooled stats shift (no more 31k-game outliers contaminating the pool).
   - Classical-2400 cells reach n≥30 in §3/§4 (previously dropped at the sample floor).
   - Endgame-class breakdowns for classical/2400 stabilize.
   - Most TC verdicts probably unchanged in direction; magnitudes can move.

## Decisions locked in 2026-04-30 explore session

1. **Cap value: `MAX_GAMES_PER_USER_TC = 1000`** (not 2000). Halves bullet/blitz wall-clock and disk vs the original proposal. Per-user metric stability barely moves (√2 effect on per-user SE, well below the across-user variance that drives the cohort distributions). Classical/rapid users almost never hit the cap regardless. Easy to bump later by re-running with `max=2000` — `bulk_insert_games` dedups, so it extends history rather than re-fetching.

2. **Cursor handling: option (a) — pass `since_ms` explicitly into `run_import`** (do NOT extend `import_jobs` with a `perf_type`-scoped cursor). The same lichess user can be imported once per TC; the second TC run must not see the first TC's `last_synced_at` via `get_latest_for_user_platform`. Mechanism: add `since_ms_override: int | None` to `JobState`, accept it in `create_job(...)`, and have `_make_game_iterator` use it instead of consulting `previous_job` when set. The synthetic-ImportJob pre-seed in `import_benchmark_users.py` becomes obsolete and should be deleted — the override replaces it. User-facing imports pass `None` and behavior is unchanged.

3. **Per-cell sampling stays random with seed=42**, but `persist_selection`'s username dedup must change to compound `(username, tc_bucket)`. Today the dedup is global by username (line 319, 330–343 of `select_benchmark_users.py`); without this change, multi-cell membership is silently still suppressed even after the DB-level unique constraint is relaxed. Expected incidental overlap with the fix in: ~0–10 users sitting in two cells across an entire ELO bucket, near zero in three. Random + small overlap is exactly the desired property — multi-TC qualifiers contribute incidentally, not systematically.

4. **`perf_type` × `since` interaction**: the lichess API returns "up to N most-recent games matching since AND perfType". This is exactly what we want — no edge case.

5. **Existing `benchmark_selected_users` rows with `dump_month='2026-03'`**: discarded entirely on volume drop (step 2 of rebuild). If we later want cross-dump pooling, re-running selection with a second dump (e.g. `2025-12`) appends with that month's `dump_month` tag, and the new compound-unique constraint allows the same user to appear in cross-month rows for different cells.

6. **Memory file `project_benchmark_outliers_unfiltered.md`**: delete after rebuild verification. The bug it documents will no longer apply.

7. **Tests**: update tests to match the new per-TC behavior rather than preserve the old shape. `PlayerStats` shape changes (`elos` / `tcs` / `eval_count` → `elos_by_tc` / `eval_count_by_tc`), so any test constructing `PlayerStats` directly will fail and should be rewritten. Do not preserve old fixtures or shim the new code to satisfy them. Add the new per-TC bucketing test from the acceptance criteria.

## Out of scope (do NOT bundle)

- Skill v2 collapse-verdict methodology (separate todo: `2026-04-30-benchmark-skill-v2-build.md`). This rebuild fixes data quality; skill v2 changes report shape.
- Cross-monthly-dump pooling for classical-2400. Try the per-TC fix on the existing 2026-03 dump first; if classical-2400 still under-samples, that's a follow-up.
- Re-running SEED-006 Phase 70/71/72/73 plans. Those run AFTER this rebuild because they consume the populated DB.
