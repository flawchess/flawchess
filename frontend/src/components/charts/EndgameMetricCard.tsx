/**
 * Phase 86 — Shared shell for the Conversion / Parity / Recovery cards of the
 * "Endgame Metrics" 4-card layout. Renders gauge → games-count row → WDL bar →
 * peer-bullet row (`You / Opp / Diff` text + `MiniBulletChart` for the signed
 * `userRate − opponentRate` vs 0).
 *
 * v1.17 single-bullet doctrine: per-card peer bullet vs 0 with the sig-gating
 * triple (`isConfident(deriveLevel(p, n)) ∧ outside-neutral-band ∧
 * n >= MIN_OPPONENT_BASELINE_GAMES`) applied to the diff-percent font color
 * only. Gauges stay always-colored; WDL bar stays untinted. (POLISH-01 /
 * POLISH-02 deferred to Phase 88.)
 */

import type { CSSProperties, ReactNode } from 'react';

import { Swords } from 'lucide-react';

import { MiniBulletChart } from '@/components/charts/MiniBulletChart';
import { EndgameGauge } from '@/components/charts/EndgameGauge';
import { MetricStatPopover } from '@/components/popovers/MetricStatPopover';
import { MiniWDLBar } from '@/components/stats/MiniWDLBar';
import { InfoPopover } from '@/components/ui/info-popover';
import { isConfident } from '@/lib/significance';
import { ZONE_DANGER, ZONE_SUCCESS } from '@/lib/theme';
import {
  BUCKET_DISPLAY_LABELS,
  BUCKET_DISPLAY_LABELS_WITH_METRIC,
  BULLET_DOMAIN,
  FIXED_GAUGE_ZONES,
  MIN_OPPONENT_BASELINE_GAMES,
  NEUTRAL_ZONE_MAX,
  NEUTRAL_ZONE_MIN,
  formatDiffPct,
  formatScorePct,
  opponentRate,
  userRate,
} from '@/lib/endgameMetrics';
import type { MaterialBucket, MaterialRow } from '@/types/endgames';

import { deriveLevel } from './EndgameOverallShared';

interface EndgameMetricCardProps {
  bucket: MaterialBucket;
  row: MaterialRow;
  /** Mirror-bucket row (Conv ↔ Recov, Parity ↔ Parity). Undefined if the response
   * is missing the mirror — `opponentRate` returns null in that case. */
  mirror: MaterialRow | undefined;
  /** Share of total material games this bucket occupies, as a percent 0-100
   * (e.g. 45.5 for 45.5%). Computed by the caller from `row.games / totalGames`. */
  sharePct: number;
  /** Bold metric name shown inside the popover (e.g. "Conversion"). */
  metricName: string;
  /** 1-2 sentence inline explanation rendered next to the bold name. */
  metricExplanation: ReactNode;
  /** Container data-testid (e.g. "tile-conversion"). Sub-element testids derive
   * from this via template literals: `${tileTestId}-diff`, `${tileTestId}-muted`,
   * `${tileTestId}-info`. */
  tileTestId: string;
  /** Content rendered inside the InfoPopover next to the card's h3 title. */
  titleTooltip: ReactNode;
}

