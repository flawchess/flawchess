# Phase 112: Flaws Subtab Card Rework - Context

**Gathered:** 2026-06-09
**Status:** Ready for planning

<domain>
## Phase Boundary

Rework the Library → **Flaws** subtab so each flawed position renders as a proper
`Card` matching the **Games**-subtab visual language, laid out as a responsive
**2-up grid**, with a **"View game"** action opening the full analyzed game card in
a modal.

**In scope:**
- Replace the current full-width `FlawRow` list with a new `FlawCard` in a
  responsive grid (1-up mobile → 2-up at `lg`).
- Banded `CardHeader` (player/opponent names + ratings + exact-ply platform link),
  132px miniboard with the flaw arrow, **standard move notation + eval swing on one
  line**, family-colored tag chips + the shared `Explanation` (`TagLegend`) tooltip,
  and game metadata (date · TC · termination + result).
- A **"View game"** button → a modal showing the full `LibraryGameCard` (eval chart,
  all flaws), fetched on open via a **new `GET /api/library/games/{game_id}`**.
- Backend: add `white_rating`/`black_rating` to `FlawListItem`; **drop**
  `es_before`/`es_after`/`move_san` from `game_flaws`; the flaw-list endpoint joins
  `game_positions` for eval (before+after) and the move SAN.

**Out of scope (deferred / other phases):**
- Modal auto-scrub/highlight to the specific flaw's ply (see Deferred Ideas).
- The Analysis detail viewer and best-move endpoint (SEED-036, separate later phase).
- Any change to flaw classification logic, tag taxonomy, or the cross-tab Flaw filter
  (locked by Phases 108/110).

</domain>

<decisions>
## Implementation Decisions

### Card grid & within-card layout
- **D-01 (grid):** Responsive grid `grid-cols-1 lg:grid-cols-2` — 1-up below 1024px,
  2-up at `lg`+. **Never 3-up** (the user originally floated "2 or 3" but chose 2-up;
  the 132px board + content column needs the width). Replaces the current
  `flex flex-col gap-3` single-column list in `FlawsTab`.
- **D-02 (within-card):** Board left (132px) + content stacked on the right:
  move (standard notation) + eval swing + severity badge → tag chips →
  `Explanation` (`TagLegend`) → metadata (date · TC · termination + result indicator).
  Mirrors the Games card's column-1 structure; the user's reference image confirmed
  the metadata set (date / TC / termination), with the **move replacing the opening line**.

### Header
- **D-03 (header):** `CardHeader` matching the Games card — desktop single line
  `■ White (rating) vs □ Black (rating)`, mobile two stacked lines — plus the platform
  link (see D-10). **Requires adding `white_rating`/`black_rating` to `FlawListItem`**
  (data already on the `games` row; the flaw-list query already joins `games`).

### Move notation & eval swing
- **D-04 (notation):** Flawed move in **standard notation** (`16...Nxd4`; white `N.`,
  black `N...`) via the shared `formatCandidateMove` helper (`lib/openingInsights.ts`).
  Replaces the current non-standard `Move 7: Nxd4`.
- **D-05 (eval swing — source):** Show the **before → after** eval pair using
  **`eval_cp`/`eval_mate` from `game_positions`** — **NOT** an ES→eval round-trip.
  Rationale: ES (expected score, 0–1) saturates near ±1, so a forced mate and a +9
  both map to ES≈0.99; raw eval preserves **mate-in-N** (e.g. `+4.7 → #-3`). This also
  makes `es_before`/`es_after` dead (see D-07).
