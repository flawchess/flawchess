/**
 * Phase 81 — "Endgame Start vs End" twin-tile section.
 *
 * Sits in `Endgames.tsx` directly above the existing WDL table. Composes
 * two tiles side-by-side on lg+, stacked on mobile (entry-eval first per
 * D-17 — chronological setup → execution).
 *
 *   Tile 1 ("Where you start"): avg eval at endgame entry vs 0
 *   Tile 2 ("What you do with it"): absolute endgame score vs 50%
 *
 * Both tiles reuse the locked Openings ExplorerTab pattern (rows 2 & 3):
 * inline label + value + popover + MiniBulletChart. Color logic mirrors
 * ExplorerTab's `showZoneFontColor` gate — only paint the value when
 * confidence is medium/high AND the value lands outside the neutral band.
 *
 * The backend ships raw p-values; confidence buckets are derived locally
 * via `deriveLevel` (matches `scoreConfidence.computeScoreConfidence`'s
 * thresholds — n >= 10, p < 0.01 high, p < 0.05 medium).
 */

import { MiniBulletChart } from '@/components/charts/MiniBulletChart';
import { BulletConfidencePopover } from '@/components/insights/BulletConfidencePopover';
import { ScoreConfidencePopover } from '@/components/insights/ScoreConfidencePopover';
import { formatSignedEvalPawns } from '@/lib/clockFormat';
import {
  ENDGAME_ENTRY_EVAL_CENTER,
  ENDGAME_ENTRY_EVAL_DOMAIN_PAWNS,
  ENDGAME_ENTRY_EVAL_NEUTRAL_MAX_PAWNS,
  ENDGAME_ENTRY_EVAL_NEUTRAL_MIN_PAWNS,
  endgameEntryEvalZoneColor,
} from '@/lib/endgameEntryEvalZones';
import {
  SCORE_BULLET_CENTER,
  SCORE_BULLET_NEUTRAL_MAX,
  SCORE_BULLET_NEUTRAL_MIN,
  clampScoreCi,
  scoreBulletDomain,
  scoreZoneColor,
} from '@/lib/scoreBulletConfig';
import { wilsonBounds } from '@/lib/scoreConfidence';
import type { ConfidenceLevel } from '@/lib/scoreConfidence';
import { isConfident } from '@/lib/significance';
import { MIN_GAMES_FOR_RELIABLE_STATS, ZONE_NEUTRAL } from '@/lib/theme';
import type { EndgamePerformanceResponse } from '@/types/endgames';

// Confidence-bucket thresholds (mirrors scoreConfidence.computeScoreConfidence
// so both tiles bucket identically to the rest of the app).
const CONFIDENCE_HIGH_MAX_P = 0.01;
const CONFIDENCE_MEDIUM_MAX_P = 0.05;

interface EndgameStartVsEndSectionProps {
  data: EndgamePerformanceResponse;
}

// Backend ships raw p-values; the popovers and color gates think in confidence
// buckets. Keep this in lockstep with `scoreConfidence.computeScoreConfidence`'s
// bucketing (n >= 10 gate, p < 0.01 high, p < 0.05 medium).
function deriveLevel(p: number | null, n: number): ConfidenceLevel {
  if (n < MIN_GAMES_FOR_RELIABLE_STATS || p == null) return 'low';
  if (p < CONFIDENCE_HIGH_MAX_P) return 'high';
  if (p < CONFIDENCE_MEDIUM_MAX_P) return 'medium';
  return 'low';
}

