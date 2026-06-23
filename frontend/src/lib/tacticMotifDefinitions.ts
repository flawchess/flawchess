/**
 * One-sentence definitions for each TacticMotif string (Phase 126).
 *
 * Keys match the TacticMotif Literal strings in app/services/tactic_detector.py.
 * The backend enum has 29 members; en-passant and under-promotion are surfaced as
 * "Advanced" chip families (Quick 260623). Only promotion stays omitted — chip surfacing
 * for it remains out of scope (D-09). Used by TacticMotifChip popover bodies.
 *
 * Copy guidelines: WHAT the motif is, no jargon, no em-dashes, no p-values.
 */

export const TACTIC_MOTIF_DEFINITIONS: Record<string, string> = {
  fork: 'A single piece attacks two or more of the opponent\'s pieces at the same time.',
  pin: 'A piece cannot move without exposing a more valuable piece behind it to capture.',
  skewer: 'A valuable piece is forced to move, leaving a less valuable piece behind it undefended.',
  'x-ray': 'A piece exerts indirect pressure through an enemy piece, threatening the square or piece behind it.',
  'double-check': 'The king is placed in check by two pieces simultaneously, leaving only a king move as the reply.',
  'discovered-check': 'Moving one piece uncovers a check delivered by the piece behind it, not the piece that moved.',
  'discovered-attack': 'Moving one piece uncovers an attack by a piece behind it.',
  'trapped-piece': 'A piece has no safe square to move to and will be lost regardless of where it goes.',
  'back-rank-mate': 'The king is checkmated on its home rank because it has no escape square.',
  'smothered-mate': 'A knight delivers checkmate to a king that is surrounded and blocked in by its own pieces.',
  'anastasia-mate': 'A rook and knight combine to trap a king between the edge of the board and a blocking piece.',
  'hook-mate': 'A rook, knight, and pawn coordinate to checkmate a king in the corner.',
  'arabian-mate': 'A rook and knight together checkmate a king that is trapped in a corner.',
  'boden-mate': 'Two bishops on criss-crossing diagonals deliver checkmate to a king blocked by its own pieces.',
  'double-bishop-mate': 'Two bishops on adjacent diagonals deliver checkmate while the king is cut off.',
  'dovetail-mate': 'A queen delivers checkmate to a king whose only escape squares are blocked by its own pieces in a dovetail pattern.',
  mate: 'A checkmate pattern that does not fit a specific named category.',
  // Synthetic family-level key used only by the filter-panel legend (Quick 260620-onv):
  // groups every named-mate motif under one "checkmate" row instead of listing them.
  checkmate: 'The opponent\'s king is attacked and has no legal move to escape capture.',
  'hanging-piece': 'An undefended piece can be captured for free.',
  // The `combinations` family was dropped in Phase 129, so these 8 motifs no longer map to a
  // family and never render a chip. Retained only as the raw-string fallback source for any
  // TACTIC_MOTIF_DEFINITIONS[motif] lookup; safe to delete once that fallback is gone.
  sacrifice: 'A piece or pawn is given up deliberately to gain a positional or tactical advantage.',
  deflection: 'An opponent\'s piece is lured or forced away from a critical square it was defending.',
  attraction: 'An opponent\'s piece is drawn onto a square where it becomes vulnerable to a follow-up tactic.',
  intermezzo: 'An in-between move is played before completing an expected sequence, often gaining tempo.',
  interference: 'A piece is placed on a square that disrupts the coordination between two of the opponent\'s pieces.',
  'self-interference': 'One of the opponent\'s own pieces blocks another, creating a weakness that can be exploited.',
  clearance: 'A piece vacates a square or line so another piece can use it more effectively.',
  'capturing-defender': 'The piece defending a key square or piece is captured to remove that protection.',
  // Move-type families (Quick 260623): en-passant + under-promotion surfaced as Advanced chips.
  'en-passant': 'A pawn captures an enemy pawn that has just advanced two squares, as if it had moved only one.',
  'under-promotion': 'A pawn promotes to a knight, bishop, or rook instead of a queen to deliver a specific tactic.',
};
