---
quick_id: 260414-smt
type: execute
wave: 1
depends_on: []
files_modified:
  - alembic/versions/NEW_MIGRATION.py
  - app/models/game.py
  - app/schemas/normalization.py
  - app/services/normalization.py
  - app/repositories/endgame_repository.py
  - app/services/endgame_service.py
  - app/schemas/endgames.py
  - frontend/src/components/charts/EndgameClockPressureSection.tsx
  - tests/test_normalization.py
  - tests/test_endgame_service.py
  - tests/test_endgame_repository.py
autonomous: true
must_haves:
  truths:
    - "games.base_time_seconds and games.increment_seconds columns exist and are backfilled from time_control_str for every existing row that can be parsed."
    - "New chess.com + lichess imports populate base_time_seconds and increment_seconds."
    - "_compute_clock_pressure uses per-game base_time_seconds as the % denominator — not bucket-first-seen time_control_seconds."
    - "_compute_time_pressure_chart uses per-game base_time_seconds as its bucketing denominator (same rule, for consistency)."
    - "Games where user_clock > 2 * base_time_seconds (or opp_clock > 2 * base_time_seconds) are excluded from pct accumulation and pct bucketing (bad data clamp)."
    - "The Time Pressure at Endgame Entry table displays % of base time as the primary value with absolute seconds as the secondary value (same 'NN% (Ns)' format stays, but label + popover text say 'base time'/'base clock')."
    - "All backend tests pass, ty passes with zero errors, ruff formats/lints clean, frontend build + lint + test all green."
  artifacts:
    - path: "alembic/versions/*base_time_seconds*.py"
      provides: "migration adding base_time_seconds + increment_seconds columns with backfill"
      contains: "op.add_column"
    - path: "app/models/game.py"
      provides: "Game.base_time_seconds and Game.increment_seconds mapped columns"
      contains: "base_time_seconds"
    - path: "app/services/normalization.py"
      provides: "parse_base_and_increment helper + populated fields on NormalizedGame"
      contains: "base_time_seconds"
    - path: "app/services/endgame_service.py"
      provides: "per-game base_time_seconds denominator + >2x clamp"
      contains: "base_time_seconds"
    - path: "app/repositories/endgame_repository.py"
      provides: "query_clock_stats_rows returns Game.base_time_seconds"
      contains: "base_time_seconds"
    - path: "frontend/src/components/charts/EndgameClockPressureSection.tsx"
      provides: "% of base time labeling + updated popover text"
      contains: "base"
  key_links:
    - from: "import pipeline (chess.com + lichess normalize)"
      to: "games.base_time_seconds / games.increment_seconds columns"
      via: "parse_base_and_increment + NormalizedGame schema"
      pattern: "base_time_seconds"
    - from: "_compute_clock_pressure"
      to: "Game.base_time_seconds (per row)"
      via: "query_clock_stats_rows SELECT"
      pattern: "base_time_seconds"
    - from: "_compute_time_pressure_chart"
      to: "Game.base_time_seconds (per row)"
      via: "query_clock_stats_rows SELECT"
      pattern: "base_time_seconds"
---

<objective>
Split `games.time_control` into two explicit fields — `base_time_seconds` (the
starting clock in seconds) and `increment_seconds` — then switch the Time Pressure
at Endgame Entry table and the Time Pressure vs Performance chart to divide by
the per-game base time instead of the broken bucket-first-seen
`time_control_seconds` estimate.

Purpose:
- Fix the "129% of time remaining at endgame entry" bug caused by two compounding
  defects: (1) `time_control_seconds` is an estimate (`base + increment*40`) that
  inflates rapid clocks, and (2) `_compute_clock_pressure` stores the first-seen
  estimate per bucket and divides every other game in the bucket by it — so an
  1800+0 game's 1500s clock is divided by 600 (= 250%).
- Surface a denominator that is apples-to-apples within a bucket: % of each
  game's own starting clock.

