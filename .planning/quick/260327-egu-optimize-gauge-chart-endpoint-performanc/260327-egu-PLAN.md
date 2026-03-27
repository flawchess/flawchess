---
phase: quick
plan: 260327-egu
type: execute
wave: 1
depends_on: []
files_modified:
  - app/repositories/endgame_repository.py
  - app/services/endgame_service.py
  - app/models/game_position.py
  - alembic/versions/*_add_covering_index_for_endgame_queries.py
autonomous: true
requirements: []
must_haves:
  truths:
    - "GET /api/endgames/performance responds significantly faster than before"
    - "Gauge chart data is identical to pre-optimization output"
  artifacts:
    - path: "app/repositories/endgame_repository.py"
      provides: "Dedicated conversion/recovery aggregate query"
    - path: "app/services/endgame_service.py"
      provides: "Parallelized query execution in get_endgame_performance"
    - path: "app/models/game_position.py"
      provides: "Covering index for endgame GROUP BY queries"
  key_links:
    - from: "app/services/endgame_service.py"
      to: "app/repositories/endgame_repository.py"
      via: "query_conversion_recovery_aggregates import"
      pattern: "query_conversion_recovery_aggregates"
---

<objective>
Optimize the GET /api/endgames/performance endpoint that feeds the gauge charts.

Root cause: `get_endgame_performance` runs two heavy sequential query batches:
1. `query_endgame_performance_rows` (2 queries via asyncio.gather) for WDL comparison
2. `get_endgame_stats` (calls `query_endgame_entry_rows` + `count_filtered_games`) just to extract aggregate conversion/recovery counts

The second call is the full WDL stats orchestrator — it fetches ALL per-(game, class) rows into Python, aggregates 6 categories, counts total games — all to extract 4 numbers (conversion_wins, conversion_games, recovery_saves, recovery_games). This is massively redundant.

Fix: (1) Write a dedicated SQL aggregate query for conversion/recovery, (2) run it concurrently with the WDL query, (3) add a covering index for the common GROUP BY pattern.

Purpose: Make gauge charts load as fast as other endgame stats.
Output: Optimized endpoint, new repository query, covering index migration.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@app/repositories/endgame_repository.py
@app/services/endgame_service.py
@app/models/game_position.py
@app/schemas/endgames.py
@tests/test_endgame_service.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add covering index and dedicated conversion/recovery aggregate query</name>
  <files>
    app/models/game_position.py,
    app/repositories/endgame_repository.py,
    alembic/versions/*_add_covering_index_for_endgame_queries.py
  </files>
  <action>
1. In `app/models/game_position.py`, add a covering index for endgame GROUP BY queries. The existing partial index `ix_gp_user_endgame_class` has `(user_id, endgame_class)` but queries GROUP BY `game_id` and need `ply` for COUNT. Add:
   ```python
   Index(
       "ix_gp_user_endgame_game",
       "user_id", "game_id", "endgame_class", "ply",
       postgresql_where=text("endgame_class IS NOT NULL"),
   ),
   ```
   This covers the common pattern: `WHERE user_id = ? AND endgame_class IS NOT NULL GROUP BY game_id [, endgame_class] HAVING COUNT(ply) >= 6`. The index-only scan avoids hitting the heap for these aggregation queries.

2. In `app/repositories/endgame_repository.py`, add a new function `query_conversion_recovery_aggregates` that computes the 4 aggregate values directly in SQL instead of fetching all rows:

   The query should:
   - Reuse the same `span_subq` and `entry_pos_subq` JOIN pattern from `query_endgame_entry_rows`
   - JOIN Game for `result`, `user_color` (needed to derive outcome)
   - Return raw rows of `(endgame_class_int, result, user_color, user_material_imbalance)` — same shape as `query_endgame_entry_rows` but WITHOUT `game_id` (not needed for aggregation)
   - Apply `_apply_game_filters`

   Actually, on reflection: the aggregation in `_aggregate_endgame_stats` uses Python logic (`derive_user_result`) which is hard to replicate in SQL. The real win is NOT in changing the query shape but in:
   - Running the entry_rows query CONCURRENTLY with the performance_rows query
   - Skipping the redundant `count_filtered_games` call (not needed for gauge values)

   So instead: add a lightweight wrapper `query_endgame_entry_rows_for_aggregation` that is just `query_endgame_entry_rows` (same query, same result) but named distinctly for clarity. OR simply import and call `query_endgame_entry_rows` directly from `get_endgame_performance`.

3. Generate Alembic migration: `uv run alembic revision --autogenerate -m "add covering index for endgame queries"`

   Review the migration to ensure it only contains the new index creation and no unrelated column type noise (Float(24)/REAL). Remove any spurious alter_column ops if present.
  </action>
  <verify>
    <automated>cd /home/aimfeld/Projects/Python/flawchess && uv run alembic upgrade head && uv run pytest tests/test_endgame_service.py -x</automated>
  </verify>
  <done>Covering index exists in model and migration. All existing endgame tests pass.</done>
</task>

<task type="auto">
  <name>Task 2: Parallelize queries in get_endgame_performance and eliminate redundant get_endgame_stats call</name>
  <files>app/services/endgame_service.py</files>
  <action>
Refactor `get_endgame_performance` to eliminate the sequential `get_endgame_stats` call:

1. Replace the sequential flow:
   ```python
   # BEFORE (sequential, redundant)
   endgame_rows, non_endgame_rows = await query_endgame_performance_rows(...)
   # ... build WDL ...
   stats = await get_endgame_stats(...)  # HEAVY: runs query_endgame_entry_rows + count_filtered_games
   # ... extract 4 numbers from stats ...
   ```

   With concurrent execution:
   ```python
   # AFTER (concurrent, no redundancy)
   import asyncio

   (endgame_rows, non_endgame_rows), entry_rows = await asyncio.gather(
       query_endgame_performance_rows(
           session, user_id=user_id,
           time_control=time_control, platform=platform,
           rated=rated, opponent_type=opponent_type,
           recency_cutoff=cutoff,
       ),
       query_endgame_entry_rows(
           session, user_id=user_id,
           time_control=time_control, platform=platform,
           rated=rated, opponent_type=opponent_type,
           recency_cutoff=cutoff,
       ),
   )
   ```

2. After getting `entry_rows`, compute conversion/recovery aggregates inline using `_aggregate_endgame_stats(entry_rows)` (already imported/available), then sum across categories — same logic as before but without the redundant `count_filtered_games` call:
   ```python
   categories = _aggregate_endgame_stats(entry_rows)
   total_conversion_wins = sum(c.conversion.conversion_wins for c in categories)
   total_conversion_games = sum(c.conversion.conversion_games for c in categories)
   total_recovery_saves = sum(c.conversion.recovery_saves for c in categories)
   total_recovery_games = sum(c.conversion.recovery_games for c in categories)
   ```

3. This eliminates:
   - The redundant `count_filtered_games` query (not needed for gauge values)
   - The sequential blocking — both query batches now run concurrently
   - Total query reduction: from 4 queries (2 sequential batches) to 4 queries (1 concurrent batch, since `query_endgame_performance_rows` internally runs 2 via gather, and `query_endgame_entry_rows` is 1 query)

4. Add a comment explaining why we call `query_endgame_entry_rows` directly instead of `get_endgame_stats`:
   ```python
   # Fetch entry rows directly (not via get_endgame_stats) to avoid redundant
   # count_filtered_games query and enable concurrent execution with performance rows.
   ```
  </action>
  <verify>
    <automated>cd /home/aimfeld/Projects/Python/flawchess && uv run pytest tests/test_endgame_service.py -x -v</automated>
  </verify>
  <done>
    - get_endgame_performance runs queries concurrently via asyncio.gather
    - No more sequential get_endgame_stats call
    - Redundant count_filtered_games query eliminated
    - All existing tests pass with identical output
  </done>
</task>

</tasks>

<verification>
1. All endgame tests pass: `uv run pytest tests/test_endgame_service.py -x`
2. Full test suite passes: `uv run pytest -x`
3. Manual: hit GET /api/endgames/performance and verify response shape is unchanged
4. Lint: `uv run ruff check app/services/endgame_service.py app/repositories/endgame_repository.py app/models/game_position.py`
</verification>

<success_criteria>
- Gauge chart endpoint runs queries concurrently instead of sequentially
- Redundant get_endgame_stats call eliminated (saves 1-2 queries per request)
- Covering index speeds up GROUP BY game_id on game_positions
- All existing tests pass unchanged
- Response shape identical to pre-optimization
</success_criteria>

<output>
After completion, create `.planning/quick/260327-egu-optimize-gauge-chart-endpoint-performanc/260327-egu-SUMMARY.md`
</output>
