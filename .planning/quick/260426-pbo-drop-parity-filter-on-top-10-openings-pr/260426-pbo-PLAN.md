---
phase: 260426-pbo
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - app/repositories/stats_repository.py
  - app/schemas/stats.py
  - app/services/stats_service.py
  - tests/test_stats_repository.py
  - tests/test_stats_service.py
  - frontend/src/types/stats.ts
  - frontend/src/components/stats/MostPlayedOpeningsTable.tsx
  - frontend/src/pages/Openings.tsx
autonomous: true
requirements: [PRE-01]

must_haves:
  truths:
    - "Black users see white-defined named openings (e.g. 'vs. Caro-Kann Defense: Hillbilly Attack') in their top-10 when they have games matching that position."
    - "Off-color rows render with a 'vs. ' prefix in both desktop and mobile top-10 lists."
    - "Same-color rows render WITHOUT the 'vs. ' prefix (no behavioral regression for openings that already appeared)."
    - "Backend test asserts both prefix presence (off-color) and absence (same-color) parametrized by user color."
    - "ty + ruff + pytest + frontend lint all pass."
  artifacts:
    - path: "app/repositories/stats_repository.py"
      provides: "query_top_openings_sql_wdl returns display_name column, parity filter removed"
      contains: "display_name"
    - path: "app/schemas/stats.py"
      provides: "OpeningWDL.display_name field"
      contains: "display_name"
    - path: "frontend/src/types/stats.ts"
      provides: "OpeningWDL.display_name TS field"
      contains: "display_name"
  key_links:
    - from: "app/repositories/stats_repository.py"
      to: "app/services/stats_service.py"
      via: "row tuple unpacking now includes display_name"
      pattern: "display_name"
    - from: "app/services/stats_service.py"
      to: "app/schemas/stats.py"
      via: "OpeningWDL(display_name=...)"
      pattern: "display_name="
    - from: "frontend/src/components/stats/MostPlayedOpeningsTable.tsx"
      to: "OpeningWDL.display_name"
      via: "formatName(o.display_name) replaces formatName(o.opening_name)"
      pattern: "display_name"
---

<objective>
Drop the ply-parity filter in `query_top_openings_sql_wdl` so black users see white-defined openings (and vice versa). Surface a pre-computed `display_name` column that prefixes off-color rows with `"vs. "` so labels still read naturally. Frontend renders `display_name` instead of `opening_name`.

Purpose: The current filter excludes ~half of all named ECO openings per color (e.g. `Caro-Kann Defense: Hillbilly Attack`, ply 3, has 816 dev-DB games tagged `user_color='black'` but is invisible). Coverage loss outweighs the labeling-aesthetic win. This is a v1.13 Phase 70 prerequisite (PRE-01).

Output: Off-color rows visible with `"vs. "` prefix, same-color rows unchanged, regression test parametrized by color, frontend updated, ty/ruff/pytest green.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.planning/todos/pending/2026-04-26-top10-openings-parity-bug.md
@CLAUDE.md
@app/repositories/stats_repository.py
@app/schemas/stats.py
@app/services/stats_service.py
@frontend/src/types/stats.ts
@frontend/src/components/stats/MostPlayedOpeningsTable.tsx

<interfaces>
<!-- Existing OpeningWDL schema (will gain `display_name`) -->

From `app/schemas/stats.py`:
```python
class OpeningWDL(BaseModel):
    opening_eco: str
    opening_name: str    # canonical name — KEEP for FEN/bookmark lookups
    label: str           # "Opening Name (ECO)" — already present, used elsewhere
    pgn: str
    fen: str
    full_hash: str
    wins: int; draws: int; losses: int; total: int
    win_pct: float; draw_pct: float; loss_pct: float
    # NEW:
    # display_name: str  # canonical name with "vs. " prefix when off-color
```

From `app/repositories/stats_repository.py` (current SELECT order — used by service):
```python
# Current returned tuple shape (per row):
# (eco, name, pgn, fen, full_hash, total, wins, draws, losses)
# After change:
# (eco, name, display_name, pgn, fen, full_hash, total, wins, draws, losses)
```

From `app/services/stats_service.py:322` (current unpacking that must be updated):
```python
for eco, name, pgn, fen, full_hash, total, wins, draws, losses in rows:
```

From `frontend/src/components/stats/MostPlayedOpeningsTable.tsx:62`:
```tsx
{formatName(o.opening_name)}  // change to o.display_name
```
</interfaces>

