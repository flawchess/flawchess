---
phase: quick-260626-bdt
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - app/repositories/library_repository.py
  - app/services/library_service.py
  - tests/test_library_repository.py
  - frontend/src/pages/library/FlawsTab.tsx
  - frontend/src/pages/library/GamesTab.tsx
autonomous: true
requirements:
  - QUICK-260626-bdt-suppress-decided-lost-tactic-tags
user_setup: []

must_haves:
  truths:
    - "A flaw whose pre-move eval is decisively lost for the mover has its tactic-motif tag + depth treated as ABSENT on the Flaws page, Games page, and eval-chart tooltip — but the flaw itself still exists."
    - "Filtering by a motif (e.g. fork) does NOT return fork-flaws from decided-lost positions; the matched_count agrees with the filtered list."
    - "Tactic depth min/max filter excludes decided-lost flaws (their depth is suppressed)."
    - "Decided-lost flaws STILL count in blunder/mistake severity totals and STILL render eval-chart markers."
    - "Null pre-move eval fails OPEN: the tactic tag is shown / the flaw matches the motif filter."
    - "The Flaws path (query_flaws) and the Games path (flaw_exists_from_table EXISTS) agree on which flaws match a tactic filter."
    - "The tactic explorer / tactic-comparison surfaces are unchanged (full detail retained)."
  artifacts:
    - path: "app/repositories/library_repository.py"
      provides: "decided-lost predicate (SQL + Python), SQL gate in build_flaw_filter_clauses, PositionBefore join in flaw_exists_from_table, decided_lost short-circuit in tactic_slot_visible, decided_lost threading in query_flaws"
      contains: "MATE_LADDER_LOPSIDED_CP"
    - path: "app/services/library_service.py"
      provides: "decided_lost computed from pre-move position eval and threaded into tactic_slot_visible for the eval-chart tactic_by_ply build"
    - path: "tests/test_library_repository.py"
      provides: "6 backend tests covering exclusion, severity-still-counts, fail-open, Flaws/Games agreement, POV sign-flip, boundary"
  key_links:
    - from: "app/repositories/library_repository.py:build_flaw_filter_clauses"
      to: "app/repositories/library_repository.py:flaw_exists_from_table"
      via: "decided-lost SQL predicate ANDed onto the tactic clause; flaw_exists adds the PositionBefore (ply N-1) LEFT JOIN that supplies eval columns"
      pattern: "decided_lost"
    - from: "app/repositories/library_repository.py:tactic_slot_visible"
      to: "app/services/library_service.py:_build_card"
      via: "decided_lost bool threaded from pre-move position eval into tactic_by_ply build"
      pattern: "decided_lost"
---

<objective>
Suppress tactic-motif tags (label + depth number) on flaws whose PRE-MOVE eval was already decisively lost for the mover. Backend-driven, ON BY DEFAULT, no user toggle. READ/SERVE-LAYER ONLY — the classifier (flaws_service.py) and all stored game_flaws columns/stats stay untouched.

A "decided-lost" flaw still EXISTS, still counts in severity totals, and still renders an eval-chart marker; only its tactic-motif tag + tactic depth are treated as absent everywhere the tactic tag is queried, listed, counted, filtered, or shown in the eval-chart tooltip.

Purpose: a tactic "found" or "missed" in a position that was already lost is noise — it teaches nothing and inflates tactic surfaces. Suppressing it at the serve layer keeps the underlying data intact while cleaning the Flaws/Games/eval-chart surfaces.

Output: a shared decided-lost predicate (SQL + Python), gated into the two filter/serialization chokepoints, plus backend tests and a frontend null-tag verification.
</objective>

<execution_context>
@$HOME/.claude/gsd-core/workflows/execute-plan.md
@$HOME/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@./CLAUDE.md

# Core files (read fully before editing):
@app/repositories/library_repository.py
@app/services/library_service.py
@app/schemas/library.py
@tests/test_library_repository.py

# Constant source (DO NOT MODIFY this file):
# app/services/flaws_service.py — MATE_LADDER_LOPSIDED_CP = 700 (line ~69)
</context>

<architecture_notes>
Chokepoints discovered during planning (the executor must verify line numbers against current code, but the structure holds):

1. SQL FILTER chokepoint — `build_flaw_filter_clauses` (library_repository.py ~431).
   Used by BOTH `query_flaws` (Flaws list + its matched_count) AND `flaw_exists_from_table` (Games-tab EXISTS).
   `query_utils.apply_game_filters` delegates the Games-tab tactic EXISTS to `flaw_exists_from_table`, so fixing that one function covers the Games tab automatically — do NOT add a separate gate in query_utils.py.

