/**
 * trainArrows — pure reveal-board overlay builder (arrows + square-corner
 * quality badges) for the Train solve screen (Phase 190.1, D-02; reworked per
 * 190.1 UAT).
 *
 * Color language (190.1 UAT, recolored per Phase 200 D-04/D-05): BLUE always
 * marks the engine's best move (the app-wide "engine pointer" hue), the
 * user's PLAYED move is colored by its own move quality (good/inaccuracy/
 * mistake/blunder), alternative fine moves — the SERVER's vetted "Also
 * fine" list as of Phase 211 (D-01), no longer the client engine's MultiPV
 * ranks — are dark green regardless of whether the server classified them
 * best, good or inaccuracy (a 'best'-quality alternative keeps its blue
 * best-star BADGE, though — the deep engine's endorsement is real
 * information), and the thin white on-top arrow still marks the move
 * played in the original game.
 * Every arrow additionally gets the matching move-quality badge (the shared
 * SquareMarker corner glyphs) on its target square.
 *
 * Quick 261008-opg reverses Phase 200 D-04/D-05, which drew a played
 * inaccuracy as good so the board would not contradict a verdict that called
 * it correct. Since tiered scoring (SEED-119) an inaccuracy earns 1 move point,
 * not 2, and the verdict says "decent move [+1]", so the green collapse itself
 * became the contradiction. Only the server-vetted "Also fine" alternatives
 * still render inaccuracy as good: they are listed as acceptable moves.
 *
 * Extracted into its own module (rather than inlined in TrainSolveScreen) so
 * the puzzle-type-aware arrow selection is unit-testable without rendering a
 * board, and so TrainSolveScreen's own logic stays small.
 */

import type { BoardArrow, SquareMarker } from '@/components/board/ChessBoard';
import { DARK_GREEN } from '@/lib/arrowColor';
import { classifyLiveSeverity, evalToExpectedScore, sideToMoveFromFen } from '@/lib/liveFlaw';
import {
  MOVE_HIGHLIGHT_BEST,
  MOVE_HIGHLIGHT_BLUNDER,
  MOVE_HIGHLIGHT_GOOD,
  MOVE_HIGHLIGHT_MISTAKE,
  MOVE_HIGHLIGHT_SQUARE,
  MOVE_QUALITY_GOOD,
  MOVE_QUALITY_INACCURACY,
  MOVE_QUALITY_MISTAKE,
  MOVE_QUALITY_BLUNDER,
  NEXT_MOVE_ARROW,
  STOCKFISH_SECONDARY_LINE,
  TRAIN_BEST_MOVE_ARROW,
  TRAIN_FOCUS_ARROW_DIM_OPACITY,
  TRAIN_FOCUS_ARROW_LIT_OPACITY,
  TRAIN_FOCUS_BADGE_DIM_OPACITY,
  TRAIN_FOCUS_BADGE_LIT_OPACITY,
} from '@/lib/theme';
import type { PvLine } from '@/hooks/uciParser';
import type { RoleKey } from '@/lib/trainRevealLines';
import type { FlawSeverity } from '@/types/library';

export type TrainPuzzleType = 'sharp' | 'soft' | 'herring';

/**
 * Move-quality taxonomy for the reveal board (190.1 UAT). Deliberately the
 * subset of lib/moveQuality.ts's MoveQuality that the grading engine can
 * actually distinguish here — no 'gem'/'great' (those need the Maia overlay,
 * which the Train loop doesn't run).
 */
export type TrainMoveQuality = 'best' | 'good' | FlawSeverity;

/**
 * One server-certified alternative ("Also fine" move). Phase 211 (D-01): the
 * list is the verdict's `vetted_moves` — soft deep-best + `su`, herring
 * good-band ladder — no longer derived from the client engine's MultiPV mount
 * search. 'good' (drop not even an inaccuracy) and 'inaccuracy' (drop within
 * [INACCURACY_DROP, MISTAKE_DROP), still a correct move by SOLV-03's rule)
 * are retained because the wire shape mirrors them; the reveal renders both
 * as good (see `buildTrainRevealOverlay`). D-01 amendment (2026-08-16): 'best' marks the
 * deep best move itself, served FIRST on a soft puzzle — usually filtered out
 * below (it coincides with the client's best arrow), but displayable when the
 * two engines disagree, which is exactly the case that used to strand the
 * "several fine moves" copy with an empty row.
 */
export interface TrainFineMove {
  uci: string;
  quality: 'best' | 'good' | 'inaccuracy';
}

