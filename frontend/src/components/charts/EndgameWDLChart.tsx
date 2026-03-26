import { InfoPopover } from '@/components/ui/info-popover';
import { ChartContainer, ChartTooltip, ChartLegend, ChartLegendContent } from '@/components/ui/chart';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid } from 'recharts';
import { cn } from '@/lib/utils';
import type { EndgameCategoryStats, EndgameClass } from '@/types/endgames';

interface EndgameWDLChartProps {
  categories: EndgameCategoryStats[];
  selectedCategory: EndgameClass | null;
  onCategoryClick: (category: EndgameClass) => void;
}

const chartConfig = {
  win_pct: { label: 'Wins', color: 'oklch(0.50 0.14 145)' },
  draw_pct: { label: 'Draws', color: 'oklch(0.60 0.02 260)' },
  loss_pct: { label: 'Losses', color: 'oklch(0.50 0.15 25)' },
  game_count: { label: 'Games', color: 'transparent' },
};

// Map EndgameClass to slug used in data-testid
const CLASS_TO_SLUG: Record<EndgameClass, string> = {
  rook: 'rook',
  minor_piece: 'minor-piece',
  pawn: 'pawn',
  queen: 'queen',
  mixed: 'mixed',
  pawnless: 'pawnless',
};

function formatConversionMetric(pct: number, saves: number, games: number): string {
  if (games === 0) return '—';
  return `${pct.toFixed(0)}% (${saves}/${games})`;
}

