---
phase: 112-flaws-subtab-card-rework
verified: 2026-06-09T18:30:00Z
status: passed
score: 8/8 must-haves verified; 5/5 human-UAT items user-verified during /gsd-ship
overrides_applied: 0
human_verification:
  - test: "Open the Library → Flaws subtab at ≥1024px viewport. Confirm flaws render as a 2-column card grid."
    expected: "Cards appear side-by-side in pairs; each card has a banded header, 132px miniboard with arrow, move+eval line, severity badge, tag chips, and metadata."
    why_human: "Grid layout, card visual language, and board rendering require browser inspection."
  - test: "Resize to <1024px (mobile). Confirm the grid collapses to a single column."
    expected: "Each FlawCard occupies the full width; no side-by-side cards below lg breakpoint."
    why_human: "Responsive breakpoint behavior requires a browser."
  - test: "Click 'View game' on any flaw card. Observe the modal."
    expected: "A Dialog opens showing a spinner briefly, then the full LibraryGameCard with the eval chart and analyzed positions. The modal is wide (max-w-4xl) and scrollable."
    why_human: "Modal open/close behavior, LibraryGameCard rendering inside Dialog, and eval-chart tooltip clipping (Pitfall 2) require live browser interaction."
  - test: "Click 'View game' for a flaw belonging to your account. Inspect the network request."
    expected: "GET /api/library/games/{game_id} returns 200 with a valid GameFlawCard JSON payload."
    why_human: "Live API call verification against production/dev backend."
  - test: "Confirm the platform deep-link on each flaw card opens the correct platform position."
    expected: "Clicking the ExternalLink icon opens lichess/chess.com at the exact half-move of the flaw."
    why_human: "External link navigation requires a browser."
---

# Phase 112: Flaws Subtab Card Rework — Verification Report

**Phase Goal:** Rework the Library → Flaws subtab so each flawed position renders as a proper `Card` matching the Games-subtab visual language — banded header with player/opponent names + ratings, a 132px miniboard with the flaw arrow, the move in standard notation alongside the eval swing, family-colored tag chips with a shared Explanation tooltip — laid out as a responsive 2-up card grid, with a "View game" action that opens the full analyzed game card in a modal.

