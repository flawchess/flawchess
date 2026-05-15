/**
 * Phase 86 — Composite "Endgame Skill" card for the 4-card Endgame Metrics
 * layout. Renders gauge (using ENDGAME_SKILL_ZONES) -> games-count row +
 * Games-with-Endgame MiniWDLBar -> Skill Delta-ES Score Gap bullet
 * (ScoreGapRow vs 0).
 *
 * Skill is the equal-weighted mean of Conv + Parity + Recov Score Gaps over
 * active buckets; the backend produces section2_score_gap_skill_* per Phase
 * 87.2 D-01.
 *
 * Quick task 260516-1h5: Replaced the plain `Games: N` text with the same
 * games-count + MiniWDLBar layout used by the Conv/Parity/Recov cards, driven
 * by `perfData.endgame_wdl` (Games with Endgame).
 *
 * Phase 87.2 refactor: replaced the rate-based peer-bullet (You/Opp/Gap +
 * MiniBulletChart vs mirror-bucket opponent) with a ScoreGapRow anchored on
 * the Stockfish baseline (vs 0). Props oppSkill/pValue/ciLow/ciHigh deleted;
 * replaced by scoreGapMean/scoreGapN/scoreGapPValue/scoreGapCiLow/scoreGapCiHigh.
 * Per D-08: no "vs opponents" framing. Zone-only tint (Phase 85.1 D-04 inherited).
 */

import { Cpu, Swords } from 'lucide-react';

import { EndgameGauge } from '@/components/charts/EndgameGauge';
import { MetricStatPopover } from '@/components/popovers/MetricStatPopover';
import { MiniWDLBar } from '@/components/stats/MiniWDLBar';
import { InfoPopover } from '@/components/ui/info-popover';
import { ZONE_DANGER, ZONE_SUCCESS } from '@/lib/theme';
import {
  ENDGAME_SKILL_ZONES,
} from '@/lib/endgameMetrics';
// Neutral band for the Skill Delta-ES Score Gap bullet (D-02 / Plan 01).
import {
  SECTION2_SCORE_GAP_SKILL_NEUTRAL_MIN,
  SECTION2_SCORE_GAP_SKILL_NEUTRAL_MAX,
} from '@/generated/endgameZones';
import type { EndgameWDLSummary } from '@/types/endgames';

import { ScoreGapRow } from './EndgameOverallScoreGapRow';
import { deriveLevel } from './EndgameOverallShared';

// Skill-specific popover copy per D-08: equal-weighted mean of the three
// bucket gaps. Identical sigmoid-bias caveat suffix as the 3 bucket cards.
// No "vs opponents" framing (D-08 rule: Stockfish-baseline anchor).
// No em-dashes per CLAUDE.md style guide.
const SKILL_POPOVER_COPY =
  'Equal-weighted average of the three per-bucket Score Gaps above (Conversion + Parity + Recovery, each contributing equally). One-number summary of overall endgame performance vs Stockfish expectations, independent of which entry-eval bucket your endgames cluster in. Positive = above the Stockfish baseline; negative = below.';

interface EndgameSkillCardProps {
  /** Composite skill rate (mean of active per-bucket rates). Null when fewer
   * than 2 buckets are active. Used only for the gauge display. */
  skill: number | null;
  /** Games-with-Endgame WDL summary (`perfData.endgame_wdl`). Drives the
   * games-count row and the MiniWDLBar inside the Skill card. */
  endgameWdl: EndgameWDLSummary;
  /** Phase 87.2: 5 eval-baseline Delta-ES Score Gap fields from
   * ScoreGapMaterialResponse.section2_score_gap_skill_*. */
  scoreGapMean: number | null;
  scoreGapN: number | null;
  scoreGapPValue: number | null;
  scoreGapCiLow: number | null;
  scoreGapCiHigh: number | null;
  /** Container data-testid (Plan 05 passes "tile-endgame-skill"). */
  tileTestId: string;
}

