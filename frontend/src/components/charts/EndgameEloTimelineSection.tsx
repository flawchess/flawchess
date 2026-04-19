/**
 * Phase 57 — Endgame ELO Timeline section (revised Phase 57.1).
 *
 * Paired-line weekly timeline per (platform, time_control) combo:
 *   - bright stroke: Actual ELO (per-combo asof rating at each emitted date)
 *   - dark dashed stroke: Endgame ELO (skill-adjusted rating anchored on Actual ELO)
 *
 * Phase 57.1 additions:
 *   - Muted volume bars at the bottom ~20% of the chart canvas showing endgame
 *     games per ISO week summed across currently-visible combos (ComposedChart +
 *     hidden right Y-axis; Pattern 3 in 57.1-RESEARCH.md).
 *   - Tooltip gains a "Games this week: N (visible combos)" top line.
 *   - Info popover + subtitle rewritten per CONTEXT D-12/D-13/D-14/D-16.
 *
 * Owns its own loading / error / empty / chart branches so the locked
 * component-level error UI (`endgame-elo-timeline-error`) is reachable per
 * UI-SPEC §Copywriting Contract.
 */

import { useState, useCallback, useMemo } from 'react';
import { ChartContainer, ChartTooltip, ChartLegend } from '@/components/ui/chart';
import { ComposedChart, Line, Bar, CartesianGrid, XAxis, YAxis } from 'recharts';
import { InfoPopover } from '@/components/ui/info-popover';
import { createDateTickFormatter, formatDateWithYear, niceEloAxis } from '@/lib/utils';
import { ELO_COMBO_COLORS, ENDGAME_VOLUME_BAR_COLOR } from '@/lib/theme';
import type { EndgameEloTimelineResponse, EloComboKey } from '@/types/endgames';

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

