# Phase 135: Tactic Line Explorer — Research

**Researched:** 2026-06-24
**Domain:** Chess PV stepper — FastAPI endpoint, python-chess UCI→SAN, React hook clone, Dialog/Drawer switching
**Confidence:** HIGH (all findings grounded in the actual codebase, cited to file:line)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01 (modal stacking):** Explore launched from the game-card context opens as a second Dialog stacked on top of the Game modal. Closing Explore returns the user to the Game view exactly where they were.
- **D-02 (game-card disabled state):** The game-card Explore button is always visible and disabled (greyed) when the eval chart's currently-parked position is not a tagged flaw, with a tooltip/`aria-label` explaining why.
- **D-03 (game-card placement):** Place Explore below the eval chart, adjacent to the flaw-marker navigation. Honor mobile parity.
- **D-04 (flaw-card button row):** Pull "Game" out of the flaw-card header into a dedicated button row for all flaw cards (tagged and untagged). Untagged flaws show just "Game"; tagged flaws show Explore + Game, both `brand-outline`.
- **D-05 (mobile surface):** Desktop = full-screen Dialog; mobile = Drawer (bottom sheet, full width, `max-h-[95vh]`). Stacking/return-to-Game behavior still applies on both.

### Claude's Discretion
- **Explore gating and single-line flaws:** Explore appears for any tagged flaw with ≥1 line. When only one orientation is tagged, open with that single line and hide the toggle.
- **Payoff length and short PVs:** Walk tactic move + ~2–4 payoff plies past depth-0, then truncate. Handle PVs shorter than the tactic depth gracefully (no negative counters, no crash).
- **Backend contract:** Dedicated lazy-fetch endpoint returning both PVs + display depths + motif + tactic-move index. UCI→SAN conversion location left to research.

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.
</user_constraints>

---

## Summary

Phase 135 adds a "Tactic Line Explorer": a walkable PV stepper that opens from the flaw card and game card, surfacing the stored Stockfish `pv` field from `game_positions`. The core work is four units: (1) a new `GET /library/flaws/{game_id}/{ply}/tactic-lines` endpoint in `app/routers/library.py` that joins `game_positions` at ply `n` (missed PV) and `n+1` (allowed PV), converts UCI to SAN using `python-chess`, and returns both display-ready SAN sequences plus depth/motif metadata; (2) a `useTacticLine` hook cloned from `useChessGame.ts` — most of the navigation state is reusable, but the hook must diverge on session-storage, opening-lookup, depth-counter, payoff truncation, and orientation-toggle reset; (3) a `TacticLineExplorer` component that composes `ChessBoard`, `BoardControls`, and a new `SanLadder` using the design contract from `135-UI-SPEC.md`; (4) entry-point refactors in `FlawCard.tsx` (D-04: button row) and `LibraryGameCard.tsx` (D-03: Explore button wired to the selected flaw).

**Primary recommendation:** Convert UCI to SAN server-side with `python-chess`. The `game_positions.fen` column does not exist — the pre-flaw FEN is only in `game_flaws.fen`. Use that FEN plus `chess.Board.push_uci()` / `chess.Board.san()` on each PV move to produce display-ready SAN. Return a `TacticLinesResponse` with `missed_moves: list[str] | None` and `allowed_moves: list[str] | None`. Client receives SAN directly; no chess.js conversion needed.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| PV retrieval (DB→SAN) | API / Backend | — | Requires python-chess Board to convert UCI PV to SAN; wrong to push chess logic to the client for a server-originated PV |
| Depth offset application | API / Backend | Frontend (display) | `ALLOWED_DECISION_DEPTH_OFFSET` applied server-side for response values; same constant used client-side in `toDisplayDepthForOrientation` for label rendering |
| Navigator state (ply, position) | Browser / Client | — | React state in `useTacticLine`; board is stateless, hook drives it |
| Orientation toggle | Browser / Client | — | Pure UI state, no server round-trip on toggle |
| Dialog vs Drawer surface | Browser / Client | — | `useIsMobile` breakpoint check at render time, matches existing chart pattern |
| Arrow / depth-label rendering | Browser / Client | — | `ArrowOverlay` in `ChessBoard.tsx` + `MiniBoard.tsx` depth-badge geometry — all client-side SVG |
| IDOR guard on new endpoint | API / Backend | — | user_id from JWT; check `game_flaws.user_id == user_id` before returning PV |

---

## Standard Stack

### Core

All packages are already in the project. No new dependencies required for this phase.

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `python-chess` | 1.11.x [VERIFIED: pyproject.toml] | UCI→SAN conversion on the backend | Already in project; provides `chess.Board`, `push_uci()`, `san()` |
| `react-chessboard` | v5.x [VERIFIED: package.json] | Large board in explorer | Already in project via `ChessBoard.tsx` |
| `chess.js` | v1.x [VERIFIED: package.json] | SAN-replay in `useTacticLine` hook | Already used in `useChessGame.ts` and `LibraryGameCard.tsx` |
| `vaul` (via drawer.tsx) | installed [VERIFIED: drawer.tsx:2] | Bottom-sheet Drawer for mobile (D-05) | Already imported in App.tsx, InstallPromptBanner, MobileFilterDrawer |
| TanStack Query | v5.x [VERIFIED: useLibrary.ts] | Lazy-fetch `useTacticLines` hook | Standard fetch pattern; `enabled: open` gate triggers on modal open |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `lucide-react` | installed [VERIFIED: node/require] | `Telescope` icon for Explore button (confirmed present) | Icon for the Explore button per UI-SPEC; `Play` is the fallback (both available) |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Server-side UCI→SAN (python-chess) | Client-side UCI→SAN (chess.js) | Client-side saves one server step but requires shipping raw UCI and full board FEN to the frontend; harder to unit-test depth/offset math server-side; server conversion is cleaner and already has the FEN in `game_flaws.fen` |
| `useMediaQuery` from a new hook | `window.matchMedia` inline (pattern in ScoreChart, `MOBILE_BREAKPOINT_PX = 768`) | A local `useIsMobile` hook (same pattern as `ScoreChart.tsx:34–46`) is sufficient; no new utility library needed |

