---
type: quick
slug: hux-raise-recent-games-per-tc-cap-from-1000
created: 2026-05-27
branch: gsd/phase-94.4-peer-relative-percentile-chip-refinement
---

<objective>
Raise `RECENT_GAMES_PER_TC_CAP` from 1000 to 3000 in `app/services/canonical_slice_sql.py`, and cascade the new number through every docstring, frontend tooltip / explainer string, and test assertion that hardcodes "1000" in the recent-games-per-TC context.

Purpose: Heavy single-users (e.g. user 8 with 5861 eligible blitz endgame games) currently have ~82% of their data discarded by the 1000-cap. Lifting the cap to 3000 keeps roughly 3× more games in the per-user chip computation without changing methodology.

Why no cohort regen: benchmark users are imported at ≤1000 games per TC at ingest time (`scripts/import_benchmark_users.py` passes `max_games=1000` to the Lichess API). The 3000-cap is therefore non-binding for cohort CDF rows — `benchmark_user_metric_values_v1` does not need to be recomputed.

Output: One-line constant bump + cascading text updates across ~10 files. No SQL refactor. No data backfill (per-user anchor rows refresh organically on the next import / eval drain).
</objective>

<context>
@CLAUDE.md
@app/services/canonical_slice_sql.py
@frontend/src/components/charts/PercentileChip.tsx
@frontend/src/pages/Endgames.tsx
@frontend/src/components/charts/__tests__/PercentileChip.test.tsx
</context>

<tasks>

<task type="auto">
  <name>Task 1: Bump constant + update backend docstrings + commit</name>
  <files>
    app/services/canonical_slice_sql.py,
    app/services/user_benchmark_percentiles_service.py,
    app/models/user_rating_anchors.py,
    app/models/user_benchmark_percentile.py,
    scripts/backfill_user_percentiles.py
  </files>
  <action>
    Bump the cap and cascade through backend docstrings only (no logic change anywhere).

    1. `app/services/canonical_slice_sql.py:108` — change `RECENT_GAMES_PER_TC_CAP: int = 1000` to `RECENT_GAMES_PER_TC_CAP: int = 3000`.
    2. In the same file, update every docstring / comment mention of the old number to "3000":
       - Module docstring around line 7 ("recent-1000-per-TC" wording).
       - `_recent_capped_cte` docstring near line 260.
       - The explicit `# The 1000-cap then means...` comment near line 297 — rewrite to refer to 3000 and keep the existing logic explanation intact.
       - `_recent_capped_per_tc_cte` docstring near line 327.
       - Any other "1000" / "recent-1000" string in this file (grep first), around line 1093 included.
    3. `app/services/user_benchmark_percentiles_service.py:323` — docstring "recent-1000 × ..." → "recent-3000 × ...".
    4. `app/models/user_rating_anchors.py` — lines 10, 17, 91 docstrings "recent-1000-per-TC" → "recent-3000-per-TC".
    5. `app/models/user_benchmark_percentile.py:101` — docstring "TC's recent-1000 pool" → "TC's recent-3000 pool".
    6. `scripts/backfill_user_percentiles.py:345` — docstring "recent-1000 × 36-month pool" → "recent-3000 × 36-month pool".

    Do NOT touch:
    - `.claude/skills/benchmarks/SKILL.md` (different cap — import-time Lichess API `max_games`).
    - `reports/archive/*` or `reports/benchmarks-2026-05-24.md` (historical snapshots).
    - `.planning/REQUIREMENTS.md`, `.planning/ROADMAP.md` (historical phase descriptions).
    - The `least()` symmetry in `canonical_slice_sql.py:683` (deferred follow-up).

    Before committing, run the pre-PR backend gates and resolve any output (the change is docstrings-only, so failures should only surface if grep missed a spot):

        uv run ruff format app/ tests/ scripts/
        uv run ruff check app/ tests/ scripts/ --fix
        uv run ty check app/ tests/
        uv run pytest -x

    Then commit. Suggested message:

        chore(canonical-slice): raise RECENT_GAMES_PER_TC_CAP 1000 → 3000

        Cap is non-binding for cohort (benchmark import already capped at 1000
        per TC), but relaxes the per-user pool so heavy single-users keep ~3×
        more eligible games in chip computation.
  </action>
  <verify>
    <automated>
      grep -RIn --include='*.py' -E '\brecent-1000\b|recent 1000|1000.cap|1000-cap' app/ scripts/ tests/ ; test $? -eq 1
    </automated>
  </verify>
  <done>
    - `RECENT_GAMES_PER_TC_CAP = 3000` in `canonical_slice_sql.py`.
    - No remaining "1000" mention in backend code/docstrings that refers to the recent-games-per-TC cap.
    - `ruff format/check`, `ty check`, `pytest -x` all pass.
    - Single commit made on the current branch.
  </done>
