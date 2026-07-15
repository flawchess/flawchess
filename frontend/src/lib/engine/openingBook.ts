/**
 * openingBook — the pure, synchronous bot opening-book module (Phase 169.5,
 * PLAY-11). Given the game's move history so far, the current position's
 * legal moves, the ECO prefix-set index (`@/lib/openings`'s
 * `loadOpeningPrefixSet()`), a raw Maia policy, and an rng, resolves to
 * either an in-book UCI move or `null` ("leave book — fall through to
 * `selectBotMove`").
 *
 * This module is deliberately pure and synchronous: no React, no providers,
 * no I/O, no `chess.js` import. Legal moves are always passed IN by the
 * caller — the caller's live board (the one that actually holds the move
 * history) is the single source of truth for what is legal right now; this
 * module never re-derives legality from a FEN itself.
 *
 * The one-way "left book" latch (D-03: leaving book is a one-way transition
 * within a game) is the CALLER's state (e.g. `useBotGame`'s `hasLeftBookRef`),
 * not something derivable here. It cannot be derived from move history alone:
 * ECO's 3,641 lines cover nearly every sane early position, so a game can
 * wander back onto a cataloged prefix even after the bot has already left
 * book and started searching (Pitfall 1, 169.5-RESEARCH.md). Ply-cap exits
 * are safely re-derivable from history length (monotonic), but floor-exits
 * are a fresh per-position evaluation with no memory of prior positions — so
 * the latch must be tracked externally, once, on either exit path.
 *
 * `frontend/src/lib/engine/selectBotMove.ts` is deliberately untouched by
 * this module — it is imported unchanged by both the app and
 * `scripts/calibration-harness.mjs`, whose anchor games already start from
 * mid-opening FENs (`scripts/lib/calibration-openings.mjs`'s `OPENING_BOOK`)
 * and must never gain a second book.
 */

import { samplePolicy } from './botSampling';

/**
 * The minimum RAW Maia probability (share among ALL legal moves, not among
 * book candidates) that at least one in-book continuation must reach for the
 * position to still count as book (D-03). Self-tuning by construction: it
 * fires exactly when no theory move looks human-plausible at that ELO.
 * Tuned by feel per D-03 ([ASSUMED], 169.5-RESEARCH.md Assumptions Log A1);
 * re-tunable in place.
 */
export const BOOK_POLICY_FLOOR = 0.05;

/**
 * The hard stop (in half-moves/plies) that prevents the bot replaying a deep
 * ECO mainline (the shipped corpus reaches 36 plies) for 20 plies without
 * ever engaging the engine (D-03). Eight full moves. Compared against
 * `moveHistorySan.length`, so ply 16 means "16 half-moves already played".
 * [ASSUMED] per D-03 (169.5-RESEARCH.md Assumptions Log A2); re-tunable in
 * place.
 */
export const BOOK_PLY_CAP = 16;

/** A legal move that is also a valid in-book continuation of the current line. */
export interface BookCandidate {
  uci: string;
  san: string;
}

/**
 * The D-06 persona seam. The ONLY thing a future persona (SEED-098's
 * Trickster) needs to swap to bias the book toward `data/trollOpenings.ts`
 * positions. Candidate generation (`getBookCandidates`) and the exit rule
 * (the floor/ply-cap checks in `selectBookMove`) are deliberately NOT
 * parameterized — a persona re-weights what is on the menu, it does not
 * change what is on the menu or when the bot leaves book. Do not build the
 * persona layer in this phase.
 */
export type BookWeightingFn = (
  candidates: readonly BookCandidate[],
  rawPolicy: Record<string, number>,
) => Record<string, number>;

