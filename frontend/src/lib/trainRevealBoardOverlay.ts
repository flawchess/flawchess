/**
 * trainRevealBoardOverlay: what a reveal board draws below its root position, shared by the
 * personalized-puzzle reveal (TrainSolveScreen) and the blunder-check solution so a stepped
 * line looks the same on both (engine arrows plus move-quality badges).
 */

import type { BoardArrow, SquareMarker } from '@/components/board/ChessBoard';
import type { PvLine } from '@/hooks/uciParser';
import type { TrainRevealTree } from '@/hooks/useTrainRevealTree';
import { mergeEngineBadges } from '@/lib/engineArrowGrades';
import { TRAIN_STEP_HIGHLIGHT, buildTrainStepMarkers, buildTrainStepOverlay } from '@/lib/trainArrows';
import type { TrainEngineOverlay } from '@/lib/trainArrows';
import type { ChipGroup } from '@/lib/trainRevealLines';

/** The four board props the reveal overlay decides (arrows, badges, last-move
 * square and its highlight color). */
export interface RevealBoardOverlay {
  arrows: BoardArrow[];
  markers: SquareMarker[];
  lastMove: { from: string; to: string } | null;
  lastMoveColor: string | undefined;
}

/** The slice of the reveal tree the board overlay reads. */
export type RevealOverlayTree = Pick<
  TrainRevealTree,
  | 'isAtRoot'
  | 'currentNodeId'
  | 'chipMove'
  | 'preview'
  | 'activeChip'
  | 'lastMove'
  | 'boardMarkers'
  | 'lastMoveColor'
  | 'fen'
>;

/**
 * The reveal board below the root position: the preview step board (the primary pointer is
 * what the forward button commits) or the free-play engine overlay, plus the chip's
 * first-move badge or the tree's own markers, with the engine badges merged underneath.
 */
export function resolveOffRootOverlay(
  offLineOverlay: TrainEngineOverlay,
  liveLines: readonly PvLine[],
  liveArrowCount: number,
  tree: RevealOverlayTree,
  chips: readonly Pick<ChipGroup, 'key' | 'quality'>[],
): RevealBoardOverlay {
  const preview = tree.preview;
  const previewNext =
    preview !== null && preview.anchorId === tree.currentNodeId
      ? (preview.steps[0]?.uci ?? null)
      : null;
  const engine =
    previewNext !== null
      ? buildTrainStepOverlay(previewNext, liveLines, liveArrowCount, tree.fen)
      : offLineOverlay;
  const chipMove = tree.chipMove;
  if (chipMove === null) {
    return {
      arrows: engine.arrows,
      markers: mergeEngineBadges(tree.boardMarkers, engine.badges),
      lastMove: tree.lastMove,
      lastMoveColor: tree.lastMoveColor,
    };
  }
  // A chip's first move carries its chip's quality.
  const quality = chips.find((chip) => chip.key === chipMove.line)?.quality ?? null;
  return {
    arrows: engine.arrows,
    markers: mergeEngineBadges(buildTrainStepMarkers(chipMove.uci, quality, true), engine.badges),
    lastMove: tree.lastMove,
    lastMoveColor: quality !== null ? TRAIN_STEP_HIGHLIGHT[quality] : undefined,
  };
}