Output:
- Alembic migration adding `base_time_seconds` + `increment_seconds` (both
  `SmallInteger`, nullable) and backfilling from `time_control_str`.
- Both import paths (chess.com + lichess) populate the new fields.
- Per-game denominator + >2x clamp in both `_compute_clock_pressure` and
  `_compute_time_pressure_chart`.
- Updated frontend labels + popover text (desktop-only component; no mobile
  duplicate exists for this section — confirmed by Glob).
- Tests for parse_base_and_increment, per-game denominator behavior, and the
  >2x clamp.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
</execution_context>

<context>
@./CLAUDE.md
@.planning/STATE.md
@app/models/game.py
@app/services/normalization.py
@app/schemas/normalization.py
@app/services/endgame_service.py
@app/repositories/endgame_repository.py
@app/schemas/endgames.py
@frontend/src/components/charts/EndgameClockPressureSection.tsx
@tests/test_normalization.py
@tests/test_endgame_service.py
@tests/test_endgame_repository.py
@.planning/quick/260414-pv4-fix-time-pressure-queries-to-use-whole-g/260414-pv4-PLAN.md

<interfaces>
Current relevant contracts (from reads during planning):

Game model columns (app/models/game.py):
```python
time_control_str: Mapped[str | None]           # e.g. "600+0", "600+5", "1/259200"
time_control_bucket: Mapped[str | None]        # "bullet"|"blitz"|"rapid"|"classical"
time_control_seconds: Mapped[int | None]       # ESTIMATE: base + inc*40 (keep, do NOT drop)
# NEW (this plan):
base_time_seconds: Mapped[int | None]          # SmallInteger, nullable
increment_seconds: Mapped[int | None]          # SmallInteger, nullable
```

parse_time_control signature today (normalization.py:29):
```python
def parse_time_control(tc_str: str) -> tuple[TimeControlBucket | None, int | None]:
    # returns (bucket, estimated_seconds)
```
Keep this signature; add a sibling:
```python
def parse_base_and_increment(tc_str: str) -> tuple[int | None, int | None]:
    # returns (base_time_seconds, increment_seconds)
    # "600"     -> (600, 0)
    # "600+0"   -> (600, 0)
    # "600+5"   -> (600, 5)
    # "900+10"  -> (900, 10)
    # "10+0.1"  -> (10, 0)   # round/floor fractional inc to int (matches SmallInteger)
    # "1/259200"-> (None, None)  # daily, no fixed base clock
    # ""/"-"    -> (None, None)
```
Note: fractional inc like `10+0.1` — parse as float then `int(round(increment))`;
document why (SmallInteger). If 0 < inc < 1 would round to 0, still store 0 and
it's fine — won't affect denominator.

NormalizedGame (app/schemas/normalization.py): add
```python
base_time_seconds: int | None = None
increment_seconds: int | None = None
```

Row shape returned by query_clock_stats_rows (endgame_repository.py:698-711):
Currently: (game_id, time_control_bucket, time_control_seconds, termination,
           result, user_color, ply_array, clock_array)
CHANGE TO:  (game_id, time_control_bucket, base_time_seconds, termination,
             result, user_color, ply_array, clock_array)
(Replace `Game.time_control_seconds` with `Game.base_time_seconds` in the
SELECT. Consumers both read it as `row[2]`, so positional compat is preserved
— just rename the local `time_control_seconds` variable in both consumers to
`base_time_seconds`.)

ClockStatsRow (app/schemas/endgames.py:205):
Field names `user_avg_pct` / `opp_avg_pct` stay. Docstrings change:
```python
user_avg_pct: float | None  # mean (user_clock / base_time_seconds * 100); None if no base_time
opp_avg_pct:  float | None  # mean (opp_clock  / base_time_seconds * 100); None if no base_time
```

