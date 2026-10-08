/**
 * Pure, React-free pieces of useTrainGradingEngine (review WR-02): the search
 * and grade types, the key-anchor builders, terminal-position scoring, the
 * bestmove commit, the disagreement re-check plan/finish stages, and the shared
 * settle-once timeout race. Nothing here touches a Worker or a ref, so each
 * piece is a plain function of its inputs.
 */

import { Chess } from 'chess.js';
import type { PvLine } from './uciParser';
import { dedupePvLinesByFirstMove } from './uciParser';
import { classifyLiveSeverity, evalToExpectedScore, sideToMoveFromFen } from '@/lib/liveFlaw';
import type { MoverColor } from '@/lib/liveFlaw';
import { moveTierFromSeverity } from '@/lib/trainScore';
import type { TrainMoveTier } from '@/lib/trainScore';
import type { PhoneReading } from '@/lib/trainPhoneGrade';
import { buildRecheckPayload, recheckOutcome } from '@/lib/trainRecheck';
import type { SolveRecheck, SolveResponse } from '@/types/train';

// ─── Types ──────────────────────────────────────────────────────────────────

export interface RawSearchResult {
  /** White-POV centipawns (already sign-normalized for the searched FEN). */
  evalCp: number | null;
  evalMate: number | null;
  bestMoveUci: string | null;
  /** Engine depth of the top (multipv 1) exact line; null when no exact line
   * arrived, 0 for a terminal position scored without a search (Phase 235
   * D-17: recorded with the re-check). */
  depth: number | null;
  /** UCI moves following the top (multipv 1) line's `pv` keyword — mover-POV
   * move list, not sign-dependent (190.1-01: captured for the reveal-time
   * lines, previously parsed but discarded). */
  pv: string[];
  /**
   * Every rank the engine returned for this search, sorted by `multipv`
   * ascending and white-POV sign-normalized (190.1-02 D-01 point 1). As of
   * Phase 211 (D-05) EVERY search this hook dispatches — mount, after-move,
   * reveal-time — is width 1, so this normally holds exactly one entry
   * (rank 1, whose convenience values are `evalCp`/`evalMate`/`pv` above).
   * The array shape is kept because the commit path is width-agnostic; as of
   * Phase 235 no consumer reads it any more (the anchor owns the key line, and
   * `startGameMoveSearch` compares against the key instead of an exact-UCI rank
   * lookup), and it never left this hook. Never assume
   * `lines.length` equals the requested width: the engine returns only as
   * many ranks as there are legal moves and never pads — nor that every
   * rank holds a DISTINCT move before `dedupePvLinesByFirstMove` runs at
   * commit time (see that helper for the cross-iteration staleness this
   * drops); after it, every entry's first move is unique.
   */
  lines: PvLine[];
}

/**
 * The settled think-time search for the puzzle most recently passed to
 * `startGrading` (Phase 235, replaces the old root-search result). `keyLine`
 * moves are rooted at the PUZZLE fen and `es` is the mover-POV expected score
 * of `keyLine`. `legacy` is true when the anchor came from a root search
 * (D-07: null, missing or illegal key), where `keyUci` is that search's own
 * bestmove.
 */
export interface GradingAnchor {
  fen: string;
  generation: number;
  keyUci: string | null;
  keyLine: TrainEngineLine;
  es: number;
  /** Engine depth of the anchor search (Phase 235 D-17), null when none was reported. */
  depth: number | null;
  legacy: boolean;
  /**
   * True after a CONFIRMED re-check swapped this anchor for the 3 s key line
   * (Phase 235 D-16): the game-move search then shows the phone's honest eval
   * instead of clamping it to the key line. False everywhere else.
   */
  unclamped: boolean;
}

/** A finished re-check plus the 3 s anchor it would install (see `recheckMove`). */
export interface RecheckInnerResult {
  result: RecheckResult;
  anchor: GradingAnchor;
}

