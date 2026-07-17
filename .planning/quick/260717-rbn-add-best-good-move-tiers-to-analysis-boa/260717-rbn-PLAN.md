---
phase: quick-260717-rbn
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - app/schemas/library.py
  - app/services/library_service.py
  - tests/services/test_library_service.py
  - frontend/src/lib/theme.ts
  - frontend/src/lib/bestGlyph.ts
  - frontend/src/lib/goodGlyph.ts
  - frontend/src/components/board/boardMarkers.tsx
  - frontend/src/pages/Analysis.tsx
  - frontend/src/components/results/LibraryGameCard.tsx
  - frontend/src/types/library.ts
autonomous: true
requirements: []
must_haves:
  truths:
    - "An analyzed game's eval_series emits best_move_tier='best' when the played move equals the stored game_positions.best_move (identity), out-of-book, and it is not gem/great."
    - "An analyzed game's eval_series emits best_move_tier='good' when the played move's mover-POV expected-score drop is below INACCURACY_DROP, out-of-book, and it is not best/gem/great."
    - "Book/theory plies (ply < opening_ply_count) never receive a best/good label."
    - "The analysis board move badge renders a green star (best) / green thumbs-up (good) corner glyph on the current move for BOTH players, yielding to any severity marker."
    - "The library game card scrubbed miniboard renders the best/good corner glyph, user-scoped via isUserPly."
    - "Frontend type-checks (tsc -b), knip finds no unused exports, and all backend + frontend tests pass."
  artifacts:
    - app/services/library_service.py
    - frontend/src/lib/bestGlyph.ts
    - frontend/src/lib/goodGlyph.ts
    - frontend/src/components/board/boardMarkers.tsx
  key_links:
    - "EvalPoint.best_move_tier literal union (backend app/schemas/library.py + frontend types/library.ts) must include 'best' and 'good' or the payload/consumers silently drop them."
    - "best identity comparison must be UCI-move-object equality (played parsed from SAN vs best_move parsed from UCI) on the pre-move board — never a raw SAN==UCI string compare."
    - "'good' must reuse _run_all_moves_pass output keyed at pos.ply (severity is None), the exact convention the shipped flaw markers use."
---

<objective>
Add two new server-computed per-ply move-quality tiers — Best and Good — to the
existing `EvalPoint.best_move_tier` field (currently `'gem'|'great'|null`), and
render them as corner badges on the analysis board move badge (both players) and
the library game card scrubbed miniboard (user-scoped). No DB schema changes, no
engine work, zero impact on the tier-4b backfill.

Purpose: surface positive-play feedback (the user played the engine's best move,
or a clean non-flaw move) alongside the existing gem/great rarity badges, reusing
data already stored in `game_positions` (evals + best_move + move played).

Output: extended backend classifier in `_build_eval_series`, extended
`best_move_tier` union (backend + frontend), two new green corner glyphs (star =
best, thumbs-up = good) in `boardMarkers.tsx`, wired into both surfaces.
</objective>

<execution_context>
@$HOME/.claude/gsd-core/workflows/execute-plan.md
@$HOME/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@CLAUDE.md

# Backend conventions (reuse verbatim — do not re-derive)
@app/services/best_move_candidates.py
@app/services/flaws_service.py
@app/services/library_service.py
@app/schemas/library.py
@app/services/zobrist.py

