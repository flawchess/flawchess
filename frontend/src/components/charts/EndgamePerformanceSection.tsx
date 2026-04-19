/**
 * Endgame Performance section:
 * - Endgame vs Non-Endgame WDL comparison table (games, WDL, score, score diff)
 *
 * Phase 59 removed the admin-only gauge charts (Conversion, Recovery, Endgame Skill);
 * the associated EndgameGaugesSection and its gauge-zone constants were deleted.
 */

import { useEffect, useState } from 'react';
import { Bar, CartesianGrid, ComposedChart, Line, ReferenceArea, ReferenceLine, XAxis, YAxis } from 'recharts';
import { ChartContainer, ChartTooltip } from '@/components/ui/chart';
import { InfoPopover } from '@/components/ui/info-popover';
import { MiniWDLBar } from '@/components/stats/MiniWDLBar';
import { MiniBulletChart } from '@/components/charts/MiniBulletChart';
import { ENDGAME_VOLUME_BAR_COLOR, ZONE_DANGER, ZONE_NEUTRAL, ZONE_SUCCESS } from '@/lib/theme';
import { createDateTickFormatter, formatDateWithYear } from '@/lib/utils';
import type {
  EndgamePerformanceResponse,
  ScoreGapMaterialResponse,
  ScoreGapTimelinePoint,
} from '@/types/endgames';

// Material advantage/deficit threshold in pawn points (backend uses 100 centipawns)
export const MATERIAL_ADVANTAGE_POINTS = 1;

// Persistence requirement in full moves (= 4 plies on the backend)
export const PERSISTENCE_MOVES = 2;

interface EndgamePerformanceSectionProps {
  data: EndgamePerformanceResponse;
  scoreGap?: ScoreGapMaterialResponse;
}

// Neutral zone around zero for the endgame-vs-non-endgame score difference
// bullet chart: ±0.10 marks near-parity between the two splits.
const SCORE_DIFF_NEUTRAL_MIN = -0.10;
const SCORE_DIFF_NEUTRAL_MAX = 0.10;

// Bullet domain half-width for this metric. Population p05/p95 spans ~±0.16
// (see reports/benchmarks-2026-04-16.md §1), so ±0.20 covers the observed
// range without making typical values look tiny against the default ±0.40.
const SCORE_DIFF_DOMAIN = 0.20;

// Score-diff timeline (quick-260417-o2l): plot in percentage points (0.10 -> 10).
// Zone band ±10 pp matches the table bullet chart's parity neutral threshold.
const SCORE_DIFF_TIMELINE_NEUTRAL_PCT = 10;
const SCORE_DIFF_TIMELINE_Y_DOMAIN: [number, number] = [-30, 30];
const SCORE_DIFF_TIMELINE_Y_TICKS = [-30, -20, -10, 0, 10, 20, 30];
const SCORE_DIFF_TIMELINE_ZONE_OPACITY = 0.15;
const MOBILE_BREAKPOINT_PX = 768;

