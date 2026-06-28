# Phase 139: Tactic Mode Overlay + Phase 135 Subsume - Context

**Gathered:** 2026-06-26
**Status:** Ready for planning

<domain>
## Phase Boundary

Make tactic mode on the `/analysis` board reach Phase 135 `TacticLineExplorer` parity, repoint
the "Explore" entry points to the route, then retire the standalone modal + hook. Deliverables:

- `src/components/analysis/TacticModeOverlay.tsx` — NEW conditional tactic chrome on `Analysis.tsx`
  (rendered when `isTacticMode`, i.e. `game_id` + `flaw_ply` present): motif chip(s), missed/allowed
  toggle, depth-to-punchline counter, eval badge, flaw-severity glyph on the allowed lead-in. Arrow
  helpers (`buildRootArrows` / `buildPvArrow`) port unchanged from `TacticLineExplorer`.
- `Analysis.tsx` tactic-mode wiring — call the existing `useTacticLines(gameId, flawPly)` query, seed
  the board via `useAnalysisBoard.loadMainLine(moves, position_fen)` (D-5), switch the seeded line on
  the missed/allowed toggle, and drive arrows off `isOnMainLine`.
- **Entry-point repoint** — `FlawCard` and `LibraryGameCard` "Explore" buttons change from opening a
  modal to `navigate('/analysis?game_id=…&flaw_ply=…&orientation=…')`. Plain URL params only — **no
  `location.state`** (rail dropped; return-to-game uses browser Back — see D-01/D-04).
- **Game-review-ply "Analyze position" entry** (folded in from Phase 138 D-03) — a button on the
  scrubbed ply in `LibraryGameCard` → `/analysis?fen=<reconstructed ply FEN>` (free-play, cheap; D-02).
