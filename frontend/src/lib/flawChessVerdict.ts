/**
 * flawChessVerdict — pure, worker-free, chess.js-free classification module for
 * the FlawChess-vs-Stockfish agreement verdict on the `/analysis` page (Phase
 * 157, REVIEW-02). Compares FlawChess's practical #1 pick
 * (`flawChessEngine.rankedLines[0]`) against Stockfish's objective #1 pick
 * (`engine.pvLines[0]`) and classifies the pair into one of three tiers:
 *   - aligned (D-04): the two engines pick the SAME UCI move.
 *   - safe (D-05): different moves, but the expected-score drop sacrificed by
 *     playing FlawChess's practical pick instead of Stockfish's objective best
 *     is strictly below SHARP_DROP_THRESHOLD.
 *   - sharp (D-05): different moves, expected-score drop at or above SHARP_DROP_THRESHOLD
 *     (a "trap" — objectively best but too costly/hard for a human).
 * Returns `null` (D-06) whenever either side's objective eval hasn't arrived
 * yet — never a bogus tier from a partial snapshot.
 *
 * Reuses evalToExpectedScore's Lichess winning-chances sigmoid (@/lib/liveFlaw) rather
 * than re-deriving it, and BLUNDER_DROP (@/generated/flawThresholds) as the
 * sharp/safe threshold rather than a fresh hand-picked constant.
 */

import type { RankedLine } from '@/lib/engine/types';
import type { PvLine } from '@/hooks/uciParser';
import { evalToExpectedScore, type MoverColor } from '@/lib/liveFlaw';
import { BLUNDER_DROP } from '@/generated/flawThresholds';
import { FLAWCHESS_ENGINE_ARROW, BEST_MOVE_ARROW } from '@/lib/theme';

// ─── Types ──────────────────────────────────────────────────────────────────

/** How the FlawChess practical pick relates to Stockfish's objective pick. */
export type FlawChessVerdictTier = 'aligned' | 'safe' | 'sharp';

/** One engine's pick, ready to render as an interactive move span + board arrow. */
export interface FlawChessVerdictMove {
  uci: string;
  role: 'flawchess' | 'stockfish';
  /** White-POV centipawns. Null on the FlawChess side when the pick grades to a forced mate (evalMate set instead). */
  evalCp: number | null;
  /** White-POV mate distance, when the pick grades to a forced mate (quick 260709 threaded RankedLine.objectiveEvalMate through). */
  evalMate: number | null;
  textColor: string;
  arrowColor: string;
}

export interface FlawChessVerdictResult {
  tier: FlawChessVerdictTier;
  flawChessMove: FlawChessVerdictMove;
  stockfishMove: FlawChessVerdictMove;
  /** Expected-score drop sacrificed by the FlawChess pick vs Stockfish's objective pick, from the mover's POV. Always >= 0 (D-06). */
  drop: number;
  /** Raw white-POV centipawn gap |Stockfish best − FlawChess pick| between the two DISPLAYED objective evals, or null when either side is a mate score. */
  objectiveEvalGapCp: number | null;
  /** True only when both objective evals are non-mate and within NEARLY_SAME_EVAL_CP — gates the 'safe' tier's "nearly the same eval" wording so the prose can't contradict the rendered numbers. */
  nearlySameEval: boolean;
}

/** Sharp/trap at or above this expected-score drop (D-05). Imported alias, not a bare literal, so it never drifts from the generated threshold. */
export const SHARP_DROP_THRESHOLD = BLUNDER_DROP;

/**
 * Raw-centipawn gap (white-POV, |Stockfish best − FlawChess pick|) at or below which the 'safe'
 * prose may still call the two picks "nearly the same eval". The tier split itself stays in
 * expected-score space (correct: a 150cp swing matters far more near equality than at +6), but
 * that sigmoid saturates — a ~1.5-pawn gap between two already-winning evals still lands under
 * SHARP_DROP_THRESHOLD. So the copy additionally checks the raw centipawns it actually renders and
 * drops the "nearly the same eval" claim when the shown numbers visibly differ. ~0.5 pawn.
 */
export const NEARLY_SAME_EVAL_CP = 50;

// ─── computeFlawChessVerdict ────────────────────────────────────────────────

/**
 * Classifies the FlawChess-vs-Stockfish pick pair, or returns `null` when the
 * snapshot is incomplete (D-06): either line is missing, the FlawChess
 * objective eval hasn't arrived, or the Stockfish line has no eval at all.
 */
