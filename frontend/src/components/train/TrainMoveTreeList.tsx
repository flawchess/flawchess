/**
 * TrainMoveTreeList — the reveal's single move list (Phase 237, D-03).
 *
 * Renders the active chip's pre-loaded line (plus the user's own sidelines) from
 * `useTrainRevealTree`'s list view through `VariationTree` in its `'wrap'`
 * variant: numbered tokens that wrap at every width, inline sidelines and a
 * delete x per free sideline. A tap on a token moves the tree to that node.
 *
 * Plan 06: off the known lines (on a sideline of the user's own) a one-line
 * Stockfish row sits above the list (D-03) with as many lines as the Stockfish
 * lines setting, laid out like the analysis board's (Phase 237 UAT): each line is
 * collapsed behind its own chevron, expanding by wrapping on desktop and by
 * scrolling sideways on mobile. A click on a move in it plays that engine line
 * into the sideline. On the known lines the row is absent.
 */

import type { ReactElement } from 'react';

import { EngineLines, EngineLinesSkeleton } from '@/components/analysis/EngineLines';
import { VariationTree } from '@/components/analysis/VariationTree';
import { useIsDesktop } from '@/hooks/useIsDesktop';
import type { TrainRevealTree } from '@/hooks/useTrainRevealTree';
import { useEngineDisplaySettings } from '@/lib/engineSettings';

/**
 * Height of the reveal move list: two wrapped token rows on mobile, four on desktop
 * (lg), without scrolling. A row is 24px (text-sm 20px line + py-0.5) with a 2px
 * gap-y; the box adds 16px padding + 2px border (Phase 237 UAT: h-16 scrolled at
 * two rows).
 */
export const TRAIN_MOVE_TREE_HEIGHT_CLASS = 'h-17 lg:h-30';

interface TrainMoveTreeListProps {
  tree: TrainRevealTree;
  /** Board orientation, so the Stockfish row's hover-preview miniboards match. */
  flipped: boolean;
  /** The brand ring marking the list as the focused surface. */
  ring?: boolean;
}

/** The off-line Stockfish row: the lines setting, compact (sideways scroll) on mobile. */
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
          isAnalyzing={tree.isAnalyzing}
          baseFen={tree.fen}
          flipped={flipped}
          onMoveClick={tree.playLine}
          compact={!isDesktop}
        />
      )}
    </div>
  );
}

export function TrainMoveTreeList({
  tree,
  flipped,
  ring = false,
}: TrainMoveTreeListProps): ReactElement {
  // The Stockfish row is a SIBLING of the list's testid wrapper, so queries that
  // read the list's move tokens never pick up the engine line's moves.
  return (
    <div className="flex flex-col gap-1">
      {tree.isOffLine && <TrainStockfishRow tree={tree} flipped={flipped} />}
      <div
        data-testid="train-move-tree"
        className={ring ? 'rounded-md ring-2 ring-brand-brown' : undefined}
      >
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
        />
      </div>
    </div>
  );
}
