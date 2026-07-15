/**
 * botSampling — pure, synchronous sampling/argmax/fallback helpers for
 * `selectBotMove` (Phase 166, D-04/D-06/D-09/D-11/D-12/D-13/D-14).
 *
 * Every helper here except `fallbackMove` returns `string | null`: `null`
 * signals a degenerate distribution (empty/all-zero weights), which the
 * orchestrator (`selectBotMove.ts`) interprets uniformly as "fall back to
 * `fallbackMove`" via a single `?? fallbackMove(...)` at each call site —
 * this file never decides the fallback trigger itself, it only signals it.
 * `fallbackMove` is the sole helper that throws, and only on a genuinely
 * terminal position (zero legal moves at all) — a caller precondition bug
 * per D-14, distinct from a degenerate policy/search result.
 *
 * All weighted sampling walks candidates sorted UCI-ascending first (D-12),
 * mirroring `select.ts`'s `truncateAndRenormalize` tie-break convention, so a
 * given `rng()` draw always yields the same move regardless of Map/Record
 * iteration order.
 */

import { Chess } from 'chess.js';
import type { RankedLine } from './types';

/**
 * Cumulative-distribution walk over UCI-ascending-sorted (uci, weight)
 * pairs (D-12). Returns `null` when the total weight is <= 0 or non-finite
 * (D-13's degenerate-distribution signal — empty input, all-zero weights,
 * or NaN/Infinity weights from a defective provider).
 * Clamps the exhausted-loop edge case to the last sorted UCI so a `rng()`
 * value of exactly 1 (out of the documented `[0,1)` contract, but a
 * plausible test-stub bug) never yields `undefined`.
 */
function weightedPick(entries: [string, number][], rng: () => number): string | null {
  const sorted = [...entries].sort((a, b) => (a[0] < b[0] ? -1 : a[0] > b[0] ? 1 : 0));
  const total = sorted.reduce((sum, [, w]) => sum + w, 0);
  // A NaN or Infinity total (e.g. a defective provider renormalizing p / 0
  // across the Worker boundary) must count as degenerate: `total <= 0` is
  // false for NaN, which previously let the exhausted-loop clamp silently
  // return the alphabetically-last UCI instead of signaling fallback (WR-01).
  if (!Number.isFinite(total) || total <= 0) return null;
  const draw = rng() * total;
  let cumulative = 0;
  for (const [uci, w] of sorted) {
    cumulative += w;
    if (draw < cumulative) return uci;
  }
  const last = sorted[sorted.length - 1];
  return last ? last[0] : null;
}

/**
 * Weighted-sample one UCI move from a raw Maia policy distribution
 * (D-03's `b=0` path). Returns `null` for an empty policy or one whose
 * weights sum to <= 0 (D-13 trigger) — never throws.
 */
export function samplePolicy(policy: Record<string, number>, rng: () => number): string | null {
  return weightedPick(Object.entries(policy), rng);
}

/**
 * Softmax-samples one UCI move over `RankedLine.practicalScore` at
 * sharpness `tau` (D-04). Reads `practicalScore` off each line explicitly —
 * `mctsSearch`'s `RankedLine[]` is sorted by findability-weighted
 * `rankScore`, NOT `practicalScore` (D-06), so array order must never be
 * trusted here. Uses the max-subtraction softmax-stability trick so no
 * exponent overflows to `Infinity`/`NaN` even at a very small `tau`; a
 * `tau <= 0` short-circuits to `argmaxLine` (the softmax's argmax limit).
 * Returns `null` for an empty `lines` array.
 */
export function sampleRankedLines(
  lines: readonly RankedLine[],
  tau: number,
  rng: () => number,
): string | null {
  if (lines.length === 0) return null;
  // tau <= 0 is the argmax limit of the softmax; computing it directly
  // avoids the exp(NaN) (tau = 0) and sign-flip (tau < 0) degeneracies
  // that out-of-contract tau values would otherwise hit (WR-03) — this is
  // a public API (D-09), so the precondition is enforced here, not only
  // at the orchestrator's TAU_EPSILON short-circuit.
  if (tau <= 0) return argmaxLine(lines);
  const maxScore = Math.max(...lines.map((line) => line.practicalScore));
  const weighted: [string, number][] = lines.map((line) => [
    line.rootMove,
    Math.exp((line.practicalScore - maxScore) / tau),
  ]);
  return weightedPick(weighted, rng);
}

/**
 * Deterministic argmax over `RankedLine.practicalScore`, UCI-ascending
 * tie-break (D-06/BOT-01 `b=1`). Scans every line explicitly for the true
 * maximum — never assumes `lines[0]` is the best-practicalScore line, since
 * `mctsSearch` sorts by `rankScore` (findability), not `practicalScore`.
 * Returns `null` for an empty `lines` array or when every line has a
 * non-finite `practicalScore` (D-13 degenerate-signal convention).
 */
export function argmaxLine(lines: readonly RankedLine[]): string | null {
  if (lines.length === 0) return null;
  let best: RankedLine | null = null;
  for (const line of lines) {
    // A NaN practicalScore never wins (all NaN comparisons are false), so an
    // early NaN `best` would otherwise be unbeatable by every later line —
    // skip non-finite lines entirely (WR-02); with all lines non-finite,
    // `best` stays null and the orchestrator's fallback handles it.
    if (!Number.isFinite(line.practicalScore)) continue;
    const isBetter =
      best === null ||
      line.practicalScore > best.practicalScore ||
      (line.practicalScore === best.practicalScore && line.rootMove < best.rootMove);
    if (isBetter) best = line;
  }
  return best ? best.rootMove : null;
}

/**
 * Canonical dependency-free `mulberry32` seeded PRNG (D-11) — returns a
 * function yielding values in `[0,1)`. A fixed seed always produces the
 * same output stream on repeated construction, giving `selectBotMove`
 * deterministic move selection under a fixed seed (SC4).
 */
export function mulberry32(seed: number): () => number {
  let a = seed;
  return function (): number {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

/**
 * Uniform-random legal move for `fen`, chosen UCI-ascending via `rng()`
 * (D-13's fallback for a degenerate policy/search distribution). Re-derives
 * legal moves fresh from the FEN via chess.js — never trusts a stale
 * candidate set — mirroring `treeCommon.ts`'s `applyUciMoveFen` convention
 * of never trusting an externally-supplied UCI string without chess.js
 * re-validation.
 *
 * Throws when `fen` has zero legal moves at all (checkmate/stalemate): a
 * terminal position reaching `selectBotMove` is a caller precondition bug
 * (D-14) — the game loop must detect end states before calling this
 * function. This is the ONLY helper in this module that throws.
 */
export function fallbackMove(fen: string, rng: () => number): string {
  const chess = new Chess(fen);
  const moves = chess.moves({ verbose: true });
  if (moves.length === 0) {
    throw new Error(
      `fallbackMove: no legal moves for fen "${fen}" (terminal position reached selectBotMove)`,
    );
  }
  const ucis = moves.map((move) => move.lan).sort((a, b) => (a < b ? -1 : a > b ? 1 : 0));
  const idx = Math.min(Math.floor(rng() * ucis.length), ucis.length - 1);
  // idx is clamped into [0, ucis.length - 1] and ucis is non-empty here, so
  // the access is always defined. `!` (project convention for provably
  // in-bounds indexing) narrows only the noUncheckedIndexedAccess undefined
  // arm — unlike the previous `as string`, it cannot mask a future type
  // drift of the ucis element type (IN-04).
  return ucis[idx]!;
}
