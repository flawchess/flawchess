/**
 * treeCommon.ts unit tests (Phase 159 Pitfall 2/T-159-07; Phase 182 D-10).
 *
 * Covers the `sideMatchesMover` truth table: the four combinations of the
 * `Side` ('w'|'b') and `MoverColor` ('white'|'black') literal-type domains.
 * Dedicated test so the Phase 159 temperature call sites (`mctsSearch.ts`,
 * `fallbackExpectimax.ts`) can rely on ONE verified comparison instead of
 * two independently hand-rolled inline checks.
 *
 * Also covers `buildSnapshot` → `buildRankedLines`'s `childScoreSpread`
 * field (Phase 182 D-10, STYLE-04): the multi-grandchild spread case, the
 * 0-child and 1-child null-boundary cases, and a regression check that the
 * pre-existing `RankedLine` fields (`rootMove`, `practicalScore`, `visits`)
 * are computed unchanged alongside the new additive field.
 */

import { describe, it, expect } from 'vitest';
import { sideMatchesMover, buildSnapshot, type SearchTreeNode } from '../treeCommon';
import type { Side } from '../types';

describe('sideMatchesMover', () => {
  it("'w' matches 'white'", () => {
    expect(sideMatchesMover('w', 'white')).toBe(true);
  });

  it("'b' matches 'black'", () => {
    expect(sideMatchesMover('b', 'black')).toBe(true);
  });

  it("'b' does NOT match 'white'", () => {
    expect(sideMatchesMover('b', 'white')).toBe(false);
  });

  it("'w' does NOT match 'black'", () => {
    expect(sideMatchesMover('w', 'black')).toBe(false);
  });
});

// ─── buildRankedLines childScoreSpread fixtures (Phase 182 D-10) ──────────

/** Minimal self-referential node type satisfying `SearchTreeNode<N>`. */
type TestNode = SearchTreeNode<TestNode>;

/** Builds a minimal `TestNode`, defaulting every field so callers only set what a test cares about. */
function makeNode(overrides: Partial<TestNode> = {}): TestNode {
  return {
    fen: overrides.fen ?? 'fen',
    side: overrides.side ?? ('w' as Side),
    depth: overrides.depth ?? 0,
    isRoot: overrides.isRoot ?? false,
    uci: overrides.uci ?? null,
    prior: overrides.prior ?? 1,
    value: overrides.value ?? 0.5,
    visits: overrides.visits ?? 0,
    isTerminal: overrides.isTerminal ?? false,
    isExpanded: overrides.isExpanded ?? true,
    objectiveEvalCp: overrides.objectiveEvalCp ?? null,
    objectiveEvalMate: overrides.objectiveEvalMate ?? null,
    rawMaiaProb: overrides.rawMaiaProb ?? null,
    children: overrides.children ?? new Map<string, TestNode>(),
  };
}

/** Builds a root child (a `RankedLine` candidate) with the given grandchild `.value`s as its own children. */
function makeRootChild(uci: string, grandchildValues: number[]): TestNode {
  const children = new Map<string, TestNode>();
  grandchildValues.forEach((value, i) => {
    children.set(`gc${i}`, makeNode({ uci: `gc${i}`, value }));
  });
  return makeNode({ uci, prior: 1 / grandchildValues.length || 1, value: 0.6, visits: 3, children });
}

function makeRoot(rootChildren: TestNode[]): TestNode {
  const children = new Map<string, TestNode>();
  for (const child of rootChildren) {
    if (child.uci !== null) children.set(child.uci, child);
  }
  return makeNode({ isRoot: true, side: 'w', children });
}

describe('buildRankedLines childScoreSpread (Phase 182 D-10)', () => {
  it('reports the exact max−min spread of a root child’s own grandchild values', () => {
    const child = makeRootChild('e2e4', [0.7, 0.3, 0.5]);
    const root = makeRoot([child]);

    const snapshot = buildSnapshot(root, 10, true, 1500);
    const line = snapshot.rankedLines.find((l) => l.rootMove === 'e2e4');

    expect(line?.childScoreSpread).toBeCloseTo(0.4, 10);
  });

  it('reports null for a root child with zero own children', () => {
    const child = makeRootChild('d2d4', []);
    const root = makeRoot([child]);

    const snapshot = buildSnapshot(root, 5, true, 1500);
    const line = snapshot.rankedLines.find((l) => l.rootMove === 'd2d4');

    expect(line?.childScoreSpread).toBeNull();
  });

  it('reports null for a root child with exactly one own child (boundary — never 0-as-a-signal)', () => {
    const child = makeRootChild('g1f3', [0.42]);
    const root = makeRoot([child]);

    const snapshot = buildSnapshot(root, 5, true, 1500);
    const line = snapshot.rankedLines.find((l) => l.rootMove === 'g1f3');

    expect(line?.childScoreSpread).toBeNull();
  });

  it('regression: pre-existing RankedLine fields stay correct alongside the new field', () => {
    const child = makeRootChild('b1c3', [0.2, 0.9]);
    const root = makeRoot([child]);

    const snapshot = buildSnapshot(root, 7, true, 1500);
    const line = snapshot.rankedLines.find((l) => l.rootMove === 'b1c3');

    expect(line).toBeDefined();
    expect(line?.rootMove).toBe('b1c3');
    expect(line?.practicalScore).toBeCloseTo(0.6, 10);
    expect(line?.visits).toBe(3);
    expect(line?.childScoreSpread).toBeCloseTo(0.7, 10);
  });
});