- **D-06 (eval swing — format & POV):** Both endpoints rendered **user-POV** — stored
  eval is white-POV, so **negate `eval_cp`/`eval_mate` when `user_color === 'black'`**
  (a flaw always drops the user's own eval). Reuse a formatter **extracted from
  `EvalChart.formatEval`** (`components/library/EvalChart.tsx:304`): `eval_cp` → signed
  1-decimal pawns, `eval_mate` → mate-in-N. Do **not** reuse the ES→pawns `evalStr`
  inverse-sigmoid in `tagDefinitions.ts` (that's for threshold copy, where only ES is
  available).

### game_flaws schema slimming
- **D-07 (drop dead columns):** Drop **`es_before`, `es_after`, AND `move_san`** from
  `game_flaws`. All three are pure display payload with no logic readers (severity and
  tags are precomputed into their own columns). The classifier stops persisting them.
  - **Keep `fen`** — `game_positions` stores only Zobrist hashes, **no FEN column**
    (CLAUDE.md). The flaw's board-before FEN (`fen_map[n]`) can't be derived without a
    PGN replay, so `fen` is the one denormalized display column that stays.
  - Alter migration drops the 3 columns. **Dev-only** (v1.24 unshipped → no prod data);
    re-run `scripts/backfill_flaws.py` for dev users if needed.
- **D-08 (read via join):** The flaw-list endpoint joins `game_positions` to recover
  what was dropped. Authoritative mapping (`flaws_service.py::_build_flaw_record`):
  `game_flaws.ply = n`, `move_san = positions[n].move_san`, board-before `= fen_map[n]`.
  - `move_san` → `game_positions[(game_id, ply)].move_san` (rides on a row already
    joined for eval; zero extra joins).
  - **before/after eval offsets MUST be verified empirically** before dropping ES — see
    Pitfall 1.

### Modal ("View game")
- **D-09 (presentation):** **One responsive `Dialog`** (both viewports) — wide +
  centered on desktop (~`max-w-4xl`), near-fullscreen + internal scroll on mobile.
  Reuse `LibraryGameCard` verbatim as the body. Loading = spinner during the
  single-game fetch; error = shared `LoadError` (CLAUDE.md mandatory `isError`).
- **D-10 (backend):** New **`GET /api/library/games/{game_id}`** → one `GameFlawCard`,
  reusing the existing list card-builder scoped to a single id. New
  `useLibraryGame(id)` hook fetches on modal open.
- **D-11 (trigger):** A **dedicated "View game" button only** (in the card body). Not
  whole-card-clickable, not board-click — the card has interactive chips/tooltips/links
  that would conflict, and a button is the cleanest a11y + browser-automation target.

### Platform link
- **D-12:** **Keep** the existing exact-ply external platform deep-link (`flawPlyUrl`)
  in the card header (mirrors the Games card header) **and** add the in-app "View game"
  button. Two distinct destinations: platform-at-the-move vs full-card modal.

### Claude's Discretion
- "View game" button label/icon and exact placement in the content stack.
- Spinner vs skeleton for the modal loading state; the `Dialog` `max-w-*` value.
- Exact metadata ordering within the content stack (date/TC/termination grouping).
- `data-testid`/ARIA naming (follow CLAUDE.md browser-automation conventions).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### This phase
- `.planning/ROADMAP.md` §"Phase 112: Flaws Subtab Card Rework" — goal, success
  criteria, backend prerequisites, and the explore-session decisions (D-01..D-03 there).

### Prior phase decisions (locked; do not re-derive)
- `.planning/phases/108-flaws-subtab-game-flaws-materialization-per-flaw-endpoint-cr/108-CONTEXT.md`
  — `game_flaws` schema/semantics, `GET /library/flaws` + `FlawListItem`, cross-tab
  Flaw filter, flaw pagination (size 20, shared `Pagination`).
- `.planning/phases/109-per-card-expected-score-eval-chart-games-subtab/109-CONTEXT.md`
  — `LibraryGameCard` 3-thirds structure, the inline `GameFlawCard` payload
  (`eval_series`/`flaw_markers`/`phase_transitions`/`moves`) served by `GET /library/games`,
  `EvalChart.formatEval` semantics, white-POV chart convention.
- `.planning/phases/110-flaw-tag-taxonomy-overhaul-rename-impact-family-rebuild-tool/110-CONTEXT.md`
  — finalized tag taxonomy + `TagChip`/`TagLegend` definition popovers.

### Seeds (note this phase AMENDS SEED-038)
- `.planning/seeds/SEED-038-flaw-filter-and-game-flaws-materialization.md` — original
  `game_flaws` denormalized-display schema. **This phase drops `es_before`/`es_after`/
  `move_san` from it** and reads them via `game_positions` join instead.
- `.planning/seeds/SEED-036-library-page-milestone.md` — Library milestone context;
  Analysis viewer + best-move endpoint deferred.
- `.planning/notes/flaw-tag-definitions.md` — tag definitions surfaced in the tooltip.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `frontend/src/pages/library/FlawsTab.tsx` — current tab; `FlawRow` (lines ~48-141)
  is **replaced** by the new `FlawCard`; the grid replaces the `flex-col gap-3` list.
- `frontend/src/components/results/LibraryGameCard.tsx` — the modal body (verbatim) AND
  the source pattern for the `CardHeader` (lines ~280-293), 132px `LazyMiniBoard`
  (`DESKTOP_BOARD_SIZE = 132`), and `TagLegend` usage.
- `frontend/src/components/library/TagChip.tsx` — `TagChip` + `TagLegend` (Explanation).
- `frontend/src/components/library/SeverityBadge.tsx`, `components/board/LazyMiniBoard`.
- `frontend/src/lib/openingInsights.ts::formatCandidateMove` — standard SAN notation.
- `frontend/src/components/library/EvalChart.tsx::formatEval` (line 304) — **extract** a
  bare `eval_cp`/`eval_mate` → string formatter (strip the `Eval: ` prefix) shared by the
  chart tooltip and the flaw card. `clockFormat.formatSignedEvalPawns` is the pawn formatter.
- `frontend/src/components/ui/dialog.tsx`, `drawer.tsx`, `load-error.tsx` — modal + states.
- `frontend/src/components/results/Pagination.tsx` — already used by FlawsTab.
- `frontend/src/hooks/useLibrary.ts` — `useLibraryFlaws` / `useLibraryGames`; add
  `useLibraryGame(id)`.

### Backend
- `app/routers/library.py` — `APIRouter(prefix="/library")`; add `GET /games/{game_id}`.
- `app/schemas/library.py` — `FlawListItem` (drop `es_before`/`es_after`/`move_san`; add
  `white_rating`/`black_rating` + before/after eval fields), `GameFlawCard`.
- `app/repositories/library_repository.py` — flaw-list builder (lines ~278-283): add the
  `game_positions` join for eval + move_san; drop ES reads.
- `app/services/library_service.py` — `GameFlawCard` builder to reuse for the single-game
  endpoint.
- `app/services/flaws_service.py::_build_flaw_record` — stop persisting `es_before`/
  `es_after`/`move_san`; authoritative ply/SAN mapping lives here.
- `app/models/game_flaw.py` — drop 3 columns (alter migration). `app/models/game_position.py`
  — join source (`eval_cp`/`eval_mate`/`move_san`; `(user_id, game_id, ply)` PK + indexes).
- `scripts/backfill_flaws.py` — dev rebuild after the schema change.

### Established Patterns
- Standalone `LibraryGameCard` (Phase 109 D-05) — do not fold flaw-card logic into it;
  the new `FlawCard` is a sibling component.
- Theme constants in `theme.ts`; `data-testid`/ARIA/semantic-HTML on all new interactive
  elements; `text-sm` floor (tooltip bodies may use `text-xs`); mobile parity.

### Integration Points
- New route `GET /api/library/games/{game_id}` + `useLibraryGame` hook.
- `FlawListItem` payload change (drop ES/SAN, add ratings + before/after eval).
- `game_flaws` alter migration (drop 3 columns); classifier write-path change.
- New `FlawCard` + grid + `Dialog` modal in `FlawsTab`.

</code_context>

<specifics>
## Specific Ideas

- Eval swing reads like the tag tooltip's "from +X to +Y" framing, but with real
  Stockfish eval (1-decimal pawns / mate-in-N), user-POV: e.g. `16...Nxd4  +4.7 → #-3`.
- User's reference image (Games card metadata block): `Caro-Kann Defense` / `Jun 6, 2026`
  / `Rapid · 10+5` / `⊖ Checkmate` — the flaw card reuses this block with the **move**
  in place of the opening line.

</specifics>

<deferred>
## Deferred Ideas

- **Modal auto-scrub to the flaw ply** — opening the modal from a specific flaw could
  scrub/highlight the `LibraryGameCard` eval chart to that ply. Needs a controlled-ply
  prop on the otherwise-standalone `LibraryGameCard` (it owns `hoverPly` internally).
  Default for this phase: **no auto-scrub** (modal opens at rest). Pull into a follow-up
  if desired.

None other — discussion stayed within phase scope.

</deferred>

<pitfalls>
## Implementation Pitfalls (MANDATORY for planner/researcher)

1. **Eval-join off-by-one (regression guard).** `_build_flaw_record` stores
   `ply = n` with `move_san = positions[n].move_san` and board-before `= fen_map[n]`,
   while `_run_all_moves_pass` derives ES from `positions[n-1]`/`positions[n]` under a
   *different* `n` meaning. Before dropping `es_before`/`es_after`, the planner MUST:
   add the `game_positions` eval join, convert the joined eval → ES (lichess sigmoid),
   and assert it reproduces the existing `es_before`/`es_after` on sample dev rows.
   Lock the offset empirically — do not guess.
2. **`LibraryGameCard` `overflowVisible` tooltip in a scroll container.** The card sets
   `overflowVisible` so its `EvalChart` tooltip can escape the card border. Inside a
   scrollable `Dialog` that tooltip may clip. Verify the modal renders the tooltip
   correctly (the tooltip portals, but the dialog's `overflow` may still interfere).
3. **Eval perspective + mate sign.** Stored `eval_cp`/`eval_mate` are white-POV; the
   flaw card is user-POV → negate both for `user_color === 'black'`. A blunder-into-mate
   yields `eval_mate < 0` user-POV (mate *against* the user) — format accordingly.
4. **`fen` cannot be dropped.** `game_positions` has no FEN (hashes only). Keep
   `game_flaws.fen`.

</pitfalls>

---

*Phase: 112-flaws-subtab-card-rework*
*Context gathered: 2026-06-09*