export interface GradeResult {
  /** SEED-119: the three-way move-quality tier, derived from
   * `classifyLiveSeverity` via `moveTierFromSeverity` — never a re-derived
   * boolean. `moveTier !== 'wrong'` is what feeds the SR ladder verdict. */
  moveTier: TrainMoveTier;
  /** Phase 235 (D-09): the server key on the keyed path (the root search's
   * bestmove on the legacy D-07 path), so the reveal arrow and BEST MOVE box
   * name the key even when the phone's own search would prefer another move. */
  bestMoveUci: string | null;
  /** Phase 235 (D-01): the phone's expected score after the KEY (mover POV);
   * the root ES on the legacy path. */
  esBefore: number;
  esAfter: number;
  /** The key line: `[keyUci, ...afterKeySearch.pv]` rooted at the puzzle fen
   * (D-09), derived at think time without any additional search. */
  bestLine: TrainEngineLine;
  /**
   * The played move's own line. When the played move IS the key this is
   * exactly `bestLine`. Otherwise it comes from the after-move grading search
   * (`[playedMoveUci, ...afterSearch.pv]`), with the displayed eval clamped to
   * never read better than the key line's (D-09).
   */
  playedLine: TrainEngineLine;
  /**
   * Phase 236 (D-01/D-04): the 1.5 s reading for the phone_grade record. Null
   * or absent on the legacy root anchor (D-06), on the defensive fallbacks and
   * on a re-check's replacement grade. Optional because restored reveal-cache
   * entries predate it.
   */
  phoneReading?: PhoneReading | null;
}

/**
 * One reveal-time engine line (190.1-01, D-01/D-03). `moves` are UCI strings
 * rooted at the PUZZLE's fen — not the position after any move — the
 * invariant shared by all three reveal lines (YOUR MOVE / BEST MOVE /
 * PLAYED IN GAME) so a single replay-from-puzzle-fen call always applies.
 * `evalCp`/`evalMate` are white-POV, matching every other eval in this file.
 */
export interface TrainEngineLine {
  moves: string[];
  evalCp: number | null;
  evalMate: number | null;
}

/**
 * Optional hooks into a `gradeMove` call. Phase 236 D-14: the instant path
 * renders the solution card from the think-time after-key line as soon as the
 * anchor has settled, before the played move's search finishes.
 */
export interface GradeMoveOptions {
  /** Called at most once per `gradeMove`, with the think-time after-key line.
   * Never called for a legacy (null key) root anchor. */
  onKeyLine?: (keyLine: TrainEngineLine) => void;
}

/** Phase 236 D-14/D-15: where a server-graded move's background phone grade is. */
export type InstantGradeStatus = 'pending' | 'failed';

/**
 * Phase 236 D-14/D-15: the reveal's view of a server-graded move whose phone
 * grade has not landed. `keyLine` is the think-time after-key line, set once
 * the anchor has settled (null before that). The solve screen holds `null`
 * when no instant grade is outstanding (the normal path, or the grade landed).
 */
export interface InstantGradeState {
  status: InstantGradeStatus;
  keyUci: string;
  keyLine: TrainEngineLine | null;
}

/**
 * Phase 236 review WR-02: a stand-in GradeResult for the reveal cache, used when
 * Analyze is pressed before the instant path's background grade landed. Without
 * it the click cached nothing, so browser Back lost the solved reveal (a resumed
 * session no longer contains the solved puzzle). Every number is the SERVER's
 * graded pair from the verdict (never a fabricated 0.5), the key line is the
 * think-time one when the anchor had settled, and the played-move line is empty,
 * so the restored Your-move card is the header-only card of the D-15 failed
 * state. `phoneReading` is null: the search ends with the unmount, so this solve
 * records no phone_grade (accepted gap). Returns null when the verdict carries no
 * server pair, where the caller keeps the old no-cache behaviour.
 */
export function gradeFromServerPair(verdict: SolveResponse, instant: InstantGradeState): GradeResult | null {
  const esBefore = verdict.graded_es_before;
  const esAfter = verdict.graded_es_after;
  if (esBefore == null || esAfter == null) return null;
  return {
    moveTier: verdict.move_quality,
    bestMoveUci: instant.keyUci,
    esBefore,
    esAfter,
    bestLine: instant.keyLine ?? { moves: [], evalCp: null, evalMate: null },
    playedLine: { moves: [], evalCp: null, evalMate: null },
    phoneReading: null,
  };
}

/**
 * A completed disagreement re-check (Phase 235 D-11/D-13/D-17): `grade` replaces
 * the 1.5 s grade whatever it says, `recheck` is the record that rides the
 * solve POST.
 */
