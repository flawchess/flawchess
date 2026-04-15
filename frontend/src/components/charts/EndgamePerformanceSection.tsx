/**
 * Endgame Performance section:
 * - Endgame vs Non-Endgame WDL comparison table (games, WDL, score, score diff)
 *
 * Phase 59 removed the admin-only gauge charts (Conversion, Recovery, Endgame Skill);
 * the associated EndgameGaugesSection and its gauge-zone constants were deleted.
 */

import { InfoPopover } from '@/components/ui/info-popover';
import { MiniWDLBar } from '@/components/stats/MiniWDLBar';
import { MiniBulletChart } from '@/components/charts/MiniBulletChart';
import { ZONE_DANGER, ZONE_NEUTRAL, ZONE_SUCCESS } from '@/lib/theme';
import type {
  EndgamePerformanceResponse,
  ScoreGapMaterialResponse,
} from '@/types/endgames';

// Material advantage/deficit threshold in pawn points (backend uses 100 centipawns)
export const MATERIAL_ADVANTAGE_POINTS = 1;

// Persistence requirement in full moves (= 4 plies on the backend)
export const PERSISTENCE_MOVES = 2;

interface EndgamePerformanceSectionProps {
  data: EndgamePerformanceResponse;
  scoreGap?: ScoreGapMaterialResponse;
}

// Neutral zone around zero for the endgame-vs-non-endgame score difference
// bullet chart: ±0.05 marks near-parity between the two splits.
const SCORE_DIFF_NEUTRAL_MIN = -0.05;
const SCORE_DIFF_NEUTRAL_MAX = 0.05;

export function EndgamePerformanceSection({ data, scoreGap }: EndgamePerformanceSectionProps) {
  const totalGames = data.endgame_wdl.total + data.non_endgame_wdl.total;
  const endgamePct = totalGames > 0 ? (data.endgame_wdl.total / totalGames * 100).toFixed(1) : '0.0';
  const nonEndgamePct = totalGames > 0 ? (data.non_endgame_wdl.total / totalGames * 100).toFixed(1) : '0.0';

  const diffPositive = scoreGap ? scoreGap.score_difference >= 0 : false;
  const diffFormatted = scoreGap
    ? (diffPositive ? '+' : '') + scoreGap.score_difference.toFixed(2)
    : '';
  const diffColor = scoreGap
    ? scoreGap.score_difference >= SCORE_DIFF_NEUTRAL_MAX
      ? ZONE_SUCCESS
      : scoreGap.score_difference >= SCORE_DIFF_NEUTRAL_MIN
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
                <p>Compares your win/draw/loss rates in games that reached an endgame phase versus those that did not. Only endgames that span at least 3 full moves (6 half-moves) are counted — shorter tactical transitions from middlegame into a checkmate are treated as &quot;no endgame&quot;.</p>
                <p>The Score Difference column shows the signed gap between your endgame score and non-endgame score (green = endgame stronger, red = endgame weaker, blue = near parity).</p>
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
              <th className="py-1 px-2 font-medium">Score Difference</th>
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
                <td className="py-1.5 px-2 text-right text-xs tabular-nums text-muted-foreground whitespace-nowrap">
                  {row.score !== undefined ? row.score.toFixed(2) : '—'}
                </td>
                {scoreGap ? (
                  i === 0 ? (
                    <td
                      className="py-1.5 px-2 text-left text-sm tabular-nums whitespace-nowrap"
                      data-testid="score-gap-difference"
                    >
                      <span className="font-semibold" style={{ color: diffColor }}>{diffFormatted}</span>
                    </td>
                  ) : (
                    <td className="py-1.5 px-2 text-left">
                      <MiniBulletChart
                        value={scoreGap.score_difference}
                        neutralMin={SCORE_DIFF_NEUTRAL_MIN}
                        neutralMax={SCORE_DIFF_NEUTRAL_MAX}
                        ariaLabel={`Endgame score difference: ${diffFormatted}`}
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
            <div className="flex items-baseline justify-between text-xs">
              <span className="text-muted-foreground">Score</span>
              <span className="tabular-nums text-muted-foreground">
                {row.score !== undefined ? row.score.toFixed(2) : '—'}
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
              <div className="text-sm font-medium">Score Difference</div>
              <div className="text-xs tabular-nums text-muted-foreground">
                <span className="font-semibold" style={{ color: diffColor }}>{diffFormatted}</span>
              </div>
            </div>
            <MiniBulletChart
              value={scoreGap.score_difference}
              neutralMin={SCORE_DIFF_NEUTRAL_MIN}
              neutralMax={SCORE_DIFF_NEUTRAL_MAX}
              ariaLabel={`Endgame score difference: ${diffFormatted}`}
            />
          </div>
        )}
      </div>
    </div>
  );
}

