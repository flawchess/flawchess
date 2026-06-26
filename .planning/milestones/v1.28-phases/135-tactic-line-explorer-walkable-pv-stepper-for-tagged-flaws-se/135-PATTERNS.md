# Phase 135: Tactic Line Explorer — Pattern Map

**Mapped:** 2026-06-24
**Files analyzed:** 11 new/modified files
**Analogs found:** 11 / 11

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `app/routers/library.py` (add route) | router | request-response | `app/routers/library.py` GET `/games/{game_id}` (line 127–169) | exact |
| `app/schemas/library.py` (add `TacticLinesResponse`) | model | request-response | `app/schemas/library.py` `FlawMarker` / `EvalPoint` | exact |
| `app/repositories/library_repository.py` (add `fetch_tactic_lines`) | repository | CRUD | `app/repositories/library_repository.py` existing `query_flaws` + `app/services/flaws_service.py:401–480` `_detect_tactic_for_flaw` | role-match |
| `frontend/src/hooks/useTacticLine.ts` (NEW) | hook | event-driven | `frontend/src/hooks/useChessGame.ts` | exact (~80% clone with divergences) |
| `frontend/src/hooks/useLibrary.ts` (add `useTacticLines`) | hook | request-response | `frontend/src/hooks/useLibrary.ts` `useLibraryGame` (line 193–218) | exact |
| `frontend/src/api/client.ts` (add `getTacticLines`) | utility | request-response | `frontend/src/api/client.ts` `libraryApi.getGame` (line 377–400) | exact |
| `frontend/src/components/library/TacticLineExplorer.tsx` (NEW) | component | event-driven | `frontend/src/components/library/FlawCard.tsx` Dialog block (line 442–477) + `frontend/src/App.tsx` `MobileMoreDrawer` (line 339–395) | role-match |
| `frontend/src/components/library/SanLadder.tsx` (NEW) | component | event-driven | `frontend/src/components/board/BoardControls.tsx` (stateless display + callbacks) | partial-match |
| `frontend/src/components/library/FlawCard.tsx` (D-04 button row) | component | event-driven | self (current `viewGameButton` pattern lines 207–218, 254) | exact |
| `frontend/src/components/results/LibraryGameCard.tsx` (D-03 Explore button) | component | event-driven | `frontend/src/components/library/FlawCard.tsx` Explore button disable+tooltip pattern | role-match |
| `frontend/src/components/board/ChessBoard.tsx` (add `id?` prop) | component | event-driven | self (existing `id: 'chessboard'` at line 306) | exact |

---

## Pattern Assignments

### `app/routers/library.py` — add `GET /flaws/{game_id}/{ply}/tactic-lines`

**Analog:** `app/routers/library.py` existing `get_library_game` (line 127–169) and `get_tactic_comparison` (line 254–300)

**Imports pattern** (lines 14–31 — already present, no new imports needed):
```python
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_async_session
from app.models.user import User
from app.users import current_active_user
```

**Route registration pattern** (relative path under `/library` prefix, line 33):
```python
router = APIRouter(prefix="/library", tags=["library"])
```

**IDOR + 404 pattern** (lines 157–169 — copy exactly):
```python
@router.get("/flaws/{game_id}/{ply}/tactic-lines", response_model=TacticLinesResponse)
async def get_tactic_lines(
    session: Annotated[AsyncSession, Depends(get_async_session)],
    user: Annotated[User, Depends(current_active_user)],
    game_id: int,  # FastAPI 422-rejects non-integer (T-112-05)
    ply: int,
) -> TacticLinesResponse:
    """PV walk for the TacticLineExplorer (Phase 135).

    Returns both orientations' SAN move lists, display depths, motif, and starting FEN.
    IDOR guard: returns 404 (not 403) when game/ply does not belong to user — never
    confirms whether the id exists for the requester (T-112-01 pattern).
    """
    result = await library_repository.fetch_tactic_lines(
        session, user_id=user.id, game_id=game_id, ply=ply
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Flaw not found")
    return result
```

---