**Installation:** No new packages.

---

## Package Legitimacy Audit

No new external packages are introduced in this phase. All components reuse installed dependencies.

---

## Architecture Patterns

### System Architecture Diagram

```
Flaw Card (FlawCard.tsx)            Game Card (LibraryGameCard.tsx)
  [Explore btn] → open=true           [Explore btn] → open=true (disabled if no tagged flaw)
        │                                       │
        └──────────── useTacticLines(game_id, ply, enabled=open) ─────────────┘
                              │
                     TanStack Query
                              │
              GET /api/library/flaws/{game_id}/{ply}/tactic-lines
                              │
                   library_repository.fetch_tactic_lines()
                              │
              ┌───────────────┴────────────────┐
              │                                │
  game_flaws (fen, missed/allowed depth/motif) │
              │                                │
  game_positions[ply].pv   ←── missed PV      │
  game_positions[ply+1].pv ←── allowed PV     │
              │                                │
        python-chess UCI→SAN conversion        │
              │                                │
       TacticLinesResponse ──────────────────────►
                              │
           TacticLineExplorer (component)
           ┌─────────────────────────────────┐
           │  useIsMobile()                  │
           │    ├── Desktop → Dialog         │
           │    └── Mobile  → Drawer         │
           │                                 │
           │  useTacticLine(data, orientation)│
           │    ├── position (FEN)           │
           │    ├── currentPly              │
           │    ├── depth counter           │
           │    ├── goForward / goBack      │
           │    └── goToMove               │
           │                                 │
           │  ChessBoard + ArrowOverlay      │
           │  BoardControls (infoSlot=depth) │
           │  SanLadder (move list)          │
           │  Missed/Allowed toggle          │
           └─────────────────────────────────┘
```

### Recommended Project Structure

New files:

```
app/
├── routers/library.py          # Add GET /flaws/{game_id}/{ply}/tactic-lines route
├── repositories/library_repository.py  # Add fetch_tactic_lines()
└── schemas/library.py          # Add TacticLinesResponse

frontend/src/
├── hooks/
│   └── useTacticLine.ts        # New hook (clone of useChessGame.ts, diverged)
├── api/
│   └── client.ts               # Add getTacticLines() call
├── hooks/
│   └── useLibrary.ts           # Add useTacticLines() TanStack Query hook
└── components/
    └── library/
        ├── TacticLineExplorer.tsx   # New modal/drawer component
        └── SanLadder.tsx            # New linear SAN list component
```

Modified files:

```
frontend/src/
├── components/library/FlawCard.tsx         # D-04 button row refactor
└── components/results/LibraryGameCard.tsx  # D-03 Explore button + flaw tracking
```

---

## Research Finding 1: Backend Contract and UCI→SAN Conversion

### Decision: Server-Side UCI→SAN (python-chess)

**Rationale grounded in code:**

`game_positions.pv` [VERIFIED: `app/models/game_position.py:172`] stores a space-joined UCI string (e.g. `"g8f6 d4d5 f6e4"`), only written at `flaw_ply+1` positions. `game_positions` has NO `fen` column — only Zobrist hashes are persisted. But `game_flaws.fen` [VERIFIED: `app/models/game_flaw.py:66`] stores `board.board_fen()` of the pre-flaw decision board.

The conversion recipe is:
1. Read `game_flaws.fen` → construct `chess.Board(fen)` with correct `turn` (ply parity: even = white, odd = black) — exact same logic as `_detect_tactic_for_flaw` [VERIFIED: `app/services/flaws_service.py:445–446`].
2. For the **missed PV** (`game_positions[n].pv`): use `board_before` (no flaw move pushed). Walk UCI moves via `_parse_pv()` [VERIFIED: `app/services/tactic_detector.py:241–262`] which returns `(boards, moves)`. Convert each move to SAN via `boards[i].san(moves[i])`.
3. For the **allowed PV** (`game_positions[n+1].pv`): push the flaw move onto `board_before` to produce `board_after_flaw`, then walk the allowed PV from there.

The flaw move SAN is available from `game_positions[n].move_san` [VERIFIED: `app/models/game_position.py:141`] — convert to a chess.Move via `chess.Board.parse_san()` or find it via `push_uci` from `game_flaws.move_uci` if that column exists. Actually, `move_san` is a SAN string; to get the UCI move for the allowed-PV board construction, use `board_before.parse_san(pos_n.move_san)` to get the Move object, then `board_before.push(move)`. This is exactly how `_detect_tactic_for_flaw` builds `board_after_flaw` for the allowed pass [VERIFIED: `app/services/flaws_service.py:474–480`].

**Why NOT client-side:** The client would need the raw FEN and raw UCI PV. The FEN is in `game_flaws` not `game_positions`, so the endpoint must query `game_flaws` anyway — once you have both, python-chess conversion is trivial. Doing it server-side keeps chess logic in one place (Python), makes the depth/motif integration cleaner, and produces a directly-renderable payload.

### New Endpoint Shape

```
GET /api/library/flaws/{game_id}/{ply}/tactic-lines
```

Route: `app/routers/library.py` [VERIFIED: router prefix `/library` at line 33], relative path `/flaws/{game_id}/{ply}/tactic-lines`.

```python
# app/schemas/library.py — new response model
class TacticLinesResponse(BaseModel):
    """PV walk data for the TacticLineExplorer (Phase 135)."""
    # Missed line: SAN moves from the decision position (flaw_ply PV).
    # None when game_positions[ply].pv is NULL.
    missed_moves: list[str] | None = None
    missed_depth: int | None = None        # raw 0-based loop index (DB value)
    missed_motif: str | None = None        # TacticMotif string or None
    # Allowed line: SAN moves starting from board_after_flaw (flaw_ply+1 PV).
    # First move is the flaw move itself (red arrow).
    # None when game_positions[ply+1].pv is NULL.
    allowed_moves: list[str] | None = None
    allowed_depth: int | None = None       # raw 0-based loop index (DB value)
    allowed_motif: str | None = None       # TacticMotif string or None
    # Pre-flaw decision position FEN (board_fen() — piece placement only,
    # same format as game_flaws.fen). Used to seed the explorer board.
    position_fen: str                      # from game_flaws.fen
    flaw_move_san: str | None = None       # move played (from game_positions[n].move_san)
    best_move_uci: str | None = None       # engine best move (from game_positions[n].best_move)
```

