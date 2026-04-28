import { ArrowRightLeft, Swords } from 'lucide-react';
import { LazyMiniBoard } from '@/components/board/LazyMiniBoard';
import { Tooltip } from '@/components/ui/tooltip';
import {
  formatCandidateMove,
  formatConfidenceTooltip,
  getSeverityBorderColor,
} from '@/lib/openingInsights';
import { MIN_GAMES_FOR_RELIABLE_STATS, UNRELIABLE_OPACITY } from '@/lib/theme';
import type { OpeningInsightFinding } from '@/types/insights';

interface OpeningFindingCardProps {
  finding: OpeningInsightFinding;
  idx: number;
  onFindingClick: (finding: OpeningInsightFinding) => void;
  onOpenGames: (finding: OpeningInsightFinding) => void;
}

const MOBILE_BOARD_SIZE = 105;
const DESKTOP_BOARD_SIZE = 100;
const UNNAMED_SENTINEL = '<unnamed line>';

export function OpeningFindingCard({
  finding,
  idx,
  onFindingClick,
  onOpenGames,
}: OpeningFindingCardProps) {
  const colorLabel = finding.color === 'white' ? 'White' : 'Black';
  const candidateMoveDisplay = formatCandidateMove(
    finding.entry_san_sequence,
    finding.candidate_move_san,
  );
  const borderLeftColor = getSeverityBorderColor(
    finding.classification,
    finding.severity,
  );
  const isUnnamed = finding.opening_name === UNNAMED_SENTINEL;

  // D-02: Score-based prose (replaces broken loss_rate/win_rate reads removed in Phase 75).
  // Edge case: if rounding to integer would show 50% but classification implies otherwise,
  // fall back to one decimal place to avoid contradicting the section title.
  const rawPercent = finding.score * 100;
  const wouldContradict =
    (finding.classification === 'weakness' && Math.round(rawPercent) >= 50) ||
    (finding.classification === 'strength' && Math.round(rawPercent) <= 50);
  const scoreDisplay = wouldContradict ? rawPercent.toFixed(1) : Math.round(rawPercent).toString();

  // D-11: Apply UNRELIABLE_OPACITY when n_games < 10 OR confidence is low.
  const isUnreliable =
    finding.n_games < MIN_GAMES_FOR_RELIABLE_STATS || finding.confidence === 'low';
  const cardStyle: React.CSSProperties = {
    borderLeftColor,
    ...(isUnreliable ? { opacity: UNRELIABLE_OPACITY } : {}),
  };

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
    </div>
  );

  // D-02: "You score X% as <Color> after <seq>" — same form for both weakness and strength.
  // Section title carries the polarity; the border tint via getSeverityBorderColor conveys direction visually.
  const proseLine = (
    <p className="text-sm text-muted-foreground">
      You score{' '}
      <span style={{ color: borderLeftColor }} className="font-semibold">
        {scoreDisplay}%
      </span>{' '}
      as {colorLabel} after{' '}
      <span className="font-mono text-foreground">{candidateMoveDisplay}</span>
    </p>
  );

  // "Confidence: low/medium/high" line — tooltip on hover over the level word
  // matches the Moves/Games link pattern (hover-only, no tap-friendly trigger).
  const confidenceLine = (
    <p
      className="text-sm text-muted-foreground flex items-center gap-1"
      data-testid={`opening-finding-card-${idx}-confidence`}
    >
      Confidence:{' '}
      <Tooltip content={formatConfidenceTooltip(finding.confidence, finding.p_value, finding.score)}>
        <span className="font-medium" data-testid={`opening-finding-card-${idx}-confidence-info`}>
          {finding.confidence}
        </span>
      </Tooltip>
    </p>
  );

  const linksRow = (
    <div className="flex items-center gap-4">
      <Tooltip content={`Open ${finding.display_name} in the Move Explorer`}>
        <button
          type="button"
          className="flex items-center gap-1 text-sm text-brand-brown-light hover:text-brand-brown-highlight transition-colors"
          aria-label={`Open ${finding.display_name} in the Move Explorer`}
          data-testid={`opening-finding-card-${idx}-moves`}
          onClick={() => onFindingClick(finding)}
        >
          <ArrowRightLeft className="h-3.5 w-3.5" />
          <span>Moves</span>
        </button>
      </Tooltip>
      <Tooltip content={`View ${finding.n_games} games for ${finding.opening_name}`}>
        <button
          type="button"
          className="flex items-center gap-1 text-sm text-brand-brown-light hover:text-brand-brown-highlight transition-colors"
          aria-label={`View ${finding.n_games} games for ${finding.opening_name}`}
          data-testid={`opening-finding-card-${idx}-games`}
          onClick={() => onOpenGames(finding)}
        >
          <Swords className="h-3.5 w-3.5" />
          <span className="tabular-nums">{finding.n_games}</span>
          <span>Games</span>
        </button>
      </Tooltip>
    </div>
  );

  return (
    <div
      data-testid={`opening-finding-card-${idx}`}
      className="block border-l-4 charcoal-texture border border-border/20 rounded px-4 py-3"
      style={cardStyle}
    >
      {/* Mobile: header full-width on top, board + prose/links row below */}
      <div className="flex flex-col gap-2 sm:hidden">
        {headerLine}
        <div className="flex gap-3 items-start">
          <LazyMiniBoard
            fen={finding.entry_fen}
            flipped={finding.color === 'black'}
            size={MOBILE_BOARD_SIZE}
          />
          <div className="flex-1 min-w-0 flex flex-col gap-2">
            {proseLine}
            {confidenceLine}
            {linksRow}
          </div>
        </div>
      </div>

      {/* Desktop: board left, header + prose + links stacked right */}
      <div className="hidden sm:flex gap-3 items-center">
        <LazyMiniBoard
          fen={finding.entry_fen}
          flipped={finding.color === 'black'}
          size={DESKTOP_BOARD_SIZE}
        />
        <div className="min-w-0 flex-1 flex flex-col gap-2">
          {headerLine}
          {proseLine}
          {confidenceLine}
          {linksRow}
        </div>
      </div>
    </div>
  );
}