/**
 * Phase 211 (D-06): find the served vetted move whose UCI starts at `from`
 * and ends at `to`, or null. The free-play ROOT ply's key lookup — this is
 * the squares-only twin of `uciParser.ts`'s exact-UCI `rankLineForMove`, and
 * it carries forward the contract of the retired squares-only rank matcher
 * (formerly beside `rankLineForMove` in uciParser.ts) verbatim in substance:
 * - The four-character slice exists because the move tree (`MoveNode` in
 *   `useAnalysisBoard.ts`) stores only `from`/`to` and no promotion piece —
 *   a full-string compare would miss a promotion (the same reason
 *   `useTreeMoveGrading`'s `isBest` check slices its UCI to four characters).
 * - Ties (two entries naming the same squares — a promotion-variant pair)
 *   resolve by ARRAY ORDER, which is the server's own best-first order:
 *   the first match wins. Callers must NOT re-sort `moves` — the ordering
 *   IS the tie rule.
 * - A malformed/short UCI simply does not match and never throws (a short
 *   slice can never equal a four-character `from + to`).
 *
 * Lives here rather than in the UCI parser because it matches the
 * server-certified move type (`TrainFineMove`, declared above), not an
 * engine PV line; putting it in a hook would create a hook-to-hook
 * dependency instead.
 */
export function vettedMoveForSquares(
  moves: readonly TrainFineMove[],
  from: string,
  to: string,
): TrainFineMove | null {
  const fromTo = `${from}${to}`;
  return moves.find((move) => move.uci.slice(0, 4) === fromTo) ?? null;
}

/**
 * Arrow caps, counted in ALTERNATIVES (Phase 200 UAT round 4) — not in total
 * arrows as the original D-02 constants were: the filter runs BEFORE the
 * slice in `buildTrainRevealOverlay`, so the best move and a played
 * alternative never consume a slot. Phase 211 (D-01) split the former shared
 * non-sharp cap into THREE independent per-puzzle-type budgets — the
 * alternatives are now the server's certified list, whose upper bound
 * differs per type, not slices of one client MultiPV array.
 */
/** A sharp puzzle has exactly one right move by definition (D-02), so it
 * draws NO alternative arrows at all, regardless of how many entries the
 * fine-moves set has. Deliberately kept at zero after the round-4 recount:
 * the sharp/soft label comes from the server's deep MultiPV-2 answer key,
 * which outranks the solve loop's 1.5s client search — if the deep key says
 * the runner-up is itself a mistake, green alternatives here would both
 * teach the wrong lesson and contradict the critical-vs-several guess the
 * user just scored on. */
export const TRAIN_SHARP_ALT_MOVE_ARROWS = 0;
/** A soft puzzle draws at most ONE green alternative. The served list holds
 * up to TWO entries since the D-01 amendment (2026-08-16) — the deep best
 * (quality 'best', first) plus the second-best `su` — and when the client's
 * own best arrow coincides with neither (the two engines disagree AND the
 * played move is off-key), both survive the filter below. The cap of 1 then
 * deliberately truncates to the FIRST survivor: the server's best-first
 * order is a documented contract of the vetted list, so the drawn entry is
 * always the STRONGEST new fine move, and a soft board never shows more
 * than one green arrow. Phase 211 (D-01): no longer derived from the
 * retired MultiPV mount-search width; the server list's own shape is the
 * authority. */
export const TRAIN_SOFT_ALT_MOVE_ARROWS = 1;
/** A red herring's certified list comes from the stored 5-entry ladder
 * (`app/services/train_pool.py` `HERRING_LADDER_SIZE`), whose top entry is
 * drawn as the best-move arrow — leaving at most 4 alternatives. A DISPLAY
 * bound only, kept as defence in depth: the server already caps the list it
 * serves (only good-band ladder entries qualify), and the server-side ladder
 * length is the authority — this constant is deliberately NOT imported from
 * the backend. */
export const TRAIN_HERRING_ALT_MOVE_ARROWS = 4;
/** The TOTAL alternative arrows at a soft puzzle's root (quick 261010-e5l):
 * server-certified alternatives first (still capped by
 * TRAIN_SOFT_ALT_MOVE_ARROWS), live engine lines fill the rest. Deliberately
 * independent of the Stockfish arrows setting (sfArrows), which governs
 * stepped and off-line boards only. */
export const TRAIN_SOFT_TOTAL_ALT_MOVE_ARROWS = 3;
/** Minimum search depth for a live alternative to draw. A live alternative is a
 * visible "this is also good" claim, and the first iterations of a MultiPV
 * search still reorder candidates and swing evals, so a shallow line could
 * flash a move that turns out to be an inaccuracy. 10 equals
 * GRADING_DEPTH_FLOOR in lib/engine/gradingLadder.ts, the shallowest depth the
 * app's own move grading trusts; it sits above EvalBar's depth-8 mate floor and
 * below the depth-12 step gate that quick 261009-por dropped because slow
 * phones never reached it inside the 1500 ms movetime. Kept as its own number
 * (not imported) so retuning the bot grading ladder never moves this display
 * gate. Checked on BOTH the top line and the candidate (secondary lines of an
 * iteration can trail the top line by a depth). A device that never reaches it
 * shows the board without live alternatives (fails safe). */
