/**
 * Endgame Performance section:
 * - Endgame vs Non-Endgame WDL comparison table (games, WDL, score, score gap)
 *
 * Phase 59 removed the admin-only gauge charts (Conversion, Recovery, Endgame Skill);
 * the associated EndgameGaugesSection and its gauge-zone constants were deleted.
 */

import { useEffect, useState } from 'react';
import { Area, CartesianGrid, ComposedChart, Line, XAxis, YAxis } from 'recharts';
import { ChartContainer, ChartTooltip } from '@/components/ui/chart';
import { InfoPopover } from '@/components/ui/info-popover';
import { MiniWDLBar } from '@/components/stats/MiniWDLBar';
import { MiniBulletChart } from '@/components/charts/MiniBulletChart';
import {
  SCORE_TIMELINE_FILL_ABOVE,
  SCORE_TIMELINE_FILL_BELOW,
  SCORE_TIMELINE_LINE_ENDGAME,
  SCORE_TIMELINE_LINE_NON_ENDGAME,
  ZONE_DANGER,
  ZONE_NEUTRAL,
  ZONE_SUCCESS,
} from '@/lib/theme';
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

// Neutral zone around zero for the endgame-vs-non-endgame score gap
// bullet chart: ±0.10 marks near-parity between the two splits.
const SCORE_GAP_NEUTRAL_MIN = -0.10;
const SCORE_GAP_NEUTRAL_MAX = 0.10;

// Bullet domain half-width for this metric. Population p05/p95 spans ~±0.16
// (see reports/benchmarks-2026-04-16.md §1), so ±0.20 covers the observed
// range without making typical values look tiny against the default ±0.40.
const SCORE_GAP_DOMAIN = 0.20;

// Endgame vs Non-Endgame Score timeline (Phase 68). Absolute scores on a
// 0-100 Y-axis. Epsilon band: when |endgame - non_endgame| <= 1 pp, neither
// shaded band renders — avoids flicker around the crossover.
const SCORE_TIMELINE_Y_DOMAIN: [number, number] = [0, 100];
const SCORE_TIMELINE_Y_TICKS = [0, 25, 50, 75, 100];
const SCORE_TIMELINE_EPSILON_PCT = 1;
const MOBILE_BREAKPOINT_PX = 768;

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

  const gapPositive = scoreGap ? scoreGap.score_difference >= 0 : false;
  const gapFormatted = scoreGap
    ? (gapPositive ? '+' : '') + `${Math.round(scoreGap.score_difference * 100)}%`
    : '';
  const gapColor = scoreGap
    ? scoreGap.score_difference >= SCORE_GAP_NEUTRAL_MAX
      ? ZONE_SUCCESS
      : scoreGap.score_difference >= SCORE_GAP_NEUTRAL_MIN
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
                <p>The <strong>Score Gap</strong> column shows the signed gap between your endgame Score and non-endgame Score (green = endgame stronger, red = endgame weaker, blue = near parity).</p>
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
              <th className="py-1 px-2 font-medium text-right">Score</th>
              <th className="py-1 px-2 font-medium">Score Gap</th>
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
                      <span className="font-semibold" style={{ color: gapColor }}>{gapFormatted}</span>
                    </td>
                  ) : (
                    <td className="py-1.5 px-2 text-left">
                      <MiniBulletChart
                        value={scoreGap.score_difference}
                        neutralMin={SCORE_GAP_NEUTRAL_MIN}
                        neutralMax={SCORE_GAP_NEUTRAL_MAX}
                        domain={SCORE_GAP_DOMAIN}
                        ariaLabel={`Endgame vs non-endgame score gap: ${gapFormatted}`}
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
              <span className="text-muted-foreground">Score</span>
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
              <div className="text-sm font-medium">Score Gap</div>
              <div className="text-sm tabular-nums">
                <span className="font-semibold" style={{ color: gapColor }}>{gapFormatted}</span>
              </div>
            </div>
            <MiniBulletChart
              value={scoreGap.score_difference}
              neutralMin={SCORE_GAP_NEUTRAL_MIN}
              neutralMax={SCORE_GAP_NEUTRAL_MAX}
              domain={SCORE_GAP_DOMAIN}
              ariaLabel={`Endgame vs non-endgame score gap: ${gapFormatted}`}
            />
          </div>
        )}
      </div>
    </div>
  );
}

export interface EndgameScoreOverTimeChartProps {
  timeline: ScoreGapTimelinePoint[];
  window: number;
}