export function EndgameStartVsEndSection({ data }: EndgameStartVsEndSectionProps) {
  // ── Tile 1 derived values (entry eval) ───────────────────────────────────
  const evalLevel = deriveLevel(data.entry_eval_p_value, data.entry_eval_n);
  const evalZoneHex = endgameEntryEvalZoneColor(data.entry_eval_mean_pawns);
  const evalIsInColoredZone = evalZoneHex !== ZONE_NEUTRAL;
  const evalShowZoneFontColor = isConfident(evalLevel) && evalIsInColoredZone;
  const evalColor: string | undefined = evalShowZoneFontColor ? evalZoneHex : undefined;
  const showTile1Chart = data.entry_eval_n >= MIN_GAMES_FOR_RELIABLE_STATS;

  // ── Tile 2 derived values (endgame score vs 50%) ─────────────────────────
  const totalGames = data.endgame_wdl.total;
  const score =
    totalGames > 0
      ? (data.endgame_wdl.wins + 0.5 * data.endgame_wdl.draws) / totalGames
      : 0;
  const scoreLevel = deriveLevel(data.endgame_score_p_value, totalGames);
  const scoreZoneHex = scoreZoneColor(score);
  const scoreIsInColoredZone = scoreZoneHex !== ZONE_NEUTRAL;
  const scoreShowZoneFontColor = isConfident(scoreLevel) && scoreIsInColoredZone;
  const scoreColor: string | undefined = scoreShowZoneFontColor ? scoreZoneHex : undefined;
  const [scoreCiLow, scoreCiHigh] = wilsonBounds(score, totalGames);
  const showTile2Chart = totalGames >= MIN_GAMES_FOR_RELIABLE_STATS;

  // ScoreConfidencePopover.pValue is non-nullable; coerce null to 1.0
  // (the popover's "no signal" baseline — same coercion BulletConfidencePopover
  // does internally).
  const scorePValueForPopover = data.endgame_score_p_value ?? 1;

  return (
    <section data-testid="endgame-start-vs-end-section">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Tile 1 — entry eval, FIRST in DOM for D-17 mobile chronological order */}
        <div
          className="charcoal-texture rounded-md p-4"
          data-testid="tile-entry-eval"
        >
          <h3 className="text-base font-semibold mb-2">Where you start</h3>
          {showTile1Chart ? (
            // grid-cols-1 stacks label-row and chart on mobile; lg+ puts them
            // side-by-side once each tile is wide enough to fit both.
            <div className="grid grid-cols-1 lg:grid-cols-[auto_minmax(0,1fr)] gap-x-3 gap-y-2 items-center">
              <span className="flex items-center gap-1 text-sm tabular-nums w-full">
                <span className="text-muted-foreground">Endgame entry eval:</span>
                <span
                  className="ml-auto font-semibold inline-flex items-center gap-0.5"
                  style={evalColor ? { color: evalColor } : undefined}
                  data-testid="entry-eval-value"
                >
                  {formatSignedEvalPawns(data.entry_eval_mean_pawns)}
                </span>
                <BulletConfidencePopover
                  level={evalLevel}
                  pValue={data.entry_eval_p_value}
                  gameCount={data.entry_eval_n}
                  evalMeanPawns={data.entry_eval_mean_pawns}
                  // Endgame stats are color-agnostic; the popover's `color` prop
                  // drives the per-color baseline tick. White is a fallback —
                  // BulletConfidencePopover.tsx:15 union is white | black only,
                  // so a non-color string would fail tsc.
                  color="white"
                  testId="entry-eval-popover-trigger"
                />
              </span>
              <div className="min-w-0 tabular-nums">
                <MiniBulletChart
                  value={data.entry_eval_mean_pawns}
                  center={ENDGAME_ENTRY_EVAL_CENTER}
                  neutralMin={ENDGAME_ENTRY_EVAL_NEUTRAL_MIN_PAWNS}
                  neutralMax={ENDGAME_ENTRY_EVAL_NEUTRAL_MAX_PAWNS}
                  domain={ENDGAME_ENTRY_EVAL_DOMAIN_PAWNS}
                  ciLow={data.entry_eval_ci_low_pawns ?? undefined}
                  ciHigh={data.entry_eval_ci_high_pawns ?? undefined}
                  barColor="neutral"
                  ariaLabel={`Endgame entry eval: ${data.entry_eval_mean_pawns.toFixed(2)} pawns`}
                />
              </div>
            </div>
          ) : (
            <p className="text-sm text-muted-foreground py-4">Not enough data yet</p>
          )}
        </div>

        {/* Tile 2 — endgame score vs 50% */}
        <div
          className="charcoal-texture rounded-md p-4"
          data-testid="tile-endgame-score"
        >
          <h3 className="text-base font-semibold mb-2">What you do with it</h3>
          {showTile2Chart ? (
            // grid-cols-1 stacks label-row and chart on mobile; lg+ puts them
            // side-by-side once each tile is wide enough to fit both.
            <div className="grid grid-cols-1 lg:grid-cols-[auto_minmax(0,1fr)] gap-x-3 gap-y-2 items-center">
              <span className="flex items-center gap-1 text-sm tabular-nums w-full">
                <span className="text-muted-foreground">Endgame score:</span>
                <span
                  className="ml-auto font-semibold"
                  style={scoreColor ? { color: scoreColor } : undefined}
                  data-testid="endgame-score-value"
                >
                  {`${(score * 100).toFixed(1)}%`}
                </span>
                <ScoreConfidencePopover
                  level={scoreLevel}
                  pValue={scorePValueForPopover}
                  score={score}
                  gameCount={totalGames}
                  testId="endgame-score-popover-trigger"
                />
              </span>
              <div className="min-w-0 tabular-nums">
                <MiniBulletChart
                  value={score}
                  center={SCORE_BULLET_CENTER}
                  neutralMin={SCORE_BULLET_NEUTRAL_MIN}
                  neutralMax={SCORE_BULLET_NEUTRAL_MAX}
                  domain={scoreBulletDomain()}
                  ciLow={clampScoreCi(scoreCiLow)}
                  ciHigh={clampScoreCi(scoreCiHigh)}
                  barColor="neutral"
                  ariaLabel={`Endgame score: ${(score * 100).toFixed(1)}%`}
                />
              </div>
            </div>
          ) : (
            <p className="text-sm text-muted-foreground py-4">Not enough data yet</p>
          )}
        </div>
      </div>
    </section>
  );
}