export interface RecheckResult {
  grade: GradeResult;
  recheck: SolveRecheck;
}

// ─── Helpers ────────────────────────────────────────────────────────────────

/** Build the legacy root anchor's key line from a settled root search: rank
 * 1's PV, falling back to a single-element array containing the bestmove token
 * when the PV is empty (190.1-02 D-01 point 1). */
function bestLineFrom(best: RawSearchResult): TrainEngineLine {
  const moves = best.pv.length > 0 ? best.pv : best.bestMoveUci !== null ? [best.bestMoveUci] : [];
  return { moves, evalCp: best.evalCp, evalMate: best.evalMate };
}

/**
 * Bug fix (190.1 UAT round 9; rationale narrowed by Phase 211): a played/game
 * move evaluated by its own after-move search occasionally READS better than
 * the best move (e.g. your Ke4 −4.5 vs best Ke5 −4.0). With the mount search
 * at width 1 (Phase 211 D-05) the node budget is no longer split across
 * ranks, so the surviving causes are the after-move search spending its
 * budget one ply DEEPER than the mount search, and ordinary cross-search cp
 * variance in decided positions (project_eval_nondeterminism). The verdict
 * already treats "better than best" as correct; this clamp only stops the
 * DISPLAYED eval from contradicting the "best move" label. From the mover's
 * POV the shown eval is capped at the best line's eval; the line's moves are
 * untouched.
 */
export function clampLineEvalToBest(
  line: TrainEngineLine,
  best: TrainEngineLine,
  mover: MoverColor,
): TrainEngineLine {
  const esLine = evalToExpectedScore(line.evalCp, line.evalMate, mover);
  const esBest = evalToExpectedScore(best.evalCp, best.evalMate, mover);
  if (esLine <= esBest) return line;
  return { ...line, evalCp: best.evalCp, evalMate: best.evalMate };
}

/** Convert a UCI move string ("e2e4", "e7e8q") applied to `fen` into the
 * resulting FEN, or null on illegal/malformed input. */
export function fenAfterUciMove(fen: string, uci: string): string | null {
  if (uci.length < 4) return null;
  try {
    const chess = new Chess(fen);
    const move = chess.move({
      from: uci.slice(0, 2),
      to: uci.slice(2, 4),
      promotion: uci.length > 4 ? uci.slice(4, 5) : undefined,
    });
    if (!move) return null;
    return chess.fen();
  } catch {
    return null;
  }
}

/**
 * Mate distance reported for a delivered mate. `evalToExpectedScore` reads only
 * the SIGN of a non-zero mate, so any positive distance is equivalent; 1
 * matches what the old root search reported for a mate-in-one key.
 */
const DELIVERED_MATE_DISTANCE = 1;

/**
 * Bug fix (Phase 235): the vendored Stockfish answers a mated or stalemated FEN
 * with `mate 0` or no score at all, which `evalToExpectedScore` reads as a
 * neutral 0.5. A mating key anchored at 0.5 would let any decent move grade
 * good, and a non-best mating move was already graded as a blunder before this
 * phase. A position with no legal moves is scored directly instead of being
 * searched: checkmate is a delivered mate for the side that just moved (the
 * side to move is mated), stalemate is a draw. Returns null for a normal
 * position, which is searched.
 */
export function terminalSearchResult(fen: string): RawSearchResult | null {
  let chess: Chess;
  try {
    chess = new Chess(fen);
  } catch {
    return null;
  }
  if (chess.isCheckmate()) {
    const sideToMove = fen.split(' ')[1];
    return {
      evalCp: null,
      // White-POV: black to move and mated means white delivered the mate.
      evalMate: sideToMove === 'b' ? DELIVERED_MATE_DISTANCE : -DELIVERED_MATE_DISTANCE,
      bestMoveUci: null,
      depth: 0,
      pv: [],
      lines: [],
    };
  }
  if (chess.isStalemate()) {
    return { evalCp: 0, evalMate: null, bestMoveUci: null, depth: 0, pv: [], lines: [] };
  }
  return null;
}

/** Phase 235 (D-08): the keyed anchor from the settled after-key search. The
 * raw eval is already white-POV, so `evalToExpectedScore` with the PUZZLE mover
 * yields a value directly comparable with the after-played search. */