interface ScoreOverTimeChartPoint {
  date: string;
  endgame: number;       // 0-100 whole-number percentage
  non_endgame: number;   // 0-100 whole-number percentage
  endgame_game_count: number;
  non_endgame_game_count: number;
  // Ranged tuple [low, high] — Recharts renders an <Area> as a band between
  // the two values. Null when the sign/epsilon rule says this band is absent
  // at this point, which makes Recharts skip the segment cleanly.
  band_above: [number, number] | null;
  band_below: [number, number] | null;
}

/**
 * Phase 68: two-line absolute Score timeline (endgame + non-endgame) with
 * a sign-aware shaded band in between.
 *
 * Shading:
 * - band_above (green): endgame leads non-endgame by > 1 pp.
 * - band_below (red):   endgame trails non-endgame by > 1 pp.
 * - Within ±1 pp: neither band renders (epsilon neutral — avoids flicker
 *   at the crossover).
 *
 * Each `<Area>` is wrapped in a testid-carrying `<g>` so tests assert on
 * testid presence rather than computed fill color (jsdom + oklch tokens
 * don't compute reliably). If ALL points at the band's dataKey are null,
 * the wrapping `<g>` is not rendered at all, letting the epsilon/all-above/
 * all-below fixtures assert presence/absence deterministically.
 */
