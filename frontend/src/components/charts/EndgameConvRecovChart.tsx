/**
 * Per-type Conversion & Recovery mini-gauge cards (260501-s0u).
 *
 * Replaces the grouped bar chart with six per-type cards, each showing two
 * EndgameGauge instances using per-type typical bands from PER_CLASS_GAUGE_ZONES.
 */

import { InfoPopover } from '@/components/ui/info-popover';
import { EndgameGauge } from '@/components/charts/EndgameGauge';
import {
  colorizeGaugeZones,
  MIN_GAMES_FOR_RELIABLE_STATS,
} from '@/lib/theme';
import {
  PER_CLASS_GAUGE_ZONES,
  type EndgameClassKey,
} from '@/generated/endgameZones';
import { MATERIAL_ADVANTAGE_POINTS, PERSISTENCE_MOVES } from '@/components/charts/EndgamePerformanceSection';
import type { EndgameCategoryStats } from '@/types/endgames';

interface EndgameConvRecovChartProps {
  categories: EndgameCategoryStats[];
}

export function EndgameConvRecovChart({ categories }: EndgameConvRecovChartProps) {
  const activeCategories = categories.filter(
    (c) => c.conversion.conversion_games > 0 || c.conversion.recovery_games > 0,
  );

  return (
    <div data-testid="conv-recov-chart">
      <div className="mb-3">
        <h3 className="text-base font-semibold">
          <span className="inline-flex items-center gap-1">
            Conversion &amp; Recovery by Endgame Type
            <InfoPopover ariaLabel="Conversion and Recovery info" testId="conv-recov-chart-info" side="top">
              <div className="space-y-2">
                <p>
                  <strong>Conversion</strong>: percentage of endgame sequences per type with a
                  material advantage of at least {MATERIAL_ADVANTAGE_POINTS} point (persisted for
                  at least {PERSISTENCE_MOVES} moves) where you went on to win the game.
                </p>
                <p>
                  <strong>Recovery</strong>: percentage of endgame sequences per type with a
                  material deficit of at least {MATERIAL_ADVANTAGE_POINTS} point (persisted for
                  at least {PERSISTENCE_MOVES} moves) where you went on to draw or win the game.
                </p>
                <p>
                  Gauge zones are per-type typical bands sourced from pooled FlawChess benchmark
                  data. Blue = typical for that type, red = below, green = above. Zones differ by
                  type because each endgame type has its own natural distribution.
                </p>
              </div>
            </InfoPopover>
          </span>
        </h3>
        <p className="text-sm text-muted-foreground mt-1">
          Which endgame types you convert best and which you defend best, compared to type-specific baselines.
        </p>
      </div>

      {activeCategories.length === 0 ? (
        <p className="text-sm text-muted-foreground py-4">
          Not enough data for conversion/recovery analysis
        </p>
      ) : (
        <div
          className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4"
          data-testid="conv-recov-grid"
        >
          {activeCategories.map((cat) => {
            const classKey = cat.endgame_class as EndgameClassKey;
            const bands = PER_CLASS_GAUGE_ZONES[classKey];
            // noUncheckedIndexedAccess guard — should always exist for the six known classes
            if (!bands) return null;

            const [convLower, convUpper] = bands.conversion;
            const [recovLower, recovUpper] = bands.recovery;

            const convZones = colorizeGaugeZones([
              { from: 0, to: convLower },
              { from: convLower, to: convUpper },
              { from: convUpper, to: 1.0 },
            ]);
            const recovZones = colorizeGaugeZones([
              { from: 0, to: recovLower },
              { from: recovLower, to: recovUpper },
              { from: recovUpper, to: 1.0 },
            ]);

            const totalGames =
              cat.conversion.conversion_games + cat.conversion.recovery_games;
            const isSparse = totalGames > 0 && totalGames < MIN_GAMES_FOR_RELIABLE_STATS;

            return (
              <div
                key={cat.endgame_class}
                className="rounded border border-border p-4 space-y-3"
                data-testid={`class-gauge-${cat.endgame_class}`}
              >
                <div className="flex items-baseline justify-between">
                  <h4 className="text-sm font-medium">{cat.label}</h4>
                  {isSparse && (
                    <span className="text-xs text-muted-foreground tabular-nums">
                      n={totalGames}
                    </span>
                  )}
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <div className="flex flex-col items-center">
                    <div className="text-sm text-muted-foreground mb-1">Conversion (Win)</div>
                    <EndgameGauge
                      value={cat.conversion.conversion_pct}
                      maxValue={100}
                      label="Conversion"
                      zones={convZones}
                      size={130}
                    />
                  </div>
                  <div className="flex flex-col items-center">
                    <div className="text-sm text-muted-foreground mb-1">Recovery (Save)</div>
                    <EndgameGauge
                      value={cat.conversion.recovery_pct}
                      maxValue={100}
                      label="Recovery"
                      zones={recovZones}
                      size={130}
                    />
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