## Notes for executor

- **`formatName` interaction:** `formatName` splits on `": "`. For `"vs. Caro-Kann Defense: Hillbilly Attack"` it produces bold `"vs. Caro-Kann Defense:"` + lighter `"Hillbilly Attack"`. That reads correctly; no formatter change needed.
- **Keep `opening_name` (canonical, unprefixed):** the bookmark suggestion path (`app/routers/position_bookmarks.py`) and frontend bookmark builder (`Openings.tsx:818-862`) use `opening_name` and `label` as the canonical opening identity. Do NOT modify those — only add `display_name` alongside. `label` stays as `f"{name} ({eco})"`.
- **Do NOT change the existing `label` field semantics.** Leave as-is.
- **Pre-fix grep already done by planner:** the only `ply_count % 2` filter in `app/repositories/` and `app/services/` is the target line. (`endgame_service.py:1110` uses `ply % 2 == user_parity` for clock semantics — unrelated.) Executor does NOT need to re-grep.
- **`min_ply` floor stays.** Only the parity equality is removed.
- **Sentry rules:** no new exception handling needed; this is a SQL-shape and rendering change.
- **Comment the bug-fix site** per CLAUDE.md: explain the parity filter was removed and why (coverage gap), reference the `vs. ` prefix as the new approach.
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Backend — drop parity filter, add display_name, update service unpacking, add regression test</name>
  <files>
    app/repositories/stats_repository.py,
    app/schemas/stats.py,
    app/services/stats_service.py,
    tests/test_stats_repository.py,
    tests/test_stats_service.py
  </files>
  <behavior>
    - `query_top_openings_sql_wdl(color="black")` returns rows for openings where `ply_count` is odd (white-defined) when those games exist for the user — formerly excluded.
    - Each returned row carries a `display_name` field equal to `f"vs. {name}"` when the opening's defining ply is off-color for the requesting user, else equal to `name`.
    - `OpeningWDL.display_name` populated by `stats_service.get_most_played_openings` and serialized in the response.
    - Regression test (parametrized over `color in ("white", "black")`):
      - Insert games with two openings: one same-color (parity matches user color) and one off-color (parity opposite). Both above `min_games`.
      - Assert both appear in the result.
      - Assert the off-color row's `display_name` starts with `"vs. "` and equals `f"vs. {opening_name}"`.
      - Assert the same-color row's `display_name` equals `opening_name` (no prefix).
    - Existing `test_stats_service.py::test_get_most_played_openings*` continues to pass; if it asserts `display_name`, ensure the field is present on every row.
  </behavior>
  <action>
    1. **`app/repositories/stats_repository.py` — `query_top_openings_sql_wdl`:**
       - Remove the line `_openings_dedup.c.ply_count % 2 == (1 if color == "white" else 0),` from the `.where()` clause. Keep the `min_ply` floor.
       - Add a computed column to the SELECT using `case()` from sqlalchemy (already imported via `from sqlalchemy import ...` — add `case` to the import if not present):
         ```python
         from sqlalchemy import case  # add to existing imports if missing

         user_parity = 1 if color == "white" else 0  # named constant — no magic numbers
         display_name_col = case(
             (_openings_dedup.c.ply_count % 2 != user_parity,
              literal("vs. ") + Game.opening_name),
             else_=Game.opening_name,
         ).label("display_name")
         ```
         (`literal` from `sqlalchemy` may already be imported; add if needed. Alternative: `func.concat("vs. ", Game.opening_name)` — pick whichever yields a cleaner SQL log. PostgreSQL `||` via `op("||")` also fine.)
       - Place `display_name_col` in the SELECT immediately after `Game.opening_name` so the row tuple becomes
         `(eco, name, display_name, pgn, fen, full_hash, total, wins, draws, losses)`.
       - Add `display_name_col` to `.group_by(...)` (PostgreSQL requires it because it's a non-aggregate select expression).
       - Add a comment at the modification site explaining what changed and why (CLAUDE.md "Comment bug fixes" rule):
         ```python
         # 2026-04-26 (PRE-01): parity filter removed. Previously
         # `ply_count % 2 == user_parity` excluded ~48% of named ECO openings
         # per color (e.g. black users never saw white-defined openings like
         # Caro-Kann Defense: Hillbilly Attack despite playing them). Off-color
         # rows are now surfaced with a `vs. ` prefix via `display_name`.
         ```
    2. **`app/schemas/stats.py`:** add `display_name: str` to `OpeningWDL` (place adjacent to `label` with a comment describing it as "name with `vs. ` prefix when off-color").
    3. **`app/services/stats_service.py` — `rows_to_openings` (~line 322):**
       - Update the unpacking to `for eco, name, display_name, pgn, fen, full_hash, total, wins, draws, losses in rows:`.
       - Pass `display_name=display_name` to `OpeningWDL(...)`. Keep `opening_name=name` and `label=f"{name} ({eco})"` unchanged.
    4. **`tests/test_stats_repository.py`:** add a parametrized regression test (mirror the style of existing tests in this file — they already create games via the local `_create_game` helper, see lines 60-100 for signature). Use ECO/name pairs whose `_openings_dedup.ply_count` parity is known: e.g. `("B10", "Caro-Kann Defense: Hillbilly Attack")` (ply 3, odd — off-color for black, same-color for white) and `("B00", "King's Pawn Game")` (ply 1, odd — same-color for white, off-color for black). The test must:
       - Seed openings via the existing fixture/setup (existing tests already join `_openings_dedup`; reuse that path — check the top of the file for fixture wiring).
       - Insert ≥ `min_games` games for each opening with `user_color` parametrized.
       - Call `query_top_openings_sql_wdl` with `min_games=1, min_ply=2` (or whatever the existing tests use), `color=<param>`.
       - Assert both openings appear in the returned rows (formerly only one would).
       - Assert the row tuple's `display_name` index has the `"vs. "` prefix exactly when parity mismatches user color.
       - Name the test `test_top_openings_includes_off_color_with_vs_prefix` (or similar).
    5. **`tests/test_stats_service.py`:** if the existing `test_get_most_played_openings*` test inspects fields, extend it to assert `hasattr(opening, "display_name")` and that `display_name` matches `opening_name` OR equals `f"vs. {opening_name}"`. No new test needed unless trivial.
    6. Run `uv run ruff format app/ tests/`, `uv run ruff check app/ tests/`, `uv run ty check app/ tests/`, `uv run pytest tests/test_stats_repository.py tests/test_stats_service.py -x`.
  </action>
  <verify>
    <automated>
docker compose -f docker-compose.dev.yml -p flawchess-dev up -d &&
uv run ruff format --check app/ tests/ &&
uv run ruff check app/ tests/ &&
uv run ty check app/ tests/ &&
uv run pytest tests/test_stats_repository.py tests/test_stats_service.py -x
    </automated>
  </verify>
  <done>
    - Parity filter line removed from `query_top_openings_sql_wdl`; bug-fix comment added.
    - `display_name` present in SQL SELECT, group_by, OpeningWDL schema, and service-layer construction.
    - Regression test passes for both `color="white"` and `color="black"`, asserting prefix presence on off-color rows and absence on same-color rows.
    - `uv run ruff check`, `uv run ty check`, and the targeted pytest run all exit 0.
  </done>
</task>

<task type="auto">
  <name>Task 2: Frontend — add display_name to OpeningWDL type, render in desktop + mobile top-10 lists</name>
  <files>
    frontend/src/types/stats.ts,
    frontend/src/components/stats/MostPlayedOpeningsTable.tsx,
    frontend/src/pages/Openings.tsx
  </files>
  <action>
    1. **`frontend/src/types/stats.ts`:** add `display_name: string;` to the `OpeningWDL` interface (next to `label`).
    2. **`frontend/src/components/stats/MostPlayedOpeningsTable.tsx` (desktop):**
       - Line 62: change `{formatName(o.opening_name)}` → `{formatName(o.display_name)}`.
       - Tooltip + aria-label on game-count button (lines 71, 74): keep using `o.opening_name` — the tooltip says "View N games for {name}" and the canonical name reads better there. (Optional: switch to `display_name` if it reads better; the user-visible row label is the primary requirement.)
    3. **`frontend/src/pages/Openings.tsx` (mobile MPO renderer, ~line 124):** change `{o.opening_name}` → `{o.display_name}`.
       - Tooltip + aria-label at lines 128/131: same logic as desktop — keep `opening_name`.
    4. **Bookmark builder (`Openings.tsx` ~line 828):** the `buildBookmarkRows` helper synthesizes `OpeningWDL` rows from bookmarks. Add `display_name: b.label` (or `b.label.replace(/ \([^)]*\)$/, '')` if `label` includes the ECO suffix — match the existing `opening_name` value at line 830). Bookmarks have no parity context, so `display_name === opening_name`. This keeps the type satisfied without changing bookmark UI.
    5. Search for any OTHER consumer that constructs an `OpeningWDL` literal — `grep -rn "OpeningWDL\b" frontend/src/` — and add `display_name` there too. (Mocks in tests, if any, should also be updated.)
    6. Run `cd frontend && npm run lint && npm run build`. Knip should remain clean (no new unused exports).
  </action>
  <verify>
    <automated>cd frontend && npm run lint && npx tsc --noEmit && npm test -- --run</automated>
  </verify>
  <done>
    - `OpeningWDL` TS interface has `display_name: string`.
    - Desktop + mobile top-10 row labels render `display_name` (so off-color rows show `vs. ...`).
    - All `OpeningWDL` constructions in frontend code populate `display_name` (bookmark synth uses canonical name).
    - `npm run lint`, `tsc --noEmit`, `npm test`, and `npm run build` all succeed.
  </done>
</task>

<task type="checkpoint:human-verify" gate="blocking">
  <what-built>
    - Parity filter removed from `query_top_openings_sql_wdl`; off-color openings now appear in the top-10 with a `"vs. "` prefix.
    - Regression test added (both colors) asserting prefix presence/absence.
    - Frontend (desktop + mobile) renders `display_name` instead of `opening_name`.
  </what-built>
  <how-to-verify>
    1. Start dev DB + backend + frontend: `bin/run_local.sh` (or backend + frontend separately).
    2. Log in as Adrian's account (the user from the bug report).
    3. Open the Openings page, switch to the Black top-10. Confirm `vs. Caro-Kann Defense: Hillbilly Attack` (or similar white-defined opening with N games) is now visible with the `vs. ` prefix.
    4. Verify same-color rows (e.g. white user playing `Italian Game`) render WITHOUT the `vs. ` prefix.
    5. Verify on mobile width (Chrome devtools, narrow viewport) — the mobile MPO renderer in `Openings.tsx` shows the prefix too.
    6. (Optional) Verify via `mcp__flawchess-db__query`:
       ```sql
       -- adapt user_id; should now return >0 rows for off-color openings
       SELECT g.opening_eco, g.opening_name, COUNT(*)
       FROM games g
       JOIN openings_dedup o ON g.opening_eco = o.eco AND g.opening_name = o.name
       WHERE g.user_id = <UID> AND g.user_color = 'black'
         AND o.ply_count % 2 = 1  -- white-defined, formerly excluded
       GROUP BY 1,2 ORDER BY 3 DESC LIMIT 5;
       ```
  </how-to-verify>
  <resume-signal>Type "approved" once the prefix renders correctly in both desktop and mobile, or describe issues.</resume-signal>
</task>

</tasks>

<verification>
- `uv run ruff check app/ tests/` exits 0
- `uv run ty check app/ tests/` exits 0
- `uv run pytest tests/test_stats_repository.py tests/test_stats_service.py -x` passes (including the new parametrized regression test)
- `cd frontend && npm run lint && npx tsc --noEmit && npm test -- --run && npm run build` all succeed
- Manual UI check confirms off-color rows visible with `vs. ` prefix, same-color rows unchanged
</verification>

<success_criteria>
- [ ] Parity filter removed from `query_top_openings_sql_wdl`; bug-fix comment present
- [ ] `display_name` added to backend SQL SELECT, schema, service unpack, frontend type, desktop + mobile renderers
- [ ] Regression test (parametrized over both colors) passes — asserts prefix on off-color rows AND absence on same-color rows
- [ ] All existing stats tests still green
- [ ] ty + ruff + pytest + frontend lint/build/test green
- [ ] Manual UI check confirms `vs. Caro-Kann Defense: Hillbilly Attack` appears for the original-reporter user account
</success_criteria>

<output>
After completion, append a 1-2 line entry under `## [Unreleased]` → `### Fixed` in `CHANGELOG.md` referencing PRE-01 (e.g. "Top-10 openings now include opponent-defined openings (e.g. `vs. Caro-Kann Defense: Hillbilly Attack`) which were previously hidden by a ply-parity filter.").

Mark the source todo as completed: move `.planning/todos/pending/2026-04-26-top10-openings-parity-bug.md` → `.planning/todos/done/` (or update its status frontmatter, whichever convention this repo uses).

Update `.planning/STATE.md` "Pending Todos" — strike PRE-01 line or move to "Quick Tasks Completed" table with this directory + commit hash.
</output>