Frontend component: `frontend/src/components/charts/EndgameClockPressureSection.tsx`
— renders the "My avg time / Opp avg time" columns as `formatClockCell(pct, secs)`
which already outputs `"NN% (Ns)"`. No mobile variant exists (Glob confirms a
single file). Keep cell format; update column popover text to say "base time".

Constant to add (top of endgame_service.py near NUM_BUCKETS):
```python
# Clamp: games where either clock at endgame entry exceeds this multiple of
# base_time_seconds are treated as bad data (bogus clock readings, e.g. from
# adjudicated or disconnected games). 2x handles legitimate banked increment
# (p99 in prod is 109%).
MAX_CLOCK_PCT_OF_BASE = 2.0
```
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add base_time_seconds + increment_seconds columns, backfill migration, update import pipeline</name>
  <files>
    alembic/versions/NEW_MIGRATION.py,
    app/models/game.py,
    app/schemas/normalization.py,
    app/services/normalization.py,
    tests/test_normalization.py
  </files>
  <action>
1. **Model** (`app/models/game.py`): Add two mapped columns right after
   `time_control_seconds`:
   ```python
   base_time_seconds: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
   increment_seconds: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
   ```
   Keep `time_control_seconds` as-is (still used for bucketing).

2. **Schema** (`app/schemas/normalization.py`): Add `base_time_seconds: int | None = None`
   and `increment_seconds: int | None = None` to `NormalizedGame` (matches existing
   default-None style used by lichess analysis fields).

3. **Parser** (`app/services/normalization.py`): Add `parse_base_and_increment(tc_str: str)
   -> tuple[int | None, int | None]`. Reuse the same parsing shape as
   `parse_time_control` (float parse, catch ValueError). Rules:
   - empty / "-" / daily ("X/Y"): return `(None, None)`
   - `base` cast via `int(round(base))`, `increment` via `int(round(increment))`
   - Plain "600" (no "+"): `(600, 0)`
   Add a docstring with the same examples as in the interfaces block above.

4. **Wire into normalize_chesscom_game + normalize_lichess_game**: In both
   functions, after the existing `parse_time_control` call, also call
   `parse_base_and_increment` on the same input string (chess.com: raw `tc_str`;
   lichess: the `f"{clock_initial}+{clock_increment}"` string; correspondence and
   empty branches: `(None, None)`). Pass the two new fields into the
   `NormalizedGame(...)` constructor.

5. **Import service wiring**: Search app/services/import_service.py (and any
   caller that builds a `Game(...)` from a `NormalizedGame`) for the `Game(` /
   `game = Game(` construction site and add
   `base_time_seconds=normalized.base_time_seconds,
   increment_seconds=normalized.increment_seconds,`. If the construction uses
   `**normalized.model_dump()` it works automatically — verify. Do NOT change
   other behavior.

6. **Alembic migration**: Create via
   `uv run alembic revision -m "add base_time_seconds and increment_seconds to games"`
   then edit the generated file:
   ```python
   def upgrade() -> None:
       op.add_column("games", sa.Column("base_time_seconds", sa.SmallInteger(), nullable=True))
       op.add_column("games", sa.Column("increment_seconds", sa.SmallInteger(), nullable=True))

       # Backfill from time_control_str using Python-side reparse (same rules as
       # app/services/normalization.py::parse_base_and_increment). Inline here so the
       # migration stays self-contained and future-proof against code renames.
       conn = op.get_bind()
       rows = conn.execute(sa.text(
           "SELECT id, time_control_str FROM games WHERE time_control_str IS NOT NULL "
           "AND base_time_seconds IS NULL"
       )).fetchall()
       BATCH = 500
       updates: list[dict] = []
       for row in rows:
           tc = row.time_control_str
           base, inc = _parse_base_inc(tc)  # local helper defined inside this file
           if base is None:
               continue
           updates.append({"id": row.id, "b": base, "i": inc or 0})
           if len(updates) >= BATCH:
               conn.execute(sa.text(
                   "UPDATE games SET base_time_seconds = :b, increment_seconds = :i WHERE id = :id"
               ), updates)
               updates = []
       if updates:
           conn.execute(sa.text(
               "UPDATE games SET base_time_seconds = :b, increment_seconds = :i WHERE id = :id"
           ), updates)

   def downgrade() -> None:
       op.drop_column("games", "increment_seconds")
       op.drop_column("games", "base_time_seconds")
   ```
   Define `_parse_base_inc` at module level inside the migration file (do NOT
   import from app.services — migrations must be self-contained against future
   refactors).

