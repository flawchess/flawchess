/**
 * Time Pressure at Endgame Entry section:
 * Per-time-control table showing clock state when entering endgames.
 * Columns: Time Control | Games | My avg time | Opp avg time | Avg clock diff | Net timeout rate
 */

import { useState, useEffect } from 'react';
import { CartesianGrid, Line, LineChart, ReferenceArea, ReferenceLine, XAxis, YAxis } from 'recharts';
import { ChartContainer, ChartTooltip } from '@/components/ui/chart';
import { InfoPopover } from '@/components/ui/info-popover';
import { ZONE_DANGER, ZONE_NEUTRAL, ZONE_SUCCESS } from '@/lib/theme';
import { createDateTickFormatter, formatDateWithYear } from '@/lib/utils';
import type { ClockPressureResponse, ClockPressureTimelinePoint } from '@/types/endgames';

// Threshold (in % of base clock time) within which a clock-diff is considered
// neutral and shown in the bullet-chart's blue zone color. Beyond this band,
// red (user had less time) or green (user had more time).
const NEUTRAL_PCT_THRESHOLD = 10;

// Threshold (in percentage points) within which the net timeout rate is
// considered neutral. Beyond this band, red (flagged more) or green (flagged
// opponent more).
const NEUTRAL_TIMEOUT_THRESHOLD = 5;

// Clock-diff timeline chart (quick-260416-w3q): fixed ±30% Y-axis centered on 0.
const TIMELINE_Y_DOMAIN: [number, number] = [-30, 30];
const TIMELINE_Y_TICKS = [-30, -20, -10, 0, 10, 20, 30];
const MOBILE_BREAKPOINT_PX = 768;

// Muted zone backgrounds on the timeline (match MiniBulletChart zone hues).
// Lower than the bullet chart's 0.35 because the timeline spans the full chart
// area — 0.35 would dominate the line.
const TIMELINE_ZONE_OPACITY = 0.15;

function zoneColor(diff: number): string {
  if (diff > NEUTRAL_PCT_THRESHOLD) return ZONE_SUCCESS;
  if (diff < -NEUTRAL_PCT_THRESHOLD) return ZONE_DANGER;
  return ZONE_NEUTRAL;
}

function useIsMobile(): boolean {
  const [isMobile, setIsMobile] = useState(() =>
    typeof window !== 'undefined'
      && window.matchMedia(`(max-width: ${MOBILE_BREAKPOINT_PX - 1}px)`).matches,
  );
  useEffect(() => {
    const mq = window.matchMedia(`(max-width: ${MOBILE_BREAKPOINT_PX - 1}px)`);
    const update = () => setIsMobile(mq.matches);
    mq.addEventListener('change', update);
    return () => mq.removeEventListener('change', update);
  }, []);
  return isMobile;
}

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

      {/* Clock-diff timeline (quick-260416-w3q): weekly rolling-100 mean, ±20% axis. */}
      <ClockDiffTimelineChart
        timeline={data.timeline}
        window={data.timeline_window}
      />
    </div>
  );
}

interface ClockDiffTimelineChartProps {
  timeline: ClockPressureTimelinePoint[];
  window: number;
}