- **Deletion gate** — after the 4 regression behaviors verify against the new overlay, delete
  `TacticLineExplorer.tsx` + `useTacticLine.ts`; `npm run knip` passes clean (TACTIC-03 / SC#4).

**Out of scope:** any backend work (D-4 locked — reuse the Phase 135 `tactic-lines` endpoint
unchanged); the cross-flaw next/prev-tactic rail (DROPPED — see D-01, a scope amendment vs SC#2);
URL write-back / live-variation serialization (D-01 carried, v2); the rich `?game_id=&ply=` game-review
reader (cheap `?fen=` chosen instead — D-02); paste-a-FEN box (BOARD-V2-01, v2); detector/motif changes
(frozen at 134).
</domain>

<decisions>
## Implementation Decisions

### Tactic-rail scope (discussed)
- **D-01:** **No cross-flaw next/prev-tactic rail.** Opening Explore passes a SINGLE flaw's data —
  its missed PV and/or allowed PV, both already returned by the existing `tactic-lines` response for
  one `game_id`+`flaw_ply`. The only in-tactic navigation is the **missed/allowed toggle** within that
  one flaw. There is no list of other flaws to walk and **no `location.state`** carried.
  - **SCOPE AMENDMENT (flag at milestone close):** ROADMAP Phase 139 SC#2, REQUIREMENTS TACTIC-02, and
    `.planning/research/*` all name a "next/prev-tactic rail" as required. The user descoped it. The
    SC#3 regression item "tactic-rail state on route re-entry" is therefore **reinterpreted** as:
    correct board re-seed + orientation/depth reset when the opened flaw or orientation changes (no
    multi-flaw rail to persist). Record this; do NOT silently edit ROADMAP/REQUIREMENTS.

### Game-review-ply entry point (discussed; folded from Phase 138 D-03)
- **D-02:** **Cheap `?fen=` entry now.** An "Analyze position" button on the scrubbed game ply
  (`LibraryGameCard` already reconstructs a per-ply FEN client-side) navigates to
  `/analysis?fen=<that FEN>` — free-play mode, **no tactic chrome, no game-move numbering carried**.
  Reuses the existing v1 `fen` reader (no new param/plumbing, no backend). Place it by the eval-chart /
  ply-nav the user already interacts with; **apply to desktop + mobile** (CLAUDE.md parity rule). This
  satisfies ROUTE-02's game-review clause (previously deferred from 138).

### Engine ↔ stored-PV arrows in tactic mode (discussed)
- **D-03:** **Board-arrow source toggle, stored-PV default while on-line.**
  - While ON the stored line: default to the **Phase 135 stored-PV arrows** (best-move blue + flaw red
    + depth countdown badge) for 135 visual parity. A **board-arrow toggle** ("Stored PV" ⇄ "Engine")
    lets the user switch the on-board arrows to the **live Stockfish** best-move arrow(s) on demand
    (e.g. to see the engine's view / second-best of the stored position). Never draw stored-PV AND
    engine arrows simultaneously (avoids two competing blue arrows / lesson confusion).
  - **The toggle governs ONLY the board arrows.** The `EvalBar` and `EngineLines` side panel stay
    **live throughout** (they're side-panel readouts, not board clutter) — the user always sees live
    eval + top lines regardless of the arrow toggle.
  - OFF the stored line (user deviated): there is no stored PV, so **live engine arrows only**; the
    toggle is hidden/disabled. (Engine analyzes every position from page mount — D-06 of Phase 138.)

### Return-to-Game UX (discussed)
- **D-04:** **Accept browser Back.** Explore navigates to the full `/analysis` route; the user returns
  to the originating library/game view via the browser/in-app Back button (React Router preserves the
  prior route). **No "return to game" plumbing, no `location.state`, no modal stacking** — the deep
  nested-Dialog focus/scroll-restore complexity from Phase 135 (D-01/D-05) is retired with the modal.
  Matches the milestone model: analysis is a destination, not a modal (Phase 138 D-05, no nav item).

### Claude's Discretion
- **`TacticModeOverlay` layout** — how the motif chip row / toggle / depth counter / eval badge compose
  into the `Analysis.tsx` shell (desktop side panel vs mobile stacked). Reuse `TacticMotifChip`,
  `HorizontalMoveList`, `moveNumberLabel`, `formatFlawEval`/`mateAtPly`, `isBlackToMove` unchanged.
- **Board-arrow toggle UI** — exact control (segmented toggle / button), label copy, `data-testid`,
  placement, and default-on-mount state (lean: "Stored PV" selected by default on-line). Hidden when
  off-line. `text-sm` floor, theme tokens, `data-testid` on interactive elements.
- **"Analyze position" (game-review) button** — exact placement/label/icon/`Button` variant
  (`brand-outline` secondary per CLAUDE.md unless it reads as the primary CTA there); mobile+desktop.
- **Default board orientation** in tactic mode — reuse the Phase 135 flaw-maker-perspective rule
  (`isBlackToMove` → flip), preserve manual flips per opened flaw.
- **Regression-test placement** — write the 4 regression checks against `TacticLineExplorer`/the new
  overlay BEFORE deleting anything (PITFALLS Pitfall 9 prevention).
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### v1.29 milestone research (primary spec for this phase)
- `.planning/research/ARCHITECTURE.md` — § Pattern 4 (Tactic Mode as a Conditional Overlay: seeding,
  live-engine handoff, arrow strategy, Phase 135 parity list), § "Tactic mode entry flow" + "Tactic-mode
  deviation flow", § Pattern 5 (read-only URL params; tactic params `game_id`/`flaw_ply`/`orientation`
  + plain `fen`), § Component Responsibilities (`TacticModeOverlay` props, `useAnalysisBoard` contract),
  and the Phase 4 build-sequence section (lines ~542–547). NOTE: this research assumes a next/prev-tactic
  rail — **superseded by D-01** (rail dropped).
- `.planning/research/PITFALLS.md` — Pitfall 9 (subsume-without-regression: the 4 behaviors), engine/worker
  lifecycle on the tactic-seeded page.
- `.planning/research/SUMMARY.md` — Phase 4 / Phase 139 section + regression gate (also assumes the rail —
  superseded by D-01).

### Requirements & roadmap
- `.planning/REQUIREMENTS.md` — TACTIC-01, TACTIC-02 (rail clause superseded by D-01), TACTIC-03,
  ROUTE-02 (game-review clause satisfied by D-02).
- `.planning/ROADMAP.md` § "Phase 139" — 4 success criteria. SC#2 names a rail (superseded by D-01);
  SC#3's "tactic-rail state on route re-entry" reinterpreted per D-01.

### Phase 135 parity source (the behavior bar to replicate — read before porting)
- `frontend/src/components/library/TacticLineExplorer.tsx` — the modal being subsumed: `buildRootArrows`
  / `buildPvArrow`, orientation toggle, eval badge, flaw-severity glyph, depth labels, move-list
  decorations. Port the arrow + display logic into `TacticModeOverlay` unchanged.
- `frontend/src/hooks/useTacticLine.ts` — the PV stepper being retired (its behavior is now
  `useAnalysisBoard` + `loadMainLine` seeding).
- `.planning/milestones/v1.28-phases/135-tactic-line-explorer-walkable-pv-stepper-for-tagged-flaws-se/135-CONTEXT.md`
  — the locked Phase 135 design (depth mechanic, missed/allowed semantics, real-game-ply numbering).
- `frontend/src/lib/tacticDepth.ts` — `toDisplayDepthForOrientation`, `ALLOWED_DECISION_DEPTH_OFFSET`,
  `DEPTH_DISPLAY_OFFSET` (MUST reuse, do not recompute).
- `frontend/src/lib/tacticComparisonMeta.ts` — `resolveVisibleTactic` (live flaw-filter gate on depth
  labels; same usage as the modal).

### Prior-phase context (the pieces this phase composes)
- `.planning/phases/138-analysis-route-page-shell-entry-points/138-CONTEXT.md` — page shell, param
  parsing (`game_id`/`flaw_ply`/`orientation` already parsed in `Analysis.tsx`), engine-on-by-default
  (D-06), read-only URL (D-01), and the game-review-ply fold-in note (D-03).
- `.planning/phases/137-useanalysisboard-hook-analysis-display-components/137-CONTEXT.md` —
  `useAnalysisBoard` return contract (`loadMainLine`, `isOnMainLine`, `mainLine`, `rootFen`,
  `lastMove`, navigation) + EvalBar/EngineLines/VariationTree props.

### Prior-art in the codebase (entry points to repoint)
- `frontend/src/components/library/FlawCard.tsx` — `exploreOpen` state + Explore button (~line 240–260);
  repoint to `navigate('/analysis?...')`, drop the embedded `<TacticLineExplorer>`.
- `frontend/src/components/results/LibraryGameCard.tsx` — Explore button (desktop ~894, mobile ~990) +
  the per-ply FEN reconstruction (host for the D-02 "Analyze position" button); repoint Explore,
  drop the embedded `<TacticLineExplorer>`.
- `frontend/src/pages/Analysis.tsx` — tactic-param reader (already present); add the overlay + seeding.
- `frontend/src/hooks/useLibrary.ts` — `useTacticLines(gameId, ply, enabled)` query (reused unchanged,
  now called from `Analysis.tsx` instead of the modal).
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `useAnalysisBoard` (137): `loadMainLine(sans, rootFen)` seeds the stored PV as `mainLine`;
  `isOnMainLine(nodeId)` distinguishes stored PV from user variations (the arrow-mode switch in D-03).
- `useTacticLines` (135, `useLibrary.ts`): lazy TanStack Query returning both missed/allowed PVs +
  depths + motifs + tactic-move indices + evals for one flaw. Query key `['tactic-lines', gameId, ply]`,
  unchanged. The ONLY data source needed for tactic mode (D-01 — no flaw-list query).
- Port directly from `TacticLineExplorer`: `buildRootArrows`, `buildPvArrow`, `isBlackToMove`,
  `TacticMotifChip`, `HorizontalMoveList` + `moveLabel`/`moveNumberLabel`, `formatFlawEval`/`mateAtPly`,
  `resolveVisibleTactic`, severity glyphs, theme arrow/label tokens (`BEST_MOVE_ARROW`, `PAYOFF_MOVE_ARROW`,
  `TAC_MISSED`/`TAC_ALLOWED` + label colors).
- `LibraryGameCard` already reconstructs a per-ply `{fen}` for its scrub viewer — the D-02 "Analyze
  position" button just URL-encodes that FEN.

### Established Patterns
- Tactic mode = a mode flag on `Analysis.tsx` (`isTacticMode = gameId != null && flawPly != null`), not
  a separate component tree (ARCHITECTURE Pattern 4).
- `/analysis` does NOT unmount on search-param change (same route) — orientation toggle / arrow-mode
  state lives in component state and survives param updates.
- Entry-point navigation: `useNavigate()` → `navigate('/analysis?...')`. CLAUDE.md: secondary buttons =
  `variant="brand-outline"`; mobile+desktop parity for any entry button; `data-testid` on interactive
  elements; `text-sm` floor; theme constants in `theme.ts`; run `tsc -b` before integrating shared-type
  / prop changes; `npm run knip` must pass after deletion.

### Integration Points
- `Analysis.tsx` gains: `useTacticLines` call, `loadMainLine` seeding effect (re-seed on orientation
  change), `TacticModeOverlay` render, arrow-source state + board-arrow selection (D-03).
- `FlawCard` / `LibraryGameCard`: Explore button onClick → `navigate(...)`; remove `<TacticLineExplorer>`
  + its open state. `LibraryGameCard` also gains the D-02 "Analyze position" button.
- Deletion: `TacticLineExplorer.tsx`, `useTacticLine.ts` (+ their `__tests__`) removed once the 4
  regression behaviors verify against the overlay; knip then confirms no dead exports.
</code_context>

<specifics>
## Specific Ideas

- The arrow-source toggle ("Stored PV" ⇄ "Engine") is the user's idea to satisfy curiosity about the
  engine's view (e.g. second-best move) of the stored position without cluttering the board with two
  arrow sets. Default to Stored PV on-line; engine-only off-line.
- Lesson feel preserved: stored-PV arrows + depth countdown are the default while walking the line;
  live eval/lines are always visible alongside.
</specifics>

<deferred>
## Deferred Ideas

- **Cross-flaw next/prev-tactic rail** — DROPPED for v1 per D-01 (user descope). If revisited, the
  cleanest source is a `location.state` ordered list passed by the entry point (filtered flaws from
  FlawsTab / in-game flaws from the game card), seeded once into `Analysis.tsx` state, rail calls
  `setSearchParams`, hidden on direct-URL entry. Scope amendment vs ROADMAP SC#2 / TACTIC-02 — surface
  at milestone close.
- **Rich `?game_id=&ply=` game-review reader** — replays the game on the Analysis side for real
  game-move numbering; deferred in favor of the cheap `?fen=` entry (D-02). v2 if move numbering on
  game-review positions is wanted.
- **ROADMAP/REQUIREMENTS wording cleanup** — Phase 138's title + ROUTE-02 still say "game-review ply"
  (Phase 138 D-04); plus the rail descope (D-01) needs SC#2/TACTIC-02 amendment. Adjust at milestone
  close, not via unrequested edits now.
- **URL write-back / live-variation serialization, "copy position link", paste-a-FEN/PGN box** — v2
  (carried from Phase 137/138).

### Reviewed Todos (not folded)
None folded. All 10 `todo.match-phase` hits were keyword-noise unrelated to tactic mode (recovery
popover copy, Tailwind axis-label fix, benchmark rebuilds, prod backfills) — none touch the
tactic/analysis surfaces.
</deferred>

---

*Phase: 139-tactic-mode-overlay-phase-135-subsume*
*Context gathered: 2026-06-26*