export function EndgameMetricCard({
  bucket,
  row,
  mirror,
  sharePct,
  metricName,
  metricExplanation,
  tileTestId,
  titleTooltip,
}: EndgameMetricCardProps) {
  const userR = userRate(row);
  const oppR = opponentRate(row, mirror);
  const hasGames = row.games > 0;
  const hasOpponent =
    oppR !== null && row.opponent_games >= MIN_OPPONENT_BASELINE_GAMES;

  // Diff is only meaningful when opponent is available; otherwise unused.
  const diff = hasOpponent ? userR - (oppR as number) : 0;

  // Sig-gating triple: confident level AND outside the neutral band AND
  // sample-size floor met. The MIN_OPPONENT_BASELINE_GAMES floor is encoded
  // both in `hasOpponent` (controls whether the row renders) and in `deriveLevel`
  // (uses MIN_GAMES_FOR_RELIABLE_STATS, same threshold).
  const level = deriveLevel(row.diff_p_value, row.opponent_games);
  const outsideNeutral = diff < NEUTRAL_ZONE_MIN || diff >= NEUTRAL_ZONE_MAX;
  const paintColor = hasOpponent && isConfident(level) && outsideNeutral;
  const diffStyle: CSSProperties | undefined = paintColor
    ? { color: diff < NEUTRAL_ZONE_MIN ? ZONE_DANGER : ZONE_SUCCESS }
    : undefined;

  const sharePctFormatted = sharePct.toFixed(1);
  const gamesCountFormatted = row.games.toLocaleString();

  return (
    <div className="charcoal-texture rounded-md p-4" data-testid={tileTestId}>
      <h3 className="text-base font-semibold mb-2 inline-flex items-center gap-1">
        {BUCKET_DISPLAY_LABELS_WITH_METRIC[bucket]}
        <InfoPopover
          ariaLabel={`${BUCKET_DISPLAY_LABELS_WITH_METRIC[bucket]} info`}
          testId={`${tileTestId}-title-info`}
          side="top"
        >
          {titleTooltip}
        </InfoPopover>
      </h3>
      <div className="flex flex-col gap-4">
        {/* Gauge row — opacity-50 when no games per D-17. */}
        <div className={`flex justify-center${hasGames ? '' : ' opacity-50'}`}>
          <EndgameGauge
            value={userR * 100}
            label={BUCKET_DISPLAY_LABELS[bucket]}
            zones={FIXED_GAUGE_ZONES[bucket]}
          />
        </div>

        {hasGames ? (
          <>
            {/* Games-count row — mirrors EndgameOverallCard.tsx:88-100. */}
            <div className="flex flex-col gap-2">
              <span className="flex items-center gap-2 text-sm tabular-nums w-full">
                <span className="text-muted-foreground">Win/Draw/Loss</span>
                <span
                  className="ml-auto inline-flex items-center gap-1 text-sm text-muted-foreground tabular-nums whitespace-nowrap"
                  data-testid={`${tileTestId}-games-count`}
                >
                  <span>
                    Games: {sharePctFormatted}% ({gamesCountFormatted})
                  </span>
                  <Swords className="h-3.5 w-3.5" aria-hidden="true" />
                </span>
              </span>
              <div className="min-w-0">
                <MiniWDLBar
                  win_pct={row.win_pct}
                  draw_pct={row.draw_pct}
                  loss_pct={row.loss_pct}
                />
              </div>
            </div>

            {/* Peer-bullet row */}
            {hasOpponent ? (
              <div className="flex flex-col gap-2">
                <span className="flex items-center gap-1 text-sm tabular-nums w-full flex-wrap">
                  <span>
                    <span className="text-muted-foreground">You: </span>
                    <span
                      className="font-medium"
                      data-testid={`${tileTestId}-you`}
                    >
                      {formatScorePct(userR)}
                    </span>
                  </span>
                  <span>
                    <span className="text-muted-foreground">Opp: </span>
                    <span
                      className="font-medium"
                      data-testid={`${tileTestId}-opp`}
                    >
                      {formatScorePct(oppR as number)}
                    </span>
                  </span>
                  <span>
                    <span className="text-muted-foreground">Gap: </span>
                    <span
                      className="font-semibold"
                      style={diffStyle}
                      data-testid={`${tileTestId}-diff`}
                    >
                      {formatDiffPct(userR, oppR as number)}
                    </span>
                  </span>
                  <MetricStatPopover
                    name={metricName}
                    explanation={metricExplanation}
                    value={userR - (oppR as number)}
                    baseline={0}
                    unit="percent"
                    gameCount={row.opponent_games}
                    level={level}
                    pValue={row.diff_p_value}
                    vocabulary="score"
                    neutralLower={NEUTRAL_ZONE_MIN}
                    neutralUpper={NEUTRAL_ZONE_MAX}
                    baselineLabel="0%"
                    relative
                    methodology={
                      <>
                        Score: per-bucket headline rate (Conv = wins, Parity = wins + ½ draws, Recov = wins + draws).<br />
                        Test: Wald-z on the signed difference vs 0.<br />
                        Confidence interval: 95% normal-approx on the diff.
                      </>
                    }
                    testId={`${tileTestId}-info`}
                    ariaLabel={`What is ${metricName}?`}
                  />
                </span>
                <div className="min-w-0 tabular-nums">
                  <MiniBulletChart
                    value={diff}
                    neutralMin={NEUTRAL_ZONE_MIN}
                    neutralMax={NEUTRAL_ZONE_MAX}
                    domain={BULLET_DOMAIN}
                    ciLow={row.diff_ci_low ?? undefined}
                    ciHigh={row.diff_ci_high ?? undefined}
                    barColor="neutral"
                    ariaLabel={`${BUCKET_DISPLAY_LABELS[bucket]}: ${formatDiffPct(userR, oppR as number)} vs opponents`}
                  />
                </div>
              </div>
            ) : (
              <span
                className="text-sm text-muted-foreground"
                data-testid={`${tileTestId}-muted`}
              >
                n &lt; {MIN_OPPONENT_BASELINE_GAMES}, baseline unavailable
              </span>
            )}
          </>
        ) : (
          <p className="text-sm text-muted-foreground py-4">Not enough data yet</p>
        )}
      </div>
    </div>
  );
}
