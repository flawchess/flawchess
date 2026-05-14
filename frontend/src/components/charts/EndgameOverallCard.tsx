/**
 * Phase 85 — Cards 1 and 3 of the "Endgame Overall Performance" composite
 * section. Renders a WDL bar over a sig-gated chess-score bullet (W + 0.5·D).
 *
 * Per-card sig-gating triple (n >= MIN_GAMES_FOR_RELIABLE_STATS AND
 * isConfident(level) AND outside neutral band) gates only the score font
 * color. The Wilson whiskers on the bullet are driven by `wilsonBounds`
 * locally (matches the Tile-2 pattern of the legacy EndgameStartVsEndSection).
 */

import type { ReactNode } from 'react';

import { Swords } from 'lucide-react';

import { MiniBulletChart } from '@/components/charts/MiniBulletChart';
import { MetricStatPopover } from '@/components/popovers/MetricStatPopover';
import { MiniWDLBar } from '@/components/stats/MiniWDLBar';
import {
  SCORE_BULLET_CENTER,
  SCORE_BULLET_NEUTRAL_MAX,
  SCORE_BULLET_NEUTRAL_MIN,
  clampScoreCi,
  scoreZoneColor,
} from '@/lib/scoreBulletConfig';
import { wilsonBounds } from '@/lib/scoreConfidence';
import { isConfident } from '@/lib/significance';
import { MIN_GAMES_FOR_RELIABLE_STATS, ZONE_NEUTRAL } from '@/lib/theme';
import type { EndgameWDLSummary } from '@/types/endgames';

import { ENDGAME_TILE_SCORE_DOMAIN, deriveLevel } from './EndgameOverallShared';

// Neutral band for score-vs-50% (matches arrowColor.ts / WdlConfidenceTooltip
// historical bounds). 260514-i3l moved these inline as MetricStatPopover
// props rather than re-importing from ScoreConfidencePopover/WdlConfidenceTooltip.
const SCORE_NEUTRAL_LOWER = 0.45;
const SCORE_NEUTRAL_UPPER = 0.55;

interface EndgameCardProps {
  title: string;
  scoreLabel: string;
  tileTestId: string;
  scoreValueTestId: string;
  scorePopoverTestId: string;
  popoverAriaLabel: string;
  gamesCountTestId: string;
  wdl: EndgameWDLSummary;
  pValue: number | null;
  gamesShare: number;
  /** Bold metric name shown inside the popover (e.g. "Endgame Score"). */
  popoverName: string;
  /** 1-2 sentence inline explanation rendered next to the bold name. */
  popoverExplanation: ReactNode;
}

export function EndgameCard({
  title,
  scoreLabel,
  tileTestId,
  scoreValueTestId,
  scorePopoverTestId,
  popoverAriaLabel,
  gamesCountTestId,
  wdl,
  pValue,
  gamesShare,
  popoverName,
  popoverExplanation,
}: EndgameCardProps) {
  const total = wdl.total;
  const score = total > 0 ? (wdl.wins + 0.5 * wdl.draws) / total : 0;
  const level = deriveLevel(pValue, total);
  const zoneHex = scoreZoneColor(score);
  const isInColoredZone = zoneHex !== ZONE_NEUTRAL;
  const scoreShowZoneFontColor = isConfident(level) && isInColoredZone;
  const scoreColor: string | undefined = scoreShowZoneFontColor ? zoneHex : undefined;
  const [ciLow, ciHigh] = wilsonBounds(score, total);
  const showWdl = total > 0;
  const showScoreRow = total >= MIN_GAMES_FOR_RELIABLE_STATS;
  const scorePct = `${Math.round(score * 100)}%`;
  const sharePct = `${(gamesShare * 100).toFixed(1)}%`;
  const gamesCountFormatted = total.toLocaleString();

  return (
    <div className="charcoal-texture rounded-md p-4" data-testid={tileTestId}>
      <h3 className="text-base font-semibold mb-2">{title}</h3>
      <div className="flex flex-col gap-4">
        {showWdl ? (
          <div className="flex flex-col gap-2">
            <span className="flex items-center gap-2 text-sm tabular-nums w-full">
              <span className="text-muted-foreground">Win/Draw/Loss</span>
              <span
                className="ml-auto inline-flex items-center gap-1 text-sm text-muted-foreground tabular-nums whitespace-nowrap"
                data-testid={gamesCountTestId}
              >
                <span>
                  Games: {sharePct} ({gamesCountFormatted})
                </span>
                <Swords className="h-3.5 w-3.5" aria-hidden="true" />
              </span>
            </span>
            <div className="min-w-0">
              <MiniWDLBar
                win_pct={wdl.win_pct}
                draw_pct={wdl.draw_pct}
                loss_pct={wdl.loss_pct}
              />
            </div>
          </div>
        ) : (
          <p className="text-sm text-muted-foreground py-4">Not enough data yet</p>
        )}

        {showScoreRow ? (
          <div className="flex flex-col gap-2">
            <span className="flex items-center gap-1 text-sm tabular-nums w-full">
              <span className="text-muted-foreground">{scoreLabel}</span>
              <span
                className="font-semibold"
                style={scoreColor ? { color: scoreColor } : undefined}
                data-testid={scoreValueTestId}
              >
                {scorePct}
              </span>
              <MetricStatPopover
                name={popoverName}
                explanation={popoverExplanation}
                value={score}
                baseline={0.5}
                unit="percent"
                gameCount={total}
                level={level}
                pValue={pValue}
                vocabulary="score"
                neutralLower={SCORE_NEUTRAL_LOWER}
                neutralUpper={SCORE_NEUTRAL_UPPER}
                baselineLabel="50%"
                methodology={
                  <>
                    Score: wins + ½ draws.<br />
                    Test: two-sided Wilson score test vs 50%.<br />
                    Confidence interval: Wilson 95% (whiskers).
                  </>
                }
                testId={scorePopoverTestId}
                ariaLabel={popoverAriaLabel}
              />
            </span>
            <div className="min-w-0 tabular-nums">
              <MiniBulletChart
                value={score}
                center={SCORE_BULLET_CENTER}
                neutralMin={SCORE_BULLET_NEUTRAL_MIN}
                neutralMax={SCORE_BULLET_NEUTRAL_MAX}
                domain={ENDGAME_TILE_SCORE_DOMAIN}
                ciLow={clampScoreCi(ciLow)}
                ciHigh={clampScoreCi(ciHigh)}
                barColor="neutral"
                ariaLabel={`${title}: score ${scorePct}`}
              />
            </div>
          </div>
        ) : (
          showWdl && (
            <p className="text-sm text-muted-foreground py-4">Not enough data yet</p>
          )
        )}
      </div>
    </div>
  );
}
