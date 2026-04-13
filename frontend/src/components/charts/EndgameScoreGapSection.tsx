/**
 * Endgame Score Gap & Material Breakdown section:
 * - Signed score difference (endgame score vs non-endgame score), green >= 0, red < 0
 * - Material-stratified WDL table: Conversion / Even / Recovery, with a mini
 *   bullet chart comparing each bucket's score to the user's overall score.
 *   Conversion/Recovery require the material imbalance to persist 4 plies into
 *   the endgame to filter out transient trade noise — games that don't persist
 *   fall into the Even bucket.
 */

import { InfoPopover } from '@/components/ui/info-popover';
import { MiniWDLBar } from '@/components/stats/MiniWDLBar';
import { MiniBulletChart } from '@/components/charts/MiniBulletChart';
import type { MaterialBucket, ScoreGapMaterialResponse } from '@/types/endgames';

// Per-bucket neutral zones for the bullet chart. Overall score is a
// weighted average across material situations, so the "expected" diff is not
// zero for every bucket: when converting, users should outperform overall;
// when recovering, underperforming overall is expected. Each zone is 0.10 wide.
const NEUTRAL_ZONES: Record<MaterialBucket, { min: number; max: number }> = {
  conversion: { min: 0.10, max: 0.20 },  // converting advantage
  even: { min: -0.05, max: 0.05 },       // even material: zone sits symmetric around 0
  recovery: { min: -0.20, max: -0.10 },  // recovering from deficit
};

// Short display names — the material indicator ("≥ +1", "≤ −1") lives in the
// section description, freeing column/card space (especially on mobile).
const BUCKET_DISPLAY_LABELS: Record<MaterialBucket, string> = {
  conversion: 'Conversion',
  even: 'Even',
  recovery: 'Recovery',
};

interface EndgameScoreGapSectionProps {
  data: ScoreGapMaterialResponse;
}

export function EndgameScoreGapSection({ data }: EndgameScoreGapSectionProps) {
  const overallFormatted = data.overall_score.toFixed(2);
  const totalMaterialGames = data.material_rows.reduce((sum, r) => sum + r.games, 0);

  return (
    <div className="space-y-4" data-testid="score-gap-section">
      {/* Section header */}
      <div>
        <h3 className="text-base font-semibold">
          <span className="inline-flex items-center gap-1">
            Endgame Conversion & Recovery
            <InfoPopover
              ariaLabel="Conversion & Recovery info"
              testId="material-breakdown-section-info"
              side="top"
            >
              The material table shows how your performance varies based on
              whether you entered endgames with a material advantage (Conversion),
              roughly even material (Even), or a deficit (Recovery). Conversion
              and Recovery require the imbalance to persist 4 plies into the
              endgame — transient imbalances from piece trades fall into Even.
              The bar shows each bucket's score minus your overall score, with
              warning zones calibrated per material context: when converting
              you're expected to outperform overall, when recovering you're
              expected to underperform, and when even you should be near overall.
              Tick marks show the warning zone boundaries.
            </InfoPopover>
          </span>
        </h3>
        <p className="text-sm text-muted-foreground mt-1">
          How you perform entering endgames with a material advantage
          (Conversion, ≥ +1 point), roughly even material (Even), or a
          material deficit (Recovery, ≤ −1 point).
        </p>
      </div>

      {/* Desktop: table layout */}
      <div className="hidden lg:block overflow-x-auto">
        <table
          className="w-full min-w-[720px] text-sm sm:text-base table-fixed"
          data-testid="material-table"
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
              <th className="py-1 pr-3 font-medium" aria-label="Material bucket" />
              <th className="py-1 px-2 font-medium text-right">Games</th>
              <th className="py-1 px-2 font-medium">Win / Draw / Loss</th>
              <th className="py-1 px-2 font-medium text-right">
                Score (Diff)
              </th>
              <th className="py-1 px-2 font-medium">
                Score vs Overall Score ({overallFormatted})
              </th>
            </tr>
          </thead>
          <tbody>
            {data.material_rows.map((row) => {
              const diff = row.score - data.overall_score;
              const diffLabel =
                (diff >= 0 ? '+' : '') + diff.toFixed(2);
              const neutralZone = NEUTRAL_ZONES[row.bucket];
              const pct =
                totalMaterialGames > 0
                  ? ((row.games / totalMaterialGames) * 100).toFixed(1)
                  : '0.0';
              return (
                <tr
                  key={row.bucket}
                  className={row.games === 0 ? 'opacity-50' : undefined}
                  data-testid={`material-row-${row.bucket}`}
                >
                  <td className="py-1.5 pr-3 text-sm">
                    {BUCKET_DISPLAY_LABELS[row.bucket]}
                  </td>
                  <td className="py-1.5 px-2 text-right text-sm tabular-nums whitespace-nowrap">
                    {pct}% ({row.games.toLocaleString()})
                  </td>
                  <td className="py-1.5 px-2">
                    <MiniWDLBar
                      win_pct={row.win_pct}
                      draw_pct={row.draw_pct}
                      loss_pct={row.loss_pct}
                    />
                  </td>
                  <td className="py-1.5 px-2 text-right text-xs tabular-nums text-muted-foreground whitespace-nowrap">
                    {row.score.toFixed(2)} ({diffLabel})
                  </td>
                  <td className="py-1.5 px-2">
                    <MiniBulletChart
                      value={diff}
                      neutralMin={neutralZone.min}
                      neutralMax={neutralZone.max}
                      ariaLabel={`${BUCKET_DISPLAY_LABELS[row.bucket]}: ${diffLabel} vs overall`}
                    />
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Mobile: stacked cards */}
      <div className="lg:hidden space-y-3" data-testid="material-cards">
        {data.material_rows.map((row) => {
          const diff = row.score - data.overall_score;
          const diffLabel = (diff >= 0 ? '+' : '') + diff.toFixed(2);
          const neutralZone = NEUTRAL_ZONES[row.bucket];
          const pct =
            totalMaterialGames > 0
              ? ((row.games / totalMaterialGames) * 100).toFixed(1)
              : '0.0';
          return (
            <div
              key={row.bucket}
              className={
                'rounded border border-border p-3 space-y-2' +
                (row.games === 0 ? ' opacity-50' : '')
              }
              data-testid={`material-card-${row.bucket}`}
            >
              <div className="flex items-baseline justify-between">
                <div className="text-sm font-medium">
                  {BUCKET_DISPLAY_LABELS[row.bucket]}
                </div>
                <div className="text-xs tabular-nums text-muted-foreground">
                  {pct}% ({row.games.toLocaleString()} games)
                </div>
              </div>
              <div>
                <div className="text-xs text-muted-foreground mb-1">
                  Win / Draw / Loss
                </div>
                <MiniWDLBar
                  win_pct={row.win_pct}
                  draw_pct={row.draw_pct}
                  loss_pct={row.loss_pct}
                />
              </div>
              <div>
                <div className="flex items-baseline justify-between text-xs mb-1">
                  <span className="text-muted-foreground">
                    Score vs Overall Score ({overallFormatted})
                  </span>
                  <span className="tabular-nums text-muted-foreground">
                    {row.score.toFixed(2)} ({diffLabel})
                  </span>
                </div>
                <MiniBulletChart
                  value={diff}
                  neutralMin={neutralZone.min}
                  neutralMax={neutralZone.max}
                  ariaLabel={`${BUCKET_DISPLAY_LABELS[row.bucket]}: ${diffLabel} vs overall`}
                />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
