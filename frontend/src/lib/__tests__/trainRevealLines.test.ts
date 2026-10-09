/**
 * trainRevealLines tests (Phase 237 Plan 02): the pure chip/line model behind the
 * Train reveal's single move tree. buildChipGroups lifts the Phase 190.1 / 236
 * buildLineBoxes grouping (its TrainReveal.test.tsx cases are ported here at the
 * data level); the tree helpers are exercised on hand-built node maps.
 */

import { describe, expect, it } from 'vitest';
import { Chess } from 'chess.js';

import type { MoveNode, NodeId } from '@/hooks/useAnalysisBoard';
import type { GradeResult, TrainEngineLine } from '@/hooks/useTrainGradingEngine';
import type { InstantGradeState } from '@/hooks/trainGradingSupport';
import {
  CANONICAL_ROLE_ORDER,
  MAX_LINE_PLIES,
  REVEAL_TREE_SNAPSHOT_MAX_PATHS,
  REVEAL_TREE_SNAPSHOT_MAX_PLIES,
  buildChipGroups,
  buildRevealTreeSnapshot,
  buildTreeListView,
  classifyTreeNodes,
  nodeUci,
  pathToNode,
  resolveForwardTarget,
  revealBestUciOf,
  sanFromUci,
  walkLinePath,
} from '@/lib/trainRevealLines';
import type { BuildChipGroupsInput, GameMoveLineState, RoleKey } from '@/lib/trainRevealLines';

const START_FEN = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1';

function line(moves: string[], evalCp: number | null = 50): TrainEngineLine {
  return { moves, evalCp, evalMate: null };
}

function gradeResult(bestMoves: string[], playedMoves: string[]): GradeResult {
  return {
    moveTier: 'good',
    bestMoveUci: bestMoves[0] ?? null,
    esBefore: 0.5,
    esAfter: 0.5,
    bestLine: line(bestMoves, 50),
    playedLine: line(playedMoves, 10),
  };
}

function input(overrides: Partial<BuildChipGroupsInput> = {}): BuildChipGroupsInput {
  return {
    puzzleFen: START_FEN,
    playedMoveUci: null,
    gradeResult: null,
    instantGrade: null,
    gameMoveUci: null,
    gameMoveLine: { status: 'idle' },
    playedMoveQuality: null,
    gameMoveQuality: null,
    ...overrides,
  };
}

