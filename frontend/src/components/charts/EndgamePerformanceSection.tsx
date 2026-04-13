/**
 * Endgame Performance section (D-03 through D-07):
 * - Endgame vs Non-Endgame WDL comparison table (games, WDL, score, score diff)
 * - Three semicircle gauge charts (Conversion, Recovery, Endgame Skill) in a single row
 */

import { EndgameGauge, type GaugeZone } from '@/components/charts/EndgameGauge';
import { InfoPopover } from '@/components/ui/info-popover';
import { MiniWDLBar } from '@/components/stats/MiniWDLBar';
import { MiniBulletChart } from '@/components/charts/MiniBulletChart';
import { GAUGE_DANGER, GAUGE_WARNING, GAUGE_SUCCESS } from '@/lib/theme';
import type {
  EndgamePerformanceResponse,
  ScoreGapMaterialResponse,
} from '@/types/endgames';

// Material advantage/deficit threshold in pawn points (backend uses 100 centipawns)
export const MATERIAL_ADVANTAGE_POINTS = 1;

// Persistence requirement in full moves (= 4 plies on the backend)
export const PERSISTENCE_MOVES = 2;

// Per-gauge zone definitions — thresholds differ per metric, colors from theme constants
const CONVERSION_ZONES: GaugeZone[] = [
  { from: 0,    to: 0.5,  color: GAUGE_DANGER },
  { from: 0.5,  to: 0.7,  color: GAUGE_WARNING },
  { from: 0.7,  to: 1.0,  color: GAUGE_SUCCESS },
];

const RECOVERY_ZONES: GaugeZone[] = [
  { from: 0,    to: 0.15,  color: GAUGE_DANGER },
  { from: 0.15,  to: 0.35, color: GAUGE_WARNING },
  { from: 0.35, to: 1.0,  color: GAUGE_SUCCESS },
];

const ENDGAME_SKILL_ZONES: GaugeZone[] = [
  { from: 0,    to: 0.4,  color: GAUGE_DANGER },
  { from: 0.4,  to: 0.6,  color: GAUGE_WARNING },
  { from: 0.6,  to: 1.0,  color: GAUGE_SUCCESS },
];

interface EndgamePerformanceSectionProps {
  data: EndgamePerformanceResponse;
  scoreGap?: ScoreGapMaterialResponse;
}

interface EndgameGaugesSectionProps {
  data: EndgamePerformanceResponse;
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
      <h3 className="text-base font-semibold">
        <span className="inline-flex items-center gap-1">
          Games with vs without Endgame
          <InfoPopover ariaLabel="Games with vs without Endgame info" testId="perf-section-info" side="top">
            Compares your win/draw/loss rates in games that reached an endgame phase versus those that did not. The Score Difference column shows the signed gap between your endgame score and non-endgame score (green = endgame stronger, red = endgame weaker, narrow grey band = near parity).
          </InfoPopover>
        </span>
      </h3>

      <div className="overflow-x-auto">
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
                <td
                  className="py-1.5 px-2"
                  data-testid={i === 0 ? 'score-gap-difference' : undefined}
                >
                  {scoreGap && i === 0 && (
                    <span
                      className={
                        (diffPositive ? 'text-green-500' : 'text-red-500') +
                        ' font-semibold tabular-nums whitespace-nowrap'
                      }
                    >
                      {diffFormatted}
                    </span>
                  )}
                  {scoreGap && i === 1 && (
                    <MiniBulletChart
                      value={scoreGap.score_difference}
                      neutralMin={SCORE_DIFF_NEUTRAL_MIN}
                      neutralMax={SCORE_DIFF_NEUTRAL_MAX}
                      ariaLabel={`Endgame score difference: ${diffFormatted}`}
                    />
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

/**
 * Gauge charts for Conversion, Recovery, and Endgame Skill.
 * Split from EndgamePerformanceSection for layout flexibility.
 */
export function EndgameGaugesSection({ data }: EndgameGaugesSectionProps) {
  return (
    <div className="space-y-4">
      <h3 className="text-base font-semibold">
        Conversion, Recovery, and Endgame Skill
      </h3>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-6 sm:gap-4 mb-2" data-testid="perf-gauges">

        {/* Conversion gauge */}
        <div className="flex flex-col items-center gap-0">
          <div className="relative z-10 flex items-center gap-1 text-sm text-foreground text-center">
            <span>Conversion</span>
            <InfoPopover ariaLabel="Conversion info" testId="gauge-conversion-info" side="top">
              Percentage of endgame sequences with a material advantage of at least {MATERIAL_ADVANTAGE_POINTS} point (persisted for at least {PERSISTENCE_MOVES} moves) where you went on to win the game. Measures how well you close out winning endgames.
            </InfoPopover>
          </div>
          <EndgameGauge
            value={data.aggregate_conversion_pct}
            label="Conversion"
            zones={CONVERSION_ZONES}
          />
          <span className="-mt-1 text-xs text-muted-foreground">({data.aggregate_conversion_wins} of {data.aggregate_conversion_games} sequences)</span>
        </div>

        {/* Recovery gauge */}
        <div className="flex flex-col items-center gap-0">
          <div className="relative z-10 flex items-center gap-1 text-sm text-foreground text-center">
            <span>Recovery</span>
            <InfoPopover ariaLabel="Recovery info" testId="gauge-recovery-info" side="top">
              Percentage of endgame sequences with a material deficit of at least {MATERIAL_ADVANTAGE_POINTS} point (persisted for at least {PERSISTENCE_MOVES} moves) where you went on to draw or win the game. Measures how well you defend losing endgames.
            </InfoPopover>
          </div>
          <EndgameGauge
            value={data.aggregate_recovery_pct}
            label="Recovery"
            zones={RECOVERY_ZONES}
          />
          <span className="-mt-1 text-xs text-muted-foreground">({data.aggregate_recovery_saves} of {data.aggregate_recovery_games} sequences)</span>
        </div>

        {/* Endgame Skill gauge */}
        <div className="flex flex-col items-center gap-0">
          <div className="relative z-10 flex items-center gap-1 text-sm text-foreground text-center">
            <span>Endgame Skill</span>
            <InfoPopover ariaLabel="Endgame Skill info" testId="gauge-endgame-skill-info" side="top">
              A weighted average of your conversion rate (70%) and recovery rate (30%). Measures overall endgame proficiency.
            </InfoPopover>
          </div>
          <EndgameGauge
            value={data.endgame_skill}
            label="Endgame Skill"
            zones={ENDGAME_SKILL_ZONES}
          />
        </div>

      </div>
    </div>
  );
}