export function EndgameSkillCard({
  skill,
  endgameWdl,
  scoreGapMean,
  scoreGapN,
  scoreGapPValue,
  scoreGapCiLow,
  scoreGapCiHigh,
  tileTestId,
}: EndgameSkillCardProps) {
  const hasSkill = skill !== null;

  // Phase 87.2: Skill Delta-ES Score Gap derivation.
  // Zone-only tint (Phase 85.1 D-04): no sig-gate on the row font color.
  const gapMean = scoreGapMean;
  const gapN = scoreGapN ?? 0;
  const showGapRow = gapN > 0;
  const gapFormatted =
    gapMean != null
      ? (gapMean >= 0 ? '+' : '') + `${Math.round(gapMean * 100)}%`
      : '—';
  const gapColor: string | undefined =
    gapMean != null
      ? gapMean < SECTION2_SCORE_GAP_SKILL_NEUTRAL_MIN
        ? ZONE_DANGER
        : gapMean >= SECTION2_SCORE_GAP_SKILL_NEUTRAL_MAX
          ? ZONE_SUCCESS
          : undefined
      : undefined;
  const gapLevel = deriveLevel(scoreGapPValue ?? null, gapN);

  const gaugeValue = (skill ?? 0) * 100;
  const gamesCountFormatted = endgameWdl.total.toLocaleString();
  const showWdlBlock = endgameWdl.total > 0;

  return (
    <div className="charcoal-texture rounded-md p-4" data-testid={tileTestId}>
      <h3 className="text-base font-semibold mb-2 inline-flex items-center gap-1">
        Endgame Skill
        <InfoPopover
          ariaLabel="Endgame Skill info"
          testId={`${tileTestId}-title-info`}
          side="top"
        >
          <div className="space-y-2">
            <p>
              <strong>Endgame Skill:</strong> the average of your Conversion,
              Parity, and Recovery rates. A one-number summary of overall
              endgame proficiency calibrated against the Stockfish expected-score
              baseline.
            </p>
            <p>
              The <strong>gauge</strong> plots it against a fixed
              band (blue = typical, red = below, green = above). Bands
              are calibrated from FlawChess Benchmark data and don't shift with filters,
              giving you a stable target you can chase as you improve.
            </p>
            <p>
              The <strong>Skill Score Gap</strong> bullet below shows the same
              three-bucket composite measured a different way: how your scores
              compare to the Stockfish baseline for each entry-eval bucket.
              The gauge tracks absolute performance; the bullet tracks
              performance vs expectation.
            </p>
            <p>
              The <strong>Endgame ELO timeline</strong> below uses the same
              Endgame Skill to adjust your rating by your per-week endgame
              performance.
            </p>
          </div>
        </InfoPopover>
      </h3>
      <div className="flex flex-col gap-4">
        {/* Gauge row -- opacity-50 when skill is null per D-17. */}
        <div className={`flex justify-center${hasSkill ? '' : ' opacity-50'}`}>
          <EndgameGauge
            value={gaugeValue}
            label="Endgame Skill"
            zones={ENDGAME_SKILL_ZONES}
          />
        </div>

        {hasSkill ? (
          <>
            {/* Mirror of the games-count row in EndgameMetricCard.tsx. */}
            {showWdlBlock && (
              <div className="flex flex-col gap-2">
                <span className="flex items-center gap-2 text-sm tabular-nums w-full">
                  <span className="text-muted-foreground">Win/Draw/Loss</span>
                  <span
                    className="ml-auto inline-flex items-center gap-1 text-sm text-muted-foreground tabular-nums whitespace-nowrap"
                    data-testid={`${tileTestId}-games-count`}
                  >
                    <span>Games: {gamesCountFormatted}</span>
                    <Swords className="h-3.5 w-3.5" aria-hidden="true" />
                  </span>
                </span>
                <div className="min-w-0">
                  <MiniWDLBar
                    win_pct={endgameWdl.win_pct}
                    draw_pct={endgameWdl.draw_pct}
                    loss_pct={endgameWdl.loss_pct}
                  />
                </div>
              </div>
            )}

            {/* Phase 87.2: Skill Delta-ES Score Gap bullet (replaces peer-bullet row).
                Shows when gapN > 0; hidden when no span data yet. */}
            {showGapRow && (
              <div data-testid={`${tileTestId}-score-gap-bullet`}>
                <ScoreGapRow
                  label={
                    <span className="inline-flex items-center gap-1">
                      <Cpu className="h-3.5 w-3.5" aria-hidden="true" />
                      Skill Score Gap:
                    </span>
                  }
                  value={gapMean ?? 0}
                  formatted={gapFormatted}
                  resultColor={gapColor}
                  valueTestId={`${tileTestId}-score-gap-value`}
                  ariaLabel={`Skill Score Gap: ${gapFormatted}`}
                  neutralMin={SECTION2_SCORE_GAP_SKILL_NEUTRAL_MIN}
                  neutralMax={SECTION2_SCORE_GAP_SKILL_NEUTRAL_MAX}
                  ciLow={scoreGapCiLow ?? undefined}
                  ciHigh={scoreGapCiHigh ?? undefined}
                  tooltip={
                    <MetricStatPopover
                      name={'Skill Score Gap'}
                      explanation={SKILL_POPOVER_COPY}
                      value={gapMean ?? 0}
                      baseline={0}
                      unit="percent"
                      gameCount={gapN}
                      level={gapLevel}
                      pValue={scoreGapPValue}
                      vocabulary="score"
                      neutralLower={SECTION2_SCORE_GAP_SKILL_NEUTRAL_MIN}
                      neutralUpper={SECTION2_SCORE_GAP_SKILL_NEUTRAL_MAX}
                      baselineLabel="0%"
                      methodology={
                        <>
                          Score: equal-weighted mean of the three bucket means (Conv + Parity + Recov).<br />
                          Test: variance-of-sum propagation from the three independent paired-z tests.<br />
                          Confidence interval: 95% normal-approx on the propagated SE.
                        </>
                      }
                      testId={`${tileTestId}-score-gap-info`}
                      ariaLabel={'What is Skill Score Gap?'}
                    />
                  }
                />
              </div>
            )}
          </>
        ) : (
          <p className="text-sm text-muted-foreground py-4">Not enough data yet</p>
        )}
      </div>
    </div>
  );
}
