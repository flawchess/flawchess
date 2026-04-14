/**
 * Time Pressure at Endgame Entry section:
 * Per-time-control table showing clock state when entering endgames.
 * Columns: Time Control | Games | My avg time | Opp avg time | Avg clock diff | Net timeout rate
 */

import { InfoPopover } from '@/components/ui/info-popover';
import type { ClockPressureResponse } from '@/types/endgames';

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
              <p className="mt-1"><strong>% of base time</strong> = remaining clock divided by the starting clock for that game (e.g. 600 for a 600+0 game, 900 for a 900+10 game). Values above 100% are possible when increment banks past the starting clock; bad-data readings above 200% of base are excluded.</p>
              <p className="mt-1"><strong>Avg clock diff:</strong> average difference (your clock minus opponent&apos;s clock) in seconds. Positive means you had more time.</p>
              <p className="mt-1"><strong>Net timeout rate:</strong> (timeout wins minus timeout losses) divided by total endgame games. Negative means you get flagged more than you flag.</p>
              <p className="mt-1">Includes every game that reached an endgame phase (total of at least 3 full moves / 6 half-moves spent in the endgame, summed across all endgame types). The entry clocks are measured at the first endgame position reached in the game.</p>
            </InfoPopover>
          </span>
        </h3>
        <p className="text-sm text-muted-foreground mt-1">
          How much clock (as % of base time) you have entering endgames, and how often you flag compared to your opponents.
        </p>
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
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
            {data.rows.map((row) => {
              const diff = row.avg_clock_diff_seconds;
              const diffClass =
                diff === null || diff === 0
                  ? undefined
                  : diff > 0
                    ? 'text-green-500'
                    : 'text-red-500';

              const timeoutRate = row.net_timeout_rate;
              const timeoutClass =
                timeoutRate === 0
                  ? undefined
                  : timeoutRate > 0
                    ? 'text-green-500'
                    : 'text-red-500';

              return (
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
                  <td className={`py-1.5 px-2 text-right text-sm tabular-nums${diffClass ? ` ${diffClass}` : ''}`}>
                    {formatSignedSeconds(diff)}
                  </td>
                  <td className={`py-1.5 pl-2 text-right text-sm tabular-nums${timeoutClass ? ` ${timeoutClass}` : ''}`}>
                    {formatNetTimeoutRate(timeoutRate)}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Coverage note */}
      <p className="text-xs text-muted-foreground mt-2">
        Games without time control are excluded.
      </p>
    </div>
  );
}
