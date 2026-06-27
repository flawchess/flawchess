// @vitest-environment jsdom
/**
 * useAnalysisBoard hook tests (Phase 137, Plan 01).
 *
 * Required D-05 behaviors:
 * 1. Mid-line fork: a move at a mid-line node creates a child node; mainLine is NOT truncated.
 * 2. Navigation: goBack / goForward / goToNode move currentNodeId and position correctly.
 * 3. O(1) goToNode: position equals the stored FEN, not a root-replay artifact.
 * 4. loadMainLine + isOnMainLine: seeds mainLine IDs in order; true for seeded, false for forked.
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
});