export const TRAIN_LIVE_ALT_MIN_DEPTH = 10;
/** The reveal engine's root width floor for a soft puzzle: the best move plus
 * every alternative slot. */
export const TRAIN_LIVE_ALT_ROOT_MULTIPV = TRAIN_SOFT_TOTAL_ALT_MOVE_ARROWS + 1;
/** No root width floor (sharp and herring draw no live alternatives). */
const NO_ROOT_MULTIPV_FLOOR = 0;

/**
 * The reveal engine's MultiPV floor at the puzzle position. Only a soft puzzle
 * draws live alternatives, so only it pays the shallower root top line of a
 * wider search; sharp and herring keep the settings width.
 */
export function trainRootMultiPvFloor(puzzleType: TrainPuzzleType): number {
  switch (puzzleType) {
    case 'sharp':
      return NO_ROOT_MULTIPV_FLOOR;
    case 'soft':
      return TRAIN_LIVE_ALT_ROOT_MULTIPV;
    case 'herring':
      return NO_ROOT_MULTIPV_FLOOR;
  }
}

/** Normal engine-arrow width (matches Analysis.tsx's
 * STOCKFISH_ENGINE_ARROW_WIDTH) — used for the green good-move arrows. */
export const TRAIN_GOOD_MOVE_ARROW_WIDTH = 0.5;
/** Normal engine-arrow width, same value as TRAIN_GOOD_MOVE_ARROW_WIDTH — a
 * distinct named constant per D-02 (distinct arrow widths), so the
 * played-move arrow's width can be retuned independently later. */
export const TRAIN_PLAYED_MOVE_ARROW_WIDTH = 0.5;
/** Width of the blue best-move arrow — same rationale as the played-move
 * width constant above. */
export const TRAIN_BEST_MOVE_ARROW_WIDTH = 0.5;
/** Thinner width for the game-move arrow (matches Analysis.tsx's
 * NEXT_MOVE_ARROW_WIDTH) — reads as a subtle hint layered over the wider
 * quality arrows, same treatment as the analysis board's translucent white
 * next-move arrow. */
export const TRAIN_GAME_MOVE_ARROW_WIDTH = 0.18;

/** Arrow fill per move quality. 'best' uses the app-wide engine-pointer blue,
 * never a green — the whole point of the 190.1 UAT recolor. */
const QUALITY_ARROW_COLOR: Record<TrainMoveQuality, string> = {
  best: TRAIN_BEST_MOVE_ARROW,
  good: MOVE_QUALITY_GOOD,
  inaccuracy: MOVE_QUALITY_INACCURACY,
  mistake: MOVE_QUALITY_MISTAKE,
  blunder: MOVE_QUALITY_BLUNDER,
};

/**
 * Phase 237 UAT: the color of a reveal chip's board arrow, so the chip can show
 * which arrow it focuses. Mirrors `buildTrainRevealOverlay`: a chip holding the
 * played or best move is drawn in its quality color (blue for best, an unrated
 * played move as good); a game-only chip is the thin white game arrow.
 */
export function chipArrowColor(
  roles: readonly RoleKey[],
  quality: TrainMoveQuality | null,
): string {
  if (roles.includes('best')) return TRAIN_BEST_MOVE_ARROW;
  if (roles.includes('your')) return QUALITY_ARROW_COLOR[quality ?? 'good'];
  return NEXT_MOVE_ARROW;
}

/**
 * Last-move square-highlight color per move quality (190.1 UAT stepping):
 * mirrors useGameOverlay's severity mapping (inaccuracy = the shared yellow),
 * plus blue for an engine-best/engine-line move.
 */
export const TRAIN_STEP_HIGHLIGHT: Record<TrainMoveQuality, string> = {
  best: MOVE_HIGHLIGHT_BEST,
  good: MOVE_HIGHLIGHT_GOOD,
  inaccuracy: MOVE_HIGHLIGHT_SQUARE,
  mistake: MOVE_HIGHLIGHT_MISTAKE,
  blunder: MOVE_HIGHLIGHT_BLUNDER,
};

/**
 * The single blue engine-pointer arrow for one UCI move, or no arrow at all
 * for a null/malformed input. Shared by the reveal stepper and free play so
 * the engine hue and width can never drift between the two surfaces; the
 * distinct `layerKey` keeps them from colliding under `dedupeArrowsByMove`.
 */
function enginePointerArrows(uci: string | null, layerKey: string): BoardArrow[] {
  const squares = squaresFromUci(uci);
  if (squares === null) return [];
  return [
    {
      ...squares,
      color: TRAIN_BEST_MOVE_ARROW,
      width: TRAIN_BEST_MOVE_ARROW_WIDTH,
      layerKey,
    },
  ];
}