2. SERIALIZATION chokepoint — `tactic_slot_visible` (library_repository.py ~337).
   The single Python display predicate, called at BOTH `query_flaws` row serialization (Flaws list/modal, ~869-952) AND `_build_card`'s `tactic_by_ply` build (library_service.py ~439/458, which feeds eval-chart FlawMarkers via `_build_eval_series`). A single `decided_lost` short-circuit covers both serialization surfaces.

3. Tactic explorer / tactic-comparison (`fetch_tactic_comparison`, `get_tactic_comparison`, `TacticLinesResponse`/`/tactic-lines`) does NOT route through these two chokepoints — it reads game_flaws/positions directly with its own aggregation. It therefore retains full detail with no change. Confirm no suppression leaks into it (test/grep, not code).

PRE-MOVE EVAL availability:
- `query_flaws` already LEFT-JOINs `PositionBefore` (ply=N-1, aliased) → `pos_before.eval_cp` / `pos_before.eval_mate` are in scope at serialization.
- `flaw_exists_from_table` does NOT currently join positions → must add a `PositionBefore` aliased LEFT JOIN at ply = GameFlaw.ply - 1 (user+game scoped) inside the EXISTS, so the same eval columns feed the SQL predicate.
- `_build_card` (library_service) has `positions: list[GamePosition]` in scope → build a `{ply: GamePosition}` index once and look up ply N-1.

PREDICATE — "decided-lost", pre-move, MOVER-POV (mover == user on all these surfaces because every path applies `player_only_gate`; tactic chips only ever attach to player plies):
- eval is WHITE-POV on game_positions (eval_cp / eval_mate; eval_mate positive = White has mate).
- Decided-lost when (sign-flipped to the mover):
  - white mover: `eval_mate_before < 0` (Black has mate) OR `eval_cp_before <= -MATE_LADDER_LOPSIDED_CP`.
  - black mover: `eval_mate_before > 0` (White has mate) OR `eval_cp_before >= +MATE_LADDER_LOPSIDED_CP`.
- FAIL OPEN: when BOTH eval_cp_before AND eval_mate_before are NULL → NOT decided-lost. A row with a mate eval but null cp (or vice versa) is handled by the per-column NULL guards (an absent column simply does not contribute its disjunct). eval_mate == 0 is treated as not-decisive (strict `< 0` / `> 0`).
- Reuse `MATE_LADDER_LOPSIDED_CP` (import from flaws_service) — NO magic 700 (CLAUDE.md).
</architecture_notes>

<tasks>

<task type="auto">
  <name>Task 1: Decided-lost predicate + SQL gate + serialization nulling (backend)</name>
  <files>app/repositories/library_repository.py, app/services/library_service.py</files>
  <action>
Implement the decided-lost suppression at the two chokepoints. All work is read/serve-layer; do NOT touch flaws_service.py, game_flaws columns, or any stats aggregation.

1. In library_repository.py, import the threshold constant: add `MATE_LADDER_LOPSIDED_CP` to the existing `from app.services.flaws_service import (...)` block (alongside FlawSeverity, FlawTag). No magic 700 anywhere.

2. Add two co-located helper functions near build_flaw_filter_clauses, each with explicit return types and a docstring cross-referencing the other (mirroring the existing tactic_slot_visible ↔ build_flaw_filter_clauses convention — both must agree on "decided-lost"):
   - `is_decided_lost(eval_cp_before: int | None, eval_mate_before: int | None, *, mover_is_white: bool) -> bool` — the pure-Python predicate. Strict mate signs (`< 0` / `> 0`); cp uses `<= -MATE_LADDER_LOPSIDED_CP` (white) / `>= MATE_LADDER_LOPSIDED_CP` (black). Both args None → False (fail open). Keep nesting <= 2.
   - `decided_lost_sql(eval_cp_col: Any, eval_mate_col: Any, user_color_col: Any) -> ColumnElement[bool]` — the SQLAlchemy equivalent. Build it NULL-safe so it never evaluates to SQL NULL: wrap each disjunct in `and_(col.isnot(None), <against-expr>)` so a NULL column contributes False, and pick the sign with `Game.user_color == "white"` (use the passed `user_color_col`). Shape: `or_(and_(eval_mate_col.isnot(None), or_(and_(white, eval_mate_col < 0), and_(~white, eval_mate_col > 0))), and_(eval_cp_col.isnot(None), or_(and_(white, eval_cp_col <= -MATE_LADDER_LOPSIDED_CP), and_(~white, eval_cp_col >= MATE_LADDER_LOPSIDED_CP))))` where `white = user_color_col == "white"`. Because every disjunct is NULL-guarded, the result is always true/false (never NULL) → fail-open is structural.

