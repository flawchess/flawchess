// @vitest-environment jsdom
/**
 * Phase 137 Plan 03: VariationTree render tests.
 * Phase 140 Plan 02: Two-level nesting, inline flaw chips, blunder/mistake markers.
 *
 * Fixture A: 3-node main line (1.e4 1...e5 2.Nf3) + one variation (1...d5
 * branching from node 1). Tests cover both dual-DOM paths (mobile + desktop),
 * main-line rendering, variation rendering (BOARD-05), active node
 * aria-current, click → onNodeClick, and the empty state.
 *
 * Fixture B: Extended tree with pvLine (nodes 10, 11) and a level-2 sub-fork
 * (node 20, parent=11). Tests cover variation-pv-section, variation-subpv-section,
 * inline flaw chips, and blunder/mistake severity markers.
 */

import { afterEach, beforeAll, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';

import { VariationTree } from '../VariationTree';
import type { FlawMarkerEntry } from '../VariationTree';
import type { NodeId, MoveNode } from '@/hooks/useAnalysisBoard';

beforeAll(() => {
  // jsdom does not implement scrollIntoView — stub it so the desktop auto-scroll
  // effect does not throw.
  Element.prototype.scrollIntoView = vi.fn();

  Object.defineProperty(window, 'matchMedia', {
    writable: true,
    value: vi.fn().mockImplementation((query: string) => ({
      matches: false,
      media: query,
      onchange: null,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      addListener: vi.fn(),
      removeListener: vi.fn(),
      dispatchEvent: vi.fn(),
    })),
  });

  class ResizeObserverStub {
    observe() {}
    unobserve() {}
    disconnect() {}
  }
  (globalThis as unknown as { ResizeObserver: typeof ResizeObserverStub }).ResizeObserver =
    ResizeObserverStub;
});

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

// ─── Fixture ──────────────────────────────────────────────────────────────────

/**
 * Main line: ids [1, 2, 3]
 *   1. e4 (id=1, parentId=null)
 *   1... e5 (id=2, parentId=1)
 *   2. Nf3 (id=3, parentId=2)
 *
 * Variation: id=4 (1... d5), branching from id=1 (the fork parent).
 * currentNodeId=4 → buildVariationChain yields chain=[4], forkParentId=1.
 */
function buildFixture(): {
  nodes: Map<NodeId, MoveNode>;
  mainLine: NodeId[];
} {
  const nodes = new Map<NodeId, MoveNode>([
    [
      1,
      {
        id: 1,
        san: 'e4',
        fen: 'rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1',
        from: 'e2',
        to: 'e4',
        parentId: null,
      },
    ],
    [
      2,
      {
        id: 2,
        san: 'e5',
        fen: 'rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq e6 0 2',
        from: 'e7',
        to: 'e5',
        parentId: 1,
      },
    ],
    [
      3,
      {
        id: 3,
        san: 'Nf3',
        fen: 'rnbqkbnr/pppp1ppp/8/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R b KQkq - 1 2',
        from: 'g1',
        to: 'f3',
        parentId: 2,
      },
    ],
    [
      4,
      {
        id: 4,
        san: 'd5',
        fen: 'rnbqkbnr/ppp1pppp/8/3p4/4P3/8/PPPP1PPP/RNBQKBNR w KQkq d6 0 2',
        from: 'd7',
        to: 'd5',
        parentId: 1, // branches from id=1 (after 1. e4)
      },
    ],
  ]);
  const mainLine: NodeId[] = [1, 2, 3];
  return { nodes, mainLine };
}

// ─── Fixture B — two-level nesting + flaw markers ────────────────────────────

/**
 * Main line: ids [1, 2, 3]
 *   1. e4 (id=1) 1...e5 (id=2) 2. Nf3 (id=3)
 *
 * pvLine: ids [10, 11] — grafted from id=1 (after 1.e4, the decision position).
 *   10: Nf3 (parentId=1), 11: d5 (parentId=10)
 *
 * Level-2 sub-fork: id=20 — user plays c4 from pvLine node 11.
 *   20: c4 (parentId=11)
 *
 * currentNodeId=10 → level 1 (on pvLine)
 * currentNodeId=20 → level 2 (sub-fork from pvLine node 11)
 */
function buildPvFixture(): {
  nodes: Map<NodeId, MoveNode>;
  mainLine: NodeId[];
  pvLine: NodeId[];
} {
  const nodes = new Map<NodeId, MoveNode>([
    [
      1,
      {
        id: 1,
        san: 'e4',
        fen: 'rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1',
        from: 'e2',
        to: 'e4',
        parentId: null,
      },
    ],
    [
      2,
      {
        id: 2,
        san: 'e5',
        fen: 'rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq e6 0 2',
        from: 'e7',
        to: 'e5',
        parentId: 1,
      },
    ],
    [
      3,
      {
        id: 3,
        san: 'Nf3',
        fen: 'rnbqkbnr/pppp1ppp/8/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R b KQkq - 1 2',
        from: 'g1',
        to: 'f3',
        parentId: 2,
      },
    ],
    // PV sideline grafted from node 1 (after 1.e4).
    [
      10,
      {
        id: 10,
        san: 'Nf3',
        fen: 'rnbqkbnr/pppppppp/8/8/4P3/5N2/PPPP1PPP/RNBQKB1R b KQkq - 1 1',
        from: 'g1',
        to: 'f3',
        parentId: 1,
      },
    ],
    [
      11,
      {
        id: 11,
        san: 'd5',
        fen: 'rnbqkbnr/ppp1pppp/8/3p4/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq d6 0 2',
        from: 'd7',
        to: 'd5',
        parentId: 10,
      },
    ],
    // Level-2 sub-fork from pvLine node 11.
    [
      20,
      {
        id: 20,
        san: 'c4',
        fen: 'rnbqkbnr/ppp1pppp/8/3p4/2P1P3/5N2/PP1P1PPP/RNBQKB1R b KQkq c3 0 2',
        from: 'c2',
        to: 'c4',
        parentId: 11,
      },
    ],
  ]);
  const mainLine: NodeId[] = [1, 2, 3];
  const pvLine: NodeId[] = [10, 11];
  return { nodes, mainLine, pvLine };
}

// ─── Tests ────────────────────────────────────────────────────────────────────

describe('VariationTree', () => {
  it('(1) renders both mobile and desktop DOM paths regardless of viewport', () => {
    const { nodes, mainLine } = buildFixture();
    render(
      <VariationTree
        nodes={nodes}
        mainLine={mainLine}
        currentNodeId={3}
        onNodeClick={vi.fn()}
      />,
    );
    // Both subtrees are always present in the DOM; CSS hides one at runtime.
    expect(screen.getByTestId('variation-tree-mobile')).toBeTruthy();
    expect(screen.getByTestId('variation-tree-desktop')).toBeTruthy();
  });

  it('(2) main-line move buttons render with correct data-testids and SAN text', () => {
    const { nodes, mainLine } = buildFixture();
    render(
      <VariationTree
        nodes={nodes}
        mainLine={mainLine}
        currentNodeId={null}
        onNodeClick={vi.fn()}
      />,
    );
    // Dual-DOM: each node id appears in both mobile and desktop paths.
    const e4Buttons = screen.getAllByTestId('variation-node-1');
    expect(e4Buttons.length).toBeGreaterThan(0);
    expect(e4Buttons[0]!.textContent).toContain('e4');

    const e5Buttons = screen.getAllByTestId('variation-node-2');
    expect(e5Buttons.length).toBeGreaterThan(0);

    const nf3Buttons = screen.getAllByTestId('variation-node-3');
    expect(nf3Buttons.length).toBeGreaterThan(0);
  });

  it('(3) variation node renders when currentNodeId is on a variation (BOARD-05)', () => {
    const { nodes, mainLine } = buildFixture();
    render(
      <VariationTree
        nodes={nodes}
        mainLine={mainLine}
        currentNodeId={4}
        onNodeClick={vi.fn()}
      />,
    );
    // Node 4 (d5) is the variation node — must appear in at least one DOM path.
    const d5Buttons = screen.getAllByTestId('variation-node-4');
    expect(d5Buttons.length).toBeGreaterThan(0);
    expect(d5Buttons[0]!.textContent).toContain('d5');
  });

  it('(4) active node carries aria-current="step"', () => {
    const { nodes, mainLine } = buildFixture();
    render(
      <VariationTree
        nodes={nodes}
        mainLine={mainLine}
        currentNodeId={2}
        onNodeClick={vi.fn()}
      />,
    );
    const node2Buttons = screen.getAllByTestId('variation-node-2');
    // At least one DOM-path button must have aria-current="step".
    const hasAriaCurrent = node2Buttons.some(
      (btn) => btn.getAttribute('aria-current') === 'step',
    );
    expect(hasAriaCurrent).toBe(true);
  });

  it('(4b) non-active nodes do not carry aria-current', () => {
    const { nodes, mainLine } = buildFixture();
    render(
      <VariationTree
        nodes={nodes}
        mainLine={mainLine}
        currentNodeId={2}
        onNodeClick={vi.fn()}
      />,
    );
    const node1Buttons = screen.getAllByTestId('variation-node-1');
    // None of the node-1 buttons should have aria-current=step.
    const noneHasAriaCurrent = node1Buttons.every(
      (btn) => btn.getAttribute('aria-current') !== 'step',
    );
    expect(noneHasAriaCurrent).toBe(true);
  });

  it('(5) clicking a move button calls onNodeClick with the nodeId', () => {
    const { nodes, mainLine } = buildFixture();
    const onNodeClick = vi.fn();
    render(
      <VariationTree
        nodes={nodes}
        mainLine={mainLine}
        currentNodeId={null}
        onNodeClick={onNodeClick}
      />,
    );
    // Click the first occurrence of node 3 (Nf3 — mobile DOM path button).
    const nf3Buttons = screen.getAllByTestId('variation-node-3');
    expect(nf3Buttons.length).toBeGreaterThan(0);
    fireEvent.click(nf3Buttons[0]!);
    expect(onNodeClick).toHaveBeenCalledWith(3);
  });

  it('(5b) clicking the variation node calls onNodeClick with variation nodeId', () => {
    const { nodes, mainLine } = buildFixture();
    const onNodeClick = vi.fn();
    render(
      <VariationTree
        nodes={nodes}
        mainLine={mainLine}
        currentNodeId={4}
        onNodeClick={onNodeClick}
      />,
    );
    const d5Buttons = screen.getAllByTestId('variation-node-4');
    expect(d5Buttons.length).toBeGreaterThan(0);
    fireEvent.click(d5Buttons[0]!);
    expect(onNodeClick).toHaveBeenCalledWith(4);
  });

  it('(6) empty state shows "No moves yet" in at least one DOM path', () => {
    render(
      <VariationTree
        nodes={new Map()}
        mainLine={[]}
        currentNodeId={null}
        onNodeClick={vi.fn()}
      />,
    );
    // Both paths render the empty text (mobile via HorizontalMoveList emptyText,
    // desktop via the explicit <p>).
    const emptyTexts = screen.getAllByText('No moves yet');
    expect(emptyTexts.length).toBeGreaterThan(0);
  });

  // ─── Phase 140 Plan 02: two-level nesting + inline chips + markers ───────────

  it('(7) variation-pv-section renders in desktop when currentNodeId is on pvLine (level 1)', () => {
    const { nodes, mainLine, pvLine } = buildPvFixture();
    render(
      <VariationTree
        nodes={nodes}
        mainLine={mainLine}
        currentNodeId={10}
        pvLine={pvLine}
        onNodeClick={vi.fn()}
      />,
    );
    // Desktop shows the Level-1 PV block.
    expect(screen.getByTestId('variation-pv-section')).toBeTruthy();
    // No Level-2 block for a level-1 current node.
    expect(screen.queryByTestId('variation-subpv-section')).toBeNull();
  });

  it('(8) variation-subpv-section renders in desktop when currentNodeId is a level-2 sub-fork', () => {
    const { nodes, mainLine, pvLine } = buildPvFixture();
    render(
      <VariationTree
        nodes={nodes}
        mainLine={mainLine}
        currentNodeId={20}
        pvLine={pvLine}
        onNodeClick={vi.fn()}
      />,
    );
    // Desktop shows both Level-1 and Level-2 blocks.
    expect(screen.getByTestId('variation-pv-section')).toBeTruthy();
    expect(screen.getByTestId('variation-subpv-section')).toBeTruthy();
    // The sub-pv section should contain the sub-fork node (id=20, 'c4').
    const subpv = screen.getByTestId('variation-subpv-section');
    expect(subpv).toBeTruthy();
    // node 20 should appear inside or outside the subpv section as a button
    const c4Buttons = screen.getAllByTestId('variation-node-20');
    expect(c4Buttons.length).toBeGreaterThan(0);
  });

  it('(9) flaw-inline-tag-missed-{nodeId} shows the motif name + depth (UAT 260627)', () => {
    const { nodes, mainLine } = buildPvFixture();
    const flawMarkerByNodeId = new Map<NodeId, FlawMarkerEntry>([
      [2, { missedMotif: 'fork', allowedMotif: null, missedDepth: 1, allowedDepth: null, severity: 'blunder', ply: 1 }],
    ]);
    const onPvChipClick = vi.fn();
    render(
      <VariationTree
        nodes={nodes}
        mainLine={mainLine}
        currentNodeId={2}
        flawMarkerByNodeId={flawMarkerByNodeId}
        onPvChipClick={onPvChipClick}
        activePvNodeId={null}
        onNodeClick={vi.fn()}
      />,
    );
    // Desktop chip: flaw-inline-tag-missed-2 (node 2 = e5 on the main line).
    // New label = motif name + orientation-anchored depth (missed: depth+1 = 2).
    const chip = screen.getByTestId('flaw-inline-tag-missed-2');
    expect(chip).toBeTruthy();
    expect(chip.textContent).toContain('fork');
    expect(chip.textContent).toContain('2');
    expect(chip.textContent).not.toContain('Missed');
  });

  it('(9b) flaw-inline-tag-allowed-{nodeId} shows the motif name + depth (UAT 260627)', () => {
    const { nodes, mainLine } = buildPvFixture();
    const flawMarkerByNodeId = new Map<NodeId, FlawMarkerEntry>([
      [3, { missedMotif: null, allowedMotif: 'pin', missedDepth: null, allowedDepth: 1, severity: 'mistake', ply: 2 }],
    ]);
    render(
      <VariationTree
        nodes={nodes}
        mainLine={mainLine}
        currentNodeId={3}
        flawMarkerByNodeId={flawMarkerByNodeId}
        activePvNodeId={null}
        onNodeClick={vi.fn()}
      />,
    );
    // Quick 260628-1t5 DECISION 2: the move list is a navigable surface, so the allowed
    // +1 decision-anchor offset is dropped (anchored=false). depth 1 → display 2 (raw + 1),
    // reading on the same scale as missed (was 3 when anchored).
    const chip = screen.getByTestId('flaw-inline-tag-allowed-3');
    expect(chip).toBeTruthy();
    expect(chip.textContent).toContain('pin');
    expect(chip.textContent).toContain('2');
    expect(chip.textContent).not.toContain('Allowed');
  });

  it('(9c) clicking the chip calls onPvChipClick with nodeId and flaw info', () => {
    const { nodes, mainLine } = buildPvFixture();
    const flawMarkerByNodeId = new Map<NodeId, FlawMarkerEntry>([
      [2, { missedMotif: 'fork', allowedMotif: null, missedDepth: null, allowedDepth: null, severity: 'blunder', ply: 1 }],
    ]);
    const onPvChipClick = vi.fn();
    render(
      <VariationTree
        nodes={nodes}
        mainLine={mainLine}
        currentNodeId={null}
        flawMarkerByNodeId={flawMarkerByNodeId}
        onPvChipClick={onPvChipClick}
        activePvNodeId={null}
        onNodeClick={vi.fn()}
      />,
    );
    const chip = screen.getByTestId('flaw-inline-tag-missed-2');
    fireEvent.click(chip);
    expect(onPvChipClick).toHaveBeenCalledWith(2, { ply: 1, orientation: 'missed' });
  });

  it('(10) blunder severity marker renders for a non-tactic blunder flaw entry', () => {
    const { nodes, mainLine } = buildPvFixture();
    const flawMarkerByNodeId = new Map<NodeId, FlawMarkerEntry>([
      [2, { missedMotif: null, allowedMotif: null, missedDepth: null, allowedDepth: null, severity: 'blunder', ply: 1 }],
    ]);
    render(
      <VariationTree
        nodes={nodes}
        mainLine={mainLine}
        currentNodeId={null}
        flawMarkerByNodeId={flawMarkerByNodeId}
        onNodeClick={vi.fn()}
      />,
    );
    // Blunder marker is an SVG (aria-hidden). Node 2 row should have the marker.
    // We assert that no chip is shown (no tactic motif) but there IS an SVG in the row.
    expect(screen.queryByTestId('flaw-inline-tag-missed-2')).toBeNull();
    expect(screen.queryByTestId('flaw-inline-tag-allowed-2')).toBeNull();
    // The severity icon is rendered as an aria-hidden SVG — check via the desktop row area.
    const desktopTree = screen.getByTestId('variation-tree-desktop');
    // The SVG icons are present but aria-hidden; verify the node button is still there.
    expect(screen.getAllByTestId('variation-node-2').length).toBeGreaterThan(0);
    // SVG should be in the desktop tree.
    const svgs = desktopTree.querySelectorAll('svg');
    expect(svgs.length).toBeGreaterThan(0);
  });

  it('(11) inaccuracy severity renders no chip and no marker', () => {
    const { nodes, mainLine } = buildPvFixture();
    const flawMarkerByNodeId = new Map<NodeId, FlawMarkerEntry>([
      [2, { missedMotif: null, allowedMotif: null, missedDepth: null, allowedDepth: null, severity: 'inaccuracy', ply: 1 }],
    ]);
    render(
      <VariationTree
        nodes={nodes}
        mainLine={mainLine}
        currentNodeId={null}
        flawMarkerByNodeId={flawMarkerByNodeId}
        onNodeClick={vi.fn()}
      />,
    );
    // No chip for inaccuracy.
    expect(screen.queryByTestId('flaw-inline-tag-missed-2')).toBeNull();
    expect(screen.queryByTestId('flaw-inline-tag-allowed-2')).toBeNull();
    // No SVG icon for inaccuracy (D-03).
    const desktopTree = screen.getByTestId('variation-tree-desktop');
    const svgs = desktopTree.querySelectorAll('svg');
    expect(svgs.length).toBe(0);
  });

  it('(12) active chip (activePvNodeId === nodeId) shows ring and collapse aria-label', () => {
    const { nodes, mainLine } = buildPvFixture();
    const flawMarkerByNodeId = new Map<NodeId, FlawMarkerEntry>([
      [2, { missedMotif: 'fork', allowedMotif: null, missedDepth: null, allowedDepth: null, severity: 'blunder', ply: 1 }],
    ]);
    render(
      <VariationTree
        nodes={nodes}
        mainLine={mainLine}
        currentNodeId={null}
        flawMarkerByNodeId={flawMarkerByNodeId}
        onPvChipClick={vi.fn()}
        activePvNodeId={2}
        onNodeClick={vi.fn()}
      />,
    );
    const chip = screen.getByTestId('flaw-inline-tag-missed-2');
    // Active chip aria-label ends with "collapse".
    expect(chip.getAttribute('aria-label')).toContain('collapse');
  });

  it('(13) pvFetchError shows error message text next to the active chip', () => {
    const { nodes, mainLine } = buildPvFixture();
    const flawMarkerByNodeId = new Map<NodeId, FlawMarkerEntry>([
      [2, { missedMotif: 'fork', allowedMotif: null, missedDepth: null, allowedDepth: null, severity: 'blunder', ply: 1 }],
    ]);
    render(
      <VariationTree
        nodes={nodes}
        mainLine={mainLine}
        currentNodeId={null}
        flawMarkerByNodeId={flawMarkerByNodeId}
        activePvNodeId={2}
        pvFetchError={true}
        onNodeClick={vi.fn()}
      />,
    );
    // Error message appears next to the active chip.
    const errorText = screen.getByText('Tactic line not available for this flaw.');
    expect(errorText).toBeTruthy();
  });

  // Quick 260628-1t5 item 1: a freely-played move the live engine grades as a
  // blunder/mistake injects a severity-only entry keyed by the CURRENT (variation/free)
  // node. The move list must paint the matching glyph there, mirroring the board.
  it('(14) injected live severity on the CURRENT variation node renders the glyph', () => {
    const { nodes, mainLine, pvLine } = buildPvFixture();
    const flawMarkerByNodeId = new Map<NodeId, FlawMarkerEntry>([
      [10, { missedMotif: null, allowedMotif: null, missedDepth: null, allowedDepth: null, severity: 'blunder', ply: -1 }],
    ]);
    render(
      <VariationTree
        nodes={nodes}
        mainLine={mainLine}
        currentNodeId={10} // variation node 10 is the current node
        pvLine={pvLine}
        flawMarkerByNodeId={flawMarkerByNodeId}
        onNodeClick={vi.fn()}
      />,
    );
    // Severity-only entry → no tactic chip.
    expect(screen.queryByTestId('flaw-inline-tag-missed-10')).toBeNull();
    expect(screen.queryByTestId('flaw-inline-tag-allowed-10')).toBeNull();
    // The blunder glyph (aria-hidden SVG) renders in the desktop variation section.
    const desktopTree = screen.getByTestId('variation-tree-desktop');
    expect(desktopTree.querySelectorAll('svg').length).toBeGreaterThan(0);
    expect(screen.getAllByTestId('variation-node-10').length).toBeGreaterThan(0);
  });

  it('(15) injected severity on a NON-current variation node still renders the glyph', () => {
    const { nodes, mainLine, pvLine } = buildPvFixture();
    const flawMarkerByNodeId = new Map<NodeId, FlawMarkerEntry>([
      [10, { missedMotif: null, allowedMotif: null, missedDepth: null, allowedDepth: null, severity: 'blunder', ply: -1 }],
    ]);
    render(
      <VariationTree
        nodes={nodes}
        mainLine={mainLine}
        currentNodeId={11} // node 10 carries the entry but is NOT current
        pvLine={pvLine}
        flawMarkerByNodeId={flawMarkerByNodeId}
        onNodeClick={vi.fn()}
      />,
    );
    // Quick 260628-r5v UAT: the glyph now persists on every explored sideline move, not just
    // the current one — node 10's blunder entry still paints its glyph while node 11 is current.
    const desktopTree = screen.getByTestId('variation-tree-desktop');
    expect(desktopTree.querySelectorAll('svg').length).toBeGreaterThan(0);
  });
});
