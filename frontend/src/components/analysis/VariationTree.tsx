/**
 * VariationTree — responsive move list for the analysis board (Phase 137 Plan 03).
 *
 * Renders the flat main line plus the single active variation (BOARD-05).
 * Responsive split (D-02): mobile extends HorizontalMoveList (horizontal chips
 * with variation inline in parentheses); desktop uses a new vertical paired
 * N. white black list with the active variation as an indented sub-section.
 * Split is Tailwind dual-DOM (sm:hidden / hidden sm:block) — no media-query hook.
 */

import { useRef, useEffect, Fragment } from 'react';
import type { ReactNode } from 'react';
import type { NodeId, MoveNode } from '@/hooks/useAnalysisBoard';
import { HorizontalMoveList } from '@/components/board/HorizontalMoveList';
import type { HorizontalMoveItem } from '@/components/board/HorizontalMoveList';
import { moveLabel } from '@/lib/moveNumberLabel';
import { cn } from '@/lib/utils';

// ─── Props ───────────────────────────────────────────────────────────────────

export interface VariationTreeProps {
  nodes: Map<NodeId, MoveNode>;
  mainLine: NodeId[];
  currentNodeId: NodeId | null;
  /** Game ply of rootFen, for move-number labels. Default 0. */
  rootPly?: number;
  /** Called with the node id when a move chip is clicked. Wired to goToNode in Phase 138. */
  onNodeClick: (nodeId: NodeId) => void;
  /** Height override passed to the mobile HorizontalMoveList. */
  heightClass?: string;
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

interface VariationChain {
  forkParentId: NodeId | null;
  chain: NodeId[];
}

/**
 * Walk from currentNodeId up through parentId pointers to the nearest
 * mainLine ancestor. Returns the chain in fork-to-current order.
 * Returns an empty chain when currentNodeId is null or already on the main line.
 */
function buildVariationChain(
  nodes: Map<NodeId, MoveNode>,
  mainLine: NodeId[],
  currentNodeId: NodeId | null,
): VariationChain {
  if (currentNodeId === null) return { forkParentId: null, chain: [] };
  const mainLineSet = new Set(mainLine);
  if (mainLineSet.has(currentNodeId)) return { forkParentId: null, chain: [] };

  const reversed: NodeId[] = [];
  let id: NodeId | null = currentNodeId;
  while (id !== null && !mainLineSet.has(id)) {
    reversed.push(id);
    const node = nodes.get(id);
    id = node?.parentId ?? null;
  }
  return { forkParentId: id, chain: reversed.reverse() };
}

// ─── Desktop row types and builders ──────────────────────────────────────────

interface DesktopRow {
  moveNumber: number;
  whiteNodeId: NodeId | undefined;
  blackNodeId: NodeId | undefined;
}

function buildDesktopRows(mainLine: NodeId[], rootPly: number): DesktopRow[] {
  const rows: DesktopRow[] = [];
  let idx = 0;

  // When rootPly is odd (black to move at root), first row has only a black cell.
  if (rootPly % 2 !== 0 && mainLine.length > 0) {
    rows.push({
      moveNumber: Math.ceil((rootPly + 1) / 2),
      whiteNodeId: undefined,
      blackNodeId: mainLine[0]!, // safe: length > 0 checked above
    });
    idx = 1;
  }

  while (idx < mainLine.length) {
    const ply = rootPly + idx;
    rows.push({
      moveNumber: Math.ceil((ply + 1) / 2),
      whiteNodeId: mainLine[idx]!, // safe: idx < length (loop invariant)
      blackNodeId: idx + 1 < mainLine.length ? mainLine[idx + 1]! : undefined,
    });
    idx += 2;
  }

  return rows;
}

function buildVariationRows(
  chain: NodeId[],
  forkIdx: number,
  rootPly: number,
): DesktopRow[] {
  const rows: DesktopRow[] = [];
  const startPly = rootPly + forkIdx + 1; // ply of the first variation move
  let idx = 0;

  // When the first variation move is black's turn, open with a black-only row.
  if (startPly % 2 !== 0 && chain.length > 0) {
    rows.push({
      moveNumber: Math.ceil((startPly + 1) / 2),
      whiteNodeId: undefined,
      blackNodeId: chain[0]!, // safe: length > 0 checked above
    });
    idx = 1;
  }

  while (idx < chain.length) {
    const ply = startPly + idx;
    rows.push({
      moveNumber: Math.ceil((ply + 1) / 2),
      whiteNodeId: chain[idx]!, // safe: idx < length (loop invariant)
      blackNodeId: idx + 1 < chain.length ? chain[idx + 1]! : undefined,
    });
    idx += 2;
  }

  return rows;
}

// ─── Mobile sub-component ────────────────────────────────────────────────────

function MobileTree({
  nodes,
  mainLine,
  currentNodeId,
  rootPly,
  onNodeClick,
  heightClass,
}: VariationTreeProps) {
  const rootPlyVal = rootPly ?? 0;
  const { forkParentId, chain } = buildVariationChain(nodes, mainLine, currentNodeId);
  const forkIdx = forkParentId !== null ? mainLine.indexOf(forkParentId) : -1;

  // Map main-line nodes to chip items.
  const mainItems = mainLine.map((nodeId, idx): HorizontalMoveItem | null => {
    const node = nodes.get(nodeId);
    if (!node) return null;
    const plyOffset = rootPlyVal + idx;
    const isWhite = plyOffset % 2 === 0;
    const label = isWhite ? moveLabel(rootPlyVal, idx) : null;
    const isFork = idx === forkIdx;
    const isAfterFork = forkIdx >= 0 && idx > forkIdx;

    return {
      key: nodeId,
      ply: nodeId, // HorizontalMoveList calls onMoveClick(ply) → onNodeClick(nodeId)
      numberLabel: label,
      san: node.san,
      isCurrent: nodeId === currentNodeId,
      dimmed: isAfterFork,
      testId: `variation-node-${nodeId}`,
      ariaLabel: `Move ${label ?? ''} ${node.san}`.trim(),
      // Opening paren as trailing inside the fork button (v1 simplification).
      trailing:
        isFork && chain.length > 0 ? (
          <span className="text-muted-foreground select-none ml-0.5">(</span>
        ) : undefined,
    };
  });

  // Map variation-chain nodes to chip items.
  const varItems = chain.map((nodeId, varIdx): HorizontalMoveItem | null => {
    const node = nodes.get(nodeId);
    if (!node) return null;
    const varPlyIdx = (forkIdx >= 0 ? forkIdx + 1 : 0) + varIdx;
    const plyOffset = rootPlyVal + varPlyIdx;
    const isWhite = plyOffset % 2 === 0;
    const label = isWhite ? moveLabel(rootPlyVal, varPlyIdx) : null;
    const isLast = varIdx === chain.length - 1;

    return {
      key: nodeId,
      ply: nodeId,
      numberLabel: label,
      san: node.san,
      isCurrent: nodeId === currentNodeId,
      testId: `variation-node-${nodeId}`,
      ariaLabel: `Move ${label ?? ''} ${node.san}`.trim(),
      // Closing paren inside the last variation chip button.
      trailing: isLast ? (
        <span className="text-muted-foreground select-none">)</span>
      ) : undefined,
    };
  });

  const filteredMain = mainItems.filter((i): i is HorizontalMoveItem => i !== null);
  const filteredVar = varItems.filter((i): i is HorizontalMoveItem => i !== null);

  // Insert variation items between the fork node and the rest of the main line.
  const finalItems: HorizontalMoveItem[] =
    forkIdx >= 0
      ? [
          ...filteredMain.slice(0, forkIdx + 1),
          ...filteredVar,
          ...filteredMain.slice(forkIdx + 1),
        ]
      : filteredMain;

  return (
    <HorizontalMoveList
      items={finalItems}
      onMoveClick={(ply) => onNodeClick(ply)}
      heightClass={heightClass ?? 'h-20 sm:h-20'}
      emptyText="No moves yet"
      testId="variation-tree-mobile"
    />
  );
}

// ─── Desktop sub-component ───────────────────────────────────────────────────

function DesktopTree({
  nodes,
  mainLine,
  currentNodeId,
  rootPly,
  onNodeClick,
}: VariationTreeProps) {
  const activeRef = useRef<HTMLButtonElement | null>(null);
  const rootPlyVal = rootPly ?? 0;

  // Scroll the active node into view whenever currentNodeId changes.
  useEffect(() => {
    activeRef.current?.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
  }, [currentNodeId]);

  const { forkParentId, chain } = buildVariationChain(nodes, mainLine, currentNodeId);
  const forkIdx = forkParentId !== null ? mainLine.indexOf(forkParentId) : -1;

  if (mainLine.length === 0 && nodes.size === 0) {
    return (
      <div
        data-testid="variation-tree-desktop"
        aria-label="Move list"
        role="navigation"
        className="overflow-y-auto"
      >
        <p className="text-sm text-muted-foreground p-2">No moves yet</p>
      </div>
    );
  }

  const mainRows = buildDesktopRows(mainLine, rootPlyVal);
  const varRows =
    chain.length > 0 && forkIdx >= 0
      ? buildVariationRows(chain, forkIdx, rootPlyVal)
      : [];

  const forkRowIdx =
    forkIdx >= 0
      ? mainRows.findIndex(
          (r) => r.whiteNodeId === forkParentId || r.blackNodeId === forkParentId,
        )
      : -1;

  const renderMoveButton = (nodeId: NodeId, label: string, isVariation: boolean): ReactNode => {
    const node = nodes.get(nodeId);
    if (!node) return null;
    const isCurrent = nodeId === currentNodeId;
    return (
      <button
        ref={isCurrent ? activeRef : undefined}
        data-testid={`variation-node-${nodeId}`}
        aria-label={`Move ${label} ${node.san}`}
        aria-current={isCurrent ? 'step' : undefined}
        onClick={() => onNodeClick(nodeId)}
        className={cn(
          'text-sm font-mono px-1 py-0.5 rounded transition-colors hover:bg-accent',
          isCurrent && 'bg-primary text-primary-foreground hover:bg-primary/90',
          !isCurrent && isVariation && 'text-muted-foreground',
        )}
      >
        {node.san}
      </button>
    );
  };

  const renderDesktopRow = (row: DesktopRow, isVariation: boolean): ReactNode => {
    const whiteLabel = `${row.moveNumber}.`;
    const blackLabel = `${row.moveNumber}...`;
    return (
      <div className="flex items-center min-h-[28px]">
        <span className="w-8 shrink-0 text-sm text-muted-foreground select-none">
          {row.moveNumber}.
        </span>
        <div className="flex-1 min-w-0">
          {row.whiteNodeId !== undefined &&
            renderMoveButton(row.whiteNodeId, whiteLabel, isVariation)}
        </div>
        <div className="flex-1 min-w-0">
          {row.blackNodeId !== undefined &&
            renderMoveButton(row.blackNodeId, blackLabel, isVariation)}
        </div>
      </div>
    );
  };

  return (
    <div
      data-testid="variation-tree-desktop"
      aria-label="Move list"
      role="navigation"
      className="overflow-y-auto"
    >
      {mainRows.map((row, rowIdx) => (
        <Fragment key={rowIdx}>
          {renderDesktopRow(row, false)}
          {rowIdx === forkRowIdx && varRows.length > 0 && (
            <div className="ml-8">
              {varRows.map((vRow, vIdx) => (
                <Fragment key={vIdx}>{renderDesktopRow(vRow, true)}</Fragment>
              ))}
            </div>
          )}
        </Fragment>
      ))}
    </div>
  );
}

// ─── Main export ─────────────────────────────────────────────────────────────

/**
 * VariationTree — navigable move list showing the main line + single active
 * variation. Click any node to call onNodeClick(nodeId) (→ goToNode in Phase 138).
 *
 * Security: node.san comes from chess.js-validated moves, not user input.
 * React auto-escapes all JSX children — no unsafe HTML injection.
 */
export function VariationTree(props: VariationTreeProps) {
  return (
    <div data-testid="analysis-variation-tree" aria-label="Move list" role="navigation">
      {/* Mobile path — HorizontalMoveList with variation inline in parentheses */}
      <div className="sm:hidden">
        <MobileTree {...props} />
      </div>
      {/* Desktop path — vertical paired N. white black list with indented variation */}
      <div className="hidden sm:block">
        <DesktopTree {...props} />
      </div>
    </div>
  );
}
