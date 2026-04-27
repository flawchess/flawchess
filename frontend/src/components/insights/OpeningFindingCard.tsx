import { ExternalLink } from 'lucide-react';
import { LazyMiniBoard } from '@/components/board/LazyMiniBoard';
import { getSeverityBorderColor, trimMoveSequence } from '@/lib/openingInsights';
import type { OpeningInsightFinding } from '@/types/insights';

interface OpeningFindingCardProps {
  finding: OpeningInsightFinding;
  idx: number;
  onFindingClick: (finding: OpeningInsightFinding) => void;
}

const MOBILE_BOARD_SIZE = 105;
const DESKTOP_BOARD_SIZE = 100;
const UNNAMED_SENTINEL = '<unnamed line>';

export function OpeningFindingCard({ finding, idx, onFindingClick }: OpeningFindingCardProps) {
  const isWeakness = finding.classification === 'weakness';
  const ratePercent = Math.round(
    (isWeakness ? finding.loss_rate : finding.win_rate) * 100,
  );
  const colorLabel = finding.color === 'white' ? 'White' : 'Black';
  const verb = isWeakness ? 'lose' : 'win';
  const trimmedSequence = trimMoveSequence(
    finding.entry_san_sequence,
    finding.candidate_move_san,
  );
  const borderLeftColor = getSeverityBorderColor(
    finding.classification,
    finding.severity,
  );
  const isUnnamed = finding.opening_name === UNNAMED_SENTINEL;

  const headerLine = (
    <div className="flex items-center gap-2 text-sm min-w-0">
      <span className="truncate text-foreground font-medium min-w-0">
        {isUnnamed ? (
          <span className="italic text-muted-foreground">{finding.display_name}</span>
        ) : (
          finding.display_name
        )}
        {finding.opening_eco && (
          <span className="ml-1 text-muted-foreground">({finding.opening_eco})</span>
        )}
      </span>
      <span
        className="ml-auto shrink-0 text-muted-foreground"
        aria-hidden="true"
      >
        <ExternalLink className="h-4 w-4" />
      </span>
    </div>
  );

  const proseLine = (
    <p className="text-sm text-muted-foreground">
      You {verb}{' '}
      <span style={{ color: borderLeftColor }} className="font-semibold">
        {ratePercent}%
      </span>{' '}
      as {colorLabel} after{' '}
      <span className="font-mono text-foreground">{trimmedSequence}</span>{' '}
      <span className="text-muted-foreground">(n={finding.n_games})</span>
    </p>
  );

  return (
    <a
      href="/openings/explorer"
      data-testid={`opening-finding-card-${idx}`}
      aria-label={`Open ${finding.display_name} (${finding.candidate_move_san}) in Move Explorer`}
      onClick={(e) => {
        e.preventDefault();
        onFindingClick(finding);
      }}
      className="block border-l-4 charcoal-texture border border-border/20 rounded px-4 py-3 cursor-pointer hover:bg-muted/30 transition-colors"
      style={{ borderLeftColor }}
    >
      {/* Mobile: header full-width on top, board + prose row below */}
      <div className="flex flex-col gap-2 sm:hidden">
        {headerLine}
        <div className="flex gap-3 items-start">
          <LazyMiniBoard
            fen={finding.entry_fen}
            flipped={finding.color === 'black'}
            size={MOBILE_BOARD_SIZE}
          />
          <div className="flex-1 min-w-0 flex flex-col gap-1">{proseLine}</div>
        </div>
      </div>

      {/* Desktop: board left, header + prose stacked right */}
      <div className="hidden sm:flex gap-3 items-center">
        <LazyMiniBoard
          fen={finding.entry_fen}
          flipped={finding.color === 'black'}
          size={DESKTOP_BOARD_SIZE}
        />
        <div className="min-w-0 flex-1 flex flex-col gap-2">
          {headerLine}
          {proseLine}
        </div>
      </div>
    </a>
  );
}