export function EndgameScoreOverTimeChart({ timeline, window }: EndgameScoreOverTimeChartProps) {
  const isMobile = useIsMobile();

  if (timeline.length === 0) return null;

  const data: ScoreOverTimeChartPoint[] = timeline.map((p) => {
    // Plan 01 guarantees endgame_score / non_endgame_score are present
    // on every point — no fallback needed.
    const endgame = Math.round(p.endgame_score * 100);
    const non_endgame = Math.round(p.non_endgame_score * 100);
    const diff = endgame - non_endgame;

    const band_above: [number, number] | null =
      diff > SCORE_TIMELINE_EPSILON_PCT ? [non_endgame, endgame] : null;
    const band_below: [number, number] | null =
      diff < -SCORE_TIMELINE_EPSILON_PCT ? [endgame, non_endgame] : null;

    return {
      date: p.date,
      endgame,
      non_endgame,
      endgame_game_count: p.endgame_game_count,
      non_endgame_game_count: p.non_endgame_game_count,
      band_above,
      band_below,
    };
  });

  // If every point's band_above is null, omit the entire `<g data-testid=
  // "score-band-above">` wrapper — tests assert on the wrapper's presence.
  // Same for band_below. This is cleaner than relying on Recharts to suppress
  // empty paths.
  const hasAboveBand = data.some((p) => p.band_above !== null);
  const hasBelowBand = data.some((p) => p.band_below !== null);

  const dates = data.map((p) => p.date);
  const formatDateTick = createDateTickFormatter(dates);

  return (
    <div data-testid="endgame-score-timeline-chart">
      <div className="mb-3">
        <h3 className="text-base font-semibold">
          <span className="inline-flex items-center gap-1">
            Endgame vs Non-Endgame Score over Time
            <InfoPopover
              ariaLabel="Endgame vs non-endgame score timeline info"
              testId="score-timeline-info"
              side="top"
            >
              <p>
                Your endgame Score and non-endgame Score over the trailing {window} games,
                sampled once per week.
              </p>
              <p className="mt-1">
                The shaded area between the lines is color-coded: green when your
                endgame Score leads your non-endgame Score, red when it trails.
              </p>
              <p className="mt-1">
                Early weeks where either side has fewer than 10 games in the
                window are hidden.
              </p>
            </InfoPopover>
          </span>
        </h3>
        <p className="text-sm text-muted-foreground mt-1">
          Is your endgame improving faster than the rest of your game?
        </p>
      </div>
      <div className={isMobile ? '' : 'flex items-stretch'}>
        {!isMobile && (
          <div
            className="flex items-center text-xs text-muted-foreground shrink-0 pt-33 -mr-1"
            style={{ writingMode: 'vertical-rl', transform: 'rotate(180deg)' }}
          >
            Score
          </div>
        )}
        <ChartContainer
          config={{}}
          className="w-full h-72"
          data-testid="endgame-score-timeline-chart-container"
        >
          <ComposedChart
            data={data}
            margin={{ top: 5, right: 10, left: isMobile ? 0 : 10, bottom: 10 }}
          >
            <CartesianGrid vertical={false} />
            <XAxis dataKey="date" tickFormatter={formatDateTick} />
            <YAxis
              domain={SCORE_TIMELINE_Y_DOMAIN}
              ticks={SCORE_TIMELINE_Y_TICKS}
              allowDataOverflow={false}
              tickFormatter={(v: number) => `${v}%`}
              width={44}
            />
            <ChartTooltip
              content={({ active, payload, label }) => {
                if (!active || !payload?.length) return null;
                const point = payload.find(
                  (p) => (p.payload as ScoreOverTimeChartPoint | undefined)?.date !== undefined,
                )?.payload as ScoreOverTimeChartPoint | undefined;
                if (!point) return null;
                const gap = point.endgame - point.non_endgame;
                const gapSign = gap > 0 ? '+' : '';
                return (
                  <div className="rounded-lg border border-border/50 bg-background px-3 py-2 text-xs shadow-xl space-y-1">
                    <div className="font-medium">
                      Week of {formatDateWithYear(label as string)}
                    </div>
                    <div className="flex items-center gap-1.5">
                      <div
                        className="h-2 w-2 shrink-0 rounded-[2px]"
                        style={{ backgroundColor: SCORE_TIMELINE_LINE_ENDGAME }}
                      />
                      <span>
                        Endgame: {point.endgame}%
                        <span className="text-muted-foreground ml-1">
                          (n={point.endgame_game_count})
                        </span>
                      </span>
                    </div>
                    <div className="flex items-center gap-1.5">
                      <div
                        className="h-2 w-2 shrink-0 rounded-[2px]"
                        style={{ backgroundColor: SCORE_TIMELINE_LINE_NON_ENDGAME }}
                      />
                      <span>
                        Non-endgame: {point.non_endgame}%
                        <span className="text-muted-foreground ml-1">
                          (n={point.non_endgame_game_count})
                        </span>
                      </span>
                    </div>
                    <div className="text-muted-foreground">
                      Gap: {gapSign}{gap}%
                    </div>
                  </div>
                );
              }}
            />
            {hasAboveBand && (
              <g data-testid="score-band-above">
                <Area
                  type="monotone"
                  dataKey="band_above"
                  fill={SCORE_TIMELINE_FILL_ABOVE}
                  stroke="none"
                  isAnimationActive={false}
                  connectNulls={false}
                  legendType="none"
                />
              </g>
            )}
            {hasBelowBand && (
              <g data-testid="score-band-below">
                <Area
                  type="monotone"
                  dataKey="band_below"
                  fill={SCORE_TIMELINE_FILL_BELOW}
                  stroke="none"
                  isAnimationActive={false}
                  connectNulls={false}
                  legendType="none"
                />
              </g>
            )}
            <Line
              type="monotone"
              dataKey="endgame"
              stroke={SCORE_TIMELINE_LINE_ENDGAME}
              strokeWidth={2}
              dot={false}
              connectNulls={false}
              isAnimationActive={false}
            />
            <Line
              type="monotone"
              dataKey="non_endgame"
              stroke={SCORE_TIMELINE_LINE_NON_ENDGAME}
              strokeWidth={2}
              dot={false}
              connectNulls={false}
              isAnimationActive={false}
            />
          </ComposedChart>
        </ChartContainer>
      </div>
      {/* Custom legend rendered outside the chart so we can attach per-item
          data-testid attributes. Recharts' default <Legend> doesn't expose
          hooks for that without a custom `content` render prop, and this
          approach avoids another indirection. */}
      <div
        className="flex flex-wrap items-center justify-center gap-4 mt-1 text-xs text-muted-foreground"
        data-testid="endgame-score-timeline-legend"
      >
        <span className="inline-flex items-center gap-1.5" data-testid="chart-legend-endgame">
          <span
            className="inline-block h-2 w-2 rounded-[2px]"
            style={{ backgroundColor: SCORE_TIMELINE_LINE_ENDGAME }}
            aria-hidden="true"
          />
          Endgame
        </span>
        <span className="inline-flex items-center gap-1.5" data-testid="chart-legend-non-endgame">
          <span
            className="inline-block h-2 w-2 rounded-[2px]"
            style={{ backgroundColor: SCORE_TIMELINE_LINE_NON_ENDGAME }}
            aria-hidden="true"
          />
          Non-endgame
        </span>
      </div>
      <p className="text-xs text-muted-foreground text-center mt-1">
        Week (rolling average of the last {window} games per side)
      </p>
    </div>
  );
}

