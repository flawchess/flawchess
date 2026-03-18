---
phase: 16-improve-game-cards-ui-icons-layout-hover-minimap
verified: 2026-03-18T22:30:00Z
status: human_needed
score: 9/9 must-haves verified
re_verification:
  previous_status: gaps_found
  previous_score: 8/9
  gaps_closed:
    - "DB migration for result_fen column (20260318_212045_f3c8c11c64c9_add_result_fen_to_games.py)"
  gaps_remaining: []
  regressions: []
human_verification:
  - test: "Hover over a game card on desktop"
    expected: "120px MiniBoard tooltip appears showing the final board position, oriented correctly (flipped when user played as black)"
    why_human: "Radix tooltip rendering and board orientation cannot be verified programmatically"
  - test: "Tap a game card on mobile (or narrow viewport)"
    expected: "MiniBoard appears inline below the metadata row; tapping a second card collapses the first; tapping an open card collapses it"
    why_human: "Mobile expand/collapse behavior, single-at-a-time state, and touch interaction cannot be verified programmatically"
  - test: "View cards for daily chess.com games (which have no time control or date)"
    expected: "No NaN, no dash placeholder — the Clock and Calendar metadata items are simply absent"
    why_human: "Requires live data with null time_control_bucket and played_at values"
---

# Phase 16: Game Card UI Improvements — Verification Report

**Phase Goal:** Restructure game cards to a 3-row layout with lucide-react icons for metadata, null-safe rendering, and an on-demand hover/tap minimap showing the game's final position.
**Verified:** 2026-03-18T22:30:00Z
**Status:** HUMAN NEEDED (all automated checks pass; 3 items require browser testing)
**Re-verification:** Yes — after gap closure (previous status: gaps_found, score: 8/9)

---

## Re-verification Summary

The single gap from the initial verification has been closed:

- **Gap closed:** Alembic migration `20260318_212045_f3c8c11c64c9_add_result_fen_to_games.py` was generated and committed. It contains `op.add_column('games', sa.Column('result_fen', sa.String(length=100), nullable=True))` — exactly matching the model column definition. The `down_revision` correctly chains from `6dc12353580e` (the previous head).

No regressions detected in previously-passing artifacts.

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `hashes_for_game()` returns `(hash_tuples, result_fen)` 2-tuple | VERIFIED | `zobrist.py`: return type annotation is `tuple[list[...], str \| None]`; `result_fen = board.board_fen()` then `return results, result_fen` |
| 2 | Game model has a nullable `result_fen` VARCHAR column | VERIFIED | `app/models/game.py` line 57: `result_fen: Mapped[str \| None] = mapped_column(String(100), nullable=True)` |
| 3 | DB migration exists for `result_fen` | VERIFIED | `alembic/versions/20260318_212045_f3c8c11c64c9_add_result_fen_to_games.py`: `op.add_column('games', sa.Column('result_fen', sa.String(length=100), nullable=True))` |
| 4 | Import pipeline stores `result_fen` on the Game row | VERIFIED | `import_service.py`: `hash_tuples, result_fen = hashes_for_game(pgn)`; `sa_update(...).values(..., result_fen=result_fen)` |
| 5 | `GameRecord` API schema includes `result_fen` (backend and frontend) | VERIFIED | `app/schemas/analysis.py` line 77: `result_fen: str \| None = None`; `frontend/src/types/api.ts` line 82: `result_fen: string \| null` |
| 6 | Game cards display 3-row layout with BookOpen, Clock, Calendar, Swords, Hash icons | VERIFIED | `GameCard.tsx`: imports all 5 icons; Row 2 has `<BookOpen>`; Row 3 has `<Clock>`, `<Calendar>`, `<Swords>`, `<Hash>` |
| 7 | Null metadata fields are omitted entirely | VERIFIED | `GameCard.tsx`: all four metadata items have explicit null guards (`&&` checks) |
| 8 | Desktop hover shows MiniBoard tooltip; mobile tap expands inline | VERIFIED (automated) | `GameCard.tsx`: Tooltip wraps card when `result_fen` exists with `hidden sm:block`; `isExpanded && game.result_fen` inline expand with `sm:hidden` |
| 9 | `GameCardList` provides `TooltipProvider` and manages `expandedGameId` state | VERIFIED | `GameCardList.tsx`: `TooltipProvider` wraps card stack; `useState<number \| null>(null)` manages expanded state; `isExpanded`/`onToggle` passed to each `GameCard` |

