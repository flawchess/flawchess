# Quick 261012-a6m — Context (locked decisions)

## Request (owner, verbatim)
When rendering stockfish engine arrows on the board (analysis page, train puzzle solution):
- Render the best move icon for the top engine move.
- For secondary lines, render the corresponding move quality icon, compared to the top move
  (good, inaccuracy, mistake, or blunder). Use transparency, matching the arrows for secondary
  lines which are also transparent.

## Locked decisions (owner answers, 2026-10-12)
- D-01 Engines: **Stockfish arrows only** on the Analysis page. FlawChess Engine (amber) arrows get no badges.
- D-02 Depth gate: arrows keep drawing immediately as today; badges appear only once BOTH the top
  line and that line have depth >= 10 (same value as TRAIN_LIVE_ALT_MIN_DEPTH / GRADING_DEPTH_FLOOR;
  own named constant or reuse, no magic number). Top-line badge (best star) also gated on top-line depth >= 10.
- D-03 Collisions: the existing last-move square marker (severity/gem/great/best/good/book) WINS; the
  engine badge is skipped on a square that already carries a marker. Two engine arrows targeting
  the same square: the higher-ranked (lower index) arrow keeps the badge.
- D-04 Train: stepped-preview and free-play boards get badges on every drawn Stockfish arrow, graded
  against the live engine's top line (pvLines[0]). The step board's solid blue preview pointer gets
  the best star only if it IS the live top move; otherwise it is graded vs the top line like a
  secondary (needs its PV line in pvLines to grade; if not present, no badge). The reveal-root
  overlay (buildTrainRevealOverlay) already badges its arrows — leave it unchanged.
- D-05 Grading: quality of rank k = classifyLiveSeverity(esTop, esLine_k) ?? 'good' using the same
  expected-score pipeline as the app (lib/liveFlaw evalToExpectedScore, side-to-move perspective) —
  never a new cutoff. Rank 0 = 'best'.
- D-06 Transparency: badges on secondary arrows use SquareMarker.opacity (already supported, boardMarkers.tsx
  renders <g opacity>), with a named constant chosen to visually match the secondary-arrow alpha
  (STOCKFISH_SECONDARY_LINE is blue @ 0.45 vs primary @ 0.8). Top-move best badge renders fully opaque.
- D-07 Hover isolation: when the move-quality-bar hover or the PV-sideline tactic overlay replaces the
  engine arrows, no engine badges render (badges follow the arrows actually drawn). Arrow count 0 => no badges.

## Added 2026-10-12 (owner follow-up)
- D-08 Proportional transparency: a secondary Stockfish arrow's alpha scales with its expected-score
  drop vs the top line (same esTop - esLine used for grading). Linear map, clamped: drop 0 =>
  SECONDARY_MAX alpha (below the primary 0.8 so the top arrow stays distinct), drop >= the blunder
  ES threshold (import from lib/liveFlaw, no new cutoff) => SECONDARY_MIN alpha (floor so blunder
  arrows stay visible). Named constants. The badge on that arrow uses the SAME opacity value
  (supersedes D-06's single fixed badge opacity). Applies to both Analysis and Train step/free-play.
  Before the depth gate (D-02) is met, arrows keep today's fixed STOCKFISH_SECONDARY_LINE color and no badge.
  Top arrow unchanged (solid primary, opaque best badge).
