/**
 * Phase 85 redesign-in-place — "Endgame Overall Performance" 3-card composite
 * section. Replaces the legacy EndgameGamesWithWithoutSection (2-card + footer)
 * and absorbs Card 2 from the legacy EndgameStartVsEndSection ("Where you
 * start" tile). See 85-CONTEXT.md §"Redesign Decision (Post-Execution,
 * 2026-05-13)" for the rationale.
 *
 * Layout: 3-column card grid on lg+, stacked on mobile.
 *   Card 1 | Card 2 | Card 3
 *   "Games without Endgame" | "At Endgame Entry" | "Games with Endgame"
 *
 * Endgame Score Gap sits in column 2 on desktop (via lg:col-start-2 on the
 * 4th grid child), naturally stacked at the bottom on mobile after Card 3.
 *
 * Inside-card layout is single-column at every breakpoint (label-above-chart)
 * so the WDL bar / bullet charts use the full card width on desktop too.
 *
 * Cards 1 and 3 carry the share-of-games badge "NN.N% (count) <swords>"
 * inline with the "Win / Draw / Loss" label (right-aligned). Matches the
 * games-count + Swords pattern used across the app (e.g. WDLChartRow).
 *
 * No section-root h3 or section-level InfoPopover — the question line under
 * the page-level h2 carries the framing.
 *
 * CR-01 preserved: achievable-score MiniBulletChart uses OFFSET-form
 * neutralMin/neutralMax (absolute registry bounds minus center), not absolute
 * bounds directly.
 *
 * v1.17 single-bullet doctrine: per-card score bullet anchored at 0.50.
 * Per-card sig-gating triple (n >= MIN_GAMES_FOR_RELIABLE_STATS AND
 * isConfident(level) AND outside neutral band) gates only the score font color.
 * Score Gap font color is zone-only (no sig test) per D-04.
 */

import { Cpu, Swords } from 'lucide-react';

import { MiniBulletChart } from '@/components/charts/MiniBulletChart';
import { BulletConfidencePopover } from '@/components/insights/BulletConfidencePopover';
import { AchievableScorePopover } from '@/components/popovers/AchievableScorePopover';
import { MiniWDLBar } from '@/components/stats/MiniWDLBar';
import { InfoPopover } from '@/components/ui/info-popover';
import {
  ENTRY_EXPECTED_SCORE_NEUTRAL_MAX,
  ENTRY_EXPECTED_SCORE_NEUTRAL_MIN,
  entryExpectedScoreZoneColor,
  SCORE_GAP_NEUTRAL_MAX,
  SCORE_GAP_NEUTRAL_MIN,
} from '@/generated/endgameZones';
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
// CONTEXT D-13 so the neutral band [0.45, 0.55] fills ≈1/3 of the axis (0.10 / 0.30).
const ENDGAME_TILE_SCORE_DOMAIN = 0.15;

// Score Gap bullet half-domain. Population p05/p95 spans ~±0.16, so ±0.20
// covers the observed range without making typical values look tiny.
const SCORE_GAP_DOMAIN = 0.20;

// Confidence-bucket thresholds (mirrors scoreConfidence.computeScoreConfidence).
const CONFIDENCE_HIGH_MAX_P = 0.01;
const CONFIDENCE_MEDIUM_MAX_P = 0.05;

// Identical to EndgameStartVsEndSection.deriveLevel — kept in lockstep with
// scoreConfidence.computeScoreConfidence's bucketing.
function deriveLevel(p: number | null, n: number): ConfidenceLevel {
  if (n < MIN_GAMES_FOR_RELIABLE_STATS || p == null) return 'low';
  if (p < CONFIDENCE_HIGH_MAX_P) return 'high';
  if (p < CONFIDENCE_MEDIUM_MAX_P) return 'medium';
  return 'low';
}

// ── EndgameCard (Cards 1 + 3): WDL bar + score bullet ─────────────────────

interface EndgameCardProps {
  title: string;
  tileTestId: string;
  scoreValueTestId: string;
  scorePopoverTestId: string;
  popoverAriaLabel: string;
  gamesCountTestId: string;
  wdl: EndgameWDLSummary;
  pValue: number | null;
  gamesShare: number;
}

