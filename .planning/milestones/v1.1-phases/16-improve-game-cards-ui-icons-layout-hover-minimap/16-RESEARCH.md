# Phase 16: Improve Game Cards UI — Icons, Layout, Hover Minimap - Research

**Researched:** 2026-03-18
**Domain:** React frontend UI (card layout, lucide-react icons, Radix tooltip, MiniBoard) + Python backend (SQLAlchemy model, import pipeline)
**Confidence:** HIGH — all key decisions verified directly against existing codebase; no external unknowns

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Card layout — 3-row structure**
- Row 1: Result badge (W/D/L) + player names with ratings (white vs black) + platform icon + external link
- Row 2: Opening name only (full width, no ECO code) — gives the opening maximum horizontal space
- Row 3: Metadata with icons — time control, date, termination, move count — separated by dot/space
- Player names in regular font weight (not bold) for both user and opponent — the result badge and left border color already indicate outcome
- Keep the existing 4px color-coded left border (green/gray/red)

**Icons for metadata (row 3)**
- Icons for ALL metadata items on row 3: Clock (time control), Calendar (date), Flag/swords (termination), Hash (move count)
- BookOpen before opening name on row 2
- Icons should be subtle (text-muted-foreground, same size as text-xs) — informative, not distracting

**Null field handling**
- If `time_control_seconds` IS NULL (daily games on chess.com), omit the time control entirely — no "NaN" display
- If `time_control_str` is null but `time_control_bucket` exists, show just the bucket (e.g. "Classical")
- If opening name is null, show "Unknown Opening" in muted text
- If date is null, omit the date item entirely
- General rule: omit metadata items with null values rather than showing placeholders

**Hover minimap — end position**
- Desktop: Hover tooltip showing a MiniBoard (120px) with the game's final position
- Mobile: Tap the card to expand and show the minimap inline below the metadata row. Only one card expanded at a time.
- Board oriented from the user's perspective (flipped when `user_color` is black)
- Rendered on-demand (hover/tap) — NOT pre-rendered for all cards on the page
- Reuse existing `MiniBoard` component from `components/board/MiniBoard.tsx`

**Backend — result_fen at import time**
- Add `result_fen` column to the `games` table (nullable VARCHAR, stores piece-placement FEN like `board_fen()`)
- Compute during import: grab `board.board_fen()` at the end of the replay loop in `hashes_for_game()`
- Include `result_fen` in the `GameRecord` API response schema
- DB wipe accepted — no migration needed, reimport populates the column

### Claude's Discretion
- Exact icon choices from lucide-react (e.g. `Swords` vs `Flag` for termination)
- Tooltip positioning logic (above/below card based on viewport)
- Exact spacing and gap values between rows
- Mobile tap-to-expand animation (if any)
- Whether to use the existing board/MiniBoard.tsx or position-bookmarks/MiniBoard.tsx (or consolidate)

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope
</user_constraints>

---

## Summary

Phase 16 is a focused UI enhancement with a lightweight backend component. The frontend work restructures `GameCard.tsx` from 2 rows to 3 rows, adds lucide-react icons to metadata, and introduces a hover/tap minimap using the existing `MiniBoard` component and the project's `Tooltip`/`TooltipContent` infrastructure (already used in `MoveExplorer.tsx`). The backend work adds a `result_fen` nullable VARCHAR column to the `games` table, computes it for free inside the existing `hashes_for_game()` PGN replay loop, and threads it through `GameRecord` schema and `analysis_repository`.

All dependencies are already in the project. `lucide-react 0.577.0` is installed and all required icons (`Clock`, `Calendar`, `Flag`, `Swords`, `Hash`, `BookOpen`) are confirmed present. The Radix UI tooltip system (`@/components/ui/tooltip.tsx`) is already wired up and used in `MoveExplorer`. The `board/MiniBoard.tsx` component accepts `fen`, `size`, and `flipped` props and works immediately.

**Primary recommendation:** Implement backend first (model + schema + import pipeline), then rebuild `GameCard.tsx` in a single focused task. The backend is a DB wipe + reimport so changes are clean with no migration path needed.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| lucide-react | 0.577.0 | Icon components | Already installed; used throughout app |
| @radix-ui/react-tooltip (via shadcn `tooltip.tsx`) | installed | Hover tooltip primitive | Already wrapped in `components/ui/tooltip.tsx` |
| react-chessboard | 5.x | MiniBoard rendering | Already used in existing MiniBoard components |
| SQLAlchemy 2.x async | installed | ORM — add `result_fen` column | Project ORM standard |