3. Gate the SQL tactic clause in `build_flaw_filter_clauses`: add a new keyword param `decided_lost: ColumnElement[bool] | None = None` (default None = no suppression, backward-compatible). When non-None, AND `not_(decided_lost)` onto the assembled tactic clause ONCE — i.e. change the final `clauses.append(or_(*pair_branches))` to append `and_(or_(*pair_branches), not_(decided_lost))` when decided_lost is provided, else the existing `or_(*pair_branches)`. Import `not_` from sqlalchemy. Do NOT gate severity/tempo/opportunity/impact/phase clauses — ONLY the tactic clause. Update the docstring.

4. Add a `decided_lost: bool = False` keyword param to `tactic_slot_visible`. As the FIRST check in the body (before orientation/confidence/family/depth), `if decided_lost: return False`. Update the docstring to note this is the decided-lost suppression and that it must stay consistent with the SQL `decided_lost_sql` gate.

5. Thread decided_lost through `flaw_exists_from_table`: create a `PositionBefore = aliased(GamePosition, name="pos_before_exists")` inside the function; build `dl = decided_lost_sql(PositionBefore.eval_cp, PositionBefore.eval_mate, Game.user_color)`; pass `decided_lost=dl` into the `build_flaw_filter_clauses(...)` call. Add a `.outerjoin(PositionBefore, (PositionBefore.game_id == GameFlaw.game_id) & (PositionBefore.user_id == GameFlaw.user_id) & (PositionBefore.ply == GameFlaw.ply - 1))` to the inner `select(GameFlaw.ply)` BEFORE the `.where(...)`. LEFT JOIN so ply 0/1 flaws (no prior position) keep null eval → fail open. The EXISTS stays correlated on `GameFlaw.game_id == Game.id` and user-scoped (do not weaken T-108-07).

6. Thread decided_lost through `query_flaws`: it already has the `PositionBefore` alias and joins it. Build `dl = decided_lost_sql(PositionBefore.eval_cp, PositionBefore.eval_mate, Game.user_color)` and pass `decided_lost=dl` into the `build_flaw_filter_clauses(...)` call. In the row serialization, for EACH of the 6 tactic-field conditionals (allowed/missed × motif/confidence/depth), pass `decided_lost=is_decided_lost(pos_before.eval_cp if pos_before else None, pos_before.eval_mate if pos_before else None, mover_is_white=(game.user_color == "white"))` into the `tactic_slot_visible(...)` call. Compute this bool ONCE per row (assign to a local, e.g. `row_decided_lost`) before constructing the FlawListItem to avoid recomputation and keep the comprehension readable — if the existing list comprehension can't host a local cleanly, lift the per-row construction into a small `_build_flaw_item(...)` helper rather than inlining `is_decided_lost` six times (keep functions shallow per CLAUDE.md).

7. In library_service.py `_build_card`, thread decided_lost into the eval-chart `tactic_by_ply` build (the two `tactic_slot_visible(...)` calls, ~439 and ~458): import `is_decided_lost` from library_repository (library_service already imports from it). Build a `pos_by_ply: dict[int, GamePosition] = {p.ply: p for p in positions}` once before the `for fr in flaw_rows` loop. Inside the loop compute `prev = pos_by_ply.get(fr.ply - 1)` then `fr_decided_lost = is_decided_lost(prev.eval_cp if prev else None, prev.eval_mate if prev else None, mover_is_white=(game.user_color == "white"))` and pass `decided_lost=fr_decided_lost` into BOTH tactic_slot_visible calls. Mover == user here (flaw_rows are player-gated via fetch_page_game_flaws).

Type safety (ty must pass): explicit return types on both helpers; use `Any` for the SQLAlchemy column params (matching the existing `_tactic_cols` style); the `mover_is_white` param is keyword-only `bool`. Do not introduce bare `str` for color — compare `game.user_color == "white"`.
  </action>
  <verify>
    <automated>uv run ruff format app/ && uv run ruff check app/ --fix && uv run ty check app/ tests/</automated>
  </verify>
  <done>
- `MATE_LADDER_LOPSIDED_CP` is imported and used in library_repository.py; grep finds no bare `700` in the new code.
- `build_flaw_filter_clauses`, `flaw_exists_from_table`, and `query_flaws` all thread a `decided_lost` SQL expression; `tactic_slot_visible` has a `decided_lost: bool` first-return short-circuit.
- `_build_card` computes per-flaw decided_lost from the ply N-1 position eval and passes it into both tactic_slot_visible calls.
- Severity/tempo/opportunity/impact/phase clauses are NOT gated by decided_lost (only the tactic clause).
- `uv run ty check app/ tests/` passes with zero errors; ruff clean.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Backend tests for decided-lost suppression</name>
  <files>tests/test_library_repository.py</files>
  <behavior>