/**
 * While stepping a reveal line (190.1 UAT), the PRIMARY arrow on the board is a
 * blue pointer for the line's next move from the shown position (it comes
 * from a Stockfish line, so it reads in the engine hue). Null/absent next
 * move (end of the line) draws nothing. `buildTrainStepOverlayArrows` adds the
 * live engine's secondary arrows underneath it.
 */
export function buildTrainStepArrows(nextMoveUci: string | null): BoardArrow[] {
  return enginePointerArrows(nextMoveUci, 'step-next');
}

/** The from-to squares of a UCI move (drops any promotion suffix), the key the
 * board draws arrows by. */
function fromToKey(uci: string): string {
  return uci.slice(0, 4);
}

/**
 * Quick 261009-por: the live engine lines minus the one whose first move is the
 * known line's next move (compared by from-to squares). On a stepped chip line
 * that move is already the line's own (the solid blue pointer, the chip's eval),
 * so the Stockfish row and the secondary arrows both leave it out. A null next
 * move (end of the line) keeps every line.
 */
export function dropLineMove(pvLines: readonly PvLine[], nextMoveUci: string | null): PvLine[] {
  if (nextMoveUci === null) return [...pvLines];
  const lineKey = fromToKey(nextMoveUci);
  return pvLines.filter((line) => {
    const move = line.moves[0];
    return move === undefined || fromToKey(move) !== lineKey;
  });
}

/**
 * Secondary arrows for the reveal engine's top moves on a stepped position.
 * Walks ranks in reverse (mirroring `buildTrainFreePlayArrows`) and skips
 * malformed first moves and moves that share from-to squares with the line's
 * next move. Every live arrow is
 * secondary-colored, rank 0 included: the line owns the solid blue.
 */
function stepLiveArrows(
  nextMoveUci: string | null,
  pvLines: readonly PvLine[],
  count: number,
): BoardArrow[] {
  const arrows: BoardArrow[] = [];
  const lineKey = nextMoveUci === null ? null : fromToKey(nextMoveUci);
  for (let rank = Math.min(count, pvLines.length) - 1; rank >= 0; rank--) {
    const line = pvLines[rank];
    if (line === undefined) continue;
    const move = line.moves[0] ?? null;
    const squares = squaresFromUci(move);
    if (move === null || squares === null) continue;
    if (fromToKey(move) === lineKey) continue;
    arrows.push({
      ...squares,
      color: STOCKFISH_SECONDARY_LINE,
      width: TRAIN_BEST_MOVE_ARROW_WIDTH,
      layerKey: `step-live-${rank}`,
    });
  }
  return arrows;
}

/**
 * Quick 261009-por: a stepped known-line position keeps the line's blue pointer
 * AND shows the live reveal engine's other top moves (up to `count`, the
 * Stockfish arrows setting) as translucent secondaries, exactly as many as the
 * free-play board draws off the known lines. No depth gate (owner call): the
 * arrows settle as the search deepens, the same as off the known lines, and a
 * gate would leave slow phones with no live arrows at all. The line pointer is
 * pushed LAST so
 * it paints on top (same-tier stable sort in the board's arrow overlay).
 * `pvLines` is the staleness-guarded list for the shown position (empty until
 * the engine reaches it). At the end of a line (`nextMoveUci` null) the live
 * moves draw as secondaries with no primary.
 */
export function buildTrainStepOverlayArrows(
  nextMoveUci: string | null,
  pvLines: readonly PvLine[],
  count: number,
): BoardArrow[] {
  return [...stepLiveArrows(nextMoveUci, pvLines, count), ...buildTrainStepArrows(nextMoveUci)];
}

/**
 * Phase 200 UAT round 5 / Phase 228 (D-13, D-15): while exploring, the board
 * carries the free-play engine's own top moves as blue arrows — exactly what
 * the analysis board shows for its Stockfish engine (same hue, same width).
 * This replaces the original EXPLORE-03 rule of "no arrows at all while
 * exploring": a sideline you cannot see the best answer to is a worse teacher
 * than one you can.
 *
 * The Stockfish arrows setting sets how many live engine arrows draw (`count`,
 * 0-3; 0 draws none). Rank 0 is the solid engine blue, ranks 1..N-1 share the
 * Stockfish translucent color at the SAME width (D-15), pushed in reverse rank
 * order so the primary paints on top. The reveal LEGEND arrows (blue best,
 * green also-fine, game-move) are built elsewhere and always draw (D-13).
 *
 * The caller passes the STALENESS-GUARDED free-play `pvLines`
 * (`TrainFreePlayState.pvLines`), so a position the engine hasn't reached yet
 * simply draws nothing rather than pointing at the previous position's
 * answer. A terminal position (mate/stalemate) yields no PV and therefore no
 * arrow; a line with a malformed first move is skipped.
 */