# Frontend surfaces
@frontend/src/components/board/boardMarkers.tsx
@frontend/src/components/results/LibraryGameCard.tsx
@frontend/src/components/icons/GemIcon.tsx
@frontend/src/components/icons/GreatMoveIcon.tsx
@frontend/src/lib/gemGlyph.ts
@frontend/src/lib/greatGlyph.ts
@frontend/src/types/library.ts
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Backend — emit 'best'/'good' tiers from _build_eval_series</name>
  <files>app/schemas/library.py, app/services/library_service.py, tests/services/test_library_service.py</files>
  <behavior>
    Precedence per ply (highest wins): gem > great > best > good > (null/flaw).
    - Test: an out-of-book ply whose played move == game_positions.best_move, classified "neither" by classify_best_move, gets best_move_tier='best', maia_prob stays None.
    - Test: an out-of-book ply where played != best_move and the mover-POV drop is below INACCURACY_DROP (0.05) gets best_move_tier='good', maia_prob None.
    - Test: a negative drop (played evaluates BETTER than the pre-move eval) with played != best_move classifies as 'good'.
    - Test: a ply that classify_best_move returns 'gem'/'great' for keeps 'gem'/'great' (never downgraded to best/good) and still carries maia_prob.
    - Test: a book ply (ply < opening_ply_count) with played == best_move gets best_move_tier=None (no best/good in book).
    - Test: a ply whose drop >= INACCURACY_DROP (an inaccuracy/mistake/blunder) and played != best_move gets best_move_tier=None (falls through to the flaw path).
    - Test: a ply with a missing eval (no all_moves entry) and best_move absent gets best_move_tier=None.
    - Test: the terminal position (move_san None) never gets a tier.
  </behavior>
  <action>
Extend the tier literal to four values and compute best/good in the existing per-ply loop of `_build_eval_series`.

1. In `app/schemas/library.py`, widen `EvalPoint.best_move_tier` from `Literal["gem", "great"] | None` to `Literal["gem", "great", "best", "good"] | None`. Update the field's docstring: 'best' = played move equals the stored engine best_move (identity, noise-immune); 'good' = mover-POV expected-score drop below INACCURACY_DROP and not best/gem/great. Note maia_prob stays None for best/good (it is a gem/great-only rarity stat).

2. In `app/services/library_service.py`:
   - Add a parameter `opening_ply_count: int = 0` to `_build_eval_series`. Thread the already-computed value from each caller: `_build_card` computes `moves_data` and calls `find_opening_ply_count` (currently at the card level) — reorder so `opening_ply_count = find_opening_ply_count(moves_data) if moves_data else 0` is available BEFORE the `_build_eval_series(...)` call, and pass it in. Verify every call site of `_build_eval_series` passes it (grep for `_build_eval_series(`).
   - Add a module-level helper `_best_move_identity_plies(positions: list[GamePosition]) -> set[int]` that replays ONE `chess.Board()` over `positions` in ply order: for each pos with `move_san` not None, parse the played move via `board.parse_san(pos.move_san)` on the PRE-move board, and if `pos.best_move` is not None compare it to `chess.Move.from_uci(pos.best_move)` by Move-object equality; collect `pos.ply` into the set when equal; then `board.push(played_move)`. Wrap the whole replay in `try/except (ValueError, chess.IllegalMoveError)` and stop early on a malformed SAN/UCI (return the plies collected so far) — mirror the guard posture of `_same_dest_as_best_line` in flaws_service. Do NOT compare SAN to UCI as strings.
   - In the per-ply loop, AFTER the existing gem/great block (which sets `best_move_tier` only when `classify_best_move` returns non-"neither"), when `best_move_tier` is still None, `pos.move_san is not None`, and `pos.ply >= opening_ply_count` (out of book), apply: if `pos.ply in identity_plies` set `best_move_tier = "best"`; else read `entry = all_moves.get(pos.ply)` and when `entry is not None` and its severity element is None set `best_move_tier = "good"`. `all_moves` is already computed at the top of the function (`_run_all_moves_pass(positions)`) — reuse it, do not recompute. This keys 'good' at pos.ply exactly like the shipped flaw markers (`all_moves[pos.ply]` describes the move `pos.move_san` from position pos.ply — confirmed by the post-move eval convention in zobrist.py: row P eval = eval of position P+1, so all_moves[P] es_before=positions[P-1], es_after=positions[P] is the quality of positions[P].move_san). Leave maia_prob None for best/good.
   - Import `chess` and `find_opening_ply_count` if not already imported in this module (find_opening_ply_count is already imported).

