// @vitest-environment jsdom
/**
 * useAnalysisBoard hook tests (Phase 137, Plan 01; extended Phase 140, Plan 01).
 *
 * Required D-05 behaviors (Phase 137):
 * 1. Mid-line fork: a move at a mid-line node creates a child node; mainLine is NOT truncated.
 * 2. Navigation: goBack / goForward / goToNode move currentNodeId and position correctly.
 * 3. O(1) goToNode: position equals the stored FEN, not a root-replay artifact.
 * 4. loadMainLine + isOnMainLine: seeds mainLine IDs in order; true for seeded, false for forked.
 *
 * Phase 140 Plan 01 — PV-nesting invariants:
 * 5. insertPvLine: pvLine length matches pvSans, nodes chain to forkNodeId, mainLine unmutated.
 * 6. clearPvLine: pvLine emptied, node ids removed, currentNodeId back on mainLine.
 * 7. Level-2 fork: makeMove from a pvLine node creates a node NOT in pvLine.
 */

import { describe, it, expect } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useAnalysisBoard } from '../useAnalysisBoard';
import type { MoveNode, NodeId, AnalysisBoardState } from '../useAnalysisBoard';

// ─── Chess position constants ────────────────────────────────────────────────

// After 1. e4 e5 (white to move). Verified legal from standard start.
const ROOT_FEN =
  'rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2';

// Moves playable from ROOT_FEN (white):
// 2. Nf3 = g1→f3, 2. Nc3 = b1→c3
// After Nf3 (black to move):
//   2... Nc6 = b8→c6 (main line), 2... Nf6 = g8→f6 (fork alternative)
// After Nf3 Nc6 (white to move):
//   3. Bc4 = f1→c4

const MOVE_NF3 = { from: 'g1', to: 'f3' } as const;
const MOVE_NC3 = { from: 'b1', to: 'c3' } as const; // alternative white move 2
const MOVE_NC6 = { from: 'b8', to: 'c6' } as const;
const MOVE_NF6 = { from: 'g8', to: 'f6' } as const; // alternative black move 2
const MOVE_BC4 = { from: 'f1', to: 'c4' } as const;

// SAN representation for loadMainLine
const MAIN_LINE_SANS = ['Nf3', 'Nc6', 'Bc4'];