export function buildTrainFreePlayArrows(pvLines: readonly PvLine[], count: number): BoardArrow[] {
  const arrows: BoardArrow[] = [];
  for (let i = Math.min(count, pvLines.length) - 1; i >= 0; i--) {
    const squares = squaresFromUci(pvLines[i]?.moves[0] ?? null);
    if (squares === null) continue;
    arrows.push({
      ...squares,
      color: i === 0 ? TRAIN_BEST_MOVE_ARROW : STOCKFISH_SECONDARY_LINE,
      width: TRAIN_BEST_MOVE_ARROW_WIDTH,
      layerKey: `free-${i}`,
    });
  }
  return arrows;
}

/**
 * While stepping (190.1 UAT round 4): the line's FIRST move keeps its quality
 * badge on the target square (the squares are already highlighted in the
 * quality color — the badge is the icon on top). Deeper steps are engine
 * continuations and carry no badge. Null quality (tactic-less/unresolved
 * lines) draws nothing.
 */
export function buildTrainStepMarkers(
  lastMoveUci: string,
  quality: TrainMoveQuality | null,
  isFirstMove: boolean,
): SquareMarker[] {
  if (!isFirstMove || quality === null) return [];
  const squares = squaresFromUci(lastMoveUci);
  if (squares === null) return [];
  return [markerForQuality(squares.endSquare, quality)];
}

/** One quality-annotated move for the overlay builder. `quality: null` (game
 * move only) means "not yet known" — arrow drawn, no badge. */
export interface TrainOverlayMove {
  uci: string;
  quality: TrainMoveQuality | null;
}

export interface TrainRevealOverlay {
  arrows: BoardArrow[];
  markers: SquareMarker[];
  /** Phase 200 (LEGEND-04/D-02/D-03) — exactly the alternative fine moves
   * actually drawn as green arrows (never the overflow past the puzzle-type
   * arrow cap), for the reveal sidebar's compact "Also fine" row. Derived in
   * the SAME loop that pushes the arrows themselves, so this can never list a
   * move that isn't on the board or omit one that is. */
  alsoFineMoves: TrainFineMove[];
  /** End square -> the UCI of the move whose badge actually won that square.
   *
   * `pushMarker` dedups by end square under precedence played > best > fine >
   * game, so when two candidate moves share a target square only ONE badge
   * survives — and it belongs to the higher-precedence move. Without this map
   * `buildChipFocusOverlay` could only match markers by square, which let a
   * focused alternative inherit the best move's blue badge (WR-02). Recorded
   * in the same `pushMarker` call that creates the badge, so the two can
   * never drift. */
  markerOwners: Record<string, string>;
}

/**
 * Classify a reveal move's quality from the SAME expected-score pipeline the
 * verdict itself uses (liveFlaw's classifyLiveSeverity — never a new cutoff):
 * the engine's own top move is 'best'; anything whose drop against the
 * pre-move eval isn't even an inaccuracy is 'good'; otherwise the severity.
 */
export function classifyTrainMoveQuality(
  esBefore: number,
  esMove: number,
  isBestMove: boolean,
): TrainMoveQuality {
  if (isBestMove) return 'best';
  return classifyLiveSeverity(esBefore, esMove) ?? 'good';
}

/** Phase 211 (D-01): branches on ALL THREE puzzle types explicitly — the old
 * two-way sharp/non-sharp shape is exactly what would silently cap a herring
 * at the soft budget now that the two budgets differ (RESEARCH Pitfall 6). */
function alternativeArrowCap(puzzleType: TrainPuzzleType): number {
  switch (puzzleType) {
    case 'sharp':
      return TRAIN_SHARP_ALT_MOVE_ARROWS;
    case 'soft':
      return TRAIN_SOFT_ALT_MOVE_ARROWS;
    case 'herring':
      return TRAIN_HERRING_ALT_MOVE_ARROWS;
  }
}

/** UCI ("e2e4"/"e7e8q") -> {startSquare, endSquare}, or null for a null,
 * malformed, or too-short (< 4 chars) input — never throws. */
function squaresFromUci(uci: string | null): { startSquare: string; endSquare: string } | null {
  if (uci === null || uci.length < 4) return null;
  return { startSquare: uci.slice(0, 2), endSquare: uci.slice(2, 4) };
}

/**
 * Phase 200 UAT: the SquareMarker corner badge for one move quality, exported
 * so the reveal tree (`useTreeMoveGrading`) badges a freely played move with
 * exactly the glyph the reveal board would use for the same quality.
 */
export function trainQualityMarker(square: string, quality: TrainMoveQuality): SquareMarker {
  return markerForQuality(square, quality);
}

/** The SquareMarker corner badge for a quality — the same glyph set the
 * analysis board uses (green star / thumbs-up / severity NAG glyphs). */
