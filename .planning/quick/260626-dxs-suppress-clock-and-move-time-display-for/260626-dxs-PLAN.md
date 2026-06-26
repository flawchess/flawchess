---
phase: quick-260626-dxs
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - app/services/normalization.py
  - app/services/library_service.py
  - app/repositories/library_repository.py
  - tests/services/test_normalization.py
  - tests/services/test_eval_chart_service.py
  - tests/repositories/test_library_repository.py
autonomous: true
requirements: [QUICK-260626-dxs]
must_haves:
  truths:
    - "Eval-chart tooltips show no clock/move-time for daily/correspondence games"
    - "Flaw cards show no clock/move-time for daily/correspondence games"
    - "Real classical games (e.g. 1800) still surface clock data"
  artifacts:
    - path: "app/services/normalization.py"
      provides: "is_correspondence_time_control predicate + named separator constant"
      contains: "def is_correspondence_time_control"
    - path: "app/services/library_service.py"
      provides: "clock/move-time suppression at the EvalPoint build site"
    - path: "app/repositories/library_repository.py"
      provides: "clock/move-time suppression at the FlawListItem build site"
  key_links:
    - from: "app/services/library_service.py"
      to: "app/services/normalization.py"
      via: "imports is_correspondence_time_control, applies once per game"
      pattern: "is_correspondence_time_control"
    - from: "app/repositories/library_repository.py"
      to: "app/services/normalization.py"
      via: "imports is_correspondence_time_control, applies once per flaw item"
      pattern: "is_correspondence_time_control"
---

<objective>
Suppress the clock and move-time DISPLAY for chess.com "daily" and lichess "correspondence" games in two API response build sites: the eval-chart `EvalPoint` series and the Flaws-tab `FlawListItem`. These games carry meaningless `%clk` annotations (witness: dev game id 687474, user 28 — clocks jump 0.7s → 21.3s → 1008s → 90s), so `game_positions.clock_seconds` is populated with garbage that currently renders because the frontend only guards on `!= null`.

Purpose: stop showing nonsensical clock/move-time numbers for per-move (daily/correspondence) games without touching storage, the import pipeline, or the frontend.
Output: a reusable `is_correspondence_time_control` predicate and `clock_seconds = None` / `move_seconds = None` forced at both build sites for these games.
</objective>

<execution_context>
@$HOME/.claude/gsd-core/workflows/execute-plan.md
</execution_context>

<context>
@.planning/STATE.md
@app/services/normalization.py
@app/services/library_service.py
@app/repositories/library_repository.py
</context>

<scope_guardrails>
DECIDED — do not re-investigate or expand:
- ONLY suppress the clock + move-time DISPLAY. No new TC bucket / enum / filter — daily stays bucketed `classical`.
- DO NOT touch storage or the import pipeline. `game_positions.clock_seconds` stays populated as-is (it feeds time-management stats, out of scope). No DB migration. No backfill.
- NO frontend changes — the existing `!= null` guards suppress the UI once the backend sends null.
- DO NOT gate completion on `bin/reset_db.sh` or anything prod.
</scope_guardrails>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Add is_correspondence_time_control predicate and suppress clock/move-time at both build sites</name>
  <files>app/services/normalization.py, app/services/library_service.py, app/repositories/library_repository.py, tests/services/test_normalization.py, tests/services/test_eval_chart_service.py, tests/repositories/test_library_repository.py</files>
  <behavior>
    Predicate is_correspondence_time_control(time_control_str: str | None) -> bool:
    - "1/86400" → True
    - "1/259200" → True
    - "1800" → False
    - "600+5" → False
    - "60+0" → False
    - "10+0.1" → False
    - None → False
    - "" → False  (empty/"-" guarded like the other normalization helpers)
    EvalPoint series (_build_eval_series) for a game with time_control_str="1/86400":
    - every EvalPoint has clock_seconds is None AND move_seconds is None
    EvalPoint series regression: a game with time_control_str="1800", base_time_seconds=1800, positions carrying clock_seconds still surfaces clock_seconds (preserved, non-null).
    FlawListItem (_build_flaw_item) for a game with time_control_str="1/86400":
    - clock_seconds is None AND move_seconds is None
    FlawListItem regression: a classical game (time_control_str="1800") with pos_at.clock_seconds set still surfaces clock_seconds.
  </behavior>
  <action>
