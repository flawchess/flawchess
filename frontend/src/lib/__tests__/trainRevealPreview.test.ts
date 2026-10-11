/**
 * trainRevealPreview tests (SEED-197): the pure preview model. Trees are built
 * with a child-reusing graft helper so the anchor / inheritance walks run on the
 * same node-map shape the real analysis board produces.
 */

import { describe, expect, it } from 'vitest';
import { Chess } from 'chess.js';

import type { MoveNode, NodeId } from '@/hooks/useAnalysisBoard';
import type { PvLine } from '@/hooks/uciParser';
import type { TrainEngineLine } from '@/hooks/trainGradingSupport';
import {
  TRAIN_PREVIEW_MAX_PLIES,
  TRAIN_PREVIEW_MIN_PLIES,
  buildPreviewSeeds,
  chipPreviewSeed,
  liveCandidate,
  resolvePreview,
  resolvePreviewAnchor,
} from '@/lib/trainRevealPreview';
import type { PreviewLine } from '@/lib/trainRevealPreview';
import { TRAIN_LIVE_ALT_MIN_DEPTH } from '@/lib/trainArrows';

const START_FEN = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1';
/** 1.f3 e5 2.g4 Qh4#: White is checkmated. */
const FOOLS_MATE = ['f2f3', 'e7e5', 'g2g4', 'd8h4'];
/** Black to move, no legal move, not in check. */
const STALEMATE_FEN = '7k/5Q2/6K1/8/8/8/8/8 b - - 0 1';

/** The Italian-ish line used by most tests (12 plies, all legal). */
const LONG_LINE = [
  'e2e4', 'e7e5', 'g1f3', 'b8c6', 'f1c4', 'f8c5', 'c2c3', 'g8f6', 'd2d3', 'd7d6', 'b1d2', 'c8e6',
];

function line(ucis: string[], evalCp: number | null = 50): PreviewLine {
  return { ucis, evalCp, evalMate: null };
}

function engineLine(moves: string[], evalCp: number | null = 50): TrainEngineLine {
  return { moves, evalCp, evalMate: null };
}

function pv(moves: string[], depth: number): PvLine {
  return { multipv: 1, depth, moves, evalCp: 30, evalMate: null };
}

/** Child-reusing graft: plays `ucis` under `parentId`, reusing a matching child. */
function graft(
  nodes: Map<NodeId, MoveNode>,
  parentId: NodeId | null,
  ucis: string[],
  rootFen: string = START_FEN,
): NodeId[] {
  const ids: NodeId[] = [];
  let cursor = parentId;
  for (const uci of ucis) {
    const from = uci.slice(0, 2);
    const to = uci.slice(2, 4);
    const existing = [...nodes.values()].find(
      (n) => n.parentId === cursor && n.from === from && n.to === to,
    );
    if (existing) {
      ids.push(existing.id);
      cursor = existing.id;
      continue;
    }
    const chess = new Chess(cursor === null ? rootFen : nodes.get(cursor)!.fen);
    const move = chess.move({ from, to, promotion: uci.slice(4, 5) || undefined });
    const id = nodes.size;
    nodes.set(id, { id, san: move.san, fen: chess.fen(), from: move.from, to: move.to, parentId: cursor });
    ids.push(id);
    cursor = id;
  }
  return ids;
}

const EMPTY: ReadonlyMap<NodeId, PreviewLine> = new Map();

describe('chipPreviewSeed', () => {
  it('seeds the line minus the chip first move, with the line eval', () => {
    const seed = chipPreviewSeed({ uci: 'e2e4', line: engineLine(['e2e4', 'e7e5', 'g1f3'], 77) });
    expect(seed).toEqual({ ucis: ['e7e5', 'g1f3'], evalCp: 77, evalMate: null });
  });

  it('is null for a line starting with another move, a null line and a one-move line', () => {
    expect(chipPreviewSeed({ uci: 'e2e4', line: engineLine(['d2d4', 'd7d5']) })).toBeNull();
    expect(chipPreviewSeed({ uci: 'e2e4', line: null })).toBeNull();
    expect(chipPreviewSeed({ uci: 'e2e4', line: engineLine(['e2e4']) })).toBeNull();
  });
});

