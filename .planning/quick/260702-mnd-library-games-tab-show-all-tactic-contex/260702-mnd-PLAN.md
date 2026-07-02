---
phase: quick-260702-mnd
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - app/services/library_service.py
  - app/routers/library.py
  - tests/services/test_library_service.py
  - frontend/src/components/results/LibraryGameCard.tsx
  - frontend/src/components/library/TacticMotifGroup.tsx
  - frontend/src/components/library/TacticMotifChip.tsx
  - frontend/src/components/results/__tests__/LibraryGameCard.test.tsx
  - frontend/src/api/client.ts
  - frontend/src/hooks/useLibrary.ts
  - frontend/src/hooks/__tests__/useLibraryGame.test.tsx
autonomous: true
requirements: []
must_haves:
  truths:
    - "Every analyzed Library Games card shows ALL its tactic motif chips regardless of the active tactic/severity filter"
    - "Every analyzed card shows ALL its context flaw-tag chips (already the case) — behaviour now consistent with tactic chips"
    - "Tactic/severity/context/depth/orientation filters still SELECT which games appear (query_filtered_games WHERE clause unchanged)"
    - "A tactic chip's active-filter ring lights only when the chip's markers actually match the active filter on ALL axes (family + orientation + depth)"
    - "The eval-chart white marker outline (outlinedPlies) still highlights the plies matching the active context/phase filter"
  artifacts:
    - path: "app/services/library_service.py"
      provides: "_build_card that builds tactic_by_ply with validity-only gating (decided_lost + confidence), no filter/severity pruning"
    - path: "frontend/src/components/results/LibraryGameCard.tsx"
      provides: "tactic chip derivations independent of outlinedPlies; depth-aware per-chip filter-ring flag"
    - path: "frontend/src/components/library/TacticMotifChip.tsx"
      provides: "optional filterRingActive prop overriding the store-derived ring on the Games card"
  key_links:
    - from: "app/services/library_service.py"
      to: "app/repositories/library_repository.py"
      via: "query_filtered_games (game selection) stays filtered; _build_card (card content) stops pruning"
      pattern: "query_filtered_games"
    - from: "frontend/src/components/results/LibraryGameCard.tsx"
      to: "frontend/src/lib/tacticComparisonMeta.ts"
      via: "resolveVisibleTactic(orientation, motif, depth, flawFilter) to compute the precise per-chip filter match"
      pattern: "resolveVisibleTactic"
---

<objective>
Decouple "filter selects which games appear" from "filter prunes which tags show on the card" for the Library Games tab. Today the tactic filter params (family/orientation/depth) and the severity filter both drive game selection AND null/hide non-matching tactic tags on each card. The user wants the filters to only SELECT games, while every selected card shows its full set of tactic + context flaw tags, keeping the active-filter ring so users can still see (and click through to) the matching tags.

Purpose: A selected card should be a complete picture of that game's flaws, not a filtered subset — consistent across tactic AND context tags (explicit user decision). The tactic tagger only fires on a fraction of blunders/mistakes (especially post the Multi-PV forcing-line gate), so full-tag cards stay readable.
Output: Backend stops pruning tactic tags in the card builder; the single-game endpoint sheds its now-dead pruning params; the frontend card renders all tactic chips and makes the filter ring depth-accurate.
</objective>

<execution_context>
@$HOME/.claude/gsd-core/workflows/execute-plan.md
</execution_context>

<context>
@CLAUDE.md
@app/services/library_service.py
@app/repositories/library_repository.py
@app/routers/library.py
@frontend/src/components/results/LibraryGameCard.tsx
@frontend/src/components/library/TacticMotifChip.tsx
@frontend/src/components/library/TacticMotifGroup.tsx
@frontend/src/lib/tacticComparisonMeta.ts
@frontend/src/hooks/useLibrary.ts
</context>

<decisions>
These judgment calls were resolved during planning. If any is wrong, flag before executing.

- **D-1 (severity filter also stops pruning tactic tags).** The task explicitly enumerates only the tactic filter params (family/orientation/depth). However, `_build_card` ALSO gates the per-ply tactic map by the severity filter (`severity_ints`, the "severity tactic-leak" fix). Meanwhile CONTEXT chips (`game.chips` from `_curate_chips_from_rows`) already ignore every filter and show all severities. Keeping severity gating on tactic-only would leave the card internally inconsistent (context shows mistake-severity tags, tactic hides them under "blunders only") — contradicting the user's explicit "consistency across tactic AND context tags" requirement. DECISION: remove the severity gate from the tactic map too. The two backend severity-suppression tests flip. Game selection by severity (`query_filtered_games`) is untouched.