</task>

<task type="auto">
  <name>Task 2: Update frontend tooltip + explainer copy + tests + commit</name>
  <files>
    frontend/src/components/charts/PercentileChip.tsx,
    frontend/src/pages/Endgames.tsx,
    frontend/src/components/charts/__tests__/PercentileChip.test.tsx
  </files>
  <action>
    Update every user-facing "1000" in the recent-games context to "3000", and update test assertions to match.

    1. `frontend/src/components/charts/PercentileChip.tsx:176-177` — both `bullet2` strings:
       - "most recent 1000 rated games in ${tc} over the last 36 months" → "most recent 3000 rated games in ${tc} over the last 36 months"
       - "most recent 1000 rated games per time control over the last 36 months" → "most recent 3000 rated games per time control over the last 36 months"
    2. `frontend/src/pages/Endgames.tsx`:
       - Line 412 — "your most recent 1000 rated games in that time control" → "your most recent 3000 rated games in that time control".
       - Line 433 — "Your most recent 1000 rated games per time control" → "Your most recent 3000 rated games per time control".
    3. `frontend/src/components/charts/__tests__/PercentileChip.test.tsx`:
       - Line 274 `it(...)` title — replace "1000" with "3000".
       - Line 281 — `expect(body).toContain('most recent 1000 rated games in bullet over the last 36 months')` → "...3000...".
       - Line 285 `it(...)` title — replace "1000" with "3000".
       - Line 289 — `expect(body).toContain('most recent 1000 rated games per time control over the last 36 months')` → "...3000...".

    Do NOT change any other "1000" occurrences in the frontend (search first to confirm none are in this context).

    Run the pre-PR frontend gates:

        cd frontend && npm run lint && npm test -- --run

    Then commit. Suggested message:

        copy(percentile-chip): update tooltip + explainer to recent 3000 games

        Follows backend cap bump (RECENT_GAMES_PER_TC_CAP 1000 → 3000).
        PercentileChip tooltip bullet 2, Endgames page percentile-badge
        explainer, and corresponding test assertions all updated.
  </action>
  <verify>
    <automated>
      grep -RIn --include='*.ts' --include='*.tsx' -E 'most recent 1000 rated games|your most recent 1000 rated games|Your most recent 1000 rated games' frontend/src ; test $? -eq 1
    </automated>
  </verify>
  <done>
    - Tooltip bullet 2 (per-TC and aggregated) reads "3000".
    - Endgames explainer steps 1 and 3 read "3000".
    - All 4 test assertions updated; `npm test -- --run` passes.
    - `npm run lint` passes.
    - Single commit made on the current branch.
  </done>
</task>

</tasks>

<verification>
After both commits land:

1. `git log --oneline -2` shows the two commits in order (constant bump, then frontend copy).
2. Repo-wide grep for stale wording returns nothing in the in-scope surfaces:

       grep -RIn --include='*.py' --include='*.ts' --include='*.tsx' \
         -E '\brecent-1000\b|most recent 1000 rated games|TC.s recent-1000 pool|1000-cap' \
         app/ scripts/ frontend/src tests/

3. Pre-PR checklist passes cleanly from the project root:

       uv run ruff format app/ tests/
       uv run ruff check app/ tests/ --fix
       uv run ty check app/ tests/
       uv run pytest -x
       ( cd frontend && npm run lint && npm test -- --run )

Manual UAT (optional, NOT a hard gate — out-of-band per task brief): SQL spot-check for user 8 blitz with the new cap should land `n_games` ≈ 250 (vs current 82).
</verification>

<success_criteria>
- `RECENT_GAMES_PER_TC_CAP = 3000` in `app/services/canonical_slice_sql.py`.
- No remaining "1000" references in backend docstrings or frontend tooltip / explainer copy / tests that describe the recent-games-per-TC cap.
- Pre-PR checklist (ruff format, ruff check, ty, pytest, frontend lint + tests) passes cleanly.
- Two atomic commits on `gsd/phase-94.4-peer-relative-percentile-chip-refinement`.
- No changes to cohort tables, no Alembic migration, no `bin/reset_db.sh`, no benchmark regen.
</success_criteria>

<output>
Two commits on the current branch. No SUMMARY.md required (quick task).
</output>
