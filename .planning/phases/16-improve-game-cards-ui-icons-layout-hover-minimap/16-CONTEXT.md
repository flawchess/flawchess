# Phase 16: Improve Game Cards UI — Icons, Layout, Hover Minimap - Context

**Gathered:** 2026-03-18
**Status:** Ready for planning

<domain>
## Phase Boundary

Improve the visual presentation of game cards in the Games tab: restructure the card layout to 3 rows with icons for metadata, handle null fields gracefully (no NaN), and add a hover minimap showing the end-state of each game. Requires a backend change to store `result_fen` at import time and include it in the API response.

</domain>

<decisions>
## Implementation Decisions

### Card layout — 3-row structure
- **Row 1:** Result badge (W/D/L) + player names with ratings (white ● vs black ○) + platform icon + external link
- **Row 2:** Opening name only (full width, no ECO code) — gives the opening maximum horizontal space
- **Row 3:** Metadata with icons — time control, date, termination, move count — separated by dot/space
- Player names in regular font weight (not bold) for both user and opponent — the result badge and left border color already indicate outcome
- Keep the existing 4px color-coded left border (green/gray/red)

### Icons for metadata (row 3)
- Icons for ALL metadata items on row 3:
  - Clock icon (`Clock` from lucide-react) before time control (e.g. "Blitz 3+0")
  - Calendar icon (`Calendar`) before date
  - Flag/swords icon for termination (e.g. "Resignation")
  - Hash icon for move count
- Book icon (`BookOpen`) before the opening name on row 2
- Icons should be subtle (text-muted-foreground, same size as text-xs) — informative, not distracting

### Null field handling
- If `time_control_seconds` IS NULL (daily games on chess.com), omit the time control entirely — no "NaN" display
- If `time_control_str` is null but `time_control_bucket` exists, show just the bucket (e.g. "Classical")
- If opening name is null, show "Unknown Opening" in muted text
- If date is null, omit the date item entirely
- General rule: omit metadata items with null values rather than showing placeholders

### Hover minimap — end position
- **Desktop:** Hover tooltip showing a MiniBoard (120px) with the game's final position
- **Mobile:** Tap the card to expand and show the minimap inline below the metadata row. Only one card expanded at a time.
- Board oriented from the user's perspective (flipped when `user_color` is black)
- Rendered on-demand (hover/tap) — NOT pre-rendered for all cards on the page to avoid performance issues
- Reuse existing `MiniBoard` component from `components/board/MiniBoard.tsx`

### Backend — result_fen at import time
- Add `result_fen` column to the `games` table (nullable VARCHAR, stores piece-placement FEN like `board_fen()`)
- Compute during import: the import pipeline already replays every move in `hashes_for_game()` — grab `board.board_fen()` at the end of the replay loop (essentially free)
- Include `result_fen` in the `GameRecord` API response schema
- DB wipe accepted — no migration needed, reimport populates the column

### Claude's Discretion
- Exact icon choices from lucide-react (e.g. `Swords` vs `Flag` for termination)
- Tooltip positioning logic (above/below card based on viewport)
- Exact spacing and gap values between rows
- Mobile tap-to-expand animation (if any)
- Whether to use the existing board/MiniBoard.tsx or position-bookmarks/MiniBoard.tsx (or consolidate)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Frontend — game cards
- `frontend/src/components/results/GameCard.tsx` — Current 2-row card layout, formatting functions, result badge styling
- `frontend/src/components/results/GameCardList.tsx` — Card list with pagination, scroll behavior
- `frontend/src/types/api.ts` — GameRecord interface (add result_fen field)

### Frontend — minimap
- `frontend/src/components/board/MiniBoard.tsx` — 120px read-only board component using react-chessboard
- `frontend/src/components/position-bookmarks/MiniBoard.tsx` — 80px variant used in bookmark cards
- `frontend/src/components/position-bookmarks/PositionBookmarkCard.tsx` — Example of MiniBoard usage in a card

### Backend — import pipeline
- `app/services/zobrist.py` — `hashes_for_game()` — replays PGN moves, add result_fen extraction here
- `app/services/import_service.py` — Import orchestrator, passes result_fen to game record storage
- `app/models/game.py` — Game model (add result_fen column)
- `app/schemas/analysis.py` — GameRecord schema (add result_fen to response)

### Backend — analysis API
- `app/repositories/analysis_repository.py` — Query that builds GameRecord results (include result_fen)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `MiniBoard` (board/MiniBoard.tsx): 120px read-only chessboard, accepts `fen`, `size`, `flipped` props — direct reuse for hover tooltip
- `lucide-react` v0.577.0: icon library already used throughout app (ExternalLink, Bookmark, Filter, etc.)
- `PlatformIcon` component: custom SVG chess.com/lichess icons already used in GameCard row 1
- `formatTimeControl()`, `formatDate()`, `formatOpening()` — existing formatting functions in GameCard.tsx

### Established Patterns
- Game cards use `border-l-4` with result-based colors (green/gray/red)
- Result badge: small colored pill with W/D/L text
- `data-testid` convention: `game-card-{game_id}`, `game-card-tc-{game_id}`, etc.
- Tailwind dark theme: `bg-card`, `text-muted-foreground`, `border-border`

### Integration Points
- `GameRecord` type in `frontend/src/types/api.ts` — must add `result_fen: string | null`
- `GameRecord` schema in `app/schemas/analysis.py` — must add `result_fen` field
- `hashes_for_game()` in zobrist.py — extract final board FEN at end of move replay loop
- Game model in `app/models/game.py` — add `result_fen` column

</code_context>

<specifics>
## Specific Ideas

- The 3-row layout should feel less cramped than the current 2-row design — opening names like "Sicilian Defense: Najdorf Variation" need room to breathe
- Icons should be the same visual weight as the text-xs metadata — not larger or bolder
- The hover minimap should appear quickly (no loading spinner needed since FEN is already in the response data)
- Performance is a concern: bookmark cards with inline minimaps slowed down the collapsible — the hover/tap-on-demand approach avoids this

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 16-improve-game-cards-ui-icons-layout-hover-minimap*
*Context gathered: 2026-03-18*