export function keyedAnchorFrom(
  fen: string,
  generation: number,
  keyUci: string,
  raw: RawSearchResult,
): GradingAnchor {
  return {
    fen,
    generation,
    keyUci,
    keyLine: { moves: [keyUci, ...raw.pv], evalCp: raw.evalCp, evalMate: raw.evalMate },
    es: evalToExpectedScore(raw.evalCp, raw.evalMate, sideToMoveFromFen(fen)),
    depth: raw.depth,
    legacy: false,
    unclamped: false,
  };
}

/** Phase 235 (D-07): the legacy anchor from a root search, exactly today's. */
export function legacyAnchorFrom(fen: string, generation: number, raw: RawSearchResult): GradingAnchor {
  return {
    fen,
    generation,
    keyUci: raw.bestMoveUci,
    keyLine: bestLineFrom(raw),
    es: evalToExpectedScore(raw.evalCp, raw.evalMate, sideToMoveFromFen(fen)),
    depth: raw.depth,
    legacy: true,
    unclamped: false,
  };
}

/** The 1.5 s after-played search of the move `gradeMoveInner` most recently
 * graded (Phase 235 D-17): the re-check needs its ES and depth for the record,
 * and matches on generation and move so it never reads a stale one. */
export interface LastPlayedSearch {
  generation: number;
  playedUci: string;
  es: number;
  depth: number | null;
}

// ─── Bestmove commit ────────────────────────────────────────────────────────

/**
 * 190.1-02: commit the accumulated MultiPV map, sorted by rank and sign-normalized
 * to white POV, exactly once at `bestmove`. Never assume the requested width was
 * returned (the map may have fewer entries than requested); a width-1 search
 * still yields one entry.
 */
export function buildSearchResult(
  pvMap: ReadonlyMap<number, PvLine>,
  whitePovSign: 1 | -1,
  bestMoveUci: string | null,
): RawSearchResult {
  const lines: PvLine[] = dedupePvLinesByFirstMove(
    [...pvMap.values()].sort((a, b) => a.multipv - b.multipv),
  ).map((l) => ({
    ...l,
    evalCp: l.evalCp === null ? null : l.evalCp * whitePovSign,
    evalMate: l.evalMate === null ? null : l.evalMate * whitePovSign,
  }));
  const rank1 = lines[0];
  return {
    evalCp: rank1 !== undefined ? rank1.evalCp : null,
    evalMate: rank1 !== undefined ? rank1.evalMate : null,
    bestMoveUci,
    depth: rank1 !== undefined ? rank1.depth : null,
    pv: rank1 !== undefined ? rank1.moves : [],
    lines,
  };
}

// ─── Disagreement re-check: plan -> (two searches in the hook) -> finish ───

/** Everything the re-check needs once its preconditions hold. The FAST (1.5 s)
 * values are captured here, before any re-check search can replace them. */
export interface RecheckPlan {
  fen: string;
  generation: number;
  playedMoveUci: string;
  keyUci: string;
  afterKeyFen: string;
  afterPlayedFen: string;
  keyEs: number;
  keyDepth: number | null;
  playedEs: number;
  playedDepth: number | null;
}

/**
 * Phase 235 (D-10): null when there is nothing coherent to re-check (anchor
 * mismatch, legacy anchor, played == key, no recorded 1.5 s played search,
 * illegal after-move FEN).
 */
export function planRecheck(
  fen: string,
  playedMoveUci: string,
  generation: number,
  anchor: GradingAnchor | null,
  lastPlayed: LastPlayedSearch | null,
): RecheckPlan | null {
  if (
    !anchor ||
    anchor.generation !== generation ||
    anchor.fen !== fen ||
    anchor.legacy ||
    anchor.keyUci === null ||
    playedMoveUci === anchor.keyUci ||
    !lastPlayed ||
    lastPlayed.generation !== generation ||
    lastPlayed.playedUci !== playedMoveUci
  ) {
    return null;
  }
  const keyUci = anchor.keyUci;
  const afterKeyFen = fenAfterUciMove(fen, keyUci);
  const afterPlayedFen = fenAfterUciMove(fen, playedMoveUci);
  if (afterKeyFen === null || afterPlayedFen === null) return null;
  return {
    fen,
    generation,
    playedMoveUci,
    keyUci,
    afterKeyFen,
    afterPlayedFen,
    keyEs: anchor.es,
    keyDepth: anchor.depth,
    playedEs: lastPlayed.es,
    playedDepth: lastPlayed.depth,
  };
}