- **D-2 (depth-aware filter ring — the preferred option in the task).** Once all tactic chips render, same-family chips that fail the depth filter must NOT light the active-filter ring ("highlighted === actually matches the active filter"). This is achievable cleanly because the frontend already has `resolveVisibleTactic(orientation, motif, depth, flawFilter)` (in tacticComparisonMeta.ts) which mirrors the backend `tactic_slot_visible` across ALL axes (family + orientation + the +1 decision-anchored depth range). We take the PREFERRED option, not the family/orientation-only fallback.

- **D-3 (remove now-dead single-game pruning params — consequent cleanup).** `get_library_game` (the "View game"/analysis-board single-game path) does no game selection, so its `flaw_severity`/`tactic_*`/`*_tactic_depth` params existed ONLY to drive the pruning we are removing. They are dead after D-1/D-2. The sole production caller (`Analysis.tsx`) already passes no filter, so the frontend forwarding (`getGame` params, `useLibraryGame(flawFilter)`) is already effectively dead. Remove it end-to-end rather than leave confusing dead query params. `get_library_games` KEEPS its params (they feed `query_filtered_games` selection).
</decisions>

<tasks>

<task type="auto">
  <name>Task 1: Backend — stop pruning tactic tags in _build_card; shed dead single-game params; flip tests</name>
  <files>app/services/library_service.py, app/routers/library.py, tests/services/test_library_service.py</files>
  <action>
In app/services/library_service.py `_build_card` (currently around lines 363-565): remove the five pruning parameters `flaw_severity`, `tactic_families`, `tactic_orientation`, `min_tactic_depth`, `max_tactic_depth` from the signature. In the `tactic_by_ply` construction loop (around lines 445-522): delete the `severity_ints` computation and the `if severity_ints is not None and fr.severity not in severity_ints: continue` guard (D-1), and change BOTH `tactic_slot_visible(...)` calls (the allowed slot ~474 and the missed slot ~494) to pass filter-neutral arguments — `tactic_families=()`, `tactic_orientation="either"`, `min_tactic_depth=None`, `max_tactic_depth=None` — while keeping the `decided_lost=fr_decided_lost` argument and the raw motif/confidence/depth arguments. This preserves the two legitimate validity gates (decided-lost suppression and the confidence floor) while dropping every filter-based prune. Do NOT modify `tactic_slot_visible` itself or `query_flaws` / `_query_flaws` — the Flaws subtab keeps per-slot filtering (each Flaws row IS a matching flaw). Rewrite the `_build_card` docstring paragraphs that describe the "Quick 260621-sm8" per-slot nulling and the "severity tactic leak" gate to state that the card now surfaces every valid tactic slot regardless of the active filter, and add a one-line note that game SELECTION is enforced upstream in `query_filtered_games`.

In `get_library_games` (~643): KEEP its filter/severity params (they feed `query_filtered_games`) but stop forwarding `flaw_severity=`, `tactic_families=`, `tactic_orientation=`, `min_tactic_depth=`, `max_tactic_depth=` into the `_build_card(...)` call (~736). Keep `tactic_flaw_rows=`.

In `get_library_game` (~568): remove the now-dead `flaw_severity`, `tactic_families`, `tactic_orientation`, `min_tactic_depth`, `max_tactic_depth` params (D-3), update the docstring to drop the filter-threading paragraphs, and call `_build_card(...)` without them (keep `tactic_flaw_rows=`).

In app/routers/library.py `get_library_game` (~131-171): remove the `severity`, `tactic_family`, `tactic_orientation`, `min_tactic_depth`, `max_tactic_depth` Query params and stop passing them to `library_service.get_library_game`; trim the docstring paragraphs about filter/severity threading. Remove any now-unused imports (e.g. SeverityFilter/TacticOrientationFilter) ONLY if they are unused elsewhere in the file — grep first.