### Icon Choices (Claude's Discretion — recommendation)
| Metadata Item | Recommended Icon | Rationale |
|---------------|-----------------|-----------|
| Time control | `Clock` | Universally recognized for time |
| Date | `Calendar` | Standard date icon |
| Termination | `Swords` | Chess-specific, clearer than Flag |
| Move count | `Hash` | Commonly used for counts/numbers |
| Opening name | `BookOpen` | Opening "book" — semantic match |

All five are confirmed present in lucide-react 0.577.0.

**No new packages required.**

---

## Architecture Patterns

### Recommended Project Structure
No new directories needed. Changes touch:
```
app/
├── models/game.py            # Add result_fen column
├── schemas/analysis.py       # Add result_fen to GameRecord
├── services/zobrist.py       # Return result_fen from hashes_for_game()
├── services/import_service.py # Pass result_fen to game dict
└── repositories/
    └── analysis_repository.py  # Include result_fen in query columns

frontend/src/
├── types/api.ts              # Add result_fen: string | null to GameRecord
└── components/results/
    └── GameCard.tsx          # Full rebuild: 3 rows + icons + minimap
```

### Pattern 1: result_fen extraction in hashes_for_game()
**What:** After the existing move replay loop in `hashes_for_game()`, `board` is already at the final position. Call `board.board_fen()` once and return it as an additional value.
**When to use:** Import time only — avoids the expensive `_fetch_result_fens()` PGN replay at query time.
**Current signature:**
```python
def hashes_for_game(pgn_text: str) -> list[tuple[int, int, int, int, str | None, float | None]]:
```
**New return:** Add `result_fen: str | None` as a separate return value (NOT added to each tuple — the FEN is per-game, not per-ply). Options:
- Return `(hash_tuples, result_fen)` as a 2-tuple
- Or add a separate `result_fen_for_game(pgn_text)` helper

The cleanest approach: return `(list_of_tuples, result_fen: str | None)` from `hashes_for_game()`. This keeps all PGN replay in one place and avoids a second parse.

**Example:**
```python
# At end of hashes_for_game(), after the loop:
result_fen: str | None = board.board_fen() if nodes else None
return results, result_fen
```

Callers (`import_service.py`) unpack as:
```python
hash_tuples, result_fen = hashes_for_game(pgn)
```

### Pattern 2: 3-row GameCard with inline icons
**What:** Each metadata item is an `<span>` with an icon (h-3 w-3 inline, text-muted-foreground) followed by the text value. Items are conditionally rendered — omit entirely when null.
**When to use:** Row 3 of the card only. Row 2 uses the same pattern for the opening name.

```tsx
// Source: existing GameCard.tsx + MoveExplorer.tsx Tooltip pattern
{game.time_control_bucket && (
  <span className="inline-flex items-center gap-1" data-testid={`game-card-tc-${game.game_id}`}>
    <Clock className="h-3 w-3 text-muted-foreground" />
    {formatTimeControl(game)}
  </span>
)}
```

Null guard pattern (already used in current GameCard, extend):
```tsx
// time_control: omit entirely if time_control_seconds IS NULL (daily games)
// Use time_control_str null as the signal (already null for daily games)
const showTimeControl = game.time_control_bucket !== null;
// Note: time_control_str being null means daily — show bucket only
```

### Pattern 3: Hover minimap via Radix Tooltip
**What:** Wrap the entire card in `<Tooltip>` with `<TooltipTrigger asChild>`. `TooltipContent` renders `<MiniBoard>` at 120px.
**When to use:** Desktop (non-touch). The tooltip auto-dismisses on mouse leave.

```tsx
// Source: MoveExplorer.tsx (existing Tooltip pattern in this codebase)
<TooltipProvider>
  <Tooltip>
    <TooltipTrigger asChild>
      <div data-testid={`game-card-${game.game_id}`} className={...}>
        {/* card content */}
      </div>
    </TooltipTrigger>
    {game.result_fen && (
      <TooltipContent side="right" sideOffset={8} className="p-1 bg-card border border-border">
        <MiniBoard fen={game.result_fen} size={120} flipped={game.user_color === 'black'} />
      </TooltipContent>
    )}
  </Tooltip>
</TooltipProvider>
```

