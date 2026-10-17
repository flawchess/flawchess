/**
 * useAnalysisBoardArrows — the board-overlay derivation cluster of `Analysis()`.
 *
 * Owns every `BoardArrow[]`/`SquareMarker[]` value the `<ChessBoard>` render
 * consumes: the PV-sideline tactic overlay, the move-quality hover preview,
 * the translucent next-move arrow, the two live-engine arrow layers (each drawing
 * its own settings-driven count of arrows), and the
 * square-marker/last-move-tint derivation (severity > gem/great > best/good >
 * book precedence). WHY a separate hook: this is a pure transform of
 * already-computed board/engine/gem state (no state/effects of its own beyond
 * `useMemo`), the same shape as `useLiveMoveFlaw.ts`.
 *
 * Ownership boundary: this hook calls no engine hook of its own — the
 * FlawChess ranked lines and the reconciled Stockfish ranking
 * (`stockfishArrowLines`, the same list that feeds the Stockfish card) are
 * already-resolved results threaded in as options, exactly like
 * `useAnalysisEngineLines.ts`'s `engine`/`flawChessEngine`/`grading` fields.
 * `resolveMarkerFor` (from `useAnalysisGemMarkers`) and `storedBestGoodByPly`
 * (held in `Analysis.tsx`) arrive as options too.
 *
 * `forkPlyForOrientation` is imported from `lib/analysisTactics.ts` (a lib
 * module, not a page module, so "hooks must not depend on page-level modules"
 * does not apply) rather than copied here, so the fork-ply rule cannot drift.
 *
 * The Stockfish arrows (never the FlawChess ones)
 * are graded by `lib/engineArrowGrades` in ONE pass (`stockfishGrades`) once the
 * lines are deep enough: ranks 1+ take a proportional alpha, and every drawn
 * arrow's target square gets a move-quality badge (rank 0 the best star at the primary arrow alpha).
 * The badges merge UNDER the existing square markers (they never displace one)
 * and follow the arrows actually drawn: none while the move-quality hover or the
 * PV-sideline overlay replaces the engine arrows.
 */

import { useMemo } from 'react';
import { Chess } from 'chess.js';
import type { BoardArrow, SquareMarker } from '@/components/board/ChessBoard';
import type { NodeId, MoveNode } from '@/hooks/useAnalysisBoard';
import type { RankedLine } from '@/lib/engine/types';
import type { PvLine } from '@/hooks/uciParser';
import type { HoveredQualityMove } from '@/components/analysis/MaiaMoveQualityBar';
import type { TacticLinesResponse } from '@/types/library';
import { toDisplayDepthForOrientation } from '@/lib/tacticDepth';
import { buildPvArrow } from '@/lib/tacticArrows';
import { uciToSquares } from '@/lib/sanToSquares';
import {
  buildRankedEngineBadges,
  gradeEngineLines,
  mergeEngineBadges,
  stockfishSecondaryArrowColor,
  flawChessSecondaryAlphas,
  flawChessSecondaryArrowColor,
  type EngineLineGrade,
} from '@/lib/engineArrowGrades';
import { forkPlyForOrientation, type TacticRef } from '@/lib/analysisTactics';
import {
  TAC_MISSED,
  TAC_ALLOWED,
  FLAWCHESS_ENGINE_ARROW,
  BEST_MOVE_ARROW,
  NEXT_MOVE_ARROW,
  MOVE_HIGHLIGHT_GEM,
  MOVE_HIGHLIGHT_GREAT,
} from '@/lib/theme';

// Arrow-width tuning constants (0-1 normalized, 0 = thinnest, 1 = thickest).
// This hook is their sole reader after this extraction, so they move with the
// cluster rather than staying behind as an orphaned import.
const QUALITY_HOVER_ARROW_WIDTH = 0.6;
const NEXT_MOVE_ARROW_WIDTH = 0.18;
// Each live-engine overlay keeps its engine's width for EVERY rank: rank 2..N
// differ from rank 1 only by the engine's translucent color. How many arrows an
// engine draws is the settings-driven `fcArrowCount` / `sfArrowCount` option.
const FLAWCHESS_ENGINE_ARROW_WIDTH = 1.0;
const STOCKFISH_ENGINE_ARROW_WIDTH = 0.5;

interface EngineArrowStyle {
  /** Solid color of the rank-1 (primary) arrow. */
  primaryColor: string;
  width: number;
  /** layerKey prefix: `${prefix}-${rank index}`. */
  prefix: 'fc' | 'sf';
}

