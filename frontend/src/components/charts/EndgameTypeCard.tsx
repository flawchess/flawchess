/**
 * Phase 87 follow-up — Per-class card shell for the 5-card Endgame Type
 * Breakdown section. Replaces the original Conv + Recov peer-diff bullet rows
 * (which always rendered the same magnitude because of the same-game mirror
 * identity) with a SINGLE chess-score bullet using the same pattern as the
 * "Games with Endgame" card (see EndgameOverallCard / EndgameCard). The two
 * per-class gauges (Conversion, Recovery) at the top of each card are kept.
 *
 * Card structure (top-to-bottom):
 *   1. Title + per-card title InfoPopover + optional n={total} chip.
 *   2. Side-by-side Conv + Recov gauges (unchanged).
 *   3. WDL bar row with the Games deep-link.
 *   4. Score bullet (W + 0.5*D / N) sig-gated against 50%.
 *   5. Per-span Score Gap bullet (eval-based, Cpu-iconed) — Phase 87.1.
 *
 * Empty / sparse handling (CONTEXT D-13 / D-14 / D-15):
 * - total === 0: gauge row opacity-50, "Not enough data yet" placeholder, no
 *   WDL / Score row, no Games link.
 * - 0 < total < MIN_GAMES_FOR_RELIABLE_STATS: body wrapper gets UNRELIABLE_OPACITY,
 *   `n={total}` chip appears next to the title (full opacity). Score row hidden.
 */

import type { CSSProperties } from 'react';

import { Link } from 'react-router-dom';
import { Cpu, Swords } from 'lucide-react';

import { EndgameGauge } from '@/components/charts/EndgameGauge';
import { MiniBulletChart } from '@/components/charts/MiniBulletChart';
import { MetricStatPopover } from '@/components/popovers/MetricStatPopover';
import { MiniWDLBar } from '@/components/stats/MiniWDLBar';
import { InfoPopover } from '@/components/ui/info-popover';
import { Tooltip } from '@/components/ui/tooltip';
// Frontend constant names use the user-facing "ENDGAME_TYPE_SCORE_GAP" form;
// internal identifier is `endgame_type_achievable_score_gap` (see
// app/services/endgame_zones.py). Dual-label scheme per CONTEXT D-02.
import {
  ENDGAME_TYPE_SCORE_GAP_NEUTRAL_MAX,
  ENDGAME_TYPE_SCORE_GAP_NEUTRAL_MIN,
  PER_CLASS_GAUGE_ZONES,
} from '@/generated/endgameZones';
import {
  SCORE_BULLET_CENTER,
  SCORE_BULLET_NEUTRAL_MAX,
  SCORE_BULLET_NEUTRAL_MIN,
  clampScoreCi,
  scoreZoneColor,
} from '@/lib/scoreBulletConfig';
import { wilsonBounds } from '@/lib/scoreConfidence';
import { isConfident } from '@/lib/significance';
import {
  MIN_GAMES_FOR_RELIABLE_STATS,
  UNRELIABLE_OPACITY,
  ZONE_DANGER,
  ZONE_NEUTRAL,
  ZONE_SUCCESS,
  colorizeGaugeZones,
} from '@/lib/theme';
import {
  ENDGAME_CLASS_TO_SLUG,
  ENDGAME_TYPE_DESCRIPTIONS,
  SHOW_WDL_BAR_IN_TYPE_CARDS,
} from '@/lib/endgameMetrics';
import type { EndgameCategoryStats, EndgameClass } from '@/types/endgames';

import { ScoreGapRow } from './EndgameOverallScoreGapRow';
import {
  ENDGAME_TILE_SCORE_DOMAIN,
  ENDGAME_TYPE_SCORE_GAP_DOMAIN,
  deriveLevel,
} from './EndgameOverallShared';

// Per-card gauge size — extracted per REVIEW IN-02 (was hard-coded 4 times).
const PER_TYPE_GAUGE_SIZE = 130;

// Score-vs-50% neutral band, mirrors EndgameOverallCard (260514-i3l). Kept inline
// rather than re-importing because the bounds are the same one-line constants.
const SCORE_NEUTRAL_LOWER = 0.45;
const SCORE_NEUTRAL_UPPER = 0.55;

export interface EndgameTypeCardProps {
  category: EndgameCategoryStats;
  sharePct: number;
  onCategorySelect: (cls: EndgameClass) => void;
  tileTestId: string;
}

