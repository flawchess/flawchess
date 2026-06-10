/**
 * Phase 87.6 — Endgame ELO Timeline section.
 *
 * Three-line weekly timeline per (platform, time_control) combo plus one
 * signed band per combo:
 *   - bold bright stroke: Actual ELO (per-combo asof rating at each emitted date)
 *   - dashed fine stroke: Endgame ELO (actual ELO + spread/2)
 *   - dotted fine stroke: Non-Endgame ELO (actual ELO − spread/2)
 *   - signed band: green when Endgame ELO >= Non-Endgame ELO, red when below
 *
 * Phase 57.1 additions (carried forward):
 *   - Muted volume bars at the bottom ~20% of the chart canvas showing endgame
 *     games per ISO week summed across currently-visible combos.
 *   - Tooltip gains a "Games this week: N (visible combos)" top line.
 *
 * Phase 87.6 amendment (2026-05-17): the earlier 87.6 per-side FIDE Performance
 * Rating mapping is replaced by a logistic stretch anchored on Actual ELO:
 *     spread = 400 · log10((s_E / (1 − s_E)) / (s_N / (1 − s_N)))
 *     endgame_elo     = actual_elo + spread / 2
 *     non_endgame_elo = actual_elo − spread / 2
 * The midpoint property holds exactly: `endgame_elo + non_endgame_elo ==
 * 2 · actual_elo` for every point. UAT against prod showed the PR-direct
 * mapping violated this invariant in ~88% of weekly points.
 * See .planning/notes/endgame-elo-logistic-anchored.md for derivation.
 *
 * Recharts UAT pitfall (Phase 68, 260424-pc6): every <Area> and <Line> for
 * the chart must be a DIRECT child of <ComposedChart> (not inside <g> or
 * <React.Fragment>). Recharts' `findAllByType` in `generateCategoricalChart`
 * only inspects direct children's `type.displayName` — wrapping hides them
 * from the scan, so the series never registers with the chart axes and no
 * <path> is emitted. The flatMap contract here guarantees direct children.
 */

import { useState, useCallback, useMemo, useEffect, useId } from 'react';
import { ChartContainer, ChartTooltip, ChartLegend } from '@/components/ui/chart';
import { ComposedChart, Line, Area, Bar, CartesianGrid, XAxis, YAxis } from 'recharts';
import { InfoPopover } from '@/components/ui/info-popover';
import { CardHeader } from '@/components/ui/card';
import { ChartTooltipBox } from '@/components/ui/chart-tooltip-box';
import { createDateTickFormatter, formatDateWithYear, niceEloAxis } from '@/lib/utils';
import {
  ELO_COMBO_COLORS,
  ENDGAME_VOLUME_BAR_COLOR,
  SCORE_TIMELINE_FILL_ABOVE,
  SCORE_TIMELINE_FILL_BELOW,
} from '@/lib/theme';
import { signedBandGradient } from '@/lib/signedBandGradient';
import type { GradientStop } from '@/lib/signedBandGradient';
import { computePrimaryTc } from '@/lib/primaryTc';
import { MIN_GAMES_PER_TC_CARD } from '@/generated/endgameZones';
import { inactivityGapReferenceLines } from './InactivityGapReferenceLines';
import type { EndgameEloTimelineResponse, EloComboKey } from '@/types/endgames';

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

interface EndgameEloTimelineSectionProps {
  data: EndgameEloTimelineResponse | undefined;
  isLoading: boolean;
  isError: boolean;
}

// Human-readable labels per UI-SPEC §Combo display labels.
// Platform lowercase, time control title-cased, no abbreviations.
const COMBO_LABELS: Record<EloComboKey, string> = {
  chess_com_bullet: 'chess.com Bullet',
  chess_com_blitz: 'chess.com Blitz',
  chess_com_rapid: 'chess.com Rapid',
  chess_com_classical: 'chess.com Classical',
  lichess_bullet: 'lichess Bullet',
  lichess_blitz: 'lichess Blitz',
  lichess_rapid: 'lichess Rapid',
  lichess_classical: 'lichess Classical',
};