export function computeFlawChessVerdict(
  flawChessLine: RankedLine | null,
  stockfishLine: PvLine | null,
  mover: MoverColor,
): FlawChessVerdictResult | null {
  if (flawChessLine == null || stockfishLine == null) return null;
  // A forced-mate leaf grades to evalMate (cp null), so accept either — bailing on a
  // null cp alone dropped the whole verdict on mate lines, surfacing the muted
  // "Turn on Stockfish" prompt even with Stockfish on (quick 260709).
  if (flawChessLine.objectiveEvalCp == null && flawChessLine.objectiveEvalMate == null) return null;

  const sfMoveUci = stockfishLine.moves[0];
  if (sfMoveUci === undefined) return null;

  const sfEvalCp = stockfishLine.evalCp;
  const sfEvalMate = stockfishLine.evalMate;
  if (sfEvalCp == null && sfEvalMate == null) return null;

  const flawChessMove: FlawChessVerdictMove = {
    uci: flawChessLine.rootMove,
    role: 'flawchess',
    evalCp: flawChessLine.objectiveEvalCp,
    evalMate: flawChessLine.objectiveEvalMate,
    textColor: FLAWCHESS_ENGINE_ARROW,
    arrowColor: FLAWCHESS_ENGINE_ARROW,
  };
  const stockfishMove: FlawChessVerdictMove = {
    uci: sfMoveUci,
    role: 'stockfish',
    evalCp: sfEvalCp,
    evalMate: sfEvalMate,
    textColor: BEST_MOVE_ARROW,
    arrowColor: BEST_MOVE_ARROW,
  };

  // Raw white-POV centipawn gap between the two evals the prose actually renders. Null when EITHER
  // side is a mate score (a forced mate vs a cp eval is never "nearly the same eval") — including
  // the FlawChess side, whose objectiveEvalCp is null on a mate leaf (quick 260709).
  const objectiveEvalGapCp =
    sfEvalCp == null || flawChessLine.objectiveEvalCp == null
      ? null
      : Math.abs(sfEvalCp - flawChessLine.objectiveEvalCp);
  const nearlySameEval = objectiveEvalGapCp != null && objectiveEvalGapCp <= NEARLY_SAME_EVAL_CP;

  // D-04: aligned check is UCI-string equality, done BEFORE the drop split.
  if (flawChessLine.rootMove === sfMoveUci) {
    return { tier: 'aligned', flawChessMove, stockfishMove, drop: 0, objectiveEvalGapCp, nearlySameEval };
  }

  const fcExpectedScore = evalToExpectedScore(flawChessLine.objectiveEvalCp, flawChessLine.objectiveEvalMate, mover);
  const sfExpectedScore = evalToExpectedScore(sfEvalCp, sfEvalMate, mover);
  // The max() is load-bearing, not merely defensive: fcExpectedScore derives from the FlawChess
  // pick's objectiveEvalCp — a move-restricted grade from a DIFFERENT Stockfish search than
  // Stockfish's PV — so it can exceed sfExpectedScore (the pick graded "better" than the objective
  // best, e.g. Qc7 +2.8 vs O-O +1.3 when the two searches disagree). A sacrifice can't be negative,
  // so clamp to 0; the prose relies on nearlySameEval (raw cp), not this drop, to avoid narrating
  // that cross-search disagreement as "nearly the same eval".
  const drop = Math.max(0, sfExpectedScore - fcExpectedScore);

  const tier: FlawChessVerdictTier = drop < SHARP_DROP_THRESHOLD ? 'safe' : 'sharp';

  return { tier, flawChessMove, stockfishMove, drop, objectiveEvalGapCp, nearlySameEval };
}

// ─── computeFindabilityGate (Phase 159 ride-along, D-10/D-11/D-12) ─────────

/**
 * Margin (raw Maia probability, 0-1 scale) by which the FlawChess pick's
 * probability must exceed the Stockfish pick's probability for the safe-tier
 * "far easier to find and play" claim to render (D-10). Starting value; needs
 * UAT tuning like SHARP_DROP_THRESHOLD/NEARLY_SAME_EVAL_CP — same order of
 * magnitude as INACCURACY_DROP (0.05) in generated/flawThresholds.ts.
 */
export const FINDABILITY_MARGIN = 0.05;

/**
 * Findability-claim gate (D-10). Both `pYouFc`/`pYouSf` MUST be raw Maia
 * probability at the selected ELO (D-12) — the SAME distribution the Maia
 * "Moves by Rating" chart renders beneath this prose — never the search-
 * internal temperature-adjusted prior, which this module cannot even see
 * (RankedLine has no `prior` field; this file imports nothing from
 * `lib/engine/` beyond the RankedLine type, and nothing temperature-related).
 * Returns false (never throws) whenever either probability is unavailable,
 * whenever the FlawChess pick isn't inside the chart's plotted candidate set
 * (`fcInPlottedSet`, from `selectCandidatesByMass`), or whenever the margin
 * isn't exceeded (D-10's AND, not OR).
 */
export function computeFindabilityGate(
  pYouFc: number | null,
  pYouSf: number | null,
  fcInPlottedSet: boolean,
): boolean {
  if (pYouFc == null || pYouSf == null) return false;
  return fcInPlottedSet && pYouFc > pYouSf + FINDABILITY_MARGIN;
}
