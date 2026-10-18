import { ScoreVerdictPopover } from '@/components/openings/stats/VerdictPopover';
import {
  formatScorePercent,
  openingVerdict,
  openingVerdictReason,
  verdictValueColor,
  type OpeningVerdictInput,
} from '@/lib/openingVerdict';
import { cn } from '@/lib/utils';

interface ScoreLineProps {
  score: number;
  games: number;
  wins: number;
  draws: number;
  losses: number;
  /** The score verdict input; colours the percentage only when the verdict is better or worse. */
  input: OpeningVerdictInput;
  ci99Low: number | null;
  ci99High: number | null;
  pValue: number | null;
  /** Prefix of the testids: `${testId}-score` (the value) and `${testId}-score-info` (the popover). */
  testId: string;
}

/**
 * The Score label left, the percentage and its popover right: the words row above the WDL bar
 * on the finding and repertoire cards. The score has no bar of its own, the WDL bar shows it.
 */
export function ScoreLine({
  score,
  games,
  wins,
  draws,
  losses,
  input,
  ci99Low,
  ci99High,
  pValue,
  testId,
}: ScoreLineProps) {
  const verdict = openingVerdict(input);
  const valueColor = verdictValueColor(verdict);
  // Same words row as the VerdictBar: muted label left, value and popover right.
  return (
    <div className="flex items-center justify-between gap-2 text-sm">
      <span className="min-w-0 text-muted-foreground">Score</span>
      <div className="flex shrink-0 items-center gap-1">
        <span
          className={cn('whitespace-nowrap font-semibold tabular-nums', !valueColor && 'text-foreground')}
          style={valueColor ? { color: valueColor } : undefined}
          data-testid={`${testId}-score`}
          data-verdict={verdict}
        >
          {formatScorePercent(score)}
        </span>
        <ScoreVerdictPopover
          testId={`${testId}-score-info`}
          score={score}
          games={games}
          wins={wins}
          draws={draws}
          losses={losses}
          reason={openingVerdictReason(input)}
          ci99Low={ci99Low}
          ci99High={ci99High}
          pValue={pValue}
        />
      </div>
    </div>
  );
}