**Verified:** 2026-06-09T18:30:00Z
**Status:** human_needed (all automated checks pass; 5 items require browser/live-API confirmation)
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Flaw results render as Cards in a responsive grid (`grid grid-cols-1 lg:grid-cols-2`), replacing the full-width single-column row list (old `FlawRow` deleted) | VERIFIED | `FlawsTab.tsx:307` — `<div className="grid grid-cols-1 lg:grid-cols-2 gap-4" data-testid="flaw-grid">`. `grep FlawRow FlawsTab.tsx` returns nothing. `MINI_BOARD_SIZE` also gone. |
| 2 | Each card has a banded CardHeader identical in content to the Games card: `■ White (rating) vs □ Black (rating)` + platform icon/link. `white_rating`/`black_rating` on `/library/flaws` payload + `FlawListItem` | VERIFIED | `FlawCard.tsx:148-160` — `CardHeader` with `■ {whiteName} {whiteRating}` / `□ {blackName} {blackRating}`. `FlawListItem` in `library.py:136-137` and `library.ts:198-200` carry `white_rating`/`black_rating`. `query_flaws` in `library_repository.py:313-314` sources them from `game.white_rating`/`game.black_rating`. |
| 3 | Miniboard renders at 132px desktop (was 80px) with the flawed-move arrow | VERIFIED | `FlawCard.tsx:28` — `const DESKTOP_BOARD_SIZE = 132`. `FlawCard.tsx:211-220` — `<LazyMiniBoard fen={flaw.fen} size={DESKTOP_BOARD_SIZE} arrows={[{from, to, color: SEV_BLUNDER}]} />`. Arrow sourced from `sanToSquares` at line 84-86. |
| 4 | Flawed move shown in standard notation (`16...Nxd4`; white `N.` / black `N...`) via shared move-notation logic — not "Move 7: Nxd4" — with the eval swing from raw `eval_cp`/`eval_mate` (user-POV, mate-aware) on the SAME line, plus the severity badge | VERIFIED | `openingInsights.ts:19-23` — `formatMoveNotation` exports `"N.san"` for even ply (white), `"N...san"` for odd ply (black). `FlawCard.tsx:89-91` uses it. `formatFlawEval.ts` handles user-POV negation (`applyUserPov`) and mate formatting (`#${evalMate}`). All rendered on same line at `FlawCard.tsx:225-229`. `SeverityBadge` at line 232. |
| 5 | Tag chips use family-colored TagChip + a single Explanation/TagLegend tooltip (matching the Games card), replacing per-chip popovers | VERIFIED | `FlawCard.tsx:237-244` — `<TagChip key={tag} tag={tag} gameId={flaw.game_id} definition={false} />` map + `<TagLegend tags={flaw.tags} gameId={flaw.game_id} />`. `TagLegend` exported from `TagChip.tsx:259`. |
| 6 | Within-card layout: miniboard column left + stacked content column right (move+swing+severity → tag chips → Explanation → metadata) | VERIFIED | `FlawCard.tsx:209` — `<div className="flex gap-3 items-start p-3">` wraps `LazyMiniBoard` (left) and `<div className="flex flex-col gap-1.5 ...">` content stack (right) in canonical order: move line (224-229), SeverityBadge (232), TagChip row (234-241), TagLegend (243-244), metadata (246-198), View-game button (250-261). |
| 7 | A "View game" action opens a modal showing the full analyzed game's `LibraryGameCard`, fetched on open via a NEW `GET /api/library/games/{game_id}` endpoint returning a single `GameFlawCard`, with strict IDOR guard (404 not 403 for non-owned games) | VERIFIED | Backend: `library.py:106-122` — `@router.get("/games/{game_id}", response_model=GameFlawCard)` raises `HTTPException(status_code=404, detail="Game not found")` when service returns `None`. `library_service.py:410-411` — IDOR guard `if game is None or game.user_id != user_id: return None`. Frontend: `FlawCard.tsx:266-281` — `Dialog` with `useLibraryGame(open ? flaw.game_id : null)`, all three states (isLoading spinner, isError LoadError, data LibraryGameCard). `client.ts:293-294` — `getGame` targeting `/library/games/${gameId}`. `useLibrary.ts:91-99` — `useLibraryGame` with `enabled: gameId !== null`. |
| 8 | Mobile + browser-automation parity: `data-testid` / ARIA / semantic HTML on all new interactive elements (card, view-game button, modal); grid collapses to 1-up on mobile | VERIFIED | `FlawCard.tsx:206` — `data-testid={flaw-card-${game_id}-${ply}}` on `<Card as="article">`. Line 255 — `data-testid={flaw-card-view-game-${game_id}-${ply}}` + `aria-label`. Line 269-270 — `data-testid="flaw-game-modal"` + `aria-label`. Line 134 — `data-testid={flaw-card-platform-link-...}` + `aria-label`. Line 131 — `rel="noopener noreferrer"`. Grid `grid-cols-1 lg:grid-cols-2` collapses at <1024px. Mobile header stacks at `FlawCard.tsx:154-157`. |