Mirror the existing fixtures in tests/test_library_repository.py (`_seed_game`, `_seed_position`, `_seed_game_flaw`, the per-user cleanup pattern, and the `query_flaws` / `flaw_exists_from_table` call styles already exercised by TestQueryFlaws / TestExistsFilter). `_seed_position(eval_cp=..., eval_mate=...)` already supports seeding the pre-move eval at ply N-1. `_seed_game_flaw(allowed_tactic_motif=int(TacticMotifInt.FORK), allowed_tactic_confidence=100, allowed_tactic_depth=...)` seeds a tactic-bearing flaw (confidence >= 70 so it passes the chip lever). Use a distinct user_id and clean up non-guest rows in a finally block per the eval-lottery isolation memory.

Add a `TestDecidedLostSuppression` class with these tests (one decisive behavior each):

1. test_decided_lost_fork_excluded_from_motif_filter — white mover, flaw at ply N with a FORK in the allowed slot (conf 100), seed `_seed_position(ply=N-1, eval_cp=-900)`. `query_flaws(..., tactic_families=["fork"], orientation="allowed")` returns 0 rows for that flaw (excluded). A control flaw in a contestable position (eval_cp=-100) with the same fork IS returned.

2. test_decided_lost_flaw_still_counts_severity — the same decided-lost fork flaw (blunder, eval_cp_before=-900) STILL appears with NO tactic filter (default query_flaws), AND its serialized `allowed_tactic_motif`/`allowed_tactic_depth` are None (tag suppressed) while `severity == "blunder"` and the row is present (flaw still exists + counts).

3. test_null_pre_move_eval_fails_open — flaw with NO PositionBefore row (ply 0/1) OR a ply N-1 position with eval_cp=None AND eval_mate=None: the fork tag is NOT suppressed — `query_flaws(tactic_families=["fork"], orientation="allowed")` RETURNS the row, and the serialized `allowed_tactic_motif` is non-None.

4. test_flaws_and_games_paths_agree — for the SAME seeded data (one decided-lost fork game, one contestable fork game), assert `query_flaws(tactic_families=["fork"])` and the `flaw_exists_from_table`-backed `apply_game_filters` Games path (use the existing `_matching_game_ids`-style helper or call flaw_exists path) select the SAME set of games: contestable matches, decided-lost does not.

5. test_pov_sign_flip — (a) white mover with eval_cp_before=-800 → suppressed; (b) black mover (`_seed_game(user_color="black")`, flaw at an ODD ply so player_only_gate keeps it) with eval_cp_before=+800 → suppressed; (c) the clearly-WINNING equivalents (white mover at +800, black mover at -800) are NOT suppressed (tag shown / matches filter). Mate variant optional but encouraged: white mover eval_mate_before=-2 suppressed; eval_mate_before=+2 not.

6. test_boundary_threshold — white mover at exactly eval_cp_before == -MATE_LADDER_LOPSIDED_CP (-700) IS suppressed (inclusive); a flaw at eval_cp_before=-300 (still playable) is NOT suppressed.

Each test asserts on either query_flaws row presence/serialized tactic field None-ness, or on the selected game-id set — not on internal predicate calls. Import `MATE_LADDER_LOPSIDED_CP` and `TacticMotifInt` for the seeds.
  </behavior>
  <action>
Write the `TestDecidedLostSuppression` class described in <behavior>. Reuse the module's existing seed helpers and call signatures exactly (read TestQueryFlaws / TestExistsFilter in the same file for the canonical invocation of query_flaws and the Games-path filter). Follow the eval-lottery test-isolation memory: distinct user_id, finally-block cleanup of any non-guest Game/GamePosition/game_flaws rows so parallel `-n auto` runs do not flake. No new fixtures unless an existing one genuinely cannot express the case; prefer extending call args over new helpers.
  </action>
  <verify>
    <automated>uv run pytest tests/test_library_repository.py -k DecidedLost -p no:randomly</automated>
  </verify>
  <done>
- 6 tests in TestDecidedLostSuppression pass.
- `uv run pytest tests/test_library_repository.py -n auto` is green (no isolation flakes / no leaked-row failures).
- Tests assert decided-lost exclusion, severity-still-counts + tag-nulled, fail-open on null eval, Flaws/Games agreement, POV sign-flip both colors + winning-side non-suppression, and the -700 boundary.
  </done>
</task>