**IDOR pattern:** Route checks `game_flaws.user_id == user.id` before returning anything. 404 (not 403) on miss, matching the existing `get_library_game` pattern [VERIFIED: `app/routers/library.py:157–168`].

**What the repository function fetches (two positions):**

```python
# Pseudocode for library_repository.fetch_tactic_lines()
# 1. SELECT game_flaws WHERE user_id=user_id AND game_id=game_id AND ply=ply
#    → flaw row (for .fen, .missed_tactic_*, .allowed_tactic_*, player_only_gate)
# 2. SELECT game_positions WHERE user_id=user_id AND game_id=game_id AND ply IN (ply, ply+1)
#    → two rows (pos_n for missed PV + best_move; pos_n1 for allowed PV)
# 3. Convert UCI PV to SAN using python-chess (see below)
# 4. Return TacticLinesResponse
```

**PV→SAN conversion logic:**

```python
import chess
from app.services.tactic_detector import _parse_pv

def _pv_to_san(fen: str, ply: int, pv: str | None) -> list[str] | None:
    """Convert a space-joined UCI PV string to SAN, starting from fen.
    
    fen is board_fen() (piece placement only). ply determines turn.
    Returns None when pv is None/empty; returns partial list on parse error.
    """
    if not pv:
        return None
    board = chess.Board(fen)
    board.turn = chess.WHITE if ply % 2 == 0 else chess.BLACK
    try:
        boards, moves = _parse_pv(board, pv)
    except ValueError:
        return None
    return [boards[i].san(moves[i]) for i in range(len(moves))]
```

For the **allowed** line the starting board is `board_after_flaw` (flaw move pushed). The SAN list starts with the flaw move itself so the ladder correctly shows "Red move (the mistake) → opponent's punishment".

**Payoff truncation:** Apply in the repository function. The total SAN list length = `min(len(raw_moves), tactic_depth + PAYOFF_MAX_PLIES)` where `PAYOFF_MAX_PLIES: int = 3` (executor picks within the 2–4 band from CONTEXT.md). Name the constant so it's not a magic number.

---

## Research Finding 2: PV Anchoring and Offset Semantics

### Confirmed PV Sources

**Missed line** [VERIFIED: `app/services/flaws_service.py:453–455`]:
- Source: `positions[n].pv` where `n = flaw.ply`
- Board: `board_before` (no flaw move; same decision position as the pre-flaw miniboard)
- Depth stored: `game_flaws.missed_tactic_depth` — 0-based index into the missed PV's loop at which the motif fires
- The detector fires DURING the PV walk starting from `board_before.turn`

**Allowed line** [VERIFIED: `app/services/flaws_service.py:479–480`]:
- Source: `positions[n + 1].pv` where `n = flaw.ply`
- Board: `board_after_flaw` (flaw move pushed)
- Depth stored: `game_flaws.allowed_tactic_depth` — 0-based index within the allowed PV's loop
- The allowed PV starts one ply LATER than the missed PV; hence the +1 decision-anchor offset

### Offset Constants

Both are 0-based raw detector-loop indices within their own PV. The display offset is:

```
display_depth = raw_depth + DEPTH_DISPLAY_OFFSET (+ ALLOWED_DECISION_DEPTH_OFFSET for allowed)
```

Constants [VERIFIED]:
- `DEPTH_DISPLAY_OFFSET = 1` (`frontend/src/lib/tacticDepth.ts:30`) — 0-based → 1-based for all user-visible depths
- `ALLOWED_DECISION_DEPTH_OFFSET = 1` (`frontend/src/lib/tacticDepth.ts:49`) — allowed PV starts 1 ply later
- Python mirror: `ALLOWED_DECISION_DEPTH_OFFSET: int = 1` (`app/repositories/library_repository.py:78`)

**What the endpoint must return:** Raw 0-based depths (`missed_depth`, `allowed_depth`). The frontend applies `toDisplayDepthForOrientation()` [VERIFIED: `frontend/src/lib/tacticDepth.ts:59–65`] to get the 1-based display numbers. This matches how the miniboard depth badges already work in `FlawCard.tsx:141–148` [VERIFIED].

**Depth counter in the explorer:** At the root (ply 0), show `toDisplayDepthForOrientation(flaw.missed_depth, 'missed')` for the missed orientation and `toDisplayDepthForOrientation(flaw.allowed_depth, 'allowed')` for the allowed orientation. As the user steps forward, the counter decrements by 1 per ply (floor at 0). Past depth-0: show "Payoff" (per UI-SPEC). The hook tracks this as `Math.max(0, displayDepthAtRoot - currentPly)` where `displayDepthAtRoot` is set on load and reset on orientation toggle.

**Tactic-move index:** The depth-0 move is at PV index `raw_tactic_depth`. The endpoint should also return `missed_tactic_ply_index: int | None` and `allowed_tactic_ply_index: int | None` (same value as the raw depth), so the SAN ladder can highlight the tactic punchline move without recomputing.

---

## Research Finding 3: Frontend Hook Architecture

### What `useChessGame.ts` Provides

[VERIFIED: `frontend/src/hooks/useChessGame.ts`]