function markerForQuality(square: string, quality: TrainMoveQuality): SquareMarker {
  if (quality === 'best') return { square, best: true };
  if (quality === 'good') return { square, good: true };
  return { square, severity: quality };
}

/**
 * Builds the reveal board's full overlay (D-02, recolored per 190.1 UAT and
 * Phase 200 D-04/D-05):
 * - a BLUE best-move arrow (the engine's top move) with a 'best' badge
 * - up to `alternativeArrowCap` additional fine-move arrows (soft/herring
 *   only — sharp draws none), always dark green with the 'good' badge, an
 *   inaccuracy-quality alternative included (it is listed as acceptable)
 * - the user's played-move arrow colored by its own quality (inaccuracy is
 *   yellow since quick 261008-opg), with the matching quality badge — merged into the blue arrow when the played move IS the best move
 * - a thin white game-move arrow (drawn on top) for the move played in the
 *   game, with its quality badge once known (`quality: null` = no badge yet)
 *
 * Returns an empty overlay whenever `verdictLanded` is false — nothing may be
 * visible before the attempt is graded. Every arrow gets its own `layerKey`
 * so a coincident from-to pair across roles renders as concentric arrows
 * instead of collapsing under `dedupeArrowsByMove`. Badges are deduped by
 * TARGET SQUARE with precedence played > best > fine > game (the played
 * move's verdict is the one the user is here to learn).
 */
export function buildTrainRevealOverlay(
  puzzleType: TrainPuzzleType,
  fineMoves: TrainFineMove[],
  bestMoveUci: string | null,
  playedMove: TrainOverlayMove | null,
  gameMove: TrainOverlayMove | null,
  verdictLanded: boolean,
): TrainRevealOverlay {
  if (!verdictLanded) return { arrows: [], markers: [], alsoFineMoves: [], markerOwners: {} };

  const arrows: BoardArrow[] = [];
  const markers: SquareMarker[] = [];
  const alsoFineMoves: TrainFineMove[] = [];
  const markedSquares = new Set<string>();
  const markerOwners: Record<string, string> = {};

  function pushMarker(uci: string, quality: TrainMoveQuality | null): void {
    if (quality === null) return;
    const squares = squaresFromUci(uci);
    if (squares === null || markedSquares.has(squares.endSquare)) return;
    markedSquares.add(squares.endSquare);
    markerOwners[squares.endSquare] = uci;
    markers.push(markerForQuality(squares.endSquare, quality));
  }

  // The alternatives actually drawable as green arrows: every fine move that
  // is NOT already drawn as the blue best arrow or the quality-colored played
  // arrow, capped at the puzzle type's alternative budget. Phase 200 UAT
  // round 4: the filter runs BEFORE the slice, so the best move (always rank 1
  // of `fineMoves`) and a played alternative no longer consume alternative
  // slots — see the cap constants' comment for the bug this fixes.
  const alternatives = fineMoves
    .filter((fine) => fine.uci !== bestMoveUci && fine.uci !== playedMove?.uci)
    .slice(0, alternativeArrowCap(puzzleType));

  // Badge precedence pass first (played > best > fine > game), independent of
  // arrow draw order.
  if (playedMove !== null) pushMarker(playedMove.uci, playedMove.quality);
  if (bestMoveUci !== null) pushMarker(bestMoveUci, 'best');
  // "Also fine" alternatives keep the good badge even at inaccuracy quality,
  // matching their always-green arrow below.
  for (const fine of alternatives) {
    pushMarker(fine.uci, fine.quality === 'inaccuracy' ? 'good' : fine.quality);
  }
  if (gameMove !== null) pushMarker(gameMove.uci, gameMove.quality);

  // Played-move arrow, colored by its quality — unless it IS the best move,
  // in which case the blue best arrow below is the single arrow for both.
  const playedIsBest = playedMove !== null && playedMove.uci === bestMoveUci;
  if (playedMove !== null && !playedIsBest) {
    const squares = squaresFromUci(playedMove.uci);
    if (squares !== null) {
      arrows.push({
        ...squares,
        color: QUALITY_ARROW_COLOR[playedMove.quality ?? 'good'],
        width: TRAIN_PLAYED_MOVE_ARROW_WIDTH,
        layerKey: 'played',
      });
    }
  }

  const bestSquares = squaresFromUci(bestMoveUci);
  if (bestSquares !== null) {
    arrows.push({
      ...bestSquares,
      color: TRAIN_BEST_MOVE_ARROW,
      width: TRAIN_BEST_MOVE_ARROW_WIDTH,
      layerKey: 'best',
    });
  }

  // Alternative fine moves (soft/herring rank 2+): always dark green, an
  // inaccuracy-quality alternative included. Moves already
  // drawn as the best or played arrow were filtered out when `alternatives`
  // was built. Every pushed arrow gets a matching `alsoFineMoves` entry in
  // the SAME iteration (Phase 200 LEGEND-04/D-03), so the sidebar row and the
  // board arrows can never drift.
  alternatives.forEach((fine, index) => {
    const squares = squaresFromUci(fine.uci);
    if (squares === null) return;
    arrows.push({
      ...squares,
      color: DARK_GREEN,
      width: TRAIN_GOOD_MOVE_ARROW_WIDTH,
      layerKey: `good-${index}`,
    });
    alsoFineMoves.push(fine);
  });

  const gameSquares = squaresFromUci(gameMove?.uci ?? null);
  if (gameSquares !== null) {
    arrows.push({
      ...gameSquares,
      color: NEXT_MOVE_ARROW,
      width: TRAIN_GAME_MOVE_ARROW_WIDTH,
      onTop: true,
      layerKey: 'game',
    });
  }

  return { arrows, markers, alsoFineMoves, markerOwners };
}

