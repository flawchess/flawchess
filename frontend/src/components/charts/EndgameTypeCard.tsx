/**
 * Phase 87 — Per-class card shell for the 5-card Endgame Type Breakdown section.
 * Mirrors the Phase 86 EndgameMetricCard pattern with two metrics per card (Conv
 * + Recov gauges + peer bullets), a Games deep-link instead of a static games-
 * count span, and the per-card title InfoPopover from D-11. v1.17 single-bullet
 * doctrine per peer bullet.
 *
 * Sig-gating triple applied per metric: `isConfident(deriveLevel(p, n)) ∧
 * outside-neutral-band ∧ hasOpponent` paints the diff-percent inline color
 * (ZONE_DANGER below NEUTRAL_ZONE_MIN, ZONE_SUCCESS at/above NEUTRAL_ZONE_MAX).
 * Gauges always-colored, WDL bar untinted (POLISH-02 deferred to Phase 88).
 *
 * Empty / sparse handling (CONTEXT D-13 / D-14 / D-15):
 * - total === 0: gauge row opacity-50, "Not enough data yet" placeholder.
 * - opp sparse on a metric: replace THAT peer-bullet row with "n < N,
 *   baseline unavailable" muted text. Gauges + WDL still render.
 * - 0 < total < MIN_GAMES_FOR_RELIABLE_STATS: body wrapper gets UNRELIABLE_OPACITY,
 *   `n={total}` chip appears next to the title (full opacity).
 */

import type { CSSProperties, ReactNode } from 'react';

import { Link } from 'react-router-dom';
import { Swords } from 'lucide-react';

import { EndgameGauge } from '@/components/charts/EndgameGauge';
import { MiniBulletChart } from '@/components/charts/MiniBulletChart';
import { MetricStatPopover } from '@/components/popovers/MetricStatPopover';
import { MiniWDLBar } from '@/components/stats/MiniWDLBar';
import { InfoPopover } from '@/components/ui/info-popover';
import { Tooltip } from '@/components/ui/tooltip';
import {
  PER_CLASS_GAUGE_ZONES,
  type EndgameClassKey,
} from '@/generated/endgameZones';
import { isConfident } from '@/lib/significance';
import {
  MIN_GAMES_FOR_RELIABLE_STATS,
  UNRELIABLE_OPACITY,
  ZONE_DANGER,
  ZONE_SUCCESS,
  colorizeGaugeZones,
} from '@/lib/theme';
import {
  BULLET_DOMAIN,
  ENDGAME_CLASS_TO_SLUG,
  ENDGAME_TYPE_DESCRIPTIONS,
  MIN_OPPONENT_BASELINE_GAMES,
  NEUTRAL_ZONE_MAX,
  NEUTRAL_ZONE_MIN,
  SHOW_WDL_BAR_IN_TYPE_CARDS,
  formatDiffPct,
  formatScorePct,
} from '@/lib/endgameMetrics';
import type { EndgameCategoryStats, EndgameClass } from '@/types/endgames';

import { deriveLevel } from './EndgameOverallShared';

// Locked D-10 copy (Conv + Recov peer-bullet popover bodies).
const CONV_EXPLANATION =
  "Your win rate among games where you entered this Endgame Type with a Stockfish eval ≥ +1.0, compared to your opponents' win rate in the same situation across the same Endgame Type. Filter-responsive: baseline shifts with rating x TC x color x opponent-type filters.";

const RECOV_EXPLANATION =
  "Your save rate (wins + draws count) among games where you entered this Endgame Type with a Stockfish eval ≤ −1.0, compared to your opponents' save rate in the same situation across the same Endgame Type. Filter-responsive.";