7. **Tests** (`tests/test_normalization.py`): Add cases for
   `parse_base_and_increment`: "600" → (600,0), "600+0" → (600,0), "600+5" →
   (600,5), "900+10" → (900,10), "10+0.1" → (10,0), "1/259200" → (None,None),
   "" → (None,None), "-" → (None,None). Also add at least one integration-style
   test ensuring `normalize_chesscom_game` and `normalize_lichess_game` return
   `base_time_seconds`/`increment_seconds` populated for a standard "600+5"
   game and None for a daily game. Use existing fixture patterns in that file.
  </action>
  <verify>
    <automated>
docker compose -f docker-compose.dev.yml -p flawchess-dev up -d &&
uv run alembic upgrade head &&
uv run pytest tests/test_normalization.py -x &&
uv run ty check app/ tests/ &&
uv run ruff check app/ tests/ &&
uv run ruff format --check app/ tests/
    </automated>
  </verify>
  <done>
    - Columns exist on `games` and are populated on existing rows (spot-check with
      flawchess-db MCP: `SELECT COUNT(*) FROM games WHERE base_time_seconds IS NOT NULL`
      > 0 after upgrade).
    - All test_normalization tests pass including new ones.
    - ty + ruff clean.
  </done>
</task>

<task type="auto">
  <name>Task 2: Switch time pressure to per-game base_time_seconds denominator + >2x clamp</name>
  <files>
    app/repositories/endgame_repository.py,
    app/services/endgame_service.py,
    app/schemas/endgames.py,
    tests/test_endgame_service.py,
    tests/test_endgame_repository.py
  </files>
  <action>
1. **Repository** (`app/repositories/endgame_repository.py::query_clock_stats_rows`):
   In the `select(...)` (line ~698-711), replace `Game.time_control_seconds`
   with `Game.base_time_seconds`. Update the docstring row-shape comment to
   `(game_id, time_control_bucket, base_time_seconds, termination, result,
   user_color, ply_array, clock_array)`. Add a brief explanation comment noting
   this is the post-quick-260414-smt change and why (% of estimated
   time_control_seconds was broken because bucket-first-seen was mixing
   different starting clocks; per-game base_time_seconds is apples-to-apples).

2. **Add constant** near the top of `endgame_service.py` (next to NUM_BUCKETS):
   ```python
   # Games where a clock reading at endgame entry exceeds 2x the base time are
   # treated as bad data and excluded from the % computation. Banked increment
   # legitimately pushes this above 100% (p99 in prod is 109%), but >200% is
   # noise (saw max 2047% in prod).
   MAX_CLOCK_PCT_OF_BASE = 2.0
   ```

