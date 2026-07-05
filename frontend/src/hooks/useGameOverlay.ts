/**
 * useGameOverlay — precomputed board overlay + eval bar for the /analysis game mode
 * (Quick 260627, Phase 140 UAT items 4 & 5).
 *
 * Mirrors the LibraryGameCard miniboard: every position in the game has a precomputed
 * engine best move (eval_series[ply].best_move) and eval (eval_series[ply].eval_cp/mate),
 * plus per-ply tactic-depth badges from the flaw markers. While the board sits on the
 * main line we drive:
 *   - a BLUE best-move arrow from the precomputed best move (shown immediately, no
 *     wait for the live engine), with the missed-tactic depth label when present;
 *   - a severity-colored flaw arrow on the played move with the allowed-tactic depth
 *     label — the "tactic overlay" that shows even before any PV sideline is loaded;
 *   - the eval bar from the precomputed eval (synthetic depth so mate displays).
 * The live engine then only contributes the GREY second-best arrow (pvLines[1]).
 *
 * Off the main line (sideline exploration / fork) there is no precomputed data, so the
 * live engine drives: blue = pvLines[0], grey = pvLines[1], eval = live engine.
 *
 * Ply key contract: mainLine[k] is the position after move k+1, which equals the
 * miniboard's perPly[k] and the eval_series / flaw_markers `ply == k`. So we look up
 * every per-ply map with k = mainLine.indexOf(currentNodeId).
 */

import { useMemo } from 'react';

import type { BoardArrow, SquareMarker } from '@/components/board/ChessBoard';
import type { EvalPoint, FlawMarker, FlawSeverity } from '@/types/library';
import type { NodeId } from '@/hooks/useAnalysisBoard';
import type { PvLine } from '@/hooks/uciParser';
import { uciToSquares } from '@/lib/sanToSquares';
import { tacticDepthBadge } from '@/lib/tacticComparisonMeta';
import {
  BEST_MOVE_ARROW,
  SECOND_BEST_ARROW,
  TAC_ALLOWED,
  TAC_ALLOWED_LABEL,
  TAC_MISSED,
  TAC_MISSED_LABEL,
  MOVE_HIGHLIGHT_SQUARE,
  MOVE_HIGHLIGHT_BLUNDER,
  MOVE_HIGHLIGHT_MISTAKE,
  MOVE_HIGHLIGHT_GOOD,
} from '@/lib/theme';

// Severity-coded last-move square overlay (item 5): inaccuracy keeps the legacy
// translucent yellow; blunder/mistake get their red/orange hues at the same alpha.
const MOVE_HIGHLIGHT_SEVERITY: Record<FlawSeverity, string> = {
  blunder: MOVE_HIGHLIGHT_BLUNDER,
  mistake: MOVE_HIGHLIGHT_MISTAKE,
  inaccuracy: MOVE_HIGHLIGHT_SQUARE,
};

/** Synthetic depth so EvalBar's mate gate (depth >= 8) fires for precomputed evals. */
const PRECOMPUTED_EVAL_DEPTH = 99;
/** Arrow stroke width — matches the analysis-board tactic-mode arrows. */
const ARROW_WIDTH = 0.5;

export interface GameOverlay {
  /** Board arrows for game mode, or undefined when none apply. */
  boardArrows: BoardArrow[] | undefined;
  /**
   * Severity glyph markers for the played move (item 4) — replaces the old
   * red/orange/yellow flaw arrow. Empty off the main line or on clean moves.
   */
  squareMarkers: SquareMarker[];
  /**
   * Severity-coded color for the last-move square overlay (item 5), or undefined
   * off the main line (ChessBoard then falls back to its default yellow).
   */
  lastMoveHighlightColor: string | undefined;
  /** Eval bar centipawns (precomputed when on the main line, else live engine). */
  evalCp: number | null;
  /** Eval bar mate score (precomputed when on the main line, else live engine). */
  evalMate: number | null;
  /** Eval bar depth — high synthetic value when precomputed so mate renders. */
  evalDepth: number;
  /** True when the eval bar + blue arrow are driven by precomputed game data. */
  usingPrecomputed: boolean;
}

export interface UseGameOverlayParams {
  /** Active only in game mode; otherwise the hook passes the live engine through. */
  enabled: boolean;
  evalSeries: EvalPoint[] | null | undefined;
  flawMarkers: FlawMarker[] | null | undefined;
  mainLine: NodeId[];
  currentNodeId: NodeId | null;
  isOnMainLine: (nodeId: NodeId) => boolean;
  /** Move into the current node (from/to) — drives the flaw arrow on the main line. */
  lastMove: { from: string; to: string } | null;
  enginePvLines: PvLine[];
  engineEvalCp: number | null;
  engineEvalMate: number | null;
  engineDepth: number;
}

/** Per-ply maps derived once from the game's eval series + flaw markers. */
interface PlyMaps {
  bestMoveByPly: Map<number, string>;
  evalByPly: Map<number, EvalPoint>;
  severityByPly: Map<number, FlawSeverity>;
  depthByPly: Map<number, { missed?: string; allowed?: string }>;
}

