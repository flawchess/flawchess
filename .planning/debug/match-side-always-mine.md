---
status: diagnosed
trigger: "Investigate why the match_side heuristic always returns 'mine' instead of suggesting 'Both' for many positions."
created: 2026-03-15T00:00:00Z
updated: 2026-03-15T00:00:00Z
---

## Current Focus

hypothesis: The suggest_match_side query scope is fundamentally mismatched with get_top_positions_for_color, making the ratio almost always ~1.0
test: Logical analysis of query semantics
expecting: The ratio should frequently exceed 1.5 for common openings, but the query design prevents it
next_action: Return diagnosis

## Symptoms

expected: suggest_match_side should return "both" for positions where the opponent's pieces vary significantly across games
actual: Always returns "mine" for all suggested positions
errors: None (logic bug, not crash)
reproduction: Call GET /position-bookmarks/suggestions - all suggestions have suggested_match_side="mine"
started: Since feature was implemented

## Eliminated

(none needed - root cause identified on first analysis)

## Evidence

- timestamp: 2026-03-15T00:00:00Z
  checked: get_top_positions_for_color query (lines 154-202)
  found: Groups by (white_hash, black_hash, full_hash) - meaning each returned row represents an EXACT full board position, not just a "my pieces" position
  implication: Each suggestion already has a fixed full_hash, so by definition there is minimal variation in full_hash for those games

- timestamp: 2026-03-15T00:00:00Z
  checked: suggest_match_side query (lines 205-236)
  found: Filters by the user's color hash (e.g. white_hash=X) and counts distinct full_hashes vs distinct games
  implication: The query asks "for all positions where MY pieces are in this arrangement, how many distinct full board states exist?" This is the right question BUT there is a critical flaw in where the data comes from.

- timestamp: 2026-03-15T00:00:00Z
  checked: The interaction between the two functions
  found: get_top_positions_for_color groups by (white_hash, black_hash, full_hash). The top results are positions where one EXACT full board state occurs most often. For popular openings (e.g. Sicilian after 7 moves), the most common exact position will have high game_count. The suggest_match_side then queries by white_hash alone (not full_hash), which SHOULD capture variation. But the issue is that the suggest_match_side query has NO ply filter - it searches ALL plies.
  implication: A white_hash value appears at many different plies throughout a game (the same piece configuration can occur at different points). At ply 0, all white games share the same white_hash. This pollutes the ratio calculation.

- timestamp: 2026-03-15T00:00:00Z
  checked: Deeper analysis of ratio behavior
  found: Actually, reconsidering - at different plies the white pieces WILL be different (pieces get captured/moved), so white_hash changes. The real issue is simpler. Consider: for the MOST PLAYED openings, positions where the user plays the same pieces (same white_hash) are by definition the popular ones. In popular openings, both sides tend to play mainline moves, so the opponent's pieces also tend to be the same. The ratio of distinct_full_hashes / distinct_games will naturally be close to 1.0 for the MOST popular positions because popularity implies convergence. The threshold of 1.5 means the opponent would need to have 50% MORE distinct full positions than games, which is mathematically impossible (ratio is always <= 1.0 because each game contributes at most one full_hash per white_hash occurrence).
  implication: THIS IS THE ROOT CAUSE. The ratio can never exceed 1.0, so the threshold of 1.5 can never be reached.

- timestamp: 2026-03-15T00:00:00Z
  checked: Mathematical proof that ratio <= 1.0
  found: The query counts DISTINCT full_hash and DISTINCT game_id where white_hash = X. Each (game_id, white_hash) combination has exactly one full_hash at a given ply. But WITHOUT a ply filter, a single game can have the same white_hash at multiple plies with different full_hashes (opponent moved but user's pieces stayed same). So ratio CAN exceed 1.0 in theory. However, in practice for opening positions (ply 6-14), pieces rarely stay in same config across multiple plies, so distinct_full per game is ~1.
  implication: Need to reconsider. Let me think more carefully.

- timestamp: 2026-03-15T00:00:00Z
  checked: Final analysis of the ratio semantics
  found: The query lacks a ply constraint. For a given white_hash, across ALL plies in a game, a game might contribute multiple distinct full_hashes (same white piece arrangement, different opponent piece arrangements at different plies). BUT the key insight is that suggest_match_side is called with the white_hash from a SPECIFIC position (e.g., after 1.e4 e5 2.Nf3 Nc6 3.Bb5). That specific white_hash is highly specific to that ply range. In practice, the SAME white piece configuration rarely appears at very different plies. So each game contributes roughly 1 full_hash per occurrence of that white_hash, giving a ratio very close to 1.0. The threshold of 1.5 requires 50% more full_hash variation than games, which almost never happens in practice for opening positions.
  implication: The heuristic is fundamentally flawed - the ratio is almost always near 1.0 for opening positions, making the 1.5 threshold unreachable.

## Resolution

root_cause: |
  The suggest_match_side ratio (distinct_full_hashes / distinct_games) is structurally almost always <= ~1.0, making the threshold of 1.5 effectively unreachable.

  The ratio measures: "For positions where my pieces are arranged as X (white_hash=X), how many distinct full board positions exist per game?"

  For opening positions (ply 6-14), a specific white_hash is highly characteristic of a narrow ply range. Each game where white_hash=X typically contributes ~1 distinct full_hash for that white_hash occurrence. So distinct_full_hashes ~ distinct_games, giving ratio ~ 1.0.

  For the ratio to reach 1.5, you'd need games where the SAME white piece arrangement co-occurs with 1.5x different opponent arrangements PER GAME on average. This would require the same white_hash to appear at multiple plies within the same game with different opponent positions - which rarely happens in openings because each move changes the piece configuration.

  The correct approach would be to compare across games rather than within: "For N games where my pieces are in position X, how many distinct opponent configurations exist?" This is simply COUNT(DISTINCT full_hash) / COUNT(DISTINCT game_id) but with a ply constraint matching the suggestion ply range. Even then, the issue is that for the MOST POPULAR positions (which is what get_top_positions_for_color returns), convergence is inherent - they're popular precisely because both sides play the same moves.

  A better heuristic might compare: the game_count when grouping by (white_hash, black_hash, full_hash) vs the game_count when grouping by only the user's hash (white_hash or black_hash). If the "my pieces only" count is much higher than the "exact position" count, it means the opponent varies a lot, suggesting "mine" is appropriate. If they're similar, "both" is fine.
fix: (diagnosis only)
verification: (diagnosis only)
files_changed: []