const METHODOLOGY_BLOCK: ReactNode = (
  <>
    Score: per-bucket headline rate (Conv = wins, Recov = wins + draws).
    <br />
    Test: Wald-z on the signed difference vs 0.
    <br />
    Confidence interval: 95% normal-approx on the diff.
  </>
);

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

  // 0-1 scale values for peer-bullet displays. Gauges still consume the
  // 0-100 conversion_pct / recovery_pct directly via maxValue=100.
  const userConv = category.conversion.conversion_pct / 100;
  const oppConv = category.conversion.opp_conversion_pct;
  const userRecov = category.conversion.recovery_pct / 100;
  const oppRecov = category.conversion.opp_recovery_pct;

  const hasConvOpponent =
    oppConv !== null &&
    category.conversion.opp_conversion_games >= MIN_OPPONENT_BASELINE_GAMES;
  const hasRecovOpponent =
    oppRecov !== null &&
    category.conversion.opp_recovery_games >= MIN_OPPONENT_BASELINE_GAMES;

  const convDiff = hasConvOpponent ? userConv - (oppConv as number) : 0;
  const recovDiff = hasRecovOpponent ? userRecov - (oppRecov as number) : 0;

  // Sig-gating triple per peer bullet (CONTEXT D-09). The helper's
  // deriveLevel(p, n) returns 'low' when n < MIN_GAMES_FOR_RELIABLE_STATS or
  // p == null, so hasConvOpponent / hasRecovOpponent already cover the
  // sample-size floor; the extra `hasXxxOpponent` guard below is defensive.
  const convLevel = deriveLevel(
    category.conversion.conv_diff_p_value,
    category.conversion.opp_conversion_games,
  );
  const convOutsideNeutral =
    convDiff < NEUTRAL_ZONE_MIN || convDiff >= NEUTRAL_ZONE_MAX;
  const convPaint =
    hasConvOpponent && isConfident(convLevel) && convOutsideNeutral;
  const convDiffStyle: CSSProperties | undefined = convPaint
    ? { color: convDiff < NEUTRAL_ZONE_MIN ? ZONE_DANGER : ZONE_SUCCESS }
    : undefined;

  const recovLevel = deriveLevel(
    category.conversion.recov_diff_p_value,
    category.conversion.opp_recovery_games,
  );
  const recovOutsideNeutral =
    recovDiff < NEUTRAL_ZONE_MIN || recovDiff >= NEUTRAL_ZONE_MAX;
  const recovPaint =
    hasRecovOpponent && isConfident(recovLevel) && recovOutsideNeutral;
  const recovDiffStyle: CSSProperties | undefined = recovPaint
    ? { color: recovDiff < NEUTRAL_ZONE_MIN ? ZONE_DANGER : ZONE_SUCCESS }
    : undefined;

  // Gauge zones (per-class p25/p75 from PER_CLASS_GAUGE_ZONES). The Record
  // access is safe for all 6 known EndgameClass values; the defensive `!bands`
  // branch below should never trigger in production (pawnless is filtered
  // upstream via HIDDEN_ENDGAME_CLASSES at Endgames.tsx:53). We satisfy
  // noUncheckedIndexedAccess by treating a missing entry as "no data" and
  // rendering the empty-class shell.
  const classKey = category.endgame_class as EndgameClassKey;
  const bands = PER_CLASS_GAUGE_ZONES[classKey];

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
        {ENDGAME_TYPE_DESCRIPTIONS[
          category.endgame_class as Exclude<EndgameClass, 'pawnless'>
        ] ?? ''}
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

  // Empty-class shell (no games at all, or unknown class with no bands).
  if (!hasGames || !bands) {
    return (
      <div
        className="charcoal-texture rounded-md p-4"
        data-testid={tileTestId}
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
                zones={colorizeGaugeZones([
                  { from: 0, to: 1.0 },
                ])}
                size={130}
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
                zones={colorizeGaugeZones([
                  { from: 0, to: 1.0 },
                ])}
                size={130}
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

  const [convLower, convUpper] = bands.conversion;
  const [recovLower, recovUpper] = bands.recovery;
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
    <div className="charcoal-texture rounded-md p-4" data-testid={tileTestId}>
      {titleRow}
      <div className="flex flex-col gap-4" style={bodyStyle}>
        {/* Gauge row (Conv | Recov side-by-side). Per CONTEXT D-13, gauges
            stay rendered with opacity-50 when no games; here we already
            short-circuited the empty-class shell above, so this branch is
            always full opacity. */}
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
              size={130}
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
              size={130}
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

        {/* Conv peer-bullet row */}
        {hasConvOpponent ? (
          <div
            className="flex flex-col gap-2"
            data-testid={`${tileTestId}-conv-row`}
          >
            <span className="flex items-center gap-1 text-sm tabular-nums w-full flex-wrap">
              <span>
                <span className="text-muted-foreground">Conversion, You: </span>
                <span
                  className="font-medium"
                  data-testid={`${tileTestId}-conv-you`}
                >
                  {formatScorePct(userConv)}
                </span>
              </span>
              <span>
                <span className="text-muted-foreground">Opp: </span>
                <span
                  className="font-medium"
                  data-testid={`${tileTestId}-conv-opp`}
                >
                  {formatScorePct(oppConv as number)}
                </span>
              </span>
              <span>
                <span className="text-muted-foreground">Gap: </span>
                <span
                  className="font-semibold"
                  style={convDiffStyle}
                  data-testid={`${tileTestId}-conv-diff`}
                >
                  {formatDiffPct(userConv, oppConv as number)}
                </span>
              </span>
              <MetricStatPopover
                name="Conversion"
                explanation={CONV_EXPLANATION}
                value={convDiff}
                baseline={0}
                unit="percent"
                gameCount={category.conversion.opp_conversion_games}
                level={convLevel}
                pValue={category.conversion.conv_diff_p_value}
                vocabulary="score"
                neutralLower={NEUTRAL_ZONE_MIN}
                neutralUpper={NEUTRAL_ZONE_MAX}
                baselineLabel="0%"
                relative
                methodology={METHODOLOGY_BLOCK}
                testId={`${tileTestId}-conv-info`}
                ariaLabel="What is Conversion?"
              />
            </span>
            <div className="min-w-0 tabular-nums">
              <MiniBulletChart
                value={convDiff}
                neutralMin={NEUTRAL_ZONE_MIN}
                neutralMax={NEUTRAL_ZONE_MAX}
                domain={BULLET_DOMAIN}
                ciLow={category.conversion.conv_diff_ci_low ?? undefined}
                ciHigh={category.conversion.conv_diff_ci_high ?? undefined}
                barColor="neutral"
                ariaLabel={`Conversion: ${formatDiffPct(userConv, oppConv as number)} vs opponents`}
              />
            </div>
          </div>
        ) : (
          <span
            className="text-sm text-muted-foreground"
            data-testid={`${tileTestId}-conv-muted`}
          >
            Conversion, n &lt; {MIN_OPPONENT_BASELINE_GAMES}, baseline unavailable
          </span>
        )}

        {/* Recov peer-bullet row */}
        {hasRecovOpponent ? (
          <div
            className="flex flex-col gap-2"
            data-testid={`${tileTestId}-recov-row`}
          >
            <span className="flex items-center gap-1 text-sm tabular-nums w-full flex-wrap">
              <span>
                <span className="text-muted-foreground">Recovery, You: </span>
                <span
                  className="font-medium"
                  data-testid={`${tileTestId}-recov-you`}
                >
                  {formatScorePct(userRecov)}
                </span>
              </span>
              <span>
                <span className="text-muted-foreground">Opp: </span>
                <span
                  className="font-medium"
                  data-testid={`${tileTestId}-recov-opp`}
                >
                  {formatScorePct(oppRecov as number)}
                </span>
              </span>
              <span>
                <span className="text-muted-foreground">Gap: </span>
                <span
                  className="font-semibold"
                  style={recovDiffStyle}
                  data-testid={`${tileTestId}-recov-diff`}
                >
                  {formatDiffPct(userRecov, oppRecov as number)}
                </span>
              </span>
              <MetricStatPopover
                name="Recovery"
                explanation={RECOV_EXPLANATION}
                value={recovDiff}
                baseline={0}
                unit="percent"
                gameCount={category.conversion.opp_recovery_games}
                level={recovLevel}
                pValue={category.conversion.recov_diff_p_value}
                vocabulary="score"
                neutralLower={NEUTRAL_ZONE_MIN}
                neutralUpper={NEUTRAL_ZONE_MAX}
                baselineLabel="0%"
                relative
                methodology={METHODOLOGY_BLOCK}
                testId={`${tileTestId}-recov-info`}
                ariaLabel="What is Recovery?"
              />
            </span>
            <div className="min-w-0 tabular-nums">
              <MiniBulletChart
                value={recovDiff}
                neutralMin={NEUTRAL_ZONE_MIN}
                neutralMax={NEUTRAL_ZONE_MAX}
                domain={BULLET_DOMAIN}
                ciLow={category.conversion.recov_diff_ci_low ?? undefined}
                ciHigh={category.conversion.recov_diff_ci_high ?? undefined}
                barColor="neutral"
                ariaLabel={`Recovery: ${formatDiffPct(userRecov, oppRecov as number)} vs opponents`}
              />
            </div>
          </div>
        ) : (
          <span
            className="text-sm text-muted-foreground"
            data-testid={`${tileTestId}-recov-muted`}
          >
            Recovery, n &lt; {MIN_OPPONENT_BASELINE_GAMES}, baseline unavailable
          </span>
        )}
      </div>
    </div>
  );
}