describe('buildPreviewSeeds', () => {
  it('keys each seed by the chip first-move node and skips chips without node or seed', () => {
    const chips = [
      { key: 'your' as const, uci: 'e2e4', line: engineLine(['e2e4', 'e7e5']) },
      { key: 'best' as const, uci: 'd2d4', line: engineLine(['d2d4']) }, // no tail
      { key: 'game' as const, uci: 'g1f3', line: engineLine(['g1f3', 'g8f6']) }, // no node yet
    ];
    const seeds = buildPreviewSeeds(chips, { your: [7], best: [8] });
    expect([...seeds.keys()]).toEqual([7]);
    expect(seeds.get(7)?.ucis).toEqual(['e7e5']);
  });
});

describe('liveCandidate', () => {
  it('needs depth TRAIN_LIVE_ALT_MIN_DEPTH and at least one move', () => {
    expect(TRAIN_LIVE_ALT_MIN_DEPTH).toBe(10);
    expect(liveCandidate([pv(['e7e5'], 9)])).toBeNull();
    expect(liveCandidate([pv(['e7e5', 'g1f3'], 10)])?.ucis).toEqual(['e7e5', 'g1f3']);
    expect(liveCandidate([pv([], 12)])).toBeNull();
    expect(liveCandidate([])).toBeNull();
  });
});

describe('resolvePreviewAnchor', () => {
  it('a current leaf is its own anchor', () => {
    const nodes = new Map<NodeId, MoveNode>();
    const [e4, e5] = graft(nodes, null, ['e2e4', 'e7e5']);
    expect(resolvePreviewAnchor({ nodes, currentNodeId: e5!, activeChipFirstId: e4! })).toBe(e5);
  });

  it('at the root the anchor is the active chip first move while it is a leaf', () => {
    const nodes = new Map<NodeId, MoveNode>();
    const [e4] = graft(nodes, null, ['e2e4']);
    expect(resolvePreviewAnchor({ nodes, currentNodeId: null, activeChipFirstId: e4! })).toBe(e4);
    expect(resolvePreviewAnchor({ nodes, currentNodeId: null, activeChipFirstId: null })).toBeNull();
  });

  it('is null for a node with children, at the root too', () => {
    const nodes = new Map<NodeId, MoveNode>();
    const [e4] = graft(nodes, null, ['e2e4', 'e7e5']);
    expect(resolvePreviewAnchor({ nodes, currentNodeId: e4!, activeChipFirstId: e4! })).toBeNull();
    expect(resolvePreviewAnchor({ nodes, currentNodeId: null, activeChipFirstId: e4! })).toBeNull();
  });

  it('is null at checkmate and at stalemate', () => {
    const mate = new Map<NodeId, MoveNode>();
    const ids = graft(mate, null, FOOLS_MATE);
    expect(resolvePreviewAnchor({ nodes: mate, currentNodeId: ids.at(-1)!, activeChipFirstId: null })).toBeNull();

    const stale = new Map<NodeId, MoveNode>();
    stale.set(0, { id: 0, san: 'Qf7', fen: STALEMATE_FEN, from: 'f6', to: 'f7', parentId: null });
    expect(resolvePreviewAnchor({ nodes: stale, currentNodeId: 0, activeChipFirstId: null })).toBeNull();
  });
});

describe('resolvePreview precedence', () => {
  function fixture() {
    const nodes = new Map<NodeId, MoveNode>();
    const [e4] = graft(nodes, null, ['e2e4']);
    return { nodes, e4: e4! };
  }

  it('live beats stored, stored beats seed, seed beats inherited', () => {
    const { nodes, e4 } = fixture();
    const live = line(['e7e5', 'g1f3']);
    const stored = new Map([[e4, line(['c7c5'])]]);
    const seeds = new Map([[e4, line(['e7e6'])]]);

    expect(resolvePreview({ nodes, anchorId: e4, live, stored, seeds })?.source).toBe('live');
    expect(resolvePreview({ nodes, anchorId: e4, live: null, stored, seeds })).toMatchObject({
      source: 'stored',
      steps: [{ uci: 'c7c5', san: 'c5' }],
    });
    expect(resolvePreview({ nodes, anchorId: e4, live: null, stored: EMPTY, seeds })).toMatchObject({
      source: 'seed',
      steps: [{ uci: 'e7e6', san: 'e6' }],
    });
  });

  it('a live line illegal from the anchor falls through to the next candidate', () => {
    const { nodes, e4 } = fixture();
    const live = line(['e2e4']); // White's move again: illegal with Black to move
    const seeds = new Map([[e4, line(['e7e5'])]]);
    const resolved = resolvePreview({ nodes, anchorId: e4, live, stored: EMPTY, seeds });
    expect(resolved?.source).toBe('seed');
  });

  it('is null when no candidate exists', () => {
    const { nodes, e4 } = fixture();
    expect(resolvePreview({ nodes, anchorId: e4, live: null, stored: EMPTY, seeds: EMPTY })).toBeNull();
  });
});