### `app/schemas/library.py` — add `TacticLinesResponse`

**Analog:** `app/schemas/library.py` `FlawMarker` (lines 48–75) and `EvalPoint` (lines 32–45)

**Schema pattern** (lines 1–25 for existing import block, lines 32–45 for `EvalPoint` shape):
```python
from pydantic import BaseModel

class TacticLinesResponse(BaseModel):
    """PV walk data for the TacticLineExplorer (Phase 135).

    missed_moves: SAN from the decision position (flaw_ply PV). None when pv is NULL.
    allowed_moves: SAN starting with the flaw move (prepended) then opponent PV.
                   None when game_positions[ply+1].pv is NULL.
    position_fen: full FEN (with side-to-move from ply parity) for chess.js root board.
    """
    missed_moves: list[str] | None = None
    missed_depth: int | None = None        # raw 0-based loop index (DB value)
    missed_tactic_ply_index: int | None = None  # same as missed_depth; for SAN ladder highlight
    missed_motif: str | None = None
    allowed_moves: list[str] | None = None
    allowed_depth: int | None = None       # raw 0-based loop index (DB value)
    allowed_tactic_ply_index: int | None = None  # same as allowed_depth; for SAN ladder highlight
    allowed_motif: str | None = None
    position_fen: str                      # full FEN from game_flaws.fen + side-to-move
    flaw_move_san: str | None = None       # move played (game_positions[n].move_san)
    best_move_uci: str | None = None       # engine best move (game_positions[n].best_move)
    flaw_ply: int                          # real game ply (for move-number labeling in SAN ladder)
```

---

### `app/repositories/library_repository.py` — add `fetch_tactic_lines()`

**Analog:** `app/services/flaws_service.py:401–480` `_detect_tactic_for_flaw` (FEN→board construction, `_parse_pv` usage) and `app/repositories/library_repository.py` existing DB query patterns

**Constants pattern** (lines 50–78 — already in scope):
```python
# Already defined at module level — reuse:
ALLOWED_DECISION_DEPTH_OFFSET: int = 1  # line 78
_TACTIC_CHIP_CONFIDENCE_MIN: int = 70   # line 60
```

**New constants to add** (name per CLAUDE.md "no magic numbers"):
```python
PAYOFF_MAX_PLIES: int = 3  # 2–4 payoff plies past depth-0 punchline (CONTEXT.md band)
```

**PV helper pattern** (mirrors `_parse_pv` in `app/services/tactic_detector.py:241–262`):
```python
import chess
from app.services.tactic_detector import _parse_pv

def _pv_to_san_list(board: chess.Board, pv: str | None) -> list[str] | None:
    """Convert space-joined UCI PV to SAN. Returns None on absent/unparseable PV."""
    if not pv:
        return None
    try:
        boards, moves = _parse_pv(board, pv)
    except ValueError:
        return None
    return [boards[i].san(moves[i]) for i in range(len(moves))]

def _truncate_pv(sans: list[str] | None, tactic_depth_raw: int | None) -> list[str] | None:
    """Cap SAN list to tactic punchline + PAYOFF_MAX_PLIES. Handles short PVs gracefully."""
    if sans is None:
        return None
    if tactic_depth_raw is None:
        return sans[:PAYOFF_MAX_PLIES]
    return sans[: tactic_depth_raw + 1 + PAYOFF_MAX_PLIES]
```

**Board construction pattern** (from `app/services/flaws_service.py:445–446, 474–480`):
```python
# Reconstruct board from board_fen() + ply parity (same as _detect_tactic_for_flaw):
board_before = chess.Board(flaw.fen)
board_before.turn = chess.WHITE if flaw.ply % 2 == 0 else chess.BLACK

# Missed PV: walk from board_before (no flaw move pushed)
missed_sans = _pv_to_san_list(board_before.copy(), pos_n.pv if pos_n else None)

# Allowed PV: push flaw move to get board_after_flaw, prepend flaw move SAN
flaw_move = board_before.parse_san(pos_n.move_san)  # same as flaws_service.py:474
board_after_flaw = board_before.copy()
board_after_flaw.push(flaw_move)
allowed_raw = _pv_to_san_list(board_after_flaw, pos_n1.pv if pos_n1 else None)
allowed_sans = [pos_n.move_san] + allowed_raw if allowed_raw else None  # prepend flaw move

# Full FEN for frontend (chess.js needs side-to-move):
full_fen = board_before.fen()  # python-chess fen() already includes side-to-move
```

