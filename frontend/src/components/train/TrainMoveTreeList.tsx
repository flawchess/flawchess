/**
 * TrainMoveTreeList — the reveal's single move list.
 *
 * Renders the active chip's first move, the user's committed continuation and
 * sidelines from `useTrainRevealTree`'s list view through `VariationTree` in its
 * `'wrap'` variant: numbered tokens that wrap at every width, inline sidelines and
 * a delete x per free sideline. A tap on a token moves the tree to that node.
 *
 * At a leaf the list ends in a dimmed engine preview (at most six
 * plies, no eval). A tap on preview token i commits i + 1 plies as real nodes.
 * The Stockfish row sits below the list on every node except the puzzle
 * position, with as many lines as the Stockfish lines setting (each line
 * collapsed behind its own chevron). It always shows lines 1..N, so the top
 * line's live eval reads there, like the analysis board (a live eval pill
 * inside the move list would be confusing). A click on a move in it plays that
 * engine line into the tree.
 */

import type { ReactElement } from 'react';

import { EngineLines, EngineLinesSkeleton } from '@/components/analysis/EngineLines';
import { VariationTree } from '@/components/analysis/VariationTree';
import type { VariationTreePreview } from '@/components/analysis/VariationTree';
import { useIsDesktop } from '@/hooks/useIsDesktop';
import { fenToPly } from '@/hooks/useTrainRevealTree';
import type { TrainRevealTree } from '@/hooks/useTrainRevealTree';
import { useEngineDisplaySettings } from '@/lib/engineSettings';

/**
 * Height of the reveal move list: two wrapped token rows on mobile, four on
 * desktop (lg), without scrolling. A row is 24px (text-sm 20px line + py-0.5)
 * with a 2px gap-y; the box adds 16px padding + 2px border (h-16 scrolls at
 * two rows). Mobile adds a little air under the second row (h-19, still on the
 * 4px grid).
 */
export const TRAIN_MOVE_TREE_HEIGHT_CLASS = 'h-19 lg:h-30';

interface TrainMoveTreeListProps {
  tree: TrainRevealTree;
  /** Board orientation, so the Stockfish row's hover-preview miniboards match. */
  flipped: boolean;
}

/** The Stockfish row: the lines setting, compact (sideways scroll) on mobile.
 * Shown on every node except the puzzle position. At the puzzle
 * position the chips are the server's graded answer key, and a short live ranking
 * there would read as contradicting it. */
function TrainStockfishRow({
  tree,
  flipped,
}: {
  tree: TrainRevealTree;
  flipped: boolean;
}): ReactElement {
  const isDesktop = useIsDesktop();
  const { sfLines } = useEngineDisplaySettings();
  return (
    <div data-testid="train-sf-row">
      {tree.pvLines.length === 0 ? (
        <EngineLinesSkeleton rows={sfLines} compact={!isDesktop} />
      ) : (
        <EngineLines
          pvLines={tree.pvLines}
          maxLines={sfLines}
          isAnalyzing={false}
          // Without it the row numbers every line from "1."
          startPly={fenToPly(tree.fen)}
          baseFen={tree.fen}
          flipped={flipped}
          onMoveClick={tree.playLine}
          compact={!isDesktop}
        />
      )}
    </div>
  );
}

/** The tree's preview as VariationTree's render model, or undefined without one. */
function toVariationPreview(tree: TrainRevealTree): VariationTreePreview | undefined {
  const preview = tree.preview;
  if (preview === null || preview.steps.length === 0) return undefined;
  return {
    anchorId: preview.anchorId,
    sans: preview.steps.map((step) => step.san),
    // Token i commits i + 1 plies (at the puzzle position the chip move is played first).
    onTokenClick: (index) => tree.commitPreview(index + 1),
  };
}

export function TrainMoveTreeList({
  tree,
  flipped,
}: TrainMoveTreeListProps): ReactElement {
  // The Stockfish row is a SIBLING of the list's testid wrapper, so queries that
  // read the list's move tokens never pick up the engine line's moves. It sits
  // BELOW the list, so the list keeps its place when the row appears or
  // leaves.
  return (
    <div className="flex flex-col gap-1">
      <div data-testid="train-move-tree">
        <VariationTree
          variant="wrap"
          nodes={tree.listView.nodes}
          mainLine={tree.listView.mainLine}
          currentNodeId={tree.currentNodeId}
          rootPly={tree.rootPly}
          onNodeClick={tree.goToNode}
          onDeleteLine={tree.deleteLine}
          flawMarkerByNodeId={tree.moveListMarkers}
          heightClass={TRAIN_MOVE_TREE_HEIGHT_CLASS}
          preview={toVariationPreview(tree)}
        />
      </div>
      {!tree.isAtRoot && <TrainStockfishRow tree={tree} flipped={flipped} />}
    </div>
  );
}