describe('resolvePreview minimum length (SEED-197 UAT)', () => {
  /** Tail of LONG_LINE after 1.e4: 11 plies, so the fallback clips to the max. */
  const TAIL = LONG_LINE.slice(1);

  function fixture() {
    const nodes = new Map<NodeId, MoveNode>();
    const [e4] = graft(nodes, null, ['e2e4']);
    return { nodes, e4: e4! };
  }

  it('a short live line yields to a longer fallback with the same first move', () => {
    const { nodes, e4 } = fixture();
    const live = line(['e7e5', 'g1f3']); // a hash-truncated PV
    expect(live.ucis.length).toBeLessThan(TRAIN_PREVIEW_MIN_PLIES);
    for (const [stored, seeds, source] of [
      [new Map([[e4, line(TAIL)]]), EMPTY, 'stored'],
      [EMPTY, new Map([[e4, line(TAIL)]]), 'seed'],
    ] as const) {
      const resolved = resolvePreview({ nodes, anchorId: e4, live, stored, seeds });
      expect(resolved?.source).toBe(source);
      expect(resolved?.steps).toHaveLength(TRAIN_PREVIEW_MAX_PLIES);
    }
  });

  it('a short live line yields to a longer inherited tail', () => {
    const nodes = new Map<NodeId, MoveNode>();
    const [e4, e5] = graft(nodes, null, ['e2e4', 'e7e5']);
    const seeds = new Map([[e4!, line(TAIL)]]);
    const live = line(['g1f3']);
    const resolved = resolvePreview({ nodes, anchorId: e5!, live, stored: EMPTY, seeds });
    expect(resolved?.source).toBe('inherited');
    expect(resolved?.steps[0]?.uci).toBe('g1f3');
    expect(resolved?.steps).toHaveLength(TRAIN_PREVIEW_MAX_PLIES);
  });

  it('a short live line that disagrees on the first move wins over a longer fallback', () => {
    const { nodes, e4 } = fixture();
    const live = line(['c7c5', 'g1f3']);
    const seeds = new Map([[e4, line(TAIL)]]);
    const resolved = resolvePreview({ nodes, anchorId: e4, live, stored: EMPTY, seeds });
    expect(resolved?.source).toBe('live');
    expect(resolved?.steps.map((step) => step.uci)).toEqual(['c7c5', 'g1f3']);
  });

  it('a live line of at least TRAIN_PREVIEW_MIN_PLIES wins over a longer agreeing fallback', () => {
    const { nodes, e4 } = fixture();
    const live = line(['e7e5', 'g1f3', 'b8c6', 'f1b5', 'a7a6']);
    expect(live.ucis).toHaveLength(TRAIN_PREVIEW_MIN_PLIES);
    const seeds = new Map([[e4, line(TAIL)]]);
    expect(resolvePreview({ nodes, anchorId: e4, live, stored: EMPTY, seeds })?.source).toBe('live');
  });

  it('a short live line wins when the agreeing fallback is not longer', () => {
    const { nodes, e4 } = fixture();
    const live = line(['e7e5', 'g1f3', 'b8c6']);
    const seeds = new Map([[e4, line(['e7e5', 'g1f3'])]]);
    expect(resolvePreview({ nodes, anchorId: e4, live, stored: EMPTY, seeds })?.source).toBe('live');
  });
});