3. **_compute_clock_pressure** (endgame_service.py:730-864):
   - Rename the `time_control_seconds` row unpack to `base_time_seconds` (still
     `row[2]`).
   - Delete the `tc_seconds: dict[str, int | None] = {}` accumulator (lines
     ~761-762) and the `if tc not in tc_seconds:` / `tc_seconds[tc] = ...`
     block (~784-785) entirely. Delete `tc_secs = tc_seconds.get(tc)` /
     `if tc_secs is not None and tc_secs > 0:` (~796-799) and replace with
     per-row logic described next.
   - After extracting `user_clock` / `opp_clock`, only accumulate pct when BOTH
     clocks are present AND `base_time_seconds` is not None AND > 0 AND neither
     clock exceeds `MAX_CLOCK_PCT_OF_BASE * base_time_seconds`. If the clamp
     trips, skip the pct contribution for THIS game (but still accumulate the
     absolute seconds — keep current behavior for absolute metrics).
     Rationale: the absolute seconds columns are merely descriptive; the %
     columns are the ones that break under absurd readings.
     Actually: simpler + more defensible is to skip the WHOLE game from clock
     accumulation when the clamp trips (user_clocks, opp_clocks, clock_diffs,
     and both pcts). Do this — prevents the bad reading from polluting any
     aggregate. Add an inline comment explaining.
   - Compute pct as `user_clock / base_time_seconds * 100` and
     `opp_clock / base_time_seconds * 100` per game.
   - Leave the timeout accumulation untouched (unaffected by clock values).
   - Keep `ClockStatsRow.user_avg_pct` / `opp_avg_pct` field names; update the
     docstrings in `app/schemas/endgames.py` to read
     `"mean (user_clock / base_time_seconds * 100) at entry; None if no base_time_seconds"`
     and the analogous opp version.

4. **_compute_time_pressure_chart** (endgame_service.py:894-990): Same
   treatment — rename `time_control_seconds` to `base_time_seconds` in the row
   unpack, and add the same >2x clamp (skip the game entirely if either
   `user_clock > MAX_CLOCK_PCT_OF_BASE * base_time_seconds` or `opp_clock >
   MAX_CLOCK_PCT_OF_BASE * base_time_seconds`). Bucket rule unchanged
   (`min(int(pct / BUCKET_WIDTH_PCT), NUM_BUCKETS - 1)` still clamps 0-9 for
   normal values; only the bad-data filter is new).

5. **Tests** (`tests/test_endgame_service.py`): Update existing
   `_compute_clock_pressure` tests that construct rows — change row tuples so
   position 2 is per-game `base_time_seconds` not `time_control_seconds`. Add
   a new test: two games in rapid bucket with different base_time_seconds (600
   and 1800), verify `user_avg_pct` is the per-game mean (not bucket-first-seen).
   Add a clamp test: one game where `user_clock = 3 * base_time_seconds` is
   excluded entirely (game count still counts it as endgame, but it contributes
   nothing to clock_games / user_avg_pct / user_avg_seconds). Also add an
   analogous test for `_compute_time_pressure_chart` covering per-game
   denominator + clamp.

6. **Tests** (`tests/test_endgame_repository.py`): If the file asserts on
   selected column order or specific column values from `query_clock_stats_rows`,
   update to expect `base_time_seconds` at position 2 (grep for
   `time_control_seconds` in that file — may be absent, in which case no change
   needed).

7. **Docstring hygiene**: Update the `query_clock_stats_rows` docstring's
   "Returns rows of:" line to match the new column.
  </action>
  <verify>
    <automated>
uv run pytest tests/test_endgame_service.py tests/test_endgame_repository.py -x &&
uv run pytest -x &&
uv run ty check app/ tests/ &&
uv run ruff check app/ tests/ &&
uv run ruff format --check app/ tests/
    </automated>
  </verify>
  <done>
    - Per-game denominator test passes: two rapid games (600 base + 1800 base)
      produce `user_avg_pct` equal to per-game mean, not bucketed.
    - Clamp test passes: a 3x-base clock contributes nothing.
    - Full pytest suite green, ty clean, ruff clean.
    - Spot check with flawchess-db MCP: run the endgames overview endpoint in
      dev (via API) and verify user_avg_pct is in a plausible range (0–110%)
      for all time control rows.
  </done>
</task>

<task type="auto">
  <name>Task 3: Frontend — relabel Time Pressure columns/popover to reflect % of base time</name>
  <files>
    frontend/src/components/charts/EndgameClockPressureSection.tsx
  </files>
  <action>