describe('buildChipGroups', () => {
  it('played == best merges into ONE Move = Best chip carrying the best line', () => {
    const best = line(['e2e4', 'e7e5', 'g1f3'], 50);
    const chips = buildChipGroups(
      input({
        playedMoveUci: 'e2e4',
        gradeResult: { ...gradeResult(['e2e4'], ['e2e4']), bestLine: best, playedLine: best },
      }),
    );
    expect(chips).toHaveLength(1);
    expect(chips[0]).toMatchObject({
      key: 'your',
      roles: ['your', 'best'],
      label: 'Move = Best',
      uci: 'e2e4',
      san: 'e4',
      pending: null,
      quality: 'best',
    });
    expect(chips[0]?.line).toBe(best);
    expect(chips[0]?.lineUcis).toEqual(['e2e4', 'e7e5', 'g1f3']);
  });

  it('game == played merges into Move = Game and shows the played line', () => {
    const chips = buildChipGroups(
      input({
        playedMoveUci: 'd2d4',
        gradeResult: gradeResult(['e2e4', 'e7e5'], ['d2d4', 'd7d5']),
        gameMoveUci: 'd2d4',
        playedMoveQuality: 'inaccuracy',
      }),
    );
    expect(chips.map((c) => c.label)).toEqual(['Move = Game', 'Best']);
    const merged = chips[0];
    expect(merged?.key).toBe('your');
    expect(merged?.lineUcis).toEqual(['d2d4', 'd7d5']);
    expect(merged?.quality).toBe('inaccuracy');
  });

  it('game == best merges generically under the best key (D-02 rule, not designed around)', () => {
    const chips = buildChipGroups(
      input({
        playedMoveUci: 'd2d4',
        gradeResult: gradeResult(['e2e4', 'e7e5'], ['d2d4']),
        gameMoveUci: 'e2e4',
      }),
    );
    expect(chips.map((c) => [c.key, c.label])).toEqual([
      ['your', 'Move'],
      ['best', 'Best = Game'],
    ]);
  });

  it('three distinct moves yield three chips in your / best / game order', () => {
    const chips = buildChipGroups(
      input({
        playedMoveUci: 'd2d4',
        gradeResult: gradeResult(['e2e4'], ['d2d4']),
        gameMoveUci: 'g1f3',
        gameMoveLine: { status: 'ready', line: line(['g1f3'], -20) },
        gameMoveQuality: 'blunder',
      }),
    );
    expect(chips.map((c) => c.key)).toEqual(['your', 'best', 'game']);
    expect(chips.map((c) => c.uci)).toEqual(['d2d4', 'e2e4', 'g1f3']);
    expect(chips[2]?.quality).toBe('blunder');
    expect(chips[2]?.pending).toBeNull();
    expect(CANONICAL_ROLE_ORDER).toEqual(['your', 'best', 'game']);
  });

  it('a long engine line is capped at 12 plies and still starts with the chip move', () => {
    const longLine = [
      'e2e4', 'e7e5', 'g1f3', 'b8c6', 'f1c4', 'f8c5',
      'c2c3', 'g8f6', 'd2d3', 'd7d6', 'b1d2', 'c8e6',
      'c4b3', 'd8d7',
    ];
    const chips = buildChipGroups(
      input({
        playedMoveUci: 'e2e4',
        gradeResult: gradeResult(longLine, longLine),
      }),
    );
    const lineUcis = chips[0]?.lineUcis ?? [];
    expect(MAX_LINE_PLIES).toBe(12);
    expect(lineUcis).toHaveLength(12);
    expect(lineUcis[0]).toBe('e2e4');
    expect(lineUcis.at(-1)).toBe('c8e6');
  });

  it('an empty or mismatched line yields just the chip first move', () => {
    const standIn = gradeResult(['e2e4'], []); // the WR-02 stand-in: empty played line
    const chips = buildChipGroups(input({ playedMoveUci: 'd2d4', gradeResult: standIn }));
    expect(chips[0]?.lineUcis).toEqual(['d2d4']);

    const mismatched = buildChipGroups(
      input({ playedMoveUci: 'd2d4', gradeResult: gradeResult(['e2e4'], ['c2c4', 'c7c5']) }),
    );
    expect(mismatched[0]?.lineUcis).toEqual(['d2d4']);
  });

  it('produces no chips before any grade or key exists, and no your/best chip without a played move', () => {
    expect(buildChipGroups(input())).toEqual([]);
    const chips = buildChipGroups(
      input({ gradeResult: gradeResult(['e2e4'], ['e2e4']), playedMoveUci: null }),
    );
    expect(chips.map((c) => c.key)).toEqual(['best']);
  });

  describe('Phase 236 instant path', () => {
    const pendingKey = (keyLine: TrainEngineLine | null, status: InstantGradeState['status']) => ({
      status,
      keyUci: 'e2e4',
      keyLine,
    });

    it('your and best are pending-loading while the background grade runs', () => {
      const chips = buildChipGroups(
        input({ playedMoveUci: 'd2d4', instantGrade: pendingKey(null, 'pending') }),
      );
      expect(chips.map((c) => [c.key, c.pending, c.lineUcis])).toEqual([
        ['your', 'loading', ['d2d4']],
        ['best', 'loading', ['e2e4']],
      ]);
    });

    it('turns pending into failed once the search gave up', () => {
      const chips = buildChipGroups(
        input({ playedMoveUci: 'd2d4', instantGrade: pendingKey(null, 'failed') }),
      );
      expect(chips.map((c) => c.pending)).toEqual(['failed', 'failed']);
    });

    it('the think-time key line makes the best chip ready while your stays loading', () => {
      const keyLine = line(['e2e4', 'e7e5']);
      const chips = buildChipGroups(
        input({ playedMoveUci: 'd2d4', instantGrade: pendingKey(keyLine, 'pending') }),
      );
      const best = chips.find((c) => c.key === 'best');
      const your = chips.find((c) => c.key === 'your');
      expect(best?.pending).toBeNull();
      expect(best?.lineUcis).toEqual(['e2e4', 'e7e5']);
      expect(your?.pending).toBe('loading');
    });

    it('a merged Move = Best chip with the key line is ready, not pending', () => {
      const chips = buildChipGroups(
        input({
          playedMoveUci: 'e2e4',
          instantGrade: pendingKey(line(['e2e4', 'e7e5']), 'pending'),
        }),
      );
      expect(chips).toHaveLength(1);
      expect(chips[0]?.pending).toBeNull();
    });
  });

  describe('standalone game chip', () => {
    const base = {
      playedMoveUci: 'd2d4',
      gradeResult: gradeResult(['e2e4'], ['d2d4']),
      gameMoveUci: 'g1f3',
    };
    const gameChip = (state: GameMoveLineState) =>
      buildChipGroups(input({ ...base, gameMoveLine: state })).find((c) => c.key === 'game');

    it.each<[GameMoveLineState['status'], 'loading' | 'failed' | null]>([
      ['idle', 'loading'],
      ['loading', 'loading'],
      ['error', 'failed'],
    ])('is %s -> pending %s', (status, pending) => {
      const state = { status } as GameMoveLineState;
      expect(gameChip(state)?.pending).toBe(pending);
      expect(gameChip(state)?.line).toBeNull();
      expect(gameChip(state)?.lineUcis).toEqual(['g1f3']);
    });

    it('grows its line once the search is ready', () => {
      const ready = gameChip({ status: 'ready', line: line(['g1f3', 'g8f6', 'b1c3']) });
      expect(ready?.pending).toBeNull();
      expect(ready?.lineUcis).toEqual(['g1f3', 'g8f6', 'b1c3']);
    });
  });
});

