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
 * No section-root h3 or section-level popover — the question line under
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
import { useEffect, useRef, useState } from 'react';

import { MiniBulletChart } from '@/components/charts/MiniBulletChart';
import { BulletConfidencePopover } from '@/components/insights/BulletConfidencePopover';
import { ScoreConfidencePopover } from '@/components/insights/ScoreConfidencePopover';
import { AchievableScorePopover } from '@/components/popovers/AchievableScorePopover';
import { MiniWDLBar } from '@/components/stats/MiniWDLBar';
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
  scoreLabel: string;
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
  scoreLabel,
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
              <ScoreConfidencePopover
                level={level}
                pValue={pValue ?? 1}
                score={score}
                gameCount={total}
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
      <h3 className="text-base font-semibold mb-2 inline-flex items-center gap-1">
        <Cpu className="h-4 w-4" aria-hidden="true" />
        Eval at Endgame Entry
      </h3>
      <div className="flex flex-col gap-4">
        {/* Row 1: entry-eval bullet (pawns) */}
        {showEntryEvalChart ? (
          <div className="flex flex-col gap-2">
            <span className="flex items-center gap-1 text-sm tabular-nums w-full">
              <span className="text-muted-foreground">Endgame entry eval:</span>
              <span
                className="font-semibold inline-flex items-center gap-0.5"
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
                  className="font-semibold"
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

// ── Score Gap row (label + signed math + bullet chart) ────────────────────
//
// Used for both the Endgame Score Gap (with − without) and Endgame Score
// Loss (with − achievable) rows in the Score Gaps card. Both share the same
// bullet-chart settings (center=0, neutral band from SCORE_GAP_NEUTRAL_MIN /
// MAX, domain=SCORE_GAP_DOMAIN) and the same coloring rule (operand zone
// color only when significant + outside neutral; result colored only when
// both operands are significant + result outside neutral; else inherit).

interface ScoreGapRowProps {
  label: string;
  value: number;
  formatted: string;
  operand1Pct: string;
  operand1Color: string | undefined;
  operand2Pct: string;
  operand2Color: string | undefined;
  resultColor: string | undefined;
  showMath: boolean;
  mathTestId: string;
  valueTestId: string;
  ariaLabel: string;
}

function ScoreGapRow({
  label,
  value,
  formatted,
  operand1Pct,
  operand1Color,
  operand2Pct,
  operand2Color,
  resultColor,
  showMath,
  mathTestId,
  valueTestId,
  ariaLabel,
}: ScoreGapRowProps) {
  return (
    <div className="flex flex-col gap-2">
      <span className="flex items-center gap-1 text-sm tabular-nums w-full">
        <span className="text-muted-foreground">{label}</span>
        {showMath ? (
          <span className="tabular-nums" data-testid={mathTestId}>
            <span
              className="font-semibold"
              style={operand1Color ? { color: operand1Color } : undefined}
            >
              {operand1Pct}
            </span>
            {' − '}
            <span
              className="font-semibold"
              style={operand2Color ? { color: operand2Color } : undefined}
            >
              {operand2Pct}
            </span>
            {' = '}
            <span
              className="font-semibold"
              style={resultColor ? { color: resultColor } : undefined}
              data-testid={valueTestId}
            >
              {formatted}
            </span>
          </span>
        ) : (
          <span
            className="font-semibold"
            style={resultColor ? { color: resultColor } : undefined}
            data-testid={valueTestId}
          >
            {formatted}
          </span>
        )}
      </span>
      <div className="min-w-0 tabular-nums">
        <MiniBulletChart
          value={value}
          center={0}
          neutralMin={SCORE_GAP_NEUTRAL_MIN}
          neutralMax={SCORE_GAP_NEUTRAL_MAX}
          domain={SCORE_GAP_DOMAIN}
          barColor="neutral"
          ariaLabel={ariaLabel}
        />
      </div>
    </div>
  );
}

// ── Connector arrows (desktop only) ───────────────────────────────────────
//
// Three arrows rendered as charcoal-textured div segments:
//   Card 1 bottom-center → drops down → turns right → Score Gap left-center
//   Card 3 bottom-center → drops down → turns left  → Score Gap right-center
//   Card 2 bottom-center → drops straight down      → Score Gap top-center
// Positions are measured from the live DOM (card heights vary with content)
// and recomputed on resize. Hidden on mobile via the stacked-layout check
// below and `hidden lg:block` on the wrapper.

// Line thickness matches the MiniWDLBar / MiniBulletChart row height
// (Tailwind h-5 = 20px) so the connectors visually weigh the same as the
// charts they tie together.
const ARROW_BAR_PX = 20;
const ARROW_HEAD_LEN_PX = 26; // protrusion past the trunk end
const ARROW_HEAD_HALF_HEIGHT_PX = 22; // flare past the trunk center on each side

interface ArrowGeom {
  c1x: number;
  c1Bottom: number;
  c2x: number;
  c2Bottom: number;
  c3x: number;
  c3Bottom: number;
  sgLeftEdge: number;
  sgRightEdge: number;
  sgTop: number;
  sgMidY: number;
}

function ConnectorArrows({
  containerRef,
}: {
  containerRef: React.RefObject<HTMLDivElement | null>;
}) {
  const [geom, setGeom] = useState<ArrowGeom | null>(null);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    function compute() {
      if (!container) return;
      const c1 = container.querySelector<HTMLElement>(
        '[data-testid="tile-games-without-endgame"]',
      );
      const c2 = container.querySelector<HTMLElement>(
        '[data-testid="tile-at-endgame-entry"]',
      );
      const c3 = container.querySelector<HTMLElement>(
        '[data-testid="tile-games-with-endgame"]',
      );
      const sg = container.querySelector<HTMLElement>(
        '[data-testid="endgame-score-gap"]',
      );
      if (!c1 || !c2 || !c3 || !sg) {
        setGeom(null);
        return;
      }
      const wr = container.getBoundingClientRect();
      const c1r = c1.getBoundingClientRect();
      const c2r = c2.getBoundingClientRect();
      const c3r = c3.getBoundingClientRect();
      const sgr = sg.getBoundingClientRect();

      // Mobile (stacked single-column): score gap card's left edge aligns
      // with Card 1's left edge. Bail to avoid drawing arrows that don't
      // visually make sense in the stacked layout.
      if (sgr.left <= c1r.left + 2) {
        setGeom(null);
        return;
      }

      setGeom({
        c1x: c1r.left + c1r.width / 2 - wr.left,
        c1Bottom: c1r.bottom - wr.top,
        c2x: c2r.left + c2r.width / 2 - wr.left,
        c2Bottom: c2r.bottom - wr.top,
        c3x: c3r.left + c3r.width / 2 - wr.left,
        c3Bottom: c3r.bottom - wr.top,
        sgLeftEdge: sgr.left - wr.left,
        sgRightEdge: sgr.right - wr.left,
        sgTop: sgr.top - wr.top,
        sgMidY: sgr.top + sgr.height / 2 - wr.top,
      });
    }

    compute();
    const ro = new ResizeObserver(compute);
    ro.observe(container);
    return () => ro.disconnect();
  }, [containerRef]);

  if (!geom) return null;

  const HALF_BAR = ARROW_BAR_PX / 2;
  const HEAD = ARROW_HEAD_LEN_PX;
  const HALF_HEAD_H = ARROW_HEAD_HALF_HEIGHT_PX;

  // Arrow 1: Card 1 → Score Gap left edge (arrowhead points right)
  // Vertical drops from Card 1 bottom to the horizontal trunk's bottom edge
  // (sgMidY + HALF_BAR), covering the corner block with a single rectangle.
  const a1V = {
    left: geom.c1x - HALF_BAR,
    top: geom.c1Bottom,
    width: ARROW_BAR_PX,
    height: geom.sgMidY + HALF_BAR - geom.c1Bottom,
  };
  // Horizontal trunk starts at the vertical's left edge and ends where the
  // arrowhead begins.
  const a1H = {
    left: geom.c1x - HALF_BAR,
    top: geom.sgMidY - HALF_BAR,
    width: geom.sgLeftEdge - HEAD - (geom.c1x - HALF_BAR),
    height: ARROW_BAR_PX,
  };
  const a1Head = {
    left: geom.sgLeftEdge - HEAD,
    top: geom.sgMidY - HALF_HEAD_H,
    width: HEAD,
    height: HALF_HEAD_H * 2,
    clipPath: 'polygon(0 0, 100% 50%, 0 100%)',
  };

  // Arrow 2: Card 3 → Score Gap right edge (arrowhead points left)
  const a2V = {
    left: geom.c3x - HALF_BAR,
    top: geom.c3Bottom,
    width: ARROW_BAR_PX,
    height: geom.sgMidY + HALF_BAR - geom.c3Bottom,
  };
  const a2H = {
    left: geom.sgRightEdge + HEAD,
    top: geom.sgMidY - HALF_BAR,
    width: geom.c3x + HALF_BAR - (geom.sgRightEdge + HEAD),
    height: ARROW_BAR_PX,
  };
  const a2Head = {
    left: geom.sgRightEdge,
    top: geom.sgMidY - HALF_HEAD_H,
    width: HEAD,
    height: HALF_HEAD_H * 2,
    clipPath: 'polygon(100% 0, 0 50%, 100% 100%)',
  };

  // Arrow 3: Card 2 → Score Gaps top edge (arrowhead points down)
  const a3V = {
    left: geom.c2x - HALF_BAR,
    top: geom.c2Bottom,
    width: ARROW_BAR_PX,
    height: geom.sgTop - HEAD - geom.c2Bottom,
  };
  const a3Head = {
    left: geom.c2x - HALF_HEAD_H,
    top: geom.sgTop - HEAD,
    width: HALF_HEAD_H * 2,
    height: HEAD,
    clipPath: 'polygon(0 0, 100% 0, 50% 100%)',
  };

  // `!absolute` overrides .charcoal-texture's `position: relative`. The class
  // already sets `overflow: hidden`, so clip-path on the arrowhead also clips
  // the noise pseudo-element to the triangle shape.
  const segmentClass = 'charcoal-texture !absolute';

  return (
    <div
      className="absolute inset-0 hidden lg:block pointer-events-none"
      aria-hidden="true"
    >
      <div className={segmentClass} style={a1V} />
      <div className={segmentClass} style={a1H} />
      <div className={segmentClass} style={a1Head} />
      <div className={segmentClass} style={a2V} />
      <div className={segmentClass} style={a2H} />
      <div className={segmentClass} style={a2Head} />
      <div className={segmentClass} style={a3V} />
      <div className={segmentClass} style={a3Head} />
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
  const gapPositive = scoreGap.score_difference >= 0;
  const gapFormatted =
    (gapPositive ? '+' : '') + `${Math.round(scoreGap.score_difference * 100)}%`;

  // Share of total games per card (Card 1 = without endgame, Card 3 = with endgame).
  const totalGames = data.non_endgame_wdl.total + data.endgame_wdl.total;
  const withoutShare = totalGames > 0 ? data.non_endgame_wdl.total / totalGames : 0;
  const withShare = totalGames > 0 ? data.endgame_wdl.total / totalGames : 0;

  // Per-card scores for the Score Gap math expression. Operand coloring
  // mirrors the per-card Score row: zone color only when the score is
  // significant AND outside the neutral (blue) zone; otherwise inherit
  // (white). Math order is `<with> − <without> = <gap>` to match the
  // API's `score_difference = endgame - non_endgame` sign convention
  // (positive = endgame better) and the bullet chart's zone meanings.
  const withoutScore =
    data.non_endgame_wdl.total > 0
      ? (data.non_endgame_wdl.wins + 0.5 * data.non_endgame_wdl.draws) /
        data.non_endgame_wdl.total
      : 0;
  const withScore =
    data.endgame_wdl.total > 0
      ? (data.endgame_wdl.wins + 0.5 * data.endgame_wdl.draws) /
        data.endgame_wdl.total
      : 0;
  const withoutLevel = deriveLevel(
    data.non_endgame_score_p_value,
    data.non_endgame_wdl.total,
  );
  const withLevel = deriveLevel(
    data.endgame_score_p_value,
    data.endgame_wdl.total,
  );
  function operandColor(
    score: number,
    level: ConfidenceLevel,
  ): string | undefined {
    const zoneHex = scoreZoneColor(score);
    const inColoredZone = zoneHex !== ZONE_NEUTRAL;
    return isConfident(level) && inColoredZone ? zoneHex : undefined;
  }
  const withoutScoreColor = operandColor(withoutScore, withoutLevel);
  const withScoreColor = operandColor(withScore, withLevel);
  const showGapMath =
    data.non_endgame_wdl.total > 0 && data.endgame_wdl.total > 0;
  const withoutScorePct = `${Math.round(withoutScore * 100)}%`;
  const withScorePct = `${Math.round(withScore * 100)}%`;

  // Score Gap / Score Loss result is always tinted by zone (red / blue / green),
  // never default-white. Significance gating applies to the operand (score)
  // values via operandColor, but the difference itself reads as a zone signal
  // regardless of confidence so the user always sees where they land.
  function gapZoneColor(value: number): string {
    if (value < SCORE_GAP_NEUTRAL_MIN) return ZONE_DANGER;
    if (value >= SCORE_GAP_NEUTRAL_MAX) return ZONE_SUCCESS;
    return ZONE_NEUTRAL;
  }
  const gapColor = gapZoneColor(scoreGap.score_difference);

  // Endgame Score Loss: how much the actual endgame score fell short of
  // (or exceeded) the achievable score expected from the entry eval.
  // Same math format, colors, and bullet settings as the Score Gap.
  const achievableScore = data.entry_expected_score;
  const achievableLevel = deriveLevel(
    data.entry_expected_score_p_value,
    data.entry_expected_score_n,
  );
  const achievableScoreColor = operandColor(achievableScore, achievableLevel);
  const achievableScorePct = `${Math.round(achievableScore * 100)}%`;
  const lossValue = withScore - achievableScore;
  const lossPositive = lossValue >= 0;
  const lossFormatted =
    (lossPositive ? '+' : '') + `${Math.round(lossValue * 100)}%`;
  const showLossMath =
    data.endgame_wdl.total > 0 && data.entry_expected_score_n > 0;
  const lossColor = gapZoneColor(lossValue);

  const gridRef = useRef<HTMLDivElement>(null);

  return (
    <section data-testid="endgame-overall-performance-section">
      <p className="text-sm text-muted-foreground">
        Do you perform better or worse when games reach an endgame?
      </p>

      {/* 3-column card grid on lg+, stacked on mobile. DOM order: Card 1,
          Card 2, Card 3, ScoreGap. On desktop ScoreGap is lifted to column 2
          via lg:col-start-2. Inside-card layout is single-column at every
          breakpoint (label-above-chart) so the WDL/bullet charts get the
          full card width regardless of viewport. `relative` anchors the
          ConnectorArrows SVG overlay (desktop only). */}
      <div
        ref={gridRef}
        className="relative grid grid-cols-1 lg:grid-cols-3 gap-4 mt-2"
      >
        {/* Card 1: Games without Endgame (left on desktop) */}
        <EndgameCard
          title="Games without Endgame"
          scoreLabel="Score:"
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
          scoreLabel="Endgame Score:"
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
          className="charcoal-texture rounded-md p-4 lg:col-start-2 lg:mt-8"
          data-testid="endgame-score-gap"
        >
          <h3 className="text-base font-semibold mb-2">Endgame Score Differences</h3>
          <div className="flex flex-col gap-4">
            <ScoreGapRow
              label="Endgame Score Gap:"
              value={scoreGap.score_difference}
              formatted={gapFormatted}
              operand1Pct={withScorePct}
              operand1Color={withScoreColor}
              operand2Pct={withoutScorePct}
              operand2Color={withoutScoreColor}
              resultColor={gapColor}
              showMath={showGapMath}
              mathTestId="score-gap-math"
              valueTestId="score-gap-difference"
              ariaLabel={`Endgame vs non-endgame score gap: ${gapFormatted}`}
            />
            <ScoreGapRow
              label="Endgame Score Loss:"
              value={lossValue}
              formatted={lossFormatted}
              operand1Pct={withScorePct}
              operand1Color={withScoreColor}
              operand2Pct={achievableScorePct}
              operand2Color={achievableScoreColor}
              resultColor={lossColor}
              showMath={showLossMath}
              mathTestId="endgame-score-loss-math"
              valueTestId="endgame-score-loss-value"
              ariaLabel={`Endgame score loss: ${lossFormatted}`}
            />
          </div>
        </div>

        <ConnectorArrows containerRef={gridRef} />
      </div>
    </section>
  );
}