function scoreDiffZoneColor(diffPct: number): string {
  if (diffPct > SCORE_DIFF_TIMELINE_NEUTRAL_PCT) return ZONE_SUCCESS;
  if (diffPct < -SCORE_DIFF_TIMELINE_NEUTRAL_PCT) return ZONE_DANGER;
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

export function EndgamePerformanceSection({ data, scoreGap }: EndgamePerformanceSectionProps) {
  const totalGames = data.endgame_wdl.total + data.non_endgame_wdl.total;
  const endgamePct = totalGames > 0 ? (data.endgame_wdl.total / totalGames * 100).toFixed(1) : '0.0';
  const nonEndgamePct = totalGames > 0 ? (data.non_endgame_wdl.total / totalGames * 100).toFixed(1) : '0.0';

  const diffPositive = scoreGap ? scoreGap.score_difference >= 0 : false;
  const diffFormatted = scoreGap
    ? (diffPositive ? '+' : '') + `${Math.round(scoreGap.score_difference * 100)}%`
    : '';
  const diffColor = scoreGap
    ? scoreGap.score_difference >= SCORE_DIFF_NEUTRAL_MAX
      ? ZONE_SUCCESS
      : scoreGap.score_difference >= SCORE_DIFF_NEUTRAL_MIN
        ? ZONE_NEUTRAL
        : ZONE_DANGER
    : ZONE_NEUTRAL;

  const rows = [
    {
      label: 'Yes',
      pct: endgamePct,
      wdl: data.endgame_wdl,
      score: scoreGap?.endgame_score,
      testId: 'perf-wdl-endgame',
    },
    {
      label: 'No',
      pct: nonEndgamePct,
      wdl: data.non_endgame_wdl,
      score: scoreGap?.non_endgame_score,
      testId: 'perf-wdl-non-endgame',
    },
  ];

  return (
    <div className="space-y-4">
      <div>
        <h3 className="text-base font-semibold">
          <span className="inline-flex items-center gap-1">
            Games with vs without Endgame
            <InfoPopover ariaLabel="Games with vs without Endgame info" testId="perf-section-info" side="top">
              <div className="space-y-2">
                <p>Compares your win/draw/loss rates in games that reached an endgame phase versus those that did not. Only endgames that span at least 3 full moves (6 half-moves) are counted. Shorter tactical transitions from middlegame into a checkmate are treated as &quot;no endgame&quot;.</p>
                <p>The <strong>Score % Difference</strong> column shows the signed gap between your endgame Score % and non-endgame Score % (green = endgame stronger, red = endgame weaker, blue = near parity).</p>
              </div>
            </InfoPopover>
          </span>
        </h3>
        <p className="text-sm text-muted-foreground mt-1">
          Do you perform better or worse when games reach an endgame?
        </p>
      </div>

      {/* Desktop: table layout */}
      <div className="hidden lg:block overflow-x-auto">
        <table
          className="w-full min-w-[720px] text-sm sm:text-base table-fixed"
          data-testid="perf-wdl-table"
        >
          <colgroup>
            <col style={{ width: '140px' }} />
            <col style={{ width: '130px' }} />
            <col style={{ width: '160px' }} />
            <col style={{ width: '110px' }} />
            <col style={{ width: '180px' }} />
          </colgroup>
          <thead>
            <tr className="text-left text-xs text-muted-foreground border-b border-border">
              <th className="py-1 pr-3 font-medium">Endgame</th>
              <th className="py-1 px-2 font-medium text-right">Games</th>
              <th className="py-1 px-2 font-medium">Win / Draw / Loss</th>
              <th className="py-1 px-2 font-medium text-right">Score %</th>
              <th className="py-1 px-2 font-medium">Score % Difference</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row, i) => (
              <tr key={row.label} data-testid={row.testId}>
                <td className="py-1.5 pr-3 text-sm">{row.label}</td>
                <td className="py-1.5 px-2 text-right text-sm tabular-nums whitespace-nowrap">
                  {row.pct}% ({row.wdl.total.toLocaleString()})
                </td>
                <td className="py-1.5 px-2">
                  {row.wdl.total === 0 ? (
                    <div className="h-5 rounded bg-muted" />
                  ) : (
                    <MiniWDLBar
                      win_pct={row.wdl.win_pct}
                      draw_pct={row.wdl.draw_pct}
                      loss_pct={row.wdl.loss_pct}
                    />
                  )}
                </td>
                <td className="py-1.5 px-2 text-right text-sm tabular-nums text-muted-foreground whitespace-nowrap">
                  {row.score !== undefined ? `${Math.round(row.score * 100)}%` : '—'}
                </td>
                {scoreGap ? (
                  i === 0 ? (
                    <td
                      className="py-1.5 px-2 text-left text-sm tabular-nums whitespace-nowrap"
                      data-testid="score-gap-difference"
                    >
                      <span className="font-semibold" style={{ color: diffColor }}>{diffFormatted}</span>
                    </td>
                  ) : (
                    <td className="py-1.5 px-2 text-left">
                      <MiniBulletChart
                        value={scoreGap.score_difference}
                        neutralMin={SCORE_DIFF_NEUTRAL_MIN}
                        neutralMax={SCORE_DIFF_NEUTRAL_MAX}
                        domain={SCORE_DIFF_DOMAIN}
                        ariaLabel={`Endgame score difference: ${diffFormatted}`}
                      />
                    </td>
                  )
                ) : (
                  <td className="py-1.5 px-2" />
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Mobile: stacked cards */}
      <div className="lg:hidden space-y-3" data-testid="perf-wdl-cards">
        {rows.map((row) => (
          <div
            key={row.label}
            className="rounded border border-border p-3 space-y-2"
            data-testid={row.testId}
          >
            <div className="flex items-baseline justify-between">
              <div className="text-sm font-medium">Endgame: {row.label}</div>
              <div className="text-xs tabular-nums text-muted-foreground">
                {row.pct}% ({row.wdl.total.toLocaleString()} games)
              </div>
            </div>
            <div>
              <div className="text-xs text-muted-foreground mb-1">Win / Draw / Loss</div>
              {row.wdl.total === 0 ? (
                <div className="h-5 rounded bg-muted" />
              ) : (
                <MiniWDLBar
                  win_pct={row.wdl.win_pct}
                  draw_pct={row.wdl.draw_pct}
                  loss_pct={row.wdl.loss_pct}
                />
              )}
            </div>
            <div className="flex items-baseline justify-between text-sm">
              <span className="text-muted-foreground">Score %</span>
              <span className="tabular-nums text-muted-foreground">
                {row.score !== undefined ? `${Math.round(row.score * 100)}%` : '—'}
              </span>
            </div>
          </div>
        ))}
        {scoreGap && (
          <div
            className="rounded border border-border p-3 space-y-2"
            data-testid="score-gap-difference-mobile"
          >
            <div className="flex items-baseline justify-between">
              <div className="text-sm font-medium">Score % Difference</div>
              <div className="text-sm tabular-nums">
                <span className="font-semibold" style={{ color: diffColor }}>{diffFormatted}</span>
              </div>
            </div>
            <MiniBulletChart
              value={scoreGap.score_difference}
              neutralMin={SCORE_DIFF_NEUTRAL_MIN}
              neutralMax={SCORE_DIFF_NEUTRAL_MAX}
              domain={SCORE_DIFF_DOMAIN}
              ariaLabel={`Endgame score difference: ${diffFormatted}`}
            />
          </div>
        )}
      </div>

      {/* Score-diff timeline (quick-260417-o2l): weekly rolling-100 mean diff in pp. */}
      {scoreGap && (
        <ScoreDiffTimelineChart
          timeline={scoreGap.timeline}
          window={scoreGap.timeline_window}
        />
      )}
    </div>
  );
}

interface ScoreDiffTimelineChartProps {
  timeline: ScoreGapTimelinePoint[];
  window: number;
}

interface ScoreDiffChartPoint {
  date: string;
  diff_pct: number;
  endgame_game_count: number;
  non_endgame_game_count: number;
  per_week_total_games: number;
}

function ScoreDiffTimelineChart({ timeline, window }: ScoreDiffTimelineChartProps) {
  const isMobile = useIsMobile();

  if (timeline.length === 0) return null;

  const data: ScoreDiffChartPoint[] = timeline.map((p) => ({
    date: p.date,
    // Convert 0-1 score to percentage points for plotting (0.05 -> 5).
    diff_pct: p.score_difference * 100,
    endgame_game_count: p.endgame_game_count,
    non_endgame_game_count: p.non_endgame_game_count,
    per_week_total_games: p.per_week_total_games,
  }));

  const dates = data.map((p) => p.date);
  const formatDateTick = createDateTickFormatter(dates);

  // Extend the Y domain symmetrically when data exceeds the default ±20 band,
  // so dots never overflow the plot area.
  const values = data.map((p) => p.diff_pct);
  const dataMax = values.length > 0 ? Math.max(...values) : SCORE_DIFF_TIMELINE_Y_DOMAIN[1];
  const dataMin = values.length > 0 ? Math.min(...values) : SCORE_DIFF_TIMELINE_Y_DOMAIN[0];
  const yMax = Math.max(SCORE_DIFF_TIMELINE_Y_DOMAIN[1], Math.ceil(dataMax));
  const yMin = Math.min(SCORE_DIFF_TIMELINE_Y_DOMAIN[0], Math.floor(dataMin));
  const yDomain: [number, number] = [yMin, yMax];

  // Volume-bar Y-axis envelope. domain={[0, barMax * 5]} pins the tallest
  // bar to the bottom 20% of the chart canvas (Pattern 3 from 57.1-RESEARCH.md).
  // Math.max(..., 1) avoids a [0, 0] domain when no week has any games.
  const barMax = Math.max(1, ...data.map((p) => p.per_week_total_games));

  return (
    <div className="mt-6" data-testid="score-diff-timeline-section">
      <div className="mb-3">
        <h3 className="text-base font-semibold">
          <span className="inline-flex items-center gap-1">
            Score % Difference over Time
            <InfoPopover
              ariaLabel="Score difference timeline info"
              testId="score-diff-timeline-info"
              side="top"
            >
              <p>
                Difference between your endgame Score % and non-endgame Score %
                over the trailing {window} games per side, sampled once per week.
                Endgame and non-endgame games each carry their own
                {' '}{window}-game window, so weeks with sparse activity on one
                side still reflect the broader history of that side.
              </p>
              <p className="mt-1">
                Dots are colored by zone: green when the gap exceeds
                +{SCORE_DIFF_TIMELINE_NEUTRAL_PCT}%, red when it&apos;s below
                -{SCORE_DIFF_TIMELINE_NEUTRAL_PCT}%, blue in between.
              </p>
              <p className="mt-1">
                Early weeks where either side has fewer than 10 games in the
                window are hidden.
              </p>
            </InfoPopover>
          </span>
        </h3>
        <p className="text-sm text-muted-foreground mt-1">
          Has your endgame edge versus your non-endgame play improved over time?
        </p>
      </div>
      <div className={isMobile ? '' : 'flex items-stretch'}>
        {!isMobile && (
          <div
            className="flex items-center text-xs text-muted-foreground shrink-0 pt-33 -mr-1"
            style={{ writingMode: 'vertical-rl', transform: 'rotate(180deg)' }}
          >
            Score diff %
          </div>
        )}
        <ChartContainer
          config={{}}
          className="w-full h-72"
          data-testid="score-diff-timeline-chart"
        >
          <ComposedChart
            data={data}
            margin={{ top: 5, right: 10, left: isMobile ? 0 : 10, bottom: 10 }}
          >
            <CartesianGrid vertical={false} />
            <ReferenceArea
              yAxisId="value"
              y1={yDomain[0]}
              y2={-SCORE_DIFF_TIMELINE_NEUTRAL_PCT}
              fill={ZONE_DANGER}
              fillOpacity={SCORE_DIFF_TIMELINE_ZONE_OPACITY}
            />
            <ReferenceArea
              yAxisId="value"
              y1={-SCORE_DIFF_TIMELINE_NEUTRAL_PCT}
              y2={SCORE_DIFF_TIMELINE_NEUTRAL_PCT}
              fill={ZONE_NEUTRAL}
              fillOpacity={SCORE_DIFF_TIMELINE_ZONE_OPACITY}
            />
            <ReferenceArea
              yAxisId="value"
              y1={SCORE_DIFF_TIMELINE_NEUTRAL_PCT}
              y2={yDomain[1]}
              fill={ZONE_SUCCESS}
              fillOpacity={SCORE_DIFF_TIMELINE_ZONE_OPACITY}
            />
            <XAxis dataKey="date" tickFormatter={formatDateTick} />
            <YAxis
              yAxisId="value"
              domain={yDomain}
              ticks={SCORE_DIFF_TIMELINE_Y_TICKS}
              allowDataOverflow={false}
              tickFormatter={(v: number) =>
                v > 0 ? `+${v}%` : `${v}%`
              }
              width={44}
            />
            {/* Hidden right Y-axis dedicated to volume bars.
                domain={[0, barMax * 5]} pins the tallest bar to the bottom 20%
                of the chart canvas (Pattern 3 in 57.1-RESEARCH.md). */}
            <YAxis yAxisId="bars" orientation="right" hide domain={[0, barMax * 5]} />
            <ReferenceLine yAxisId="value" y={0} stroke="var(--border)" strokeDasharray="3 3" />
            <ChartTooltip
              content={({ active, payload, label }) => {
                if (!active || !payload?.length) return null;
                const point = payload.find(
                  (p) => (p.payload as ScoreDiffChartPoint | undefined)?.date !== undefined,
                )?.payload as ScoreDiffChartPoint | undefined;
                if (!point) return null;
                const diff = point.diff_pct;
                const sign = diff > 0 ? '+' : '';
                return (
                  <div className="rounded-lg border border-border/50 bg-background px-3 py-2 text-xs shadow-xl space-y-1">
                    <div className="font-medium">
                      Week of {formatDateWithYear(label as string)}
                    </div>
                    <div className="text-muted-foreground">
                      Games this week: {point.per_week_total_games}
                    </div>
                    <div className="flex items-center gap-1.5">
                      <div
                        className="h-2 w-2 shrink-0 rounded-[2px]"
                        style={{ backgroundColor: scoreDiffZoneColor(diff) }}
                      />
                      <span>
                        Score % diff: {sign}
                        {diff.toFixed(1)}%
                        <span className="text-muted-foreground ml-1">
                          (endgame {point.endgame_game_count} games, non-endgame {point.non_endgame_game_count} games)
                        </span>
                      </span>
                    </div>
                  </div>
                );
              }}
            />
            <Bar
              yAxisId="bars"
              dataKey="per_week_total_games"
              fill={ENDGAME_VOLUME_BAR_COLOR}
              legendType="none"
              isAnimationActive={false}
              data-testid="score-diff-volume-bars"
            />
            <Line
              yAxisId="value"
              type="monotone"
              dataKey="diff_pct"
              stroke="var(--muted-foreground)"
              strokeWidth={2}
              connectNulls={true}
              dot={false}
            />
          </ComposedChart>
        </ChartContainer>
      </div>
      <p className="text-xs text-muted-foreground text-center -mt-2">
        Week (rolling average of the last {window} games per side)
      </p>
    </div>
  );
}

