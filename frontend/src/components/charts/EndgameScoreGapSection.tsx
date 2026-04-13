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

interface EndgameScoreGapSectionProps {
  data: ScoreGapMaterialResponse;
}

export function EndgameScoreGapSection({ data }: EndgameScoreGapSectionProps) {
  const overallFormatted = data.overall_score.toFixed(2);
  const totalMaterialGames = data.material_rows.reduce((sum, r) => sum + r.games, 0);

  return (
    <div className="space-y-4" data-testid="score-gap-section">
      {/* Section header */}
      <h3 className="text-base font-semibold">
        <span className="inline-flex items-center gap-1">
          Endgame Material Breakdown
          <InfoPopover
            ariaLabel="Material Breakdown info"
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

      {/* Material-stratified WDL table */}
      <div className="overflow-x-auto">
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
              <th className="py-1 pr-3 font-medium">Material at entry</th>
              <th className="py-1 px-2 font-medium text-right">Games</th>
              <th className="py-1 px-2 font-medium">Win / Draw / Loss</th>
              <th className="py-1 px-2 font-medium text-right">
                Score (Diff)
              </th>
              <th className="py-1 px-2 font-medium">
                Score vs Overall ({overallFormatted})
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
                  <td className="py-1.5 pr-3 text-sm">{row.label}</td>
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
                      ariaLabel={`${row.label}: ${diffLabel} vs overall`}
                    />
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
