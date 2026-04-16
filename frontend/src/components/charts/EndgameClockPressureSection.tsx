/**
 * Time Pressure at Endgame Entry section:
 * Per-time-control table showing clock state when entering endgames.
 * Columns: Time Control | Games | My avg time | Opp avg time | Avg clock diff | Net timeout rate
 */

import { InfoPopover } from '@/components/ui/info-popover';
import { ZONE_DANGER, ZONE_NEUTRAL, ZONE_SUCCESS } from '@/lib/theme';
import type { ClockPressureResponse } from '@/types/endgames';

// Threshold (in % of base clock time) within which a clock-diff is considered
// neutral and shown in the bullet-chart's blue zone color. Beyond this band,
// red (user had less time) or green (user had more time).
const NEUTRAL_PCT_THRESHOLD = 10;

// Threshold (in percentage points) within which the net timeout rate is
// considered neutral. Beyond this band, red (flagged more) or green (flagged
// opponent more).
const NEUTRAL_TIMEOUT_THRESHOLD = 5;

interface EndgameClockPressureSectionProps {
  data: ClockPressureResponse;
}

/** Format clock cell as "12% (7s)" or "45% (1,116s)". Returns "—" if either value is null. */
function formatClockCell(pct: number | null, secs: number | null): string {
  if (pct === null || secs === null) return '—';
  const roundedPct = Math.round(pct);
  const roundedSecs = Math.round(secs);
  return `${roundedPct}% (${roundedSecs.toLocaleString()}s)`;
}

/** Format signed seconds diff as "+45s", "-5s", or "—" if null. */
function formatSignedSeconds(diff: number | null): string {
  if (diff === null) return '—';
  const rounded = Math.round(diff);
  if (rounded > 0) return `+${rounded}s`;
  return `${rounded}s`;
}

/** Format signed percent diff as "+5%", "-3%", "0%", or "—" if either side is null. */
function formatSignedPct(userPct: number | null, oppPct: number | null): string {
  if (userPct === null || oppPct === null) return '—';
  const rounded = Math.round(userPct - oppPct);
  if (rounded > 0) return `+${rounded}%`;
  return `${rounded}%`;
}

/** Format net timeout rate as "+1.0%", "-8.0%", or "0.0%". */
function formatNetTimeoutRate(rate: number): string {
  const formatted = Math.abs(rate).toFixed(1);
  if (rate > 0) return `+${formatted}%`;
  if (rate < 0) return `-${formatted}%`;
  return `0.0%`;
}

