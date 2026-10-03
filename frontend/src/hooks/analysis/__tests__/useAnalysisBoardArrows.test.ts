// @vitest-environment jsdom
/**
 * useAnalysisBoardArrows — Phase 228 (D-14, D-15): each engine draws its chosen
 * number of arrows, read rank-by-rank from the SAME ranking that feeds its
 * card; rank 1 is the solid primary, ranks 2..N share one translucent per-engine
 * color, widths stay per engine, and the primary is pushed last so it paints on
 * top within its width tier.
 */
import { describe, it, expect } from 'vitest';
import { renderHook } from '@testing-library/react';

import {
  useAnalysisBoardArrows,
  type UseAnalysisBoardArrowsOptions,
} from '@/hooks/analysis/useAnalysisBoardArrows';
import type { BoardArrow } from '@/components/board/ChessBoard';
import type { PvLine } from '@/hooks/uciParser';
import type { RankedLine } from '@/lib/engine/types';
import type { MoveNode, NodeId } from '@/hooks/useAnalysisBoard';
import {
  BEST_MOVE_ARROW,
  FLAWCHESS_ENGINE_ARROW,
  FLAWCHESS_SECONDARY_LINE,
  STOCKFISH_SECONDARY_LINE,
} from '@/lib/theme';
import { DEFAULT_ARROWS } from '@/lib/engineSettings';

const START_FEN = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1';

function pvLine(multipv: number, firstMove: string): PvLine {
  return { multipv, depth: 12, moves: [firstMove, 'e7e5'], evalCp: 20, evalMate: null };
}

/** Plain-data RankedLine (no lazy accessors needed for arrow derivation). */
function rankedLine(rootMove: string, practicalScore: number): RankedLine {
  return {
    rootMove,
    practicalScore,
    objectiveEvalCp: 0,
    objectiveEvalMate: null,
    modalPath: [rootMove],
    modalStats: [],
    visits: 10,
    childScoreSpread: null,
  };
}

const SF_LINES: PvLine[] = [
  pvLine(1, 'e2e4'),
  pvLine(2, 'd2d4'),
  pvLine(3, 'g1f3'),
  pvLine(4, 'c2c4'),
];
const FC_LINES: RankedLine[] = [
  rankedLine('b1c3', 0.6),
  rankedLine('g2g3', 0.55),
  rankedLine('b2b3', 0.5),
];

function baseOptions(
  overrides: Partial<UseAnalysisBoardArrowsOptions> = {},
): UseAnalysisBoardArrowsOptions {
  return {
    position: START_FEN,
    currentNodeId: null,
    nodes: new Map<NodeId, MoveNode>(),
    mainLine: [],
    isOnMainLine: () => true,
    lastMove: null,
    isGameMode: false,
    gameOpeningPlyCount: null,
    currentMainlinePly: -1,
    focusedFlaw: null,
    contextualTacticData: null,
    contextualOnStoredLine: false,
    contextualCurrentPly: 0,
    focusedPvLine: [],
    hoveredQualityMoves: null,
    flawChessEnabled: true,
    flawChessRankedLines: FC_LINES,
    engineEnabled: true,
    stockfishArrowLines: SF_LINES,
    fcArrowCount: DEFAULT_ARROWS,
    sfArrowCount: DEFAULT_ARROWS,
    gameOverlaySquareMarkers: [],
    liveFlawSquareMarkers: [],
    resolveMarkerFor: () => null,
    storedBestGoodByPly: new Map<number, 'best' | 'good'>(),
    ...overrides,
  };
}

function arrowsFor(prefix: 'fc' | 'sf', overrides: Partial<UseAnalysisBoardArrowsOptions>): BoardArrow[] {
  const { result } = renderHook(() => useAnalysisBoardArrows(baseOptions(overrides)));
  return (result.current.boardArrows ?? []).filter((a) => a.layerKey?.startsWith(`${prefix}-`));
}

function byKey(arrows: BoardArrow[], key: string): BoardArrow | undefined {
  return arrows.find((a) => a.layerKey === key);
}

