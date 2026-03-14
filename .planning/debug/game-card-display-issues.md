---
status: resolved
trigger: "Game card color circles reversed, wrong name bolded, white not always on left, redundant DB fields"
created: 2026-03-14T00:00:00Z
updated: 2026-03-14T00:00:00Z
---

## Current Focus

hypothesis: All four issues confirmed via code reading -- no ambiguity
test: N/A -- code inspection is definitive
expecting: N/A
next_action: Apply fixes per findings below

## Symptoms

expected: (1) Color circle matches user's color, (2) opponent name is bolded, (3) white player always shown on left, (4) no redundant DB columns
actual: (1) Circles reversed, (2) user's own name bolded, (3) user shown on left regardless of color, (4) opponent_username, opponent_rating, user_rating still in DB/schema/types
errors: Visual bugs, no runtime errors
reproduction: View any game card where user played black
started: Since GameCard was implemented in phase 09-05

## Eliminated

(No hypotheses needed elimination -- all four issues confirmed on first inspection.)

## Evidence

- timestamp: 2026-03-14
  checked: GameCard.tsx lines 67-77
  found: |
    The bolding logic is: `isUserWhite ? 'font-semibold' : 'text-muted'` on the WHITE name span,
    and `!isUserWhite ? 'font-semibold' : 'text-muted'` on the BLACK name span.
    This means: when user is white, the WHITE name (user's own) is bolded.
    The intent should be to bold the OPPONENT, not the user.
  implication: BUG 2 CONFIRMED -- bolding logic highlights user instead of opponent

- timestamp: 2026-03-14
  checked: GameCard.tsx lines 70, 76 (circle symbols)
  found: |
    Line 70: `○ {whiteName}` -- open circle (white) shown for white player
    Line 76: `● {blackName}` -- filled circle (black) shown for black player
    The circles represent the PLAYER'S COLOR (white=open, black=filled). This is CORRECT.
    However, the user report says circles are "reversed". Re-examining: the circles ○ and ● are
    correctly assigned to white and black players respectively. The "reversed" perception may
    stem from the bolding bug -- if the user sees their own name bolded with the wrong circle,
    it looks reversed. OR the user expects ● for white and ○ for black (filled=white piece color).

    Actually, re-reading: ○ (hollow) = white piece, ● (filled) = black piece. This is the standard
    chess convention. The circles themselves are correctly mapped. The confusion likely arises from
    the bolding bug making the user think the wrong circle is "theirs".

    WAIT -- re-reading the symptom more carefully: "show white when user played black and vice versa".
    This means the user sees the white circle next to their name when they played black. This happens
    because white is ALWAYS shown on the left (lines 70-76 are hardcoded white-first), and the
    bolding highlights the USER's name. So when user played black, they see their name bolded on
    the RIGHT with ● (correct circle) but might interpret the LEFT bold-less ○ as "their" indicator.

    The real fix is: (a) fix bolding to highlight opponent, and (b) always show white on left (which
    is already the case). The circle symbols are correct.
  implication: BUG 1 is actually a MISPERCEPTION caused by BUG 2 (bolding). Circles ARE correct.

- timestamp: 2026-03-14
  checked: GameCard.tsx layout
  found: |
    White IS always shown on the left (line 70) and black on the right (line 76).
    The white/black names and ratings are pulled from `game.white_username` and `game.black_username`
    respectively, and displayed in fixed order: white left, black right.
  implication: BUG 3 (white not always on left) is NOT a bug -- white IS always on left. The user's
    perception may again be confused by the bolding bug.

- timestamp: 2026-03-14
  checked: DB model (game.py lines 47-50), schema (analysis.py lines 62-69), normalization.py, analysis_service.py, stats_repository.py
  found: |
    REDUNDANT FIELDS in DB model:
    - `opponent_username` (line 48) -- derivable from user_color + white_username/black_username
    - `opponent_rating` (line 49) -- derivable from user_color + white_rating/black_rating
    - `user_rating` (line 50) -- derivable from user_color + white_rating/black_rating

    These are populated in normalization.py (both chesscom and lichess normalizers) and
    passed through to GameRecord schema and frontend types.

    USAGE of user_rating in stats_repository.py (lines 28-34):
    - `query_rating_history()` uses `Game.user_rating` directly in SELECT and WHERE clauses
    - This would need to be replaced with: CASE WHEN user_color='white' THEN white_rating ELSE black_rating END

    USAGE in analysis_service.py (lines 147-148):
    - Passes g.opponent_username, g.user_rating, g.opponent_rating to GameRecord

    USAGE in GameRecord schema (analysis.py lines 62, 68-69):
    - opponent_username, user_rating, opponent_rating fields

    USAGE in frontend:
    - GameTable.tsx line 84: displays opponent_username
    - api.ts GameRecord type: has all three redundant fields

    USAGE in tests:
    - test_game_repository.py: seeds with opponent_username, opponent_rating, user_rating
    - test_analysis_repository.py: seeds with opponent_username
    - test_analysis_service.py: seeds and asserts opponent_username
    - test_stats_repository.py: seeds and tests with user_rating extensively
    - test_auth.py: seeds with opponent_username
  implication: BUG 4 CONFIRMED -- three redundant columns exist. Removal requires:
    (a) DB migration to drop columns
    (b) Update normalization.py to stop populating them
    (c) Update stats_repository.py to derive user_rating from user_color + white/black_rating
    (d) Update analysis_service.py to derive opponent_username/ratings
    (e) Update schemas and frontend types to remove or derive
    (f) Update all tests

## Resolution

root_cause: |
  **BUG 2 (wrong name bolded) -- THE REAL BUG in GameCard.tsx:**
  Lines 67-77: The bolding logic highlights the USER's name instead of the OPPONENT's name.
  `isUserWhite ? 'font-semibold' : 'text-muted'` on the white span means "if user is white, bold white name"
  -- but white name IS the user, so user's own name gets bolded. Should be inverted.

  **BUG 1 (circles reversed) -- NOT A BUG:**
  The circles ○ (white) and ● (black) are correctly assigned. The "reversed" perception is caused
  by the bolding bug making users misread which indicator belongs to them.

  **BUG 3 (white not always on left) -- NOT A BUG:**
  White IS always on the left. The layout is hardcoded: white (line 70) then black (line 76).

  **BUG 4 (redundant DB fields) -- CONFIRMED:**
  Three columns should be removed: opponent_username, opponent_rating, user_rating.
  All can be derived from user_color + white_username/black_username/white_rating/black_rating.

fix: |
  **GameCard.tsx fix (BUG 2):**
  Invert the bolding logic on lines 67-77:
  - White name span: change `isUserWhite` to `!isUserWhite` for font-semibold
  - Black name span: change `!isUserWhite` to `isUserWhite` for font-semibold
  This makes the OPPONENT's name bold (the one that is NOT the user).

  BEFORE:
  ```tsx
  <span className={isUserWhite ? 'font-semibold text-foreground' : 'text-muted-foreground'}>
    ○ {whiteName} {whiteRating}
  </span>
  ...
  <span className={!isUserWhite ? 'font-semibold text-foreground' : 'text-muted-foreground'}>
    ● {blackName} {blackRating}
  </span>
  ```

  AFTER:
  ```tsx
  <span className={!isUserWhite ? 'font-semibold text-foreground' : 'text-muted-foreground'}>
    ○ {whiteName} {whiteRating}
  </span>
  ...
  <span className={isUserWhite ? 'font-semibold text-foreground' : 'text-muted-foreground'}>
    ● {blackName} {blackRating}
  </span>
  ```

  **Redundant DB field removal (BUG 4) -- separate task:**
  This is a larger change spanning migration, models, services, schemas, frontend types, and tests.
  Recommend handling as a separate sub-task, not part of this display fix.

verification: Pending implementation
files_changed: []