- **Reusable core:** `position` (FEN), `moveHistory` (SAN array), `currentPly` (int), `replayTo()` (rebuilds board from history), `goForward`, `goBack`, `goToMove`, `loadMoves` (accepts `string[]` and replays to end), `lastMove` ({from, to}).
- **Reusable pattern:** `replayTo(history, ply)` rebuilds a fresh `Chess` instance by replaying `history[0..ply-1]`. This works identically for tactic PV moves — `chess.js` accepts SAN natively.
- **Must NOT carry over:** session-storage persistence (`STORAGE_KEY`), opening lookup (`findOpening` / `preloadOpenings`), Zobrist hashing (`computeHashes`), `getHashForOpenings`, `makeMove` (user-draggable moves), `MAX_EXPLORER_PLY` guard. The tactic explorer has a fixed linear PV — no free play.
- **Keyboard handler must be scoped:** `useChessGame` attaches to `window`. The new hook must scope to the explorer container (ref or dialog portal) to avoid conflicting with page-level shortcuts. Use `containerRef.current?.addEventListener` + cleanup, or restrict to `e.target` inside the dialog.

### `useTacticLine` Hook Design

```typescript
// frontend/src/hooks/useTacticLine.ts

interface TacticLineState {
  position: string;          // current FEN
  currentPly: number;        // 0 = root (decision position), 1+ = after PV moves
  lastMove: { from: string; to: string } | null;
  displayDepth: number;      // toDisplayDepthForOrientation(rootDepth - currentPly, orientation), floor 0
  isPayoff: boolean;         // currentPly > tacticPlyIndex (past depth-0)
  goForward: () => void;     // advance one ply (capped at moveHistory.length)
  goBack: () => void;        // retreat one ply (floor at 0)
  goToMove: (ply: number) => void;
  reset: () => void;         // return to root
  canGoForward: boolean;
  canGoBack: boolean;
}

interface UseTacticLineOptions {
  // SAN moves from TacticLinesResponse (missed_moves or allowed_moves).
  // If starting with the allowed line, first move is the flaw move (red).
  moves: string[] | null;
  // Starting FEN (board_fen() from TacticLinesResponse.position_fen).
  // Must be a full FEN — append " {turn} - - 0 1" from ply parity.
  rootFen: string;
  // Raw 0-based tactic depth index (missed_depth or allowed_depth from response).
  tacticDepthRaw: number;
  // Orientation drives the display offset formula.
  orientation: 'missed' | 'allowed';
}
```

**Divergences from `useChessGame`:**
1. No `sessionStorage` — state is ephemeral to the modal open.
2. No opening lookup.
3. No Zobrist hashing.
4. `loadMoves` called once on mount / orientation change instead of interactively.
5. Depth counter: `rootDisplayDepth - currentPly`, floored at 0.
6. `isPayoff`: `currentPly > tacticDepthRaw` (past the punchline move).
7. Payoff truncation: `moves` passed in is already truncated by the server; hook just walks it.
8. Keyboard handler: attach to `containerRef.current` not `window`.
9. `reset()` calls `replayTo(moves, 0)` which returns to the root FEN (no prior position; starting position is the decision board).

**Root position (ply=0) arrows:** At ply 0 the hook does not have a `lastMove` (no move has been made). The `TacticLineExplorer` must derive both arrows (missed best-move blue + allowed red flaw-move) from `TacticLinesResponse.best_move_uci` and `TacticLinesResponse.flaw_move_san` using the existing `uciToSquares` / `sanToSquares` helpers [VERIFIED: `frontend/src/lib/sanToSquares.ts`]. After ply 0, the current move arrow comes from `lastMove` provided by the hook.

**FEN reconstruction for root:** `game_flaws.fen` is a `board_fen()` (piece placement only, no side-to-move). To use it with `chess.js`, construct the full FEN: `"${position_fen} ${turn} - - 0 1"` where `turn` is derived from `flaw.ply % 2 === 0 ? 'w' : 'b'` [VERIFIED: `app/services/flaws_service.py:445–446`]. The endpoint should return `position_fen` with this side-to-move already appended, or return `flaw_ply` so the frontend can derive it. Simplest: return a full FEN from the backend (avoids client-side ply-parity logic).

---

## Research Finding 4: Entry Points

### FlawCard.tsx Refactor (D-04)

**Current state** [VERIFIED: `frontend/src/components/library/FlawCard.tsx:207–218`]:

The "Game" button is a `<button type="button">` with class `ml-auto shrink-0 inline-flex ... text-sm text-brand-brown-light` — NOT a shadcn `Button` component with `variant="brand-outline"`. It lives in the `CardHeader` as `viewGameButton`.

**Required changes:**
1. Remove `viewGameButton` from `CardHeader` [VERIFIED: line 254: `{viewGameButton}` inside `CardHeader`].
2. Add a new `buttonRow` below the card body in BOTH the mobile section (`sm:hidden` block, line 410) and the desktop section (`hidden sm:flex` block, line 427).
3. `buttonRow` = `<div className="flex gap-2 mt-2 px-3 pb-3">`:
   - Tagged flaw (`flaw.missed_tactic_motif != null || flaw.allowed_tactic_motif != null`): `<Button variant="brand-outline" data-testid="flaw-btn-explore">Explore</Button>` + `<Button variant="brand-outline" data-testid="flaw-btn-game">Game</Button>`
   - Untagged flaw: `<Button variant="brand-outline" data-testid="flaw-btn-game">Game</Button>` only

**Gate check:** The existing `missed_tactic_motif` / `allowed_tactic_motif` fields are set to `null` in the payload when the confidence gate fails [VERIFIED: `app/repositories/library_repository.py:864–946`]. So `flaw.missed_tactic_motif != null || flaw.allowed_tactic_motif != null` correctly identifies "tagged" without a separate boolean.

### LibraryGameCard.tsx Refactor (D-03)

**Current state** [VERIFIED: `frontend/src/components/results/LibraryGameCard.tsx:1–100`]:

`LibraryGameCard` renders an eval chart (`EvalChart`) and manages per-ply navigation state via `buildPerPly` (line 85). The card receives `flaw_markers: FlawMarker[]` from `GameFlawCard` and the `initialPly` prop. The per-ply flaw tracking uses the slider's current ply.

**D-03 placement:** The Explore button goes below the eval chart row. The component needs to track the "currently selected flaw" from the eval chart navigation.