export interface TrainLiveAlternativeContext {
  puzzleType: TrainPuzzleType;
  puzzleFen: string;
  bestMoveUci: string | null;
  playedMoveUci: string | null;
  /** The overlay's alsoFineMoves: the server alternatives actually drawn green. */
  drawnAlternatives: readonly TrainFineMove[];
}

/** True when the line carries a usable score at a trustworthy depth. */
function isScoredLiveLine(line: PvLine): boolean {
  if (line.depth < TRAIN_LIVE_ALT_MIN_DEPTH) return false;
  return line.evalCp !== null || line.evalMate !== null;
}

/**
 * Quick 261010-e5l: the soft puzzle's live-engine alternatives, drawn at the
 * puzzle position next to the server-certified one. Walks the root search's
 * lines 1.. in rank order and keeps those that classify as good (no
 * inaccuracy or worse, mover POV, via the app's own classifyLiveSeverity) once
 * both the top line and the candidate reach TRAIN_LIVE_ALT_MIN_DEPTH. Fills
 * the slots the server alternatives left of TRAIN_SOFT_TOTAL_ALT_MOVE_ARROWS.
 *
 * Skipped lines (shallow, unscored, malformed, excluded or an inaccuracy) never
 * consume a slot. Excluded: the best arrow, the played move, every drawn server
 * alternative and an earlier live line on the same squares. The game move is
 * deliberately NOT excluded: server alternatives are not filtered against it
 * either, the game arrow is a thin white hint that can be a bad move while a
 * wide translucent arrow under it adds the "also a good move" fact, and under
 * chip focus both arrows match the Game chip by squares and light together.
 *
 * Owner UAT 2026-10-10: live alternatives are presented exactly like the
 * certified ones (green arrow, 'good' badge, listed in the "Also fine" text);
 * the original faint blue, badge-less, unlisted styling made the same "also a
 * good move" fact read as a different kind of move. Sharp draws none (one
 * right move), herring keeps its own certified ladder.
 *
 * Returns null while the root search is not yet trustworthy (top line
 * shallow or unscored), so a caller can keep the last settled list instead of
 * flashing an empty one; [] when it is settled and nothing qualifies.
 */
export function buildTrainLiveAlternatives(
  context: TrainLiveAlternativeContext,
  rootPvLines: readonly PvLine[],
): TrainFineMove[] | null {
  if (context.puzzleType !== 'soft') return [];
  const slots = Math.max(0, TRAIN_SOFT_TOTAL_ALT_MOVE_ARROWS - context.drawnAlternatives.length);
  if (slots === 0) return [];
  const top = rootPvLines[0];
  if (top === undefined || !isScoredLiveLine(top)) return null;

  const mover = sideToMoveFromFen(context.puzzleFen);
  const esTop = evalToExpectedScore(top.evalCp, top.evalMate, mover);
  const drawn = new Set<string>();
  for (const uci of [context.bestMoveUci, context.playedMoveUci]) {
    if (uci !== null) drawn.add(fromToKey(uci));
  }
  for (const fine of context.drawnAlternatives) drawn.add(fromToKey(fine.uci));

  const alternatives: TrainFineMove[] = [];
  for (let index = 1; index < rootPvLines.length && alternatives.length < slots; index++) {
    const line = rootPvLines[index];
    if (line === undefined || !isScoredLiveLine(line)) continue;
    const move = line.moves[0] ?? null;
    if (squaresFromUci(move) === null || move === null || drawn.has(fromToKey(move))) continue;
    const esLine = evalToExpectedScore(line.evalCp, line.evalMate, mover);
    if (classifyLiveSeverity(esTop, esLine) !== null) continue;
    drawn.add(fromToKey(move));
    alternatives.push({ uci: move, quality: 'good' });
  }
  return alternatives;
}

