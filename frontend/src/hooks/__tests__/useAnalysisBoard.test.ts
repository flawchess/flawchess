// @vitest-environment jsdom
/**
 * useAnalysisBoard hook tests (Phase 137, Plan 01; extended Phase 140, Plan 01;
 * rewritten to the multi-line flat-sibling contract, Quick 260703-kyb).
 *
 * Required D-05 behaviors (Phase 137):
 * 1. Mid-line fork: a move at a mid-line node creates a child node; mainLine is NOT truncated.
 * 2. Navigation: goBack / goForward / goToNode move currentNodeId and position correctly.
 * 3. O(1) goToNode: position equals the stored FEN, not a root-replay artifact.
 * 4. loadMainLine + isOnMainLine: seeds mainLine IDs in order; true for seeded, false for forked.
 *
 * Quick 260703-kyb — multi-line flat-sibling invariants (replaces the old singleton
 * pvLine/clearPvLine/Level-2 behaviors):
 * 5. insertPvLine unions ids: opening two lines off two different forks leaves both
 *    isOnPvLine-true simultaneously; mainLine stays unmutated.
 * 6. deleteSubtree removes exactly one line's ids (the other line is untouched) and
 *    recovers currentNodeId to the deleted line's fork parent when the board was inside it.
 * 7. clearAllSidelines strips every non-mainLine node and empties pvNodeIds.
 * 8. goForward from a fork still steps into an open sideline (pvNodeIds membership).
 * 9. makeMove off a PV node yields a node with isOnPvLine=false (a free-move sub-fork).
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

  // ── Quick 260703-kyb Behavior 5: insertPvLine unions ids across lines ──

  it('insertPvLine unions ids: two lines off two different forks are both open simultaneously; mainLine unmutated', () => {
    const { result } = renderHook(() => useAnalysisBoard(ROOT_FEN));

    // Seed a 3-move main line: Nf3, Nc6, Bc4
    act(() => {
      result.current.loadMainLine(MAIN_LINE_SANS, ROOT_FEN);
    });
    const mainLineBefore = [...result.current.mainLine];
    expect(mainLineBefore).toHaveLength(3);

    // Line A: fork from node0 (after Nf3, black to move) — Nf6, Bc4.
    const forkA: NodeId = mainLineBefore[0]!;
    act(() => {
      result.current.insertPvLine(['Nf6', 'Bc4'], forkA);
    });
    const lineARootId = 3; // first grafted id after the 3-node main line (ids 0,1,2)
    expect(result.current.isOnPvLine(lineARootId)).toBe(true);

    // Line B: fork from node1 (after Nf3 Nc6, white to move) — Bb5 (Ruy Lopez).
    const forkB: NodeId = mainLineBefore[1]!;
    act(() => {
      result.current.insertPvLine(['Bb5'], forkB);
    });
    const lineBRootId = 5; // next id after line A's two nodes (3, 4)

    // Both lines' nodes are simultaneously in pvNodeIds — insertPvLine UNIONS, never clobbers.
    expect(result.current.isOnPvLine(lineARootId)).toBe(true);
    expect(result.current.isOnPvLine(4)).toBe(true); // line A's second node
    expect(result.current.isOnPvLine(lineBRootId)).toBe(true);

    // mainLine is reference-unchanged (same ids)
    expect(result.current.mainLine).toEqual(mainLineBefore);

    // nodes.size = 3 mainLine + 2 (line A) + 1 (line B)
    expect(result.current.nodes.size).toBe(6);
  });

  // ── Quick thl item 4 (retained under the multi-line contract) ──────────
  it('goForward from the fork node steps into an open sideline (pvNodeIds membership), not the main line', () => {
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
    const firstPvId = 3;
    expect(result.current.isOnPvLine(firstPvId)).toBe(true);

    // Forward from the fork must enter the sideline, not mainLine[1].
    act(() => {
      result.current.goForward();
    });
    expect(result.current.currentNodeId).toBe(firstPvId);
    expect(result.current.currentNodeId).not.toBe(mainLine[1]);
  });

  // ── Quick 260703-kyb Behavior 6: deleteSubtree removes exactly one line ──

  it('deleteSubtree removes exactly one open line and recovers currentNodeId to its fork parent; the other line is untouched', () => {
    const { result } = renderHook(() => useAnalysisBoard(ROOT_FEN));

    act(() => {
      result.current.loadMainLine(MAIN_LINE_SANS, ROOT_FEN);
    });
    const mainLine = [...result.current.mainLine];
    const forkA: NodeId = mainLine[0]!;
    const forkB: NodeId = mainLine[1]!;

    act(() => {
      result.current.insertPvLine(['Nf6', 'Bc4'], forkA); // ids 3, 4
    });
    act(() => {
      result.current.insertPvLine(['Bb5'], forkB); // id 5
    });

    // Navigate the board into line A (node 4, parent=3, parent's parent=forkA).
    act(() => {
      result.current.goToNode(4);
    });
    expect(result.current.currentNodeId).toBe(4);

    // Delete line A's root (id 3) — removes 3 and 4.
    act(() => {
      result.current.deleteSubtree(3);
    });

    expect(result.current.nodes.has(3)).toBe(false);
    expect(result.current.nodes.has(4)).toBe(false);
    expect(result.current.isOnPvLine(3)).toBe(false);
    expect(result.current.isOnPvLine(4)).toBe(false);

    // Line B (id 5) is untouched.
    expect(result.current.nodes.has(5)).toBe(true);
    expect(result.current.isOnPvLine(5)).toBe(true);

    // currentNodeId recovers to line A's fork parent (forkA), since it was inside the
    // deleted subtree.
    expect(result.current.currentNodeId).toBe(forkA);
  });

  it('deleteSubtree is a no-op on currentNodeId when the board is NOT inside the deleted subtree', () => {
    const { result } = renderHook(() => useAnalysisBoard(ROOT_FEN));

    act(() => {
      result.current.loadMainLine(MAIN_LINE_SANS, ROOT_FEN);
    });
    const forkA: NodeId = result.current.mainLine[0]!;

    act(() => {
      result.current.insertPvLine(['Nf6'], forkA); // id 3
    });
    // Stay on the main line (goToNode to mainLine[2]).
    const mainLineLeaf = result.current.mainLine[2]!;
    act(() => {
      result.current.goToNode(mainLineLeaf);
    });

    act(() => {
      result.current.deleteSubtree(3);
    });

    expect(result.current.nodes.has(3)).toBe(false);
    // currentNodeId is unchanged — the board was never inside the deleted subtree.
    expect(result.current.currentNodeId).toBe(mainLineLeaf);
  });

  // ── Quick 260703-kyb Behavior 7: clearAllSidelines strips every non-mainLine node ──

  it('clearAllSidelines strips every non-mainLine node, empties pvNodeIds, and recovers currentNodeId to mainLine', () => {
    const { result } = renderHook(() => useAnalysisBoard(ROOT_FEN));

    act(() => {
      result.current.loadMainLine(MAIN_LINE_SANS, ROOT_FEN);
    });
    const mainLine = [...result.current.mainLine];
    const forkA: NodeId = mainLine[0]!;
    const forkB: NodeId = mainLine[1]!;

    act(() => {
      result.current.insertPvLine(['Nf6', 'Bc4'], forkA); // ids 3, 4
    });
    act(() => {
      result.current.insertPvLine(['Bb5'], forkB); // id 5
    });
    act(() => {
      result.current.goToNode(4);
    });

    act(() => {
      result.current.clearAllSidelines();
    });

    // Only mainLine nodes remain.
    expect(result.current.nodes.size).toBe(mainLine.length);
    for (const id of mainLine) expect(result.current.nodes.has(id)).toBe(true);
    expect(result.current.nodes.has(3)).toBe(false);
    expect(result.current.nodes.has(4)).toBe(false);
    expect(result.current.nodes.has(5)).toBe(false);

    // pvNodeIds is empty — no line reads as open.
    expect(result.current.isOnPvLine(3)).toBe(false);
    expect(result.current.isOnPvLine(5)).toBe(false);

    // currentNodeId recovered to the nearest mainLine ancestor of node 4 (forkA).
    expect(result.current.currentNodeId).toBe(forkA);
    expect(result.current.isOnMainLine(result.current.currentNodeId!)).toBe(true);
  });

  // ── Quick 260703-kyb Behavior 9: makeMove off a PV node is a free-move sub-fork ──

  it('makeMove from a PV node creates a node NOT in pvNodeIds (free-move sub-fork, deletable independently)', () => {
    const { result } = renderHook(() => useAnalysisBoard(ROOT_FEN));

    act(() => {
      result.current.loadMainLine(MAIN_LINE_SANS, ROOT_FEN);
    });
    const forkNodeId: NodeId = result.current.mainLine[0]!;

    // Insert a PV: Nf6 from forkNodeId (after Nf3, black to move)
    act(() => {
      result.current.insertPvLine(['Nf6'], forkNodeId); // id 3
    });
    const pvNodeId = 3;

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

    // The new node is NOT in pvNodeIds — it's a free-move sub-fork, not part of the tactic line.
    expect(result.current.isOnPvLine(newNodeId!)).toBe(false);
    // The original PV node is unchanged.
    expect(result.current.isOnPvLine(pvNodeId)).toBe(true);
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
