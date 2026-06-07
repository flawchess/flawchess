/**
 * EvalChart — per-game expected-score area chart (Phase 109, LIBG-10).
 *
 * White-perspective ES per ply, filled from the 0.5 midline with two-region
 * shading (light grey >0.5 / near-black <0.5), a 50% midline, at most two
 * phase-transition vertical lines
 * (middlegame, endgame — no ply-0 line per D-06), and dual-marker flaw dots
 * (filled = player, hollow = opponent, color = severity — D-07).
 *
 * Flaw dots use a custom `dot` render prop on an invisible <Line> overlay inside
 * ComposedChart — the established EndgameClockDiffOverTimeChart pattern. This
 * replaces the previously considered <Scatter> approach; recharts 3.8.1 Scatter
 * uses area-based `size` not radius `r`, making pixel-precise sizing unreliable.
 */

import { useId, useState } from 'react';
import { Area, ComposedChart, Line, ReferenceLine, XAxis, YAxis } from 'recharts';
import { ChartContainer, ChartTooltip } from '@/components/ui/chart';
import {
  EVAL_CHART_AREA_BLACK_AHEAD,
  EVAL_CHART_AREA_WHITE_AHEAD,
  EVAL_CHART_LINE,
  EVAL_CHART_MIDLINE,
  EVAL_CHART_PHASE_LINE,
  SEV_BLUNDER,
  SEV_INACCURACY,
  SEV_MISTAKE,
} from '@/lib/theme';
import type {
  EvalPoint,
  FlawMarker,
  FlawSeverity,
  FlawTag,
  PhaseTransitions,
} from '@/types/library';

// ─── Props ────────────────────────────────────────────────────────────────────