describe('useAnalysisBoardArrows — Stockfish arrows 1..N from the reconciled ranking (D-14)', () => {
  it('sfArrowCount 3 draws three DISTINCT moves, rank k reading line k', () => {
    const sf = arrowsFor('sf', { sfArrowCount: 3 });
    expect(sf).toHaveLength(3);
    const sf0 = byKey(sf, 'sf-0');
    const sf1 = byKey(sf, 'sf-1');
    const sf2 = byKey(sf, 'sf-2');
    expect([sf0?.startSquare, sf0?.endSquare]).toEqual(['e2', 'e4']);
    expect([sf1?.startSquare, sf1?.endSquare]).toEqual(['d2', 'd4']);
    expect([sf2?.startSquare, sf2?.endSquare]).toEqual(['g1', 'f3']);
    const moves = new Set(sf.map((a) => `${a.startSquare}${a.endSquare}`));
    expect(moves.size).toBe(3);
  });

  it('rank 1 is the solid BEST_MOVE_ARROW, ranks 2..N the translucent secondary, one shared width', () => {
    const sf = arrowsFor('sf', { sfArrowCount: 3 });
    expect(byKey(sf, 'sf-0')?.color).toBe(BEST_MOVE_ARROW);
    expect(byKey(sf, 'sf-1')?.color).toBe(STOCKFISH_SECONDARY_LINE);
    expect(byKey(sf, 'sf-2')?.color).toBe(STOCKFISH_SECONDARY_LINE);
    const widths = new Set(sf.map((a) => a.width));
    expect(widths.size).toBe(1);
  });

  it('the primary is pushed LAST so it paints on top within its width tier', () => {
    const { result } = renderHook(() =>
      useAnalysisBoardArrows(baseOptions({ sfArrowCount: 3, fcArrowCount: 2 })),
    );
    const keys = (result.current.boardArrows ?? []).map((a) => a.layerKey);
    expect(keys.indexOf('sf-0')).toBeGreaterThan(keys.indexOf('sf-1'));
    expect(keys.indexOf('sf-0')).toBeGreaterThan(keys.indexOf('sf-2'));
    expect(keys.indexOf('fc-0')).toBeGreaterThan(keys.indexOf('fc-1'));
  });

  it('a count above the available lines yields only the available arrows', () => {
    const sf = arrowsFor('sf', { sfArrowCount: 3, stockfishArrowLines: [pvLine(1, 'e2e4')] });
    expect(sf.map((a) => a.layerKey)).toEqual(['sf-0']);
  });

  it('sfArrowCount 0 yields no sf arrows while the fc arrows remain', () => {
    const { result } = renderHook(() => useAnalysisBoardArrows(baseOptions({ sfArrowCount: 0 })));
    const keys = (result.current.boardArrows ?? []).map((a) => a.layerKey);
    expect(keys.some((k) => k?.startsWith('sf-'))).toBe(false);
    expect(keys).toContain('fc-0');
  });

  it('engineEnabled false yields no sf arrows', () => {
    expect(arrowsFor('sf', { engineEnabled: false, sfArrowCount: 3 })).toHaveLength(0);
  });
});

describe('useAnalysisBoardArrows — FlawChess arrows (D-15)', () => {
  it('fcArrowCount 2 draws solid gold then translucent gold, equal width, wider than Stockfish', () => {
    const { result } = renderHook(() =>
      useAnalysisBoardArrows(baseOptions({ fcArrowCount: 2, sfArrowCount: 1 })),
    );
    const all = result.current.boardArrows ?? [];
    const fc0 = byKey(all, 'fc-0');
    const fc1 = byKey(all, 'fc-1');
    const sf0 = byKey(all, 'sf-0');
    expect(fc0?.color).toBe(FLAWCHESS_ENGINE_ARROW);
    expect(fc1?.color).toBe(FLAWCHESS_SECONDARY_LINE);
    expect(fc0?.width).toBe(fc1?.width);
    expect(fc0?.width).toBeGreaterThan(sf0?.width ?? Infinity);
    expect([fc1?.startSquare, fc1?.endSquare]).toEqual(['g2', 'g3']);
  });

  it('fcArrowCount 0 yields no fc arrows while the sf arrows remain', () => {
    const { result } = renderHook(() => useAnalysisBoardArrows(baseOptions({ fcArrowCount: 0 })));
    const keys = (result.current.boardArrows ?? []).map((a) => a.layerKey);
    expect(keys.some((k) => k?.startsWith('fc-'))).toBe(false);
    expect(keys).toContain('sf-0');
  });

  it('flawChessEnabled false yields no fc arrows', () => {
    expect(arrowsFor('fc', { flawChessEnabled: false, fcArrowCount: 3 })).toHaveLength(0);
  });
});