export function EndgameWDLChart({ categories, selectedCategory, onCategoryClick }: EndgameWDLChartProps) {
  // Backend already sorts by total desc — transform for Recharts
  const data = categories.map((cat) => ({
    endgame_class: cat.endgame_class,
    label: cat.label,
    slug: CLASS_TO_SLUG[cat.endgame_class],
    win_pct: cat.win_pct,
    draw_pct: cat.draw_pct,
    loss_pct: cat.loss_pct,
    wins: cat.wins,
    draws: cat.draws,
    losses: cat.losses,
    total: cat.total,
    game_count: cat.total,
    conversion_pct: cat.conversion.conversion_pct,
    conversion_games: cat.conversion.conversion_games,
    conversion_wins: cat.conversion.conversion_wins,
    recovery_pct: cat.conversion.recovery_pct,
    recovery_games: cat.conversion.recovery_games,
    recovery_saves: cat.conversion.recovery_saves,
  }));

  return (
    <div data-testid="endgame-wdl-chart">
      <h2 className="text-lg font-medium mb-3">
        <span className="inline-flex items-center gap-1">
          Results by Endgame Type
          <InfoPopover ariaLabel="Results by endgame type info" testId="endgame-chart-info" side="top">
            Shows your win, draw, and loss percentages for each endgame type, based on games that reached that endgame.
            Conversion is your win rate when you entered the endgame with more material. Recovery is your draw+win rate
            when you entered with less material. Click a row to view the matching games.
          </InfoPopover>
        </span>
      </h2>

      {/* Per-category clickable rows with inline conversion/recovery metrics */}
      <div className="space-y-1">
        {data.map((cat) => {
          const isSelected = selectedCategory === cat.endgame_class;
          const conversionText = formatConversionMetric(cat.conversion_pct, cat.conversion_wins, cat.conversion_games);
          const recoveryText = formatConversionMetric(cat.recovery_pct, cat.recovery_saves, cat.recovery_games);

          return (
            <button
              key={cat.endgame_class}
              data-testid={`endgame-category-${cat.slug}`}
              aria-pressed={isSelected}
              aria-label={`${cat.label} endgame category`}
              onClick={() => onCategoryClick(cat.endgame_class)}
              className={cn(
                'w-full text-left rounded px-2 py-1.5 transition-colors cursor-pointer',
                isSelected
                  ? 'bg-muted/50 ring-1 ring-primary/40'
                  : 'hover:bg-muted/30',
              )}
            >
              {/* Category label and game count */}
              <div className="flex items-center justify-between mb-1">
                <span className="text-sm font-medium">{cat.label}</span>
                <span className="text-xs text-muted-foreground">{cat.total} games</span>
              </div>

              {/* Stacked WDL bar */}
              <div className="flex h-5 w-full overflow-hidden rounded mb-1">
                {cat.win_pct > 0 && (
                  <div
                    className="transition-all"
                    style={{ width: `${cat.win_pct}%`, backgroundColor: 'oklch(0.50 0.14 145)' }}
                  />
                )}
                {cat.draw_pct > 0 && (
                  <div
                    className="transition-all"
                    style={{ width: `${cat.draw_pct}%`, backgroundColor: 'oklch(0.60 0.02 260)' }}
                  />
                )}
                {cat.loss_pct > 0 && (
                  <div
                    className="transition-all"
                    style={{ width: `${cat.loss_pct}%`, backgroundColor: 'oklch(0.50 0.15 25)' }}
                  />
                )}
              </div>

              {/* WDL percentages */}
              <div className="flex gap-3 text-xs text-muted-foreground mb-1">
                <span style={{ color: 'oklch(0.50 0.14 145)' }}>W: {cat.win_pct.toFixed(0)}%</span>
                <span style={{ color: 'oklch(0.60 0.02 260)' }}>D: {cat.draw_pct.toFixed(0)}%</span>
                <span style={{ color: 'oklch(0.50 0.15 25)' }}>L: {cat.loss_pct.toFixed(0)}%</span>
              </div>

              {/* Inline conversion / recovery metrics per D-06, D-10 */}
              <p className="text-xs text-muted-foreground">
                Conversion: {conversionText} · Recovery: {recoveryText}
              </p>
            </button>
          );
        })}
      </div>

      {/* Hidden chart kept for legend — used only to provide chartConfig context if needed in future */}
      {/* The main visual is the custom per-row layout above for interactivity + inline metrics */}
      {data.length > 0 && (
        <div className="sr-only">
          <ChartContainer config={chartConfig} className="w-full" style={{ height: Math.max(120, data.length * 64 + 60) }}>
            <BarChart data={data} layout="vertical" margin={{ left: 8, right: 16 }}>
              <CartesianGrid horizontal={false} />
              <YAxis dataKey="label" type="category" width={120} tick={{ fontSize: 12 }} tickLine={false} axisLine={false} />
              <XAxis xAxisId="pct" type="number" domain={[0, 100]} ticks={[0, 25, 50, 75, 100]} tickFormatter={(v) => `${v}%`} tick={{ fontSize: 11 }} />
              <XAxis xAxisId="count" type="number" orientation="top" hide={true} />
              <ChartTooltip
                content={({ active, payload }) => {
                  if (!active || !payload?.length) return null;
                  const d = payload[0].payload;
                  return (
                    <div className="rounded-lg border border-border/50 bg-background px-3 py-2 text-xs shadow-xl space-y-1">
                      <div className="font-medium">{d.label}</div>
                      <div className="text-green-600">Wins: {d.wins} ({d.win_pct.toFixed(1)}%)</div>
                      <div className="text-gray-400">Draws: {d.draws} ({d.draw_pct.toFixed(1)}%)</div>
                      <div className="text-red-600">Losses: {d.losses} ({d.loss_pct.toFixed(1)}%)</div>
                      <div className="text-muted-foreground pt-0.5 border-t border-border/50">Total: {d.total} games</div>
                    </div>
                  );
                }}
              />
              <ChartLegend content={<ChartLegendContent />} />
              <Bar xAxisId="pct" dataKey="win_pct" stackId="wdl" fill="var(--color-win_pct)" />
              <Bar xAxisId="pct" dataKey="draw_pct" stackId="wdl" fill="var(--color-draw_pct)" />
              <Bar xAxisId="pct" dataKey="loss_pct" stackId="wdl" fill="var(--color-loss_pct)" />
              <Bar
                xAxisId="count"
                dataKey="game_count"
                name="Games"
                fill="transparent"
                shape={(props: unknown) => {
                  const { x, y, width, height } = props as { x: number; y: number; width: number; height: number };
                  return <rect x={x} y={y} width={width} height={height} fill="transparent" stroke="oklch(0.6 0 0)" strokeWidth={1} />;
                }}
              />
            </BarChart>
          </ChartContainer>
        </div>
      )}
    </div>
  );
}