**Important:** `TooltipContent` uses `TooltipPrimitive.Portal` — it renders outside the card DOM tree, so overflow clipping on the card list does not affect it.

### Pattern 4: Mobile tap-to-expand minimap
**What:** Track `expandedGameId: number | null` state in `GameCardList` (one expanded at a time). Each `GameCard` receives an `isExpanded` prop and an `onToggle` callback. On tap, render `<MiniBoard>` inline below the metadata row.

**State location:** `GameCardList` (not OpeningsPage) — expansion is local UI state for the games list.

```tsx
// In GameCardList.tsx
const [expandedGameId, setExpandedGameId] = useState<number | null>(null);

const handleToggle = (gameId: number) => {
  setExpandedGameId(prev => prev === gameId ? null : gameId);
};
```

```tsx
// In GameCard.tsx — mobile expand section
{isExpanded && game.result_fen && (
  <div className="mt-2 flex justify-center sm:hidden" data-testid={`game-card-minimap-${game.game_id}`}>
    <MiniBoard fen={game.result_fen} size={120} flipped={game.user_color === 'black'} />
  </div>
)}
```

The card itself needs `onClick` on mobile. Use `sm:hidden` / `hidden sm:block` to separate mobile/desktop rendering: tooltip only on desktop (pointer devices), inline expand only on mobile.

**Making the card clickable on mobile without breaking the external link:** Make the whole card `<div>` have `onClick={onToggle}` but add `e.stopPropagation()` on the external link `<a>` tag.

### MiniBoard component decision
Use `components/board/MiniBoard.tsx` (120px default). The `position-bookmarks/MiniBoard.tsx` variant (80px default) is narrower and carries `data-testid="mini-board"` — it's semantically the same component. Recommend consolidating into one component in `components/board/MiniBoard.tsx` during this phase by adding `data-testid` support. The 60px size in PositionBookmarkCard would then pass `size={60}`.

### Anti-Patterns to Avoid
- **Pre-rendering all MiniBoardss:** Do NOT render MiniBoard for every card on page load. Radix Tooltip is lazy by default (only mounts content when open). The mobile expand pattern is also on-demand. This was the issue that caused slowness in bookmark cards per CONTEXT.md.
- **Using `board.fen()` instead of `board.board_fen()`:** `board.fen()` includes castling rights and en passant — use `board.board_fen()` for piece-placement-only FEN per CLAUDE.md constraint.
- **Showing "NaN" for daily games:** Daily chess.com games have `time_control_str = null`. The existing `formatTimeControl()` would produce NaN if called on null. Guard: only render time control item if `time_control_bucket` is non-null AND apply null check on `time_control_str` inside the formatter.
- **ECO code on row 2:** Locked decision says "no ECO code" on row 2. Current `formatOpening()` prepends ECO — replace with opening name only.
- **TooltipContent default styling:** The default `TooltipContent` className uses `bg-foreground text-background` (dark background for text tooltips). Override with `bg-card border border-border p-1` for the MiniBoard tooltip to match the card aesthetic.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Hover tooltip | Custom CSS `:hover` + absolute positioning | Radix Tooltip (`components/ui/tooltip.tsx`) | Already wrapped; handles focus, keyboard, portal, z-index, viewport edge detection automatically |
| Icon SVGs | Inline SVG strings | lucide-react | Already installed; tree-shakeable; consistent sizing API |
| Board rendering | Custom SVG/canvas chess board | `board/MiniBoard.tsx` (wraps react-chessboard) | Already works, correct piece images, orientation support |

---

## Common Pitfalls

### Pitfall 1: TooltipProvider nesting
**What goes wrong:** Each `<Tooltip>` requires a `<TooltipProvider>` ancestor. Wrapping each card individually in `TooltipProvider` works but is wasteful. Wrapping the whole `GameCardList` in one `TooltipProvider` is cleaner.
**Why it happens:** Radix requires the Provider for context.
**How to avoid:** Place a single `<TooltipProvider>` in `GameCardList` wrapping the card stack. The existing `MoveExplorer.tsx` wraps each icon individually — acceptable at small scale but `GameCardList` renders up to 50 cards.
**Warning signs:** React context warnings, tooltip not appearing.

