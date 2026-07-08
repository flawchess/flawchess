/**
 * leafScore — converts a leaf's white-POV Stockfish eval into a root-relative
 * expected score (ENGINE-05).
 *
 * `rootMover` MUST be the ROOT position's side to move — computed EXACTLY
 * ONCE via `sideToMoveFromFen(rootFen)` and threaded as a CONSTANT through
 * the entire search — NEVER the leaf node's own side to move. SEED-082's
 * backup formula has no per-ply negation term (unlike textbook negamax), so
 * every value flowing into `backup.ts`, at every depth, must already be
 * expressed in this SAME fixed reference frame (D-06 / 153-RESEARCH.md
 * Pattern 3 "Root-relative score frame"). Recomputing `rootMover` per node
 * (or passing the leaf's own side to move) silently flips sign every ply and
 * corrupts the whole search — this is the single subtlest correctness detail
 * in the phase, which is why it has its own fixture test.
 */

import { evalToExpectedScore, type MoverColor } from '@/lib/liveFlaw';
import type { MoveGrade } from './types';

/**
 * Converts `grade`'s white-POV eval (cp or mate-in-N) into the ROOT player's
 * expected score, 0-1. Reuses the existing lichess sigmoid verbatim — no new
 * mate logic or sigmoid constant here; `grade.evalMate` passes through
 * unchanged (the existing sigmoid already maps it to ±MATE_CP_EQUIVALENT).
 */
export function leafExpectedScore(grade: MoveGrade, rootMover: MoverColor): number {
  return evalToExpectedScore(grade.evalCp, grade.evalMate, rootMover);
}