export function EndgameClockPressureSection({ data }: EndgameClockPressureSectionProps) {
  return (
    <div className="space-y-4" data-testid="clock-pressure-section">
      {/* Section header */}
      <div>
        <h3 className="text-base font-semibold">
          <span className="inline-flex items-center gap-1">
            Time Pressure at Endgame Entry
            <InfoPopover
              ariaLabel="Clock pressure info"
              testId="clock-pressure-info"
              side="top"
            >
              <p>Shows your clock situation when entering endgames, broken down by time control.</p>
              <p className="mt-1"><strong>My avg time:</strong> your average remaining clock at endgame entry (% of base clock time + absolute seconds, pre-increment).</p>
              <p className="mt-1"><strong>Opp avg time:</strong> opponent&apos;s average remaining clock.</p>
              <p className="mt-1"><strong>% of base time</strong> = remaining clock divided by the starting clock for that game (e.g. 600 for a 600+0 game, 900 for a 900+10 game).</p>
              <p className="mt-1"><strong>Avg clock diff:</strong> difference between your average and your opponent&apos;s average remaining clock, shown as % of base time with absolute seconds in parentheses. Positive means you had more time.</p>
              <p className="mt-1"><strong>Net timeout rate:</strong> (timeout wins minus timeout losses) divided by total endgame games. Negative means you get flagged more than you flag.</p>
            </InfoPopover>
          </span>
        </h3>
        <p className="text-sm text-muted-foreground mt-1">
          How much clock (as % of base time) you have entering endgames, and how often you flag compared to your opponents.
        </p>
      </div>

      {/* Per-row computed display values (shared between desktop table and mobile cards) */}
      {(() => {
        const computedRows = data.rows.map((row) => {
          const pctDiff =
            row.user_avg_pct !== null && row.opp_avg_pct !== null
              ? row.user_avg_pct - row.opp_avg_pct
              : null;
          const diffColor =
            pctDiff === null
              ? undefined
              : pctDiff > NEUTRAL_PCT_THRESHOLD
                ? ZONE_SUCCESS
                : pctDiff < -NEUTRAL_PCT_THRESHOLD
                  ? ZONE_DANGER
                  : ZONE_NEUTRAL;

          const timeoutRate = row.net_timeout_rate;
          const timeoutColor =
            timeoutRate > NEUTRAL_TIMEOUT_THRESHOLD
              ? ZONE_SUCCESS
              : timeoutRate < -NEUTRAL_TIMEOUT_THRESHOLD
                ? ZONE_DANGER
                : ZONE_NEUTRAL;

          return { row, diffColor, timeoutColor };
        });

        return (
          <>
            {/* Desktop: table layout */}
            <div className="hidden lg:block overflow-x-auto">
              <table
                className="w-full min-w-[480px] text-sm"
                data-testid="clock-pressure-table"
              >
                <thead>
                  <tr className="text-left text-xs text-muted-foreground border-b border-border">
                    <th className="py-1 pr-3 font-medium">Time Control</th>
                    <th className="py-1 px-2 font-medium text-right">Games</th>
                    <th className="py-1 px-2 font-medium text-right">My avg time</th>
                    <th className="py-1 px-2 font-medium text-right">Opp avg time</th>
                    <th className="py-1 px-2 font-medium text-right">Avg clock diff</th>
                    <th className="py-1 pl-2 font-medium text-right">Net timeout rate</th>
                  </tr>
                </thead>
                <tbody>
                  {computedRows.map(({ row, diffColor, timeoutColor }) => (
                    <tr
                      key={row.time_control}
                      data-testid={`clock-pressure-row-${row.time_control}`}
                    >
                      <td className="py-1.5 pr-3 text-sm">{row.label}</td>
                      <td className="py-1.5 px-2 text-right text-sm tabular-nums">
                        {row.total_endgame_games.toLocaleString()}
                      </td>
                      <td className="py-1.5 px-2 text-right text-sm tabular-nums">
                        {formatClockCell(row.user_avg_pct, row.user_avg_seconds)}
                      </td>
                      <td className="py-1.5 px-2 text-right text-sm tabular-nums">
                        {formatClockCell(row.opp_avg_pct, row.opp_avg_seconds)}
                      </td>
                      <td
                        className="py-1.5 px-2 text-right text-sm tabular-nums"
                        style={diffColor ? { color: diffColor } : undefined}
                      >
                        {formatSignedPct(row.user_avg_pct, row.opp_avg_pct)}
                        <span className="text-muted-foreground ml-1">({formatSignedSeconds(row.avg_clock_diff_seconds)})</span>
                      </td>
                      <td
                        className="py-1.5 pl-2 text-right text-sm tabular-nums"
                        style={{ color: timeoutColor }}
                      >
                        {formatNetTimeoutRate(row.net_timeout_rate)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Mobile: stacked cards */}
            <div className="lg:hidden space-y-3" data-testid="clock-pressure-cards">
              {computedRows.map(({ row, diffColor, timeoutColor }) => (
                <div
                  key={row.time_control}
                  className="rounded border border-border p-3 space-y-2"
                  data-testid={`clock-pressure-card-${row.time_control}`}
                >
                  <div className="flex items-baseline justify-between">
                    <div className="text-sm font-medium">{row.label}</div>
                    <div className="text-xs tabular-nums text-muted-foreground">
                      {row.total_endgame_games.toLocaleString()} games
                    </div>
                  </div>
                  <div className="flex items-baseline justify-between text-sm">
                    <span className="text-muted-foreground">My avg time</span>
                    <span className="tabular-nums">
                      {formatClockCell(row.user_avg_pct, row.user_avg_seconds)}
                    </span>
                  </div>
                  <div className="flex items-baseline justify-between text-sm">
                    <span className="text-muted-foreground">Opp avg time</span>
                    <span className="tabular-nums">
                      {formatClockCell(row.opp_avg_pct, row.opp_avg_seconds)}
                    </span>
                  </div>
                  <div className="flex items-baseline justify-between text-sm">
                    <span className="text-muted-foreground">Avg clock diff</span>
                    <span
                      className="tabular-nums"
                      style={diffColor ? { color: diffColor } : undefined}
                    >
                      {formatSignedPct(row.user_avg_pct, row.opp_avg_pct)}
                      <span className="text-muted-foreground ml-1">({formatSignedSeconds(row.avg_clock_diff_seconds)})</span>
                    </span>
                  </div>
                  <div className="flex items-baseline justify-between text-sm">
                    <span className="text-muted-foreground">Net timeout rate</span>
                    <span className="tabular-nums" style={{ color: timeoutColor }}>
                      {formatNetTimeoutRate(row.net_timeout_rate)}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </>
        );
      })()}

      {/* Coverage note */}
      <p className="text-xs text-muted-foreground mt-2">
        Games without time control are excluded.
      </p>
    </div>
  );
}