**SQLAlchemy async query pattern** (mirrors existing patterns in `library_repository.py`):
```python
from sqlalchemy import select
from app.models.game_flaw import GameFlaw
from app.models.game_position import GamePosition

# Two queries — NOT asyncio.gather (CLAUDE.md constraint: single AsyncSession)
flaw_q = await session.execute(
    select(GameFlaw).where(
        GameFlaw.user_id == user_id,
        GameFlaw.game_id == game_id,
        GameFlaw.ply == ply,
    )
)
flaw = flaw_q.scalar_one_or_none()
if flaw is None:
    return None  # caller raises 404

pos_q = await session.execute(
    select(GamePosition).where(
        GamePosition.user_id == user_id,
        GamePosition.game_id == game_id,
        GamePosition.ply.in_([ply, ply + 1]),
    )
)
positions = {p.ply: p for p in pos_q.scalars().all()}
```

---

### `frontend/src/hooks/useTacticLine.ts` (NEW)

**Analog:** `frontend/src/hooks/useChessGame.ts` (full file — ~80% reuse)

**Imports pattern** (lines 1–9 of `useChessGame.ts` — strip Zobrist/opening imports):
```typescript
import { useRef, useState, useCallback, useEffect } from 'react';
import { Chess } from 'chess.js';
import { toDisplayDepthForOrientation } from '@/lib/tacticDepth';
import type { TacticOrientation } from '@/types/library';
```

**Core `replayTo` pattern** (lines 143–160 of `useChessGame.ts` — copy with rootFen divergence):
```typescript
// Divergence from useChessGame: start from rootFen (decision position), not start position.
// chess.js new Chess(fen) accepts full FEN from backend.
const replayTo = useCallback((history: string[], ply: number) => {
  const chess = new Chess(rootFen);  // rootFen from TacticLinesResponse.position_fen
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
}, [rootFen]);
```

**goForward/goBack/goToMove pattern** (lines 205–232 of `useChessGame.ts` — copy verbatim):
```typescript
// Copy from useChessGame.ts lines 205–232; these work identically for tactic PV.
const goForward = useCallback(() => {
  setMoveHistory((prev) => {
    if (currentPly < prev.length) replayTo(prev, currentPly + 1);
    return prev;
  });
}, [currentPly, replayTo]);
```

**Keyboard pattern** (lines 263–279 of `useChessGame.ts` — scope to container, not window):
```typescript
// Divergence: attach to containerRef.current, not window, to avoid conflicts
// with page-level shortcuts when multiple boards are mounted.
useEffect(() => {
  const container = containerRef.current;
  if (!container) return;
  const handleKeyDown = (e: KeyboardEvent) => {
    if (e.key === 'ArrowLeft') { e.preventDefault(); goBack(); }
    else if (e.key === 'ArrowRight') { e.preventDefault(); goForward(); }
  };
  container.addEventListener('keydown', handleKeyDown);
  return () => container.removeEventListener('keydown', handleKeyDown);
}, [goBack, goForward]);
```

**Depth counter (new — not in useChessGame)**:
```typescript
// displayDepth: decrement from rootDisplayDepth by 1 per ply, floor at 0.
// isPayoff: past the tactic punchline move.
const rootDisplayDepth = toDisplayDepthForOrientation(tacticDepthRaw, orientation);
const displayDepth = Math.max(0, rootDisplayDepth - currentPly);
const isPayoff = currentPly > tacticDepthRaw;
```

