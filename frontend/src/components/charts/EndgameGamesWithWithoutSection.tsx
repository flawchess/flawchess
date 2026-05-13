/**
 * Phase 85 — "Games with vs without Endgame" twin-tile section.
 *
 * Replaces the legacy table at the top of EndgamePerformanceSection.tsx with
 * two side-by-side cards (No left, Yes right per D-14) on lg+, stacked on
 * mobile, plus a full-width Score Gap footer bullet spanning both columns.
 *
 *   Left tile  ("Games without Endgame"): WDL bar + chess-score vs 0.50
 *   Right tile ("Games with Endgame")   : WDL bar + chess-score vs 0.50
 *   Footer    ("Score Gap (Yes − No)") : signed score_difference vs 0
 *
 * v1.17 single-bullet doctrine: Section 1 has no peer / cohort baseline.
 * The per-card score bullet is anchored at 0.50, the natural balanced-WDL
 * anchor (not a population p50). The per-card sig-gating triple
 * (n >= MIN_GAMES_FOR_RELIABLE_STATS ∧ isConfident(level) ∧ outside
 * neutral band) gates only the per-card score font color; the footer Score
 * Gap font color is zone-only (no sig test), preserving legacy semantics
 * per D-04.
 *
 * Card ordering (D-14): No (without Endgame) on the LEFT, Yes (with
 * Endgame) on the RIGHT. Both per-card score bullets reuse the locked
 * ENDGAME_TILE_SCORE_DOMAIN = 0.15 (D-13) so the neutral band fills ≈1/3
 * of the axis, matching the EndgameStartVsEndSection tiles' visual rhythm.
 */

import { MiniBulletChart } from '@/components/charts/MiniBulletChart';
import { MiniWDLBar } from '@/components/stats/MiniWDLBar';
import { InfoPopover } from '@/components/ui/info-popover';
import {
  SCORE_GAP_NEUTRAL_MAX,
  SCORE_GAP_NEUTRAL_MIN,
} from '@/generated/endgameZones';
import {
  SCORE_BULLET_CENTER,
  SCORE_BULLET_NEUTRAL_MAX,
  SCORE_BULLET_NEUTRAL_MIN,
  clampScoreCi,
  scoreZoneColor,
} from '@/lib/scoreBulletConfig';
import { wilsonBounds } from '@/lib/scoreConfidence';
import type { ConfidenceLevel } from '@/lib/scoreConfidence';
import { isConfident } from '@/lib/significance';
import {
  MIN_GAMES_FOR_RELIABLE_STATS,
  ZONE_DANGER,
  ZONE_NEUTRAL,
  ZONE_SUCCESS,
} from '@/lib/theme';
import type {
  EndgamePerformanceResponse,
  EndgameWDLSummary,
  ScoreGapMaterialResponse,
} from '@/types/endgames';

// Endgame tile half-domain for the W+0.5D bullets. Locked to 0.15 per
// CONTEXT D-13 (do NOT use the wider 0.25 default from scoreBulletConfig.ts)
// so the neutral band [0.45, 0.55] fills ≈1/3 of the axis (0.10 / 0.30),
// matching Tile 2 of EndgameStartVsEndSection.
const ENDGAME_TILE_SCORE_DOMAIN = 0.15;

// Footer Score Gap bullet half-domain. Population p05/p95 spans ~±0.16, so
// ±0.20 covers the observed range without making typical values look tiny.
// Source-of-truth: CONTEXT D-05 (and the legacy constant at
// EndgamePerformanceSection.tsx:38 the legacy section uses; declared locally
// because Plan 04 deletes that file).
const SCORE_GAP_DOMAIN = 0.20;

// Confidence-bucket thresholds (mirrors scoreConfidence.computeScoreConfidence
// and EndgameStartVsEndSection.tsx so all endgame tiles bucket identically).
const CONFIDENCE_HIGH_MAX_P = 0.01;
const CONFIDENCE_MEDIUM_MAX_P = 0.05;

interface EndgameGamesWithWithoutSectionProps {
  data: EndgamePerformanceResponse;
  scoreGap: ScoreGapMaterialResponse;
}

// Identical to EndgameStartVsEndSection.deriveLevel; mirrored locally rather
// than imported since that helper is not exported. Keep in lockstep with
// scoreConfidence.computeScoreConfidence's bucketing.
function deriveLevel(p: number | null, n: number): ConfidenceLevel {
  if (n < MIN_GAMES_FOR_RELIABLE_STATS || p == null) return 'low';
  if (p < CONFIDENCE_HIGH_MAX_P) return 'high';
  if (p < CONFIDENCE_MEDIUM_MAX_P) return 'medium';
  return 'low';
}

interface EndgameCardProps {
  title: string;
  tileTestId: string;
  scoreValueTestId: string;
  scorePopoverTestId: string;
  popoverAriaLabel: string;
  wdl: EndgameWDLSummary;
  pValue: number | null;
}