In tests/services/test_library_service.py `TestBuildCardTacticPerSlotSuppression`: (1) FLIP `test_single_game_depth_filter_nulls_out_of_range_slot` — remove the removed depth args from the `get_library_game` call and assert the allowed slot is now POPULATED (`discovered-attack`) regardless of the former depth filter; rename to reflect "shows all slots". (2) FLIP `test_severity_filter_gates_tactic_slots_in_games_response` — assert BOTH the blunder-ply and mistake-ply tactics are populated under every `flaw_severity` value (the game is still selected; nothing is pruned); rename accordingly. (3) FLIP `test_single_game_severity_filter_gates_tactic_slots` — remove the `flaw_severity=` arg and assert both plies' tactics survive. (4) KEEP `test_default_filter_both_slots_populated_in_games_response` and `test_single_game_default_filter_unaffected` as regression guards. (5) LEAVE `test_orientation_filter_nulls_excluded_slot_in_flaw_markers` unchanged — it exercises `query_flaws` (the Flaws subtab), which still prunes; add a short comment noting it validates the Flaws path, not the Games card. (6) ADD one positive lock-in test: call `get_library_games` with an active `tactic_families`/depth filter that would previously have nulled a slot, and assert the card's `flaw_markers` still carry every seeded motif (both slots) — proving selection-only semantics.
  </action>
  <verify>
    <automated>uv run pytest tests/services/test_library_service.py tests/test_library_router.py -q && uv run ruff check app/ tests/ && uv run ty check app/ tests/</automated>
  </verify>
  <done>_build_card no longer accepts or applies any filter/severity pruning for the tactic map; get_library_games still selects via query_filtered_games; get_library_game and its router shed the dead params; backend tests assert full-tag cards; ruff + ty clean.</done>
</task>

<task type="auto">
  <name>Task 2: Frontend — render all tactic chips; make the filter ring depth-accurate (desktop + mobile)</name>
  <files>frontend/src/components/results/LibraryGameCard.tsx, frontend/src/components/library/TacticMotifGroup.tsx, frontend/src/components/library/TacticMotifChip.tsx, frontend/src/components/results/__tests__/LibraryGameCard.test.tsx</files>
  <action>
In frontend/src/components/results/LibraryGameCard.tsx, stop using `outlinedPlies` to gate tactic chips (it currently serves double duty). Keep the `outlinedPlies` memo and keep passing it to `<EvalChart outlinedPlies={...}>` (both the mobile ~998 and desktop ~1075 instances) — its eval-chart white-outline role is unchanged. Remove its GATING role from the three tactic derivations: in `motifPlies` (~380) drop the `if (outlinedPlies && !outlinedPlies.has(fm.ply)) continue;` line and remove `outlinedPlies` from that memo's dep array; in `tacticMotifs` (~468) change `passesContext` to gate on `fm.is_user` only (drop the `outlinedPlies` term) and remove it from the dep array; in `highlightedPlies` (~430) drop the `(!outlinedPlies || outlinedPlies.has(fm.ply))` term from the motif branch so hovering/cycling a tactic chip highlights all of its plies, and remove `outlinedPlies` from that dep array. Do NOT touch context-chip rendering (`contextChips` / `game.chips` / `tagCounts` / `tagPlies`) — context chips already render every tag unconditionally, which is now the target behaviour for tactic chips too. Update the block comments on these memos to say the card shows all tactic chips and selection is filter-driven server-side.

Add depth-aware ring support (D-2). The store hook is already read as `const [flawFilter] = useFlawFilterStore()` (~349); use the full `flawFilter` (tacticFamilies, tacticOrientation, tacticDepthMin, tacticDepthMax). Compute a `tacticFilterActive` boolean (true when any tactic axis is non-default — families non-empty, orientation !== 'either', or the depth range differs from DEFAULT_TACTIC_DEPTH_VALUE). Add a memo producing a Set of chip keys that fully match the active filter: for each `fm` where `fm.is_user`, for each orientation slot with a raw motif, call `resolveVisibleTactic(orientation, rawMotif, depth, flawFilter)` (import from '@/lib/tacticComparisonMeta') and, when it returns non-null, add `motifPliesKey(orientation, tacticMotifLabel(rawMotif))` to the set. In `renderChipsBlock` (~855), for each motif passed to `<TacticMotifGroup>`, compute `filterRingActive = tacticFilterActive && matchKeys.has(motifPliesKey(orientation, motif))` and include it on the motif item. Because `renderChipsBlock()` is the single shared source for BOTH mobile (~921) and desktop (~1119) bodies, this satisfies the desktop+mobile parity rule in one place — verify no other duplicated tactic-chip markup exists.

In frontend/src/components/library/TacticMotifGroup.tsx, extend the `motifs` prop item type to `{ motif: string; count: number; filterRingActive?: boolean }` and forward `filterRingActive` to `<TacticMotifChip>`.

In frontend/src/components/library/TacticMotifChip.tsx, add an optional `filterRingActive?: boolean` prop. Compute `const ringActive = filterRingActive ?? isActive;` (where `isActive` is the existing store-derived family+orientation match, kept for FlawCard which passes no prop) and use `ringActive` in place of `isActive` for both the `ACTIVE_FILTER_RING_CLASS` className (~198) and the `--tw-ring-color` style (~207). This keeps FlawCard's store-driven ring intact while giving the Games card the precise all-axes (incl. depth) match. Add data-testid coverage is unchanged (chips already have testids).

