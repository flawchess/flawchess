/**
 * Phase 57 — Endgame ELO Timeline section.
 *
 * Paired-line weekly timeline per (platform, time_control) combo:
 *   - bright stroke: Endgame ELO (performance rating from skill composite)
 *   - dark dashed stroke: Actual ELO (rolling mean user_rating for same combo)
 *
 * Owns its own loading / error / empty / chart branches so the locked
 * component-level error UI (`endgame-elo-timeline-error`) is reachable per
 * UI-SPEC §Copywriting Contract. All visual decisions LOCKED in 57-UI-SPEC.md.
 */

import { useState, useCallback, useMemo } from 'react';
import { ChartContainer, ChartTooltip, ChartLegend } from '@/components/ui/chart';
import { LineChart, Line, CartesianGrid, XAxis, YAxis } from 'recharts';
import { InfoPopover } from '@/components/ui/info-popover';
import { createDateTickFormatter, formatDateWithYear, niceEloAxis } from '@/lib/utils';
import { ELO_COMBO_COLORS } from '@/lib/theme';
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

  const infoPopover = (
    <InfoPopover
      ariaLabel="Endgame ELO Timeline info"
      testId="endgame-elo-timeline-info"
      side="top"
    >
      <div className="space-y-2">
        <p>
          <strong>Endgame ELO</strong> is a performance rating derived from your
          Endgame Skill (the average of Conversion Win %, Parity Score %, and
          Recovery Save %). We compute it as
          <em> avg_opponent_rating + 400 &middot; log10(skill / (1 &minus; skill))</em>,
          using the rolling window's opponent pool for the skill and for the
          average opponent rating.
        </p>
        <p>
          The bright line is Endgame ELO, the dark line is your <strong>Actual ELO</strong>
          {' '}(average rating over the same rolling window of all games for that combo).
          The gap between the lines is the interesting signal: well above Actual ELO
          means your endgames are pulling your rating up; well below means they're
          pulling it down.
        </p>
        <p>
          Points are emitted weekly and each point looks back at your trailing 100
          endgame games for that platform and time control. Weeks with fewer than
          10 qualifying endgame games are hidden. Skill is clamped to the 5&ndash;95 %
          range so a handful of lucky or unlucky endgames can't produce an
          absurd performance rating at the extremes.
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
        Endgame ELO versus Actual ELO over time, per platform and time control.
        Bright lines are Endgame ELO, dark lines are Actual ELO.
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

  // Build merged chart rows: one row per date with {combo_key}_endgame_elo /
  // {combo_key}_actual_elo / {combo_key}_games_in_window columns.
  const chartData = allDates.map((date) => {
    const row: Record<string, string | number | undefined> = { date };
    for (const combo of data.combos) {
      const pt = combo.points.find((p) => p.date === date);
      if (pt) {
        row[`${combo.combo_key}_endgame_elo`] = pt.endgame_elo;
        row[`${combo.combo_key}_actual_elo`] = pt.actual_elo;
        row[`${combo.combo_key}_games_in_window`] = pt.endgame_games_in_window;
      }
      // undefined produces a gap that `connectNulls` bridges.
    }
    return row;
  });

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
        <LineChart data={chartData}>
          <CartesianGrid vertical={false} />
          <XAxis dataKey="date" tickFormatter={formatDateTick} tick={{ fontSize: 12 }} />
          <YAxis domain={yAxis.domain} ticks={yAxis.ticks} tick={{ fontSize: 12 }} />
          <ChartTooltip
            content={({ active, label }) => {
              if (!active) return null;
              // Group data by combo and filter out hidden combos.
              const visibleCombos = data.combos.filter(
                (c) => !hiddenKeys.has(c.combo_key),
              );
              const dateRow = chartData.find((r) => r.date === (label as string));
              if (!dateRow) return null;
              return (
                <div className="rounded-lg border border-border/50 bg-background px-3 py-2 text-xs shadow-xl space-y-1">
                  <div className="font-medium">{formatDateWithYear(label as string)}</div>
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
                          <span>Endgame ELO: {endgame}</span>
                        </div>
                        <div className="flex items-center gap-1.5">
                          <span
                            className="h-2 w-2 shrink-0 rounded-[2px]"
                            style={{ backgroundColor: colors.dark }}
                          />
                          <span>
                            Actual ELO: {actual}
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
          {/* flatMap (NOT React.Fragment) — Recharts 2.15.x traverses React.Children
              to discover <Line> instances, and Fragment wrappers are historically
              unreliable inside chart children. A flat array ensures every <Line>
              is a direct child of <LineChart>. */}
          {data.combos.flatMap((combo) => {
            const colors = getComboColors(combo.combo_key);
            const isHidden = hiddenKeys.has(combo.combo_key);
            return [
              <Line
                key={`${combo.combo_key}_endgame_elo`}
                type="monotone"
                dataKey={`${combo.combo_key}_endgame_elo`}
                name={combo.combo_key}
                stroke={colors.bright}
                strokeWidth={2}
                dot={false}
                connectNulls={true}
                hide={isHidden}
              />,
              <Line
                key={`${combo.combo_key}_actual_elo`}
                type="monotone"
                dataKey={`${combo.combo_key}_actual_elo`}
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
        </LineChart>
      </ChartContainer>
    </div>
  );
}