**Finding:** `LibraryGameCard` already builds `perPly` from the moves mainline and the `GameFlawCard.flaw_markers` list contains flaw info per ply. The selected ply is maintained by an `useState` driven by the eval chart's slider. The Explore button needs to know:
1. What ply is currently selected (the eval chart's selected ply).
2. Whether that ply's `flaw_markers` entry is a tagged flaw (has `missed_tactic_motif` or `allowed_tactic_motif` non-null).
3. `is_user: true` (user flaw only, not opponent).

The disabled state: `selectedPlyFlawMarker?.missed_tactic_motif == null && selectedPlyFlawMarker?.allowed_tactic_motif == null` → button is disabled.

---

## Research Finding 5: Mobile Surface Pattern (D-05)

### Drawer Pattern Confirmed

[VERIFIED: `frontend/src/components/ui/drawer.tsx:6–72`] — `vaul` Drawer is already installed and used in:
- `frontend/src/App.tsx:327–394` (MobileMoreDrawer, direction="bottom")
- `frontend/src/components/install/InstallPromptBanner.tsx` (direction="bottom")
- `frontend/src/components/filters/MobileFilterDrawer.tsx` (filter sidebar)

The `DrawerContent` base class sets `data-[vaul-drawer-direction=bottom]:max-h-[80vh]` at line 62. The UI-SPEC requires `max-h-[95vh]` — override this with a `className` prop on `DrawerContent`. The base class also sets `data-[vaul-drawer-direction=left]:sm:max-w-sm` (filter drawer default) which does NOT apply to the bottom direction, so no width override conflict for bottom drawers.

### Breakpoint Detection

No `useMediaQuery` hook exists in the project. The established pattern from `ScoreChart.tsx:34–46` and `EndgameEloTimelineSection.tsx:59–65` is a local `useIsMobile()` hook:

```typescript
const MOBILE_BREAKPOINT_PX = 768;  // matches Tailwind `md` breakpoint

function useIsMobile(): boolean {
  const [isMobile, setIsMobile] = useState(() =>
    typeof window !== 'undefined'
      && window.matchMedia(`(max-width: ${MOBILE_BREAKPOINT_PX - 1}px)`).matches,
  );
  useEffect(() => {
    const mq = window.matchMedia(`(max-width: ${MOBILE_BREAKPOINT_PX - 1}px)`);
    const update = () => setIsMobile(mq.matches);
    mq.addEventListener('change', update);
    return () => mq.removeEventListener('change', update);
  }, []);
  return isMobile;
}
```

Define this once in `TacticLineExplorer.tsx` (or extract to a shared `useMobileBreakpoint.ts` hook if the planner identifies it's needed elsewhere). The UI-SPEC pattern of `const isDesktop = useMediaQuery('(min-width: 768px)')` maps to `!useIsMobile()`.

### Nested Dialog Concern (D-01/D-05)

The D-01 risk (nested dialog focus/scroll trap on mobile) is **resolved by D-05** — on mobile the explorer opens as a `Drawer` (different Radix primitive from the game-card's `Dialog`), so there is no Dialog-in-Dialog nesting on the surface that was at risk. On desktop the explorer is a Dialog nested in the FlawCard's Dialog — Radix UI's Dialog handles focus management via a portal and correctly scopes focus to the topmost open dialog. No custom focus trap code is needed.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| UCI→SAN conversion | Custom move string parser | `python-chess` `_parse_pv()` + `board.san()` | Already used by `tactic_detector.py:241–262`; handles promotion, en passant, castling |
| PV walking | Manual UCI split + board reconstruction | `_parse_pv()` from `tactic_detector.py` | Handles AssertionError from pseudo-illegal moves (raises ValueError); reuse the guard |
| Bottom sheet on mobile | Custom CSS slide-up panel | `vaul` Drawer via `drawer.tsx` | Already in project; handles drag gestures, focus, animation |
| Arrow rendering with depth labels | Custom SVG | `MiniBoard.tsx` depth-badge geometry + `ChessBoard.tsx`'s `ArrowOverlay` | Both already handle the label/color conventions; tactic explorer uses `ChessBoard.tsx`'s overlay |
| Board state navigation | Custom ply tracker | Clone `replayTo()` pattern from `useChessGame.ts` | Tested, handles ply bounds, extracts `from/to` for highlighting |

**Key insight:** `_parse_pv` in `tactic_detector.py` is the right building block for the repository conversion function. It already catches `AssertionError` (pseudo-illegal move) as `ValueError`. Import it from `app.services.tactic_detector` in the new repository helper.

---

## Common Pitfalls

### Pitfall 1: Short PV — tactic depth exceeds PV length

**What goes wrong:** `game_flaws.missed_tactic_depth` is 5 but `game_positions[n].pv` only has 3 UCI moves. If the hook computes `displayDepth = rootDepth - currentPly` without bounding to PV length, the depth counter goes below 0.

**Why it happens:** `pv` is written by the Stockfish drain and may be truncated (engine ran out of nodes, or the last few moves are noise). The tactic fires at `depth=5` in a longer search but the stored PV has fewer plies.

**How to avoid:** In the repository function, cap the truncated SAN list at `min(len(sans), PAYOFF_MAX_PLIES + tactic_depth + 1)` where `tactic_depth` is the raw depth. The explorer never needs moves beyond the payoff band. In `useTacticLine`, floor depth display at 0 and never compute a negative. `isPayoff` is `currentPly > tacticDepthRaw && currentPly <= moves.length`.

**Warning signs:** Test with a flaw where `allowed_tactic_depth > len(allowed_moves)`. The test helper for `fetch_tactic_lines` must cover this edge case.

### Pitfall 2: `position_fen` is `board_fen()` (piece-only), not a full FEN

**What goes wrong:** `game_flaws.fen` stores `board.board_fen()` [VERIFIED: `app/services/flaws_service.py:66` comment]. If the endpoint returns this raw string to chess.js, `new Chess(fen)` will fail because chess.js requires a full FEN including side-to-move, castling rights, and en passant.

**How to avoid:** The endpoint should return a FULL FEN with the side-to-move determined from ply parity. In python-chess: `board = chess.Board(fen); board.turn = chess.WHITE if ply % 2 == 0 else chess.BLACK; return board.fen()`. Alternatively return `fen + f" {'w' if ply % 2 == 0 else 'b'} - - 0 1"` (castling rights unknown — chess.js accepts this for display purposes).

### Pitfall 3: Allowed PV first move — whose SAN is it?

**What goes wrong:** `allowed_moves[0]` is the FLAW MOVE (the red move the player made). If the hook treats all `moves[]` as engine continuation moves from the start, arrows are wrong.

**Why it happens:** The allowed PV starts from `board_after_flaw` — it begins with the opponent's refutation. But for the explorer ladder, CONTEXT.md / SEED-065 specifies that "for the allowed line, the first move you walk forward IS the red flaw move." The PV stored in `game_positions[n+1].pv` starts AFTER the flaw move (it's the opponent's line). So the flaw move itself is NOT in the stored PV.

**Clarification from code** [VERIFIED: `app/services/flaws_service.py:474–480`]: `pv_allowed = positions[n + 1].pv`. This is the PV starting from `board_after_flaw` (flaw move already pushed). The flaw move is NOT in `pv_allowed`; it's in `positions[n].move_san`.

**How to handle:** For the allowed line, prepend the flaw move SAN to the UCI→SAN-converted PV. In the repository function: `allowed_moves = [flaw_move_san] + _pv_to_san(board_after_flaw_fen, ply + 1, pos_n1.pv)`. The explorer hook then has `allowed_moves[0]` = flaw move (red arrow at ply 1), `allowed_moves[1+]` = opponent PV (blue arrows). At the root (ply 0) both arrows are shown from `best_move_uci` + `flaw_move_san`.

### Pitfall 4: `game_positions[n].pv` may be NULL for missed PV

**What goes wrong:** `pv` is only written for positions AT flaw ply+1 (refutation). The missed PV `game_positions[n].pv` is the PV AT the decision position. This field is populated for flaw positions — but NOT guaranteed for every position [VERIFIED: `app/models/game_position.py:170–172` comment: "NULL for non-flaw positions"]. For the missed line, `game_positions[n].pv` is written at the FLAW ply, which IS a flaw position — so it should be populated. But check: `positions[n+1].pv` is for the allowed line; `positions[n].pv` is for the missed line. Both are non-null when the eval drain ran and stored the PV.

**How to avoid:** The endpoint sets `missed_moves = None` when `pos_n.pv is None` and `allowed_moves = None` when `pos_n1 is None or pos_n1.pv is None`. The frontend's "empty state" (from UI-SPEC: "Tactic line not available for this flaw.") handles `null` for either line.

### Pitfall 5: Single-orientation flaws — toggle visibility

**What goes wrong:** A flaw has `missed_tactic_motif` but `allowed_tactic_motif` is null. If the toggle is shown in the disabled state (not hidden), the UX is confusing.

**How to avoid (per CONTEXT.md Claude's Discretion):** When only one orientation is non-null, hide the toggle entirely and default to the available orientation. The `TacticLineExplorer` checks `data.missed_moves != null && data.allowed_moves != null` to decide toggle visibility. Per UI-SPEC: "Visible only when BOTH lines exist. Hidden (not disabled) when only one line."

### Pitfall 6: ChessBoard `id` prop conflict

**What goes wrong:** `ChessBoard` passes `id: 'chessboard'` to `react-chessboard` options [VERIFIED: `frontend/src/components/board/ChessBoard.tsx:306`]. If two board instances are in the DOM (game view + explorer), they share the same `id`, conflicting square testids.

**How to avoid:** The `TacticLineExplorer` uses its own board instance, but it needs `id="tactic-explorer-board"` per UI-SPEC. Currently `id` is hardcoded in `ChessBoard.tsx` as `'chessboard'`. The planner must add an optional `id?: string` prop to `ChessBoard` (defaulting to `'chessboard'`) so the explorer can pass `'tactic-explorer-board'`.

---

## Code Examples

Verified patterns from the codebase:

### Backend: PV→SAN repository function structure

```python
# Follows _detect_tactic_for_flaw pattern
# Source: app/services/flaws_service.py:401–480 (VERIFIED)
import chess
from app.services.tactic_detector import _parse_pv

PAYOFF_MAX_PLIES: int = 3  # 2-4 band from CONTEXT.md; named constant per CLAUDE.md

def _pv_to_san_list(board: chess.Board, pv: str | None) -> list[str] | None:
    """Convert space-joined UCI PV to SAN list from starting board. Returns None on absent PV."""
    if not pv:
        return None
    try:
        boards, moves = _parse_pv(board, pv)
    except ValueError:
        return None
    return [boards[i].san(moves[i]) for i in range(len(moves))]

def _truncate_pv(sans: list[str] | None, tactic_depth_raw: int | None) -> list[str] | None:
    """Truncate SAN list to tactic punchline + PAYOFF_MAX_PLIES. Handles short PVs gracefully."""
    if sans is None:
        return None
    if tactic_depth_raw is None:
        return sans[:PAYOFF_MAX_PLIES]
    return sans[: tactic_depth_raw + 1 + PAYOFF_MAX_PLIES]
```

### Frontend: `replayTo` pattern (from useChessGame.ts:143–160)

```typescript
// Source: frontend/src/hooks/useChessGame.ts:143–160 (VERIFIED)
const replayTo = useCallback((history: string[], ply: number) => {
  const chess = new Chess();
  let fromSq: string | null = null;
  let toSq: string | null = null;
  for (let i = 0; i < ply; i++) {
    const move = chess.move(history[i]!);
    if (i === ply - 1 && move) {
      fromSq = move.from;
      toSq = move.to;
    }
  }
  chessRef.current = chess;
  setPosition(chess.fen());
  setCurrentPly(ply);
  setLastMove(fromSq && toSq ? { from: fromSq, to: toSq } : null);
}, []);
```

For `useTacticLine`, this is the same pattern but with a non-standard starting FEN (root is the decision position, not the starting position). Initialize `chessRef` with `new Chess(rootFen)` and replay from there:

```typescript
// useTacticLine divergence: start from rootFen, not starting position
const replayTo = useCallback((history: string[], ply: number) => {
  const chess = new Chess(rootFen);  // root = decision position
  // ... same loop as useChessGame ...
}, [rootFen]);
```

### Frontend: ArrowOverlay arrow interface

```typescript
// Source: frontend/src/components/board/ChessBoard.tsx:14–30 (VERIFIED)
interface BoardArrow {
  startSquare: string;
  endSquare: string;
  color: string;
  width: number;       // 0-1 normalized
  isHovered?: boolean;
  isHighlightPulse?: boolean;
}
// Note: ChessBoard.tsx's ArrowOverlay does NOT support depth labels.
// Depth labels are a MiniBoard.tsx feature (SVG <text> on target square).
// The TacticLineExplorer needs a CUSTOM overlay (or extends ArrowOverlay) to add depth badges.
```

**Important:** `ChessBoard.tsx`'s `ArrowOverlay` does not render depth labels — that feature is in `MiniBoard.tsx` only [VERIFIED: `frontend/src/components/board/MiniBoard.tsx:16–35`]. The planner must account for building a custom `TacticArrowOverlay` for the explorer board that adds depth-badge SVG `<text>` elements, following the `MiniBoard.tsx` geometry pattern (`DEPTH_LABEL_FONT`, `DEPTH_LABEL_CORNER_INSET`, etc.).

### Frontend: Drawer usage pattern

```tsx
// Source: frontend/src/App.tsx:340–394 (VERIFIED)
<Drawer open={open} onOpenChange={onOpenChange} direction="bottom">
  <DrawerContent className="w-full max-h-[95vh]">  {/* override default 80vh */}
    <DrawerHeader>
      <DrawerTitle>Explore Tactic</DrawerTitle>
    </DrawerHeader>
    {/* body */}
  </DrawerContent>
</Drawer>
```

### Frontend: `useLibrary.ts` hook pattern for lazy-fetch

```typescript
// Source: frontend/src/hooks/useLibrary.ts:1–15 (VERIFIED)
// New hook follows same shape as useLibraryGame
export function useTacticLines(
  gameId: number | null,
  ply: number | null,
  enabled: boolean,
) {
  return useQuery({
    queryKey: ['tactic-lines', gameId, ply],
    queryFn: () => libraryApi.getTacticLines(gameId!, ply!),
    enabled: enabled && gameId != null && ply != null,
    staleTime: LIBRARY_STALE_TIME,
  });
}
```

---

## Runtime State Inventory

Not applicable — this is a greenfield frontend/endpoint feature with no renames or migrations.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| python-chess | UCI→SAN backend conversion | ✓ | 1.11.x [VERIFIED: pyproject.toml] | — |
| react-chessboard v5 | Explorer board | ✓ | 5.x [VERIFIED: package.json] | — |
| vaul (Drawer) | Mobile drawer | ✓ | installed [VERIFIED: drawer.tsx] | — |
| chess.js | SAN replay in hook | ✓ | 1.x [VERIFIED: useChessGame.ts] | — |
| lucide-react `Telescope` | Explore button icon | ✓ | confirmed [VERIFIED: node require] | `Play` icon |
| PostgreSQL (dev) | DB join for PVs | ✓ | Docker compose | — |

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (backend), vitest (frontend) |
| Config file | `pytest.ini` / `vitest.config.ts` |
| Quick run command | `uv run pytest tests/routers/test_library_tactic_lines.py -x` |
| Full suite command | `uv run pytest -n auto -x` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| — | GET /tactic-lines returns 200 with TacticLinesResponse shape | integration | `uv run pytest tests/routers/test_library_tactic_lines.py::test_200_shape -x` | ❌ Wave 0 |
| — | GET /tactic-lines returns 404 for wrong user (IDOR) | integration | `uv run pytest tests/routers/test_library_tactic_lines.py::test_404_wrong_user -x` | ❌ Wave 0 |
| — | GET /tactic-lines returns 401 unauthenticated | integration | `uv run pytest tests/routers/test_library_tactic_lines.py::test_401_unauthenticated -x` | ❌ Wave 0 |
| — | n vs n+1 PV anchoring: missed from pos[n].pv, allowed from pos[n+1].pv | unit | `uv run pytest tests/repositories/test_library_tactic_lines_repo.py -x` | ❌ Wave 0 |
| — | Short PV (length < tactic_depth): no crash, no negative depth display | unit | included in repo test | ❌ Wave 0 |
| — | ALLOWED_DECISION_DEPTH_OFFSET applied correctly in response | unit | included in repo test | ❌ Wave 0 |
| — | useTacticLine: goForward/goBack update position and depth | frontend unit | `npm test -- --run hooks/useTacticLine` | ❌ Wave 0 |
| — | FlawCard renders Explore+Game button row for tagged, Game-only for untagged | frontend unit | `npm test -- --run FlawCard` | exists ✅ (extend) |
| — | Explorer Explore button disabled when no tagged flaw selected in game card | frontend unit | `npm test -- --run TacticLineExplorer` | ❌ Wave 0 |

### Sampling Rate

- Per task commit: `uv run pytest tests/routers/test_library_tactic_lines.py -x` + `npm test -- --run`
- Per wave merge: `uv run pytest -n auto -x` + `npm run lint && npm test -- --run`
- Phase gate: full suite green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/routers/test_library_tactic_lines.py` — endpoint shape + 401 + 404 + IDOR
- [ ] `tests/repositories/test_library_tactic_lines_repo.py` — PV anchoring, offset math, short PV edge case, NULL PV graceful handling
- [ ] `frontend/src/hooks/__tests__/useTacticLine.test.tsx` — navigation, depth counter, orientation reset
- [ ] `frontend/src/components/library/__tests__/TacticLineExplorer.test.tsx` — render, toggle, disabled state
- [ ] `ChessBoard.tsx` id prop: add `id?: string` prop and update tests if any assert on `id="chessboard"`

---

## Security Domain

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes | FastAPI-Users JWT — inherited from existing `/library/*` pattern |
| V4 Access Control | yes | user_id from JWT only; 404 (not 403) on IDOR; matches T-108-10 / T-112-01 pattern |
| V5 Input Validation | yes | `game_id: int` and `ply: int` path params; FastAPI 422-rejects non-integers (T-112-05 pattern) |
| V6 Cryptography | no | No crypto in this phase |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| IDOR on game_id/ply | Disclosure | user_id from JWT, `game_flaws.user_id == user_id` WHERE clause before returning PV |
| Non-integer path param | Tampering | FastAPI `int` type annotation auto-validates |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `game_positions[n].pv` (missed line) is consistently populated for flaw positions — it was written by the eval drain alongside `allowed_tactic_*` classification | Research Finding 4, Pitfall 4 | If missed PV is sparse, more flaws will show "not available"; not a crash but feature coverage is lower |
| A2 | The allowed SAN list prepends the flaw move (`flaw_move_san`) to make `allowed_moves[0]` the red move | Research Finding 3, Pitfall 3 | If this semantic is wrong the arrow at ply 1 will be wrong color |
| A3 | `PAYOFF_MAX_PLIES = 3` (middle of the 2–4 band from CONTEXT.md) is acceptable | Common Pitfalls | Executor has discretion in the 2–4 range; this is a reasonable default constant |

---

## Open Questions (RESOLVED)

1. **Full FEN vs board_fen from endpoint**
   - What we know: `game_flaws.fen` is `board_fen()` (piece-placement only); chess.js needs full FEN.
   - What's unclear: Whether the endpoint should compute side-to-move from ply parity and return a full FEN, or return `fen` + `ply` and let the frontend derive it.
   - RESOLVED: Return a full FEN from the endpoint (`board.fen()` after setting `board.turn` from ply parity). Simpler frontend code, zero ambiguity. Implemented in Plan 01 Task 2.

2. **`ChessBoard` `id` prop refactor scope**
   - What we know: `id: 'chessboard'` is hardcoded in `ChessBoard.tsx:306`; the explorer needs `id="tactic-explorer-board"`.
   - What's unclear: Whether there is any test that asserts on the hardcoded id string.
   - RESOLVED: Add `id?: string` prop to `ChessBoard` (default `'chessboard'`). Minimal change, no behavior impact. Implemented in Plan 02 Task 2.

3. **Depth-label SVG in the large explorer board**
   - What we know: `ChessBoard.tsx`'s `ArrowOverlay` does NOT support depth labels (confirmed code read); only `MiniBoard.tsx` has SVG depth badges.
   - What's unclear: Whether to (a) extend `ChessBoard`'s `ArrowOverlay` with an optional label prop, (b) write a parallel `TacticArrowOverlay` component for the explorer, or (c) render a separate SVG layer beside the board for depth badges.
   - RESOLVED: Add an optional `label?: string; labelColor?: string` to `BoardArrow` in `ChessBoard.tsx` and mirror the `MiniBoard.tsx` badge geometry. This is the cleanest extension that doesn't duplicate the entire overlay. Implemented in Plan 02 Task 2.

---

## Sources

### Primary (HIGH confidence — verified in codebase)

- `app/repositories/library_repository.py` — `ALLOWED_DECISION_DEPTH_OFFSET`, `_TACTIC_CHIP_CONFIDENCE_MIN`, `_parse_pv` reuse pattern, query_flaws join structure
- `app/services/tactic_detector.py:241–262` — `_parse_pv()` implementation (board sequence builder)
- `app/services/flaws_service.py:401–480` — `_detect_tactic_for_flaw()` (PV sourcing, board construction, fen→turn mapping)
- `app/models/game_position.py:169–172` — `pv` column definition and semantics (NULL for non-flaw positions)
- `app/models/game_flaw.py:60–94` — `fen` column (board_fen(), pre-flaw), tactic depth semantics
- `app/routers/library.py` — router prefix, IDOR/404 pattern, existing endpoint shapes
- `app/schemas/library.py` — `FlawListItem`, `EvalPoint`, existing response model patterns
- `frontend/src/hooks/useChessGame.ts` — full hook internals (replayTo, loadMoves, keyboard, session storage)
- `frontend/src/lib/tacticDepth.ts` — `toDisplayDepthForOrientation`, `ALLOWED_DECISION_DEPTH_OFFSET`, `DEPTH_DISPLAY_OFFSET`
- `frontend/src/components/board/ChessBoard.tsx` — `ArrowOverlay` interface, `id` hardcoding at line 306
- `frontend/src/components/board/MiniBoard.tsx` — depth-label badge geometry constants
- `frontend/src/components/board/BoardControls.tsx` — `infoSlot` prop, size variants
- `frontend/src/components/library/FlawCard.tsx` — current button placement (line 207–218, 254), card structure
- `frontend/src/components/ui/drawer.tsx` — Drawer primitives, vaul-direction CSS, max-h default
- `frontend/src/App.tsx:340–394` — existing bottom Drawer usage pattern

### Secondary (MEDIUM confidence — cross-referenced)

- `frontend/src/lib/sanToSquares.ts` — `uciToSquares`, `sanToSquares`, `fenAfterMove` helpers (confirmed available)
- `frontend/src/components/charts/ScoreChart.tsx:32–46` — `useIsMobile` pattern with `MOBILE_BREAKPOINT_PX = 768`
- `tests/routers/test_library_tactic_comparison.py` — router test pattern to clone for new tactic-lines tests
- `tests/repositories/test_library_repository.py` — repository unit test pattern

---

## Metadata

**Confidence breakdown:**
- Backend contract: HIGH — all PV fields, fen column, IDOR pattern verified in code
- PV anchoring/offsets: HIGH — both Python and TS constants verified with exact file:line citations
- Frontend hook architecture: HIGH — `useChessGame.ts` read in full; divergences clearly identified
- Mobile drawer pattern: HIGH — vaul usage verified in three existing files
- Depth-label in large board: MEDIUM — confirmed MiniBoard has it; ChessBoard does not; extension approach is [ASSUMED] reasonable

**Research date:** 2026-06-24
**Valid until:** 2026-07-24 (stable project; no fast-moving external deps)