**What to OMIT from useChessGame** (do not carry over):
- `STORAGE_KEY`, `readPersistedBoardState`, `computeInitialChessState` (no persistence)
- `computeHashes`, `ZobristHashes`, `getHashForOpenings` (no Zobrist)
- `preloadOpenings`, `findOpening`, `openingName` (no opening lookup)
- `makeMove` with free-play drag (tactic explorer is read-only)
- `MAX_EXPLORER_PLY` guard (PV is finite and pre-truncated by server)
- `window.sessionStorage` writes
- `window.addEventListener('keydown', ...)` — use containerRef instead

---

### `frontend/src/hooks/useLibrary.ts` — add `useTacticLines()`

**Analog:** `useLibraryGame` at lines 193–218 — copy the lazy-fetch pattern exactly:
```typescript
// Copy from useLibraryGame (lines 193–218), change queryKey, queryFn, enabled guard.
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
    refetchOnWindowFocus: false,  // matches useLibraryGame line 216
  });
}
```

---

### `frontend/src/api/client.ts` — add `libraryApi.getTacticLines()`

**Analog:** `libraryApi.getGame` (lines 377–400) — simple GET with path params:
```typescript
// Add to libraryApi object. Same pattern as getGame but no query params beyond path.
getTacticLines: (gameId: number, ply: number) =>
  apiClient
    .get<TacticLinesResponse>(`/library/flaws/${gameId}/${ply}/tactic-lines`)
    .then(r => r.data),
```

**Type import** — add `TacticLinesResponse` to the import from `@/types/library` (same line 16 pattern).

---

### `frontend/src/components/library/TacticLineExplorer.tsx` (NEW)

**Analog (Dialog half):** `frontend/src/components/library/FlawCard.tsx` lines 442–477

**Dialog pattern** (FlawCard.tsx lines 443–476):
```tsx
// Desktop path — copy Dialog usage from FlawCard.tsx:
<Dialog open={open} onOpenChange={(v) => !v && onOpenChange(false)}>
  <DialogContent
    data-testid="tactic-explorer-dialog"
    className="no-scrollbar max-w-[calc(100%-1rem)] sm:max-w-4xl overflow-y-auto max-h-[90vh] sm:p-6"
  >
    <DialogTitle className="text-base font-semibold">
      Explore Tactic
    </DialogTitle>
    {/* body */}
  </DialogContent>
</Dialog>
```

**Analog (Drawer half):** `frontend/src/App.tsx` `MobileMoreDrawer` (lines 339–395)

**Drawer pattern** (App.tsx lines 340–394):
```tsx
// Mobile path — copy Drawer usage from App.tsx MobileMoreDrawer:
<Drawer open={open} onOpenChange={onOpenChange} direction="bottom">
  <DrawerContent
    data-testid="tactic-explorer-drawer"
    className="w-full max-h-[95vh]"  {/* override default 80vh */}
  >
    <DrawerHeader>
      <DrawerTitle className="text-base font-semibold">Explore Tactic</DrawerTitle>
    </DrawerHeader>
    {/* body */}
  </DrawerContent>
</Drawer>
```

**useIsMobile pattern** (from `frontend/src/components/charts/ScoreChart.tsx:34–46`):
```typescript
// Define locally in TacticLineExplorer.tsx (or extract to useMobileBreakpoint.ts):
const MOBILE_BREAKPOINT_PX = 768;  // matches Tailwind `md`

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

**Arrow pattern** (from `FlawCard.tsx` lines 149–172 — `boardArrows` array shape for `ChessBoard`):
```typescript
// At root (ply 0): show both arrows simultaneously (matches miniboard convention).
// Uses uciToSquares / sanToSquares from @/lib/sanToSquares (same as FlawCard.tsx:133).
import { uciToSquares, sanToSquares } from '@/lib/sanToSquares';
import { BEST_MOVE_ARROW, TAC_MISSED_LABEL, TAC_ALLOWED_LABEL } from '@/lib/theme';
import { toDisplayDepthForOrientation } from '@/lib/tacticDepth';