const FLAWCHESS_ARROW_STYLE: EngineArrowStyle = {
  primaryColor: FLAWCHESS_ENGINE_ARROW,
  width: FLAWCHESS_ENGINE_ARROW_WIDTH,
  prefix: 'fc',
};

const STOCKFISH_ARROW_STYLE: EngineArrowStyle = {
  primaryColor: BEST_MOVE_ARROW,
  width: STOCKFISH_ENGINE_ARROW_WIDTH,
  prefix: 'sf',
};

/**
 * Pushes up to `count` arrows for one engine into `out`, rank k reading
 * `rootMoves[k]` (each rank names its own move, so ranks 2..N are distinct
 * and match the card order). Iterates from the lowest rank down to 0 so the
 * primary is pushed LAST and paints on top within its width tier
 * (ChessBoard's width sort keeps input order for equal keys).
 * A count of 0 draws nothing for the engine (its card is unaffected).
 * `secondaryColors` (aligned with `rootMoves`) colors ranks 1+: each engine's graded
 * translucent color.
 */
function pushEngineArrows(
  out: BoardArrow[],
  rootMoves: ReadonlyArray<string | null>,
  count: number,
  style: EngineArrowStyle,
  secondaryColors: ReadonlyArray<string>,
): void {
  for (let i = Math.min(count, rootMoves.length) - 1; i >= 0; i--) {
    const squares = uciToSquares(rootMoves[i] ?? null);
    if (!squares) continue;
    out.push({
      startSquare: squares.from,
      endSquare: squares.to,
      color: i === 0 ? style.primaryColor : (secondaryColors[i] ?? style.primaryColor),
      width: style.width,
      layerKey: `${style.prefix}-${i}`,
    });
  }
}

/**
 * Named seam (CLAUDE.md: extract one named predicate/helper, not five
 * one-line helpers) that keeps `boardSquareMarkers` under the enforced
 * complexity-15 limit. Sticky gem/great marker append — see that memo's own
 * comment for the precedence rule this implements:
 * yields to any existing severity marker already on the square.
 */
function appendGemGreatMarker(
  base: SquareMarker[],
  markerHere: { tier: 'gem' | 'great' } | null,
  lastMove: { from: string; to: string } | null,
): SquareMarker[] {
  if (markerHere === null || lastMove == null) return base; // non-null resolution = confirmed gem/great
  if (base.some((m) => m.square === lastMove.to && m.severity != null)) return base;
  return [
    ...base,
    markerHere.tier === 'great' ? { square: lastMove.to, great: true } : { square: lastMove.to, gem: true },
  ];
}

/**
 * Best/good marker append — the same defensive precedence
 * `appendGemGreatMarker` uses (yields to any existing severity/gem/great
 * marker on the square), appended only for the current MAINLINE ply.
 */
function appendBestGoodMarker(
  withMarker: SquareMarker[],
  bestGoodTier: 'best' | 'good' | undefined,
  lastMove: { from: string; to: string } | null,
): SquareMarker[] {
  if (bestGoodTier == null || lastMove == null) return withMarker;
  if (
    withMarker.some(
      (m) => m.square === lastMove.to && (m.severity != null || m.gem === true || m.great === true),
    )
  ) {
    return withMarker;
  }
  return [
    ...withMarker,
    bestGoodTier === 'best' ? { square: lastMove.to, best: true } : { square: lastMove.to, good: true },
  ];
}

/**
 * Book marker append — LOWEST precedence in
 * severity > gem/great > best/good > book. Appended only when the current
 * node is a MAINLINE ply inside the book AND the square carries none of
 * severity/gem/great/best/good.
 */
function appendBookMarker(
  withBestGood: SquareMarker[],
  isBookPly: boolean,
  lastMove: { from: string; to: string } | null,
): SquareMarker[] {
  if (!isBookPly || lastMove == null) return withBestGood;
  if (
    withBestGood.some(
      (m) =>
        m.square === lastMove.to &&
        (m.severity != null ||
          m.gem === true ||
          m.great === true ||
          m.best === true ||
          m.good === true),
    )
  ) {
    return withBestGood;
  }
  return [...withBestGood, { square: lastMove.to, book: true }];
}