// Fallback color when a combo_key somehow doesn't match EloComboKey at runtime
// (shouldn't happen — backend is constrained — but satisfies noUncheckedIndexedAccess).
const FALLBACK_COMBO_COLOR = { bright: 'oklch(0.55 0.15 200)', dark: 'oklch(0.35 0.12 200)' };

function getComboColors(combo_key: string): { bright: string; dark: string } {
  return ELO_COMBO_COLORS[combo_key as EloComboKey] ?? FALLBACK_COMBO_COLOR;
}

function getComboLabel(combo_key: string): string {
  return COMBO_LABELS[combo_key as EloComboKey] ?? combo_key;
}

// 260530-pll: replaced the old active-weeks/top-1-by-games heuristic with a
// primary-TC heuristic that aligns with EndgameMetricsByTcSection's accordion.
// All combos whose time_control equals the primary TC are visible by default
// (both platforms when both were played). Other-TC combos start hidden.
//
// Fallback: if computePrimaryTc returns null (no TC clears MIN_GAMES_PER_TC_CARD),
// nothing is hidden — show everything to avoid a blank chart.

function computeDefaultHiddenByPrimaryTc(
  combos: ReadonlyArray<{
    combo_key: string;
    time_control: string;
    points: ReadonlyArray<{ per_week_total_games: number }>;
  }>,
): Set<string> {
  // Build per-TC summed totals for computePrimaryTc: sum per_week_total_games
  // across all points for each combo, then aggregate across both platforms per TC.
  const byTc: Record<string, { total: number }[]> = {};
  for (const combo of combos) {
    let total = 0;
    for (const pt of combo.points) total += pt.per_week_total_games;
    const tc = combo.time_control;
    const existing = byTc[tc];
    if (existing) {
      existing.push({ total });
    } else {
      byTc[tc] = [{ total }];
    }
  }
  const primaryTc = computePrimaryTc(byTc, MIN_GAMES_PER_TC_CARD);
  if (!primaryTc) {
    // No TC clears the floor — fall back to showing everything.
    return new Set<string>();
  }
  const hidden = new Set<string>();
  for (const combo of combos) {
    if (combo.time_control !== primaryTc) {
      hidden.add(combo.combo_key);
    }
  }
  return hidden;
}