describe('sanFromUci / revealBestUciOf', () => {
  it('converts a legal UCI, and returns null for null, short, and illegal input', () => {
    expect(sanFromUci(START_FEN, 'e2e4')).toBe('e4');
    expect(sanFromUci(START_FEN, null)).toBeNull();
    expect(sanFromUci(START_FEN, 'e2')).toBeNull();
    expect(sanFromUci(START_FEN, 'e2e5')).toBeNull();
  });

  it('prefers the graded key line over the instant key', () => {
    const instant: InstantGradeState = { status: 'pending', keyUci: 'd2d4', keyLine: null };
    expect(revealBestUciOf(gradeResult(['e2e4'], ['e2e4']), instant)).toBe('e2e4');
    expect(revealBestUciOf(null, instant)).toBe('d2d4');
    expect(revealBestUciOf(null, null)).toBeNull();
  });

  it('reads bestMoveUci so an empty stand-in bestLine still yields the key (WR-01)', () => {
    // gradeFromServerPair shape: bestMoveUci = instant key, bestLine empty.
    const standIn: GradeResult = { ...gradeResult([], []), bestMoveUci: 'e2e4' };
    expect(standIn.bestLine.moves).toEqual([]);
    expect(revealBestUciOf(standIn, null)).toBe('e2e4');
    const chips = buildChipGroups(input({ playedMoveUci: 'd2d4', gradeResult: standIn }));
    expect(chips.map((c) => c.key)).toEqual(['your', 'best']);
    expect(chips[1]?.uci).toBe('e2e4');
  });
});

// ─── Tree helpers ────────────────────────────────────────────────────────────

/** Builds nodes for `ucis` under `parentId` (starting from `fenOfParent`) into `nodes`. */
function addLine(
  nodes: Map<NodeId, MoveNode>,
  parentId: NodeId | null,
  ucis: string[],
  fenOfParent: string = START_FEN,
): NodeId[] {
  const chess = new Chess(parentId === null ? fenOfParent : nodes.get(parentId)!.fen);
  const ids: NodeId[] = [];
  let cursor = parentId;
  for (const uci of ucis) {
    const move = chess.move({ from: uci.slice(0, 2), to: uci.slice(2, 4), promotion: uci.slice(4, 5) || undefined });
    const id = nodes.size;
    nodes.set(id, { id, san: move.san, fen: chess.fen(), from: move.from, to: move.to, parentId: cursor });
    ids.push(id);
    cursor = id;
  }
  return ids;
}

describe('walkLinePath', () => {
  it('returns node ids along the line and stops at the first missing child', () => {
    const nodes = new Map<NodeId, MoveNode>();
    const ids = addLine(nodes, null, ['e2e4', 'e7e5', 'g1f3']);
    expect(walkLinePath(nodes, ['e2e4', 'e7e5', 'g1f3'])).toEqual(ids);
    expect(walkLinePath(nodes, ['e2e4', 'e7e5', 'g1f3', 'b8c6'])).toEqual(ids);
    expect(walkLinePath(nodes, ['e2e4', 'c7c5', 'g1f3'])).toEqual([ids[0]]);
    expect(walkLinePath(nodes, ['d2d4'])).toEqual([]);
    expect(walkLinePath(nodes, [])).toEqual([]);
  });

  it('can start below a node', () => {
    const nodes = new Map<NodeId, MoveNode>();
    const ids = addLine(nodes, null, ['e2e4', 'e7e5', 'g1f3']);
    expect(walkLinePath(nodes, ['e7e5', 'g1f3'], ids[0])).toEqual([ids[1], ids[2]]);
  });
});

