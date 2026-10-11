import { MiniWDLBar } from '@/components/stats/MiniWDLBar';
import { METRIC_BRACKET_COLOR, METRIC_BRACKET_DIM_OVERLAY } from '@/lib/theme';

export interface WdlShares {
  /** Percent of games, 0-100. */
  win: number;
  draw: number;
  loss: number;
}

interface BracketedWdlBarProps {
  shares: WdlShares;
  /** How much of the bar the big number counts, in percent of the bar width. */
  covered: number;
  testId: string;
}

/**
 * A WDL bar with a bracket on top spanning the share the big number above counts,
 * and everything past the span dimmed. Shared by the Overall score card and the
 * Conversion / Parity / Recovery cards so all four read alike.
 */
export function BracketedWdlBar({ shares, covered, testId }: BracketedWdlBarProps) {
  return (
    <div>
      <div
        className="mb-0.5 h-2 rounded-t-md border-x-[1.5px] border-t-[1.5px]"
        style={{ width: `${covered}%`, borderColor: METRIC_BRACKET_COLOR }}
        data-testid={`${testId}-bracket-span`}
      />
      <div className="relative" data-testid={`${testId}-bar`}>
        <MiniWDLBar win_pct={shares.win} draw_pct={shares.draw} loss_pct={shares.loss} />
        <div
          className="pointer-events-none absolute inset-y-0 right-0 rounded-r-sm"
          style={{ left: `${covered}%`, backgroundColor: METRIC_BRACKET_DIM_OVERLAY }}
          data-testid={`${testId}-dim`}
        />
      </div>
    </div>
  );
}