const rootArrows: BoardArrow[] = [
  // missed orientation best-move (blue)
  ...(bestMoveUci ? [{ startSquare: ..., endSquare: ..., color: BEST_MOVE_ARROW,
                        width: 0.5, label: missedDepthLabel, labelColor: TAC_MISSED_LABEL }] : []),
  // allowed orientation flaw-move (red)
  ...(flawMoveSan ? [{ startSquare: ..., endSquare: ..., color: severityColor,
                        width: 0.5, label: allowedDepthLabel, labelColor: TAC_ALLOWED_LABEL }] : []),
];
```

**Missed/Allowed toggle pattern** (ghost buttons, aria-pressed — from UI-SPEC):
```tsx
// Two ghost buttons — active state via conditional className.
// Uses theme color constants, not hard-coded hex.
<div className="flex gap-2">
  <Button
    variant="ghost"
    aria-pressed={orientation === 'missed'}
    data-testid="tactic-toggle-missed"
    onClick={() => { setOrientation('missed'); reset(); }}
    className={orientation === 'missed' ? 'bg-[--toggle-active] text-[--toggle-active-foreground]' : ''}
  >
    Missed
  </Button>
  <Button
    variant="ghost"
    aria-pressed={orientation === 'allowed'}
    data-testid="tactic-toggle-allowed"
    onClick={() => { setOrientation('allowed'); reset(); }}
    className={orientation === 'allowed' ? 'bg-[--toggle-active] text-[--toggle-active-foreground]' : ''}
  >
    Allowed
  </Button>
</div>
{/* Toggle visible only when BOTH lines exist */}
```

**ChessBoard usage** (with new `id` prop — see ChessBoard pattern below):
```tsx
<ChessBoard
  id="tactic-explorer-board"       // new optional prop; default remains 'chessboard'
  position={tacticLine.position}
  onPieceDrop={() => false}        // read-only: reject all drag-drop
  flipped={flipped}
  lastMove={tacticLine.lastMove ?? undefined}
  arrows={currentArrows}
/>
```

**BoardControls infoSlot pattern** (from `BoardControls.tsx` line 13):
```tsx
<BoardControls
  onBack={tacticLine.goBack}
  onForward={tacticLine.goForward}
  onReset={tacticLine.reset}
  onFlip={() => setFlipped(f => !f)}
  canGoBack={tacticLine.canGoBack}
  canGoForward={tacticLine.canGoForward}
  size={isMobile ? 'md' : 'sm'}
  infoSlot={
    <span data-testid="tactic-depth-readout" className="text-sm font-medium">
      {tacticLine.isPayoff ? 'Payoff' : `Depth: ${tacticLine.displayDepth}`}
    </span>
  }
/>
```

---

### `frontend/src/components/library/SanLadder.tsx` (NEW)

**Analog:** `frontend/src/components/board/BoardControls.tsx` (stateless display + callback props pattern)

**Component shape pattern** (matches BoardControls.tsx lines 1–22):
```tsx
// Stateless display component — all state in useTacticLine hook, callbacks passed as props.
interface SanLadderProps {
  moves: string[];           // SAN strings from TacticLinesResponse
  currentPly: number;        // 0 = root (before first move)
  tacticPlyIndex: number;    // depth-0 punchline index (for coloring)
  orientation: 'missed' | 'allowed';
  flawPly: number;           // real game ply of flaw (for move-number labeling)
  onGoToMove: (ply: number) => void;
}
```

**Move-number computation** (from `formatMoveNotation` pattern in `FlawCard.tsx:175–177`):
```typescript
// Move numbers anchored to real game ply (not restarted at 1).
// ply 0 = root; move index i corresponds to real game ply (flawPly + i).
// Full move number = Math.ceil((flawPly + i + 1) / 2); suffix = '...' for black.
```

**Row highlighting pattern** (brand-brown left border — from UI-SPEC):
```tsx
<li
  role="listitem"
  aria-current={currentPly === i + 1 ? 'step' : undefined}
  data-testid={`tactic-san-move-${flawPly + i}`}
  onClick={() => onGoToMove(i + 1)}
  className={cn(
    'cursor-pointer px-3 py-1 text-sm rounded-sm',
    currentPly === i + 1 && 'border-l-2 border-brand-brown bg-brand-brown/10',
    i === tacticPlyIndex && orientation === 'missed' && 'text-[TAC_MISSED color]',
    i === tacticPlyIndex && orientation === 'allowed' && 'text-[TAC_ALLOWED color]',
    i > tacticPlyIndex && 'text-muted-foreground',  // payoff moves dimmed
  )}
