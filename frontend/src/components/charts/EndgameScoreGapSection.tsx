/**
 * Endgame Score Gap & Material Breakdown section:
 * - Signed score difference (endgame score vs non-endgame score), green >= 0, red < 0
 * - Material-stratified WDL table: Ahead / Equal / Behind, with a mini bullet
 *   chart comparing each bucket's score to the user's overall score.
 */

import { InfoPopover } from '@/components/ui/info-popover';
import { MiniWDLBar } from '@/components/stats/MiniWDLBar';
import { MiniBulletChart } from '@/components/charts/MiniBulletChart';
import type { MaterialBucket, ScoreGapMaterialResponse } from '@/types/endgames';

// Per-bucket amber (neutral) zones for the bullet chart. Overall score is a
// weighted average across material situations, so the "expected" diff is not
// zero for every bucket: when ahead, users should outperform overall; when
// behind, underperforming overall is expected. Each zone is 0.10 wide.
const AMBER_ZONES: Record<MaterialBucket, { min: number; max: number }> = {
  ahead: { min: 0.05, max: 0.15 },     // converting advantage: neutral is +0 to +0.10
  equal: { min: -0.05, max: 0.05 }, // equal material: neutral is symmetric around 0
  behind: { min: -0.15, max: -0.05 },   // recovering: neutral is -0.10 to 0
};

interface EndgameScoreGapSectionProps {
  data: ScoreGapMaterialResponse;
}

export function EndgameScoreGapSection({ data }: EndgameScoreGapSectionProps) {
  const diffPositive = data.score_difference >= 0;
  const diffFormatted =
    (diffPositive ? '+' : '') + data.score_difference.toFixed(2);

  const overallFormatted = data.overall_score.toFixed(2);

  return (
    <div className="space-y-4" data-testid="score-gap-section">
      {/* Section header */}
      <h3 className="text-base font-semibold">
        <span className="inline-flex items-center gap-1">
          Endgame Score Gap &amp; Material Breakdown
          <InfoPopover
            ariaLabel="Score Gap info"
            testId="score-gap-section-info"
            side="top"
          >
            Compares your endgame score (wins + half draws) with your non-endgame
            score. The material table shows how your performance varies based on
            whether you entered endgames with a material advantage, equal material,
            or a deficit. The bar shows each bucket's score minus your overall
            score, with amber (neutral) zones calibrated per material context —
            when ahead you're expected to outperform overall, when behind you're
            expected to underperform, and when equal you should be near overall.
            Tick marks show the amber zone boundaries.
          </InfoPopover>
        </span>
      </h3>

      {/* Score difference display */}
      <div
        className="flex flex-col gap-1 rounded-md bg-muted/30 px-3 py-2"
        data-testid="score-gap-difference"
      >
        <div className="flex items-center justify-between">
          <span className="text-sm font-medium">Endgame Score Difference</span>
          <span
            className={
              diffPositive
                ? 'text-green-500 font-semibold text-base'
                : 'text-red-500 font-semibold text-base'
            }
          >
            {diffFormatted}
          </span>
        </div>
        <p className="text-xs text-muted-foreground">
          Endgame: {data.endgame_score.toFixed(2)} | Non-endgame:{' '}
          {data.non_endgame_score.toFixed(2)}
        </p>
      </div>

      {/* Material-stratified WDL table */}
      <div className="overflow-x-auto">
        <table
          className="w-full min-w-[520px] text-sm sm:text-base"
          data-testid="material-table"
        >
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
              const amberZone = AMBER_ZONES[row.bucket];
              return (
                <tr
                  key={row.bucket}
                  className={row.games === 0 ? 'opacity-50' : undefined}
                  data-testid={`material-row-${row.bucket}`}
                >
                  <td className="py-1.5 pr-3 text-sm">{row.label}</td>
                  <td className="py-1.5 px-2 text-right text-sm tabular-nums">
                    {row.games.toLocaleString()}
                  </td>
                  <td className="py-1.5 px-2 min-w-[120px]">
                    <MiniWDLBar
                      win_pct={row.win_pct}
                      draw_pct={row.draw_pct}
                      loss_pct={row.loss_pct}
                    />
                  </td>
                  <td className="py-1.5 px-2 text-right text-xs tabular-nums text-muted-foreground whitespace-nowrap">
                    {row.score.toFixed(2)} ({diffLabel})
                  </td>
                  <td className="py-1.5 px-2 min-w-[140px]">
                    <MiniBulletChart
                      value={diff}
                      amberMin={amberZone.min}
                      amberMax={amberZone.max}
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