<task type="auto">
  <name>Task 3: Frontend null-tag verification (Flaws/Games/eval-chart tooltip)</name>
  <files>frontend/src/pages/library/FlawsTab.tsx, frontend/src/pages/library/GamesTab.tsx</files>
  <action>
The backend now returns `null` for `allowed_tactic_motif`/`missed_tactic_motif` (+ confidence + depth) on decided-lost flaws. These fields were ALREADY nullable (gated by confidence), so the frontend SHOULD handle null/absent tactic tags cleanly with no change. VERIFY this — do not add a toggle or new prop.

1. Locate the tactic-tag chip rendering in FlawsTab.tsx and GamesTab.tsx, and the eval-chart tooltip tactic entry (grep for `tactic_motif`, `tactic_depth`, `TacticChip`, or the tooltip component the eval chart uses — likely shared, e.g. an EvalChart tooltip in frontend/src/components or frontend/src/pages/library). Confirm each render site guards on the motif being non-null/defined before rendering a chip or a depth badge (e.g. `motif && <Chip .../>`), so a null motif renders NOTHING — no empty chip, no "undefined", no `depth+1` NaN badge, no crash.

2. If any site renders a chip/badge WITHOUT a null guard (would show an empty chip or `undefined`/`NaN`), add the minimal guard there (and apply the SAME guard to the mobile variant per CLAUDE.md "Always apply changes to mobile too"). If all sites already guard correctly, make NO code change and record that in the SUMMARY.

3. Only if you touched a shared TS type or property access, run the type build (lint+test do not type-check per CLAUDE.md).
  </action>
  <verify>
    <automated>cd frontend && npm run lint && npm run build</automated>
  </verify>
  <done>
- Every tactic-tag / depth render site in FlawsTab, GamesTab, and the eval-chart tooltip guards on a non-null motif → a null motif renders nothing (verified by reading the code; minimal guard added only where missing, mobile variant included).
- `npm run lint` and `npm run build` (tsc) pass.
- SUMMARY records whether any frontend change was needed or the existing null-guards already sufficed.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| client → /library/flaws, /library/games | Filter query params (tactic_family, orientation, depth, severity) cross into SQL — already bound-parameterized via closed Literal enums / int-coded dict lookups (no change here). |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-bdt-01 | Information disclosure | new PositionBefore LEFT JOIN inside flaw_exists_from_table | mitigate | Join is user-scoped (`PositionBefore.user_id == GameFlaw.user_id`) and game-correlated; the EXISTS keeps `GameFlaw.user_id == user_id` and `GameFlaw.game_id == Game.id` (T-108-07 unchanged — no cross-user position rows can attach). |
| T-bdt-02 | Tampering | decided-lost predicate (SQL + Python) | accept | Read-only serve-layer gate over already-stored eval columns; no writes, no new user input, no new package. Predicate is NULL-safe (fail-open structural). |
</threat_model>

<verification>
Run after all tasks:
- `uv run ruff format app/ tests/ && uv run ruff check app/ tests/`
- `uv run ty check app/ tests/` (zero errors)
- `uv run pytest tests/test_library_repository.py -n auto`
- `cd frontend && npm run lint && npm run build`

Sanity greps:
- `grep -n "decided_lost\|is_decided_lost\|decided_lost_sql" app/repositories/library_repository.py app/services/library_service.py` — predicate threaded through all four backend sites.
- `grep -rn "700" app/repositories/library_repository.py` — no new bare 700 literal (constant only).
- Confirm flaws_service.py, game_flaws columns, and stats aggregation functions (fetch_stats_aggregates, fetch_flaw_trend_rows, fetch_tactic_comparison) are unchanged: `git diff --stat` shows only the 5 files in files_modified.
</verification>

<success_criteria>
- Decided-lost flaws have their tactic-motif tag + depth suppressed on Flaws page, Games page, and eval-chart tooltip; the flaw itself, its severity count, and its eval marker remain.
- Motif filter, depth filter, and the matched_count all exclude decided-lost flaws consistently (same predicate at the SQL chokepoint).
- Flaws path and Games path agree on tactic-filter matching.
- Null pre-move eval fails open (tag shown / flaw matches).
- POV sign-flip correct for white and black movers; winning-side equivalents not suppressed; -700 boundary inclusive.
- Tactic explorer / tactic-comparison surfaces unchanged.
- flaws_service.py + stored columns + stats untouched.
- ty, ruff, backend tests, frontend lint+build all green.
</success_criteria>

<output>
Create `.planning/quick/260626-bdt-suppress-tactic-motif-tags-on-flaws-from/260626-bdt-SUMMARY.md` when done.
</output>
