/**
 * Endgame Performance section:
 * - Endgame vs Non-Endgame WDL comparison table (games, WDL, score, score gap)
 *
 * Phase 59 removed the admin-only gauge charts (Conversion, Recovery, Endgame Skill);
 * the associated EndgameGaugesSection and its gauge-zone constants were deleted.
 *
 * Phase 85 (D-09): the score-over-time chart and its helpers were extracted
 * to a dedicated file; Plan 04 will delete the section function below, this
 * file is kept temporarily for that surgery.
 */

import { InfoPopover } from '@/components/ui/info-popover';
import { MiniWDLBar } from '@/components/stats/MiniWDLBar';
import { MiniBulletChart } from '@/components/charts/MiniBulletChart';
import {
  ZONE_DANGER,
  ZONE_NEUTRAL,
  ZONE_SUCCESS,
} from '@/lib/theme';
import {
  SCORE_GAP_NEUTRAL_MIN,
  SCORE_GAP_NEUTRAL_MAX,
} from '@/generated/endgameZones';
import type {
  EndgamePerformanceResponse,
  ScoreGapMaterialResponse,
} from '@/types/endgames';

interface EndgamePerformanceSectionProps {
  data: EndgamePerformanceResponse;
  scoreGap?: ScoreGapMaterialResponse;
}

// Bullet domain half-width for this metric. Population p05/p95 spans ~±0.16
// (see reports/benchmarks-2026-04-16.md §1), so ±0.20 covers the observed
// range without making typical values look tiny against the default ±0.40.
const SCORE_GAP_DOMAIN = 0.20;

export function EndgamePerformanceSection({ data, scoreGap }: EndgamePerformanceSectionProps) {
  const totalGames = data.endgame_wdl.total + data.non_endgame_wdl.total;
  const endgamePct = totalGames > 0 ? (data.endgame_wdl.total / totalGames * 100).toFixed(1) : '0.0';
  const nonEndgamePct = totalGames > 0 ? (data.non_endgame_wdl.total / totalGames * 100).toFixed(1) : '0.0';

  const gapPositive = scoreGap ? scoreGap.score_difference >= 0 : false;
  const gapFormatted = scoreGap
    ? (gapPositive ? '+' : '') + `${Math.round(scoreGap.score_difference * 100)}%`
    : '';
  const gapColor = scoreGap
    ? scoreGap.score_difference >= SCORE_GAP_NEUTRAL_MAX
      ? ZONE_SUCCESS
      : scoreGap.score_difference >= SCORE_GAP_NEUTRAL_MIN
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
    <div className="space-y-4" data-testid="endgame-performance-section">
      <div>
        <h3 className="text-base font-semibold">
          <span className="inline-flex items-center gap-1">
            Games with vs without Endgame
            <InfoPopover ariaLabel="Games with vs without Endgame info" testId="perf-section-info" side="top">
              <div className="space-y-2">
                <p>Compares your win/draw/loss rates in games that reached an endgame phase versus those that did not. Only endgames that span at least 3 full moves (6 half-moves) are counted. Shorter tactical transitions from middlegame into a checkmate are treated as &quot;no endgame&quot;.</p>
                <p>The <strong>Score Gap</strong> column shows the signed gap between your endgame Score and non-endgame Score (green = endgame stronger, red = endgame weaker, blue = near parity).</p>
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
              <th className="py-1 px-2 font-medium">Score Gap</th>
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
                <td className="py-1.5 px-2 text-right text-sm tabular-nums text-muted-foreground whitespace-nowrap">
                  {row.score !== undefined ? `${Math.round(row.score * 100)}%` : '—'}
                </td>
                {scoreGap ? (
                  i === 0 ? (
                    <td
                      className="py-1.5 px-2 text-left text-sm tabular-nums whitespace-nowrap"
                      data-testid="score-gap-difference"
                    >
                      <span className="font-semibold" style={{ color: gapColor }}>{gapFormatted}</span>
                    </td>
                  ) : (
                    <td className="py-1.5 px-2 text-left">
                      <MiniBulletChart
                        value={scoreGap.score_difference}
                        neutralMin={SCORE_GAP_NEUTRAL_MIN}
                        neutralMax={SCORE_GAP_NEUTRAL_MAX}
                        domain={SCORE_GAP_DOMAIN}
                        barColor="neutral"
                        ariaLabel={`Endgame vs non-endgame score gap: ${gapFormatted}`}
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
            <div className="flex items-baseline justify-between text-sm">
              <span className="text-muted-foreground">Score</span>
              <span className="tabular-nums text-muted-foreground">
                {row.score !== undefined ? `${Math.round(row.score * 100)}%` : '—'}
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
              <div className="text-sm font-medium">Score Gap</div>
              <div className="text-sm tabular-nums">
                <span className="font-semibold" style={{ color: gapColor }}>{gapFormatted}</span>
              </div>
            </div>
            <MiniBulletChart
              value={scoreGap.score_difference}
              neutralMin={SCORE_GAP_NEUTRAL_MIN}
              neutralMax={SCORE_GAP_NEUTRAL_MAX}
              domain={SCORE_GAP_DOMAIN}
              barColor="neutral"
              ariaLabel={`Endgame vs non-endgame score gap: ${gapFormatted}`}
            />
          </div>
        )}
      </div>
    </div>
  );
}