Update frontend/src/components/results/__tests__/LibraryGameCard.test.tsx: adjust/replace any assertions that expected tactic chips to be hidden/pruned under an active context or tactic filter — they must now assert all tactic chips render. Add a test that with an active tactic-depth (or family) filter, a same-family chip whose plies fall OUTSIDE the depth range renders WITHOUT the active-filter ring while an in-range chip renders WITH it (assert on the ring class / ring presence via the chip testid).
  </action>
  <verify>
    <automated>cd frontend && npx tsc -b && npm run lint && npm test -- --run src/components/results/__tests__/LibraryGameCard.test.tsx</automated>
  </verify>
  <done>All tactic chips render on every analyzed card regardless of filter; outlinedPlies drives only the eval-chart outline; the filter ring reflects the full active filter (family+orientation+depth); mobile and desktop share the change via renderChipsBlock; tsc/lint/tests pass.</done>
</task>

<task type="auto">
  <name>Task 3: Frontend — remove dead single-game filter forwarding; run full pre-merge gate</name>
  <files>frontend/src/api/client.ts, frontend/src/hooks/useLibrary.ts, frontend/src/hooks/__tests__/useLibraryGame.test.tsx</files>
  <action>
In frontend/src/api/client.ts `getGame` (~382-404): remove the `params` argument entirely (severity/tactic_family/tactic_orientation/min_tactic_depth/max_tactic_depth) since the backend endpoint no longer accepts them (Task 1). Simplify to a plain `GET /library/games/${gameId}` with no query params. Update the adjacent comment (~374) that describes forwarding the active tactic filter.

In frontend/src/hooks/useLibrary.ts `useLibraryGame` (~193-218): remove the `flawFilter` parameter and the derived `severity`/`tacticFamily`/`tacticOrientation`/`depthParam` locals, simplify the queryKey to `['library-game', gameId]`, and call `libraryApi.getGame(gameId!)` with no params. Update the docstring to note the single-game card is now filter-independent (content no longer changes with the flaw filter). Verify the sole caller Analysis.tsx (~217, already `useLibraryGame(isGameMode ? gameId : null)`) still type-checks; adjust any other callers surfaced by tsc.

Update frontend/src/hooks/__tests__/useLibraryGame.test.tsx: drop any assertions about forwarded filter query params; assert the hook fetches the bare single-game endpoint. Remove now-unused imports.

Then run the full CLAUDE.md pre-merge gate across the whole change (backend + frontend), including `npm run knip` to catch any dead exports left by the param removal.
  </action>
  <verify>
    <automated>cd frontend && npx tsc -b && npm run lint && npm run knip && npm test -- --run</automated>
  </verify>
  <done>getGame and useLibraryGame no longer forward filter params; queryKey simplified; hook test updated; knip clean; frontend tsc/lint/tests pass.</done>
</task>

</tasks>

<verification>
Full pre-merge gate (CLAUDE.md), run before integrating:
- `uv run ruff format app/ tests/`
- `uv run ruff check app/ tests/ --fix`
- `uv run ty check app/ tests/`  (zero errors)
- `uv run pytest -n auto -x`
- `( cd frontend && npx tsc -b && npm run lint && npm run knip && npm test -- --run )`

Manual (HUMAN-UAT, optional against existing dev DB): on the Library Games tab, apply a tactic-family + depth filter; confirm the returned cards still show ALL tactic + context chips, with only the truly-matching chips ringed, and the eval-chart white outline still marks the matching plies.
</verification>

<success_criteria>
- Applying any tactic/severity/context/depth/orientation filter on the Games tab changes WHICH games appear but never removes tags from a shown card.
- Tactic and context chips are consistent: both show the game's full set on every selected card.
- The active-filter ring lights only on chips that truly match the active filter across family + orientation + depth.
- The eval-chart white marker outline (context/phase matches) is unchanged.
- No dead filter params remain on the single-game endpoint / client / hook.
- Full pre-merge gate passes (ruff, ty, pytest, tsc -b, lint, knip, frontend tests).
</success_criteria>

<output>
Quick task — no SUMMARY required. Append a terse user-facing bullet under `## [Unreleased]` in CHANGELOG.md (### Changed) noting that Library Games cards now show all tactic + context tags with filters acting on game selection only.
</output>