**Score: 8/8 truths verified**

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `app/schemas/library.py` | `FlawListItem` with `white_rating`/`black_rating` + before/after eval; no `es_before`/`es_after` | VERIFIED | Lines 131-137: all six `int | None` fields present; `es_before`/`es_after` absent; comment at line 116 confirms D-07 |
| `app/repositories/library_repository.py` | Two aliased `game_positions` outerjoins sourcing move_san + before/after eval | VERIFIED | Lines 243-261: `PositionAt = aliased(GamePosition, name="pos_at")`, `PositionBefore = aliased(GamePosition, name="pos_before")`, both outerjoin on `(game_id, user_id, ply)` |
| `app/models/game_flaw.py` | `es_before`/`es_after`/`move_san` removed; `fen` kept | VERIFIED | Model has no `es_before`, `es_after`, or `move_san` mapped columns; `fen` present at line 66 |
| `alembic/versions/20260609_drop_game_flaws_display_cols.py` | Drop-column migration (`revision=f8a2d1c9b345`, `down_revision=e1a7c93b6f02`) | VERIFIED | File exists; `upgrade()` calls `drop_column` for all three columns; `downgrade()` re-adds them nullable |
| `app/repositories/game_flaws_repository.py` | `flaw_record_to_row` does not write `es_before`/`es_after`/`move_san` | VERIFIED | Lines 100-116: dict contains only `user_id`, `game_id`, `ply`, `severity`, `tempo`, `phase`, `is_miss`, `is_lucky`, `is_reversed`, `is_squandered`, `fen`; comment at line 111 confirms D-07 |
| `app/services/library_service.py` | `get_library_game(session, user_id, game_id) -> GameFlawCard | None` with IDOR guard | VERIFIED | Lines 393-431: function exists with `session.get(Game, game_id)` then `game.user_id != user_id` guard; reuses `_build_card`; sequential awaits |
| `app/routers/library.py` | `GET /games/{game_id}` route, 404 on `None`, relative path | VERIFIED | Lines 106-122: `@router.get("/games/{game_id}", response_model=GameFlawCard)`, raises 404 with `"Game not found"`; no `/library` prefix in decorator |
| `frontend/src/lib/openingInsights.ts` | `formatMoveNotation(plyIndex, san)` exported; `formatCandidateMove` delegates to it | VERIFIED | Lines 19-23: `formatMoveNotation` exported. Line 43: `return formatMoveNotation(entrySanSequence.length, candidateMoveSan)` |
| `frontend/src/lib/formatFlawEval.ts` | `formatFlawEval(...)` with user-POV negation and mate formatting | VERIFIED | Full file: `applyUserPov` negates both cp/mate for black; `formatFlawEvalPart` uses `#${mate}` or `formatSignedEvalPawns(cp/100)` or `'—'`; exported `formatFlawEval` joins with ` → ` |
| `frontend/src/components/library/FlawCard.tsx` | Full card component with header, 132px board, move+swing, SeverityBadge, TagChip/TagLegend, metadata, View-game button + Dialog | VERIFIED | Complete component with all required elements; `DESKTOP_BOARD_SIZE=132`; all data-testid/ARIA present |
| `frontend/src/pages/library/FlawsTab.tsx` | Responsive FlawCard grid replacing FlawRow + flex-col list; FlawRow + MINI_BOARD_SIZE deleted | VERIFIED | Line 307: `grid grid-cols-1 lg:grid-cols-2 gap-4` with `data-testid="flaw-grid"`; `grep FlawRow` and `grep MINI_BOARD_SIZE` return nothing |
| `frontend/src/hooks/useLibrary.ts` | `useLibraryGame(gameId: number | null)` with `enabled: gameId !== null` | VERIFIED | Lines 91-99: hook exported with `enabled: gameId !== null`, `queryKey: ['library-game', gameId]`, `staleTime: LIBRARY_STALE_TIME` |
| `frontend/src/api/client.ts` | `libraryApi.getGame(gameId)` targeting `/library/games/${gameId}` | VERIFIED | Line 293-294: `getGame: (gameId: number) => apiClient.get<GameFlawCard>('/library/games/${gameId}').then(r => r.data)` inside `libraryApi` object |
| `frontend/src/types/library.ts` | `FlawListItem` with six new fields; no `es_before`/`es_after` | VERIFIED | Lines 195-200: all six fields (`eval_cp_before`, `eval_mate_before`, `eval_cp_after`, `eval_mate_after`, `white_rating`, `black_rating`); `es_before`/`es_after` absent from interface (only in comment at line 184) |
| `CHANGELOG.md` | `[Unreleased]` bullet for Phase 112 Flaws card rework | VERIFIED | Line 22: "Flaws subtab card rework (Phase 112) — ..." under `### Changed` |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `FlawsTab.tsx` | `FlawCard.tsx` | `grid map over flaws` | VERIFIED | `FlawsTab.tsx:309` — `<FlawCard key={...} flaw={flaw} />` inside the `flaw-grid` div |
| `FlawCard.tsx` | `useLibraryGame` | `open ? flaw.game_id : null` | VERIFIED | `FlawCard.tsx:76` — `const { data, isLoading, isError } = useLibraryGame(open ? flaw.game_id : null)` |
| `useLibraryGame` | `GET /api/library/games/{game_id}` | `libraryApi.getGame` | VERIFIED | `useLibrary.ts:94` — `queryFn: () => libraryApi.getGame(gameId!)` |
| `library.py::get_library_game` | `library_service.get_library_game` | `user_id=user.id` from `current_active_user` | VERIFIED | `library.py:119` — `card = await library_service.get_library_game(session, user_id=user.id, game_id=game_id)` |
| `library_service.get_library_game` | `_build_card` | scoped to one `game_id` | VERIFIED | `library_service.py:431` — `return _build_card(game, flaw_rows, is_analyzed, positions)` |
| `query_flaws` | `GamePosition` (two aliases) | `outerjoin on (game_id, user_id, ply)` and `ply-1` | VERIFIED | `library_repository.py:247-261` — `outerjoin(PositionAt, ...)` and `outerjoin(PositionBefore, ...)` |

---

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|-------------------|--------|
| `FlawCard.tsx` | `flaw` prop | `useLibraryFlaws` → `GET /library/flaws` → `query_flaws` | Yes — two aliased LEFT JOINs on `game_positions` populate `eval_cp_before/after`, `move_san`; `game.white_rating`/`black_rating` from `games` join | FLOWING |
| `FlawCard.tsx Dialog` | `data` from `useLibraryGame` | `GET /library/games/{game_id}` → `get_library_game` → `_build_card` | Yes — same three batch queries as `get_library_games` (`fetch_page_analyzed_set`, `fetch_page_game_flaws`, `fetch_page_eval_positions`) | FLOWING |
| `formatFlawEval` | `eval_cp_before/after`, `eval_mate_before/after` | `FlawListItem.eval_cp_before` etc. from `query_flaws` join | Yes — from `game_positions.eval_cp`/`eval_mate` via two aliased outerjoins | FLOWING |