describe('nodeUci / pathToNode', () => {
  it('rebuilds the UCI of a move, including a lowercase promotion letter', () => {
    const nodes = new Map<NodeId, MoveNode>();
    const [e4] = addLine(nodes, null, ['e2e4']);
    expect(nodeUci(nodes.get(e4!)!)).toBe('e2e4');

    const promo = new Map<NodeId, MoveNode>();
    const [queen] = addLine(promo, null, ['e7e8q'], '7k/4P3/8/8/8/8/8/K7 w - - 0 1');
    expect(promo.get(queen!)?.san.startsWith('e8=Q')).toBe(true);
    expect(nodeUci(promo.get(queen!)!)).toBe('e7e8q');
  });

  it('lists ids from the first move down to the node, empty at the root, and stops at a missing parent', () => {
    const nodes = new Map<NodeId, MoveNode>();
    const ids = addLine(nodes, null, ['e2e4', 'e7e5', 'g1f3']);
    expect(pathToNode(nodes, ids[2]!)).toEqual(ids);
    expect(pathToNode(nodes, null)).toEqual([]);

    const orphaned = new Map(nodes);
    orphaned.delete(ids[0]!);
    expect(pathToNode(orphaned, ids[2]!)).toEqual([ids[1], ids[2]]);
  });
});

describe('classifyTreeNodes', () => {
  it('owns line nodes, free nodes by nearest known ancestor, and root forks by null', () => {
    const nodes = new Map<NodeId, MoveNode>();
    const your = addLine(nodes, null, ['e2e4', 'e7e5']);
    const best = addLine(nodes, null, ['d2d4', 'd7d5']);
    const freeOffYour = addLine(nodes, your[0]!, ['c7c5']); // sibling of e5 under e4
    const freeDeep = addLine(nodes, freeOffYour[0]!, ['g1f3']);
    const rootFork = addLine(nodes, null, ['g1f3']);
    const rootForkChild = addLine(nodes, rootFork[0]!, ['g8f6']);
    const linePaths: Partial<Record<RoleKey, NodeId[]>> = { your, best };

    const owners = classifyTreeNodes(nodes, linePaths);

    for (const id of your) expect(owners.get(id)).toBe('your');
    for (const id of best) expect(owners.get(id)).toBe('best');
    expect(owners.get(freeOffYour[0]!)).toBe('your');
    expect(owners.get(freeDeep[0]!)).toBe('your');
    expect(owners.get(rootFork[0]!)).toBeNull();
    expect(owners.get(rootForkChild[0]!)).toBeNull();
    expect(owners.size).toBe(nodes.size);
  });
});

describe('buildTreeListView', () => {
  function fixture() {
    const nodes = new Map<NodeId, MoveNode>();
    const your = addLine(nodes, null, ['e2e4', 'e7e5']);
    const best = addLine(nodes, null, ['d2d4', 'd7d5']);
    const game = addLine(nodes, null, ['c2c4']);
    const freeOffYour = addLine(nodes, your[0]!, ['c7c5']);
    const freeOffBest = addLine(nodes, best[0]!, ['g8f6']);
    const rootFork = addLine(nodes, null, ['g1f3']);
    const rootForkChild = addLine(nodes, rootFork[0]!, ['g8f6']);
    const linePaths: Partial<Record<RoleKey, NodeId[]>> = { your, best, game };
    const owners = classifyTreeNodes(nodes, linePaths);
    return { nodes, linePaths, owners, your, best, game, freeOffYour, freeOffBest, rootFork, rootForkChild };
  }

  it('active chip: its line, the free subtrees hanging off it and the free root forks', () => {
    const f = fixture();

    const view = buildTreeListView(f.nodes, f.linePaths, f.owners, 'best');

    expect(view.mainLine).toEqual(f.best);
    expect(new Set(view.nodes.keys())).toEqual(
      new Set([...f.best, ...f.freeOffBest, ...f.rootFork, ...f.rootForkChild]),
    );
  });

  it('hands back a main line copy, never the live path array', () => {
    const f = fixture();

    const view = buildTreeListView(f.nodes, f.linePaths, f.owners, 'your');

    expect(view.mainLine).not.toBe(f.linePaths.your);
    expect(view.mainLine).toEqual(f.your);
  });

  it('no active chip (D-04): an empty main line and only the root-fork subtrees', () => {
    const f = fixture();

    const view = buildTreeListView(f.nodes, f.linePaths, f.owners, null);

    expect(view.mainLine).toEqual([]);
    expect(new Set(view.nodes.keys())).toEqual(new Set([...f.rootFork, ...f.rootForkChild]));
  });
});

