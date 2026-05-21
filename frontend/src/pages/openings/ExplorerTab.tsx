import type { ReactNode } from 'react';
import type { UseQueryResult } from '@tanstack/react-query';
import { MoveExplorer } from '@/components/move-explorer/MoveExplorer';
import { PositionResultsPanel } from '@/components/charts/PositionResultsPanel';
import { EvalCoverageHeader } from '@/components/EvalCoverageHeader';
import type { Color, NextMovesResponse, OpeningsResponse } from '@/types/api';
import type { HighlightedMove } from './useDeepLinkHighlight';

type ExplorerTabProps = {
  gamesData: OpeningsResponse | undefined;
  filterColor: Color;
  positionResultsLabel: ReactNode;
  nextMoves: UseQueryResult<NextMovesResponse>;
  position: string;
  onMoveClick: (from: string, to: string) => boolean;
  onMoveHover: (san: string | null) => void;
  highlightedMove: HighlightedMove | null;
  pulseActive: boolean;
  onHighlightConsumed: () => void;
};

export function ExplorerTab({
  gamesData,
  filterColor,
  positionResultsLabel,
  nextMoves,
  position,
  onMoveClick,
  onMoveHover,
  highlightedMove,
  pulseActive,
  onHighlightConsumed,
}: ExplorerTabProps) {
  return (
    <div className="flex flex-col gap-4">
      <EvalCoverageHeader />
      {gamesData && (
        <PositionResultsPanel
          stats={gamesData.stats}
          evalBaselinePawns={gamesData.eval_baseline_pawns}
          filterColor={filterColor}
          label={positionResultsLabel}
          gamesHref="/openings/games"
          className="order-2 lg:order-1"
        />
      )}
      <div className="charcoal-texture rounded-md p-4 order-1 lg:order-2">
        <MoveExplorer
          moves={nextMoves.data?.moves ?? []}
          isLoading={nextMoves.isLoading}
          isError={nextMoves.isError}
          position={position}
          onMoveClick={onMoveClick}
          onMoveHover={onMoveHover}
          highlightedMove={
            highlightedMove !== null
              ? { ...highlightedMove, pulse: pulseActive }
              : null
          }
          onHighlightConsumed={onHighlightConsumed}
        />
      </div>
    </div>
  );
}