### Pitfall 2: hashes_for_game() signature change breaks tests
**What goes wrong:** Changing the return type of `hashes_for_game()` from `list[tuple]` to `tuple[list[tuple], str | None]` breaks `test_zobrist.py` which calls the function directly.
**Why it happens:** 28 test cases reference the current return format.
**How to avoid:** Update `test_zobrist.py` alongside the function change. All tests that call `hashes_for_game()` need to unpack the new 2-tuple. Test updates are mechanical.
**Warning signs:** `ValueError: too many values to unpack` in import_service.py or test failures.

### Pitfall 3: result_fen column not in analysis_repository select
**What goes wrong:** `query_matching_games()` returns `Game` ORM objects — SQLAlchemy loads all mapped columns by default. So adding `result_fen` to the `Game` model is sufficient; no query change needed for the ORM path.
**Why it happens:** The existing `query_matching_games` returns `result.scalars().all()` (full ORM objects).
**How to avoid:** Just add the column to `Game` model and `GameRecord` schema. The ORM loads it automatically.

### Pitfall 4: Mobile tap event bubbling
**What goes wrong:** Tapping the external link icon on mobile also triggers card expand/collapse.
**Why it happens:** `onClick` on the card `<div>` captures bubbled events from child elements.
**How to avoid:** Add `onClick={(e) => e.stopPropagation()}` to the external link `<a>` element in row 1.

### Pitfall 5: Tooltip not showing when card has no result_fen
**What goes wrong:** `<Tooltip>` renders with no visible content when `result_fen` is null (freshly wiped DB during development, or games without PGN).
**Why it happens:** Tooltip always renders trigger, content is conditionally null.
**How to avoid:** Only wrap in `<Tooltip>` when `game.result_fen` is non-null. When null, render the card as a plain `<div>` without tooltip wrapper. Or use `disableHoverableContent` prop to prevent empty tooltip flash.

---

## Code Examples

### Backend: result_fen in hashes_for_game()
```python
# Modified signature — returns (hash_tuples, result_fen)
def hashes_for_game(pgn_text: str) -> tuple[
    list[tuple[int, int, int, int, str | None, float | None]],
    str | None
]:
    # ... existing parsing ...
    if game is None or not nodes:
        return [], None

    # ... existing loop ...
    board.push(node.move)

    # Final position: no move is played from here
    wh, bh, fh = compute_hashes(board)
    results.append((len(nodes), wh, bh, fh, None, None))
    result_fen = board.board_fen()  # piece-placement only, per CLAUDE.md

    return results, result_fen
```

### Backend: Game model column
```python
# app/models/game.py — add after move_count
result_fen: Mapped[str | None] = mapped_column(String(100), nullable=True)
```

### Backend: GameRecord schema
```python
# app/schemas/analysis.py
class GameRecord(BaseModel):
    ...
    result_fen: str | None = None
```

### Backend: import_service.py usage
```python
# In _flush_batch, replace:
hash_tuples = hashes_for_game(pgn)
# With:
hash_tuples, result_fen = hashes_for_game(pgn)

# Then update the game with result_fen:
await session.execute(
    sa_update(Game).where(Game.id == game_id).values(
        move_count=move_count,
        result_fen=result_fen,
    )
)
```

### Frontend: GameRecord type
```typescript
// frontend/src/types/api.ts
export interface GameRecord {
  ...
  result_fen: string | null;
}
```

### Frontend: Tooltip wrapper in GameCardList
```tsx
// GameCardList.tsx — wrap card stack section
<TooltipProvider>
  <div className="flex flex-col gap-2">
    {games.map((game) => (
      <GameCard
        key={game.game_id}
        game={game}
        isExpanded={expandedGameId === game.game_id}
        onToggle={() => setExpandedGameId(
          expandedGameId === game.game_id ? null : game.game_id
        )}
      />
    ))}
  </div>
</TooltipProvider>
```

---

## State of the Art

| Old Approach | Current Approach | Impact |
|--------------|------------------|--------|
| result_fen computed at query time via `_fetch_result_fens()` (for next-moves) | result_fen stored at import time in `games.result_fen` | Eliminates PGN replay on every games tab load; FEN instantly available in GameRecord |
| 2-row card (all metadata crowded on row 2) | 3-row card (opening gets its own row) | More readable for long opening names like "Sicilian Defense: Najdorf Variation" |
| No end-position preview | Hover minimap (desktop) / tap-expand (mobile) | Quick visual reference without leaving the page |