function EndgameCard({
  title,
  tileTestId,
  scoreValueTestId,
  scorePopoverTestId,
  popoverAriaLabel,
  gamesCountTestId,
  wdl,
  pValue,
  gamesShare,
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
              <span className="text-muted-foreground">Win / Draw / Loss</span>
              <span
                className="ml-auto inline-flex items-center gap-1 text-sm text-muted-foreground tabular-nums whitespace-nowrap"
                data-testid={gamesCountTestId}
              >
                <span>
                  {sharePct} ({gamesCountFormatted})
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

// ── Card 2 ("At Endgame Entry"): entry eval + achievable score, no WDL ────

interface EntryCardProps {
  data: EndgamePerformanceResponse;
}

function EntryCard({ data }: EntryCardProps) {
  // Row 1: entry eval
  const evalLevel = deriveLevel(data.entry_eval_p_value, data.entry_eval_n);
  const evalZoneHex = endgameEntryEvalZoneColor(data.entry_eval_mean_pawns);
  const evalIsInColoredZone = evalZoneHex !== ZONE_NEUTRAL;
  const evalShowZoneFontColor = isConfident(evalLevel) && evalIsInColoredZone;
  const evalColor: string | undefined = evalShowZoneFontColor ? evalZoneHex : undefined;
  const showEntryEvalChart = data.entry_eval_n >= MIN_GAMES_FOR_RELIABLE_STATS;

  // Row 2: achievable score (CR-01: use OFFSET-form for neutralMin/neutralMax)
  const achievableLevel = deriveLevel(
    data.entry_expected_score_p_value,
    data.entry_expected_score_n,
  );
  const achievableZoneHex = entryExpectedScoreZoneColor(data.entry_expected_score);
  const achievableIsInColoredZone = achievableZoneHex !== ZONE_NEUTRAL;
  const achievableShowZoneFontColor =
    isConfident(achievableLevel) && achievableIsInColoredZone;
  const achievableColor: string | undefined = achievableShowZoneFontColor
    ? achievableZoneHex
    : undefined;
  const showAchievableChart =
    data.entry_expected_score_n >= MIN_GAMES_FOR_RELIABLE_STATS;

  return (
    <div className="charcoal-texture rounded-md p-4" data-testid="tile-at-endgame-entry">
      <h3 className="text-base font-semibold mb-2">At Endgame Entry</h3>
      <div className="flex flex-col gap-4">
        {/* Row 1: entry-eval bullet (pawns) */}
        {showEntryEvalChart ? (
          <div className="flex flex-col gap-2">
            <span className="flex items-center gap-1 text-sm tabular-nums w-full">
              <span className="text-muted-foreground">Endgame entry eval:</span>
              <span
                className="ml-auto font-semibold inline-flex items-center gap-0.5"
                style={evalColor ? { color: evalColor } : undefined}
                data-testid="entry-eval-value"
              >
                {formatSignedEvalPawns(data.entry_eval_mean_pawns)}
                <Cpu className="h-3.5 w-3.5" aria-hidden="true" />
              </span>
              <BulletConfidencePopover
                level={evalLevel}
                pValue={data.entry_eval_p_value}
                gameCount={data.entry_eval_n}
                evalMeanPawns={data.entry_eval_mean_pawns}
                // Endgame stats are color-agnostic — no baseline tick is
                // rendered, so suppress its legend line in the tooltip.
                // `color` is a required-prop fallback; with showBaselineTick
                // false it is not surfaced to the user.
                color="white"
                showBaselineTick={false}
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

        {/* Row 2: achievable score bullet (CR-01: OFFSET-form neutralMin/neutralMax). */}
        <div data-testid="endgame-achievable-score">
          {showAchievableChart ? (
            <div className="flex flex-col gap-2">
              <span className="flex items-center gap-1 text-sm tabular-nums w-full">
                <span className="text-muted-foreground">Achievable score:</span>
                <span
                  className="ml-auto font-semibold"
                  style={achievableColor ? { color: achievableColor } : undefined}
                  data-testid="achievable-score-value"
                >
                  {`${(data.entry_expected_score * 100).toFixed(0)}%`}
                </span>
                <AchievableScorePopover
                  score={data.entry_expected_score}
                  gameCount={data.entry_expected_score_n}
                  level={achievableLevel}
                  pValue={data.entry_expected_score_p_value ?? 1}
                />
              </span>
              <div className="min-w-0 tabular-nums">
                {/* MiniBulletChart neutralMin/neutralMax are OFFSETS from center; the
                    registry stores absolute bounds, so convert by subtracting center
                    (CR-01 fix: passing absolute bounds collapses the neutral band). */}
                <MiniBulletChart
                  value={data.entry_expected_score}
                  center={SCORE_BULLET_CENTER}
                  neutralMin={ENTRY_EXPECTED_SCORE_NEUTRAL_MIN - SCORE_BULLET_CENTER}
                  neutralMax={ENTRY_EXPECTED_SCORE_NEUTRAL_MAX - SCORE_BULLET_CENTER}
                  domain={ENDGAME_TILE_SCORE_DOMAIN}
                  ciLow={
                    data.entry_expected_score_ci_low != null
                      ? clampScoreCi(data.entry_expected_score_ci_low)
                      : undefined
                  }
                  ciHigh={
                    data.entry_expected_score_ci_high != null
                      ? clampScoreCi(data.entry_expected_score_ci_high)
                      : undefined
                  }
                  barColor="neutral"
                  ariaLabel={`Achievable score: ${(data.entry_expected_score * 100).toFixed(0)}%`}
                />
              </div>
            </div>
          ) : (
            <p className="text-sm text-muted-foreground py-4">Not enough data yet</p>
          )}
        </div>
      </div>
    </div>
  );
}

// ── Main export ────────────────────────────────────────────────────────────

export function EndgameOverallPerformanceSection({
  data,
  scoreGap,
}: {
  data: EndgamePerformanceResponse;
  scoreGap: ScoreGapMaterialResponse;
}) {
  // Score Gap: zone-only font color (no sig gating per D-04).
  const gapPositive = scoreGap.score_difference >= 0;
  const gapFormatted =
    (gapPositive ? '+' : '') + `${Math.round(scoreGap.score_difference * 100)}%`;
  const gapColor =
    scoreGap.score_difference >= SCORE_GAP_NEUTRAL_MAX
      ? ZONE_SUCCESS
      : scoreGap.score_difference >= SCORE_GAP_NEUTRAL_MIN
        ? ZONE_NEUTRAL
        : ZONE_DANGER;

  // Share of total games per card (Card 1 = without endgame, Card 3 = with endgame).
  const totalGames = data.non_endgame_wdl.total + data.endgame_wdl.total;
  const withoutShare = totalGames > 0 ? data.non_endgame_wdl.total / totalGames : 0;
  const withShare = totalGames > 0 ? data.endgame_wdl.total / totalGames : 0;

  return (
    <section data-testid="endgame-overall-performance-section">
      <p className="text-sm text-muted-foreground">
        Do you perform better or worse when games reach an endgame?
      </p>

      {/* 3-column card grid on lg+, stacked on mobile. DOM order: Card 1,
          Card 2, Card 3, ScoreGap. On desktop ScoreGap is lifted to column 2
          via lg:col-start-2. Inside-card layout is single-column at every
          breakpoint (label-above-chart) so the WDL/bullet charts get the
          full card width regardless of viewport. */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mt-2">
        {/* Card 1: Games without Endgame (left on desktop) */}
        <EndgameCard
          title="Games without Endgame"
          tileTestId="tile-games-without-endgame"
          scoreValueTestId="score-value-no"
          scorePopoverTestId="score-info-no"
          popoverAriaLabel="Games without Endgame score info"
          gamesCountTestId="games-count-no"
          wdl={data.non_endgame_wdl}
          pValue={data.non_endgame_score_p_value}
          gamesShare={withoutShare}
        />

        {/* Card 2: At Endgame Entry (center on desktop — no WDL bar) */}
        <EntryCard data={data} />

        {/* Card 3: Games with Endgame (right on desktop) */}
        <EndgameCard
          title="Games with Endgame"
          tileTestId="tile-games-with-endgame"
          scoreValueTestId="score-value-yes"
          scorePopoverTestId="score-info-yes"
          popoverAriaLabel="Games with Endgame score info"
          gamesCountTestId="games-count-yes"
          wdl={data.endgame_wdl}
          pValue={data.endgame_score_p_value}
          gamesShare={withShare}
        />

        {/* Endgame Score Gap: lg:col-start-2 places it under Card 2 on desktop.
            On mobile (single column) it falls naturally after Card 3. */}
        <div
          className="charcoal-texture rounded-md p-4 lg:col-start-2"
          data-testid="endgame-score-gap"
        >
          <h3 className="text-base font-semibold mb-2">Endgame Score Gap</h3>
          <div className="flex flex-col gap-2">
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
      </div>
    </section>
  );
}
