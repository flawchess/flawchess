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
  /** How much of the bar the formula counts, in percent of the bar width. */
  covered: number;
  /** What the bracket counts, e.g. "wins + ½draws". No value: the big number above says it. */
  label: string;
  testId: string;
}

/**
 * A WDL bar with a bracket on top spanning the share a formula counts, the formula
 * above the bracket, and everything past the span dimmed. Shared by the Overall
 * score card and the Conversion / Parity / Recovery cards so all four read alike.
 */
export function BracketedWdlBar({ shares, covered, label, testId }: BracketedWdlBarProps) {
  return (
    <div>
      {/* Centered over the span; `justify-center-safe` falls back to left-aligned when
          the label is wider than the span, so it never runs off the bar's left edge. */}
      <div className="mb-1 flex justify-center-safe" style={{ width: `${covered}%` }}>
        <span
          className="whitespace-nowrap text-sm text-muted-foreground"
          data-testid={`${testId}-bracket-label`}
        >
          {label}
        </span>
      </div>
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