Add a module-level named constant for the per-move time-control separator in app/services/normalization.py (no magic string per CLAUDE.md), e.g. CORRESPONDENCE_TC_SEPARATOR = "/" — this is the slash in chess.com's "1/86400" daily format and the lichess correspondence normalization "1/{daysPerTurn*86400}" (see normalize_lichess_game, the `speed == "correspondence"` branch). Add an explicitly-typed predicate `is_correspondence_time_control(time_control_str: str | None) -> bool` that returns True when the string is non-empty, not "-", and contains the separator; False otherwise. Place it next to the existing time-control helpers (parse_time_control / parse_base_and_increment, which already detect daily via `"/" in tc_str`). Keep it small and shallow. Optionally route the two existing inline `"/" in tc_str` checks in parse_time_control / parse_base_and_increment through the constant for consistency, but do NOT change their behavior.

In app/services/library_service.py `_build_eval_series`: import is_correspondence_time_control, compute the flag ONCE per game before the position loop (e.g. `is_correspondence = is_correspondence_time_control(game.time_control_str)`). At the per-row clock derivation (currently `clock = pos.clock_seconds`, then the move_seconds block runs only `if clock is not None`), force `clock = None` when is_correspondence so both the EvalPoint clock_seconds AND the derived move_seconds become None for these games. Add a bug-fix comment at the site explaining WHY (daily/correspondence %clk values are meaningless, witnessed by nonsensical jumps; suppress display, storage untouched).

In app/repositories/library_repository.py `_build_flaw_item`: import is_correspondence_time_control, compute the flag ONCE at the top from game.time_control_str, and force both `clock_seconds=None` and `move_seconds=None` (skip the `_compute_move_seconds` call) when True. Add the same bug-fix comment. Note `parse_base_and_increment` is already imported from app.services.normalization here — add is_correspondence_time_control to that import.

Tests:
- tests/services/test_normalization.py: unit test the predicate over the cases in <behavior> (slash → True; "1800"/"600+5"/"60+0"/"10+0.1"/None/"" → False).
- tests/services/test_eval_chart_service.py: extend the `_make_game` helper with a `time_control_str: str | None = None` param (set game.time_control_str). Add a test that a daily game (time_control_str="1/86400") yields every EvalPoint with clock_seconds is None and move_seconds is None even when positions carry clock_seconds; add/keep a regression test that a classical game (time_control_str="1800", base_time_seconds=1800) with clock-bearing positions still surfaces clock_seconds.
- tests/repositories/test_library_repository.py: add a direct unit test for `_build_flaw_item` (importable, no DB needed — construct GameFlaw/Game/GamePosition in memory like the eval-chart test pattern). Assert a daily game (time_control_str="1/86400") yields clock_seconds is None and move_seconds is None, and a classical game (time_control_str="1800") with pos_at.clock_seconds and pos_two_before.clock_seconds set still surfaces non-null clock_seconds.

Honor CLAUDE.md: explicit return type annotations, no magic strings, ty-clean, small/shallow functions, bug-fix comments at both suppression sites.
  </action>
  <verify>
    <automated>cd /home/aimfeld/Projects/Python/flawchess && uv run ruff format app/ tests/ && uv run ruff check app/ tests/ --fix && uv run ty check app/ tests/ && uv run pytest -n auto tests/services/test_normalization.py tests/services/test_eval_chart_service.py tests/repositories/test_library_repository.py -x</automated>
  </verify>
  <done>
    is_correspondence_time_control returns True for slash strings and False for "1800"/"600+5"/None/""; daily/correspondence games yield clock_seconds=None and move_seconds=None at both the EvalPoint and FlawListItem build sites; classical games still surface clock data; ruff/ty clean; the three touched test modules pass under `-n auto`.
  </done>
</task>

</tasks>

<verification>
- `uv run ty check app/ tests/` passes with zero errors.
- `uv run ruff format app/ tests/` and `uv run ruff check app/ tests/ --fix` leave a clean tree (commit any style fixes with a `style(...)`/`chore(...)` prefix).
- `uv run pytest -n auto tests/services/test_normalization.py tests/services/test_eval_chart_service.py tests/repositories/test_library_repository.py` is green (dev DB must be up for the repository test).
- No changes under `frontend/`, no Alembic migration, no import-pipeline edits, no new TC bucket/enum/filter.
</verification>

<success_criteria>
Daily/correspondence games (`time_control_str` containing the per-move separator) send `clock_seconds = None` and `move_seconds = None` from both the eval-chart series and the flaw list, so the existing frontend `!= null` guards hide the meaningless clock/move-time. Real classical games (`"1800"`) still surface clock data. Storage, import pipeline, and frontend untouched.
</success_criteria>

<output>
Create `.planning/quick/260626-dxs-suppress-clock-and-move-time-display-for/260626-dxs-SUMMARY.md` when done.
</output>