describe('resolveForwardTarget', () => {
  function fixture() {
    const nodes = new Map<NodeId, MoveNode>();
    // BEST is added first so its nodes carry the lowest ids.
    const best = addLine(nodes, null, ['d2d4', 'd7d5']);
    const your = addLine(nodes, null, ['e2e4', 'e7e5', 'g1f3']);
    const freeOffE4 = addLine(nodes, your[0]!, ['c7c5']); // a free sideline off 1.e4
    const linePaths: Partial<Record<RoleKey, NodeId[]>> = { your, best };
    return { nodes, linePaths, your, best, freeOffE4 };
  }
  const NONE: ReadonlyMap<NodeId | null, NodeId> = new Map();

  it('at the puzzle position it enters the active chip, never the lowest-id child', () => {
    const f = fixture();
    const target = resolveForwardTarget({
      nodes: f.nodes, currentNodeId: null, activeChip: 'your', linePaths: f.linePaths,
      lastChildByParent: NONE,
    });
    expect(target).toBe(f.your[0]);
    expect(f.best[0]!).toBeLessThan(f.your[0]!);
  });

  it('at the puzzle position it ignores a remembered child once a chip is active', () => {
    const f = fixture();
    const target = resolveForwardTarget({
      nodes: f.nodes, currentNodeId: null, activeChip: 'your', linePaths: f.linePaths,
      lastChildByParent: new Map([[null, f.best[0]!]]),
    });
    expect(target).toBe(f.your[0]);
  });

  it('with no active chip it prefers the last-visited root child, else the lowest id', () => {
    const f = fixture();
    const base = { nodes: f.nodes, currentNodeId: null, activeChip: null, linePaths: f.linePaths };
    expect(resolveForwardTarget({ ...base, lastChildByParent: NONE })).toBe(f.best[0]);
    expect(
      resolveForwardTarget({ ...base, lastChildByParent: new Map([[null, f.your[0]!]]) }),
    ).toBe(f.your[0]);
  });

  it('below the root it prefers the last-visited child over the known line', () => {
    const f = fixture();
    const target = resolveForwardTarget({
      nodes: f.nodes, currentNodeId: f.your[0]!, activeChip: 'your', linePaths: f.linePaths,
      lastChildByParent: new Map([[f.your[0]!, f.freeOffE4[0]!]]),
    });
    expect(target).toBe(f.freeOffE4[0]);
  });

  it('with no last-visited child it follows the known line, not the lowest id', () => {
    const nodes = new Map<NodeId, MoveNode>();
    const e4 = addLine(nodes, null, ['e2e4']);
    const free = addLine(nodes, e4[0]!, ['c7c5']); // created FIRST: lowest-id child of e4
    const rest = addLine(nodes, e4[0]!, ['e7e5', 'g1f3']);
    expect(free[0]!).toBeLessThan(rest[0]!);

    const target = resolveForwardTarget({
      nodes, currentNodeId: e4[0]!, activeChip: 'your',
      linePaths: { your: [e4[0]!, ...rest] }, lastChildByParent: NONE,
    });

    expect(target).toBe(rest[0]);
  });

  it('ignores a remembered child that is no longer a child of the node', () => {
    const f = fixture();
    const target = resolveForwardTarget({
      nodes: f.nodes, currentNodeId: f.your[0]!, activeChip: 'your', linePaths: f.linePaths,
      lastChildByParent: new Map([[f.your[0]!, 9999]]),
    });
    expect(target).toBe(f.your[1]);
  });

  it('falls back to the lowest-id child on a free node and returns null on a leaf', () => {
    const f = fixture();
    const sideChildren = addLine(f.nodes, f.freeOffE4[0]!, ['g1f3']);
    expect(
      resolveForwardTarget({
        nodes: f.nodes, currentNodeId: f.freeOffE4[0]!, activeChip: 'your',
        linePaths: f.linePaths, lastChildByParent: NONE,
      }),
    ).toBe(sideChildren[0]);
    expect(
      resolveForwardTarget({
        nodes: f.nodes, currentNodeId: sideChildren[0]!, activeChip: 'your',
        linePaths: f.linePaths, lastChildByParent: NONE,
      }),
    ).toBeNull();
  });

  it('at the end of a known line with no sideline there is nowhere to go', () => {
    const f = fixture();
    expect(
      resolveForwardTarget({
        nodes: f.nodes, currentNodeId: f.your[2]!, activeChip: 'your', linePaths: f.linePaths,
        lastChildByParent: NONE,
      }),
    ).toBeNull();
  });
});