>
  {/* move number + SAN */}
</li>
```

---

### `frontend/src/components/library/FlawCard.tsx` — D-04 button row

**Analog:** self — current `viewGameButton` (lines 207–218) and `CardHeader` usage (lines 247–255)

**Current pattern to replace** (lines 207–218, 254):
```tsx
// BEFORE: "Game" lives in CardHeader as a raw <button> with custom classNames:
const viewGameButton = (
  <button
    type="button"
    className="ml-auto shrink-0 inline-flex items-center gap-1 text-sm text-brand-brown-light ..."
    data-testid={`flaw-card-view-game-${flaw.game_id}-${flaw.ply}`}
    onClick={() => setOpen(true)}
  >
    <Swords className="h-3.5 w-3.5" /> Game
  </button>
);
// ... in CardHeader: {viewGameButton}
```

**New button row pattern** (per CLAUDE.md "secondary = `brand-outline`"):
```tsx
// AFTER: dedicated button row below card body; both buttons use shadcn Button.
// Tagged = missed_tactic_motif != null || allowed_tactic_motif != null (line 372 gate).
const isTagged = flaw.missed_tactic_motif != null || flaw.allowed_tactic_motif != null;

const buttonRow = (
  <div className="flex gap-2 mt-2 px-3 pb-3">
    {isTagged && (
      <Button
        variant="brand-outline"
        size="sm"
        data-testid="flaw-btn-explore"
        onClick={() => setExploreOpen(true)}
      >
        <Telescope className="h-3.5 w-3.5 mr-1" /> Explore
      </Button>
    )}
    <Button
      variant="brand-outline"
      size="sm"
      data-testid="flaw-btn-game"
      onClick={() => setOpen(true)}
    >
      <Swords className="h-3.5 w-3.5 mr-1" /> Game
    </Button>
  </div>
);
// Apply to BOTH sm:hidden and hidden sm:flex sections (CLAUDE.md mobile parity rule).
```

**State addition** (alongside existing `const [open, setOpen]`):
```typescript
const [exploreOpen, setExploreOpen] = useState(false);
```

---

### `frontend/src/components/results/LibraryGameCard.tsx` — D-03 Explore button

**Analog:** `frontend/src/components/library/FlawCard.tsx` `viewGameButton` disabled-state + `Tooltip` pattern (lines 207–218 for structure, UI-SPEC D-02 for disabled tooltip)

**Disabled button + Tooltip pattern** (matches UI-SPEC and existing `Tooltip` usage in FlawCard.tsx):
```tsx
import { Tooltip } from '@/components/ui/tooltip';
import { Button } from '@/components/ui/button';

// selectedFlaw = the flaw_markers entry for the currently-parked eval-chart ply.
const isTaggedFlaw =
  selectedFlaw != null &&
  (selectedFlaw.missed_tactic_motif != null || selectedFlaw.allowed_tactic_motif != null) &&
  selectedFlaw.is_user;  // user's flaw only

