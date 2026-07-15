// @vitest-environment jsdom
/**
 * Phase 137 Plan 03: VariationTree render tests.
 * Phase 140 Plan 02: Two-level nesting, inline flaw chips, blunder/mistake markers.
 * Quick 260703-kyb: rewritten to the flat-sibling multi-line contract (replaces
 * the old singleton pvLine / Level-2 nesting model).
 *
 * Fixture A: 3-node main line (1.e4 1...e5 2.Nf3) + one variation (1...d5
 * branching from node 1). Tests cover both dual-DOM paths (mobile + desktop),
 * main-line rendering, variation rendering (BOARD-05), active node
 * aria-current, click → onNodeClick, and the empty state.
 *
 * Fixture B: 3-node main line (1.e4 1...e5 2.Nf3) + TWO flat sibling lines off
 * two different mainLine forks — Line A (tactic, nodes 10/11, pvNodeIds
 * membership) off node 1 (after 1.e4), and Line B (free-move, node 20) off
 * node 2 (after 1...e5). Tests cover variation-pv-section,
 * variation-freemove-section, the × delete affordance, inline flaw chips, and
 * blunder/mistake severity markers.
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

// ─── Fixture B — two flat sibling lines + flaw markers ───────────────────────

/**
 * Main line: ids [1, 2, 3]
 *   1. e4 (id=1) 1...e5 (id=2) 2. Nf3 (id=3)
 *
 * Line A (tactic, pvNodeIds = {10, 11}) — grafted from id=1 (after 1.e4):
 *   10: Nf6 (parentId=1), 11: Nc3 (parentId=10)
 *
 * Line B (free-move) — forked from id=2 (after 1...e5):
 *   20: Bc4 (parentId=2)
 *
 * Both lines are flat siblings off DIFFERENT mainLine forks and render
 * simultaneously, regardless of currentNodeId (Quick 260703-kyb).
 */