function buildPlyMaps(
  evalSeries: EvalPoint[] | null | undefined,
  flawMarkers: FlawMarker[] | null | undefined,
): PlyMaps {
  const bestMoveByPly = new Map<number, string>();
  const evalByPly = new Map<number, EvalPoint>();
  for (const pt of evalSeries ?? []) {
    evalByPly.set(pt.ply, pt);
    if (pt.best_move) bestMoveByPly.set(pt.ply, pt.best_move);
  }

  const severityByPly = new Map<number, FlawSeverity>();
  const depthByPly = new Map<number, { missed?: string; allowed?: string }>();
  for (const fm of flawMarkers ?? []) {
    severityByPly.set(fm.ply, fm.severity);
    // Quick 260705: opponent tactic arrows (crimson allowed / teal missed) are surfaced in
    // the eval-chart tooltip (built separately in EvalChart) but NOT on the board — suppress
    // the opponent's tactic depths here so no tactic arrow paints for them. Mirrors the same
    // is_user gate on the move list (Quick 260628-u7d). Severity glyphs stay both-color.
    if (!fm.is_user) continue;
    // tacticDepthBadge returns null for family-less / hidden motifs, so a bare depth
    // never paints on the board without its paired chip (same guard as the miniboard).
    // anchored=false (Quick 260628-1t5 DECISION 2): on the navigable analysis board the
    // missed and allowed depths are no longer co-anchored on one decision board, so the
    // allowed +1 offset is dropped — allowed reads on the same plain scale as missed.
    const missed = tacticDepthBadge(fm.missed_tactic_motif, fm.missed_tactic_depth, 'missed', false);
    const allowed = tacticDepthBadge(
      fm.allowed_tactic_motif,
      fm.allowed_tactic_depth,
      'allowed',
      false,
    );
    if (missed != null || allowed != null) {
      depthByPly.set(fm.ply, { missed: missed ?? undefined, allowed: allowed ?? undefined });
    }
  }
  return { bestMoveByPly, evalByPly, severityByPly, depthByPly };
}

/**
 * Compute the game-mode board overlay (arrows) and eval-bar inputs from precomputed
 * game data, falling back to the live engine off the main line.
 */