---

### Behavioral Spot-Checks

Step 7b: SKIPPED for backend (server must be running to hit live endpoints). Frontend: component tests exercised by `npm test` (878/878 per SUMMARY-04).

---

### Probe Execution

No `scripts/*/tests/probe-*.sh` files declared or found for this phase.

---

### Requirements Coverage

Phase requirements noted as "TBD (derives from Success Criteria)" in PLAN files. All 8 success criteria verified against the codebase:

| SC | Description | Status | Evidence |
|----|-------------|--------|----------|
| SC-1 | Card grid (`grid-cols-1 lg:grid-cols-2`) replacing row list | VERIFIED | `FlawsTab.tsx:307` |
| SC-2 | Banded header with ratings; `white_rating`/`black_rating` in payload | VERIFIED | `FlawCard.tsx:148-160`, `library.py:136-137` |
| SC-3 | 132px miniboard with flaw arrow | VERIFIED | `FlawCard.tsx:28,214` |
| SC-4 | Standard notation move + eval swing + severity badge on same line | VERIFIED | `FlawCard.tsx:225-232`, `formatFlawEval.ts`, `openingInsights.ts:19-23` |
| SC-5 | TagChip + single TagLegend tooltip (no per-chip popovers) | VERIFIED | `FlawCard.tsx:237-244`, `TagChip.tsx:259` |
| SC-6 | Miniboard left + content stack right in canonical order | VERIFIED | `FlawCard.tsx:209-261` |
| SC-7 | "View game" modal via `GET /api/library/games/{game_id}` with IDOR guard | VERIFIED | `library.py:106-122`, `library_service.py:393-431`, `FlawCard.tsx:266-281` |
| SC-8 | `data-testid`/ARIA on all interactive elements; mobile 1-up grid | VERIFIED | `FlawCard.tsx:134,206,255,269-270` |

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `FlawCard.tsx` | 113 | `"TODO"` — none found | n/a | n/a |

No `TBD`, `FIXME`, `XXX`, `TODO`, placeholder text, or hardcoded empty arrays/objects in data paths found in any phase-modified files.

One noted deviation is intentional and fully documented:
- `FlawCard.tsx` uses `text-sm` floor throughout; only the Tooltip content (hover/tap opt-in surface, `ExternalLink` tooltip at line 127) may use `text-xs` per CLAUDE.md exception.

---

### Human Verification Required

1. **Flaws grid visual — 2-up desktop layout**

   **Test:** Open Library → Flaws subtab at viewport width ≥1024px with at least 2 analyzed flaws.
   **Expected:** FlawCards render side-by-side in a 2-column grid; each card shows the banded header, 132px miniboard with colored arrow, move notation + eval swing, SeverityBadge, TagChip row, TagLegend, metadata, and "View game" button.
   **Why human:** Grid layout, card visual language, board arrow rendering, and responsive breakpoint require browser inspection.

2. **Flaws grid visual — 1-up mobile collapse**

   **Test:** Resize to <1024px (or use DevTools mobile simulation).
   **Expected:** Each card occupies full width; no side-by-side cards.
   **Why human:** Responsive breakpoint behavior requires a browser.

3. **"View game" modal — open/close/content**

   **Test:** Click "View game" on any flaw card.
   **Expected:** Dialog opens (spinner briefly, then full LibraryGameCard with eval chart). Modal is scrollable and wide (`max-w-4xl`). Closing modal (X or outside click) resets the modal to closed state.
   **Why human:** Modal interaction, LibraryGameCard rendering inside Dialog, Pitfall-2 eval-chart tooltip clipping behavior all require live browser interaction.

4. **IDOR guard — live network**

   **Test:** While authenticated as user A, craft a request to `GET /api/library/games/{game_id_of_user_B}`.
   **Expected:** HTTP 404 with body `{"detail": "Game not found"}` — not 403, not another user's game data.
   **Why human:** Live backend call required; service-level IDOR is unit-tested but the live behavior should be confirmed once.

5. **Platform deep-link navigation**

   **Test:** Click the ExternalLink icon on a flaw card (lichess or chess.com game).
   **Expected:** A new tab opens at the exact half-move of the flaw on the platform's analysis board.
   **Why human:** External link navigation and platform URL correctness require a browser with real game data.

---

### Gaps Summary

No gaps. All 8 success criteria verified against the actual source files. The 5 human-verification items are behavioral/visual checks requiring browser interaction — all underlying code is fully implemented and wired.

---

_Verified: 2026-06-09T18:30:00Z_
_Verifier: Claude (gsd-verifier)_