interface EvalChartProps {
  gameId: number;
  evalSeries: EvalPoint[];
  flawMarkers: FlawMarker[];
  phaseTransitions: PhaseTransitions;
  /** SAN mainline (moves[i] = move at ply i) — labels the tooltip for any ply. */
  moves: string[];
  /** Tailwind height class — 'h-24' (desktop default) or 'h-20' (mobile). */
  heightClass?: string;
  /**
   * Fired with the exact hovered ply (null on mouse-leave) so the parent card can
   * drive its miniboard to that position. No snapping — the crosshair, tooltip,
   * and board all track the precise hovered ply.
   */
  onHoverPlyChange?: (ply: number | null) => void;
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

/** Map FlawSeverity to its theme color constant. No inline literals. */
function severityColor(sev: FlawSeverity): string {
  if (sev === 'blunder') return SEV_BLUNDER;
  if (sev === 'mistake') return SEV_MISTAKE;
  return SEV_INACCURACY;
}

/** ES midline — the area fills from here, and the gradient splits here. */
const ES_MIDLINE = 0.5;

/** Game-phase tags — excluded from the tooltip tag list (shown via phase lines). */
const PHASE_TAGS: ReadonlySet<FlawTag> = new Set(['opening', 'middlegame', 'endgame']);

/**
 * Fraction (0–1, from the top) of the filled area's bounding box where ES=0.5
 * falls. The Area fills from the 0.5 baseline, so its bbox spans
 * [min(ES,0.5), max(ES,0.5)]; an SVG `objectBoundingBox` gradient maps 0→top,
 * 1→bottom. Placing the white/black colour stops at this offset pins the colour
 * split to the 50% midline regardless of how far the eval swings (previously a
 * hard-coded 50% stop sat below the midline whenever the eval never reached the
 * chart top/bottom).
 */
function midlineGradientOffset(series: EvalPoint[]): number {
  const values = series.map((p) => p.es).filter((v): v is number => v != null);
  const top = Math.max(...values, ES_MIDLINE);
  const bottom = Math.min(...values, ES_MIDLINE);
  if (top === bottom) return ES_MIDLINE;
  return (top - ES_MIDLINE) / (top - bottom);
}

/** Mistake/blunder flaw-dot radius. */
const FLAW_DOT_RADIUS = 4.5;

/** Hollow-square half-side as a fraction of FLAW_DOT_RADIUS (visually balances the filled circle). */
const SQUARE_HALF_SIDE_FACTOR = 0.85;

/**
 * The flaw-marker glyph: filled circle for the player (is_user), hollow square
 * for the opponent — color = severity (D-07). Shared by the chart dot renderer
 * and the tooltip so the two surfaces stay in sync. fill="none" is explicit on
 * the square to avoid SVG's default black fill (Pitfall 6 — omitting the fill
 * attribute is not the same as transparent).
 */
function flawDotElement(
  isUser: boolean,
  color: string,
  cx: number,
  cy: number,
  r: number,
  key: string,
): React.ReactElement {
  if (isUser) {
    return <circle key={key} cx={cx} cy={cy} r={r} fill={color} />;
  }
  const s = r * SQUARE_HALF_SIDE_FACTOR;
  return (
    <rect
      key={key}
      x={cx - s}
      y={cy - s}
      width={2 * s}
      height={2 * s}
      fill="none"
      stroke={color}
      strokeWidth={2}
      strokeLinejoin="round"
    />
  );
}

/**
 * Custom dot render prop for the invisible <Line> overlay.
 * Draws filled circles (player) or hollow squares (opponent) at mistake/blunder
 * plies — inaccuracies are not in the map, so they get no dot. Returns empty <g>
 * for non-flaw plies — never returns null (Pitfall 7).
 */
function buildDotRenderer(markerMap: Map<number, FlawMarker>) {
  return function customDotRenderer(props: {
    cx?: number;
    cy?: number;
    payload?: EvalPoint;
  }): React.ReactElement {
    const { cx, cy, payload } = props;
    if (!payload || cx == null || cy == null || !Number.isFinite(cx) || !Number.isFinite(cy)) {
      // Empty <g> not null — avoids React key warning (recharts 3.8.1 Pitfall 7).
      return <g key={`nodot-${String(payload?.ply ?? cx)}`} />;
    }
    const marker = markerMap.get(payload.ply);
    if (!marker || payload.es == null) {
      return <g key={`nodot-${payload.ply}`} />;
    }
    const color = severityColor(marker.severity);
    return flawDotElement(marker.is_user, color, cx, cy, FLAW_DOT_RADIUS, `dot-${payload.ply}`);
  };
}

/** PGN move-number label for a ply — even ply = White ("N.san"), odd = Black ("N...san"). */
function formatMoveLabel(ply: number, san: string | null): string {
  if (!san) return `Ply ${ply}`; // fallback when SAN is missing (e.g. final position)
  const moveNumber = Math.floor(ply / 2) + 1;
  return ply % 2 === 0 ? `${moveNumber}.${san}` : `${moveNumber}...${san}`;
}

/** White-perspective eval string for a ply — mate takes priority over cp. */
function formatEval(point: EvalPoint | undefined): string {
  if (point?.eval_mate != null) {
    // Signed, white-perspective: "Mate in 5#" (White) / "Mate in -6#" (Black).
    return `Eval: Mate in ${point.eval_mate}#`;
  }
  if (point?.eval_cp != null) {
    const cpValue = point.eval_cp / 100;
    const sign = cpValue >= 0 ? '+' : '';
    return `Eval: ${sign}${cpValue.toFixed(1)}`;
  }
  return 'Eval: —';
}

/** Clock remaining as m:ss (floored), e.g. 179.4 → "2:59". */
function formatClock(seconds: number): string {
  const total = Math.max(0, Math.floor(seconds));
  const m = Math.floor(total / 60);
  const s = total % 60;
  return `${m}:${s.toString().padStart(2, '0')}`;
}

/** Inline glyph matching the chart's flaw dot, for the tooltip legend. */
const GLYPH_BOX = 12;
function MarkerGlyph({ isUser, color }: { isUser: boolean; color: string }): React.ReactElement {
  const c = GLYPH_BOX / 2;
  return (
    <svg
      width={GLYPH_BOX}
      height={GLYPH_BOX}
      viewBox={`0 0 ${GLYPH_BOX} ${GLYPH_BOX}`}
      className="shrink-0"
      aria-hidden="true"
    >
      {flawDotElement(isUser, color, c, c, FLAW_DOT_RADIUS, 'glyph')}
    </svg>
  );
}

/** Flaw detail block (glyph + You/Opponent + severity + tags) for a M/B marker. */
function FlawTooltipDetail({ marker }: { marker: FlawMarker }): React.ReactElement {
  const color = severityColor(marker.severity);
  // Drop game-phase tags (opening/middlegame/endgame) — conveyed by the phase
  // lines, not the tooltip.
  const tags = marker.tags.filter((t) => !PHASE_TAGS.has(t));
  return (
    <>
      <div className="flex items-center gap-1.5" style={{ color }}>
        <MarkerGlyph isUser={marker.is_user} color={color} />
        <span>
          {marker.is_user ? 'You' : 'Opponent'} &middot;{' '}
          {marker.severity.charAt(0).toUpperCase() + marker.severity.slice(1)}
        </span>
      </div>
      {tags.length > 0 && (
        <ul className="list-disc pl-5 text-muted-foreground">
          {tags.map((t) => (
            <li key={t}>{t}</li>
          ))}
        </ul>
      )}
    </>
  );
}

/**
 * Tooltip content render prop. Tracks the exact hovered ply (no snapping): shows
 * that ply's move (PGN notation) + white-perspective eval, plus a You/Opponent
 * glyph + severity + tags when the hovered ply is itself a mistake/blunder.
 * Returns null for plies with no eval (es == null).
 */
function buildTooltipContent(
  moves: string[],
  markerMap: Map<number, FlawMarker>,
  evalByPly: Map<number, EvalPoint>,
) {
  return function TooltipContent({
    active,
    payload,
  }: {
    active?: boolean;
    payload?: Array<{ payload?: EvalPoint }>;
  }): React.ReactElement | null {
    if (!active || !payload?.length) return null;
    const point = payload[0]?.payload as EvalPoint | undefined;
    if (!point || point.ply == null || point.es == null) return null;

    const evalStr = formatEval(evalByPly.get(point.ply));
    const moveLabel = formatMoveLabel(point.ply, moves[point.ply] ?? null);
    const marker = markerMap.get(point.ply); // M/B only — undefined on clean plies

    return (
      // text-xs: intentional — established project recharts chart-tooltip pattern.
      // Same as EndgameScoreOverTimeChart, EndgameClockDiffOverTimeChart, FlawTrendChart.
      // CLAUDE.md explicitly exempts hover/tap chart tooltips (popover-surface exception).
      <div className="rounded-lg border border-border/50 bg-background px-3 py-2 text-xs shadow-xl space-y-1">
        <div className="text-muted-foreground">
          {moveLabel} &middot; {evalStr}
        </div>
        {(point.clock_seconds != null || point.move_seconds != null) && (
          <div className="text-muted-foreground">
            {point.clock_seconds != null && <>Clock: {formatClock(point.clock_seconds)}</>}
            {point.clock_seconds != null && point.move_seconds != null && <> &middot; </>}
            {point.move_seconds != null && <>Move: {point.move_seconds.toFixed(1)}s</>}
          </div>
        )}
        {marker && <FlawTooltipDetail marker={marker} />}
      </div>
    );
  };
}

// ─── Component ────────────────────────────────────────────────────────────────

/**
 * Expected-score area chart embedded in LibraryGameCard (Phase 109, LIBG-10).
 *
 * Renders at desktop height h-24 (default) or mobile height h-20 when
 * `heightClass="h-20"` is passed. Wraps in a div with data-testid + aria-label
 * for browser automation and accessibility.
 */
export function EvalChart({
  gameId,
  evalSeries,
  flawMarkers,
  phaseTransitions,
  moves,
  heightClass = 'h-24',
  onHoverPlyChange,
}: EvalChartProps) {
  // Stable SVG gradient ID per instance — prevents collisions when 20 cards
  // render simultaneously (useId from React 18+).
  const rawId = useId();
  const gradientId = `eval-gradient-${rawId.replace(/[^a-zA-Z0-9]/g, '_')}`;

  // Only mistakes/blunders are shown on the chart — inaccuracies get no dot.
  // evalByPly resolves a ply to its eval string for the tooltip.
  const mbMarkers = flawMarkers.filter((m) => m.severity !== 'inaccuracy');
  const evalByPly = new Map(evalSeries.map((p) => [p.ply, p]));

  // O(1) ply lookup for the dot renderer and tooltip (mistakes/blunders only).
  const markerMap = new Map(mbMarkers.map((m) => [m.ply, m]));
  const dotRenderer = buildDotRenderer(markerMap);
  const tooltipContent = buildTooltipContent(moves, markerMap, evalByPly);

  // Where the 0.5 midline sits within the filled area's bounding box, so the
  // gradient colour split lands exactly on the midline (see helper).
  const gradientOffset = midlineGradientOffset(evalSeries);

  // Hover crosshair tracks the EXACT hovered ply (no snapping). We mirror the ply
  // up to the parent (onHoverPlyChange) so the card's miniboard scrubs in sync,
  // and draw our own vertical ReferenceLine at that ply (the default tooltip
  // cursor is disabled below).
  const [hoverPly, setHoverPly] = useState<number | null>(null);
  const updateHoverPly = (ply: number | null) => {
    setHoverPly(ply);
    onHoverPlyChange?.(ply);
  };
  // Mouse and touch share this handler. Recharts fires onMouseMove only on
  // pointer devices, so on touch the crosshair + parent miniboard never updated
  // (the tooltip kept working because Recharts tracks tooltip state internally,
  // independent of these callbacks). onTouchMove delivers the same nextState
  // with activeLabel, so wiring it here syncs the crosshair/miniboard on drag.
  const handlePointerMove = (state: { activeLabel?: string | number }) => {
    const raw = state?.activeLabel;
    updateHoverPly(raw == null ? null : Number(raw));
  };
  const handleMouseLeave = () => updateHoverPly(null);

  return (
    <div
      data-testid={`eval-chart-${gameId}`}
      aria-label={`Expected score chart for game ${gameId}`}
      role="img"
      // Suppress the UA focus outline recharts shows when its surface / tabIndex=-1
      // tooltip wrapper takes focus on click (looked like a white border on the chart).
      //
      // relative z-10 while hovering: the tooltip escapes the chart viewBox (y=true)
      // and overlaps the card content stacked below it (the mobile flaw block, which
      // is later in DOM within the same .charcoal-texture column and would otherwise
      // paint on top). Lifting the chart's subtree keeps the tooltip readable. The
      // card itself bumps to z-30 on hover to clear the *following* card (see
      // LibraryGameCard).
      className={`w-full [&_:focus]:outline-none [&_:focus-visible]:outline-none${
        hoverPly != null ? ' relative z-10' : ''
      }`}
    >
      <ChartContainer config={{}} className={`w-full ${heightClass}`}>
        <ComposedChart
          data={evalSeries}
          margin={{ top: 4, right: 4, left: 4, bottom: 4 }}
          onMouseMove={handlePointerMove}
          onMouseLeave={handleMouseLeave}
          onTouchMove={handlePointerMove}
        >
          <defs>
            {/*
              Two-region vertical gradient split at the 0.5 midline. The split
              offset is data-dependent (gradientOffset) because the Area fills
              from the 0.5 baseline, so its bounding box — to which an
              objectBoundingBox gradient maps — only spans the eval's actual
              range. Above the split = White-ahead (light grey); below = Black-
              ahead (near-black).
            */}
            <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
              <stop offset={0}              stopColor={EVAL_CHART_AREA_WHITE_AHEAD} />
              <stop offset={gradientOffset} stopColor={EVAL_CHART_AREA_WHITE_AHEAD} />
              <stop offset={gradientOffset} stopColor={EVAL_CHART_AREA_BLACK_AHEAD} />
              <stop offset={1}              stopColor={EVAL_CHART_AREA_BLACK_AHEAD} />
            </linearGradient>
          </defs>

          {/* Hidden axes — compact sparkline mode, no ticks or labels. */}
          <XAxis dataKey="ply" hide />
          <YAxis hide domain={[0, 1]} />

          {/* ES area — fills from the 0.5 midline (baseValue), two-region
              gradient split at that midline, no dot markers. */}
          <Area
            type="monotone"
            dataKey="es"
            baseValue={ES_MIDLINE}
            stroke={EVAL_CHART_LINE}
            strokeWidth={1.5}
            fill={`url(#${gradientId})`}
            fillOpacity={1}
            dot={false}
            activeDot={false}
            connectNulls={false}
            isAnimationActive={false}
          />

          {/* 50% midline — dashed horizontal reference. */}
          <ReferenceLine
            y={0.5}
            stroke={EVAL_CHART_MIDLINE}
            strokeWidth={1}
            strokeDasharray="3 3"
            aria-hidden="true"
          />

          {/* Hover crosshair — tracks the exact hovered ply (no snapping). The
              default tooltip cursor is disabled; this dashed vertical line is
              drawn at the hovered ply via the real x-axis scale. */}
          {hoverPly != null && (
            <ReferenceLine
              x={hoverPly}
              stroke={EVAL_CHART_MIDLINE}
              strokeWidth={1}
              strokeDasharray="3 3"
              aria-hidden="true"
            />
          )}

          {/* Phase-transition vertical lines — at most two (D-06).
              Opening boundary (ply 0) gets no line — implicit start of chart. */}
          {phaseTransitions.middlegame_ply != null && (
            <ReferenceLine
              x={phaseTransitions.middlegame_ply}
              stroke={EVAL_CHART_PHASE_LINE}
              strokeWidth={1}
              aria-hidden="true"
            />
          )}
          {phaseTransitions.endgame_ply != null && (
            <ReferenceLine
              x={phaseTransitions.endgame_ply}
              stroke={EVAL_CHART_PHASE_LINE}
              strokeWidth={1}
              aria-hidden="true"
            />
          )}

          {/*
            Invisible line overlay — renders flaw dots via custom dot render prop.
            stroke="none" keeps the line invisible; the dot prop draws the markers.
            Uses the EndgameClockDiffOverTimeChart hollow/filled circle pattern.
          */}
          <Line
            type="monotone"
            dataKey="es"
            stroke="none"
            dot={dotRenderer}
            activeDot={false}
            connectNulls={false}
            isAnimationActive={false}
          />

          {/* Per-ply tooltip showing eval + You/Opponent flaw info.
              allowEscapeViewBox y=true lets it render above/below the short
              sparkline instead of covering it (the chart is only h-20/h-24, so
              an in-viewBox tooltip blankets the whole thing on mobile). */}
          <ChartTooltip
            content={tooltipContent}
            cursor={false}
            allowEscapeViewBox={{ x: false, y: true }}
          />
        </ComposedChart>
      </ChartContainer>
    </div>
  );
}