function EndgameCard({
  title,
  tileTestId,
  scoreValueTestId,
  scorePopoverTestId,
  popoverAriaLabel,
  wdl,
  pValue,
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

  return (
    <div className="charcoal-texture rounded-md p-4" data-testid={tileTestId}>
      <h3 className="text-base font-semibold mb-2">{title}</h3>
      <div className="flex flex-col gap-4">
        {showWdl ? (
          <div className="grid grid-cols-1 lg:grid-cols-[14rem_minmax(0,1fr)] gap-x-3 gap-y-2 items-center">
            <span className="flex items-center gap-1 text-sm tabular-nums w-full">
              <span className="text-muted-foreground">Win / Draw / Loss:</span>
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
          <div className="grid grid-cols-1 lg:grid-cols-[14rem_minmax(0,1fr)] gap-x-3 gap-y-2 items-center">
            <span className="flex items-center gap-1 text-sm tabular-nums w-full">
              <span className="text-muted-foreground">Score:</span>
              <span
                className="ml-auto font-semibold"
                style={scoreColor ? { color: scoreColor } : undefined}
                data-testid={scoreValueTestId}
              >
                {scorePct}
              </span>
              <InfoPopover
                ariaLabel={popoverAriaLabel}
                testId={scorePopoverTestId}
                side="top"
              >
                <p>
                  This score&apos;s neutral anchor sits at 50% by construction.
                  At 50% your wins balance your losses (after counting draws as
                  half-points). Unlike the rating-tier-conditioned p50 used in
                  other sections, this anchor is not a population statistic and
                  does not shift with your rating or time control.
                </p>
              </InfoPopover>
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

export function EndgameGamesWithWithoutSection({
  data,
  scoreGap,
}: EndgameGamesWithWithoutSectionProps) {
  // Footer Score Gap: zone-only font color (no sig gating per D-04).
  const gapPositive = scoreGap.score_difference >= 0;
  const gapFormatted =
    (gapPositive ? '+' : '') + `${Math.round(scoreGap.score_difference * 100)}%`;
  const gapColor =
    scoreGap.score_difference >= SCORE_GAP_NEUTRAL_MAX
      ? ZONE_SUCCESS
      : scoreGap.score_difference >= SCORE_GAP_NEUTRAL_MIN
        ? ZONE_NEUTRAL
        : ZONE_DANGER;

  return (
    <section data-testid="endgame-games-with-without-section">
      <div>
        <h3 className="text-base font-semibold">
          <span className="inline-flex items-center gap-1">
            Games with vs without Endgame
            <InfoPopover
              ariaLabel="Games with vs without Endgame info"
              testId="perf-section-info"
              side="top"
            >
              <div className="space-y-2">
                <p>
                  Compares your win/draw/loss rates in games that reached an
                  endgame phase versus those that did not. Only endgames that
                  span at least 3 full moves (6 half-moves) are counted. Shorter
                  tactical transitions from middlegame into a checkmate are
                  treated as &quot;no endgame&quot;.
                </p>
                <p>
                  The <strong>Score Gap</strong> column shows the signed gap
                  between your endgame Score and non-endgame Score (green =
                  endgame stronger, red = endgame weaker, blue = near parity).
                </p>
              </div>
            </InfoPopover>
          </span>
        </h3>
        <p className="text-sm text-muted-foreground mt-1">
          Do you perform better or worse when games reach an endgame?
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mt-4">
        {/* Left: No (without Endgame). D-14 locks No-left, Yes-right. */}
        <EndgameCard
          title="Games without Endgame"
          tileTestId="tile-games-without-endgame"
          scoreValueTestId="score-value-no"
          scorePopoverTestId="score-info-no"
          popoverAriaLabel="Games without Endgame score info"
          wdl={data.non_endgame_wdl}
          pValue={data.non_endgame_score_p_value}
        />
        {/* Right: Yes (with Endgame). */}
        <EndgameCard
          title="Games with Endgame"
          tileTestId="tile-games-with-endgame"
          scoreValueTestId="score-value-yes"
          scorePopoverTestId="score-info-yes"
          popoverAriaLabel="Games with Endgame score info"
          wdl={data.endgame_wdl}
          pValue={data.endgame_score_p_value}
        />
      </div>

      <div
        className="charcoal-texture rounded-md p-4 mt-4"
        data-testid="score-gap-footer"
      >
        <h3 className="text-base font-semibold mb-2">Score Gap (Yes − No)</h3>
        <div className="grid grid-cols-1 lg:grid-cols-[14rem_minmax(0,1fr)] gap-x-3 gap-y-2 items-center">
          <span className="flex items-center gap-1 text-sm tabular-nums w-full">
            <span className="text-muted-foreground">Difference:</span>
            <span
              className="ml-auto font-semibold"
              style={{ color: gapColor }}
              data-testid="score-gap-difference"
            >
              {gapFormatted}
            </span>
          </span>
          <div className="min-w-0 tabular-nums">
            <MiniBulletChart
              value={scoreGap.score_difference}
              center={0}
              neutralMin={SCORE_GAP_NEUTRAL_MIN}
              neutralMax={SCORE_GAP_NEUTRAL_MAX}
              domain={SCORE_GAP_DOMAIN}
              barColor="neutral"
              ariaLabel={`Endgame vs non-endgame score gap: ${gapFormatted}`}
            />
          </div>
        </div>
      </div>
    </section>
  );
}