describe('buildRevealTreeSnapshot', () => {
  it('known-line nodes alone produce no sideline path', () => {
    const nodes = new Map<NodeId, MoveNode>();
    const your = addLine(nodes, null, ['e2e4', 'e7e5']);
    const best = addLine(nodes, null, ['d2d4']);

    const snapshot = buildRevealTreeSnapshot(nodes, your[1]!, { your, best }, 'your');

    expect(snapshot).toEqual({
      rootFocus: 'your',
      currentPath: ['e2e4', 'e7e5'],
      sidelinePaths: [],
    });
  });

  it('each free leaf contributes its full root -> leaf path, and free ancestors are not repeated', () => {
    const nodes = new Map<NodeId, MoveNode>();
    const your = addLine(nodes, null, ['e2e4', 'e7e5']);
    const sidelineA = addLine(nodes, your[0]!, ['c7c5', 'g1f3']); // free chain off 1.e4
    addLine(nodes, your[0]!, ['e7e6']); // second free leaf off 1.e4
    addLine(nodes, null, ['g1f3']); // a free root fork

    const snapshot = buildRevealTreeSnapshot(nodes, sidelineA[1]!, { your }, null);

    expect(snapshot.rootFocus).toBeNull();
    expect(snapshot.currentPath).toEqual(['e2e4', 'c7c5', 'g1f3']);
    expect(snapshot.sidelinePaths).toEqual([
      ['e2e4', 'c7c5', 'g1f3'],
      ['e2e4', 'e7e6'],
      ['g1f3'],
    ]);
  });

  it('is empty at the puzzle position', () => {
    const nodes = new Map<NodeId, MoveNode>();
    expect(buildRevealTreeSnapshot(nodes, null, {}, 'best')).toEqual({
      rootFocus: 'best',
      currentPath: [],
      sidelinePaths: [],
    });
  });

  it('carries a promotion letter in the UCI path', () => {
    const nodes = new Map<NodeId, MoveNode>();
    const fen = '7k/4P3/8/8/8/8/8/K7 w - - 0 1';
    const [queen] = addLine(nodes, null, ['e7e8q'], fen);

    const snapshot = buildRevealTreeSnapshot(nodes, queen!, {}, null);

    expect(snapshot.currentPath).toEqual(['e7e8q']);
    expect(snapshot.sidelinePaths).toEqual([['e7e8q']]);
  });

  it('caps the number of paths and the length of each path', () => {
    const nodes = new Map<NodeId, MoveNode>();
    for (const first of ['e2e4', 'd2d4']) {
      const [firstId] = addLine(nodes, null, [first]);
      const chess = new Chess(nodes.get(firstId!)!.fen);
      for (const reply of chess.moves({ verbose: true })) {
        addLine(nodes, firstId!, [reply.from + reply.to]);
      }
    }
    const shuffle = ['g1f3', 'g8f6', 'f3g1', 'f6g8'];
    const longChain = addLine(
      nodes,
      null,
      Array.from({ length: 80 }, (_, i) => shuffle[i % shuffle.length]!),
    );

    const snapshot = buildRevealTreeSnapshot(nodes, longChain.at(-1)!, {}, null);

    expect(snapshot.sidelinePaths).toHaveLength(REVEAL_TREE_SNAPSHOT_MAX_PATHS);
    expect(snapshot.currentPath).toHaveLength(REVEAL_TREE_SNAPSHOT_MAX_PLIES);
    for (const path of snapshot.sidelinePaths) {
      expect(path.length).toBeLessThanOrEqual(REVEAL_TREE_SNAPSHOT_MAX_PLIES);
    }
  });
});
