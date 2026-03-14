# Phase 9: Rework the Games List with Game Cards, Username Import, and Improved Pagination - Context

**Gathered:** 2026-03-14
**Status:** Ready for planning

<domain>
## Phase Boundary

Transform the games list from a plain HTML table to rich full-width game cards showing more metadata per game, move chess platform usernames from localStorage to backend user profile storage with a streamlined import modal, and replace the current naive pagination with truncated page numbers and a smaller page size.

</domain>

<decisions>
## Implementation Decisions

### Game card layout
- Full-width card list (vertically stacked), replacing the current `<table>` in GameTable.tsx
- Each card has a colored left border accent: green for win, gray for draw, red for loss
- Cards show all current fields plus new fields:
  - **Existing**: result badge (W/D/L), opponent username, date, time control bucket, platform link
  - **New**: user rating vs opponent rating, opening name + ECO code, color indicator (white/black), platform icon (chess.com/lichess), number of moves
- Card visual hierarchy: result + opponent prominent on first line, metadata (ratings, opening, TC, date, moves) on second line

### Move count column
- Add `move_count: Mapped[int | None]` column to the Game model
- Alembic migration to add the column
- Backfill existing games by counting moves from stored PGN
- Populate move_count at import time for new games

### GameRecord schema expansion
- Add to GameRecord (backend schema + frontend type): user_rating, opponent_rating, opening_name, opening_eco, user_color, platform, move_count
- These fields already exist on the Game model — just need to be included in the response serialization

### Username storage — backend user profile
- Add `chess_com_username: Mapped[str | None]` and `lichess_username: Mapped[str | None]` columns to the User model
- Alembic migration for the new columns
- New endpoint: GET/PUT /users/me/profile (or extend existing user endpoint)
- Whenever an import runs, the backend auto-updates the stored username for that platform — no separate "save username" step
- Remove localStorage username storage from frontend (backend is source of truth)

### Import modal redesign
- **Returning user (usernames set)**: Shows both platforms with username displayed and per-platform [Sync] buttons. One click to import — no typing needed. "Edit usernames" link to switch to input mode.
- **First-time user (no usernames)**: Shows input fields per platform (similar to current modal). After first import, username is saved and modal switches to Sync view.
- Per-platform Sync buttons only (no "Sync All" button)
- Import still runs in background with progress toast (unchanged)

### Pagination improvements
- Truncated page numbers: show first/last pages + window around current page (e.g., `< 1 2 3 ... 8 9 10 ... 48 49 50 >`)
- Page size reduced from 50 to 20 (cards are taller than table rows)
- Pagination controls at bottom of list only
- "X of Y games matched" counter stays at the top
- Page change scrolls to top of the results/cards area
- Keep offset-based pagination (no cursor-based change needed)

### Claude's Discretion
- Exact card spacing, padding, typography within the card
- Platform icon implementation (SVG, emoji, or text badge)
- Color indicator visual (circle, piece icon, or text)
- Truncated pagination window size (how many pages around current to show)
- How to handle missing data in cards (null ratings, null opening, etc.)
- Backfill strategy for move_count (migration script vs management command)
- Profile endpoint design (new router vs extending FastAPI-Users)

</decisions>

<specifics>
## Specific Ideas

- Left-accent border on cards for result color — green/gray/red, similar to the current badge style but applied as card border
- Import modal for returning users: both platforms visible at once, each with username + Sync button — no platform toggle needed
- Cards should feel scannable — key info (result, opponent, ratings) prominent, secondary info (opening, date, moves) more subdued

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `GameTable.tsx`: Current games list component — will be replaced/rewritten as GameCardList
- `WDLBar.tsx`: Result color classes (green/gray/red) — reuse same color tokens for card borders
- `ImportModal.tsx`: Current import modal — restructure to support two-mode UI (sync view vs input view)
- `useImportTrigger` hook: Import trigger mutation — reuse for Sync buttons
- `apiClient`: Axios client with auth — add profile endpoints

### Established Patterns
- TanStack Query for all server state
- shadcn/ui components (Button, Dialog, Input, ToggleGroup)
- Dark theme (Nova/Radix)
- Backend: routers/services/repositories layering
- Pydantic v2 schemas for API contracts

### Integration Points
- `Dashboard.tsx`: Replace `<GameTable>` with new `<GameCardList>` component
- `app/schemas/analysis.py`: Expand GameRecord with new fields
- `app/models/game.py`: Add move_count column
- `app/models/user.py`: Add chess_com_username, lichess_username columns
- `app/services/import_service.py`: Update username on user profile after import
- Alembic: Two migrations (move_count on games, usernames on users)

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 09-rework-the-games-list-with-game-cards-username-import-and-improved-pagination*
*Context gathered: 2026-03-14*