3. Add the tests above to `tests/services/test_library_service.py`, following the existing gem/great `_build_eval_series` fixture pattern (construct GamePosition rows with eval_cp/eval_mate/move_san/best_move; assert on the returned eval_series[i].best_move_tier). Use realistic UCI/SAN pairs so `parse_san`/`from_uci` succeed (e.g. from the initial position, move_san "e4" with best_move "e2e4").

Do NOT apply the imported-eval divergence guard to best/good (it is gem/great-only per the locked scope). Do NOT touch the tier-4b backfill, game_best_moves, or any SQL.
  </action>
  <verify>
    <automated>uv run pytest tests/services/test_library_service.py -x -q && uv run ty check app/ tests/ && uv run ruff check app/ tests/</automated>
  </verify>
  <done>eval_series emits 'best'/'good' per the precedence and book gate; all new + existing library_service tests pass; ty and ruff clean.</done>
</task>

<task type="auto">
  <name>Task 2: Frontend — green star/thumbs-up corner glyphs on board + card</name>
  <files>frontend/src/lib/theme.ts, frontend/src/lib/bestGlyph.ts, frontend/src/lib/goodGlyph.ts, frontend/src/components/board/boardMarkers.tsx, frontend/src/pages/Analysis.tsx, frontend/src/components/results/LibraryGameCard.tsx, frontend/src/types/library.ts</files>
  <action>
Render Best (green circle + white star) and Good (green circle + white thumbs-up) corner glyphs on the two in-scope surfaces. All semantic colors come from theme.ts.

1. `frontend/src/types/library.ts`: widen `EvalPoint.best_move_tier` to `'gem' | 'great' | 'best' | 'good' | null` (mirror the backend). Update the doc comment to describe best (identity) and good (sub-inaccuracy drop) and that maia_prob is null for them.

2. `frontend/src/lib/theme.ts`: add two green semantic constants next to `MAIA_ACCENT`/`GREAT_ACCENT`, e.g. `BEST_ACCENT` (a deeper green, reuse the WDL_WIN hue 145 at a distinct lightness) and `GOOD_ACCENT` (a lighter green, e.g. the existing MOVE_QUALITY_GOOD light green hue). They must be visually distinguishable from each other and from the violet/blue gem/great accents. Do NOT hard-code these hues in components.

3. `frontend/src/lib/bestGlyph.ts` and `frontend/src/lib/goodGlyph.ts`: create plain color-spec modules mirroring `gemGlyph.ts`/`greatGlyph.ts` exactly (`export const BEST_GLYPH: { color: string } = { color: BEST_ACCENT }` / `GOOD_GLYPH` with `GOOD_ACCENT`). Plain modules, not components (react-refresh rule, matching the existing glyph files). Do NOT create standalone BestIcon.tsx / GoodIcon.tsx React components — the two in-scope surfaces are board SVG overlays (boardMarkers), nothing imports a standalone icon component, and knip fails CI on unused exports (the move-list and count-badge surfaces that consume GemIcon/GreatMoveIcon are explicitly out of scope).

4. `frontend/src/components/board/boardMarkers.tsx`: add `best?: boolean` and `good?: boolean` to `SquareMarker` (document them as additive, mutually-exclusive-by-construction alternatives like the existing `gem`/`great`/`book` flags). In `SquareMarkerBadge`, add two branches after the `great`/`book` branches, before the severity fallback: `marker.best` → green circle filled `BEST_GLYPH.color` + a white lucide `Star`; `marker.good` → green circle filled `GOOD_GLYPH.color` + a white lucide `ThumbsUp`. Reuse the existing badge geometry (`iconSize = 2 * r * GEM_ICON_DIAMETER_RATIO`, same `MARKER_STROKE`, `stroke="#fff"`) exactly as the gem branch — no new geometry constants. Import `Star`, `ThumbsUp` from `lucide-react`.