**Score:** 9/9 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `app/services/zobrist.py` | `hashes_for_game()` returns `(tuples, result_fen)` 2-tuple | VERIFIED | Correct signature and `return results, result_fen` |
| `app/models/game.py` | `result_fen` nullable VARCHAR(100) column | VERIFIED | Line 57 matches plan exactly |
| `alembic/versions/20260318_212045_f3c8c11c64c9_add_result_fen_to_games.py` | Migration adding `result_fen` to `games` table | VERIFIED | Correct `op.add_column`, correct `down_revision`, correct type |
| `app/services/import_service.py` | Unpacks 2-tuple, stores `result_fen` in `sa_update` | VERIFIED | Unpacking and `values(result_fen=result_fen)` confirmed |
| `app/schemas/analysis.py` | `GameRecord` has `result_fen: str \| None = None` | VERIFIED | Line 77 confirmed |
| `frontend/src/types/api.ts` | `GameRecord` interface has `result_fen: string \| null` | VERIFIED | Line 82 confirmed |
| `frontend/src/components/results/GameCard.tsx` | 3-row layout with icons and minimap | VERIFIED | All icons imported and used; all 3 rows present; Tooltip + MiniBoard wired |
| `frontend/src/components/results/GameCardList.tsx` | `TooltipProvider` wrapper + `expandedGameId` state | VERIFIED | Both present and wired to `GameCard` |
| `tests/test_zobrist.py` | Tests for 2-tuple return shape | VERIFIED | Tests for result_fen present; all call sites updated |
| `tests/test_import_service.py` | Mocks updated to 2-tuple shape | VERIFIED | Mock return_values confirmed as 2-tuple shape |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `zobrist.py` | `import_service.py` | `hash_tuples, result_fen = hashes_for_game(pgn)` | WIRED | Confirmed in import_service.py |
| `import_service.py` | `app/models/game.py` | `sa_update(...).values(result_fen=result_fen)` | WIRED | Confirmed |
| `alembic migration` | `games` table | `op.add_column('games', ...)` | WIRED | Migration chains correctly from previous head |
| `GameCard.tsx` | `MiniBoard.tsx` | `<MiniBoard fen={game.result_fen} size={120} flipped={game.user_color === 'black'} />` | WIRED | Present in both tooltip and mobile expand paths |
| `GameCard.tsx` | `ui/tooltip` | `<Tooltip>/<TooltipTrigger>/<TooltipContent>` wrapping card | WIRED | Tooltip wiring confirmed |
| `GameCardList.tsx` | `GameCard.tsx` | `isExpanded={expandedGameId === game.game_id}` and `onToggle` callback | WIRED | Confirmed |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| GCUI-01 | 16-01 | `result_fen` column added to games table at import time | SATISFIED | Model (game.py line 57), migration (f3c8c11c64c9), import pipeline (import_service.py) all confirmed |
| GCUI-02 | 16-01 | `result_fen` in `GameRecord` API schema (backend + frontend) | SATISFIED | `app/schemas/analysis.py` line 77; `frontend/src/types/api.ts` line 82 |
| GCUI-03 | 16-02 | 3-row layout with BookOpen, Clock, Calendar, Swords, Hash icons | SATISFIED | `GameCard.tsx` fully implements all 3 rows with all 5 icons |
| GCUI-04 | 16-02 | Null metadata omitted; null opening shows "Unknown Opening" | SATISFIED | All 4 null guards in place; fallback `Unknown Opening` text confirmed |
| GCUI-05 | 16-02 | Hover minimap on desktop; tap-expand on mobile; user-perspective orientation | SATISFIED (automated) | Tooltip + `hidden sm:block` for desktop; inline expand + `sm:hidden` for mobile; `flipped={game.user_color === 'black'}` on both MiniBoard instances |

No orphaned requirements — all 5 GCUI requirements are claimed by plans and verified above.

---

### Anti-Patterns Found

None in phase 16 files. Pre-existing `react-refresh/only-export-components` lint errors in `badge.tsx`, `button.tsx`, `tabs.tsx`, and `toggle.tsx` are out of scope and were present before this phase.

---

### Human Verification Required

#### 1. Desktop hover minimap

**Test:** On the Games sub-tab, hover over a game card that has a result_fen (any imported game with moves).
**Expected:** A 120px MiniBoard tooltip appears above the card showing the final board position. When the user played as black, the board is flipped (black's pieces at bottom).
**Why human:** Radix Tooltip rendering, tooltip positioning, and board orientation require a browser.

#### 2. Mobile tap-to-expand minimap

**Test:** On a narrow viewport (or mobile device), tap a game card.
**Expected:** The MiniBoard appears inline below the metadata row. Tapping a second card collapses the first and expands the second. Tapping an already-expanded card collapses it. Tapping the external link icon does NOT trigger expansion (stopPropagation).
**Why human:** Touch interaction, viewport-conditional CSS (`sm:hidden`), and single-at-a-time state require a browser.

#### 3. Null metadata display for daily games

**Test:** Import or view chess.com daily games (which have no time control or exact date in some cases).
**Expected:** The Clock and Calendar metadata items are completely absent — no NaN, no dash, no placeholder text.
**Why human:** Requires live data with null `time_control_bucket` and `played_at` values.

---

_Verified: 2026-03-18T22:30:00Z_
_Verifier: Claude (gsd-verifier)_