/**
 * Engine badges for the arrows actually drawn: only while the Stockfish
 * arrows are the visible overlay (not replaced by the move-quality hover or the
 * PV-sideline overlay) and the engine card is on. Existing markers win.
 */
function engineBadgeSquareMarkers(
  base: SquareMarker[],
  engineArrowsVisible: boolean,
  lines: readonly PvLine[],
  count: number,
  grades: ReadonlyArray<EngineLineGrade | null>,
): SquareMarker[] {
  if (!engineArrowsVisible) return base;
  return mergeEngineBadges(base, buildRankedEngineBadges(lines, count, grades));
}

export interface UseAnalysisBoardArrowsOptions {
  // ── Board state (useAnalysisBoard) ────────────────────────────────────
  position: string;
  currentNodeId: NodeId | null;
  nodes: Map<NodeId, MoveNode>;
  mainLine: NodeId[];
  isOnMainLine: (nodeId: NodeId) => boolean;
  lastMove: { from: string; to: string } | null;

  // ── Game mode ──────────────────────────────────────────────────────────
  isGameMode: boolean;
  gameOpeningPlyCount: number | null | undefined;
  currentMainlinePly: number;

  // ── Focused in-tree tactic sideline (the open/pending PV chip) ────────
  focusedFlaw: TacticRef | null;
  contextualTacticData: TacticLinesResponse | null | undefined;
  contextualOnStoredLine: boolean;
  contextualCurrentPly: number;
  focusedPvLine: readonly NodeId[];

  // ── Move-quality bar hover preview ────────────────────────────────────
  hoveredQualityMoves: HoveredQualityMove[] | null;

  // ── Live engine overlays — already-resolved results, no engine hook of
  // its own (see file header). ──────────────────────────────────────────
  flawChessEnabled: boolean;
  flawChessRankedLines: RankedLine[];
  engineEnabled: boolean;
  /**
   * The reconciled Stockfish ranking that feeds the Stockfish card:
   * arrow k reads line k's first move, so arrows and card rows always
   * name the same moves. Before grading lands it is the free run's own lines
   * (the fallback inside the ranking, not a separate source here).
   */
  stockfishArrowLines: PvLine[];
  /** FlawChess arrows to draw, 0-3 (settings). 0 hides the arrows, not the card. */
  fcArrowCount: number;
  /** Stockfish arrows to draw, 0-3 (settings). 0 hides the arrows, not the card. */
  sfArrowCount: number;

  // ── Precomputed/live overlay markers (useGameOverlay / useLiveMoveFlaw
  // results, unrelated hooks that stay in Analysis.tsx) ──────────────────
  gameOverlaySquareMarkers: SquareMarker[];
  liveFlawSquareMarkers: SquareMarker[];

  // ── Stored gem/great/best/good data (resolveMarkerFor comes from
  // useAnalysisGemMarkers; storedBestGoodByPly from Analysis.tsx) ───────
  resolveMarkerFor: (
    nodeId: NodeId,
    mainlinePly: number,
  ) => { tier: 'gem' | 'great' } | null;
  storedBestGoodByPly: Map<number, 'best' | 'good'>;
}

export interface UseAnalysisBoardArrowsResult {
  /** Move-list/sideline text coloring inside a focused PV. */
  sidelineNodeColors: Map<NodeId, string>;
  /** The board's full arrow overlay, precedence-resolved (hover > PV sideline > engines, +next-move). */
  boardArrows: BoardArrow[] | undefined;
  /** The board's square-marker overlay (severity > gem/great > best/good > book). */
  boardSquareMarkers: SquareMarker[];
  /** Last-move square tint for a gem/great tier marker, or undefined to fall through. */
  lastMoveTierColor: string | undefined;
}

/**
 * Derives the board's arrow and square-marker overlays. See the file header
 * for scope and ownership notes.
 */