/** A live alternative's board arrow: the certified alternatives' green arrow. */
function liveAlternativeArrows(liveAlternatives: readonly TrainFineMove[]): BoardArrow[] {
  return liveAlternatives.flatMap((fine, index) => {
    const squares = squaresFromUci(fine.uci);
    if (squares === null) return [];
    return [{ ...squares, color: DARK_GREEN, width: TRAIN_GOOD_MOVE_ARROW_WIDTH, layerKey: `live-alt-${index}` }];
  });
}

/**
 * The overlay's badges plus a 'good' badge for each live alternative, at the
 * lowest precedence (after played > best > fine > game): a live badge only
 * takes a square no overlay badge owns, so it never steals the game move's
 * square.
 */
function withLiveAlternativeBadges(
  overlay: TrainRevealOverlay,
  liveAlternatives: readonly TrainFineMove[],
): Pick<TrainRevealOverlay, 'markers' | 'markerOwners'> {
  // Keep the overlay's own objects when there is nothing to add (pass-through identity).
  if (liveAlternatives.length === 0) return overlay;
  const markers = [...overlay.markers];
  const markerOwners = { ...overlay.markerOwners };
  for (const fine of liveAlternatives) {
    const squares = squaresFromUci(fine.uci);
    if (squares === null || markerOwners[squares.endSquare] !== undefined) continue;
    markerOwners[squares.endSquare] = fine.uci;
    markers.push(markerForQuality(squares.endSquare, 'good'));
  }
  return { markers, markerOwners };
}

/**
 * Phase 237 (D-04) — the board-side half of the reveal's chip focus. DIMS a
 * reveal overlay instead of filtering it: every arrow and quality badge stays
 * on the board, the ones belonging to `activeUcis` are drawn near-opaque, the
 * rest fade to a low opacity ("the other arrows fade to ~20-30%, never
 * hidden"). The pristine board and a focused one go through this same
 * function; only the active set differs.
 *
 * Arrows match on UCI move identity (`startSquare`+`endSquare`), never on
 * `layerKey`: a coincidence-merged role (e.g. Move = Game) carries a colored
 * arrow and a thin white on-top arrow with DIFFERENT `layerKey`s for the SAME
 * move, and both must light together. A lit arrow gets `onTop: true` and a
 * dimmed one `onTop: false`, so the focused move paints above the faded ones
 * (this deliberately overrides the game arrow's own `onTop` while dimmed).
 *
 * Markers match by badge OWNERSHIP (`markerOwners`), not by end-square
 * membership (WR-02): two candidate moves can share a target square, only the
 * higher-precedence badge survives `pushMarker`, and a focused alternative
 * must not light the best move's badge. An unowned square dims.
 *
 * A null or empty `activeUcis` dims every arrow and badge (no active move).
 * A malformed UCI (< 4 chars) contributes no match and never throws.
 * `alsoFineMoves` passes through unchanged; `markerOwners` gains only the
 * live alternatives' badges.
 *
 * Quick 261010-e5l: `liveAlternatives` (the soft root's live engine alternatives) are
 * never chips, same as server alternatives, so like them they dim at the root
 * unless the focused chip's move shares their squares, and each gets the same
 * 'good' badge (`withLiveAlternativeBadges`). They are returned before the
 * overlay's arrows.
 */
export function buildChipFocusOverlay(
  overlay: TrainRevealOverlay,
  activeUcis: readonly string[] | null,
  liveAlternatives: readonly TrainFineMove[] = [],
): TrainRevealOverlay {
  const active = activeUcis ?? [];
  const activePairs = active
    .map((uci) => squaresFromUci(uci))
    .filter((squares): squares is { startSquare: string; endSquare: string } => squares !== null);
  const activeUciSet = new Set(active);

  function arrowIsLit(arrow: BoardArrow): boolean {
    return activePairs.some(
      (pair) => arrow.startSquare === pair.startSquare && arrow.endSquare === pair.endSquare,
    );
  }

  const { markers, markerOwners } = withLiveAlternativeBadges(overlay, liveAlternatives);

  function markerIsLit(marker: SquareMarker): boolean {
    const ownerUci = markerOwners[marker.square];
    return ownerUci !== undefined && activeUciSet.has(ownerUci);
  }

  function focusArrow(arrow: BoardArrow): BoardArrow {
    const lit = arrowIsLit(arrow);
    return {
      ...arrow,
      opacity: lit ? TRAIN_FOCUS_ARROW_LIT_OPACITY : TRAIN_FOCUS_ARROW_DIM_OPACITY,
      onTop: lit,
    };
  }

  return {
    ...overlay,
    // Live alternatives first: they paint beneath the certified arrows within a tier.
    arrows: [...liveAlternativeArrows(liveAlternatives), ...overlay.arrows].map(focusArrow),
    markerOwners,
    markers: markers.map((marker) => ({
      ...marker,
      opacity: markerIsLit(marker) ? TRAIN_FOCUS_BADGE_LIT_OPACITY : TRAIN_FOCUS_BADGE_DIM_OPACITY,
    })),
  };
}