export function EndgameEloTimelineSection({
  data,
  isLoading,
  isError,
}: EndgameEloTimelineSectionProps) {
  const isMobile = useIsMobile();
  // One Set keyed by combo_key — toggles ALL four chart elements (3 Lines + 1 Area) of
  // a combo as a unit. The hide={isHidden} prop on each element uses the same lookup.
  // Seeded from `computeDefaultHidden(data.combos)` so rarely-played combos start
  // hidden; React's "adjust state during render" pattern (below) resets the default
  // whenever the combo set changes (user picked different filters, new data
  // arrived). User toggles within a single dataset are preserved because the
  // signature only changes when the underlying combo list does.
  const comboSignature = useMemo(
    () => (data?.combos ?? []).map((c) => c.combo_key).sort().join('|'),
    [data?.combos],
  );
  const [hiddenKeys, setHiddenKeys] = useState<Set<string>>(() =>
    computeDefaultHiddenByPrimaryTc(data?.combos ?? []),
  );
  const [hiddenSignature, setHiddenSignature] = useState<string>(comboSignature);
  if (hiddenSignature !== comboSignature) {
    setHiddenSignature(comboSignature);
    setHiddenKeys(computeDefaultHiddenByPrimaryTc(data?.combos ?? []));
  }

  // Per-component useId for gradient IDs. The baseGradientId is suffixed per-combo
  // with `_${combo.combo_key}` to avoid SVG ID collisions across up to 8 combos.
  // useId() returns a stable per-mount unique string (e.g. ":r3:"); the regex strips
  // non-alphanumeric chars because SVG `id` must match XML NCName rules — `url(#:r3:)`
  // fails to resolve in some browsers. See research §3b.
  const rawId = useId();
  const baseGradientId = `endgame-elo-band-${rawId.replace(/[^a-zA-Z0-9]/g, '_')}`;

  const handleLegendClick = useCallback((dataKey: string) => {
    setHiddenKeys((prev) => {
      const next = new Set(prev);
      if (next.has(dataKey)) {
        next.delete(dataKey);
      } else {
        next.add(dataKey);
      }
      return next;
    });
  }, []);

  // Deduped sorted date union across all combo points. Hooks must run on every
  // render, so the `data` prop is guarded via `?? []` instead of gating with an
  // early return before the hook executes.
  const allDates = useMemo(() => {
    const set = new Set<string>();
    for (const combo of data?.combos ?? []) {
      for (const pt of combo.points) {
        set.add(pt.date);
      }
    }
    return [...set].sort();
  }, [data?.combos]);

  const formatDateTick = useMemo(() => createDateTickFormatter(allDates), [allDates]);

  // Y-axis over all visible ELO values (endgame_elo + non_endgame_elo + actual_elo)
  // for non-hidden combos. All three lines must fit in the axis envelope.
  const yAxis = useMemo(() => {
    const values: number[] = [];
    for (const combo of data?.combos ?? []) {
      if (hiddenKeys.has(combo.combo_key)) continue;
      for (const pt of combo.points) {
        values.push(pt.endgame_elo, pt.non_endgame_elo, pt.actual_elo);
      }
    }
    return niceEloAxis(values);
  }, [data?.combos, hiddenKeys]);

  // Merged chart rows: one row per date with per-combo fields:
  //   {combo_key}_endgame_elo, {combo_key}_non_endgame_elo, {combo_key}_actual_elo,
  //   {combo_key}_games_in_window, {combo_key}_per_week_games,
  //   {combo_key}_band: [min(endgame_elo, non_endgame_elo), max(...)]
  // The band tuple drives the <Area> series. TypeScript's row type includes
  // [number, number] to allow the tuple value.
  const chartData = useMemo(() => {
    return allDates.map((date) => {
      const row: Record<string, string | number | [number, number] | undefined> = { date };
      for (const combo of data?.combos ?? []) {
        const pt = combo.points.find((p) => p.date === date);
        if (pt) {
          row[`${combo.combo_key}_endgame_elo`] = pt.endgame_elo;
          row[`${combo.combo_key}_non_endgame_elo`] = pt.non_endgame_elo;
          row[`${combo.combo_key}_actual_elo`] = pt.actual_elo;
          row[`${combo.combo_key}_games_in_window`] = pt.endgame_games_in_window;
          // per_week_total_games (endgame + non-endgame) drives the volume bars
          // and tooltip count — the chart plots BOTH Endgame ELO and Non-Endgame
          // ELO, so total weekly activity is what feeds both lines. Matches the
          // Endgame Score Gap over Time chart's bars (UAT 2026-05-17).
          row[`${combo.combo_key}_per_week_games`] = pt.per_week_total_games;
          row[`${combo.combo_key}_band`] = [
            Math.min(pt.endgame_elo, pt.non_endgame_elo),
            Math.max(pt.endgame_elo, pt.non_endgame_elo),
          ];
        }
        // undefined produces a gap that `connectNulls` bridges.
      }
      return row;
    });
  }, [allDates, data?.combos]);

  // Volume bars: per-row aggregate of per_week_total_games (endgame +
  // non-endgame) across currently-visible combos. Recomputes on legend toggle
  // so hidden combos are excluded from the sum (CONTEXT D-09). Pre-UAT
  // 2026-05-17 this used per_week_endgame_games and so undercounted the games
  // feeding the Non-Endgame ELO line; matches the Endgame Score Gap over Time
  // chart's bars now.
  //
  // Explicit return type keeps the Record<string, ...> index signature alive
  // after the spread — without it TypeScript narrows to `{ per_week_total_visible }`
  // and the tooltip's per-combo lookups lose their typing.
  const barChartData = useMemo<
    Array<Record<string, string | number | [number, number] | undefined> & { per_week_total_visible: number }>
  >(() => {
    return chartData.map((row) => {
      let total = 0;
      for (const combo of data?.combos ?? []) {
        if (hiddenKeys.has(combo.combo_key)) continue;
        const n = row[`${combo.combo_key}_per_week_games`];
        if (typeof n === 'number') total += n;
      }
      return { ...row, per_week_total_visible: total };
    });
  }, [chartData, data?.combos, hiddenKeys]);

  // Bar Y-axis envelope. domain={[0, barMax * 5]} pins the tallest bar to the
  // bottom 20% of the chart canvas (Pattern 3 in 57.1-RESEARCH.md).
  const barMax = useMemo(() => {
    let m = 0;
    for (const row of barChartData) {
      const v = row.per_week_total_visible;
      if (typeof v === 'number' && v > m) m = v;
    }
    return Math.max(m, 1);
  }, [barChartData]);

  // Per-combo gradient stops for the signed band. Recomputes when combos change.
  // signedBandGradient is a pure function — O(N) per combo, cached via useMemo.
  const gradientStopsByCombo = useMemo(() => {
    const out: Record<string, GradientStop[]> = {};
    for (const combo of data?.combos ?? []) {
      const rows = combo.points.map((p, i) => ({
        x: i,
        sign: Math.sign(p.endgame_elo - p.non_endgame_elo) as 1 | -1 | 0,
      }));
      out[combo.combo_key] = signedBandGradient(
        rows,
        [0, Math.max(0, combo.points.length - 1)],
        { positive: SCORE_TIMELINE_FILL_ABOVE, negative: SCORE_TIMELINE_FILL_BELOW },
      );
    }
    return out;
  }, [data?.combos]);

  // Phase 87.6 amendment: popover copy follows CLAUDE.md popover minimalism
  // (WHAT + sign convention only; no jargon, no caveats). Minimum text-sm.
  const infoPopover = (
    <InfoPopover
      ariaLabel="Endgame ELO Timeline info"
      testId="endgame-elo-timeline-info"
      side="top"
    >
      <div className="space-y-2">
        <p>
          <strong>Endgame ELO Timeline:</strong> your Endgame ELO (dashed line)
          and Non-Endgame ELO (dotted line) over time, derived from your
          Endgame Score Gap. See the "Endgame Statistics Concepts" section at
          the top of the page for details.
        </p>
        <p>
          The band between them is your endgame's lift (green) or drag (red).
          When the dashed line sits above the dotted line, your endgame is
          pulling your rating up; below, it's holding it back.
        </p>
      </div>
    </InfoPopover>
  );

  // Card header band: recessed background + bottom separator, full-bleed to the
  // card edges (matches EndgameMetricsByTcCard / EndgameTimePressureCard). The
  // subtitle moves into the padded body below, rendered by each branch.
  const headerBand = (
    <CardHeader data-testid="endgame-elo-timeline-header">
      Endgame ELO Timeline
      {infoPopover}
    </CardHeader>
  );
  const subtitle = (
    <p className="text-sm text-muted-foreground mb-3">
      Is your endgame lifting your ELO rating, or holding it back? Green band: Endgame Score is higher than Non-Endgame Score. Red band: Endgame Score is lower.
    </p>
  );

  // Error branch FIRST (before loading) — if the overview query errored, the
  // component-level error UI is reached per UI-SPEC §Copywriting Contract.
  // Copy is LOCKED: heading + body exactly as specified; testid is LOCKED too.
  if (isError) {
    return (
      <div
        className="flex flex-col items-center justify-center p-8 text-center"
        data-testid="endgame-elo-timeline-error"
      >
        <p className="mb-2 text-base font-medium text-foreground">
          Failed to load Endgame ELO timeline
        </p>
        <p className="text-sm text-muted-foreground">
          Something went wrong. Please try again in a moment.
        </p>
      </div>
    );
  }

  // Loading skeleton: matches the `h-72` chart footprint so layout doesn't jump
  // when data arrives. Uses `animate-pulse` blocks matching the existing pattern.
  if (isLoading || !data) {
    return (
      <div>
        {headerBand}
        <div className="p-4">
          {subtitle}
          <div className="h-72 flex flex-col gap-2" aria-busy="true" aria-live="polite">
            <div className="flex-1 bg-muted animate-pulse rounded" />
            <div className="h-6 bg-muted animate-pulse rounded w-3/4 self-center" />
          </div>
        </div>
      </div>
    );
  }

  // Empty state: no qualifying combos. Keep heading + info popover visible.
  if (data.combos.length === 0) {
    return (
      <div>
        {headerBand}
        <div className="p-4">
          {subtitle}
          <div
            className="text-center text-muted-foreground py-8"
            data-testid="endgame-elo-timeline-empty"
          >
            <p className="font-medium">Not enough endgame games yet for a timeline.</p>
            <p className="text-sm mt-1">Import more games or loosen the recency filter.</p>
          </div>
        </div>
      </div>
    );
  }

  // Chart config — one entry per combo (legend renders per combo, not per line).
  const chartConfig = Object.fromEntries(
    data.combos.map((combo) => {
      const colors = getComboColors(combo.combo_key);
      return [
        combo.combo_key,
        {
          label: getComboLabel(combo.combo_key),
          color: colors.bright,
        },
      ];
    }),
  );

  // Custom legend renderer — wraps each combo in a <button> carrying the locked
  // per-item testid (`endgame-elo-legend-{combo_key}`). All three lines render in
  // the combo's bright color; the band color is sign-derived, not combo-derived.
  // A single full-color swatch represents all three lines.
  const renderLegend = () => (
    <div className="flex flex-wrap gap-x-3 gap-y-1 text-xs pt-3 justify-center">
      {data.combos.map((combo) => {
        const colors = getComboColors(combo.combo_key);
        const isHidden = hiddenKeys.has(combo.combo_key);
        const comboLabel = getComboLabel(combo.combo_key);
        return (
          <button
            key={combo.combo_key}
            type="button"
            onClick={() => handleLegendClick(combo.combo_key)}
            className={`inline-flex min-w-0 items-center gap-1.5 cursor-pointer ${isHidden ? 'opacity-50 line-through' : ''}`}
            data-testid={`endgame-elo-legend-${combo.combo_key}`}
            aria-pressed={!isHidden}
          >
            {/* Single bright swatch — all three PR/Actual lines use colors.bright. */}
            <span
              className="h-2 w-2 shrink-0 rounded-[2px]"
              style={{ backgroundColor: colors.bright }}
            />
            <span className="truncate">{comboLabel}</span>
          </button>
        );
      })}
    </div>
  );

  return (
    <div>
      {headerBand}
      <div className="p-4">
      {subtitle}
      <div className={isMobile ? '' : 'flex items-stretch'}>
        {!isMobile && (
          <div
            className="flex items-center text-xs text-muted-foreground shrink-0 pt-40 -mr-1"
            style={{ writingMode: 'vertical-rl', transform: 'rotate(180deg)' }}
          >
            ELO
          </div>
        )}
        <ChartContainer
          config={chartConfig}
          className="w-full h-72"
          data-testid="endgame-elo-timeline-chart"
        >
          <ComposedChart
            data={barChartData}
            margin={{ top: 5, right: 10, left: isMobile ? 0 : 10, bottom: 10 }}
          >
            {/* recharts 3: CartesianGrid must bind to the named primary YAxis via yAxisId */}
            <CartesianGrid vertical={false} yAxisId="elo" />
            <XAxis dataKey="date" tickFormatter={formatDateTick} tick={{ fontSize: 12 }} />
            <YAxis
              yAxisId="elo"
              domain={yAxis.domain}
              ticks={yAxis.ticks}
              interval={0}
              tick={{ fontSize: 12 }}
              width={44}
            />
            {/* Phase 57.1: hidden right Y-axis dedicated to volume bars.
                domain={[0, barMax * 5]} pins the tallest bar to the bottom 20%
                of the chart canvas (Pattern 3 in 57.1-RESEARCH.md). */}
            <YAxis yAxisId="bars" orientation="right" hide domain={[0, barMax * 5]} />
            <ChartTooltip
              content={({ active, label }) => {
                if (!active) return null;
                const visibleCombos = data.combos.filter(
                  (c) => !hiddenKeys.has(c.combo_key),
                );
                const dateRow = barChartData.find((r) => r.date === (label as string));
                if (!dateRow) return null;
                const perWeekTotal =
                  (dateRow.per_week_total_visible as number | undefined) ?? 0;
                return (
                  <ChartTooltipBox>
                    <div className="font-medium">{formatDateWithYear(label as string)}</div>
                    <div className="text-muted-foreground">
                      Games this week: {perWeekTotal}
                    </div>
                    {visibleCombos.map((combo) => {
                      const endgameElo = dateRow[`${combo.combo_key}_endgame_elo`] as number | undefined;
                      const nonEndgameElo = dateRow[`${combo.combo_key}_non_endgame_elo`] as number | undefined;
                      const actual = dateRow[`${combo.combo_key}_actual_elo`] as number | undefined;
                      const games = dateRow[`${combo.combo_key}_games_in_window`] as number | undefined;
                      if (endgameElo === undefined || nonEndgameElo === undefined || actual === undefined) return null;
                      const colors = getComboColors(combo.combo_key);
                      const comboLabel = getComboLabel(combo.combo_key);
                      return (
                        <div key={combo.combo_key} className="pt-1">
                          <div className="font-medium">{comboLabel}</div>
                          <div className="flex items-center gap-1.5">
                            <span
                              className="h-2 w-2 shrink-0 rounded-[2px]"
                              style={{ backgroundColor: colors.bright }}
                            />
                            <span>
                              Endgame ELO: {endgameElo}
                              {games !== undefined && (
                                <span className="text-muted-foreground ml-1">(past {games} games)</span>
                              )}
                            </span>
                          </div>
                          <div className="flex items-center gap-1.5">
                            <span
                              className="h-2 w-2 shrink-0 rounded-[2px]"
                              style={{ backgroundColor: colors.bright }}
                            />
                            <span>Actual ELO: {actual}</span>
                          </div>
                          <div className="flex items-center gap-1.5">
                            <span
                              className="h-2 w-2 shrink-0 rounded-[2px]"
                              style={{ backgroundColor: colors.bright }}
                            />
                            <span>
                              Non-Endgame ELO: {nonEndgameElo}
                              {games !== undefined && (
                                <span className="text-muted-foreground ml-1">(past {games} games)</span>
                              )}
                            </span>
                          </div>
                        </div>
                      );
                    })}
                  </ChartTooltipBox>
                );
              }}
            />
            {/* Custom legend: each item is a <button> with the locked per-combo testid. */}
            <ChartLegend content={renderLegend()} />
            {/* Inactivity-gap annotations via shared helper: one ReferenceLine + Palmtree
                glyph + label per gap in allDates that exceeds INACTIVITY_GAP_THRESHOLD_DAYS.
                Placed BEFORE <Bar> so annotations sit behind the data series in SVG z-order.
                Uses yAxisId="elo" (the named ELO axis for this chart — not "value").
                x must exactly match a value from allDates (Recharts Pitfall 1). */}
            {inactivityGapReferenceLines({ dates: allDates, yAxisId: 'elo' })}
            {/* Phase 57.1: muted volume bars bound to the hidden bars axis. */}
            <Bar
              yAxisId="bars"
              dataKey="per_week_total_visible"
              fill={ENDGAME_VOLUME_BAR_COLOR}
              legendType="none"
              isAnimationActive={false}
              data-testid="endgame-elo-volume-bars"
            />
            {/* Per-combo gradient definitions for the signed bands.
                Single <defs> block containing all per-combo <linearGradient> children.
                This MUST appear before the flatMap series below in document order so the
                gradients are defined before any <Area> references them via url(#...). */}
            <defs>
              {data.combos.map((combo) => {
                const stops = gradientStopsByCombo[combo.combo_key] ?? [];
                return (
                  <linearGradient
                    key={combo.combo_key}
                    id={`${baseGradientId}_${combo.combo_key}`}
                    x1="0"
                    y1="0"
                    x2="1"
                    y2="0"
                  >
                    {stops.map((stop, i) => (
                      <stop key={i} offset={`${stop.offset}%`} stopColor={stop.color} />
                    ))}
                  </linearGradient>
                );
              })}
            </defs>
            {/* flatMap (NOT React.Fragment) — Recharts 2.15.x traverses React.Children
                to discover <Line> and <Area> instances, and Fragment wrappers are
                historically unreliable inside chart children. A flat array ensures
                every series element is a direct child of <ComposedChart>.
                Phase 57.1: every series gains yAxisId="elo" so it binds to the
                named Elo axis.
                Document order = SVG z-order: Area (band, lowest) → fine Endgame ELO
                Line → fine Non-Endgame ELO Line → bold Actual ELO Line (top). */}
            {data.combos.flatMap((combo) => {
              const colors = getComboColors(combo.combo_key);
              const isHidden = hiddenKeys.has(combo.combo_key);
              return [
                // 1. Signed band (lowest z-order)
                <Area
                  yAxisId="elo"
                  key={`${combo.combo_key}_band`}
                  type="monotone"
                  dataKey={`${combo.combo_key}_band`}
                  name={combo.combo_key}
                  stroke="none"
                  fill={`url(#${baseGradientId}_${combo.combo_key})`}
                  connectNulls={true}
                  hide={isHidden}
                  isAnimationActive={false}
                  legendType="none"
                />,
                // 2. Fine Endgame ELO line (PR on endgame games) — dashed
                //    UAT 2026-05-17: dashed vs dotted distinguishes the two
                //    PR lines for users (combo color is shared with Actual ELO).
                <Line
                  yAxisId="elo"
                  key={`${combo.combo_key}_endgame_elo`}
                  type="monotone"
                  dataKey={`${combo.combo_key}_endgame_elo`}
                  name={combo.combo_key}
                  stroke={colors.bright}
                  strokeWidth={1.25}
                  strokeDasharray="6 3"
                  dot={false}
                  connectNulls={true}
                  hide={isHidden}
                  isAnimationActive={false}
                  legendType="none"
                />,
                // 3. Fine Non-Endgame ELO line (PR on non-endgame games) — dotted
                <Line
                  yAxisId="elo"
                  key={`${combo.combo_key}_non_endgame_elo`}
                  type="monotone"
                  dataKey={`${combo.combo_key}_non_endgame_elo`}
                  name={combo.combo_key}
                  stroke={colors.bright}
                  strokeWidth={1.25}
                  strokeDasharray="1 3"
                  strokeLinecap="round"
                  dot={false}
                  connectNulls={true}
                  hide={isHidden}
                  isAnimationActive={false}
                  legendType="none"
                />,
                // 4. Bold Actual ELO line (highest z-order — stays readable through band)
                <Line
                  yAxisId="elo"
                  key={`${combo.combo_key}_actual_elo`}
                  type="monotone"
                  dataKey={`${combo.combo_key}_actual_elo`}
                  name={combo.combo_key}
                  stroke={colors.bright}
                  strokeWidth={2}
                  dot={false}
                  connectNulls={true}
                  hide={isHidden}
                  isAnimationActive={false}
                />,
              ];
            })}
          </ComposedChart>
        </ChartContainer>
      </div>
      </div>
    </div>
  );
}
