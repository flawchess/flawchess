/**
 * One-sentence definitions for each TacticMotif string (Phase 126).
 *
 * Keys match the 24 TacticMotif Literal strings in app/services/tactic_detector.py
 * exactly. Used by TacticMotifChip popover bodies.
 *
 * Copy guidelines: WHAT the motif is, no jargon, no em-dashes, no p-values.
 */

export const TACTIC_MOTIF_DEFINITIONS: Record<string, string> = {
  fork: 'A single piece attacks two or more of the opponent\'s pieces at the same time.',
  pin: 'A piece cannot move without exposing a more valuable piece behind it to capture.',
  skewer: 'A valuable piece is forced to move, leaving a less valuable piece behind it undefended.',
  'x-ray': 'A piece exerts indirect pressure through an enemy piece, threatening the square or piece behind it.',
  'double-check': 'The king is placed in check by two pieces simultaneously, leaving only a king move as the reply.',
  'discovered-attack': 'Moving one piece uncovers an attack by a piece behind it.',
  'back-rank-mate': 'The king is checkmated on its home rank because it has no escape square.',
  'smothered-mate': 'A knight delivers checkmate to a king that is surrounded and blocked in by its own pieces.',
  'anastasia-mate': 'A rook and knight combine to trap a king between the edge of the board and a blocking piece.',
  'hook-mate': 'A rook, knight, and pawn coordinate to checkmate a king in the corner.',
  'arabian-mate': 'A rook and knight together checkmate a king that is trapped in a corner.',
  'boden-mate': 'Two bishops on criss-crossing diagonals deliver checkmate to a king blocked by its own pieces.',
  'double-bishop-mate': 'Two bishops on adjacent diagonals deliver checkmate while the king is cut off.',
  'dovetail-mate': 'A queen delivers checkmate to a king whose only escape squares are blocked by its own pieces in a dovetail pattern.',
  mate: 'A checkmate pattern that does not fit a specific named category.',
  'hanging-piece': 'An undefended piece can be captured for free.',
  sacrifice: 'A piece or pawn is given up deliberately to gain a positional or tactical advantage.',
  deflection: 'An opponent\'s piece is lured or forced away from a critical square it was defending.',
  attraction: 'An opponent\'s piece is drawn onto a square where it becomes vulnerable to a follow-up tactic.',
  intermezzo: 'An in-between move is played before completing an expected sequence, often gaining tempo.',
  interference: 'A piece is placed on a square that disrupts the coordination between two of the opponent\'s pieces.',
  'self-interference': 'One of the opponent\'s own pieces blocks another, creating a weakness that can be exploited.',
  clearance: 'A piece vacates a square or line so another piece can use it more effectively.',
  'capturing-defender': 'The piece defending a key square or piece is captured to remove that protection.',
};