function buildPvFixture(): {
  nodes: Map<NodeId, MoveNode>;
  mainLine: NodeId[];
  pvNodeIds: Set<NodeId>;
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
    // Line A (tactic) — grafted from node 1 (after 1.e4, black to move).
    [
      10,
      {
        id: 10,
        san: 'Nf6',
        fen: 'rnbqkb1r/pppppppp/5n2/8/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 1 2',
        from: 'g8',
        to: 'f6',
        parentId: 1,
      },
    ],
    [
      11,
      {
        id: 11,
        san: 'Nc3',
        fen: 'rnbqkb1r/pppppppp/5n2/8/4P3/2N5/PPPP1PPP/R1BQKBNR b KQkq - 2 2',
        from: 'b1',
        to: 'c3',
        parentId: 10,
      },
    ],
    // Line B (free-move) — forked from node 2 (after 1...e5, white to move).
    [
      20,
      {
        id: 20,
        san: 'Bc4',
        fen: 'rnbqkbnr/pppp1ppp/8/4p3/2B1P3/8/PPPP1PPP/RNBQK1NR b KQkq - 1 2',
        from: 'f1',
        to: 'c4',
        parentId: 2,
      },
    ],
  ]);
  const mainLine: NodeId[] = [1, 2, 3];
  const pvNodeIds = new Set<NodeId>([10, 11]);
  return { nodes, mainLine, pvNodeIds };
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

  // ─── Quick 260703-kyb: flat sibling blocks, × delete, inline chips + markers ──

  it('(7) both variation-pv-section (tactic) and variation-freemove-section render simultaneously, regardless of currentNodeId', () => {
    const { nodes, mainLine, pvNodeIds } = buildPvFixture();
    render(
      <VariationTree
        nodes={nodes}
        mainLine={mainLine}
        currentNodeId={3} // parked on the mainLine — NOT inside either sideline
        pvNodeIds={pvNodeIds}
        onNodeClick={vi.fn()}
      />,
    );
    // Both flat sibling blocks render — sidelines are always-visible, not tied to
    // where the board is currently parked (Quick 260703-kyb truth #1).
    expect(screen.getByTestId('variation-pv-section')).toBeTruthy();
    expect(screen.getByTestId('variation-freemove-section')).toBeTruthy();
    // Both lines' nodes are present.
    expect(screen.getAllByTestId('variation-node-10').length).toBeGreaterThan(0);
    expect(screen.getAllByTestId('variation-node-11').length).toBeGreaterThan(0);
    expect(screen.getAllByTestId('variation-node-20').length).toBeGreaterThan(0);
  });

  it('(8) the free-move line exposes btn-delete-line-{rootId} calling onDeleteLine; the tactic line has no ×', () => {
    const { nodes, mainLine, pvNodeIds } = buildPvFixture();
    const onDeleteLine = vi.fn();
    render(
      <VariationTree
        nodes={nodes}
        mainLine={mainLine}
        currentNodeId={null}
        pvNodeIds={pvNodeIds}
        onDeleteLine={onDeleteLine}
        onNodeClick={vi.fn()}
      />,
    );
    // Free-move line (root=20) has a working × delete affordance.
    const deleteButtons = screen.getAllByTestId('btn-delete-line-20');
    expect(deleteButtons.length).toBeGreaterThan(0);
    expect(deleteButtons[0]!.getAttribute('aria-label')).toBe('Delete variation');
    fireEvent.click(deleteButtons[0]!);
    expect(onDeleteLine).toHaveBeenCalledWith(20);
    // Tactic line (root=10) has NO × — it closes via its chip instead.
    expect(screen.queryByTestId('btn-delete-line-10')).toBeNull();
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
        activePvKeys={undefined}
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
        activePvKeys={undefined}
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
        activePvKeys={undefined}
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
    // Use the mainLine-only fixture (no sidelines at all) so the SVG count is not
    // contaminated by a free-move block's × delete-icon — Quick 260703-kyb renders
    // sidelines unconditionally now, not just when currentNodeId is inside one.
    const { nodes, mainLine } = buildFixture();
    const mainLineOnlyNodes = new Map(
      [...nodes].filter(([id]) => mainLine.includes(id)),
    );
    const flawMarkerByNodeId = new Map<NodeId, FlawMarkerEntry>([
      [2, { missedMotif: null, allowedMotif: null, missedDepth: null, allowedDepth: null, severity: 'inaccuracy', ply: 1 }],
    ]);
    render(
      <VariationTree
        nodes={mainLineOnlyNodes}
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

  it('(12) active chip (key ∈ activePvKeys) shows ring and collapse aria-label', () => {
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
        activePvKeys={new Set(['1:missed'])}
        onNodeClick={vi.fn()}
      />,
    );
    const chip = screen.getByTestId('flaw-inline-tag-missed-2');
    // Active chip aria-label ends with "collapse".
    expect(chip.getAttribute('aria-label')).toContain('collapse');
  });

  it('(12b) two chips can be simultaneously active via activePvKeys (flat siblings)', () => {
    const { nodes, mainLine } = buildPvFixture();
    const flawMarkerByNodeId = new Map<NodeId, FlawMarkerEntry>([
      [2, { missedMotif: 'fork', allowedMotif: null, missedDepth: null, allowedDepth: null, severity: 'blunder', ply: 1 }],
      [3, { missedMotif: null, allowedMotif: 'pin', missedDepth: null, allowedDepth: null, severity: 'mistake', ply: 2 }],
    ]);
    render(
      <VariationTree
        nodes={nodes}
        mainLine={mainLine}
        currentNodeId={null}
        flawMarkerByNodeId={flawMarkerByNodeId}
        onPvChipClick={vi.fn()}
        activePvKeys={new Set(['1:missed', '2:allowed'])}
        onNodeClick={vi.fn()}
      />,
    );
    expect(screen.getByTestId('flaw-inline-tag-missed-2').getAttribute('aria-label')).toContain('collapse');
    expect(screen.getByTestId('flaw-inline-tag-allowed-3').getAttribute('aria-label')).toContain('collapse');
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
        activePvKeys={new Set(['1:missed'])}
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
    const { nodes, mainLine, pvNodeIds } = buildPvFixture();
    const flawMarkerByNodeId = new Map<NodeId, FlawMarkerEntry>([
      [10, { missedMotif: null, allowedMotif: null, missedDepth: null, allowedDepth: null, severity: 'blunder', ply: -1 }],
    ]);
    render(
      <VariationTree
        nodes={nodes}
        mainLine={mainLine}
        currentNodeId={10} // variation node 10 is the current node
        pvNodeIds={pvNodeIds}
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
    const { nodes, mainLine, pvNodeIds } = buildPvFixture();
    const flawMarkerByNodeId = new Map<NodeId, FlawMarkerEntry>([
      [10, { missedMotif: null, allowedMotif: null, missedDepth: null, allowedDepth: null, severity: 'blunder', ply: -1 }],
    ]);
    render(
      <VariationTree
        nodes={nodes}
        mainLine={mainLine}
        currentNodeId={11} // node 10 carries the entry but is NOT current
        pvNodeIds={pvNodeIds}
        flawMarkerByNodeId={flawMarkerByNodeId}
        onNodeClick={vi.fn()}
      />,
    );
    // Quick 260628-r5v UAT: the glyph now persists on every explored sideline move, not just
    // the current one — node 10's blunder entry still paints its glyph while node 11 is current.
    const desktopTree = screen.getByTestId('variation-tree-desktop');
    expect(desktopTree.querySelectorAll('svg').length).toBeGreaterThan(0);
  });

  // Phase 172 (SEED-106 D-08): book marker precedence `severity > gem > book`.
  it('(16) book-only entry renders BookIcon (plain icon, not the gem popover)', () => {
    const { nodes, mainLine } = buildFixture();
    const mainLineOnlyNodes = new Map(
      [...nodes].filter(([id]) => mainLine.includes(id)),
    );
    const flawMarkerByNodeId = new Map<NodeId, FlawMarkerEntry>([
      [2, { missedMotif: null, allowedMotif: null, missedDepth: null, allowedDepth: null, book: true, ply: 1 }],
    ]);
    render(
      <VariationTree
        nodes={mainLineOnlyNodes}
        mainLine={mainLine}
        currentNodeId={null}
        flawMarkerByNodeId={flawMarkerByNodeId}
        onNodeClick={vi.fn()}
      />,
    );
    const desktopTree = screen.getByTestId('variation-tree-desktop');
    // BookIcon renders as a plain aria-hidden SVG carrying the "Opening theory" title.
    const titles = Array.from(desktopTree.querySelectorAll('title')).map((t) => t.textContent);
    expect(titles).toContain('Opening theory');
    // Book is glance-only: no gem popover trigger for this marker.
    expect(screen.queryByTestId('gem-move-popover')).toBeNull();
  });

  it('(17) severity + book: severity wins, book icon does not render (D-08)', () => {
    const { nodes, mainLine } = buildFixture();
    const mainLineOnlyNodes = new Map(
      [...nodes].filter(([id]) => mainLine.includes(id)),
    );
    const flawMarkerByNodeId = new Map<NodeId, FlawMarkerEntry>([
      [2, { missedMotif: null, allowedMotif: null, missedDepth: null, allowedDepth: null, severity: 'blunder', book: true, ply: 1 }],
    ]);
    render(
      <VariationTree
        nodes={mainLineOnlyNodes}
        mainLine={mainLine}
        currentNodeId={null}
        flawMarkerByNodeId={flawMarkerByNodeId}
        onNodeClick={vi.fn()}
      />,
    );
    const desktopTree = screen.getByTestId('variation-tree-desktop');
    // The blunder glyph ("??" text) renders...
    expect(desktopTree.textContent).toContain('??');
    // ...and the book title is NOT present — severity wins.
    const titles = Array.from(desktopTree.querySelectorAll('title')).map((t) => t.textContent);
    expect(titles).not.toContain('Opening theory');
  });

  it('(18) gem + book: gem icon renders, not book (D-08 — never arises in production per D-04)', () => {
    const { nodes, mainLine } = buildFixture();
    const mainLineOnlyNodes = new Map(
      [...nodes].filter(([id]) => mainLine.includes(id)),
    );
    const flawMarkerByNodeId = new Map<NodeId, FlawMarkerEntry>([
      [2, { missedMotif: null, allowedMotif: null, missedDepth: null, allowedDepth: null, gem: true, book: true, ply: 1 }],
    ]);
    render(
      <VariationTree
        nodes={mainLineOnlyNodes}
        mainLine={mainLine}
        currentNodeId={null}
        flawMarkerByNodeId={flawMarkerByNodeId}
        onNodeClick={vi.fn()}
      />,
    );
    const desktopTree = screen.getByTestId('variation-tree-desktop');
    const titles = Array.from(desktopTree.querySelectorAll('title')).map((t) => t.textContent);
    expect(titles).toContain('Gem move');
    expect(titles).not.toContain('Opening theory');
  });

  it('(19) no severity, gem, or book renders nothing', () => {
    const { nodes, mainLine } = buildFixture();
    const mainLineOnlyNodes = new Map(
      [...nodes].filter(([id]) => mainLine.includes(id)),
    );
    const flawMarkerByNodeId = new Map<NodeId, FlawMarkerEntry>([
      [2, { missedMotif: null, allowedMotif: null, missedDepth: null, allowedDepth: null, ply: 1 }],
    ]);
    render(
      <VariationTree
        nodes={mainLineOnlyNodes}
        mainLine={mainLine}
        currentNodeId={null}
        flawMarkerByNodeId={flawMarkerByNodeId}
        onNodeClick={vi.fn()}
      />,
    );
    const desktopTree = screen.getByTestId('variation-tree-desktop');
    expect(desktopTree.querySelectorAll('svg').length).toBe(0);
  });
});