export function useAnalysisBoardArrows(
  options: UseAnalysisBoardArrowsOptions,
): UseAnalysisBoardArrowsResult {
  const {
    position,
    currentNodeId,
    nodes,
    mainLine,
    isOnMainLine,
    lastMove,
    isGameMode,
    gameOpeningPlyCount,
    currentMainlinePly,
    focusedFlaw,
    contextualTacticData,
    contextualOnStoredLine,
    contextualCurrentPly,
    focusedPvLine,
    hoveredQualityMoves,
    flawChessEnabled,
    flawChessRankedLines,
    engineEnabled,
    stockfishArrowLines,
    fcArrowCount,
    sfArrowCount,
    gameOverlaySquareMarkers,
    liveFlawSquareMarkers,
    resolveMarkerFor,
    storedBestGoodByPly,
  } = options;

  // Move-list coloring inside the PV sideline:
  // teal (TAC_MISSED) for a missed tactic, crimson (TAC_ALLOWED) for an allowed one. Every
  // sideline move from the fork up to and including the depth-0 resolving move is colored,
  // so the whole tactic line reads in its orientation color (not just the punchline move).
  // The *_tactic_ply_index indexes the PV moves, which line up 1:1 with focusedPvLine.
  const sidelineNodeColors = useMemo(() => {
    const colors = new Map<NodeId, string>();
    if (!isGameMode || focusedFlaw == null || contextualTacticData == null) return colors;
    const isMissed = focusedFlaw.orientation === 'missed';
    // allowed_tactic_ply_index indexes the API allowed_moves (flaw move at index 0); the
    // grafted focusedPvLine drops that lead-in, so shift -1 to align.
    const resolveIdx = isMissed
      ? (contextualTacticData.missed_tactic_ply_index ?? 0)
      : (contextualTacticData.allowed_tactic_ply_index ?? 1) - 1;
    const color = isMissed ? TAC_MISSED : TAC_ALLOWED;
    for (let i = 0; i <= resolveIdx; i++) {
      const node = focusedPvLine[i];
      if (node !== undefined) colors.set(node, color);
    }
    return colors;
  }, [isGameMode, focusedFlaw, contextualTacticData, focusedPvLine]);

  // Board "tactic overlay" while navigating a PV sideline: the depth-countdown
  // arrow on the next stored PV move. Anchored to
  // the FOCUSED line's depth/orientation (the line the board is currently in).
  const pvSidelineArrows = useMemo<BoardArrow[] | null>(() => {
    if (!isGameMode || focusedFlaw == null || contextualTacticData == null) return null;
    const orientation = focusedFlaw.orientation;
    const forkNodeId = mainLine[forkPlyForOrientation(focusedFlaw.ply, orientation)];
    const onPvPath = contextualOnStoredLine || (forkNodeId !== undefined && currentNodeId === forkNodeId);
    if (!onPvPath) return null;

    const depthRaw =
      orientation === 'missed'
        ? (contextualTacticData.missed_depth ?? 0)
        : (contextualTacticData.allowed_depth ?? 0);
    // anchored=false: the analysis board is a navigable
    // surface, so the allowed +1 decision-anchor offset is dropped (allowed reads like missed).
    const rootDisplayDepth = toDisplayDepthForOrientation(depthRaw, orientation, false);

    // Steps into the focused PV from the current node (0 at the fork position).
    const stepIntoPv = contextualCurrentPly;
    const nextPvNodeId = focusedPvLine[stepIntoPv];
    const nextPvNode = nextPvNodeId !== undefined ? nodes.get(nextPvNodeId) : undefined;
    const nextMove = nextPvNode ? { from: nextPvNode.from, to: nextPvNode.to } : null;
    if (!nextMove) return null;

    const displayDepth = Math.max(0, rootDisplayDepth - stepIntoPv);
    // Depth 0 is the move after the tactic resolves: treat it as payoff so it shows no
    // number and drops the orientation color — the tactic is over by then.
    // The countdown therefore runs ...2, 1 (punchline), then payoff.
    const isPayoff = stepIntoPv >= rootDisplayDepth;
    // Only the single PV-continuation arrow here — no engine rank
    // arrows join the tactic overlay (the per-engine count settings
    // apply to the free-analysis engine layer below).
    const arrows = buildPvArrow(nextMove, displayDepth, isPayoff, orientation);
    return arrows.length > 0 ? arrows : null;
  }, [
    isGameMode,
    focusedFlaw,
    contextualTacticData,
    contextualOnStoredLine,
    contextualCurrentPly,
    currentNodeId,
    mainLine,
    focusedPvLine,
    nodes,
  ]);

  // Arrows for the move-quality bar's hovered segment — one per
  // move, tinted its severity color. Each SAN is replayed at the CURRENT position
  // to resolve from/to squares (skipped if illegal/malformed; never throws). Works
  // in both game mode and free play, so it's derived independently of isGameMode.
  const qualityHoverArrows = useMemo<BoardArrow[] | null>(() => {
    if (hoveredQualityMoves === null || hoveredQualityMoves.length === 0) return null;
    const arrows: BoardArrow[] = [];
    for (const { san, color } of hoveredQualityMoves) {
      try {
        const chess = new Chess(position);
        const move = chess.move(san);
        arrows.push({
          startSquare: move.from,
          endSquare: move.to,
          color,
          width: QUALITY_HOVER_ARROW_WIDTH,
        });
      } catch {
        // Illegal SAN for this position (stale hover across a board move) — skip it.
      }
    }
    return arrows.length > 0 ? arrows : null;
  }, [hoveredQualityMoves, position]);

  // Translucent white "next move played" arrow, shown whenever the board sits on
  // the main line (root or a main-line node). It points to the move that follows
  // in the game's main line — mainLine[0] at the root, else the node after the
  // current one. Rendered on top of the engine overlay (onTop) and a bit thinner.
  const nextMoveArrow = useMemo<BoardArrow | null>(() => {
    const onMain = currentNodeId === null || isOnMainLine(currentNodeId);
    if (!onMain) return null;
    const idx = currentNodeId === null ? -1 : mainLine.indexOf(currentNodeId);
    const nextNodeId = mainLine[idx + 1];
    if (nextNodeId === undefined) return null; // at the end of the main line
    const nextNode = nodes.get(nextNodeId);
    if (!nextNode) return null;
    return {
      startSquare: nextNode.from,
      endSquare: nextNode.to,
      color: NEXT_MOVE_ARROW,
      width: NEXT_MOVE_ARROW_WIDTH,
      onTop: true,
    };
  }, [currentNodeId, isOnMainLine, mainLine, nodes]);

  // The board's live engine
  // arrows — amber FlawChess Engine (practical moves) and blue Stockfish
  // (objective moves), each drawing its own settings-driven count (0-3).
  // Independently toggled via the engine card switches; each simply
  // doesn't render until its engine's first snapshot yields a root move (no
  // placeholder arrow, mirrors the card skeleton timing). This layer is
  // the default board overlay in BOTH game mode and free analysis — the engine
  // arrows must be identical regardless of whether a game is loaded.
  //
  // Stockfish rank k reads `stockfishArrowLines[k]`: the reconciled ranking that
  // feeds the Stockfish card. sf-0 is still the
  // reconciled argmax because that ranking's head IS the argmax; the free run's
  // own lines only appear as the pre-grading fallback inside that ranking. Ranks
  // 2..N are distinct moves in card order.
  // This is the ONLY grade pass; arrow colors and badges both read it.
  const stockfishGrades = useMemo(
    () => gradeEngineLines(stockfishArrowLines, position),
    [stockfishArrowLines, position],
  );
  const engineArrows = useMemo<BoardArrow[]>(() => {
    const arrows: BoardArrow[] = [];
    if (flawChessEnabled) {
      pushEngineArrows(
        arrows,
        flawChessRankedLines.map((line) => line.rootMove),
        fcArrowCount,
        FLAWCHESS_ARROW_STYLE,
        flawChessSecondaryAlphas(flawChessRankedLines).map(flawChessSecondaryArrowColor),
      );
    }
    if (engineEnabled) {
      pushEngineArrows(
        arrows,
        stockfishArrowLines.map((line) => line.moves[0] ?? null),
        sfArrowCount,
        STOCKFISH_ARROW_STYLE,
        stockfishGrades.map((grade) => stockfishSecondaryArrowColor(grade)),
      );
    }
    return arrows;
  }, [
    flawChessEnabled,
    flawChessRankedLines,
    fcArrowCount,
    engineEnabled,
    stockfishArrowLines,
    sfArrowCount,
    stockfishGrades,
  ]);

  // Board arrows (game/free parity): the FC + SF engine-arrow layer is
  // the default overlay in BOTH modes, so the board looks identical whether or not
  // a game is loaded. The move-quality hover overlay still wins (both modes) so
  // hovering the bar previews its moves; the game-only flaw-line drill-down overlay
  // (pvSidelineArrows, self-gated to null outside game mode) still takes precedence
  // when you navigate into a specific flaw's PV. The per-engine count settings
  // decide how many arrows each engine draws. Draw order is ChessBoard's width
  // sort with input order as the tie-break (primary pushed last); the white
  // next-move arrow layers on top (onTop).
  const baseArrows: BoardArrow[] | undefined =
    qualityHoverArrows ??
    pvSidelineArrows ??
    (engineArrows.length > 0 ? engineArrows : undefined);
  // Arrow isolation: while a move is being previewed via hover (or
  // first-tap on mobile), show ONLY that move's arrow(s). The translucent white
  // next-move arrow would otherwise survive the preview and clutter the board,
  // so it is suppressed too whenever a hover is active.
  const isHoverIsolated = qualityHoverArrows !== null;
  const boardArrows: BoardArrow[] | undefined =
    nextMoveArrow && !isHoverIsolated ? [...(baseArrows ?? []), nextMoveArrow] : baseArrows;

  // Precomputed game overlay (main line) wins; else the live free-move classification
  // (item 4), which also covers free-play mode. Then the sticky gem/great resolution,
  // then stored best/good, then book — one named helper per precedence tier (CLAUDE.md
  // seam: named helper for the marker-color decision, not five one-line helpers) keeps
  // this memo under the enforced complexity limit.
  const baseSquareMarkers = useMemo(() => {
    const base =
      gameOverlaySquareMarkers.length > 0 ? gameOverlaySquareMarkers : liveFlawSquareMarkers;
    // The STORED backend tier wins whenever this mainline ply of
    // an analyzed game has one — present or authoritatively null.
    // Only then does live resolution apply: gemByNode wins whenever it has
    // graded this node — INCLUDING an explicit `null` rejection, in which
    // case sweep.gemByPly is NOT consulted. `resolveMarkerFor` centralizes
    // ALL of this precedence (a `??` collapse silently fell through a live
    // `null` to the sweep's shallower grade). `null` here = absent or
    // graded-and-rejected.
    const markerHere =
      currentNodeId !== null ? resolveMarkerFor(currentNodeId, currentMainlinePly) : null;
    const withMarker = appendGemGreatMarker(base, markerHere, lastMove);

    // Best/good — the same defensive precedence the gem/
    // great block above uses (yields to any existing severity/gem/great
    // marker on the square), appended only for the current MAINLINE ply.
    const bestGoodTier =
      currentMainlinePly >= 0 ? storedBestGoodByPly.get(currentMainlinePly) : undefined;
    const withBestGood = appendBestGoodMarker(withMarker, bestGoodTier, lastMove);

    // Book marker — LOWEST precedence in
    // severity > gem/great > best/good > book. Appended only when the current
    // node is a MAINLINE ply inside the book AND the square carries none of
    // severity/gem/great/best/good.
    const isBookPly =
      currentMainlinePly >= 0 &&
      gameOpeningPlyCount != null &&
      currentMainlinePly < gameOpeningPlyCount;
    return appendBookMarker(withBestGood, isBookPly, lastMove);
  }, [
    gameOverlaySquareMarkers,
    liveFlawSquareMarkers,
    resolveMarkerFor,
    currentNodeId,
    currentMainlinePly,
    lastMove,
    gameOpeningPlyCount,
    storedBestGoodByPly,
  ]);

  // Engine badges merged under the base markers.
  const engineArrowsVisible =
    engineEnabled && qualityHoverArrows === null && pvSidelineArrows === null;
  const boardSquareMarkers = useMemo(
    () =>
      engineBadgeSquareMarkers(
        baseSquareMarkers,
        engineArrowsVisible,
        stockfishArrowLines,
        sfArrowCount,
        stockfishGrades,
      ),
    [baseSquareMarkers, engineArrowsVisible, stockfishArrowLines, sfArrowCount, stockfishGrades],
  );

  // Gem/great last-move square highlight: color the scrubbed move's from/to squares in
  // the tier's badge hue (violet gem / blue great "best move") instead of the generic
  // green. Derived from the already-resolved baseSquareMarkers, so it inherits their
  // severity > gem/great precedence — a tier marker sits on the square only when no
  // severity marker does, so this can never override a flaw's red/orange/yellow tint.
  const lastMoveTierColor = useMemo(() => {
    if (lastMove == null) return undefined;
    const marker = baseSquareMarkers.find((m) => m.square === lastMove.to && (m.gem || m.great));
    if (marker?.gem) return MOVE_HIGHLIGHT_GEM;
    if (marker?.great) return MOVE_HIGHLIGHT_GREAT;
    return undefined;
  }, [baseSquareMarkers, lastMove]);

  return { sidelineNodeColors, boardArrows, boardSquareMarkers, lastMoveTierColor };
}