function ClockDiffTimelineChart({ timeline, window }: ClockDiffTimelineChartProps) {
  const isMobile = useIsMobile();

  if (timeline.length === 0) return null;

  const dates = timeline.map((p) => p.date);
  const formatDateTick = createDateTickFormatter(dates);

  // Extend the Y domain symmetrically when data exceeds the default ±30 band,
  // then pin the red/green zone bounds to that same domain so the zone
  // backgrounds match the plot area exactly (no uncolored overflow, no rect
  // spilling outside the chart). Recharts uses a fixed numeric domain when
  // we pass one explicitly — no auto-extend magic, no padding.
  const values = timeline.map((p) => p.avg_clock_diff_pct);
  const dataMax = values.length > 0 ? Math.max(...values) : TIMELINE_Y_DOMAIN[1];
  const dataMin = values.length > 0 ? Math.min(...values) : TIMELINE_Y_DOMAIN[0];
  const yMax = Math.max(TIMELINE_Y_DOMAIN[1], Math.ceil(dataMax));
  const yMin = Math.min(TIMELINE_Y_DOMAIN[0], Math.floor(dataMin));
  const yDomain: [number, number] = [yMin, yMax];

  return (
    <div className="mt-6" data-testid="clock-pressure-timeline-section">
      <div className="mb-3">
        <h3 className="text-base font-semibold">
          <span className="inline-flex items-center gap-1">
            Average Clock Difference over Time
            <InfoPopover
              ariaLabel="Clock diff timeline info"
              testId="clock-pressure-timeline-info"
              side="top"
            >
              <p>
                Average clock difference (your remaining clock minus your opponent&apos;s,
                as % of base time) at endgame entry over the last {window} games,
                sampled once per week. Collapsed across all time controls — use the
                filter panel to narrow by time control.
              </p>
              <p className="mt-1">
                Dots are colored by zone: green when your lead exceeds
                +{NEUTRAL_PCT_THRESHOLD}%, red when you&apos;re down more than
                -{NEUTRAL_PCT_THRESHOLD}%, blue in between.
              </p>
              <p className="mt-1">
                Early weeks with fewer than 10 games in the window are hidden.
              </p>
            </InfoPopover>
          </span>
        </h3>
        <p className="text-sm text-muted-foreground mt-1">
          Has your time management improved, or are you still falling behind on the clock by the endgame?
        </p>
      </div>
      <div className={isMobile ? '' : 'flex items-stretch'}>
        {!isMobile && (
          <div
            className="flex items-center text-xs text-muted-foreground shrink-0 pt-30 -mr-1"
            style={{ writingMode: 'vertical-rl', transform: 'rotate(180deg)' }}
          >
            Clock diff %
          </div>
        )}
        <ChartContainer
          config={{}}
          className="w-full h-72"
          data-testid="clock-pressure-timeline-chart"
        >
          <LineChart
            data={timeline}
            margin={{ top: 5, right: 10, left: isMobile ? 0 : 10, bottom: 10 }}
          >
            <CartesianGrid vertical={false} />
            <ReferenceArea
              y1={yDomain[0]}
              y2={-NEUTRAL_PCT_THRESHOLD}
              fill={ZONE_DANGER}
              fillOpacity={TIMELINE_ZONE_OPACITY}
            />
            <ReferenceArea
              y1={-NEUTRAL_PCT_THRESHOLD}
              y2={NEUTRAL_PCT_THRESHOLD}
              fill={ZONE_NEUTRAL}
              fillOpacity={TIMELINE_ZONE_OPACITY}
            />
            <ReferenceArea
              y1={NEUTRAL_PCT_THRESHOLD}
              y2={yDomain[1]}
              fill={ZONE_SUCCESS}
              fillOpacity={TIMELINE_ZONE_OPACITY}
            />
            <XAxis dataKey="date" tickFormatter={formatDateTick} />
            <YAxis
              domain={yDomain}
              ticks={TIMELINE_Y_TICKS}
              allowDataOverflow={false}
              tickFormatter={(v: number) =>
                v > 0 ? `+${v}%` : `${v}%`
              }
              width={isMobile ? 36 : 44}
            />
            <ReferenceLine y={0} stroke="var(--border)" strokeDasharray="3 3" />
            <ChartTooltip
              content={({ active, payload, label }) => {
                if (!active || !payload?.length) return null;
                const point = payload[0]?.payload as
                  | ClockPressureTimelinePoint
                  | undefined;
                if (!point) return null;
                const diff = point.avg_clock_diff_pct;
                const sign = diff > 0 ? '+' : '';
                return (
                  <div className="rounded-lg border border-border/50 bg-background px-3 py-2 text-xs shadow-xl space-y-1">
                    <div className="font-medium">
                      Week of {formatDateWithYear(label as string)}
                    </div>
                    <div className="flex items-center gap-1.5">
                      <div
                        className="h-2 w-2 shrink-0 rounded-[2px]"
                        style={{ backgroundColor: zoneColor(diff) }}
                      />
                      <span>
                        Avg clock diff: {sign}
                        {diff.toFixed(1)}%
                        <span className="text-muted-foreground ml-1">
                          (past {point.game_count} games)
                        </span>
                      </span>
                    </div>
                  </div>
                );
              }}
            />
            <Line
              type="monotone"
              dataKey="avg_clock_diff_pct"
              stroke="var(--muted-foreground)"
              strokeWidth={2}
              connectNulls={true}
              dot={(props: {
                cx?: number;
                cy?: number;
                payload?: Record<string, unknown>;
              }) => {
                const { cx, cy, payload } = props;
                if (!payload || !Number.isFinite(cx) || !Number.isFinite(cy)) {
                  return <g key={`nodot-${String(payload?.date ?? cx)}`} />;
                }
                const diff = (payload.avg_clock_diff_pct as number) ?? 0;
                return (
                  <circle
                    key={`clock-diff-dot-${payload.date as string}`}
                    cx={cx}
                    cy={cy}
                    r={4}
                    fill={zoneColor(diff)}
                  />
                );
              }}
            />
          </LineChart>
        </ChartContainer>
      </div>
      <p className="text-xs text-muted-foreground text-center -mt-2">
        Week (rolling average of the last {window} games)
      </p>
    </div>
  );
}