export function useGameOverlay(params: UseGameOverlayParams): GameOverlay {
  const {
    enabled,
    evalSeries,
    flawMarkers,
    mainLine,
    currentNodeId,
    isOnMainLine,
    lastMove,
    enginePvLines,
    engineEvalCp,
    engineEvalMate,
    engineDepth,
  } = params;

  const maps = useMemo(
    () => buildPlyMaps(evalSeries, flawMarkers),
    [evalSeries, flawMarkers],
  );

  return useMemo<GameOverlay>(() => {
    const enginePassthrough: GameOverlay = {
      boardArrows: undefined,
      squareMarkers: [],
      lastMoveHighlightColor: undefined,
      evalCp: engineEvalCp,
      evalMate: engineEvalMate,
      evalDepth: engineDepth,
      usingPrecomputed: false,
    };
    if (!enabled) return enginePassthrough;

    const onMain = currentNodeId === null || isOnMainLine(currentNodeId);
    const k = currentNodeId !== null ? mainLine.indexOf(currentNodeId) : -1;
    const hasPly = onMain && k >= 0;

    const arrows: BoardArrow[] = [];

    // Blue best-move arrow: the engine's best move FROM the *displayed* position, so it
    // matches the live grey 2nd-best arrow (also from the current position). The board
    // shows mainLine[k] = the position after move k, whose stored best_move lives on the
    // NEXT eval-series row (best_move[k+1] = best move from position k+1); best_move[k] is
    // the move that *led into* the shown position, which pointed the arrow one ply behind
    // (UAT thl item 2). Precomputed on the main line (immediate), else live engine.
    const precomputedBest = hasPly ? maps.bestMoveByPly.get(k + 1) ?? null : null;
    // depths is anchored at the played move's decision ply k — drives the played-move
    // corner glyph's allowed-tactic label and the teal should-have-played arrow below.
    const depths = hasPly ? maps.depthByPly.get(k) : undefined;
    // When the displayed position is an allowed-tactic flaw, the following-best arrow IS the
    // opponent's refuting response, so it carries the allowed-tactic crimson AND the allowed
    // depth label — the label belongs on the response's target square, not the played flaw
    // square (Quick 260628-pu2 UAT round 2). Otherwise it stays the neutral best-continuation
    // blue with no label. depths is anchored at the played move's decision ply k.
    const allowedDepthLabel = depths?.allowed;
    const followingBestColor = allowedDepthLabel != null ? TAC_ALLOWED : BEST_MOVE_ARROW;
    let blueSquares = uciToSquares(precomputedBest);
    if (blueSquares) {
      // The engine's best continuation from the displayed post-flaw position. For an allowed
      // tactic this is the opponent's response and carries the allowed depth label; the
      // missed-tactic depth rides the teal should-have-played arrow below (Quick 260628-1t5).
      arrows.push({
        startSquare: blueSquares.from,
        endSquare: blueSquares.to,
        color: followingBestColor,
        width: ARROW_WIDTH,
        label: allowedDepthLabel,
        labelColor: allowedDepthLabel != null ? TAC_ALLOWED_LABEL : undefined,
      });
    } else {
      // No precomputed best (sideline / root): live engine top line drives the blue.
      blueSquares = uciToSquares(enginePvLines[0]?.moves[0] ?? null);
      if (blueSquares) {
        arrows.push({
          startSquare: blueSquares.from,
          endSquare: blueSquares.to,
          color: BEST_MOVE_ARROW,
          width: ARROW_WIDTH,
        });
      }
    }

    // Teal should-have-played arrow at a missed-tactic flaw ply (Quick 260628-1t5
    // DECISION 1). The displayed board mainLine[k] is the position AFTER the flaw move,
    // so this is a counterfactual arrow: the should-have-played move is the engine best
    // move FROM the pre-flaw DECISION position mainLine[k-1]. The eval series stores that
    // at bestMoveByPly.get(k) — because best_move[j] = best move from mainLine[j-1] (the
    // blue following-best above uses get(k+1) = best from the displayed mainLine[k]). This
    // get(k) vs get(k+1) distinction is the recurring off-by-one; the useGameOverlay parity
    // test pins it (teal = decision-position best, distinct from blue following-best, and
    // equal to the move FlawCard's blue arrow shows for the same flaw). Gated on a visible
    // missed tactic via depthByPly (anchored=false depth label, teal TAC_MISSED family).
    const missedDepthLabel = depths?.missed;
    if (hasPly && missedDepthLabel != null) {
      const shouldHaveSquares = uciToSquares(maps.bestMoveByPly.get(k) ?? null);
      if (shouldHaveSquares) {
        arrows.push({
          startSquare: shouldHaveSquares.from,
          endSquare: shouldHaveSquares.to,
          color: TAC_MISSED,
          width: ARROW_WIDTH,
          label: missedDepthLabel,
          labelColor: TAC_MISSED_LABEL,
        });
      }
    }

    // Played-move overlay — main line only. The flaw is now shown as a severity
    // glyph in the target square's corner (item 4) plus a severity-coded last-move
    // square highlight (item 5), replacing the old red/orange/yellow flaw arrow.
    const squareMarkers: SquareMarker[] = [];
    let lastMoveHighlightColor: string | undefined;
    if (hasPly && lastMove) {
      const severity = maps.severityByPly.get(k);
      if (severity) {
        // Severity glyph only — the allowed depth label now rides the crimson opponent-
        // response arrow (its target square), not this played-flaw square (Quick 260628-pu2
        // UAT round 2: the label was on the wrong square, and doubled when the line opened).
        squareMarkers.push({
          square: lastMove.to,
          severity,
        });
        lastMoveHighlightColor = MOVE_HIGHLIGHT_SEVERITY[severity];
      } else {
        // A clean played move on the main line reads green (item 5).
        lastMoveHighlightColor = MOVE_HIGHLIGHT_GOOD;
      }
    }

    // Light-blue second-best arrow from the live engine (pvLines[1]). When precomputed
    // best is shown, the engine's own top line is suppressed — only the 2nd best is added.
    const secondBestSquares = uciToSquares(enginePvLines[1]?.moves[0] ?? null);
    if (
      secondBestSquares &&
      !(
        blueSquares &&
        secondBestSquares.from === blueSquares.from &&
        secondBestSquares.to === blueSquares.to
      )
    ) {
      arrows.push({
        startSquare: secondBestSquares.from,
        endSquare: secondBestSquares.to,
        color: SECOND_BEST_ARROW,
        width: ARROW_WIDTH,
      });
    }

    // Eval bar: precomputed eval on the main line, else the live engine.
    const evalPt = hasPly ? maps.evalByPly.get(k) : undefined;
    const usePrecomputedEval =
      evalPt != null && (evalPt.eval_cp != null || evalPt.eval_mate != null);

    return {
      boardArrows: arrows.length > 0 ? arrows : undefined,
      squareMarkers,
      lastMoveHighlightColor,
      evalCp: usePrecomputedEval ? evalPt.eval_cp : engineEvalCp,
      evalMate: usePrecomputedEval ? evalPt.eval_mate : engineEvalMate,
      evalDepth: usePrecomputedEval ? PRECOMPUTED_EVAL_DEPTH : engineDepth,
      usingPrecomputed: usePrecomputedEval,
    };
  }, [
    enabled,
    maps,
    mainLine,
    currentNodeId,
    isOnMainLine,
    lastMove,
    enginePvLines,
    engineEvalCp,
    engineEvalMate,
    engineDepth,
  ]);
}