/**
 * The only weighting shipped today (D-02). Builds a plain
 * `Record<string, number>` containing, for each candidate,
 * `rawPolicy[candidate.uci]` when that key is defined (skipped otherwise).
 *
 * No renormalization math: `samplePolicy` (via `botSampling.ts`'s internal
 * `weightedPick`) sums whatever weights it is handed and draws
 * proportionally (`draw = rng() * total`), so a filtered-but-unnormalized
 * subset IS the "renormalized over the in-book candidate subset" D-05 asks
 * for. Do not "fix" this by dividing by the sum — that would just rescale
 * every weight by the same constant and change nothing about the resulting
 * distribution, while adding a redundant floating-point step.
 */
export const maiaPolicyWeighting: BookWeightingFn = (candidates, rawPolicy) => {
  const restricted: Record<string, number> = {};
  for (const { uci } of candidates) {
    const p = rawPolicy[uci];
    if (p !== undefined) restricted[uci] = p;
  }
  return restricted;
};

/**
 * The candidate filter (D-01/D-03). For each legal move, tests whether
 * appending its SAN to the move history so far still lands on some ECO
 * line's prefix. `legalMoves` is structurally what `chess.js`'s
 * `.moves({ verbose: true })` returns (it carries both `.san` and `.lan`),
 * so no SAN<->UCI conversion happens anywhere in this module.
 *
 * Stateless — no trie cursor, no per-turn state to reset. Every call is a
 * fresh, independent `prefixSet.has(...)` lookup.
 */
export function getBookCandidates(
  moveHistorySan: readonly string[],
  legalMoves: readonly { san: string; lan: string }[],
  prefixSet: ReadonlySet<string>,
): BookCandidate[] {
  const candidates: BookCandidate[] = [];
  for (const move of legalMoves) {
    const key = [...moveHistorySan, move.san].join(' ');
    if (prefixSet.has(key)) candidates.push({ uci: move.lan, san: move.san });
  }
  return candidates;
}

/**
 * The book's full selection pipeline (D-02/D-03/D-05). Returns the chosen
 * UCI move, or `null` — the caller's signal to leave book (fall through to
 * `selectBotMove` and latch `hasLeftBookRef`).
 *
 * Order of operations is load-bearing and must stay exactly as written:
 *   1. Ply cap check — first, and cheapest.
 *   2. Candidate generation — empty candidates means no book line survives.
 *   3. The RAW-policy floor check (see the comment at its call site below
 *      for why this must run BEFORE `weighting` is ever invoked).
 *   4. Only now: weight and sample.
 */
export function selectBookMove(
  moveHistorySan: readonly string[],
  legalMoves: readonly { san: string; lan: string }[],
  prefixSet: ReadonlySet<string>,
  rawPolicy: Record<string, number>,
  rng: () => number,
  weighting: BookWeightingFn = maiaPolicyWeighting,
): string | null {
  if (moveHistorySan.length >= BOOK_PLY_CAP) return null;

  const candidates = getBookCandidates(moveHistorySan, legalMoves, prefixSet);
  if (candidates.length === 0) return null;

  // D-03/Pitfall 3 (169.5-RESEARCH.md): the floor is checked against the RAW
  // `rawPolicy` values — each candidate's unconditional probability among
  // ALL legal moves — read DIRECTLY here, never against `weighting`'s
  // output. With exactly one book candidate, its renormalized share inside
  // `weighting`'s result is always exactly 1.0 regardless of how
  // implausible Maia actually rates the move, so a post-renormalization
  // floor check is un-triggerable in exactly the single-candidate case the
  // floor exists to catch. A future persona's weighting (D-06) may also
  // reshape the distribution arbitrarily, so the exit rule must never
  // depend on its output either way.
  const clearsFloor = candidates.some((c) => (rawPolicy[c.uci] ?? 0) >= BOOK_POLICY_FLOOR);
  if (!clearsFloor) return null;

  const restricted = weighting(candidates, rawPolicy);
  // samplePolicy's own null (empty/all-zero/non-finite distribution, D-13)
  // propagates here as another leave-book signal — no special-casing needed.
  return samplePolicy(restricted, rng);
}