Update the Time Pressure at Endgame Entry table labels to make clear the
percentage is "% of base time":

1. Popover text (`<InfoPopover>` children around lines 51-56): Change
   `"(% of total time + absolute seconds)"` wording to
   `"(% of base clock time + absolute seconds, pre-increment)"`. Add a
   new short paragraph explaining: `"% of base time = remaining clock divided
   by the starting clock for that game (e.g. 600 for a 600+0 game, 900 for a
   900+10 game). Values above 100% are possible when increment banks past the
   starting clock; bad-data readings above 200% of base are excluded."`
2. Column headers: Keep "My avg time" / "Opp avg time" as-is (the cell already
   shows "NN% (Ns)" which reads naturally). Optionally tighten the accompanying
   description paragraph (line 60-62) to include the phrase "base time" once so
   users scanning understand the unit without opening the popover. Example:
   `"How much clock (as % of base time) you have entering endgames, and how
   often you flag vs your opponents."`
3. Leave `formatClockCell` implementation untouched — output format stays
   `"NN% (Ns)"`.
4. Verify: Glob confirms there is no mobile-variant file for this section
   (`EndgameClockPressureSection.tsx` is the only match); the CLAUDE.md
   "apply to mobile too" rule is satisfied by the component being shared.
5. Do NOT touch `EndgameTimePressureSection.tsx` (that's the chart, not the
   table — no label change needed there; its buckets already say "NN-NN%").
  </action>
  <verify>
    <automated>
cd frontend && npm run lint && npm run build && npm test -- --run
    </automated>
  </verify>
  <done>
    - Popover text reflects "% of base time" / "base clock".
    - Section description mentions "base time" once.
    - `npm run build` + `npm run lint` + `npm test` all pass.
    - Running the app locally shows values clamped to plausible % (no 129%,
      no 2047%).
  </done>
</task>

</tasks>

<verification>
End-to-end checks before committing:

```bash
# Backend
docker compose -f docker-compose.dev.yml -p flawchess-dev up -d
uv run alembic upgrade head
uv run pytest
uv run ty check app/ tests/
uv run ruff check .
uv run ruff format --check .

# Frontend
cd frontend
npm run build
npm run lint
npm test -- --run
npm run knip   # dead exports check
```

Data sanity (use flawchess-db MCP after migration):
```sql
SELECT COUNT(*) AS total,
       COUNT(base_time_seconds) AS with_base,
       COUNT(increment_seconds) AS with_inc
FROM games;

-- Verify no more absurd values:
SELECT time_control_bucket, MIN(base_time_seconds), MAX(base_time_seconds),
       COUNT(*)
FROM games WHERE base_time_seconds IS NOT NULL
GROUP BY time_control_bucket;
```

Manual: Hit `/api/endgames/overview` in dev and inspect `clock_pressure.rows` —
every `user_avg_pct` should be 0–110 (banked increment can push slightly over
100 for rapid+inc; typical range 40–80).
</verification>

<success_criteria>
- `games.base_time_seconds` and `games.increment_seconds` exist, backfilled
  where `time_control_str` is parseable, NULL for daily/missing.
- Both import normalizers populate the new fields.
- `_compute_clock_pressure` + `_compute_time_pressure_chart` divide by per-game
  `base_time_seconds`, not bucket-first-seen estimate.
- Clamp (>2x) excludes bad-data games from pct aggregation.
- Table popover + description surface "base time" explicitly.
- All quality gates green: pytest, ty, ruff, npm build/lint/test/knip.
- No live rows show >200% (spot check in dev).
</success_criteria>

<output>
After completion, create `.planning/quick/260414-smt-split-time-control-into-base-time-second/260414-smt-SUMMARY.md`
with: migration revision ID, files touched, test counts added, and a brief
"before/after" showing a sample rapid-bucket row's `user_avg_pct` going from
absurd to plausible.
</output>