export function EndgameEloTimelineSection({
  data,
  isLoading,
  isError,
}: EndgameEloTimelineSectionProps) {
  // One Set keyed by combo_key — toggles BOTH lines of a combo as a unit (UI-SPEC LOCKED).
  const [hiddenKeys, setHiddenKeys] = useState<Set<string>>(new Set());

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

  // Y-axis over all visible Elo values (endgame_elo + actual_elo) for non-hidden combos.
  const yAxis = useMemo(() => {
    const values: number[] = [];
    for (const combo of data?.combos ?? []) {
      if (hiddenKeys.has(combo.combo_key)) continue;
      for (const pt of combo.points) {
        values.push(pt.endgame_elo, pt.actual_elo);
      }
    }
    return niceEloAxis(values);
  }, [data?.combos, hiddenKeys]);

  // Merged chart rows: one row per date with {combo_key}_endgame_elo /
  // {combo_key}_actual_elo / {combo_key}_games_in_window / {combo_key}_per_week_games columns.
  // Promoted to useMemo (Phase 57.1) because barChartData below derives from it;
  // inline mapping would re-create the array every render.
  const chartData = useMemo(() => {
    return allDates.map((date) => {
      const row: Record<string, string | number | undefined> = { date };
      for (const combo of data?.combos ?? []) {
        const pt = combo.points.find((p) => p.date === date);
        if (pt) {
          row[`${combo.combo_key}_endgame_elo`] = pt.endgame_elo;
          row[`${combo.combo_key}_actual_elo`] = pt.actual_elo;
          row[`${combo.combo_key}_games_in_window`] = pt.endgame_games_in_window;
          row[`${combo.combo_key}_per_week_games`] = pt.per_week_endgame_games;
        }
        // undefined produces a gap that `connectNulls` bridges.
      }
      return row;
    });
  }, [allDates, data?.combos]);

  // Phase 57.1 volume bars: per-row aggregate of per_week_endgame_games across
  // currently-visible combos. Recomputes on legend toggle so hidden combos
  // are excluded from the sum (CONTEXT D-09).
  //
  // Explicit return type keeps the Record<string, ...> index signature alive
  // after the spread — without it TypeScript narrows to `{ per_week_total_visible }`
  // and the tooltip's `dateRow[`${combo}_endgame_elo`]` lookups lose their typing.
  const barChartData = useMemo<
    Array<Record<string, string | number | undefined> & { per_week_total_visible: number }>
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
  // Math.max(m, 1) avoids a [0, 0] domain when no week has any games.
  const barMax = useMemo(() => {
    let m = 0;
    for (const row of barChartData) {
      const v = row.per_week_total_visible;
      if (typeof v === 'number' && v > m) m = v;
    }
    return Math.max(m, 1);
  }, [barChartData]);

  const infoPopover = (
    <InfoPopover
      ariaLabel="Endgame ELO Timeline info"
      testId="endgame-elo-timeline-info"
      side="top"
    >
      <div className="space-y-2">
        <p>
          <strong>Endgame ELO</strong> is your Actual ELO shifted by how much your
          Endgame Skill exceeds (or falls short of) the 50% neutral mark. We compute it as
          <em> actual_elo + 400 &middot; log10(skill / (1 &minus; skill))</em>,
          where skill is the composite of Conversion Win %, Parity Score %, and
          Recovery Save % over your trailing 100 endgame games.
        </p>
        <p>
          The solid bright line is your <strong>Actual ELO</strong> &mdash; your rating at
          each date from the most recent game on or before that date. The dark dashed
          line is <strong>Endgame ELO</strong>. If your Endgame Skill is exactly 50%
          the two lines touch; 75% skill puts Endgame ELO roughly 190 Elo above,
          25% skill puts it roughly 190 Elo below. The gap between the lines is
          the interesting signal.
        </p>
        <p>
          Points are emitted weekly; each Endgame Skill value looks back at your
          trailing 100 endgame games for that platform and time control. Weeks with
          fewer than 10 qualifying endgame games are hidden.
          Skill is clamped to the 5&ndash;95% range so a handful of lucky or
          unlucky endgames can't produce an absurd rating shift at the extremes.
        </p>
        <p>
          Chess.com uses Glicko-1 and lichess uses Glicko-2, so ratings across the
          two platforms aren't directly comparable. Each combo line is self-consistent
          on its own scale.
        </p>
      </div>
    </InfoPopover>
  );

  const headingBlock = (
    <div className="mb-3">
      <h3 className="text-base font-semibold">
        <span className="inline-flex items-center gap-1">
          Endgame ELO Timeline
          {infoPopover}
        </span>
      </h3>
      <p className="text-sm text-muted-foreground mt-1">
        Is your endgame-skill-based ELO (dashed lines) lifting your actual ELO rating (solid lines), or holding it back?
      </p>
    </div>
  );

  // Error branch FIRST (before loading) — if the overview query errored, the
  // component-level error UI is reached per UI-SPEC §Copywriting Contract.
  // Copy is LOCKED: heading + body exactly as specified; testid is LOCKED too.
  if (isError) {
    return (
      <div
        className="flex flex-col items-center justify-center py-8 text-center"
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
  // when data arrives. Uses `animate-pulse` blocks matching the existing
  // MoveExplorer skeleton pattern.
  if (isLoading || !data) {
    return (
      <div>
        {headingBlock}
        <div className="h-72 flex flex-col gap-2" aria-busy="true" aria-live="polite">
          <div className="flex-1 bg-muted animate-pulse rounded" />
          <div className="h-6 bg-muted animate-pulse rounded w-3/4 self-center" />
        </div>
      </div>
    );
  }

  // Empty state: no qualifying combos. Keep heading + info popover visible.
  if (data.combos.length === 0) {
    return (
      <div>
        {headingBlock}
        <div
          className="text-center text-muted-foreground py-8"
          data-testid="endgame-elo-timeline-empty"
        >
          <p className="font-medium">Not enough endgame games yet for a timeline.</p>
          <p className="text-sm mt-1">Import more games or loosen the recency filter.</p>
        </div>
      </div>
    );
  }

  // Chart config — one entry per combo (legend renders per combo, not per line).
  // chartData / barChartData / barMax are computed via useMemo above the early
  // returns (hooks must run on every render).
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
  // per-item testid (`endgame-elo-legend-{combo_key}`). Recharts does not
  // propagate custom props to <Line> SVG output, so the testid MUST live on the
  // legend button (the user-clickable surface) rather than on <Line>.
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
            {/* Split-swatch: half bright / half dark to signal both line tones at a glance. */}
            <span
              className="h-2 w-2 shrink-0 rounded-[2px]"
              style={{
                background: `linear-gradient(to right, ${colors.bright} 50%, ${colors.dark} 50%)`,
              }}
            />
            <span className="truncate">{comboLabel}</span>
          </button>
        );
      })}
    </div>
  );

  return (
    <div>
      {headingBlock}
      <ChartContainer
        config={chartConfig}
        className="w-full h-72"
        data-testid="endgame-elo-timeline-chart"
      >
        <ComposedChart data={barChartData}>
          <CartesianGrid vertical={false} />
          <XAxis dataKey="date" tickFormatter={formatDateTick} tick={{ fontSize: 12 }} />
          <YAxis yAxisId="elo" domain={yAxis.domain} ticks={yAxis.ticks} tick={{ fontSize: 12 }} />
          {/* Phase 57.1: hidden right Y-axis dedicated to volume bars.
              domain={[0, barMax * 5]} pins the tallest bar to the bottom 20%
              of the chart canvas (Pattern 3 in 57.1-RESEARCH.md). */}
          <YAxis yAxisId="bars" orientation="right" hide domain={[0, barMax * 5]} />
          <ChartTooltip
            content={({ active, label }) => {
              if (!active) return null;
              // Group data by combo and filter out hidden combos.
              const visibleCombos = data.combos.filter(
                (c) => !hiddenKeys.has(c.combo_key),
              );
              const dateRow = barChartData.find((r) => r.date === (label as string));
              if (!dateRow) return null;
              const perWeekTotal =
                (dateRow.per_week_total_visible as number | undefined) ?? 0;
              return (
                <div className="rounded-lg border border-border/50 bg-background px-3 py-2 text-xs shadow-xl space-y-1">
                  <div className="font-medium">{formatDateWithYear(label as string)}</div>
                  <div className="text-muted-foreground">
                    Games this week: {perWeekTotal}
                  </div>
                  {visibleCombos.map((combo) => {
                    const endgame = dateRow[`${combo.combo_key}_endgame_elo`] as number | undefined;
                    const actual = dateRow[`${combo.combo_key}_actual_elo`] as number | undefined;
                    const games = dateRow[`${combo.combo_key}_games_in_window`] as number | undefined;
                    if (endgame === undefined || actual === undefined) return null;
                    const gap = endgame - actual;
                    const gapSign = gap > 0 ? '+' : '';
                    const colors = getComboColors(combo.combo_key);
                    // Renamed from `label` to `comboLabel` — the outer destructure
                    // already binds `label` to the Recharts x-axis tick value, and
                    // reusing the name would shadow it.
                    const comboLabel = getComboLabel(combo.combo_key);
                    return (
                      <div key={combo.combo_key} className="pt-1">
                        <div className="font-medium">{comboLabel}</div>
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
                            style={{ backgroundColor: colors.dark }}
                          />
                          <span>
                            Endgame ELO: {endgame}
                            <span className="text-muted-foreground ml-1">
                              gap {gapSign}{gap}
                              {games !== undefined && ` (past ${games} games)`}
                            </span>
                          </span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              );
            }}
          />
          {/* Custom legend: each item is a <button> with the locked per-combo
              testid. Pass `content={renderLegend()}` so Recharts renders the
              custom DOM (not ChartLegendContent's default grid). */}
          <ChartLegend content={renderLegend()} />
          {/* Phase 57.1: muted volume bars bound to the hidden bars axis.
              legendType="none" keeps the bar out of the combo legend.
              isAnimationActive={false} matches the existing line behavior. */}
          <Bar
            yAxisId="bars"
            dataKey="per_week_total_visible"
            fill={ENDGAME_VOLUME_BAR_COLOR}
            legendType="none"
            isAnimationActive={false}
            data-testid="endgame-elo-volume-bars"
          />
          {/* flatMap (NOT React.Fragment) — Recharts 2.15.x traverses React.Children
              to discover <Line> instances, and Fragment wrappers are historically
              unreliable inside chart children. A flat array ensures every <Line>
              is a direct child of <ComposedChart>.
              Phase 57.1: every <Line> gains yAxisId="elo" so it binds to the
              named Elo axis (once any yAxisId is declared, Recharts requires
              explicit IDs on every series — Pitfall 1 in 57.1-RESEARCH.md). */}
          {data.combos.flatMap((combo) => {
            const colors = getComboColors(combo.combo_key);
            const isHidden = hiddenKeys.has(combo.combo_key);
            return [
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
              />,
              <Line
                yAxisId="elo"
                key={`${combo.combo_key}_endgame_elo`}
                type="monotone"
                dataKey={`${combo.combo_key}_endgame_elo`}
                name={combo.combo_key}
                stroke={colors.dark}
                strokeWidth={1.5}
                strokeDasharray="4 2"
                dot={false}
                connectNulls={true}
                hide={isHidden}
                legendType="none"
              />,
            ];
          })}
        </ComposedChart>
      </ChartContainer>
    </div>
  );
}