describe('useAnalysisBoard', () => {
  // ── Behavior 1: Mid-line fork ───────────────────────────────────────────

  it('mid-line fork: move at a mid-line node creates a child node; mainLine is unchanged', () => {
    const { result } = renderHook(() => useAnalysisBoard(ROOT_FEN));

    // Seed a 2-move main line: Nf3, Nc6
    act(() => {
      result.current.loadMainLine(['Nf3', 'Nc6'], ROOT_FEN);
    });
    const mainLineBefore = [...result.current.mainLine];
    expect(mainLineBefore).toHaveLength(2);

    // node 0 = after Nf3 (black to move) — a mid-line node (not the last)
    const midNodeId: NodeId = mainLineBefore[0]!;
    act(() => { result.current.goToNode(midNodeId); });

    const sizeBeforeFork = result.current.nodes.size;

    // Fork: play Nf6 instead of Nc6
    let forkMoved = false;
    act(() => { forkMoved = result.current.makeMove(MOVE_NF6.from, MOVE_NF6.to); });

    // makeMove must return true for a legal move
    expect(forkMoved).toBe(true);
    // nodes.size grows by exactly 1
    expect(result.current.nodes.size).toBe(sizeBeforeFork + 1);
    // new node's parentId equals the mid-line node
    const forkNodeId: NodeId | null = result.current.currentNodeId;
    expect(forkNodeId).not.toBeNull();
    const forkNode: MoveNode | undefined = result.current.nodes.get(forkNodeId!);
    expect(forkNode?.parentId).toBe(midNodeId);
    // mainLine is NOT truncated
    expect(result.current.mainLine).toEqual(mainLineBefore);
  });

  // ── Behavior 2: Navigation ──────────────────────────────────────────────

  it('goBack / goForward / goToNode move currentNodeId and position correctly', () => {
    const { result } = renderHook(() => useAnalysisBoard(ROOT_FEN));

    // Build a 2-node chain
    act(() => { result.current.makeMove(MOVE_NF3.from, MOVE_NF3.to); });
    const node0Id: NodeId | null = result.current.currentNodeId;
    expect(node0Id).not.toBeNull();

    act(() => { result.current.makeMove(MOVE_NC6.from, MOVE_NC6.to); });
    const node1Id: NodeId | null = result.current.currentNodeId;
    expect(node1Id).not.toBeNull();

    // goBack: node1 → node0
    act(() => { result.current.goBack(); });
    expect(result.current.currentNodeId).toBe(node0Id);

    // goBack from root-level node (node0, parentId=null) → position === rootFen
    act(() => { result.current.goBack(); });
    expect(result.current.currentNodeId).toBeNull();
    expect(result.current.position).toBe(ROOT_FEN);

    // goBack at root is a no-op
    act(() => { result.current.goBack(); });
    expect(result.current.currentNodeId).toBeNull();

    // goForward from root → node0 (first child)
    act(() => { result.current.goForward(); });
    expect(result.current.currentNodeId).toBe(node0Id);

    // goToNode: jump directly to node1
    act(() => { result.current.goToNode(node1Id!); });
    expect(result.current.currentNodeId).toBe(node1Id);

    // goForward from a childless node is a no-op
    const positionAtLeaf = result.current.position;
    act(() => { result.current.goForward(); });
    expect(result.current.currentNodeId).toBe(node1Id);
    expect(result.current.position).toBe(positionAtLeaf);
  });

  // ── Behavior 3: O(1) goToNode ───────────────────────────────────────────

  it('goToNode: position equals the stored FEN directly (no root replay)', () => {
    const { result } = renderHook(() => useAnalysisBoard(ROOT_FEN));

    // Build several nodes
    act(() => { result.current.makeMove(MOVE_NF3.from, MOVE_NF3.to); });
    const node0Id: NodeId | null = result.current.currentNodeId;
    expect(node0Id).not.toBeNull();

    // Capture the FEN stored in node0 at creation time
    const storedFenNode0 = result.current.nodes.get(node0Id!)?.fen;
    expect(storedFenNode0).toBeDefined();

    act(() => { result.current.makeMove(MOVE_NC6.from, MOVE_NC6.to); });
    act(() => { result.current.makeMove(MOVE_BC4.from, MOVE_BC4.to); });

    // goToNode reads the stored FEN directly — no replay
    act(() => { result.current.goToNode(node0Id!); });
    expect(result.current.position).toBe(storedFenNode0);
    expect(result.current.currentNodeId).toBe(node0Id);
  });

  // ── Behavior 4: loadMainLine + isOnMainLine ─────────────────────────────

  it('loadMainLine seeds mainLine IDs in order; isOnMainLine true for seeded, false for forked', () => {
    const { result } = renderHook(() => useAnalysisBoard(ROOT_FEN));

    act(() => {
      result.current.loadMainLine(MAIN_LINE_SANS, ROOT_FEN);
    });

    // One id per SAN
    expect(result.current.mainLine).toHaveLength(MAIN_LINE_SANS.length);

    // isOnMainLine true for every seeded id
    // Using AnalysisBoardState['nodes'] type to satisfy noUncheckedIndexedAccess
    const nodes: AnalysisBoardState['nodes'] = result.current.nodes;
    for (const id of result.current.mainLine) {
      expect(result.current.isOnMainLine(id)).toBe(true);
      // Each seeded node's FEN must be set and differ from root
      const node: MoveNode | undefined = nodes.get(id);
      expect(node).toBeDefined();
      expect(node?.fen).not.toBe(ROOT_FEN);
    }

    // Fork from node0 (after Nf3, black to move) — play Nf6 instead of Nc6
    const node0Id: NodeId = result.current.mainLine[0]!;
    act(() => { result.current.goToNode(node0Id); });
    act(() => { result.current.makeMove(MOVE_NF6.from, MOVE_NF6.to); });

    const forkedId: NodeId | null = result.current.currentNodeId;
    expect(forkedId).not.toBeNull();
    // Forked node is NOT on the main line
    expect(result.current.isOnMainLine(forkedId!)).toBe(false);
  });

  // ── Boundary: illegal move ──────────────────────────────────────────────

  it('makeMove returns false for an illegal move and leaves state unchanged', () => {
    const { result } = renderHook(() => useAnalysisBoard(ROOT_FEN));

    const sizeBeforeIllegal = result.current.nodes.size;
    let illegalResult = true;
    // a1→a1 is not a legal chess move
    act(() => { illegalResult = result.current.makeMove('a1', 'a1'); });

    expect(illegalResult).toBe(false);
    expect(result.current.nodes.size).toBe(sizeBeforeIllegal);
    expect(result.current.currentNodeId).toBeNull();
    expect(result.current.position).toBe(ROOT_FEN);
  });

  // ── Behavior 5: goToRoot ────────────────────────────────────────────────

  it('goToRoot: sets currentNodeId to null without clearing nodes or mainLine (Phase 139)', () => {
    const { result } = renderHook(() => useAnalysisBoard(ROOT_FEN));

    // Seed a mainLine so nodes + mainLine are non-empty
    act(() => {
      result.current.loadMainLine(MAIN_LINE_SANS, ROOT_FEN);
    });
    // After loadMainLine, currentNodeId is the last node (not null)
    expect(result.current.currentNodeId).not.toBeNull();
    const lineLength = result.current.mainLine.length;
    expect(lineLength).toBe(MAIN_LINE_SANS.length);

    // goToRoot sets currentNodeId to null (decision position)
    act(() => { result.current.goToRoot(); });
    expect(result.current.currentNodeId).toBeNull();
    expect(result.current.position).toBe(ROOT_FEN);

    // nodes and mainLine are UNCHANGED
    expect(result.current.mainLine).toHaveLength(lineLength);
    expect(result.current.nodes.size).toBe(lineLength);
  });

  // ── Phase 140-01 Behavior 5: insertPvLine invariants ───────────────────

  it('insertPvLine: pvLine length === pvSans.length; nodes chain to forkNodeId; mainLine unmutated; isOnPvLine/isOnMainLine correct', () => {
    const { result } = renderHook(() => useAnalysisBoard(ROOT_FEN));

    // Seed a 3-move main line: Nf3, Nc6, Bc4
    act(() => {
      result.current.loadMainLine(MAIN_LINE_SANS, ROOT_FEN);
    });
    const mainLineBefore = [...result.current.mainLine];
    expect(mainLineBefore).toHaveLength(3);

    // Fork from node0 (after Nf3, black to move)
    const forkNodeId: NodeId = mainLineBefore[0]!;
    // PV: Nf6 (black), Bc4 (white) — both legal from node0 FEN (post-Nf3, black to move)
    const pvSans = ['Nf6', 'Bc4'];

    act(() => {
      result.current.insertPvLine(pvSans, forkNodeId);
    });

    // pvLine.length === pvSans.length
    expect(result.current.pvLine).toHaveLength(pvSans.length);

    // every pvLine node's parentId chain reaches forkNodeId
    const pvLine = result.current.pvLine;
    const nodes = result.current.nodes;
    const firstPvId = pvLine[0]!;
    const firstPvNode = nodes.get(firstPvId);
    expect(firstPvNode?.parentId).toBe(forkNodeId);

    // mainLine is reference-unchanged (same ids)
    expect(result.current.mainLine).toEqual(mainLineBefore);

    // currentNodeId is forkNodeId (not first PV move)
    expect(result.current.currentNodeId).toBe(forkNodeId);

    // isOnPvLine true for first PV node, isOnMainLine false
    expect(result.current.isOnPvLine(firstPvId)).toBe(true);
    expect(result.current.isOnMainLine(firstPvId)).toBe(false);
  });

  // ── Quick thl item 4: forward steps into the open flaw sideline ─────────
  it('goForward from the fork node steps into the grafted pvLine, not the main line', () => {
    const { result } = renderHook(() => useAnalysisBoard(ROOT_FEN));

    act(() => {
      result.current.loadMainLine(MAIN_LINE_SANS, ROOT_FEN);
    });
    const mainLine = [...result.current.mainLine];
    const forkNodeId: NodeId = mainLine[0]!; // after Nf3, black to move

    act(() => {
      result.current.insertPvLine(['Nf6', 'Bc4'], forkNodeId);
    });
    // insertPvLine parks at the fork node.
    expect(result.current.currentNodeId).toBe(forkNodeId);
    const firstPvId = result.current.pvLine[0]!;

    // Forward from the fork must enter the sideline (pvLine[0]), not mainLine[1].
    act(() => {
      result.current.goForward();
    });
    expect(result.current.currentNodeId).toBe(firstPvId);
    expect(result.current.currentNodeId).not.toBe(mainLine[1]);
  });

  // ── Phase 140-01 Behavior 6: clearPvLine invariants ────────────────────

  it('clearPvLine: pvLine emptied, pvLine node ids removed from nodes, currentNodeId on mainLine', () => {
    const { result } = renderHook(() => useAnalysisBoard(ROOT_FEN));

    act(() => {
      result.current.loadMainLine(MAIN_LINE_SANS, ROOT_FEN);
    });
    const forkNodeId: NodeId = result.current.mainLine[0]!;

    // Navigate into PV so currentNodeId is on a pvLine node
    act(() => {
      result.current.insertPvLine(['Nf6'], forkNodeId);
    });
    const pvLine = [...result.current.pvLine];
    expect(pvLine).toHaveLength(1);

    // Navigate to first pv node
    const pvNodeId = pvLine[0]!;
    act(() => {
      result.current.goToNode(pvNodeId);
    });
    expect(result.current.currentNodeId).toBe(pvNodeId);

    act(() => {
      result.current.clearPvLine();
    });

    // pvLine is empty
    expect(result.current.pvLine).toHaveLength(0);

    // Prior pvLine node ids no longer in nodes map
    for (const id of pvLine) {
      expect(result.current.nodes.has(id)).toBe(false);
    }

    // currentNodeId is back on mainLine
    const currentId = result.current.currentNodeId;
    expect(currentId).not.toBeNull();
    expect(result.current.isOnMainLine(currentId!)).toBe(true);
  });

  // ── Phase 140-01 Behavior 7: level-2 fork — makeMove from pvLine node ──

  it('makeMove from a pvLine node creates a node NOT in pvLine (level-2 sub-sideline)', () => {
    const { result } = renderHook(() => useAnalysisBoard(ROOT_FEN));

    act(() => {
      result.current.loadMainLine(MAIN_LINE_SANS, ROOT_FEN);
    });
    const forkNodeId: NodeId = result.current.mainLine[0]!;

    // Insert a PV: Nf6 from forkNodeId (after Nf3, black to move)
    act(() => {
      result.current.insertPvLine(['Nf6'], forkNodeId);
    });
    const pvLine = [...result.current.pvLine];
    const pvNodeId = pvLine[0]!;

    // Navigate to the PV node and make a move from it
    act(() => {
      result.current.goToNode(pvNodeId);
    });

    // Make a legal white move (Bc4) from the PV node position
    act(() => {
      result.current.makeMove('f1', 'c4');
    });

    const newNodeId = result.current.currentNodeId;
    expect(newNodeId).not.toBeNull();

    // The new node is NOT in pvLine
    expect(result.current.isOnPvLine(newNodeId!)).toBe(false);
    // The original pvLine is unchanged
    expect(result.current.pvLine).toEqual(pvLine);
  });

  // ── Boundary: goForward with multiple children picks lowest-id child ────

  it('goForward from root picks the first child (lowest id) when multiple children exist', () => {
    const { result } = renderHook(() => useAnalysisBoard(ROOT_FEN));

    // Make two moves from root: Nf3 then go back and make Nc3
    act(() => { result.current.makeMove(MOVE_NF3.from, MOVE_NF3.to); });
    const firstChildId: NodeId | null = result.current.currentNodeId;

    act(() => { result.current.goBack(); }); // back to root

    act(() => { result.current.makeMove(MOVE_NC3.from, MOVE_NC3.to); });

    act(() => { result.current.goBack(); }); // back to root

    // goForward from root → first child inserted (lowest id)
    act(() => { result.current.goForward(); });
    expect(result.current.currentNodeId).toBe(firstChildId);
  });

  // ── playUciLine: graft the whole engine line up to the clicked move ─────

  it('playUciLine grafts the full UCI prefix from the current node and lands on the last move', () => {
    const { result } = renderHook(() => useAnalysisBoard(ROOT_FEN));

    const sizeBefore = result.current.nodes.size; // 0 — empty tree at root

    // Play three UCI moves from root: Nf3, Nc6, Bc4.
    act(() => { result.current.playUciLine(['g1f3', 'b8c6', 'f1c4']); });

    // Three new nodes were grafted (not just the clicked move).
    expect(result.current.nodes.size).toBe(sizeBefore + 3);

    // The board lands on the LAST move (Bc4), and the chain back to root is intact.
    const landedId = result.current.currentNodeId;
    expect(landedId).not.toBeNull();
    const landed = result.current.nodes.get(landedId!);
    expect(landed?.san).toBe('Bc4');
    const parent = result.current.nodes.get(landed!.parentId!);
    expect(parent?.san).toBe('Nc6');
    const grandparent = result.current.nodes.get(parent!.parentId!);
    expect(grandparent?.san).toBe('Nf3');
    expect(grandparent?.parentId).toBeNull(); // chains back to root
  });

  it('playUciLine reuses matching children instead of creating duplicate branches', () => {
    const { result } = renderHook(() => useAnalysisBoard(ROOT_FEN));

    act(() => { result.current.playUciLine(['g1f3', 'b8c6', 'f1c4']); });
    const sizeAfterFirst = result.current.nodes.size; // 3

    // Re-play a prefix of the same line from root: reuses Nf3 + Nc6, no new nodes.
    act(() => { result.current.goToRoot(); });
    act(() => { result.current.playUciLine(['g1f3', 'b8c6']); });

    expect(result.current.nodes.size).toBe(sizeAfterFirst); // no duplicates
    expect(result.current.nodes.get(result.current.currentNodeId!)?.san).toBe('Nc6');
  });
});