const exploreButton = (
  <Tooltip
    content={isTaggedFlaw ? undefined : 'Select a tagged flaw to explore'}
    disabled={isTaggedFlaw}  // only show tooltip when disabled
  >
    <Button
      variant="brand-outline"
      size="sm"
      data-testid="game-card-btn-explore"
      aria-label={isTaggedFlaw ? 'Explore tactic' : 'Select a tagged flaw to explore'}
      disabled={!isTaggedFlaw}
      onClick={() => selectedFlaw && setExploreOpen(true)}
    >
      <Telescope className="h-3.5 w-3.5 mr-1" /> Explore
    </Button>
  </Tooltip>
);
// Place below eval chart, adjacent to flaw-marker navigation (D-03).
// Apply to both mobile and desktop sections (CLAUDE.md mobile parity).
```

---

### `frontend/src/components/board/ChessBoard.tsx` — add optional `id?` prop

**Analog:** self — current hardcoded `id: 'chessboard'` at line 306

**Current pattern** (line 306 area):
```tsx
// BEFORE: hardcoded inside ChessBoardProps-to-Chessboard mapping:
customBoardId: 'chessboard'  // or id: 'chessboard' depending on react-chessboard v5 API
```

**New pattern** (minimal prop addition, default preserves existing behavior):
```tsx
// Add to ChessBoardProps interface (line 32 area):
interface ChessBoardProps {
  // ... existing props ...
  /** Board id for square testid generation. Defaults to 'chessboard'. */
  id?: string;
}

// In render (line 306 area):
customBoardId: id ?? 'chessboard'
```

---

## Shared Patterns

### Authentication / Current User
**Source:** `app/routers/library.py` lines 14–31 (imports) and all route signatures
**Apply to:** new `GET /flaws/{game_id}/{ply}/tactic-lines` route
```python
user: Annotated[User, Depends(current_active_user)]
# user.id is the ONLY source of user identity — never a query param (IDOR prevention)
```

### IDOR Guard (404 not 403)
**Source:** `app/routers/library.py` lines 157–169 (`get_library_game`)
**Apply to:** new tactic-lines route — return `None` from repository → raise `HTTPException(status_code=404)`
```python
if result is None:
    raise HTTPException(status_code=404, detail="Flaw not found")
```

### TanStack Query staleTime + refetchOnWindowFocus
**Source:** `frontend/src/hooks/useLibrary.ts` lines 193–218 (`useLibraryGame`)
**Apply to:** `useTacticLines` hook
```typescript
staleTime: LIBRARY_STALE_TIME,   // 5 * 60 * 1000
refetchOnWindowFocus: false,
```

### Secondary Button Variant
**Source:** `frontend/src/components/ui/button.tsx` `variant="brand-outline"`
**Apply to:** Explore button (flaw card, game card), Game button (flaw card)
```tsx
// NEVER hand-roll: className="bg-... text-..." on buttons
// ALWAYS: variant="brand-outline" for secondary actions
<Button variant="brand-outline" size="sm">Label</Button>
```

### Sentry: No capture on expected failures, capture on unexpected
**Source:** `app/services/flaws_service.py` existing patterns + CLAUDE.md
**Apply to:** `fetch_tactic_lines()` in `library_repository.py`
```python
# ValueError from _parse_pv (bad UCI) → return None gracefully, do NOT capture_exception
# Unexpected exceptions propagate to top-level handler
```

### data-testid on all interactive elements
**Source:** CLAUDE.md browser automation rules + UI-SPEC §Data-TestID Reference
**Apply to:** all new frontend components
```
flaw-btn-explore, flaw-btn-game, game-card-btn-explore,
tactic-explorer-dialog, tactic-explorer-drawer, tactic-explorer-board,
tactic-toggle-missed, tactic-toggle-allowed,
tactic-san-ladder, tactic-san-move-{ply}, tactic-depth-readout
```

### isError branch in data-loading chains
**Source:** CLAUDE.md frontend rules "Always handle `isError`"
**Apply to:** `TacticLineExplorer.tsx` when `useTacticLines` returns `isError`
```tsx
if (isError) return <p className="text-sm text-muted-foreground">Failed to load tactic line. Please try again.</p>;
```

---

## No Analog Found

All files have analogs in the codebase. No novel patterns needed.

---

## Metadata

**Analog search scope:** `app/routers/`, `app/services/`, `app/repositories/`, `app/schemas/`, `frontend/src/hooks/`, `frontend/src/components/board/`, `frontend/src/components/library/`, `frontend/src/api/`, `frontend/src/App.tsx`
**Files scanned:** 14 source files read in full or in targeted sections
**Pattern extraction date:** 2026-06-24