/** Grade the two 3 s searches with the same `classifyLiveSeverity` as the 1.5 s
 * pair (D-11) and build the record plus the anchor the re-check would install. */
export function finishRecheck(
  plan: RecheckPlan,
  keyRaw: RawSearchResult,
  playedRaw: RawSearchResult,
): RecheckInnerResult {
  const { fen, generation, playedMoveUci, keyUci } = plan;
  const mover = sideToMoveFromFen(fen);
  const keyEsRecheck = evalToExpectedScore(keyRaw.evalCp, keyRaw.evalMate, mover);
  const playedEsRecheck = evalToExpectedScore(playedRaw.evalCp, playedRaw.evalMate, mover);
  const moveTier = moveTierFromSeverity(classifyLiveSeverity(keyEsRecheck, playedEsRecheck));
  const outcome = recheckOutcome(moveTier);

  const keyLine: TrainEngineLine = {
    moves: [keyUci, ...keyRaw.pv],
    evalCp: keyRaw.evalCp,
    evalMate: keyRaw.evalMate,
  };
  const rawPlayedLine: TrainEngineLine = {
    moves: [playedMoveUci, ...playedRaw.pv],
    evalCp: playedRaw.evalCp,
    evalMate: playedRaw.evalMate,
  };
  // D-16: a confirmed re-check shows the phone's honest eval; a resolved
  // one is capped at the (3 s) key line like any off-key played line.
  const playedLine =
    outcome === 'confirmed' ? rawPlayedLine : clampLineEvalToBest(rawPlayedLine, keyLine, mover);
  return {
    result: {
      grade: {
        moveTier,
        bestMoveUci: keyUci,
        esBefore: keyEsRecheck,
        esAfter: playedEsRecheck,
        bestLine: keyLine,
        playedLine,
      },
      recheck: buildRecheckPayload({
        outcome,
        keyEs: plan.keyEs,
        playedEs: plan.playedEs,
        keyDepth: plan.keyDepth,
        playedDepth: plan.playedDepth,
        keyEsRecheck,
        playedEsRecheck,
        keyDepthRecheck: keyRaw.depth,
        playedDepthRecheck: playedRaw.depth,
      }),
    },
    // The 3 s key reading becomes the anchor, so the reveal's game line is
    // judged against it (clamped when resolved, honest when confirmed, D-16).
    anchor: {
      fen,
      generation,
      keyUci,
      keyLine,
      es: keyEsRecheck,
      depth: keyRaw.depth,
      legacy: false,
      unclamped: outcome === 'confirmed',
    },
  };
}

// ─── Settle-once timeout race ───────────────────────────────────────────────

/**
 * Races `work` against `timeoutMs` so the returned promise ALWAYS settles, and
 * settles exactly once: whichever of the work and the timer finishes first wins,
 * the loser is ignored. On timeout it rejects with `timeoutMessage` AND aborts the
 * `signal` handed to `work`, so work that is still running (a multi-search
 * pipeline) can stop dispatching further engine searches instead of running on
 * as a zombie (review WR-01). A non-Error rejection from `work` is normalized to
 * `new Error(failureMessage)`.
 */
export function raceWithTimeout<T>(
  work: (signal: AbortSignal) => Promise<T>,
  timeoutMs: number,
  timeoutMessage: string,
  failureMessage: string,
): Promise<T> {
  return new Promise<T>((resolve, reject) => {
    const controller = new AbortController();
    let settled = false;
    const timer = setTimeout(() => {
      if (settled) return;
      settled = true;
      controller.abort();
      reject(new Error(timeoutMessage));
    }, timeoutMs);
    work(controller.signal).then(
      (value) => {
        if (settled) return;
        settled = true;
        clearTimeout(timer);
        resolve(value);
      },
      (error: unknown) => {
        if (settled) return;
        settled = true;
        clearTimeout(timer);
        reject(error instanceof Error ? error : new Error(failureMessage));
      },
    );
  });
}
