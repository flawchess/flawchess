/**
 * Endgame Score Gap & Material Breakdown section:
 * - Signed score difference (endgame score vs non-endgame score), green >= 0, red < 0
 * - Material-stratified WDL table: Ahead / Equal / Behind, with verdict badges
 */

import { InfoPopover } from '@/components/ui/info-popover';
import { MiniWDLBar } from '@/components/stats/MiniWDLBar';
import { WDL_WIN, WDL_LOSS, GAUGE_WARNING } from '@/lib/theme';
import type { ScoreGapMaterialResponse, Verdict } from '@/types/endgames';

// Verdict badge config — colors from theme constants, not hard-coded
const VERDICT_CONFIG: Record<Verdict, { label: string; color: string }> = {
  good: { label: 'Good', color: WDL_WIN },
  ok:   { label: 'OK',   color: GAUGE_WARNING },
  bad:  { label: 'Bad',  color: WDL_LOSS },
};

interface EndgameScoreGapSectionProps {
  data: ScoreGapMaterialResponse;
}

export function EndgameScoreGapSection({ data }: EndgameScoreGapSectionProps) {
  const diffPositive = data.score_difference >= 0;
  const diffFormatted =
    (diffPositive ? '+' : '') + data.score_difference.toFixed(3);

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
            or a deficit.
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
          Endgame: {data.endgame_score.toFixed(3)} | Non-endgame:{' '}
          {data.non_endgame_score.toFixed(3)}
        </p>
      </div>

      {/* Material-stratified WDL table */}
      <div className="overflow-x-auto">
        <table
          className="w-full min-w-[440px] text-sm sm:text-base"
          data-testid="material-table"
        >
          <thead>
            <tr className="text-left text-xs text-muted-foreground border-b border-border">
              <th className="py-1 pr-3 font-medium">Material at entry</th>
              <th className="py-1 px-2 font-medium text-right">Games</th>
              <th className="py-1 px-2 font-medium">Win / Draw / Loss</th>
              <th className="py-1 px-2 font-medium text-right">Score</th>
              <th className="py-1 pl-2 font-medium text-right">Verdict</th>
            </tr>
          </thead>
          <tbody>
            {data.material_rows.map((row) => {
              const config = VERDICT_CONFIG[row.verdict];
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
                    <MiniWDLBar win_pct={row.win_pct} draw_pct={row.draw_pct} loss_pct={row.loss_pct} />
                  </td>
                  <td className="py-1.5 px-2 text-right text-sm tabular-nums">
                    {row.score.toFixed(3)}
                  </td>
                  <td className="py-1.5 pl-2 text-right">
                    <span
                      className="inline-block rounded px-1.5 py-0.5 text-xs font-medium text-white"
                      style={{ backgroundColor: config.color }}
                    >
                      {config.label}
                    </span>
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