---

## Open Questions

1. **MiniBoard consolidation**
   - What we know: Two nearly identical `MiniBoard` components exist (`board/MiniBoard.tsx` at 120px default, `position-bookmarks/MiniBoard.tsx` at 80px default with `data-testid`)
   - What's unclear: Whether consolidating in this phase is worth the risk of touching PositionBookmarkCard
   - Recommendation: Consolidate in this phase — it's a trivial prop addition. Add `data-testid` prop to `board/MiniBoard.tsx`, update `position-bookmarks/MiniBoard.tsx` to re-export or alias. Low risk, cleaner codebase.

2. **Tooltip side preference (viewport-aware)**
   - What we know: Radix `TooltipContent` has `side` prop (`"top" | "bottom" | "left" | "right"`) and auto-flips when it would overflow the viewport
   - What's unclear: Whether `side="right"` works well in the narrow Openings panel layout
   - Recommendation: Use `side="top"` as default — cards stack vertically, popping above avoids overlap with adjacent cards. Radix handles viewport collision automatically.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (backend), no frontend test framework found |
| Config file | `pytest.ini` or `pyproject.toml` (backend) |
| Quick run command | `uv run pytest tests/test_zobrist.py -x` |
| Full suite command | `uv run pytest` |

### Phase Requirements → Test Map
| Area | Behavior | Test Type | Automated Command | File Exists? |
|------|----------|-----------|-------------------|-------------|
| hashes_for_game() signature | Returns (tuples, result_fen) 2-tuple; result_fen is board_fen() of final position | unit | `uv run pytest tests/test_zobrist.py -x` | ✅ needs update |
| import_service result_fen | result_fen stored on Game after import | unit | `uv run pytest tests/test_import_service.py -x` | ✅ needs update |
| GameRecord schema | result_fen field present in API response | unit | `uv run pytest tests/test_analysis_service.py -x` | ✅ may need update |
| Null field handling | time_control null → item omitted; opening null → "Unknown Opening" | manual/visual | — | ❌ no frontend tests |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_zobrist.py tests/test_import_service.py -x`
- **Per wave merge:** `uv run pytest`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_zobrist.py` — update existing tests for new 2-tuple return from `hashes_for_game()`
- [ ] `tests/test_import_service.py` — verify `result_fen` is passed to `sa_update()` call

---

## Sources

### Primary (HIGH confidence)
- Direct code reading: `frontend/src/components/results/GameCard.tsx` — current implementation, all formatting functions
- Direct code reading: `frontend/src/components/board/MiniBoard.tsx` — props interface, confirmed size/flipped support
- Direct code reading: `frontend/src/components/ui/tooltip.tsx` — Radix UI wrapper, portal rendering confirmed
- Direct code reading: `frontend/src/components/move-explorer/MoveExplorer.tsx` — existing `TooltipProvider` usage pattern
- Direct code reading: `app/services/zobrist.py` — `hashes_for_game()` current return shape, board state after loop
- Direct code reading: `app/models/game.py` — existing columns, nullable pattern for new column
- Direct code reading: `app/schemas/analysis.py` — `GameRecord` schema, `result_fen` already in `NextMoveEntry`
- Direct code reading: `app/repositories/game_repository.py` — bulk_insert_games, sa_update usage in import_service
- Runtime verification: `lucide-react@0.577.0` installed; `Clock`, `Calendar`, `Flag`, `Swords`, `Hash`, `BookOpen`, `Timer`, `Trophy` all confirmed present via `node -e` check

### Secondary (MEDIUM confidence)
- Radix UI tooltip positioning: auto-flip on viewport collision is standard Radix behavior (consistent with v1.x docs pattern used throughout project)

---

## Metadata

**Confidence breakdown:**
- Backend changes (model, schema, import pipeline): HIGH — all files read, exact change sites identified
- Frontend card layout: HIGH — existing component fully read, all Tailwind classes understood
- Tooltip hover pattern: HIGH — verified existing usage in MoveExplorer, component API confirmed
- Mobile tap-expand: HIGH — useState pattern is standard React, `sm:hidden` breakpoint established in codebase
- Icon availability: HIGH — runtime verification against installed package

**Research date:** 2026-03-18
**Valid until:** 2026-04-18 (stable dependencies, no fast-moving parts)