export function EndgameTypeCard({
  category,
  sharePct,
  onCategorySelect,
  tileTestId,
}: EndgameTypeCardProps) {
  const slug = ENDGAME_CLASS_TO_SLUG[category.endgame_class];
  const hasGames = category.total > 0;
  const isUnreliable =
    hasGames && category.total < MIN_GAMES_FOR_RELIABLE_STATS;
  const bodyStyle: CSSProperties | undefined = isUnreliable
    ? { opacity: UNRELIABLE_OPACITY }
    : undefined;

  // Score derivation mirrors EndgameOverallCard:70-79. n=0 short-circuits to 0
  // so the call is well-defined; the score row is hidden below the sample-size
  // gate so this only ever renders for total >= MIN_GAMES_FOR_RELIABLE_STATS.
  const total = category.total;
  const score = total > 0 ? (category.wins + 0.5 * category.draws) / total : 0;
  const level = deriveLevel(category.score_p_value, total);
  const zoneHex = scoreZoneColor(score);
  const isInColoredZone = zoneHex !== ZONE_NEUTRAL;
  const scoreShowZoneFontColor = isConfident(level) && isInColoredZone;
  const scoreColor: string | undefined = scoreShowZoneFontColor ? zoneHex : undefined;
  const [ciLow, ciHigh] = wilsonBounds(score, total);
  const showScoreRow = total >= MIN_GAMES_FOR_RELIABLE_STATS;
  const scorePct = `${Math.round(score * 100)}%`;

  // Phase 87.1 (SEED-016 D-08): per-span Score Gap derivation.
  // gapZoneColor mirrors EndgameOverallPerformanceSection — zone-only tint
  // (Phase 85.1 D-04), no sig-gate on the row's font color. Hidden at n=0.
  const gapMean = category.type_achievable_score_gap_mean;
  const gapN = category.type_achievable_score_gap_n ?? 0;
  const showGapRow = gapN > 0;
  const gapFormatted =
    gapMean != null
      ? (gapMean >= 0 ? '+' : '') + `${Math.round(gapMean * 100)}%`
      : '—';
  const gapColor: string | undefined =
    gapMean != null
      ? gapMean < ENDGAME_TYPE_SCORE_GAP_NEUTRAL_MIN
        ? ZONE_DANGER
        : gapMean >= ENDGAME_TYPE_SCORE_GAP_NEUTRAL_MAX
          ? ZONE_SUCCESS
          : undefined
      : undefined;
  const gapLevel = deriveLevel(category.type_achievable_score_gap_p_value, gapN);

  // Per-class gauge zones (p25/p75 bands from the generated registry). With
  // `pawnless` filtered upstream and the union of registry keys covering the
  // remaining 5 classes, the explicit guard documents the contract instead of
  // relying on a runtime fallback (REVIEW WR-04).
  const bands =
    category.endgame_class !== 'pawnless'
      ? PER_CLASS_GAUGE_ZONES[category.endgame_class]
      : undefined;
  // REVIEW WR-03: pawnless guard surfaces missing descriptions during dev
  // rather than silently emitting an empty popover via a `?? ''` fallback.
  const typeDescription =
    category.endgame_class !== 'pawnless'
      ? ENDGAME_TYPE_DESCRIPTIONS[category.endgame_class]
      : '';

  const sharePctFormatted = sharePct.toFixed(1);
  const gamesCountFormatted = category.total.toLocaleString();

  const titleRow = (
    <h3 className="text-base font-semibold mb-2 inline-flex items-center gap-1">
      <span>{category.label}</span>
      <InfoPopover
        ariaLabel={`${category.label} info`}
        testId={`${tileTestId}-title-info`}
        side="top"
      >
        <p>
          <strong>{category.label}:</strong> {typeDescription}
        </p>
      </InfoPopover>
      {isUnreliable && (
        <span
          className="ml-2 text-sm text-muted-foreground tabular-nums"
          data-testid={`${tileTestId}-n-chip`}
        >
          n={category.total}
        </span>
      )}
    </h3>
  );

  // Empty-class shell (no games at all). REVIEW WR-04: dropped the redundant
  // !bands branch — bands existence is guaranteed for the 5 non-pawnless
  // classes via the generated registry, so the `!hasGames` path is the only
  // empty case.
  if (!hasGames) {
    return (
      <div
        className="charcoal-texture rounded-md p-4"
        data-testid={tileTestId}
        role="group"
        aria-label={`${category.label} endgame breakdown`}
      >
        {titleRow}
        <div className="flex flex-col gap-4">
          <div
            className="grid grid-cols-2 gap-2 opacity-50"
            data-testid={`${tileTestId}-gauges`}
          >
            <div
              className="flex flex-col items-center"
              data-testid={`${tileTestId}-conv-gauge`}
            >
              <div className="text-sm text-muted-foreground mb-1">
                Conversion
              </div>
              <EndgameGauge
                value={0}
                maxValue={100}
                label="Conversion"
                zones={colorizeGaugeZones([{ from: 0, to: 1.0 }])}
                size={PER_TYPE_GAUGE_SIZE}
              />
            </div>
            <div
              className="flex flex-col items-center"
              data-testid={`${tileTestId}-recov-gauge`}
            >
              <div className="text-sm text-muted-foreground mb-1">Recovery</div>
              <EndgameGauge
                value={0}
                maxValue={100}
                label="Recovery"
                zones={colorizeGaugeZones([{ from: 0, to: 1.0 }])}
                size={PER_TYPE_GAUGE_SIZE}
              />
            </div>
          </div>
          <p className="text-sm text-muted-foreground py-4">
            Not enough data yet
          </p>
        </div>
      </div>
    );
  }

  // bands is non-undefined here: hasGames implies a non-pawnless class with a
  // registry entry (HIDDEN_ENDGAME_CLASSES filters pawnless upstream).
  const [convLower, convUpper] = bands!.conversion;
  const [recovLower, recovUpper] = bands!.recovery;
  const convZones = colorizeGaugeZones([
    { from: 0, to: convLower },
    { from: convLower, to: convUpper },
    { from: convUpper, to: 1.0 },
  ]);
  const recovZones = colorizeGaugeZones([
    { from: 0, to: recovLower },
    { from: recovLower, to: recovUpper },
    { from: recovUpper, to: 1.0 },
  ]);

  const gamesLink = (
    <Tooltip content={`View ${category.label} endgame games`}>
      <Link
        to={`/endgames/games?type=${slug}`}
        onClick={() => onCategorySelect(category.endgame_class)}
        className="ml-auto inline-flex items-center gap-1 text-sm text-brand-brown-light hover:text-brand-brown-highlight tabular-nums whitespace-nowrap transition-colors"
        aria-label={`View ${category.label} endgame games`}
        data-testid={`${tileTestId}-games-link`}
      >
        <span>
          Games: {sharePctFormatted}% ({gamesCountFormatted})
        </span>
        <Swords className="h-3.5 w-3.5" aria-hidden="true" />
      </Link>
    </Tooltip>
  );

  return (
    <div
      className="charcoal-texture rounded-md p-4"
      data-testid={tileTestId}
      role="group"
      aria-label={`${category.label} endgame breakdown`}
    >
      {titleRow}
      <div className="flex flex-col gap-4" style={bodyStyle}>
        {/* Gauge row (Conv | Recov side-by-side). Gauges are always rendered
            with full opacity here; the empty-class shell above handles
            total === 0. */}
        <div
          className="grid grid-cols-2 gap-2"
          data-testid={`${tileTestId}-gauges`}
        >
          <div
            className="flex flex-col items-center"
            data-testid={`${tileTestId}-conv-gauge`}
          >
            <div className="text-sm text-muted-foreground mb-1">Conversion</div>
            <EndgameGauge
              value={category.conversion.conversion_pct}
              maxValue={100}
              label="Conversion"
              zones={convZones}
              size={PER_TYPE_GAUGE_SIZE}
            />
          </div>
          <div
            className="flex flex-col items-center"
            data-testid={`${tileTestId}-recov-gauge`}
          >
            <div className="text-sm text-muted-foreground mb-1">Recovery</div>
            <EndgameGauge
              value={category.conversion.recovery_pct}
              maxValue={100}
              label="Recovery"
              zones={recovZones}
              size={PER_TYPE_GAUGE_SIZE}
            />
          </div>
        </div>

        {SHOW_WDL_BAR_IN_TYPE_CARDS ? (
          <div className="flex flex-col gap-2">
            <span className="flex items-center gap-2 text-sm tabular-nums w-full">
              <span className="text-muted-foreground">Win/Draw/Loss</span>
              {gamesLink}
            </span>
            <div
              className="min-w-0"
              data-testid={`${tileTestId}-wdl`}
              aria-label={`${category.label} win/draw/loss distribution`}
            >
              <MiniWDLBar
                win_pct={category.win_pct}
                draw_pct={category.draw_pct}
                loss_pct={category.loss_pct}
              />
            </div>
          </div>
        ) : (
          <div className="flex w-full">{gamesLink}</div>
        )}

        {/* Single Score bullet replacing the Conv+Recov peer-diff bullets.
            Mirrors EndgameOverallCard:113-160. */}
        {showScoreRow && (
          <div
            className="flex flex-col gap-2"
            data-testid={`${tileTestId}-score-row`}
          >
            <span className="flex items-center gap-1 text-sm tabular-nums w-full">
              <span className="text-muted-foreground">{category.label} Endgame Score:</span>
              <span
                className="font-semibold"
                style={scoreColor ? { color: scoreColor } : undefined}
                data-testid={`${tileTestId}-score-value`}
              >
                {scorePct}
              </span>
              <MetricStatPopover
                name={`${category.label} Endgame Score`}
                explanation={`Your win rate (draws counted as half) across ${category.label} endgames, tested against the 50% baseline.`}
                value={score}
                baseline={0.5}
                unit="percent"
                gameCount={total}
                level={level}
                pValue={category.score_p_value}
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
                testId={`${tileTestId}-score-info`}
                ariaLabel={`What is ${category.label} Endgame Score?`}
              />
            </span>
            <div
              className="min-w-0 tabular-nums"
              data-testid={`${tileTestId}-score-bullet`}
            >
              <MiniBulletChart
                value={score}
                center={SCORE_BULLET_CENTER}
                neutralMin={SCORE_BULLET_NEUTRAL_MIN}
                neutralMax={SCORE_BULLET_NEUTRAL_MAX}
                domain={ENDGAME_TILE_SCORE_DOMAIN}
                ciLow={clampScoreCi(ciLow)}
                ciHigh={clampScoreCi(ciHigh)}
                barColor="neutral"
                ariaLabel={`${category.label} endgame score ${scorePct}`}
              />
            </div>
          </div>
        )}

        {/* Phase 87.1 (SEED-016 D-08): per-span Score Gap bullet row.
            Positioned last in the card; Cpu icon flags this as eval-based.
            Card row label is "Score Gap" (short form per D-02); card title
            ("Rook Endgames" etc.) supplies the disambiguating type context. */}
        {showGapRow && (
          <div data-testid={`${tileTestId}-asg-bullet`}>
            <ScoreGapRow
              label={
                <span className="inline-flex items-center gap-1">
                  <Cpu className="h-3.5 w-3.5" aria-hidden="true" />
                  Score Gap:
                </span>
              }
              value={gapMean ?? 0}
              formatted={gapFormatted}
              resultColor={gapColor}
              valueTestId={`${tileTestId}-asg-value`}
              ariaLabel={`${category.label} Score Gap: ${gapFormatted}`}
              neutralMin={ENDGAME_TYPE_SCORE_GAP_NEUTRAL_MIN}
              neutralMax={ENDGAME_TYPE_SCORE_GAP_NEUTRAL_MAX}
              domain={ENDGAME_TYPE_SCORE_GAP_DOMAIN}
              ciLow={category.type_achievable_score_gap_ci_low ?? undefined}
              ciHigh={category.type_achievable_score_gap_ci_high ?? undefined}
              tooltip={
                <MetricStatPopover
                  name="Score Gap"
                  explanation={`Each ${category.label} Endgame Sequence has a start Stockfish eval and an end eval, or the actual game result for the final sequence in a game. Both get converted to expected scores via the Lichess expected-score formula. The Score Gap is the average of (end − start) across all your ${category.label} sequences: positive = you outperformed expectation, negative = you gave back score.`}
                  value={gapMean ?? 0}
                  baseline={0}
                  unit="percent"
                  gameCount={gapN}
                  level={gapLevel}
                  pValue={category.type_achievable_score_gap_p_value}
                  vocabulary="score"
                  neutralLower={ENDGAME_TYPE_SCORE_GAP_NEUTRAL_MIN}
                  neutralUpper={ENDGAME_TYPE_SCORE_GAP_NEUTRAL_MAX}
                  baselineLabel="0%"
                  methodology={
                    <>
                      Score: wins + ½ draws (game result for terminal spans).<br />
                      Test: paired one-sample z-test on per-span (exit − entry expected) diffs vs 0.<br />
                      Confidence interval: 95% normal-approx on the paired diffs.
                    </>
                  }
                  testId={`${tileTestId}-asg-info`}
                  ariaLabel={`What is ${category.label} Score Gap?`}
                />
              }
            />
          </div>
        )}
      </div>
    </div>
  );
}