5. `frontend/src/pages/Analysis.tsx` (surface 1 — board move badge, BOTH players): add a `storedBestGoodByPly` memo mirroring `storedTierByPly` (line ~706) but keeping `best_move_tier === 'best' | 'good'` (map ply → 'best'|'good'), with NO user filter (the board intentionally shows both players, same as gems — see the storedTierByPly comment). In the `boardSquareMarkers` memo (line ~2573), after the existing gem/great `withMarker` block and before/around the book block, when the current node is a mainline ply (`currentMainlinePly >= 0`), `lastMove != null`, the square does NOT already carry a severity/gem/great marker, and `storedBestGoodByPly.get(currentMainlinePly)` is 'best'/'good', append `{ square: lastMove.to, best: true }` or `{ square: lastMove.to, good: true }`. Best/good yield to severity/gem/great (same defensive precedence the gem block already uses) and outrank the book badge (so exclude best/good squares from the book-append guard too). Add `storedBestGoodByPly` to the memo deps. Do NOT touch the `merged` move-list marker memo (line ~2050) — move-list labels for best/good are OUT of scope.

6. `frontend/src/components/results/LibraryGameCard.tsx` (surface 2 — card corner badge, USER-scoped): extend `bestTierByPly` (line ~457) to also map `'best'`/`'good'` (keep the existing `isUserPly` user-scoping — best/good are position-scoped, show only the user's own). Widen its Map value type to `'gem' | 'great' | 'best' | 'good'`. In the `squareMarkers` memo (line ~706), after the gem/great branches, add: `tier === 'best'` → `[{ square: hoverEntry.to, best: true }]`; `tier === 'good'` → `[{ square: hoverEntry.to, good: true }]` (severity still wins, matching the existing early-return). Do NOT add best/good count badges (bestMoveBadges), cycling, or filters — all OUT of scope. The existing `lastMoveColor` fallback to `MOVE_HIGHLIGHT_GOOD` for clean moves is acceptable as-is; optionally give a 'best' tier its own tint if trivial, but the corner badge is the required deliverable.

7. After editing shared types, run `npx tsc -b` (or `npm run build`) — npm lint/test do NOT type-check (esbuild strips types), and best_move_tier is a shared union.

data-testid: the corner glyphs are SVG marks inside the existing board/miniboard containers (which already carry `data-testid="chessboard"` / the miniboard testid) — no new interactive elements are added, so no new data-testid is required (consistent with how gem/great corner glyphs render today).
  </action>
  <verify>
    <automated>cd frontend && npx tsc -b && npm run lint && npm run knip && npm test -- --run</automated>
  </verify>
  <done>best/good render as green star/thumbs-up corner glyphs on the analysis board (both players) and the library card miniboard (user-scoped); tsc/lint/knip clean; frontend tests pass.</done>
</task>

</tasks>

<verification>
- Backend: `uv run pytest tests/services/test_library_service.py -x -q` green; `uv run ty check app/ tests/` zero errors.
- Frontend: `cd frontend && npx tsc -b && npm run lint && npm run knip && npm test -- --run` all green.
- Manual sanity (optional): open an analyzed game on /analysis, step to a move where the user played the engine's best move out of book — a green star badge appears on the move square; a clean non-best move shows a green thumbs-up. Library Games tab card miniboard shows the same on the user's own plies when scrubbed.
</verification>

<success_criteria>
- `EvalPoint.best_move_tier` is `'gem'|'great'|'best'|'good'|null` on both backend and frontend.
- Best = played move identity-equals stored best_move (out of book, not gem/great); Good = sub-INACCURACY_DROP mover-POV drop (out of book, not best/gem/great); precedence gem>great>best>good>flaws holds.
- Both surfaces render the new green glyphs with the correct scoping (board = both players, card = user-only).
- No DB/schema/engine/backfill changes; no eval-chart markers, move-list labels, count badges, cycling, or filters for best/good.
- All backend + frontend gates pass (pytest, ty, ruff, tsc, lint, knip, npm test).
</success_criteria>

<output>
Create `.planning/quick/260717-rbn-add-best-good-move-tiers-to-analysis-boa/260717-rbn-SUMMARY.md` when done.
</output>