describe('resolvePreview inheritance', () => {
  const SEED_TAIL = ['e7e5', 'g1f3', 'b8c6', 'f1c4', 'f8c5', 'c2c3'];

  function fixture() {
    const nodes = new Map<NodeId, MoveNode>();
    const ids = graft(nodes, null, LONG_LINE.slice(0, 5));
    const seeds = new Map([[ids[0]!, line(SEED_TAIL)]]);
    return { nodes, ids, seeds };
  }

  it('shows the remaining tail one ply below the chip node, and further down', () => {
    const { nodes, ids, seeds } = fixture();
    const one = resolvePreview({ nodes, anchorId: ids[1]!, live: null, stored: EMPTY, seeds });
    expect(one?.source).toBe('inherited');
    expect(one?.steps.map((s) => s.uci)).toEqual(['g1f3', 'b8c6', 'f1c4', 'f8c5', 'c2c3']);

    const three = resolvePreview({ nodes, anchorId: ids[3]!, live: null, stored: EMPTY, seeds });
    expect(three?.steps.map((s) => s.uci)).toEqual(['f1c4', 'f8c5', 'c2c3']);
  });

  it('is null when the committed path diverges from every ancestor line', () => {
    const { nodes, ids, seeds } = fixture();
    const [c5] = graft(nodes, ids[0]!, ['c7c5']);
    expect(resolvePreview({ nodes, anchorId: c5!, live: null, stored: EMPTY, seeds })).toBeNull();
  });

  it('the nearest matching ancestor wins and a mismatching nearer one is skipped', () => {
    const { nodes, ids, seeds } = fixture();
    // ids[1] = e5. A stored entry at ids[1] that diverges (d7d5 instead of g1f3)
    // is skipped when resolving ids[2]; the chip seed still matches.
    const stored = new Map([[ids[1]!, line(['b8c6', 'f1c4'])]]);
    const skipped = resolvePreview({ nodes, anchorId: ids[2]!, live: null, stored, seeds });
    expect(skipped?.steps.map((s) => s.uci)).toEqual(['b8c6', 'f1c4', 'f8c5', 'c2c3']);

    // A nearer ancestor that matches wins over the chip seed.
    const nearer = new Map([[ids[1]!, line(['g1f3', 'g8f6'])]]);
    const won = resolvePreview({ nodes, anchorId: ids[2]!, live: null, stored: nearer, seeds });
    expect(won?.steps.map((s) => s.uci)).toEqual(['g8f6']);
    expect(won?.source).toBe('inherited');
  });

  it('compares the path by from-to squares only', () => {
    const { nodes, ids } = fixture();
    // Seed written with an (irrelevant) promotion-style suffix on the first move.
    const seeds = new Map([[ids[0]!, line(['e7e5x', 'g1f3'])]]);
    const resolved = resolvePreview({ nodes, anchorId: ids[1]!, live: null, stored: EMPTY, seeds });
    expect(resolved?.steps.map((s) => s.uci)).toEqual(['g1f3']);
  });
});

describe('resolvePreview display', () => {
  it('truncates at the first illegal move and clips to TRAIN_PREVIEW_MAX_PLIES', () => {
    const nodes = new Map<NodeId, MoveNode>();
    const [e4] = graft(nodes, null, ['e2e4']);
    const illegalMid = line(['e7e5', 'g1f3', 'a1a8', 'b8c6']);
    const truncated = resolvePreview({
      nodes, anchorId: e4!, live: illegalMid, stored: EMPTY, seeds: EMPTY,
    });
    expect(truncated?.steps.map((s) => s.uci)).toEqual(['e7e5', 'g1f3']);

    const long = resolvePreview({
      nodes, anchorId: e4!, live: line(LONG_LINE.slice(1)), stored: EMPTY, seeds: EMPTY,
    });
    expect(TRAIN_PREVIEW_MAX_PLIES).toBe(6);
    expect(long?.steps).toHaveLength(TRAIN_PREVIEW_MAX_PLIES);
    expect(long?.steps[0]).toEqual({ uci: 'e7e5', san: 'e5' });
  });

  it('keeps the full tail on the resolved line while clipping the steps', () => {
    const nodes = new Map<NodeId, MoveNode>();
    const [e4] = graft(nodes, null, ['e2e4']);
    const resolved = resolvePreview({
      nodes, anchorId: e4!, live: line(LONG_LINE.slice(1)), stored: EMPTY, seeds: EMPTY,
    });
    expect(resolved?.line.ucis).toHaveLength(LONG_LINE.length - 1);
  });
});
