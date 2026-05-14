/**
 * Phase 86 — Composite "Endgame Skill" card for the 4-card Endgame Metrics
 * layout. Renders gauge (using ENDGAME_SKILL_ZONES) → games-count row →
 * peer-bullet row (`You / Opp / Gap` text + `MiniBulletChart`
 * for the signed `skill − oppSkill` vs 0).
 *
 * Skill is a composite of Conv + Parity + Recov rates over active buckets;
 * the backend produces `data.skill` and `data.opp_skill` per Phase 86 D-01..D-04.
 * No WDL bar — the single-ply composite has no W/D/L definable per SEC2-03.
 *
 * v1.17 single-bullet doctrine: per-card peer bullet vs 0 with the sig-gating
 * triple applied to the diff-percent font color only. Empty state when
 * `skill === null` (fewer than 2 active buckets) per D-17.
 */

import type { CSSProperties } from 'react';

import { MiniBulletChart } from '@/components/charts/MiniBulletChart';
import { EndgameGauge } from '@/components/charts/EndgameGauge';
import { MetricStatPopover } from '@/components/popovers/MetricStatPopover';
import { isConfident } from '@/lib/significance';
import { ZONE_DANGER, ZONE_SUCCESS } from '@/lib/theme';
import {
  BULLET_DOMAIN,
  ENDGAME_SKILL_ZONES,
  MIN_OPPONENT_BASELINE_GAMES,
  NEUTRAL_ZONE_MAX,
  NEUTRAL_ZONE_MIN,
  formatDiffPct,
  formatScorePct,
} from '@/lib/endgameMetrics';

import { deriveLevel } from './EndgameOverallShared';

interface EndgameSkillCardProps {
  /** Composite skill (mean of active per-bucket user rates). Null when fewer
   * than 2 buckets are active. */
  skill: number | null;
  /** Composite opponent skill (mean of mirror-bucket rates). Null when fewer
   * than 2 buckets are active. */
  oppSkill: number | null;
  /** Total games across all material buckets. Used for the games-count row
   * and as the n-floor for the sig-gating triple. */
  totalGames: number;
  /** Wald-z p-value on `skill - oppSkill` vs 0. Null when n_active < 2 OR
   * any active opp component has opp_row.N < MIN_OPPONENT_BASELINE_GAMES. */
  pValue: number | null;
  ciLow: number | null;
  ciHigh: number | null;
  /** Container data-testid (Plan 05 passes "tile-endgame-skill"). */
  tileTestId: string;
}

export function EndgameSkillCard({
  skill,
  oppSkill,
  totalGames,
  pValue,
  ciLow,
  ciHigh,
  tileTestId,
}: EndgameSkillCardProps) {
  // Backend invariant (compute_skill_diff_test): skill and oppSkill are both
  // null (zero active buckets) or both numbers — never one without the other.
  // So `hasSkill` alone implies `oppSkill !== null`, and we just need the
  // sample-size floor on top.
  const hasSkill = skill !== null;
  const hasOpponent = hasSkill && totalGames >= MIN_OPPONENT_BASELINE_GAMES;

  const diff = hasOpponent ? (skill as number) - (oppSkill as number) : 0;

  // Sig-gating triple identical to EndgameMetricCard.
  const level = deriveLevel(pValue, totalGames);
  const outsideNeutral = diff < NEUTRAL_ZONE_MIN || diff >= NEUTRAL_ZONE_MAX;
  const paintColor = hasOpponent && isConfident(level) && outsideNeutral;
  const diffStyle: CSSProperties | undefined = paintColor
    ? { color: diff < NEUTRAL_ZONE_MIN ? ZONE_DANGER : ZONE_SUCCESS }
    : undefined;

  const gaugeValue = (skill ?? 0) * 100;

  return (
    <div className="charcoal-texture rounded-md p-4" data-testid={tileTestId}>
      <h3 className="text-base font-semibold mb-2">Endgame Skill</h3>
      <div className="flex flex-col gap-4">
        {/* Gauge row — opacity-50 when skill is null per D-17. */}
        <div className={`flex justify-center${hasSkill ? '' : ' opacity-50'}`}>
          <EndgameGauge
            value={gaugeValue}
            label="Endgame Skill"
            zones={ENDGAME_SKILL_ZONES}
          />
        </div>

        {hasSkill ? (
          <>
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
                      {formatScorePct(skill as number)}
                    </span>
                  </span>
                  <span>
                    <span className="text-muted-foreground">Opp: </span>
                    <span
                      className="font-medium"
                      data-testid={`${tileTestId}-opp`}
                    >
                      {formatScorePct(oppSkill as number)}
                    </span>
                  </span>
                  <span>
                    <span className="text-muted-foreground">Gap: </span>
                    <span
                      className="font-semibold"
                      style={diffStyle}
                      data-testid={`${tileTestId}-diff`}
                    >
                      {formatDiffPct(skill as number, oppSkill as number)}
                    </span>
                  </span>
                  <MetricStatPopover
                    name="Endgame Skill"
                    explanation="A composite of your Conversion, Parity, and Recovery rates compared to the same composite for your opponents against you. One-number summary of overall endgame proficiency."
                    value={(skill as number) - (oppSkill as number)}
                    baseline={0}
                    unit="percent"
                    gameCount={totalGames}
                    level={level}
                    pValue={pValue}
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
                    ariaLabel="What is Endgame Skill?"
                  />
                </span>
                <div className="min-w-0 tabular-nums">
                  <MiniBulletChart
                    value={diff}
                    neutralMin={NEUTRAL_ZONE_MIN}
                    neutralMax={NEUTRAL_ZONE_MAX}
                    domain={BULLET_DOMAIN}
                    ciLow={ciLow ?? undefined}
                    ciHigh={ciHigh ?? undefined}
                    barColor="neutral"
                    ariaLabel={`Endgame Skill: ${formatDiffPct(skill as number, oppSkill as number)} vs opponents`}
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
