---
created: 2026-04-30T00:00:00.000Z
title: Rebuild benchmark DB — per-TC selection, perfType + max=2000 truncation
area: scripts / benchmark infrastructure
files:
  - scripts/select_benchmark_users.py
  - scripts/import_benchmark_users.py
  - app/services/lichess_client.py
  - app/services/import_service.py
  - app/models/benchmark_selected_user.py
  - app/models/benchmark_ingest_checkpoint.py
  - .claude/skills/benchmarks/SKILL.md
related_notes:
  - .planning/notes/benchmark-rebuild-per-tc-selection.md
related_seeds: [SEED-006, SEED-009]
---

## Why

Three issues found while reviewing `reports/benchmarks-2026-04-30.md` resolve cleanly together:

1. Mode-based user selection excludes strong-classical players who happen to play more bullet/blitz — classical-2400 is sample-starved (40 users, can't reach `--per-cell 100`).
2. The 20k post-hoc skip is wasteful (full import then mark skipped) and the SKILL queries don't filter skipped users out, so 37 outliers (avg 31k games each) contaminate bullet/blitz cells (~30% game-volume bias).
3. `perfType` lichess API param is unused; with per-TC selection it lets us fetch only the games that count for each (user, cell).

Full design in `.planning/notes/benchmark-rebuild-per-tc-selection.md`. This todo is the build checklist.

## What — implementation order

### 1. Lichess client (`app/services/lichess_client.py`)

Add two optional params to `fetch_lichess_games`:
- `max_games: int | None = None` → `params["max"]`
- `perf_type: str | None = None` → `params["perfType"]` (opt-in; preserves the user-facing-import behavior the existing comment documents)

### 2. Import service (`app/services/import_service.py`) — three-file thread-through

Add three optional fields to `JobState` (or equivalent in-memory job record): `max_games: int | None`, `perf_type: str | None`, `since_ms_override: int | None`. `create_job(...)` accepts and stores them. `_make_game_iterator` reads them off `job` and:
- For `lichess`: uses `since_ms_override` instead of consulting `previous_job` when it is not `None`; passes `max_games` and `perf_type` through to `fetch_lichess_games`.
- For `chess.com`: leave unchanged (benchmark imports are lichess-only).

This is the locked answer to the cursor question (option (a) in the design note): benchmark callers supply `since_ms_override` directly, bypassing `get_latest_for_user_platform`. Do **not** modify `get_latest_for_user_platform`, `import_jobs` schema, or any user-facing import path. With `since_ms_override=None` and `max_games=None` and `perf_type=None`, behavior is byte-for-byte identical to today.

### 3. Schema (`app/models/benchmark_selected_user.py`, `app/models/benchmark_ingest_checkpoint.py`)

Both `UniqueConstraint` declarations: change from `("lichess_username", ...)` to `("lichess_username", "tc_bucket", ...)`. Update model docstrings. No Alembic migration — benchmark tables use `metadata.create_all()`, recreated on rebuild.

### 4. Selection script (`scripts/select_benchmark_users.py`)

- `PlayerStats`: index by TC (`elos_by_tc: dict[str, list[int]]`, `eval_count_by_tc: dict[str, int]`).
- `bucket_players`: a user can produce up to 4 entries (one per qualifying TC). Per-TC eligibility (≥K eval games in that TC) AND per-TC median Elo for bucketing.
- `persist_selection`:
  - `median_elos` becomes `median_elos_by_tc: dict[tuple[str, str], int]` keyed `(username, tc)`.
  - `eval_counts` becomes `eval_counts_by_tc: dict[tuple[str, str], int]`.
  - **Critical: change the `existing` dedup set from `set[str]` (username only) to `set[tuple[str, str]]` keyed `(username, tc_bucket)`**. Today's global username dedup silently suppresses multi-cell membership even after the DB-level constraint is relaxed. Match it to the new compound unique constraint.
- Per-cell random sampling (`rng.shuffle(...); chosen = shuffled[:per_cell]`, `seed=42`) is unchanged. Multi-cell membership becomes possible but incidental (0–10 users per ELO bucket overlap two cells, near zero in three) — exactly the desired property.

### 5. Import script (`scripts/import_benchmark_users.py`)

- Delete `HARD_SKIP_THRESHOLD = 20_000` and `_should_hard_skip`. Add `MAX_GAMES_PER_USER_TC = 1000`.
- `compute_deficit_users`: signature stays `(pool, completed, target_n)`; the orchestrator already loops per-cell so `pool`/`completed` are naturally cell-scoped. No tuple-key refactor needed inside this function.
- `_load_cell_data`: unchanged — already filters by both `rating_bucket` AND `tc_bucket`.
- Checkpoint helpers (`_upsert_checkpoint_pending`, `_update_checkpoint`): WHERE includes both `lichess_username` AND `tc_bucket`.
- **Delete the synthetic ImportJob pre-seed block** in `_import_one_user` (the `synthetic_job = ImportJob(...)` insert, lines ~323–336). Replace with computing `since_ms = int(window_start.timestamp() * 1000)` and passing it through `create_job(..., since_ms_override=since_ms, max_games=MAX_GAMES_PER_USER_TC, perf_type=tc_bucket)`. This is the cursor-handling change locked in the note.
- Drop the `_should_hard_skip` branch and the `over_20k_games` skip path in `_import_one_user` outright. Update the docstring at the top of the file: remove the D-14 paragraph; replace with one describing `MAX_GAMES_PER_USER_TC` truncation at the lichess API.
- Stub user creation: unchanged (one User per real username, idempotent).

### 6. SKILL.md (`.claude/skills/benchmarks/SKILL.md`)

- No SQL changes (existing `g.time_control_bucket = bsu.tc_bucket` filter already correctly handles users in multiple cells).
- Update header caveats: `max=2000` per (user, tc) bounds the per-user history; the rating-bucket-vs-rating-at-game-time caveat shrinks accordingly.
- Drop the "warning about over-20k contamination" memory note (`project_benchmark_outliers_unfiltered.md`) — bug is gone post-rebuild.

### 7. Rebuild

Run the procedure in `.planning/notes/benchmark-rebuild-per-tc-selection.md` §"Rebuild procedure" steps 1–8.

### 8. Verify

- Per-cell user count = ~100 in every cell, including classical-2400.
- `status='skipped'` count = 0.
- Spot-check 2-3 multi-TC users: each (user, tc) has its own checkpoint row, ≤2000 games per TC.
- Run `/benchmarks`, compare new report to `reports/benchmarks-2026-04-30.md`.

## Acceptance criteria

- All 6 code areas updated as above.
- **Tests are updated to match the new behavior, not used to enforce the old behavior.** Existing tests that construct `PlayerStats` with the old shape (`elos`/`tcs`/`eval_count`) will fail and must be rewritten with the new per-TC shape (`elos_by_tc`/`eval_count_by_tc`). Tests asserting one-cell-per-user must be updated for multi-cell qualification. Do not shim the new code to satisfy old fixtures.
- New unit test covers per-TC bucketing: a synthetic player with 50 bullet + 50 classical eval games at distinct medians produces both a (rb, bullet) and a (rb, classical) entry with the correct per-TC medians.
- New unit test covers `persist_selection` compound dedup: same `(username, tc)` is skipped on re-run, but `(username, "bullet")` and `(username, "classical")` both insert.
- Rebuild completes; verification queries above all green.
- New benchmark report regenerated; classical-2400 cells exit "thin sample" status (n_users ≥ 50 in every §1-§4 cell after sample floors).

## Out of scope

- Skill v2 collapse-verdict overhaul — separate todo `2026-04-30-benchmark-skill-v2-build.md`.
- Cross-dump pooling — try the per-TC fix on 2026-03 alone first.
- Phase 70/71/72/73 (SEED-006) work — runs after this rebuild stabilizes the data.
